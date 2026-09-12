import logging
from collections.abc import Sequence
from typing import Any

from django.core.mail import send_mail

from apps.core.config_manager import shop_config
from apps.core.utils import get_base_url
from apps.notifications.domain.exceptions import NotificationEmailError
from apps.notifications.domain.interfaces import (
    OrderItemSnapshotData,
    OrderSnapshotData,
    TransactionSnapshotData,
)

logger = logging.getLogger(__name__)


class EmailAdminProvider:
    """
    Dispatches targeted alerts (orders, transactions, system) to administrators via Email.
    Does NOT implement SupportAlertProvider.

    **Business Rules:**
    - Gathers a unified context dictionary from snapshot data.
    - Fetches the message and subject templates from the dynamic configuration.
    - Formats the templates and delegates dispatch to Django's native `send_mail` utility.

    **Required:**
    - If `send_mail` raises any exception, it must be caught, logged, and re-raised as NotificationEmailError.
    """

    def __init__(self, target_emails: list[str], from_email: str, language: str = "en") -> None:
        self._target_emails = target_emails
        self._from_email = from_email
        self._language = language

    def _safe_format(self, template: str, context: dict[str, Any]) -> str:
        try:
            return template.format(**context)
        except KeyError as e:
            logger.warning(f"Missing template key {e} in email notification config. Using raw template.")
            return template

    def send_order_paid_alert(
        self, order_data: OrderSnapshotData, physical_items: Sequence[OrderItemSnapshotData]
    ) -> None:
        delivery_dict = order_data.delivery.delivery_data or {}

        zone = delivery_dict.get("destination_code", "Unknown")
        region = delivery_dict.get("region_code", "Unknown")

        zone_name = shop_config.get("locales", f"{self._language}.zone_names.{zone}")
        if isinstance(zone_name, dict):
            zone_name = zone_name.get("default", zone)
        region_name = shop_config.get("locales", f"{self._language}.zone_names.{zone}.{region}", region)

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
            "admin_url": f"{get_base_url(name='backend')}/admin/orders/order/{order_data.id}",
        }

        subject_template = shop_config.get(
            "locales", f"{self._language}.admin_notifications.emails.order_paid_subject", "New Order Paid: #{order_id}"
        )

        message_template = shop_config.get(
            "locales",
            f"{self._language}.email_notifications.order_paid_message",
            "Order {order_id} Paid. Check Admin Panel: {admin_url}",
        )

        subject = self._safe_format(str(subject_template), context)
        message = self._safe_format(str(message_template), context)

        try:
            send_mail(
                subject=subject,
                message=message,
                from_email=self._from_email,
                recipient_list=self._target_emails,
                fail_silently=False,
            )
            logger.info(f"Email alert successfully sent for order {order_data.id}.")
        except Exception as e:
            logger.error(f"Failed to send Email message for order id: {order_data.id}. Error: {e}")
            raise NotificationEmailError(
                f"Failed to send Email message for order id: {order_data.id}. Error: {e}"
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

        subject_template = shop_config.get(
            "locales",
            f"{self._language}.admin_notifications.emails.transaction_failed_subject",
            "Failed transaction: #{tx_id}",
        )

        message_template = shop_config.get(
            "locales",
            f"{self._language}.admin_notifications.emails.transaction_failed_message",
            "Transaction {tx_id} Failed! Order: {order_id}. Admin Panel: {admin_url}",
        )

        subject = self._safe_format(str(subject_template), context)
        message = self._safe_format(str(message_template), context)

        try:
            send_mail(
                subject=subject,
                message=message,
                from_email=self._from_email,
                recipient_list=self._target_emails,
                fail_silently=False,
            )
            logger.info(f"Email alert successfully sent for transaction {transaction_data.id}.")
        except Exception as e:
            logger.error(f"Failed to send Email message for transaction id: {transaction_data.id}. Error: {e}")
            raise NotificationEmailError(
                f"Failed to send Email message for transaction id: {transaction_data.id}. Error: {e}"
            ) from e

    def send_system_alert(self, source: str, error_message: str, level: str = "ERROR") -> None:
        context: dict[str, Any] = {
            "source": source,
            "level": level.upper(),
            "error_message": error_message,
        }

        subject_template = shop_config.get(
            "locales",
            f"{self._language}.admin_notifications.emails.system_subject",
            "SYSTEM ALERT [{level}]: {source}",
        )

        message_template = shop_config.get(
            "locales",
            f"{self._language}.admin_notifications.emails.system_message",
            "SYSTEM ALERT: {level}\nSource: {source}\nError: {error_message}",
        )

        subject = self._safe_format(str(subject_template), context)
        message = self._safe_format(str(message_template), context)

        try:
            send_mail(
                subject=subject,
                message=message,
                from_email=self._from_email,
                recipient_list=self._target_emails,
                fail_silently=False,
            )
            logger.info(f"System alert successfully sent via Email from source: {source}.")
        except Exception as e:
            logger.error(f"Failed to send system alert via Email. Error: {e}")
            raise NotificationEmailError(f"Failed to send system alert via Email. Error: {e}") from e
