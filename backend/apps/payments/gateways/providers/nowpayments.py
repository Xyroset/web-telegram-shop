import hashlib
import hmac
import json
import logging
from collections.abc import Mapping
from decimal import Decimal
from typing import Any

import requests

from apps.core.config_manager import shop_config
from apps.core.utils import get_base_url
from apps.payments.domain.dto import InvoiceDTO
from apps.payments.domain.exceptions import (
    PaymentGatewayBadRequestError,
    PaymentGatewayNotFoundError,
    PaymentGatewayUnavailableError,
)
from apps.payments.domain.interfaces import PaymentGatewayProtocol

logger = logging.getLogger(__name__)


class NOWPaymentsGateway(PaymentGatewayProtocol):
    """
    The Gateway for the NOWPayments provider. Satisfies PaymentGatewayProtocol.

    **Business Rules:**
    - Creates crypto invoices using the NOWPayments REST API.
    - Constructs the appropriate NOWPayments ticker (e.g., 'usdttrc20' or 'btc').
    - Verifies incoming webhook signatures using HMAC-SHA512.

    **Required:**
    - The `api_key` must be provided during initialization. Otherwise error — **PaymentGatewayNotFoundError**.
    - If the API returns a 400 status, raises **PaymentGatewayBadRequestError**.
    - For all other API or network errors, raises **PaymentGatewayUnavailableError**.
    """

    def __init__(self, api_key: str, ipn_secret: str, base_url: str) -> None:
        self._api_key = api_key
        self._ipn_secret = ipn_secret
        self._base_url = base_url

        if not self._api_key:
            raise PaymentGatewayNotFoundError("API key is missing")

        self._headers = {"x-api-key": self._api_key, "Content-Type": "application/json"}

    def _format_ticker(self, currency: str, network: str) -> str:
        if network.lower() == "internal":
            return currency.lower()
        return f"{currency.lower()}{network.lower()}"

    def create_invoice(self, amount: Decimal, currency: str, network: str, order_id: str) -> InvoiceDTO:
        url = f"{self._base_url}/invoice"
        pay_currency = self._format_ticker(currency=currency, network=network)
        domain = get_base_url(name="backend")
        ipn_url = f"{domain}/api/v1/payments/nowpayments/"

        payload = {
            "price_amount": float(amount),
            "price_currency": "usd",
            "pay_currency": pay_currency,
            "order_id": str(order_id),
            "order_description": f"Order #{order_id}",
            "ipn_callback_url": ipn_url,
            "is_fee_paid_by_user": shop_config.get(
                "payments", "payments_settings.providers.nowpayments.supports_native_fee_delegation", True
            ),
        }

        try:
            response = requests.post(url, json=payload, headers=self._headers, timeout=10)
            response.raise_for_status()
            data = response.json()

            return InvoiceDTO(
                invoice_id=str(data.get("id")),
                pay_url=data.get("invoice_url"),
                currency=data.get("pay_currency", currency),
            )

        except requests.RequestException as ex:
            error_details = "No response body"
            if ex.response is not None:
                try:
                    error_details = ex.response.json()
                except ValueError:
                    error_details = ex.response.text

            logger.error(f"NOWPayments API error for order {order_id}: {error_details}")

            if ex.response is not None and ex.response.status_code == 400:
                raise PaymentGatewayBadRequestError() from ex

            raise PaymentGatewayUnavailableError() from ex

    def verify_webhook(self, payload: Mapping[str, Any], signature: str) -> bool:
        if not self._ipn_secret or not signature:
            return False

        sorted_payload = json.dumps(payload, separators=(",", ":"), sort_keys=True)

        expected_sig = hmac.new(
            self._ipn_secret.encode("utf-8"), sorted_payload.encode("utf-8"), hashlib.sha512
        ).hexdigest()

        return hmac.compare_digest(expected_sig, signature)

    def normalize_webhook_data(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        return {
            "invoice_id": str(payload.get("invoice_id", "")),
            "payment_status": str(payload.get("payment_status", "")).lower(),
            "actually_paid": str(payload.get("actually_paid", "0.0")),
            "pay_amount": str(payload.get("pay_amount", "0.0")),
            "pay_address": str(payload.get("pay_address", "")),
            "sender_address": str(payload.get("sender_address", "")),
            "payin_hash": str(payload.get("payin_hash", "")),
        }

    def __str__(self) -> str:
        return "nowpayments"
