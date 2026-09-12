import uuid
from decimal import Decimal
from unittest.mock import MagicMock

import pytest
from pytest_mock import MockerFixture

from apps.basket.repo import BasketRepository
from apps.catalog.repo import DigitalAssetRepository, ProductRepository
from apps.delivery.domain.interfaces import ShippingPricingStrategy
from apps.delivery.domain.services import DeliveryCalculationResult
from apps.delivery.repo import DeliveryRepository
from apps.orders.domain.exceptions import OrderBasketEmptyError
from apps.orders.repo import OrderRepository, PromoCodeRepository
from apps.orders.usecases.cancellation import CancelOrderCase, ExpireOrderCase
from apps.orders.usecases.creation import CreateOrderCase
from apps.orders.usecases.fulfillment import ProcessOrderFulfillmentCase
from apps.payments.repo import PaymentTransactionRepository
from apps.users.repo import UserDeliveryDataRepository, UserRepository


class TestCancelOrderCase:
    """
    Verify business rules for order cancellation orchestration.
    """

    def test_cancel_order_happy_path(self, mocker: MockerFixture) -> None:
        """
        Happy path: Cancels an order, releases stock, and revokes Celery tasks.
        """
        mocker.patch("django.db.transaction.atomic", MagicMock())
        mocker.patch("django.db.transaction.on_commit", side_effect=lambda hook: hook())
        mock_revoke = mocker.patch("apps.orders.usecases.cancellation.current_app.control.revoke")

        mock_order_repo: MagicMock | OrderRepository = MagicMock()
        mock_user_repo: MagicMock | UserRepository = MagicMock()
        mock_delivery_repo: MagicMock | DeliveryRepository = MagicMock()
        mock_payment_repo: MagicMock | PaymentTransactionRepository = MagicMock()
        mock_promocode_repo: MagicMock | PromoCodeRepository = MagicMock()

        fake_user = MagicMock()

        fake_order = MagicMock()
        fake_order.id = uuid.uuid4()
        fake_order.state = "pending"
        fake_order.task_id = uuid.uuid4()
        fake_order.promocode = None
        fake_order.get_active_transaction.return_value = None
        fake_order.target_fiat_money.subtract.return_value.amount = Decimal("0.00")
        fake_order.mark_as_cancelled.return_value = ["state"]
        mock_order_repo.get_for_update_by.return_value = fake_order  # type: ignore[union-attr]

        fake_item_physical = MagicMock()
        fake_item_physical.is_digital = False
        mock_order_repo.get_order_items.return_value = [fake_item_physical]  # type: ignore[union-attr]

        usecase = CancelOrderCase(
            order_repo=mock_order_repo,
            user_repo=mock_user_repo,
            delivery_repo=mock_delivery_repo,
            payment_repo=mock_payment_repo,
            promocode_repo=mock_promocode_repo,
            product_repo=MagicMock(spec=ProductRepository),
            digital_asset_repo=MagicMock(spec=DigitalAssetRepository),
        )

        mock_stock_service = MagicMock()
        mock_digital_asset_service = MagicMock()
        usecase._stock_service = mock_stock_service
        usecase._digital_asset_service = mock_digital_asset_service

        usecase.execute(order_id=fake_order.id, user=fake_user)

        mock_order_repo.get_for_update_by.assert_called_once_with(id=fake_order.id, user=fake_user)  # type: ignore[union-attr]
        mock_order_repo.save.assert_called_once_with(instance=fake_order, update_fields=["state"])  # type: ignore[union-attr]
        mock_stock_service.release_physical.assert_called_once_with(order_items=[fake_item_physical])
        mock_revoke.assert_called_once_with(str(fake_order.task_id), terminate=True)


