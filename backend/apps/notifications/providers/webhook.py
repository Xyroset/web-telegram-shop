import hashlib
import hmac
import json
import logging
from collections.abc import Sequence
from typing import Any

import requests

from apps.core.config_manager import shop_config
from apps.core.utils import get_base_url
from apps.notifications.domain.exceptions import NotificationWebhookError
from apps.notifications.domain.interfaces import (
    OrderItemSnapshotData,
    OrderSnapshotData,
    TransactionSnapshotData,
)

logger = logging.getLogger(__name__)


class WebhookAdminProvider:
    """
    Dispatches alerts (orders, transactions, system) to external systems via HTTP Webhooks.
    Does NOT implement SupportAlertProvider.

    **Business Rules:**
    - Serializes domain data into a structured JSON payload.
    - Generates an HMAC-SHA256 signature for payload verification if a secret token is configured.
    - Delegates the HTTP POST request via a persistent requests Session.

    **Required:**
    - Request failures (timeout, connection error, 4xx/5xx) must be caught, logged,
      and re-raised as NotificationWebhookError.
    """

    def __init__(self, webhook_url: str, secret_token: str | None = None, timeout: float = 5.0) -> None:
        self._webhook_url = webhook_url
        self._secret_token = secret_token
        self._timeout = timeout
        self._session = requests.Session()

    def _generate_signature(self, payload_bytes: bytes) -> str:
        if not self._secret_token:
            return ""
        return hmac.new(self._secret_token.encode("utf-8"), payload_bytes, hashlib.sha256).hexdigest()

    def send_order_paid_alert(
        self, order_data: OrderSnapshotData, physical_items: Sequence[OrderItemSnapshotData]
    ) -> None:
        delivery_dict = order_data.delivery.delivery_data or {}
        address = delivery_dict.get("address_line", "Not provided")
        zone = delivery_dict.get("destination_code", "Unknown")
        region = delivery_dict.get("region_code", "Unknown")
        user_email = delivery_dict.get("email", "Unknown")
        user_phone = delivery_dict.get("phone", "Unknown")
        zip_code = delivery_dict.get("zip_code", "Unknown")
        full_name = delivery_dict.get("full_name", "Unknown")

        zone_name = shop_config.get("locales", f"en.zone_names.{zone}")
        if isinstance(zone_name, dict):
            zone_name = zone_name.get("default")
        region_name = shop_config.get("locales", f"en.zone_names.{zone}.{region}")

        payload: dict[str, Any] = {
            "event": "order.paid",
            "data": {
                "id": str(order_data.id),
                "amount_usd": str(order_data.amount_usd),
                "state": order_data.state,
                "user_id": order_data.user.tg_id,
                "full_name": full_name,
                "username": getattr(order_data.user, "tg_username", "unknown"),
                "user_email": user_email,
                "user_phone": user_phone,
                "delivery": {
                    "provider_code": order_data.delivery.provider_code,
                    "cost": str(order_data.delivery.cost),
                    "destination_code": f"{str(zone).upper()} ({zone_name})",
                    "region_code": f"{str(region).upper()} ({region_name})",
                    "zip_code": zip_code,
                    "address": address,
                },
            },
            "admin_url": f"{get_base_url(name='backend')}/admin/orders/order/{order_data.id}",
        }

        payload_bytes = json.dumps(payload).encode("utf-8")
        headers = {"Content-Type": "application/json", "User-Agent": "Telegram-Shop-Webhook-Engine/1.0"}

        if self._secret_token:
            headers["X-Shop-Signature"] = self._generate_signature(payload_bytes)

        try:
            response = self._session.post(
                url=self._webhook_url, data=payload_bytes, headers=headers, timeout=self._timeout
            )
            response.raise_for_status()
            logger.info(f"Webhook alert successfully sent for order {order_data.id}. URL - {self._webhook_url}")

        except requests.RequestException as e:
            logger.error(
                f"Failed to send Webhook message for order id and URL: Order id - {order_data.id}"
                f", URL - {self._webhook_url}. Error: {str(e)}"
            )
            raise NotificationWebhookError(
                f"Failed to send Webhook message for order id and URL: Order id - {order_data.id}"
                f", URL - {self._webhook_url}. Error: {str(e)}"
            ) from e

    def send_transaction_failed_alert(self, transaction_data: TransactionSnapshotData) -> None:
        delivery_dict = transaction_data.order.delivery.delivery_data or {}
        user_email = delivery_dict.get("email", "Unknown")
        user_phone = delivery_dict.get("phone", "Unknown")
        full_name = delivery_dict.get("full_name", "Unknown")

        payload: dict[str, Any] = {
            "event": "transaction.failed",
            "data": {
                "id": str(transaction_data.id),
                "order": {
                    "id": str(transaction_data.order.id),
                    "amount_usd": str(transaction_data.order.amount_usd),
                    "state": transaction_data.order.state,
                    "user_id": transaction_data.order.user.tg_id,
                    "full_name": full_name,
                    "username": getattr(transaction_data.order.user, "tg_username", "unknown"),
                    "user_email": user_email,
                    "user_phone": user_phone,
                },
                "transaction": {
                    "invoice_id": transaction_data.invoice_id,
                    "payment_currency": transaction_data.payment_currency,
                    "network": transaction_data.network,
                    "target_amount_usd": str(transaction_data.target_amount_usd),
                    "amount_crypto": str(transaction_data.amount_crypto),
                    "current_amount_crypto": str(transaction_data.current_amount_crypto),
                    "captured_amount_usd": str(transaction_data.captured_amount_usd),
                    "receiver_address": transaction_data.receiver_address,
                    "sender_address": transaction_data.sender_address,
                    "tx_hash": transaction_data.tx_hash,
                    "state": transaction_data.state,
                    "raw_response": transaction_data.raw_response,
                },
            },
            "admin_url": f"{get_base_url(name='backend')}/admin/payments/paymenttransaction/{transaction_data.id}",
        }

        payload_bytes = json.dumps(payload).encode("utf-8")
        headers = {"Content-Type": "application/json", "User-Agent": "Telegram-Shop-Webhook-Engine/1.0"}

        if self._secret_token:
            headers["X-Shop-Signature"] = self._generate_signature(payload_bytes)

        try:
            response = self._session.post(
                url=self._webhook_url, data=payload_bytes, headers=headers, timeout=self._timeout
            )
            response.raise_for_status()
            logger.info(
                f"Webhook alert successfully sent for transaction {transaction_data.id}. URL - {self._webhook_url}"
            )

        except requests.RequestException as e:
            logger.error(
                f"Failed to send Webhook message for transaction id and URL: Transaction id - {transaction_data.id}"
                f", URL - {self._webhook_url}. Error: {str(e)}"
            )
            raise NotificationWebhookError(
                f"Failed to send Webhook message for transaction id and URL: Transaction id - {transaction_data.id}"
                f", URL - {self._webhook_url}. Error: {str(e)}"
            ) from e

    def send_system_alert(self, source: str, error_message: str, level: str = "ERROR") -> None:
        payload: dict[str, Any] = {
            "event": "system.alert",
            "data": {
                "source": source,
                "level": level.upper(),
                "error_message": error_message,
            },
            "admin_url": f"{get_base_url(name='backend')}/admin/",
        }

        payload_bytes = json.dumps(payload).encode("utf-8")
        headers = {"Content-Type": "application/json", "User-Agent": "Telegram-Shop-Webhook-Engine/1.0"}

        if self._secret_token:
            headers["X-Shop-Signature"] = self._generate_signature(payload_bytes)

        try:
            response = self._session.post(
                url=self._webhook_url, data=payload_bytes, headers=headers, timeout=self._timeout
            )
            response.raise_for_status()
            logger.info(f"System alert successfully sent via Webhook from source: {source}.")

        except requests.RequestException as e:
            logger.error(f"Failed to send system alert via Webhook. Error: {e}")
            raise NotificationWebhookError(f"Failed to send system alert via Webhook. Error: {e}") from e
