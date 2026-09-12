import logging
from collections.abc import Sequence
from typing import Any

from apps.core.config_manager import shop_config
from apps.core.utils import get_base_url, safe_format
from apps.notifications.domain.exceptions import NotificationTelegramError
from apps.notifications.domain.interfaces import (
    OrderAlertProvider,
    OrderItemSnapshotData,
    OrderSnapshotData,
    SupportAlertProvider,
    SystemAlertProvider,
    TicketSnapshotData,
    TransactionAlertProvider,
    TransactionSnapshotData,
    UserNotificationProvider,
)
from apps.telegram.usecases import SendTelegramMessageCase

logger = logging.getLogger(__name__)


class TelegramAdminProvider(
    OrderAlertProvider,
    TransactionAlertProvider,
    SupportAlertProvider,
    SystemAlertProvider,
):
    """
    Dispatches admin alerts (orders, transactions, support, system) via Telegram.

    **Business Rules:**
    - Extracts context variables from snapshot interfaces.
    - Resolves localized templates using shop dynamic configuration.
    - Formats templates and executes dispatch via `SendTelegramMessageCase`.

    **Required:**
    - Must wrap all Telegram communication errors in `NotificationTelegramError`.
    """

    def __init__(
        self,
        chat_id: str | int,
        telegram_usecase: SendTelegramMessageCase,
        message_thread_id: int | None = None,
        language: str = "en",
    ) -> None:
        self._chat_id = chat_id
        self._telegram_usecase = telegram_usecase
        self._message_thread_id = message_thread_id
        self._language = language

    def send_order_paid_alert(
        self,
        order_data: OrderSnapshotData,
        physical_items: Sequence[OrderItemSnapshotData],
    ) -> None:
        delivery_dict = order_data.delivery.delivery_data or {}

        zone = str(delivery_dict.get("destination_code", "Unknown")).lower()
        region = str(delivery_dict.get("region_code", "Unknown")).lower()
        zone_name = shop_config.get("locales", f"{self._language}.zone_names.{zone}")
        if isinstance(zone_name, dict):
            zone_name = zone_name.get("default", zone)
        region_name = shop_config.get("locales", f"{self._language}.zone_names.{zone}.{region}", region)

        items_text = "\n".join(
            [
                f"- {item.variant.product.name}: <b>{item.variant.title} (x{item.quantity})</b>"
                for item in physical_items
            ]
        )
        if not items_text:
            items_text = "No physical items (Digital only or error)."

        context: dict[str, Any] = {
            "order_id": order_data.id,
            "tg_id": order_data.user.tg_id,
            "full_name": delivery_dict.get("full_name", "Unknown"),
            "tg_username": order_data.user.tg_username,
            "email": delivery_dict.get("email", "Unknown"),
            "phone": delivery_dict.get("phone", "Unknown"),
            "amount_usd": order_data.amount_usd,
            "order_state": order_data.state.upper(),
            "provider_code": order_data.delivery.provider_code,
            "delivery_cost": order_data.delivery.cost,
            "zone_upper": str(zone).upper(),
            "zone_name": zone_name,
            "region_upper": str(region).upper(),
            "region_name": region_name,
            "zip_code": str(delivery_dict.get("zip_code", "Unknown")),
            "address": delivery_dict.get("address_line", "Not provided"),
            "physical_items": items_text,
            "admin_url": f"{get_base_url(name='backend')}/admin/orders/order/{order_data.id}",
        }

        fallback_template = (
            "<b>Order {order_id} Paid</b>\n"
            "State: {order_state}\n\n"
            "<b>Items to pack:</b>\n"
            "{physical_items}\n\n"
            "Check Admin Panel."
        )

        template = shop_config.get(
            "locales",
            f"{self._language}.admin_notifications.telegram.order_paid_physical",
            fallback_template,
        )

        message = safe_format(str(template), context)

        try:
            self._telegram_usecase.execute(
                chat_id=self._chat_id,
                text=message,
                message_thread_id=self._message_thread_id,
            )
            logger.info(f"Telegram alert successfully sent for order {order_data.id}.")
        except Exception as e:
            logger.error(f"Failed to send Telegram message for order id: {order_data.id}. Error: {e}")
            raise NotificationTelegramError(
                f"Failed to send Telegram message for order id: {order_data.id}. Error: {e}"
            ) from e

    def send_transaction_failed_alert(self, transaction_data: TransactionSnapshotData) -> None:
        delivery_dict = transaction_data.order.delivery.delivery_data or {}

        context: dict[str, Any] = {
            "order_id": transaction_data.order.id,
            "tg_id": transaction_data.order.user.tg_id,
            "full_name": delivery_dict.get("full_name", "Unknown"),
            "tg_username": transaction_data.order.user.tg_username,
            "email": delivery_dict.get("email", "Unknown"),
            "phone": delivery_dict.get("phone", "Unknown"),
            "amount_usd": transaction_data.order.amount_usd,
            "order_state": transaction_data.order.state.upper(),
            "tx_id": transaction_data.id,
            "invoice_id": transaction_data.invoice_id,
            "currency": transaction_data.payment_currency,
            "network": transaction_data.network,
            "target_usd": transaction_data.target_amount_usd,
            "amount_crypto": transaction_data.amount_crypto,
            "current_crypto": transaction_data.current_amount_crypto,
            "captured_usd": transaction_data.captured_amount_usd,
            "receiver_address": transaction_data.receiver_address,
            "sender_address": transaction_data.sender_address,
            "tx_hash": transaction_data.tx_hash,
            "tx_state": transaction_data.state.upper(),
            "raw_response": transaction_data.raw_response,
            "admin_url": f"{get_base_url(name='backend')}/admin/payments/paymenttransaction/{transaction_data.id}",
        }

        template = shop_config.get(
            "locales",
            f"{self._language}.admin_notifications.telegram.transaction_failed",
            "Transaction {tx_id} Failed! Order: {order_id}. State: {tx_state}. Check Admin Panel.",
        )

        message = safe_format(str(template), context)

        try:
            self._telegram_usecase.execute(
                chat_id=self._chat_id,
                text=message,
                message_thread_id=self._message_thread_id,
            )
            logger.info(f"Telegram alert successfully sent for transaction {transaction_data.id}.")
        except Exception as e:
            logger.error(f"Failed to send Telegram message for transaction id: {transaction_data.id}. Error: {e}")
            raise NotificationTelegramError(
                f"Failed to send Telegram message for transaction id: {transaction_data.id}. Error: {e}"
            ) from e

    def send_support_alert(self, ticket_data: TicketSnapshotData) -> int:
        context: dict[str, Any] = {
            "ticket_id": ticket_data.id,
            "tg_id": ticket_data.user.tg_id,
            "tg_username": ticket_data.user.tg_username,
            "category": ticket_data.category.upper(),
            "state": ticket_data.state.upper(),
            "message": ticket_data.first_message.text,
            "admin_url": f"{get_base_url(name='backend')}/admin/support/ticket/{ticket_data.id}",
        }

        fallback_template = (
            "#Ticket_{ticket_id}\n\n"
            "<b>New Support Request ({state})</b>\n"
            "<b>User:</b> @{tg_username} (ID: <code>{tg_id}</code>)\n"
            "<b>Category:</b> {category}\n\n"
            "<i>{message}</i>\n\n"
            '<a href="{admin_url}">Admin panel</a>'
        )

        template = shop_config.get(
            "locales",
            f"{self._language}.admin_notifications.telegram.support",
            fallback_template,
        )
        buttons = shop_config.get(
            "locales",
            f"{self._language}.admin_notifications.telegram.buttons",
            {"accept": "Accept", "reject": "Reject"},
        )

        message = safe_format(str(template), context)

        reply_markup: dict[str, Any] = {
            "inline_keyboard": [
                [
                    {"text": f"✅ {buttons.get('accept')}", "callback_data": f"ticket_accept_{ticket_data.id}"},
                    {"text": f"❌ {buttons.get('reject')}", "callback_data": f"ticket_reject_{ticket_data.id}"},
                ]
            ]
        }

        try:
            msg_id = self._telegram_usecase.execute(
                chat_id=self._chat_id,
                text=message,
                message_thread_id=self._message_thread_id,
                reply_markup=reply_markup,
            )
            logger.info(f"Telegram alert successfully sent for support ticket {ticket_data.id}.")
            return msg_id
        except Exception as e:
            logger.error(f"Failed to send Telegram message for ticket id: {ticket_data.id}. Error: {e}")
            raise NotificationTelegramError(
                f"Failed to send Telegram message for ticket id: {ticket_data.id}. Error: {e}"
            ) from e

    def send_system_alert(self, source: str, error_message: str, level: str = "ERROR") -> None:
        context: dict[str, Any] = {
            "source": source,
            "level": level.upper(),
            "error_message": error_message,
        }

        fallback_template = "⚠️ <b>SYSTEM ALERT: {level}</b>\n<b>Source:</b> {source}\n\n<code>{error_message}</code>"

        template = shop_config.get(
            "locales",
            f"{self._language}.admin_notifications.telegram.system",
            fallback_template,
        )

        message = safe_format(str(template), context)

        try:
            self._telegram_usecase.execute(
                chat_id=self._chat_id,
                text=message,
                message_thread_id=self._message_thread_id,
            )
            logger.info(f"System alert successfully sent from source: {source}.")
        except Exception as e:
            logger.error(f"Failed to send system alert. Error: {e}")
            raise NotificationTelegramError(f"Failed to send system alert. Error: {e}") from e