class TestExpireOrderCase:
    """
    Verify business rules for order expiration orchestration.
    """

    def test_expire_order_happy_path(self, mocker: MockerFixture) -> None:
        """
        Happy path: Expires an order via scheduled tasks without user context.
        """
        mocker.patch("django.db.transaction.atomic", MagicMock())
        mocker.patch("django.db.transaction.on_commit", side_effect=lambda hook: hook())
        mock_revoke = mocker.patch("apps.orders.usecases.cancellation.current_app.control.revoke")

        mock_order_repo: MagicMock | OrderRepository = MagicMock()
        mock_user_repo: MagicMock | UserRepository = MagicMock()
        mock_delivery_repo: MagicMock | DeliveryRepository = MagicMock()

        fake_order = MagicMock()
        fake_order.id = uuid.uuid4()
        fake_order.state = "pending"
        fake_order.task_id = uuid.uuid4()
        fake_order.promocode = None
        fake_order.get_active_transaction.return_value = None
        fake_order.target_fiat_money.subtract.return_value.amount = Decimal("0.00")
        fake_order.mark_as_expired.return_value = ["state"]
        mock_order_repo.get_for_update_by.return_value = fake_order  # type: ignore[union-attr]
        mock_order_repo.get_order_items.return_value = []  # type: ignore[union-attr]

        usecase = ExpireOrderCase(
            order_repo=mock_order_repo,
            user_repo=mock_user_repo,
            delivery_repo=mock_delivery_repo,
            payment_repo=MagicMock(spec=PaymentTransactionRepository),
            promocode_repo=MagicMock(spec=PromoCodeRepository),
            product_repo=MagicMock(spec=ProductRepository),
            digital_asset_repo=MagicMock(spec=DigitalAssetRepository),
        )

        mock_stock_service = MagicMock()
        usecase._stock_service = mock_stock_service
        usecase._digital_asset_service = MagicMock()

        usecase.execute(order_id=fake_order.id)

        mock_order_repo.save.assert_called_once_with(instance=fake_order, update_fields=["state"])  # type: ignore[union-attr]
        mock_stock_service.release_physical.assert_not_called()
        mock_revoke.assert_called_once_with(str(fake_order.task_id), terminate=True)


class TestCreateOrderCase:
    """
    Verify business rules for new order creation orchestration.
    """

    def test_create_order_happy_path(self, mocker: MockerFixture) -> None:
        """
        Happy path: Creates order, calculates costs, reserves items, and clears basket.
        """
        mocker.patch("django.db.transaction.atomic", MagicMock())
        mocker.patch("django.db.transaction.on_commit", side_effect=lambda hook: hook())
        mock_send_task = mocker.patch("apps.orders.usecases.creation.current_app.send_task")

        mock_order_repo: MagicMock | OrderRepository = MagicMock()
        mock_user_repo: MagicMock | UserRepository = MagicMock()
        mock_basket_repo: MagicMock | BasketRepository = MagicMock()
        mock_delivery_repo: MagicMock | DeliveryRepository = MagicMock()
        mock_user_delivery_data_repo: MagicMock | UserDeliveryDataRepository = MagicMock()
        mock_promocode_repo: MagicMock | PromoCodeRepository = MagicMock()
        mock_shipping_strategy: MagicMock | ShippingPricingStrategy = MagicMock()

        fake_user = MagicMock()

        fake_item = MagicMock()
        fake_item.variant.id = 1
        fake_item.variant.is_digital = False
        fake_item.variant.price = Decimal("50.00")
        fake_item.quantity = 2

        fake_basket = MagicMock()
        fake_basket.is_empty = False
        fake_basket.items.all.return_value = [fake_item]
        mock_basket_repo.get_basket_with_items.return_value = fake_basket  # type: ignore[union-attr]
        mock_order_repo.get_pending_orders_count.return_value = 1  # type: ignore[union-attr]

        delivery_result = DeliveryCalculationResult(
            cost=Decimal("15.00"), is_free=False, amount_left_for_free=Decimal("0.00"), is_free_available=True
        )
        mock_shipping_strategy.calculate.return_value = delivery_result  # type: ignore[union-attr]

        fake_order = MagicMock()
        fake_order.id = uuid.uuid4()
        mock_order_repo.create.return_value = fake_order  # type: ignore[union-attr]

        fake_order_item = MagicMock()
        fake_order_item.is_digital = False
        mock_order_repo.bulk_create_items.return_value = [fake_order_item]  # type: ignore[union-attr]

        usecase = CreateOrderCase(
            order_repo=mock_order_repo,
            user_repo=mock_user_repo,
            user_delivery_data_repo=mock_user_delivery_data_repo,
            basket_repo=mock_basket_repo,
            promocode_repo=mock_promocode_repo,
            delivery_repo=mock_delivery_repo,
            product_repo=MagicMock(spec=ProductRepository),
            digital_asset_repo=MagicMock(spec=DigitalAssetRepository),
            shipping_strategy=mock_shipping_strategy,
        )

        mock_basket_service = MagicMock()
        mock_basket_service.calculate.return_value = {
            "total_price": Decimal("100.00"),
            "total_weight_kg": Decimal("2.00"),
        }
        mock_stock_service = MagicMock()
        mock_delivery_validate_service = MagicMock()
        mock_delivery_validate_service.validate_and_format.return_value = {
            "destination_code": "US",
            "region_code": None,
        }

        usecase._basket_calc_service = mock_basket_service
        usecase._stock_service = mock_stock_service
        usecase._digital_asset_service = MagicMock()
        usecase._delivery_validate_service = mock_delivery_validate_service

        result = usecase.execute(user=fake_user, code=None, delivery_data={"destination_code": "US"})

        assert result == str(fake_order.id)
        mock_delivery_validate_service.validate_and_format.assert_called_once()
        mock_order_repo.create.assert_called_once()  # type: ignore[union-attr]
        mock_stock_service.reserve_physical.assert_called_once_with(order_items=[fake_order_item])
        mock_basket_repo.clear_basket.assert_called_once_with(user=fake_user)  # type: ignore[union-attr]
        mock_delivery_repo.create.assert_called_once()  # type: ignore[union-attr]
        mock_send_task.assert_called_once()

    def test_create_order_fails_on_empty_basket(self, mocker: MockerFixture) -> None:
        """
        Failure: Cannot create an order if the user's basket is empty.
        """
        mocker.patch("django.db.transaction.atomic", MagicMock())
        mock_basket_repo: MagicMock | BasketRepository = MagicMock()
        mock_user_repo: MagicMock | UserRepository = MagicMock()
        fake_user = MagicMock()

        fake_basket = MagicMock()
        fake_basket.is_empty = True
        mock_basket_repo.get_basket_with_items.return_value = fake_basket  # type: ignore[union-attr]

        usecase = CreateOrderCase(
            order_repo=MagicMock(spec=OrderRepository),
            user_repo=mock_user_repo,
            user_delivery_data_repo=MagicMock(spec=UserDeliveryDataRepository),
            basket_repo=mock_basket_repo,
            promocode_repo=MagicMock(spec=PromoCodeRepository),
            delivery_repo=MagicMock(spec=DeliveryRepository),
            product_repo=MagicMock(spec=ProductRepository),
            digital_asset_repo=MagicMock(spec=DigitalAssetRepository),
            shipping_strategy=MagicMock(spec=ShippingPricingStrategy),
        )

        mock_delivery_validate_service = MagicMock()
        mock_delivery_validate_service.validate_and_format.return_value = {"destination_code": "US"}
        usecase._delivery_validate_service = mock_delivery_validate_service

        with pytest.raises(OrderBasketEmptyError):
            usecase.execute(user=fake_user)

        mock_delivery_validate_service.validate_and_format.assert_called_once()


