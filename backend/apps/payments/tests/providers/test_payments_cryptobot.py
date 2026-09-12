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
from apps.payments.gateways.providers import CryptoBotGateway


class TestCryptoBotGateway:
    """
    Verify behavior, HTTP request formatting, and webhook validation
    for the CryptoBot (Crypto Pay) provider.
    """

    @patch("apps.payments.gateways.providers.cryptobot.requests.post")
    @patch("apps.payments.gateways.providers.cryptobot.shop_config.get")
    def test_create_invoice_success(self, mock_shop_config_get: MagicMock, mock_post: MagicMock) -> None:
        """
        Happy path: Successfully create an invoice via Crypto Pay API.
        """
        mock_shop_config_get.return_value = 20

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "ok": True,
            "result": {
                "invoice_id": 123456,
                "pay_url": "https://t.me/CryptoBot?start=inv123",
            },
        }
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        gateway = CryptoBotGateway(api_token="fake_token", base_url="https://pay.crypt.bot/api")

        result = gateway.create_invoice(amount=Decimal("50.00"), currency="USDT", network="TRC20", order_id="ord_777")

        assert result.invoice_id == "123456"
        assert result.pay_url == "https://t.me/CryptoBot?start=inv123"
        assert result.currency == "USDT"
        mock_post.assert_called_once()

        called_kwargs = mock_post.call_args.kwargs
        assert called_kwargs["json"]["amount"] == "50.00"
        assert called_kwargs["json"]["accepted_assets"] == "USDT"
        assert called_kwargs["json"]["payload"] == "ord_777"

    @patch("apps.payments.gateways.providers.cryptobot.requests.post")
    @patch("apps.payments.gateways.providers.cryptobot.shop_config.get")
    def test_create_invoice_raises_unavailable_when_ok_is_false(
        self, mock_shop_config_get: MagicMock, mock_post: MagicMock
    ) -> None:
        """
        Failure: API returns HTTP 200, but JSON contains 'ok': False.
        """
        mock_shop_config_get.return_value = 20

        mock_response = MagicMock()
        mock_response.json.return_value = {"ok": False, "error": "Something went wrong"}
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        gateway = CryptoBotGateway(api_token="fake_token", base_url="https://pay.crypt.bot/api")

        with pytest.raises(PaymentGatewayUnavailableError):
            gateway.create_invoice(amount=Decimal("50.00"), currency="USDT", network="TRC20", order_id="ord_777")

    @patch("apps.payments.gateways.providers.cryptobot.requests.post")
    @patch("apps.payments.gateways.providers.cryptobot.shop_config.get")
    def test_create_invoice_raises_bad_request_on_400(
        self, mock_shop_config_get: MagicMock, mock_post: MagicMock
    ) -> None:
        """
        Failure: Gateway returns HTTP 400 Bad Request.
        """
        mock_shop_config_get.return_value = 20

        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.json.return_value = {"error": "BAD_REQUEST"}

        ex = requests.RequestException()
        ex.response = mock_response
        mock_post.side_effect = ex

        gateway = CryptoBotGateway(api_token="fake_token", base_url="https://pay.crypt.bot/api")

        with pytest.raises(PaymentGatewayBadRequestError):
            gateway.create_invoice(amount=Decimal("50.00"), currency="USDT", network="TRC20", order_id="ord_777")

    def test_verify_webhook_success(self) -> None:
        """
        Happy path: Webhook signature matches SHA256 HMAC of API token.
        """
        token = "my_crypto_token"
        payload = {"update_type": "invoice_paid", "payload": {"invoice_id": 123}}

        secret = hashlib.sha256(token.encode("utf-8")).digest()
        body = json.dumps(payload, separators=(",", ":"))
        valid_signature = hmac.new(secret, body.encode("utf-8"), hashlib.sha256).hexdigest()

        gateway = CryptoBotGateway(api_token=token, base_url="https://pay.crypt.bot/api")

        is_valid = gateway.verify_webhook(payload=payload, signature=valid_signature)

        assert is_valid is True

    def test_verify_webhook_fails_with_invalid_signature(self) -> None:
        """
        Failure: Webhook signature does not match.
        """
        gateway = CryptoBotGateway(api_token="fake_token", base_url="https://pay.crypt.bot/api")
        payload = {"update_type": "invoice_paid"}

        is_valid = gateway.verify_webhook(payload=payload, signature="bad_signature")

        assert is_valid is False

    def test_normalize_webhook_data_invoice_paid(self) -> None:
        """
        Happy path: 'invoice_paid' event is mapped to 'finished' status.
        """
        gateway = CryptoBotGateway(api_token="fake_token", base_url="https://pay.crypt.bot/api")
        raw_payload = {
            "update_type": "invoice_paid",
            "payload": {
                "invoice_id": 777,
                "status": "paid",
                "paid_amount": "50.00",
                "hash": "tx_abc123",
            },
        }

        normalized = gateway.normalize_webhook_data(payload=raw_payload)

        assert normalized["invoice_id"] == "777"
        assert normalized["payment_status"] == "finished"
        assert normalized["actually_paid"] == "50.00"
        assert normalized["payin_hash"] == "tx_abc123"
        assert normalized["pay_address"] == "CryptoBot Internal"
