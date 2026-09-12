import logging
from collections import defaultdict
from collections.abc import Sequence

from django.db import transaction as ts

from apps.catalog.repo import DigitalAssetRepository
from apps.notifications.domain.dto import (
    map_order_item_to_snapshot,
    map_order_to_snapshot,
    map_ticket_to_snapshot,
    map_transaction_to_snapshot,
)
from apps.notifications.domain.exceptions import NotificationProviderRunTimeError, NotificationProvidersNotFound
from apps.notifications.domain.interfaces import (
    OrderAlertProvider,
    SupportAlertProvider,
    SystemAlertProvider,
    TransactionAlertProvider,
    UserNotificationProvider,
)
from apps.orders.repo import OrderRepository
from apps.payments.repo import PaymentTransactionRepository
from apps.support.repo import TicketRepository
from apps.users.repo import UserSettingsDataRepository

logger = logging.getLogger(__name__)


class NotifyAdminOrderPaidCase:
    """
    Orchestrates the dispatch of order alerts to administrative notification providers.

    **Business Rules:**
    - Retrieves full order data by ID.
    - Iterates through all registered order alert providers and attempts to send the alert.
    - Isolates provider failures: if one fails, others are still processed.

    **Required:**
    - At least one provider must be injected. Otherwise, raises NotificationProvidersNotFound.
    - If one or more providers fail, raises NotificationProviderRunTimeError detailing the failed providers.
    """

    def __init__(self, order_repo: OrderRepository, providers: Sequence[OrderAlertProvider]) -> None:
        self._order_repo = order_repo
        self._providers = providers

    def execute(self, order_id: str) -> None:
        order = self._order_repo.get_order_with_delivery_data(order_id=order_id)
        order_items = self._order_repo.get_order_items(order=order)

        order_snapshot = map_order_to_snapshot(order=order)
        physical_items = [map_order_item_to_snapshot(item=item) for item in order_items if not item.is_digital]

        if not self._providers:
            raise NotificationProvidersNotFound()

        failed_providers = []

        for provider in self._providers:
            provider_name = provider.__class__.__name__
            try:
                provider.send_order_paid_alert(order_data=order_snapshot, physical_items=physical_items)
            except Exception as exc:
                logger.error(f"{provider_name} failed to send alert for order {order_id}: {str(exc)}")
                failed_providers.append(provider_name)

        if failed_providers:
            raise NotificationProviderRunTimeError(
                f"Notification dispatch failed for providers: {', '.join(failed_providers)}"
            )


class NotifyAdminTransactionFailedCase:
    """
    Orchestrates the dispatch of failed transaction alerts to administrative notification providers.

    **Business Rules:**
    - Retrieves full transaction data by ID.
    - Iterates through all registered transaction alert providers and attempts to send the alert.
    - Isolates provider failures: if one fails, others are still processed.

    **Required:**
    - At least one provider must be injected. Otherwise, raises NotificationProvidersNotFound.
    - If one or more providers fail, raises NotificationProviderRunTimeError detailing the failed providers.
    """

    def __init__(
        self, payment_repo: PaymentTransactionRepository, providers: Sequence[TransactionAlertProvider]
    ) -> None:
        self._payment_repo = payment_repo
        self._providers = providers

    def execute(self, transaction_id: str) -> None:
        transaction = self._payment_repo.get_by_id_with_full_details(transaction_id=transaction_id)
        transaction_snapshot = map_transaction_to_snapshot(transaction=transaction)

        if not self._providers:
            raise NotificationProvidersNotFound()

        failed_providers = []

        for provider in self._providers:
            provider_name = provider.__class__.__name__
            try:
                provider.send_transaction_failed_alert(transaction_data=transaction_snapshot)
            except Exception as exc:
                logger.error(f"{provider_name} failed to send alert for transaction {transaction.id}: {str(exc)}")
                failed_providers.append(provider_name)

        if failed_providers:
            raise NotificationProviderRunTimeError(
                f"Notification dispatch failed for providers: {', '.join(failed_providers)}"
            )


