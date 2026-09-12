from collections.abc import Mapping
from decimal import Decimal
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from apps.delivery.domain.exceptions import DeliveryUnsupportedDestinationError
from apps.delivery.domain.services import (
    DeliveryCalculationResult,
    DeliveryValidationService,
    DynamicZoneWeightCalculator,
)


class TestDynamicZoneWeightCalculator:
    """
    Verify pure domain business rules for delivery cost and weight calculations.
    """

    def test_calculate_with_standard_weight_and_no_free_shipping(self) -> None:
        """
        Happy path: Calculate cost where total price is below free shipping threshold.

        **Setup:**
        - Base rate: 50.00, Rate per kg: 10.00.
        - Billable weight: 2.5kg (1.5kg extra).
        - Multiplier for 'US': 2.0.

        **Expected:**
        - Weight cost = 50.00 + (1.5 * 10.00) = 65.00.
        - Final cost = 65.00 * 2.0 = 130.00.
        - Not free, with calculated amount left for free shipping.
        """
        calculator = DynamicZoneWeightCalculator(
            base_rate=Decimal("50.00"),
            rate_per_kg=Decimal("10.00"),
            free_threshold=Decimal("100.00"),
            max_multiplier_free_shipping_threshold=Decimal("3.0"),
            zone_multipliers={"us": Decimal("2.0")},
        )

        result = calculator.calculate(
            total_price=Decimal("50.00"),
            billable_weight_kg=Decimal("2.5"),
            destination_code="US",
        )

        assert result == DeliveryCalculationResult(
            cost=Decimal("130.00"),
            is_free=False,
            amount_left_for_free=Decimal("150.00"),
            is_free_available=True,
        )

    def test_calculate_with_free_shipping_reached(self) -> None:
        """
        Happy path: Total price exceeds the adjusted threshold, granting free shipping.

        **Setup:**
        - Free threshold: 100.00, Zone multiplier: 2.0 -> Adjusted: 200.00.
        - Total price: 250.00.
        """
        calculator = DynamicZoneWeightCalculator(
            base_rate=Decimal("50.00"),
            rate_per_kg=Decimal("10.00"),
            free_threshold=Decimal("100.00"),
            max_multiplier_free_shipping_threshold=Decimal("3.0"),
            zone_multipliers={"us": Decimal("2.0")},
        )

        result = calculator.calculate(
            total_price=Decimal("250.00"),
            billable_weight_kg=Decimal("2.0"),
            destination_code="US",
        )

        assert result == DeliveryCalculationResult(
            cost=Decimal("0.00"),
            is_free=True,
            amount_left_for_free=Decimal("0.00"),
            is_free_available=True,
        )

    def test_calculate_with_zero_weight_returns_free(self) -> None:
        """
        Edge case: Basket has 0.00 weight (e.g., empty or digital goods).
        """
        calculator = DynamicZoneWeightCalculator(
            base_rate=Decimal("50.00"),
            rate_per_kg=Decimal("10.00"),
            free_threshold=Decimal("100.00"),
            max_multiplier_free_shipping_threshold=Decimal("3.0"),
            zone_multipliers={},
        )

        result = calculator.calculate(
            total_price=Decimal("100.00"),
            billable_weight_kg=Decimal("0.00"),
        )

        assert result == DeliveryCalculationResult(
            cost=Decimal("0.00"),
            is_free=True,
            amount_left_for_free=Decimal("0.00"),
            is_free_available=True,
        )

    def test_calculate_where_multiplier_disables_free_shipping(self) -> None:
        """
        Edge case: The zone multiplier exceeds the allowed threshold for free shipping.
        """
        calculator = DynamicZoneWeightCalculator(
            base_rate=Decimal("50.00"),
            rate_per_kg=Decimal("10.00"),
            free_threshold=Decimal("100.00"),
            max_multiplier_free_shipping_threshold=Decimal("3.0"),
            zone_multipliers={"au": Decimal("5.0")},
        )

        result = calculator.calculate(
            total_price=Decimal("9999.00"),
            billable_weight_kg=Decimal("2.0"),
            destination_code="AU",
        )

        assert result.is_free is False
        assert result.is_free_available is False
        assert result.amount_left_for_free == Decimal("0.00")


