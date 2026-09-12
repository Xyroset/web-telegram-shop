import hashlib
import hmac
import json
import logging
from collections.abc import Mapping
from decimal import Decimal
from typing import Any

import requests

from apps.core.config_manager import shop_config
from apps.payments.domain.dto import InvoiceDTO
from apps.payments.domain.exceptions import (
    PaymentGatewayBadRequestError,
    PaymentGatewayNotFoundError,
    PaymentGatewayUnavailableError,
)
from apps.payments.domain.interfaces import PaymentGatewayProtocol

logger = logging.getLogger(__name__)


class CryptoBotGateway(PaymentGatewayProtocol):
    """
    Gateway for CryptoBot (Crypto Pay) payment provider. Satisfies PaymentGatewayProtocol.

    **Business Rules:**
    - Creates crypto invoices with fiat USD base amount via Crypto Pay API.
    - Configures invoice expiration time based on shop configuration.
    - Verifies webhook signatures using SHA256 HMAC of the API token and request body.
    - Normalizes webhook payload structures to the unified gateway contract.

    **Required:**
    - The `api_token` must be provided during initialization. Otherwise raises **PaymentGatewayNotFoundError**.
    - If the API returns a 400 status, raises **PaymentGatewayBadRequestError**.
    - For all other API failures or malformed responses, raises **PaymentGatewayUnavailableError**.
    """

    def __init__(self, api_token: str, base_url: str) -> None:
        self._api_token = api_token
        self._base_url = base_url

        if not self._api_token:
            raise PaymentGatewayNotFoundError("Crypto Pay API token is missing")

        self._headers = {"Crypto-Pay-API-Token": self._api_token, "Content-Type": "application/json"}

    def create_invoice(self, amount: Decimal, currency: str, network: str, order_id: str) -> InvoiceDTO:
        url = f"{self._base_url}/createInvoice"
        asset = currency.upper()
        lifetime_mins = int(shop_config.get("payments", "payments_settings.default_payment_lifetime_minutes", 20))

        payload = {
            "currency_type": "fiat",
            "fiat": "USD",
            "amount": str(amount),
            "accepted_assets": asset,
            "description": f"Order #{order_id}",
            "payload": str(order_id),
            "expires_in": lifetime_mins * 60,
        }

        try:
            response = requests.post(url, json=payload, headers=self._headers, timeout=10)
            response.raise_for_status()
            data = response.json()

            if not data.get("ok"):
                logger.error(f"CryptoBot API returned not ok for order {order_id}: {data}")
                raise PaymentGatewayUnavailableError()

            result = data.get("result", {})

            return InvoiceDTO(
                invoice_id=str(result.get("invoice_id")),
                pay_url=result.get("pay_url"),
                currency=asset,
            )

        except requests.RequestException as ex:
            error_details = "No response body"
            if ex.response is not None:
                try:
                    error_details = ex.response.json()
                except ValueError:
                    error_details = ex.response.text

            logger.error(f"CryptoBot API error for order {order_id}: {error_details}")

            if ex.response is not None and ex.response.status_code == 400:
                raise PaymentGatewayBadRequestError() from ex

            raise PaymentGatewayUnavailableError() from ex

    def verify_webhook(self, payload: Mapping[str, Any], signature: str) -> bool:
        if not self._api_token or not signature:
            return False

        secret = hashlib.sha256(self._api_token.encode("utf-8")).digest()
        body = json.dumps(payload, separators=(",", ":"))
        expected_sig = hmac.new(secret, body.encode("utf-8"), hashlib.sha256).hexdigest()

        return hmac.compare_digest(expected_sig, signature)

    def normalize_webhook_data(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        update_type = payload.get("update_type")
        invoice_data: Mapping[str, Any] = payload.get("payload") or {}

        status_mapping = {"paid": "finished", "expired": "expired"}
        raw_status = "paid" if update_type == "invoice_paid" else str(invoice_data.get("status", ""))

        return {
            "invoice_id": str(invoice_data.get("invoice_id", "")),
            "payment_status": status_mapping.get(raw_status, raw_status),
            "actually_paid": str(invoice_data.get("paid_amount", "0.0")),
            "pay_amount": str(invoice_data.get("paid_amount", "0.0")),
            "pay_address": "CryptoBot Internal",
            "sender_address": "CryptoBot User",
            "payin_hash": str(invoice_data.get("hash", "")),
        }

    def __str__(self) -> str:
        return "cryptobot"
