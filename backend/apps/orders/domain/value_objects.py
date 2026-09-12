from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class FiatMoney:
    """
    Value Object representing fiat currency in the Orders domain.

    **Business Rules:**
    - Amount cannot be negative.
    - Encapsulates rounding logic (quantize to 2 decimal places).
    - Default currency is USD.
    """

    amount: Decimal
    currency: str = "USD"

    def __post_init__(self) -> None:
        if self.amount < Decimal("0.00"):
            raise ValueError("Fiat amount cannot be negative.")

        object.__setattr__(self, "amount", self.amount.quantize(Decimal("0.01")))

    def subtract(self, other_amount: Decimal) -> "FiatMoney":
        result = self.amount - other_amount
        return FiatMoney(amount=result if result > Decimal("0.00") else Decimal("0.00"))