class NotifyAdminSupportTicketCase:
    """
    Orchestrates the dispatch of support ticket alerts.

    **Business Rules:**
    - Retrieves full ticket data by ID using the TicketRepository.
    - Iterates through all registered support providers and attempts to send the alert.
    - Updates the ticket with the tracking message ID (if returned by the provider) for future triage.
    - Isolates provider failures: if one fails, others are still processed.

    **Required:**
    - At least one provider must be injected. Otherwise, raises NotificationProvidersNotFound.
    - If one or more providers fail, raises NotificationProviderRunTimeError detailing the failed providers.
    """

    def __init__(self, ticket_repo: TicketRepository, providers: Sequence[SupportAlertProvider]) -> None:
        self._ticket_repo = ticket_repo
        self._providers = providers

    def execute(self, ticket_id: str) -> None:
        ticket = self._ticket_repo.get_by_id_with_full_details(for_update=False, id=ticket_id)
        ticket_snapshot = map_ticket_to_snapshot(ticket=ticket)

        if not self._providers:
            raise NotificationProvidersNotFound()

        failed_providers = []
        msg_id = 0

        for provider in self._providers:
            provider_name = provider.__class__.__name__
            try:
                msg = provider.send_support_alert(ticket_data=ticket_snapshot)
                if msg:
                    msg_id = msg
            except Exception as exc:
                logger.error(f"{provider_name} failed to send alert for ticket {ticket_id}: {exc}")
                failed_providers.append(provider_name)

        if failed_providers:
            raise NotificationProviderRunTimeError(
                f"Notification dispatch failed for providers: {', '.join(failed_providers)}"
            )

        with ts.atomic():
            ticket = self._ticket_repo.get_by_id_with_full_details(for_update=True, id=ticket_id)
            update_fields = ticket.update_triage_message(triage_message_id=msg_id)
            self._ticket_repo.save(instance=ticket, update_fields=update_fields)


class NotifyAdminSystemAlertCase:
    """
    Orchestrates the dispatch of critical system alerts.

    **Business Rules:**
    - Does not require a repository as it deals with raw infrastructure strings.
    - Iterates through all registered system alert providers and attempts to send the alert.
    - Isolates provider failures.

    **Required:**
    - At least one provider must be injected. Otherwise, raises NotificationProvidersNotFound.
    - If one or more providers fail, raises NotificationProviderRunTimeError detailing the failed providers.
    """

    def __init__(self, providers: Sequence[SystemAlertProvider]) -> None:
        self._providers = providers

    def execute(self, source: str, error_message: str, level: str = "ERROR") -> None:
        if not self._providers:
            raise NotificationProvidersNotFound()

        failed_providers = []

        for provider in self._providers:
            provider_name = provider.__class__.__name__
            try:
                provider.send_system_alert(source=source, error_message=error_message, level=level)
            except Exception as exc:
                logger.error(f"{provider_name} failed to send system alert from {source}: {exc}")
                failed_providers.append(provider_name)

        if failed_providers:
            raise NotificationProviderRunTimeError(
                f"Notification dispatch failed for providers: {', '.join(failed_providers)}"
            )


class NotifyUserDigitalDeliveryCase:
    """
    Orchestrates the delivery of digital keys directly to the user.

    **Business Rules:**
    - Retrieves the user's language preferences.
    - Gathers digital keys mapped to the order items.
    - Dispatches to all registered UserNotificationProviders.

    **Required:**
    - Fails silently if no digital items are present in the order.
    """

    def __init__(
        self,
        order_repo: OrderRepository,
        digital_asset_repo: DigitalAssetRepository,
        user_settings_repo: UserSettingsDataRepository,
        providers: Sequence[UserNotificationProvider],
    ) -> None:
        self._order_repo = order_repo
        self._digital_asset_repo = digital_asset_repo
        self._user_settings_repo = user_settings_repo
        self._providers = providers

    def execute(self, order_id: str) -> None:
        order = self._order_repo.get_by(id=order_id)
        user_settings = self._user_settings_repo.get_by(user=order.user)
        user_language = user_settings.current_language_code

        order_items = self._order_repo.get_order_items(order=order)
        digital_items = [item for item in order_items if item.is_digital]

        if not digital_items:
            return

        item_ids = [str(item.id) for item in digital_items]
        assets = self._digital_asset_repo.filter_by(order_item_id__in=item_ids)

        assets_map = defaultdict(list)
        for asset in assets:
            if asset.order_item_id:
                assets_map[str(asset.order_item_id)].append(asset.content)

        order_snapshot = map_order_to_snapshot(order=order)
        digital_snapshots = [
            map_order_item_to_snapshot(item=item, digital_keys=assets_map.get(str(item.id), []))
            for item in digital_items
        ]

        for provider in self._providers:
            provider.send_digital_delivery(
                order_data=order_snapshot, digital_items=digital_snapshots, language=user_language
            )
