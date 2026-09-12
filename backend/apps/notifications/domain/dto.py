from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, cast

from apps.catalog.models import Product, ProductVariant
from apps.delivery.models import Delivery
from apps.orders.models import Order, OrderItem
from apps.payments.models import PaymentTransaction
from apps.support.models import Ticket, TicketMessage
from apps.users.models import User


@dataclass(frozen=True)
class _UserSnapshotDTO:
    tg_username: str
    tg_id: int


@dataclass(frozen=True)
class _ProductSnapshotDTO:
    name: str


@dataclass(frozen=True)
class _VariantSnapshotDTO:
    title: str
    product: _ProductSnapshotDTO


@dataclass(frozen=True)
class _OrderItemSnapshotDTO:
    variant: _VariantSnapshotDTO
    quantity: int
    digital_keys: list[str]


@dataclass(frozen=True)
class _DeliverySnapshotDTO:
    provider_code: str
    cost: Decimal
    delivery_data: Mapping[str, Any]


@dataclass(frozen=True)
class _OrderSnapshotDTO:
    id: str
    user: _UserSnapshotDTO
    amount_usd: Decimal
    state: str
    delivery: _DeliverySnapshotDTO


@dataclass(frozen=True)
class _TransactionSnapshotDTO:
    id: str
    order: _OrderSnapshotDTO
    invoice_id: str
    payment_currency: str
    network: str
    target_amount_usd: Decimal
    amount_crypto: Decimal
    current_amount_crypto: Decimal
    captured_amount_usd: Decimal
    receiver_address: str
    sender_address: str
    tx_hash: str
    state: str
    raw_response: Mapping[str, Any]


@dataclass(frozen=True)
class _MessageDTO:
    text: str


@dataclass(frozen=True)
class _TicketSnapshotDTO:
    id: str
    user: _UserSnapshotDTO
    category: str
    state: str
    first_message: _MessageDTO


def map_user_to_snapshot(user: User | None) -> _UserSnapshotDTO:
    if not user:
        return _UserSnapshotDTO(tg_username="unknown", tg_id=0)
    return _UserSnapshotDTO(tg_username=str(user.tg_username), tg_id=int(user.tg_id))


def map_product_to_snapshot(product: Product | None) -> _ProductSnapshotDTO:
    if not product:
        return _ProductSnapshotDTO(name="Unknown Product")
    return _ProductSnapshotDTO(name=str(product.name))


def map_product_variant_to_snapshot(variant: ProductVariant | None) -> _VariantSnapshotDTO:
    if not variant:
        return _VariantSnapshotDTO(
            title="Unknown Variant",
            product=_ProductSnapshotDTO(name="Unknown Product"),
        )

    product_dto = map_product_to_snapshot(product=variant.product)
    return _VariantSnapshotDTO(title=str(variant.title), product=product_dto)


def map_order_item_to_snapshot(item: OrderItem, digital_keys: list[str] | None = None) -> _OrderItemSnapshotDTO:
    variant = map_product_variant_to_snapshot(variant=item.variant)
    return _OrderItemSnapshotDTO(variant=variant, quantity=int(item.quantity), digital_keys=digital_keys or [])


def map_delivery_to_snapshot(delivery: Delivery | None) -> _DeliverySnapshotDTO:
    if not delivery:
        return _DeliverySnapshotDTO(
            provider_code="none",
            cost=Decimal("0.00"),
            delivery_data={},
        )
    return _DeliverySnapshotDTO(
        provider_code=str(delivery.provider_code),
        cost=Decimal(delivery.cost),
        delivery_data=cast(Mapping[str, Any], delivery.delivery_data),
    )


def map_order_to_snapshot(order: Order) -> _OrderSnapshotDTO:
    user = map_user_to_snapshot(user=order.user)
    delivery = map_delivery_to_snapshot(delivery=order.delivery)

    return _OrderSnapshotDTO(
        id=str(order.id),
        user=user,
        amount_usd=Decimal(order.amount_usd),
        state=str(order.state),
        delivery=delivery,
    )


def map_transaction_to_snapshot(transaction: PaymentTransaction) -> _TransactionSnapshotDTO:
    order = map_order_to_snapshot(order=transaction.order)
    return _TransactionSnapshotDTO(
        id=str(transaction.id),
        order=order,
        invoice_id=str(transaction.invoice_id),
        payment_currency=str(transaction.payment_currency),
        network=str(transaction.network),
        target_amount_usd=Decimal(transaction.target_amount_usd),
        amount_crypto=Decimal(transaction.amount_crypto),
        current_amount_crypto=Decimal(transaction.current_amount_crypto),
        captured_amount_usd=Decimal(transaction.captured_amount_usd),
        receiver_address=str(transaction.receiver_address),
        sender_address=str(transaction.sender_address),
        tx_hash=str(transaction.tx_hash),
        state=str(transaction.state),
        raw_response=cast(Mapping[str, Any], transaction.raw_response),
    )


def map_message_to_snapshot(ticket_message: TicketMessage | None) -> _MessageDTO:
    if not ticket_message:
        return _MessageDTO(text="")
    return _MessageDTO(text=str(ticket_message.text))


def map_ticket_to_snapshot(ticket: Ticket) -> _TicketSnapshotDTO:
    user = map_user_to_snapshot(user=ticket.user)
    first_msg = map_message_to_snapshot(ticket_message=ticket.first_message)

    return _TicketSnapshotDTO(
        id=str(ticket.id),
        user=user,
        category=str(ticket.category),
        state=str(ticket.state),
        first_message=first_msg,
    )
