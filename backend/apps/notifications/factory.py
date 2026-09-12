import logging
import os
from collections.abc import Sequence

from apps.core.config_manager import shop_config
from apps.notifications.domain.interfaces import (
    OrderAlertProvider,
    SupportAlertProvider,
    SystemAlertProvider,
    TransactionAlertProvider,
    TypeAdminNotification,
    UserNotificationProvider,
)
from apps.notifications.providers import (
    EmailAdminProvider,
    TelegramAdminProvider,
    TelegramUserProvider,
    WebhookAdminProvider,
)
from apps.telegram.client import TelegramBotClient
from apps.telegram.usecases import SendTelegramMessageCase

logger = logging.getLogger(__name__)


def _get_telegram_admin_provider(thread_config_key: str, default_thread_id: int) -> TelegramAdminProvider | None:
    """Internal helper to safely initialize the Telegram Admin Provider."""
    telegram_chat_id = shop_config.get(
        "notifications", "notifications_settings.providers_settings.telegram.admin_chat_id"
    )
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")

    if not telegram_chat_id or not bot_token:
        logger.warning("Telegram provider skipped: TELEGRAM_ADMIN_CHAT_ID or TELEGRAM_BOT_TOKEN is missing.")
        return None

    thread_id = shop_config.get(
        "notifications", f"notifications_settings.providers_settings.telegram.{thread_config_key}", default_thread_id
    )
    language = shop_config.get("notifications", "notifications_settings.providers_settings.telegram.language", "en")

    bot_client = TelegramBotClient(token=bot_token)
    telegram_usecase = SendTelegramMessageCase(client=bot_client)

    return TelegramAdminProvider(
        chat_id=telegram_chat_id,
        telegram_usecase=telegram_usecase,
        message_thread_id=thread_id,
        language=language,
    )


def _get_email_admin_provider() -> EmailAdminProvider | None:
    """Internal helper to safely initialize the Email Admin Provider."""
    admin_emails = shop_config.get("notifications", "emails.admin_emails", [])
    if not admin_emails:
        logger.warning("Email provider skipped: ADMIN_EMAILS list is empty.")
        return None

    language = shop_config.get("notifications", "notifications_settings.providers_settings.emails.language", "en")
    return EmailAdminProvider(
        target_emails=admin_emails,
        from_email=os.getenv("EMAIL_HOST_USER", "noreply@shop.com"),
        language=language,
    )


def _get_webhook_admin_provider() -> WebhookAdminProvider | None:
    """Internal helper to safely initialize the Webhook Admin Provider."""
    webhook_url = shop_config.get("notifications", "webhook.admin_webhook_url", "")
    if not webhook_url:
        logger.debug("Webhook provider skipped: ADMIN_WEBHOOK_URL is not set.")
        return None

    return WebhookAdminProvider(webhook_url=webhook_url, secret_token=os.getenv("ADMIN_WEBHOOK_SECRET"))


def get_order_alert_providers() -> Sequence[OrderAlertProvider]:
    """Factory for providers handling order payment alerts."""
    providers: list[OrderAlertProvider] = []
    available = shop_config.get("notifications", f"notifications_settings.{TypeAdminNotification.ORDER_PAID}", [])

    if "telegram" in available:
        if tg_prov := _get_telegram_admin_provider("order_paid_thread_id", 1):
            providers.append(tg_prov)
    if "emails" in available:
        if email_prov := _get_email_admin_provider():
            providers.append(email_prov)
    if "webhook" in available:
        if wh_prov := _get_webhook_admin_provider():
            providers.append(wh_prov)

    return providers


def get_transaction_alert_providers() -> Sequence[TransactionAlertProvider]:
    """Factory for providers handling transaction failure alerts."""
    providers: list[TransactionAlertProvider] = []
    available = shop_config.get(
        "notifications", f"notifications_settings.{TypeAdminNotification.TRANSACTION_FAILED}", []
    )

    if "telegram" in available:
        if tg_prov := _get_telegram_admin_provider("transaction_failed_thread_id", 2):
            providers.append(tg_prov)
    if "emails" in available:
        if email_prov := _get_email_admin_provider():
            providers.append(email_prov)
    if "webhook" in available:
        if wh_prov := _get_webhook_admin_provider():
            providers.append(wh_prov)

    return providers


def get_support_alert_providers() -> Sequence[SupportAlertProvider]:
    """
    Factory for providers handling support alerts.
    Only returns providers that implement the SupportAlertProvider protocol (e.g., Telegram).
    """
    providers: list[SupportAlertProvider] = []
    available = shop_config.get("notifications", f"notifications_settings.{TypeAdminNotification.SUPPORT}", [])

    if "telegram" in available:
        if tg_prov := _get_telegram_admin_provider("support_thread_id", 3):
            providers.append(tg_prov)

    return providers


def get_system_alert_providers() -> Sequence[SystemAlertProvider]:
    """Factory for providers handling system alerts."""
    providers: list[SystemAlertProvider] = []
    available = shop_config.get("notifications", f"notifications_settings.{TypeAdminNotification.SYSTEM}", [])

    if "telegram" in available:
        if tg_prov := _get_telegram_admin_provider("system_thread_id", 4):
            providers.append(tg_prov)
    if "emails" in available:
        if email_prov := _get_email_admin_provider():
            providers.append(email_prov)
    if "webhook" in available:
        if wh_prov := _get_webhook_admin_provider():
            providers.append(wh_prov)

    return providers


def get_active_user_providers() -> Sequence[UserNotificationProvider]:
    """Factory function for user notification providers."""
    providers: list[UserNotificationProvider] = []

    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    if bot_token:
        bot_client = TelegramBotClient(token=bot_token)
        telegram_usecase = SendTelegramMessageCase(client=bot_client)
        providers.append(TelegramUserProvider(telegram_usecase=telegram_usecase))

    return providers
