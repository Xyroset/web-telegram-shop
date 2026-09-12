from collections.abc import Mapping, Sequence
from decimal import Decimal
from typing import Any, Protocol


class DeliverySnapshotData(Protocol):
    @property
    def provider_code(self) -> str: ...

    @property
    def cost(self) -> Decimal: ...

    @property
    def delivery_data(self) -> Mapping[str, Any]: ...


class UserSnapshotData(Protocol):
    @property
    def tg_username(self) -> str: ...

    @property
    def tg_id(self) -> int: ...


class OrderSnapshotData(Protocol):
    @property
    def id(self) -> str: ...

    @property
    def user(self) -> UserSnapshotData: ...

    @property
    def amount_usd(self) -> Decimal: ...

    @property
    def state(self) -> str: ...

    @property
    def delivery(self) -> DeliverySnapshotData: ...


class ProductSnapshotData(Protocol):
    @property
    def name(self) -> str: ...


class ProductVariantSnapshotData(Protocol):
    @property
    def title(self) -> str: ...

    @property
    def product(self) -> ProductSnapshotData: ...


class OrderItemSnapshotData(Protocol):
    @property
    def variant(self) -> ProductVariantSnapshotData: ...

    @property
    def quantity(self) -> int: ...

    @property
    def digital_keys(self) -> Sequence[str]: ...


class TransactionSnapshotData(Protocol):
    @property
    def id(self) -> str: ...

    @property
    def order(self) -> OrderSnapshotData: ...

    @property
    def invoice_id(self) -> str: ...

    @property
    def payment_currency(self) -> str: ...

    @property
    def network(self) -> str: ...

    @property
    def target_amount_usd(self) -> Decimal: ...

    @property
    def amount_crypto(self) -> Decimal: ...

    @property
    def current_amount_crypto(self) -> Decimal: ...

    @property
    def captured_amount_usd(self) -> Decimal: ...

    @property
    def receiver_address(self) -> str: ...

    @property
    def sender_address(self) -> str: ...

    @property
    def tx_hash(self) -> str: ...

    @property
    def state(self) -> str: ...

    @property
    def raw_response(self) -> Mapping[str, Any]: ...


class Message(Protocol):
    @property
    def text(self) -> str: ...


class TicketSnapshotData(Protocol):
    @property
    def id(self) -> str: ...

    @property
    def user(self) -> UserSnapshotData: ...

    @property
    def category(self) -> str: ...

    @property
    def state(self) -> str: ...

    @property
    def first_message(self) -> Message: ...