class TestProcessOrderFulfillmentCase:
    """
    Verify business rules for post-payment fulfillment orchestration.
    """

    def test_process_fulfillment_happy_path(self, mocker: MockerFixture) -> None:
        """
        Happy path: Commits stock and dispatches processing notifications.
        """
        mocker.patch("django.db.transaction.atomic", MagicMock())
        mocker.patch("django.db.transaction.on_commit", side_effect=lambda hook: hook())
        mock_send_task = mocker.patch("apps.orders.usecases.fulfillment.current_app.send_task")

        mock_order_repo: MagicMock | OrderRepository = MagicMock()
        mock_delivery_repo: MagicMock | DeliveryRepository = MagicMock()

        fake_order = MagicMock()
        fake_order.id = uuid.uuid4()
        fake_order.state = "paid"
        mock_order_repo.get_for_update_by.return_value = fake_order  # type: ignore[union-attr]

        fake_item = MagicMock()
        fake_item.is_digital = False
        mock_order_repo.get_order_items.return_value = [fake_item]  # type: ignore[union-attr]

        fake_delivery = MagicMock()
        fake_delivery.mark_as_processing.return_value = ["state"]
        mock_delivery_repo.get_for_update_by.return_value = fake_delivery  # type: ignore[union-attr]

        usecase = ProcessOrderFulfillmentCase(
            order_repo=mock_order_repo,
            delivery_repo=mock_delivery_repo,
            product_repo=MagicMock(spec=ProductRepository),
            digital_asset_repo=MagicMock(spec=DigitalAssetRepository),
        )

        mock_stock_service = MagicMock()
        usecase._stock_service = mock_stock_service
        usecase._digital_asset_service = MagicMock()

        usecase.execute(order_id=fake_order.id)

        mock_stock_service.commit_all.assert_called_once_with(order_items=[fake_item])
        fake_delivery.mark_as_processing.assert_called_once()
        mock_delivery_repo.save.assert_called_once_with(instance=fake_delivery, update_fields=["state"])  # type: ignore[union-attr]
        mock_send_task.assert_called_once_with(
            "notifications.dispatch_order_paid_notifications", args=[str(fake_order.id)]
        )
