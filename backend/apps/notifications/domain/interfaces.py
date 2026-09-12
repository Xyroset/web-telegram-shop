from collections.abc import Sequence
from enum import StrEnum
from typing import Protocol

from apps.notifications.domain.entities import (
    OrderItemSnapshotData,
    OrderSnapshotData,
    TicketSnapshotData,
    TransactionSnapshotData,
)


class OrderAlertProvider(Protocol):
    """Protocol for providers capable of sending order paid alerts."""

    def send_order_paid_alert(
        self, order_data: OrderSnapshotData, physical_items: Sequence[OrderItemSnapshotData]
    ) -> None: ...


class TransactionAlertProvider(Protocol):
    """Protocol for providers capable of sending transaction failure alerts."""

    def send_transaction_failed_alert(self, transaction_data: TransactionSnapshotData) -> None: ...


class SupportAlertProvider(Protocol):
    """Protocol for providers capable of handling two-way or one-way support alerts."""

    def send_support_alert(self, ticket_data: TicketSnapshotData) -> int | None: ...


class SystemAlertProvider(Protocol):
    """Protocol for providers capable of sending critical system errors."""

    def send_system_alert(self, source: str, error_message: str, level: str = "ERROR") -> None: ...


class UserNotificationProvider(Protocol):
    """Strategy interface for all outbound user notifications."""

    def send_digital_delivery(
        self, order_data: OrderSnapshotData, digital_items: Sequence[OrderItemSnapshotData], language: str
    ) -> None: ...


class TypeAdminNotification(StrEnum):
    ORDER_PAID = "order_paid"
    TRANSACTION_FAILED = "transaction_failed"
    SUPPORT = "support"
    SYSTEM = "system"
