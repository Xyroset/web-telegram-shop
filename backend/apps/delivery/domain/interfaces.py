from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol


@dataclass(frozen=True)
class DeliveryCalculationResult:
    cost: Decimal
    is_free: bool
    amount_left_for_free: Decimal
    is_free_available: bool = True


class ShippingPricingStrategy(Protocol):
    def calculate(
        self,
        total_price: Decimal,
        billable_weight_kg: Decimal,
        destination_code: str | None = None,
        region_code: str | None = None,
    ) -> DeliveryCalculationResult: ...
