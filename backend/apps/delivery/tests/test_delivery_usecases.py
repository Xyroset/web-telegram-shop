from decimal import Decimal
from typing import cast
from unittest.mock import MagicMock, patch

import pytest

from apps.basket.repo import BasketRepository
from apps.core.domain.exceptions import CoreObjectNotFoundError
from apps.delivery.domain.exceptions import (
    DeliveryConflictDataError,
    DeliveryUnsupportedDestinationError,
)
from apps.delivery.domain.interfaces import ShippingPricingStrategy
from apps.delivery.domain.services import DeliveryCalculationResult
from apps.delivery.repo import DeliveryRepository
from apps.delivery.usecases import (
    CalculateDeliveryEstimateCase,
    DeliverDeliveryCase,
    ReturnDeliveryCase,
    ShipDeliveryCase,
)
from apps.users.models import User
from apps.users.repo import UserDeliveryDataRepository


class TestCalculateDeliveryEstimateCase:
    """
    Verify business rules for orchestrating delivery estimation.
    """

    @patch("apps.delivery.domain.services.DeliveryValidationService.validate_against_config")
    def test_calculate_estimate_success_with_explicit_destination(self, mock_validate_config: MagicMock) -> None:
        """
        Happy path: Calculate delivery estimate with a valid basket and explicit destination.
        """
        mock_strategy: MagicMock | ShippingPricingStrategy = MagicMock()
        mock_basket_repo: MagicMock | BasketRepository = MagicMock()
        mock_delivery_data_repo: MagicMock | UserDeliveryDataRepository = MagicMock()

        fake_item = MagicMock()
        fake_item.variant.volumetric_weight_kg = Decimal("0.00")
        fake_item.variant.weight_kg = Decimal("0.00")
        fake_item.quantity = 1

        fake_basket = MagicMock()
        fake_basket.total_price = Decimal("150.00")
        fake_basket.items.all.return_value = [fake_item]
        mock_basket_repo.get_basket_with_items.return_value = fake_basket  # type: ignore[union-attr]

        expected_result = DeliveryCalculationResult(
            cost=Decimal("10.00"), is_free=False, amount_left_for_free=Decimal("5.00")
        )
        mock_strategy.calculate.return_value = expected_result  # type: ignore[union-attr]

        usecase = CalculateDeliveryEstimateCase(
            strategy=mock_strategy,
            basket_repo=mock_basket_repo,
            user_delivery_data_repo=mock_delivery_data_repo,
        )
        fake_user: MagicMock | User = MagicMock()

        result = usecase.execute(user=fake_user, destination_code="US")

        assert result == expected_result
        mock_basket_repo.get_basket_with_items.assert_called_once_with(user=fake_user)  # type: ignore[union-attr]
        mock_validate_config.assert_called_once_with(destination_code="US", region_code=None)
        mock_strategy.calculate.assert_called_once_with(  # type: ignore[union-attr]
            total_price=Decimal("150.00"),
            billable_weight_kg=Decimal("0.00"),
            destination_code="US",
            region_code=None,
        )

    @patch("apps.delivery.domain.services.DeliveryValidationService.validate_against_config")
    def test_calculate_estimate_fetches_default_destination_when_omitted(self, mock_validate_config: MagicMock) -> None:
        """
        Happy path: Fallback to user's saved delivery data if destination_code is missing.
        """
        mock_strategy: MagicMock | ShippingPricingStrategy = MagicMock()
        mock_basket_repo: MagicMock | BasketRepository = MagicMock()
        mock_delivery_data_repo: MagicMock | UserDeliveryDataRepository = MagicMock()

        cast(MagicMock, mock_basket_repo.get_basket_with_items).side_effect = CoreObjectNotFoundError

        fake_delivery_data = MagicMock()
        fake_delivery_data.destination_code = "GB"
        fake_delivery_data.region_code = "ENG"
        mock_delivery_data_repo.get_by.return_value = fake_delivery_data  # type: ignore[union-attr]

        usecase = CalculateDeliveryEstimateCase(
            strategy=mock_strategy,
            basket_repo=mock_basket_repo,
            user_delivery_data_repo=mock_delivery_data_repo,
        )
        fake_user: MagicMock | User = MagicMock()

        usecase.execute(user=fake_user, destination_code=None)

        mock_delivery_data_repo.get_by.assert_called_once_with(user=fake_user, is_current=True)  # type: ignore[union-attr]
        mock_validate_config.assert_called_once_with(destination_code="GB", region_code="ENG")
        mock_strategy.calculate.assert_called_once_with(  # type: ignore[union-attr]
            total_price=Decimal("0.00"),
            billable_weight_kg=Decimal("0.00"),
            destination_code="GB",
            region_code="ENG",
        )

    @patch("apps.delivery.domain.services.DeliveryValidationService.validate_against_config")
    def test_calculate_estimate_fails_on_unsupported_destination(self, mock_validate_config: MagicMock) -> None:
        """
        Failure: Raises DeliveryUnsupportedDestinationError if destination validation fails.
        """
        mock_strategy: MagicMock | ShippingPricingStrategy = MagicMock()
        mock_basket_repo: MagicMock | BasketRepository = MagicMock()
        mock_delivery_data_repo: MagicMock | UserDeliveryDataRepository = MagicMock()

        cast(MagicMock, mock_basket_repo.get_basket_with_items).side_effect = CoreObjectNotFoundError
        mock_validate_config.side_effect = DeliveryUnsupportedDestinationError(
            "Destination 'INVALID' is not supported."
        )

        usecase = CalculateDeliveryEstimateCase(
            strategy=mock_strategy,
            basket_repo=mock_basket_repo,
            user_delivery_data_repo=mock_delivery_data_repo,
        )
        fake_user: MagicMock | User = MagicMock()

        with pytest.raises(
            DeliveryUnsupportedDestinationError,
            match="Destination 'INVALID' is not supported.",
        ):
            usecase.execute(user=fake_user, destination_code="INVALID")

        mock_strategy.calculate.assert_not_called()  # type: ignore[union-attr]