class TestDeliveryValidationService:
    """
    Verify business rules for validating delivery destinations and formatting payload via configuration.
    """

    @patch("apps.delivery.domain.services.shop_config.get")
    def test_validate_against_config_flat_destination_success(self, mock_config_get: MagicMock) -> None:
        """
        Happy path: Successfully validate a flat multiplier destination (case-insensitive).
        """
        mock_config_get.return_value = {"eu": 1.0, "us": {"default": 2.5}}
        service = DeliveryValidationService()

        service.validate_against_config(destination_code="EU", region_code=None)

        mock_config_get.assert_called_once_with("delivery", "zone_multipliers", {})

    @patch("apps.delivery.domain.services.shop_config.get")
    def test_validate_against_config_nested_region_success(self, mock_config_get: MagicMock) -> None:
        """
        Happy path: Successfully validate a nested region inside destination.
        """
        mock_config_get.return_value = {"us": {"al": 2.5, "default": 2.5}}
        service = DeliveryValidationService()

        service.validate_against_config(destination_code="US", region_code="AL")

        mock_config_get.assert_called_once_with("delivery", "zone_multipliers", {})

    @patch("apps.delivery.domain.services.shop_config.get")
    def test_validate_against_config_missing_destination_fails(self, mock_config_get: MagicMock) -> None:
        """
        Failure: Destination code is missing or empty.
        """
        service = DeliveryValidationService()

        with pytest.raises(DeliveryUnsupportedDestinationError, match="Destination code is missing."):
            service.validate_against_config(destination_code=None, region_code=None)

        mock_config_get.assert_not_called()

    @patch("apps.delivery.domain.services.shop_config.get")
    def test_validate_against_config_unsupported_destination_fails(self, mock_config_get: MagicMock) -> None:
        """
        Failure: Destination code does not exist in configuration.
        """
        mock_config_get.return_value = {"eu": 1.0}
        service = DeliveryValidationService()

        with pytest.raises(DeliveryUnsupportedDestinationError, match="Destination 'US' is not supported."):
            service.validate_against_config(destination_code="US", region_code=None)

    @patch("apps.delivery.domain.services.shop_config.get")
    def test_validate_against_config_unsupported_region_fails(self, mock_config_get: MagicMock) -> None:
        """
        Failure: Region code is not supported and no default is defined for the destination.
        """
        mock_config_get.return_value = {"us": {"al": 2.5}}
        service = DeliveryValidationService()

        with pytest.raises(
            DeliveryUnsupportedDestinationError,
            match="Region 'AK' is not supported for 'US'.",
        ):
            service.validate_against_config(destination_code="US", region_code="AK")

    @patch("apps.delivery.domain.services.shop_config.get")
    def test_validate_against_config_missing_required_region_fails(self, mock_config_get: MagicMock) -> None:
        """
        Failure: Region is omitted, but destination requires explicit region (no 'default' key).
        """
        mock_config_get.return_value = {"us": {"al": 2.5}}
        service = DeliveryValidationService()

        with pytest.raises(
            DeliveryUnsupportedDestinationError,
            match="Region code is required for destination 'US'.",
        ):
            service.validate_against_config(destination_code="US", region_code=None)

    @patch("apps.delivery.domain.services.shop_config.get")
    def test_validate_and_format_success(self, mock_config_get: MagicMock) -> None:
        """
        Happy path: Validate raw dictionary payload, verify against config, and return clean VO dict.
        """
        mock_config_get.return_value = {"us": {"default": 2.5, "ny": 2.5}}
        service = DeliveryValidationService()
        raw_data: Mapping[str, Any] = {
            "full_name": "  Alice Smith  ",
            "email": "alice@example.com",
            "phone": "+12345678999",
            "zip_code": "10002",
            "address_line": "123 Main St",
            "destination_code": "us",
            "region_code": "ny",
        }

        result = service.validate_and_format(raw_data=raw_data)

        assert result == {
            "full_name": "Alice Smith",
            "email": "alice@example.com",
            "phone": "+12345678999",
            "zip_code": "10002",
            "address_line": "123 Main St",
            "destination_code": "US",
            "region_code": "NY",
        }
