from collections.abc import Mapping
from decimal import Decimal
from typing import Any

from apps.core.config_manager import shop_config
from apps.delivery.domain.exceptions import DeliveryUnsupportedDestinationError
from apps.delivery.domain.interfaces import DeliveryCalculationResult
from apps.delivery.domain.value_objects import DeliveryDataVO


class DynamicZoneWeightCalculator:
    def __init__(
        self,
        base_rate: Decimal,
        rate_per_kg: Decimal,
        free_threshold: Decimal,
        max_multiplier_free_shipping_threshold: Decimal,
        zone_multipliers: dict[str, Any],
        default_multiplier: Decimal = Decimal("4.0"),
    ) -> None:
        self._base_rate = base_rate
        self._rate_per_kg = rate_per_kg
        self._free_threshold = free_threshold
        self._max_multiplier_free_shipping_threshold = max_multiplier_free_shipping_threshold
        self._zone_multipliers = zone_multipliers
        self._default_multiplier = default_multiplier

    def calculate(
        self,
        total_price: Decimal,
        billable_weight_kg: Decimal,
        destination_code: str | None = None,
        region_code: str | None = None,
    ) -> DeliveryCalculationResult:

        multiplier = self._default_multiplier

        if billable_weight_kg == Decimal("0.00"):
            return DeliveryCalculationResult(
                cost=Decimal("0.00"),
                is_free=True,
                amount_left_for_free=Decimal("0.00"),
                is_free_available=True,
            )

        if destination_code:
            zone_data = self._zone_multipliers.get(destination_code.lower())

            if zone_data is not None:
                if isinstance(zone_data, dict):
                    region_val = None
                    if region_code:
                        region_val = zone_data.get(region_code.lower())

                    if region_val is None:
                        region_val = zone_data.get("default", self._default_multiplier)

                    multiplier = Decimal(str(region_val))
                else:
                    multiplier = Decimal(str(zone_data))

        extra_weight = max(Decimal("0.0"), billable_weight_kg - Decimal("1.0"))
        weight_cost = self._base_rate + (extra_weight * self._rate_per_kg)
        final_cost = (weight_cost * multiplier).quantize(Decimal("0.01"))

        is_free_available = multiplier <= self._max_multiplier_free_shipping_threshold

        if not is_free_available:
            return DeliveryCalculationResult(
                cost=final_cost,
                is_free=False,
                amount_left_for_free=Decimal("0.00"),
                is_free_available=False,
            )

        adjusted_free_threshold = self._free_threshold * multiplier

        if total_price >= adjusted_free_threshold:
            return DeliveryCalculationResult(
                cost=Decimal("0.00"),
                is_free=True,
                amount_left_for_free=Decimal("0.00"),
                is_free_available=True,
            )

        amount_left = (adjusted_free_threshold - total_price).quantize(Decimal("0.01"))

        return DeliveryCalculationResult(
            cost=final_cost,
            is_free=False,
            amount_left_for_free=amount_left,
            is_free_available=True,
        )


class DeliveryValidationService:
    """
    Domain service to validate delivery destination via config and enforce VO data formats.
    """

    def validate_against_config(self, destination_code: str | None, region_code: str | None = None) -> None:
        """
        Validate destination and region codes against the active shop configuration.
        """
        if not destination_code or not destination_code.strip():
            raise DeliveryUnsupportedDestinationError("Destination code is missing.")

        dest_code = destination_code.strip().lower()
        reg_code = region_code.strip().lower() if region_code and region_code.strip() else None

        multipliers: Mapping[str, Any] = shop_config.get("delivery", "zone_multipliers", {})

        if dest_code not in multipliers:
            raise DeliveryUnsupportedDestinationError(f"Destination '{dest_code.upper()}' is not supported.")

        zone_data = multipliers[dest_code]

        if isinstance(zone_data, dict):
            if reg_code:
                if reg_code not in zone_data and "default" not in zone_data:
                    raise DeliveryUnsupportedDestinationError(
                        f"Region '{reg_code.upper()}' is not supported for '{dest_code.upper()}'."
                    )
            else:
                if "default" not in zone_data:
                    raise DeliveryUnsupportedDestinationError(
                        f"Region code is required for destination '{dest_code.upper()}'."
                    )
        else:
            if reg_code:
                raise DeliveryUnsupportedDestinationError(
                    f"Region '{reg_code.upper()}' is not supported for '{dest_code.upper()}'."
                )

    def validate_and_format(self, raw_data: Mapping[str, Any]) -> dict[str, str | None]:
        """
        Validate raw payload, check configuration constraints, and return clean VO data.
        """
        dest_code_raw = raw_data.get("destination_code")
        dest_code = str(dest_code_raw).strip() if dest_code_raw else ""

        region_code_raw = raw_data.get("region_code")
        reg_code = str(region_code_raw).strip() if region_code_raw else ""

        self.validate_against_config(destination_code=dest_code, region_code=reg_code)

        vo = DeliveryDataVO(
            full_name=str(raw_data.get("full_name", "")).strip(),
            email=str(raw_data.get("email", "")).strip(),
            phone=str(raw_data.get("phone", "")).strip(),
            zip_code=str(raw_data.get("zip_code", "")).strip(),
            address_line=str(raw_data.get("address_line", "")).strip(),
            destination_code=dest_code.upper(),
            region_code=reg_code.upper() if reg_code else "",
        )

        return vo.to_dict()