@patch("django.db.transaction.atomic", MagicMock())
class TestShipDeliveryCase:
    """
    Verify business rules for updating delivery statuses to SHIPPED.
    """

    def test_ship_delivery_success(self) -> None:
        """
        Happy path: Successfully update delivery state to SHIPPED.
        """
        mock_repo: MagicMock | DeliveryRepository = MagicMock()
        fake_delivery = MagicMock()
        fake_delivery.tracking_number = "TRACK123"
        fake_delivery.mark_as_shipped.return_value = ["status"]

        mock_repo.get_for_update_by.return_value = fake_delivery  # type: ignore[union-attr]

        usecase = ShipDeliveryCase(delivery_repo=mock_repo)

        usecase.execute(delivery_id="del_123")

        mock_repo.get_for_update_by.assert_called_once_with(id="del_123")  # type: ignore[union-attr]
        fake_delivery.mark_as_shipped.assert_called_once()
        mock_repo.save.assert_called_once_with(fake_delivery, update_fields=["status"])  # type: ignore[union-attr]

    def test_ship_delivery_fails_without_tracking_number(self) -> None:
        """
        Failure: Cannot ship a delivery if the tracking number is missing.
        """
        mock_repo: MagicMock | DeliveryRepository = MagicMock()
        fake_delivery = MagicMock()
        fake_delivery.tracking_number = None
        mock_repo.get_for_update_by.return_value = fake_delivery  # type: ignore[union-attr]

        usecase = ShipDeliveryCase(delivery_repo=mock_repo)

        with pytest.raises(DeliveryConflictDataError, match="Cannot ship without a tracking number."):
            usecase.execute(delivery_id="del_123")

        mock_repo.save.assert_not_called()  # type: ignore[union-attr]


@patch("django.db.transaction.atomic", MagicMock())
class TestDeliverDeliveryCase:
    """
    Verify business rules for updating delivery statuses to DELIVERED.
    """

    def test_deliver_delivery_success(self) -> None:
        """
        Happy path: Successfully update delivery state to DELIVERED.
        """
        mock_repo: MagicMock | DeliveryRepository = MagicMock()
        fake_delivery = MagicMock()
        fake_delivery.mark_as_delivered.return_value = ["status"]

        mock_repo.get_for_update_by.return_value = fake_delivery  # type: ignore[union-attr]

        usecase = DeliverDeliveryCase(delivery_repo=mock_repo)

        usecase.execute(delivery_id="del_123")

        mock_repo.get_for_update_by.assert_called_once_with(id="del_123")  # type: ignore[union-attr]
        fake_delivery.mark_as_delivered.assert_called_once()
        mock_repo.save.assert_called_once_with(fake_delivery, update_fields=["status"])  # type: ignore[union-attr]


@patch("django.db.transaction.atomic", MagicMock())
class TestReturnDeliveryCase:
    """
    Verify business rules for updating delivery statuses to RETURNED.
    """

    def test_return_delivery_success(self) -> None:
        """
        Happy path: Successfully update delivery state to RETURNED.
        """
        mock_repo: MagicMock | DeliveryRepository = MagicMock()
        fake_delivery = MagicMock()
        fake_delivery.mark_as_returned.return_value = ["status"]

        mock_repo.get_for_update_by.return_value = fake_delivery  # type: ignore[union-attr]

        usecase = ReturnDeliveryCase(delivery_repo=mock_repo)

        usecase.execute(delivery_id="del_123")

        mock_repo.get_for_update_by.assert_called_once_with(id="del_123")  # type: ignore[union-attr]
        fake_delivery.mark_as_returned.assert_called_once()
        mock_repo.save.assert_called_once_with(fake_delivery, update_fields=["status"])  # type: ignore[union-attr]
