import logging
import uuid
from typing import Any

from celery import current_app
from django.db import transaction as ts
from django.forms.models import model_to_dict

from apps.basket.domain.services import BasketCalculationService
from apps.basket.repo import BasketRepository
from apps.catalog.repo import DigitalAssetRepository, ProductRepository
from apps.core.config_manager import shop_config
from apps.core.domain.exceptions import CoreObjectNotFoundError
from apps.delivery.domain.interfaces import ShippingPricingStrategy
from apps.delivery.domain.services import DeliveryValidationService
from apps.delivery.models import Delivery
from apps.delivery.repo import DeliveryRepository
from apps.orders.domain.dto import OrderItemDTO
from apps.orders.domain.exceptions import (
    OrderBasketEmptyError,
    OrderPendingLimitExceededError,
    PromoCodeAlreadyUsedError,
)
from apps.orders.domain.services import DigitalAssetManagementService, StockManagementService
from apps.orders.models import Order
from apps.orders.repo import OrderRepository, PromoCodeRepository
from apps.users.models import User
from apps.users.repo import UserDeliveryDataRepository, UserRepository

logger = logging.getLogger(__name__)


class CreateOrderCase:
    """
    Create an order from the user's shopping basket.

    **Business Rules:**
    - Resolves delivery data (explicit or fallback to user defaults) and validates it via DeliveryValidationService.
    - Validates that the basket is not empty and pending order limits are not exceeded.
    - Resolves and validates promo codes, updating their usage metrics.
    - Calculates basket items and shipping costs using pure Domain Services and injected Strategy.
    - Creates a new Order Aggregate Root in PENDING state.
    - Maps basket items to OrderItems and reserves physical/digital stock via Domain Services.
    - Empties the user's basket upon successful item reservation.
    - Creates the corresponding Delivery record.
    - Dispatches a Celery task on transaction commit to automatically expire the order after timeout.

    **Required:**
    - User basket must not be empty. Otherwise raises **OrderBasketEmptyError**.
    - User must not exceed the pending orders limit. Otherwise raises **OrderPendingLimitExceededError**.
    - Promo code (if provided) must be active and valid for the order.
    """

    def __init__(
        self,
        order_repo: OrderRepository,
        user_repo: UserRepository,
        user_delivery_data_repo: UserDeliveryDataRepository,
        basket_repo: BasketRepository,
        promocode_repo: PromoCodeRepository,
        delivery_repo: DeliveryRepository,
        product_repo: ProductRepository,
        digital_asset_repo: DigitalAssetRepository,
        shipping_strategy: ShippingPricingStrategy,
    ) -> None:
        self._order_repo = order_repo
        self._user_repo = user_repo
        self._user_delivery_data_repo = user_delivery_data_repo
        self._basket_repo = basket_repo
        self._promocode_repo = promocode_repo
        self._delivery_repo = delivery_repo
        self._shipping_strategy = shipping_strategy

        self._basket_calc_service = BasketCalculationService()
        self._stock_service = StockManagementService(product_repo=product_repo)
        self._digital_asset_service = DigitalAssetManagementService(
            digital_asset_repo=digital_asset_repo,
            product_repo=product_repo,
        )
        self._delivery_validate_service = DeliveryValidationService()

    def execute(
        self,
        user: User,
        code: str | None = None,
        delivery_data: dict[str, Any] | None = None,
    ) -> str:
        destination_code = delivery_data.get("destination_code") if delivery_data else None

        delivery_data = delivery_data if delivery_data else {}
        if not destination_code:
            try:
                preferred_delivery = self._user_delivery_data_repo.get_by(user=user, is_current=True)
                delivery_data = model_to_dict(
                    instance=preferred_delivery,
                    fields=[
                        "full_name",
                        "email",
                        "phone",
                        "zip_code",
                        "address_line",
                        "destination_code",
                        "region_code",
                    ],
                )
            except CoreObjectNotFoundError:
                delivery_data["destination_code"] = None
                delivery_data["region_code"] = None

        print(delivery_data)
        delivery_data = self._delivery_validate_service.validate_and_format(raw_data=delivery_data)

        with ts.atomic():
            basket = self._basket_repo.get_basket_with_items(user=user)
            if basket.is_empty:
                raise OrderBasketEmptyError()

            pending_count = self._order_repo.get_pending_orders_count(user=user)
            pending_limit = shop_config.get("order", "order_settings.order_pending_limit", 3)
            if pending_count >= pending_limit:
                raise OrderPendingLimitExceededError()

            basket_items = list(basket.items.all())

            promocode = None
            if code:
                promocode = self._promocode_repo.get_for_update_by(code=code)

            basket_result = self._basket_calc_service.calculate(
                user=user,
                basket=basket,
                basket_items=basket_items,
                promocode=promocode,
            )

            if promocode:
                promo_changed_fields = promocode.update_promocode_usage()
                self._promocode_repo.save(promocode, update_fields=promo_changed_fields)

                try:
                    user_promocode = self._user_repo.get_user_promocode(user=user, promocode=promocode)
                    if promocode.max_uses_per_user > user_promocode.used + 1:
                        user_promocode.update_used(new_used=user_promocode.used + 1)
                    else:
                        raise PromoCodeAlreadyUsedError(
                            f"Promo code already used by this user! Max uses: {promocode.max_uses_per_user}"
                        )
                except CoreObjectNotFoundError:
                    user_promocode = user.prepare_user_promocode(promocode=promocode)

                self._user_repo.save_user_promocode(user_promocode=user_promocode)

            delivery_result = self._shipping_strategy.calculate(
                total_price=basket_result.get("total_price"),
                billable_weight_kg=basket_result.get("total_weight_kg"),
                destination_code=delivery_data.get("destination_code"),
                region_code=delivery_data.get("region_code"),
            )

            final_order_amount = basket_result["total_price"] + delivery_result.cost
            expire_task_id = uuid.uuid4()

            order = self._order_repo.create(
                user=user,
                amount_usd=final_order_amount,
                state=Order.Status.PENDING,
                promocode=promocode,
                task_id=expire_task_id,
            )

            item_dtos = [
                OrderItemDTO(
                    variant_id=item.variant.id,
                    quantity=item.quantity,
                    fixed_price=item.variant.price,
                    is_digital=item.variant.is_digital,
                )
                for item in basket_items
            ]

            order_items_to_create = order.add_items_from_dto(items_dto=item_dtos)
            order_items = self._order_repo.bulk_create_items(items=order_items_to_create)

            physical_items = [item for item in order_items if not item.is_digital]
            digital_items = [item for item in order_items if item.is_digital]

            if digital_items:
                self._digital_asset_service.allocate_and_reserve(order_items=digital_items)
            if physical_items:
                self._stock_service.reserve_physical(order_items=physical_items)

            self._basket_repo.clear_basket(user=user)

            self._delivery_repo.create(
                order=order,
                state=Delivery.Status.PENDING,
                cost=delivery_result.cost,
                delivery_data=delivery_data,
            )

        countdown = shop_config.get("order", "order_settings.order_lifetime_minutes", 20) * 60

        def expire_order() -> None:
            current_app.send_task(
                "orders.expire_order",
                args=[str(order.id)],
                task_id=str(expire_task_id),
                countdown=countdown,
            )

        ts.on_commit(expire_order)

        return str(order.id)
