import logging

from celery import shared_task

from apps.catalog.repo import DigitalAssetRepository
from apps.core.domain.exceptions import CoreObjectNotFoundError
from apps.core.tasks import ErrorHandlingTask
from apps.notifications.domain import exceptions
from apps.notifications.factory import (
    get_active_user_providers,
    get_order_alert_providers,
    get_support_alert_providers,
    get_system_alert_providers,
    get_transaction_alert_providers,
)
from apps.notifications.usecases import (
    NotifyAdminOrderPaidCase,
    NotifyAdminSupportTicketCase,
    NotifyAdminSystemAlertCase,
    NotifyAdminTransactionFailedCase,
    NotifyUserDigitalDeliveryCase,
)
from apps.orders.repo import OrderRepository
from apps.payments.repo import PaymentTransactionRepository
from apps.support.repo import TicketRepository
from apps.users.repo import UserSettingsDataRepository

logger = logging.getLogger(__name__)


@shared_task(
    base=ErrorHandlingTask,
    name="notifications.dispatch_order_paid_notifications",
    bind=True,
    max_retries=3,
    default_retry_delay=120,
)
def dispatch_admin_order_paid_notifications_task(self, order_id: str) -> None:
    """
    **Business Rules:**
    - Initializes order alert providers and delegates dispatch to NotifyAdminOrderPaidCase.
    - Suppresses CoreObjectNotFoundError to prevent infinite retries on non-existent records.
    - Retries task if provider runtime failures occur.
    """
    order_repo = OrderRepository()
    providers = get_order_alert_providers()

    usecase = NotifyAdminOrderPaidCase(order_repo=order_repo, providers=providers)

    try:
        usecase.execute(order_id=order_id)
    except CoreObjectNotFoundError:
        logger.error(f"Order not found for notification dispatch: {order_id}")
    except (exceptions.NotificationProvidersNotFound, exceptions.NotificationProviderRunTimeError) as exc:
        raise self.retry(exc=exc)


@shared_task(
    base=ErrorHandlingTask,
    name="notifications.dispatch_admin_stuck_funds_transaction_notifications",
    bind=True,
    max_retries=3,
    default_retry_delay=120,
)
def dispatch_admin_stuck_funds_transaction_notifications_task(self, transaction_id: str) -> None:
    """
    **Business Rules:**
    - Initializes transaction alert providers and delegates dispatch to NotifyAdminTransactionFailedCase.
    - Suppresses CoreObjectNotFoundError to prevent retrying on missing transactions.
    - Retries task if notification dispatch fails.
    """
    payment_repo = PaymentTransactionRepository()
    providers = get_transaction_alert_providers()

    usecase = NotifyAdminTransactionFailedCase(payment_repo=payment_repo, providers=providers)

    try:
        usecase.execute(transaction_id=transaction_id)
    except CoreObjectNotFoundError:
        logger.error(f"Transaction not found for notification dispatch: {transaction_id}")
    except (exceptions.NotificationProvidersNotFound, exceptions.NotificationProviderRunTimeError) as exc:
        raise self.retry(exc=exc)


@shared_task(
    base=ErrorHandlingTask,
    name="notifications.dispatch_admin_support_ticket_notifications",
    bind=True,
    max_retries=3,
    default_retry_delay=120,
)
def dispatch_admin_support_ticket_notifications_task(self, ticket_id: str) -> None:
    """
    **Business Rules:**
    - Initializes support alert providers and delegates dispatch to NotifyAdminSupportTicketCase.
    - Suppresses CoreObjectNotFoundError to avoid endless retries for deleted tickets.
    - Retries task if notification dispatch fails.
    """
    ticket_repo = TicketRepository()
    providers = get_support_alert_providers()

    usecase = NotifyAdminSupportTicketCase(ticket_repo=ticket_repo, providers=providers)

    try:
        usecase.execute(ticket_id=ticket_id)
    except CoreObjectNotFoundError:
        logger.error(f"Support ticket not found for notification dispatch: {ticket_id}")
    except (exceptions.NotificationProvidersNotFound, exceptions.NotificationProviderRunTimeError) as exc:
        raise self.retry(exc=exc)


@shared_task(
    base=ErrorHandlingTask,
    name="notifications.dispatch_admin_system_alert",
    bind=True,
    max_retries=3,
    default_retry_delay=120,
)
def dispatch_admin_system_alert_task(self, source: str, error_message: str, level: str = "ERROR") -> None:
    """
    **Business Rules:**
    - Initializes system alert providers and delegates dispatch to NotifyAdminSystemAlertCase.
    - Retries task on transient provider runtime failures.
    """
    providers = get_system_alert_providers()

    usecase = NotifyAdminSystemAlertCase(providers=providers)

    try:
        usecase.execute(source=source, error_message=error_message, level=level)
    except (exceptions.NotificationProvidersNotFound, exceptions.NotificationProviderRunTimeError) as exc:
        raise self.retry(exc=exc)


@shared_task(
    base=ErrorHandlingTask,
    name="notifications.dispatch_user_digital_delivery_task",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def dispatch_user_digital_delivery_task(self, order_id: str) -> None:
    """
    **Business Rules:**
    - Gathers user providers and delivers purchased digital assets to the buyer.
    - Retries on network or telegram delivery failures.
    """
    providers = get_active_user_providers()

    usecase = NotifyUserDigitalDeliveryCase(
        order_repo=OrderRepository(),
        digital_asset_repo=DigitalAssetRepository(),
        user_settings_repo=UserSettingsDataRepository(),
        providers=providers,
    )

    try:
        usecase.execute(order_id=order_id)
    except CoreObjectNotFoundError:
        logger.error(f"Order or user settings not found for digital delivery: {order_id}")
    except Exception as exc:
        logger.error(f"Failed to send digital keys for order {order_id}: {exc}")
        raise self.retry(exc=exc)
