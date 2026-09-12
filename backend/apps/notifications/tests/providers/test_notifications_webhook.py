import json
from decimal import Decimal
from unittest.mock import MagicMock

import pytest
import requests
from pytest_mock import MockerFixture

from apps.notifications.domain.exceptions import NotificationWebhookError
from apps.notifications.providers.webhook import WebhookAdminProvider


class TestWebhookAdminProvider:
    """
    Verify business rules for formatting, signing, and sending admin webhook alerts.
    """

    @staticmethod
    def _get_fake_order() -> MagicMock:
        """Helper to create a fully populated fake order to avoid JSON serialization errors."""
        fake_order = MagicMock()
        fake_order.id = "order-123"
        fake_order.amount_usd = Decimal("150.00")
        fake_order.state = "paid"
        fake_order.user.tg_id = 12345
        fake_order.user.tg_username = "test_user"
        fake_order.delivery.provider_code = "test"
        fake_order.delivery.cost = Decimal("5.00")
        fake_order.delivery.delivery_data = {
            "address_line": "123 Main St",
            "destination_code": "eu",
            "region_code": "kh",
            "full_name": "John Doe",
            "email": "user@test.com",
            "phone": "+1234567890",
            "zip_code": "12345",
        }
        return fake_order

    @staticmethod
    def _get_fake_transaction(order_mock: MagicMock) -> MagicMock:
        """Helper to create a fully populated fake transaction."""
        fake_tx = MagicMock()
        fake_tx.id = "txn-1"
        fake_tx.invoice_id = "invoice-1"
        fake_tx.payment_currency = "USDT"
        fake_tx.network = "TRC20"
        fake_tx.target_amount_usd = Decimal("100.00")
        fake_tx.amount_crypto = Decimal("99.50")
        fake_tx.current_amount_crypto = Decimal("98.25")
        fake_tx.captured_amount_usd = Decimal("97.00")
        fake_tx.receiver_address = "receiver-address"
        fake_tx.sender_address = "sender-address"
        fake_tx.tx_hash = "tx-hash-123"
        fake_tx.state = "failed"
        fake_tx.raw_response = {"status": "failed"}
        fake_tx.order = order_mock
        return fake_tx

    def test_send_order_alert_with_signature_success(
        self, mocker: MockerFixture, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """
        Happy path: Successfully format, sign, and send a Webhook alert.
        """
        mock_session_cls = mocker.patch("apps.notifications.providers.webhook.requests.Session")
        mock_session = mock_session_cls.return_value
        monkeypatch.setenv("BACKEND_VIRTUAL_HOST", "test.localhost")

        fake_order = self._get_fake_order()

        provider = WebhookAdminProvider(webhook_url="https://api.example.com/webhook", secret_token="test_secret")

        provider.send_order_paid_alert(order_data=fake_order, physical_items=[])

        mock_session.post.assert_called_once()
        call_kwargs = mock_session.post.call_args.kwargs

        assert call_kwargs["url"] == "https://api.example.com/webhook"
        assert "X-Shop-Signature" in call_kwargs["headers"]
        assert call_kwargs["headers"]["Content-Type"] == "application/json"

        sent_payload = json.loads(call_kwargs["data"].decode("utf-8"))
        assert sent_payload["event"] == "order.paid"
        assert sent_payload["data"]["id"] == "order-123"
        assert sent_payload["data"]["delivery"]["address"] == "123 Main St"
        assert "test.localhost" in sent_payload["admin_url"]

    def test_send_order_alert_no_secret_missing_data(self, mocker: MockerFixture) -> None:
        """
        Happy path (Edge Case): Handle missing delivery dictionaries safely, no signature.
        """
        mock_session_cls = mocker.patch("apps.notifications.providers.webhook.requests.Session")
        mock_session = mock_session_cls.return_value

        fake_order = self._get_fake_order()
        fake_order.delivery.delivery_data = None

        provider = WebhookAdminProvider(webhook_url="https://api.example.com/webhook", secret_token=None)

        provider.send_order_paid_alert(order_data=fake_order, physical_items=[])

        mock_session.post.assert_called_once()
        call_kwargs = mock_session.post.call_args.kwargs

        assert "X-Shop-Signature" not in call_kwargs["headers"]

        sent_payload = json.loads(call_kwargs["data"].decode("utf-8"))
        assert sent_payload["data"]["delivery"]["address"] == "Not provided"
        assert "UNKNOWN" in sent_payload["data"]["delivery"]["destination_code"].upper()

    def test_send_order_alert_failure(self, mocker: MockerFixture) -> None:
        """
        Failure: HTTP Request raises a requests exception.
        """
        mock_session_cls = mocker.patch("apps.notifications.providers.webhook.requests.Session")
        mock_session = mock_session_cls.return_value
        mock_session.post.side_effect = requests.RequestException("Connection Refused")

        fake_order = self._get_fake_order()

        provider = WebhookAdminProvider(webhook_url="https://api.example.com/webhook")

        with pytest.raises(NotificationWebhookError) as exc_info:
            provider.send_order_paid_alert(order_data=fake_order, physical_items=[])

        assert "Failed to send Webhook message for order id" in str(exc_info.value)
        assert "Connection Refused" in str(exc_info.value)

    def test_send_transaction_failed_alert_success(
        self, mocker: MockerFixture, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """
        Happy path: Successfully format and send a Webhook alert for a failed transaction.
        """
        mock_session_cls = mocker.patch("apps.notifications.providers.webhook.requests.Session")
        mock_session = mock_session_cls.return_value
        monkeypatch.setenv("BACKEND_VIRTUAL_HOST", "test.localhost")

        fake_order = self._get_fake_order()
        fake_order.delivery.delivery_data = {"email": "test@test.com", "phone": "123", "full_name": "Test User"}

        fake_tx = self._get_fake_transaction(order_mock=fake_order)

        provider = WebhookAdminProvider(webhook_url="https://api.example.com/webhook", secret_token="test_secret")

        provider.send_transaction_failed_alert(transaction_data=fake_tx)

        mock_session.post.assert_called_once()
        call_kwargs = mock_session.post.call_args.kwargs

        assert call_kwargs["url"] == "https://api.example.com/webhook"
        assert "X-Shop-Signature" in call_kwargs["headers"]

        sent_payload = json.loads(call_kwargs["data"].decode("utf-8"))
        assert sent_payload["event"] == "transaction.failed"
        assert sent_payload["data"]["id"] == "txn-1"
        assert sent_payload["data"]["order"]["id"] == "order-123"
        assert sent_payload["data"]["transaction"]["invoice_id"] == "invoice-1"
        assert sent_payload["data"]["transaction"]["tx_hash"] == "tx-hash-123"
        assert "test.localhost" in sent_payload["admin_url"]

    def test_send_transaction_failed_alert_failure(self, mocker: MockerFixture) -> None:
        """
        Failure: HTTP Request raises a requests exception during transaction alert.
        """
        mock_session_cls = mocker.patch("apps.notifications.providers.webhook.requests.Session")
        mock_session = mock_session_cls.return_value
        mock_session.post.side_effect = requests.RequestException("Timeout Error")

        fake_order = self._get_fake_order()
        fake_tx = self._get_fake_transaction(order_mock=fake_order)

        provider = WebhookAdminProvider(webhook_url="https://api.example.com/webhook")

        with pytest.raises(NotificationWebhookError) as exc_info:
            provider.send_transaction_failed_alert(transaction_data=fake_tx)

        assert "Failed to send Webhook message for transaction id" in str(exc_info.value)
        assert "Timeout Error" in str(exc_info.value)

    def test_send_system_alert_success(self, mocker: MockerFixture, monkeypatch: pytest.MonkeyPatch) -> None:
        """
        Happy path: Successfully format and send a Webhook alert for a system event.
        """
        mock_session_cls = mocker.patch("apps.notifications.providers.webhook.requests.Session")
        mock_session = mock_session_cls.return_value
        monkeypatch.setenv("BACKEND_VIRTUAL_HOST", "test.localhost")

        provider = WebhookAdminProvider(webhook_url="https://api.example.com/webhook", secret_token="test_secret")

        provider.send_system_alert(source="Celery", error_message="Task Failed", level="CRITICAL")

        mock_session.post.assert_called_once()
        call_kwargs = mock_session.post.call_args.kwargs

        sent_payload = json.loads(call_kwargs["data"].decode("utf-8"))
        assert sent_payload["event"] == "system.alert"
        assert sent_payload["data"]["source"] == "Celery"
        assert sent_payload["data"]["level"] == "CRITICAL"
        assert sent_payload["data"]["error_message"] == "Task Failed"

    def test_send_system_alert_failure(self, mocker: MockerFixture) -> None:
        """
        Failure: HTTP Request raises a requests exception during system alert.
        """
        mock_session_cls = mocker.patch("apps.notifications.providers.webhook.requests.Session")
        mock_session = mock_session_cls.return_value
        mock_session.post.side_effect = requests.RequestException("DNS Error")

        provider = WebhookAdminProvider(webhook_url="https://api.example.com/webhook")

        with pytest.raises(NotificationWebhookError) as exc_info:
            provider.send_system_alert(source="Celery", error_message="Task Failed", level="CRITICAL")

        assert "Failed to send system alert via Webhook" in str(exc_info.value)
        assert "DNS Error" in str(exc_info.value)