class TelegramUserProvider(UserNotificationProvider):
    """
    Dispatches customer-facing notifications via Telegram.

    **Business Rules:**
    - Formats digital goods/keys directly for buyer delivery.
    - Sends message in the buyer's requested language.

    **Required:**
    - Must wrap all Telegram communication errors in `NotificationTelegramError`.
    """

    def __init__(self, telegram_usecase: SendTelegramMessageCase) -> None:
        self._telegram_usecase = telegram_usecase

    def send_digital_delivery(
        self,
        order_data: OrderSnapshotData,
        digital_items: Sequence[OrderItemSnapshotData],
        language: str,
    ) -> None:
        items_blocks = []
        for item in digital_items:
            keys_text = "\n".join([f"<code>{key}</code>" for key in item.digital_keys])
            items_blocks.append(
                f"📦 <b>{item.variant.product.name}: {item.variant.title} (x{item.quantity})</b>\n{keys_text}"
            )

        items_formatted = "\n\n".join(items_blocks)

        context: dict[str, Any] = {
            "order_id": order_data.id,
            "digital_items": items_formatted,
        }

        template = shop_config.get(
            "locales",
            f"{language}.user_notifications.telegram.order_paid_digital",
            "Here are your keys for order {order_id}:\n{digital_items}",
        )

        message = safe_format(str(template), context)

        try:
            self._telegram_usecase.execute(chat_id=order_data.user.tg_id, text=message)
            logger.info(
                f"Digital keys successfully delivered to user {order_data.user.tg_id} for order {order_data.id}."
            )
        except Exception as e:
            logger.error(f"Failed to deliver digital keys to user {order_data.user.tg_id}. Error: {e}")
            raise NotificationTelegramError(f"Failed to deliver keys. Error: {e}") from e
