import hashlib
import hmac
import json
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest
import requests

from apps.payments.domain.exceptions import (
    PaymentGatewayBadRequestError,
    PaymentGatewayUnavailableError,
)
from apps.payments.gateways.providers import NOWPaymentsGateway


class TestNOWPaymentsGateway:
    """
    Verify behavior, HTTP request formatting, and webhook validation
    for the NOWPayments provider.
    """

    @patch("apps.payments.gateways.providers.nowpayments.requests.post")
    @patch("apps.payments.gateways.providers.nowpayments.shop_config.get")
    def test_create_invoice_success(self, mock_shop_config_get: MagicMock, mock_post: MagicMock) -> None:
        """
        Happy path: Successfully create an invoice via NOWPayments API.
        """
        mock_shop_config_get.return_value = True

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "id": "555123",
            "invoice_url": "https://nowpayments.io/payment/555123",
            "pay_currency": "usdttrc20",
        }
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        gateway = NOWPaymentsGateway(
            api_key="fake_api_key", ipn_secret="fake_secret", base_url="https://api.nowpayments.io/v1"
        )

        result = gateway.create_invoice(amount=Decimal("150.00"), currency="USDT", network="TRC20", order_id="ord_123")

        assert result.invoice_id == "555123"
        assert result.pay_url == "https://nowpayments.io/payment/555123"
        assert result.currency == "usdttrc20"
        mock_post.assert_called_once()

        called_kwargs = mock_post.call_args.kwargs
        assert called_kwargs["json"]["price_amount"] == 150.0
        assert called_kwargs["json"]["pay_currency"] == "usdttrc20"
        assert called_kwargs["json"]["order_id"] == "ord_123"

    @patch("apps.payments.gateways.providers.nowpayments.requests.post")
    @patch("apps.payments.gateways.providers.nowpayments.shop_config.get")
    def test_create_invoice_raises_bad_request_on_400(
        self, mock_shop_config_get: MagicMock, mock_post: MagicMock
    ) -> None:
        """
        Failure: Gateway returns 400 Bad Request. Should raise PaymentGatewayBadRequestError.
        """
        mock_shop_config_get.return_value = True

        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.json.return_value = {"message": "Invalid currency"}

        ex = requests.RequestException()
        ex.response = mock_response
        mock_post.side_effect = ex

        gateway = NOWPaymentsGateway(
            api_key="fake_api_key", ipn_secret="fake_secret", base_url="https://api.nowpayments.io/v1"
        )

        with pytest.raises(PaymentGatewayBadRequestError):
            gateway.create_invoice(amount=Decimal("150.00"), currency="UNKNOWN", network="TRC20", order_id="ord_123")

    @patch("apps.payments.gateways.providers.nowpayments.requests.post")
    @patch("apps.payments.gateways.providers.nowpayments.shop_config.get")
    def test_create_invoice_raises_unavailable_on_timeout(
        self, mock_shop_config_get: MagicMock, mock_post: MagicMock
    ) -> None:
        """
        Failure: Network timeout or 500 error raises PaymentGatewayUnavailableError.
        """
        mock_shop_config_get.return_value = True
        mock_post.side_effect = requests.Timeout()

        gateway = NOWPaymentsGateway(
            api_key="fake_api_key", ipn_secret="fake_secret", base_url="https://api.nowpayments.io/v1"
        )

        with pytest.raises(PaymentGatewayUnavailableError):
            gateway.create_invoice(amount=Decimal("150.00"), currency="USDT", network="TRC20", order_id="ord_123")

    def test_verify_webhook_success(self) -> None:
        """
        Happy path: Webhook signature is correctly validated using HMAC-SHA512.
        """
        secret = "my_super_secret"
        payload = {"invoice_id": "123", "payment_status": "finished"}

        sorted_payload = json.dumps(payload, separators=(",", ":"), sort_keys=True)
        valid_signature = hmac.new(secret.encode("utf-8"), sorted_payload.encode("utf-8"), hashlib.sha512).hexdigest()

        gateway = NOWPaymentsGateway(
            api_key="fake_api_key", ipn_secret=secret, base_url="https://api.nowpayments.io/v1"
        )

        is_valid = gateway.verify_webhook(payload=payload, signature=valid_signature)

        assert is_valid is True

    def test_verify_webhook_fails_with_invalid_signature(self) -> None:
        """
        Failure: Webhook signature does not match expected HMAC.
        """
        gateway = NOWPaymentsGateway(
            api_key="fake_api_key", ipn_secret="my_super_secret", base_url="https://api.nowpayments.io/v1"
        )
        payload = {"invoice_id": "123"}

        is_valid = gateway.verify_webhook(payload=payload, signature="invalid_hash_string")

        assert is_valid is False

    def test_normalize_webhook_data(self) -> None:
        """
        Happy path: Webhook payload is normalized to the standard Gateway contract.
        """
        gateway = NOWPaymentsGateway(api_key="fake_api_key", ipn_secret="sec", base_url="https://api.nowpayments.io/v1")
        raw_payload = {
            "invoice_id": 999111,
            "payment_status": "FINISHED",
            "actually_paid": 150.5,
            "pay_address": "0xABC",
        }

        normalized = gateway.normalize_webhook_data(payload=raw_payload)

        assert normalized["invoice_id"] == "999111"
        assert normalized["payment_status"] == "finished"
        assert normalized["actually_paid"] == "150.5"
        assert normalized["pay_address"] == "0xABC"
        assert normalized["payin_hash"] == ""
