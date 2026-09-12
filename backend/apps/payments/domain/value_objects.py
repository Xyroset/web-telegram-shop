from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class CryptoMoney:
    """
    Value Object representing a specific amount of cryptocurrency
    on a specific blockchain network.

    **Business Rules:**
    - Amount cannot be negative.
    - Currency and network identifiers must be provided.
    - Instances are immutable (frozen).
    """

    amount: Decimal
    currency: str
    network: str

    def __post_init__(self) -> None:
        if self.amount < Decimal("0.00000000"):
            raise ValueError("Crypto amount cannot be negative.")
        if not self.currency.strip():
            raise ValueError("Currency must be specified.")
        if not self.network.strip():
            raise ValueError("Network must be specified.")

    def add(self, other_amount: Decimal) -> "CryptoMoney":
        if other_amount < Decimal("0"):
            raise ValueError("Cannot add a negative amount.")
        return CryptoMoney(amount=self.amount + other_amount, currency=self.currency, network=self.network)


@dataclass(frozen=True)
class FiatMoney:
    """
    Value Object representing fiat currency (default USD).

    **Business Rules:**
    - Amount cannot be negative.
    - Encapsulates rounding logic (quantize to 2 decimal places).
    """

    amount: Decimal
    currency: str = "USD"

    def __post_init__(self) -> None:
        if self.amount < Decimal("0.00"):
            raise ValueError("Fiat amount cannot be negative.")

        object.__setattr__(self, "amount", self.amount.quantize(Decimal("0.01")))

    def subtract(self, value: "Decimal | FiatMoney") -> "FiatMoney":
        sub_amount = value.amount if isinstance(value, FiatMoney) else value
        new_amount = self.amount - sub_amount

        if new_amount < Decimal("0.00"):
            new_amount = Decimal("0.00")

        return FiatMoney(amount=new_amount, currency=self.currency)

    def add(self, value: "Decimal | FiatMoney") -> "FiatMoney":
        add_amount = value.amount if isinstance(value, FiatMoney) else value
        return FiatMoney(amount=self.amount + add_amount, currency=self.currency)
