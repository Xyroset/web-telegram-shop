from decimal import Decimal
from unittest.mock import MagicMock

import pytest
from pytest_mock import MockerFixture

from apps.notifications.domain.exceptions import NotificationEmailError
from apps.notifications.providers.email import EmailAdminProvider


class TestEmailAdminProvider:
    """
    Verify business rules for formatting and sending admin email alerts.
    """

    def test_send_order_paid_alert_success(self, mocker: MockerFixture, monkeypatch: pytest.MonkeyPatch) -> None:
        """
        Happy path: Successfully format and send an email alert.

        **Setup:**
        - Mock Django's send_mail function.
        - Create a fake OrderSnapshotData instance fully populated with delivery info using MagicMock.
        - Set environment variables for the admin panel link.

        **Expected:**
        - send_mail is called exactly once.
        - The subject contains the correct Order ID.
        - The message successfully parses the delivery payload and admin url.
        """
        mock_send_mail = mocker.patch("apps.notifications.providers.email.send_mail")
        monkeypatch.setenv("BACKEND_VIRTUAL_HOST", "test.localhost")

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
        }

        provider = EmailAdminProvider(target_emails=["admin@test.com"], from_email="system@test.com")

        provider.send_order_paid_alert(order_data=fake_order, physical_items=[])

        mock_send_mail.assert_called_once()
        call_kwargs = mock_send_mail.call_args.kwargs

        assert "order-123" in call_kwargs["subject"]
        assert call_kwargs["from_email"] == "system@test.com"
        assert call_kwargs["recipient_list"] == ["admin@test.com"]
        assert "order-123" in call_kwargs["message"]
        assert "test.localhost" in call_kwargs["message"]

    def test_send_order_paid_alert_missing_delivery_data(self, mocker: MockerFixture) -> None:
        """
        Happy path (Edge Case): Handle missing delivery dictionaries safely.

        **Setup:**
        - Mock Django's send_mail function.
        - Create a fake OrderSnapshotData where delivery_data is None.

        **Expected:**
        - send_mail is called successfully without throwing a KeyError.
        - The message body uses the correct fallbacks (e.g., 'Unknown').
        """
        mock_send_mail = mocker.patch("apps.notifications.providers.email.send_mail")

        fake_order = MagicMock()
        fake_order.id = "order-123"
        fake_order.delivery.delivery_data = None

        provider = EmailAdminProvider(target_emails=["admin@test.com"], from_email="system@test.com")

        provider.send_order_paid_alert(order_data=fake_order, physical_items=[])

        mock_send_mail.assert_called_once()
        call_kwargs = mock_send_mail.call_args.kwargs

        assert "order-123" in call_kwargs["subject"]
        assert call_kwargs["message"] is not None

    def test_send_order_paid_alert_failure(self, mocker: MockerFixture) -> None:
        """
        Failure: SMTP or send_mail raises an exception.

        **Setup:**
        - Mock Django's send_mail to raise an Exception (simulating network/SMTP failure).

        **Expected:**
        - The exception is caught and re-raised as a NotificationEmailError.
        """
        mock_send_mail = mocker.patch("apps.notifications.providers.email.send_mail")
        mock_send_mail.side_effect = Exception("SMTP Connection Timeout")

        fake_order = MagicMock(id="order-123")

        provider = EmailAdminProvider(target_emails=["admin@test.com"], from_email="system@test.com")

        with pytest.raises(NotificationEmailError) as exc_info:
            provider.send_order_paid_alert(order_data=fake_order, physical_items=[])

        assert "Failed to send Email message for order id: order-123" in str(exc_info.value)
        assert "SMTP Connection Timeout" in str(exc_info.value)

    def test_send_transaction_failed_alert_success(
        self, mocker: MockerFixture, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """
        Happy path: Successfully format and send an email alert for a failed transaction.

        **Setup:**
        - Mock Django's send_mail function.
        - Build a fake TransactionSnapshotData object with nested order data.

        **Expected:**
        - send_mail is called exactly once.
        - The formatted message contains transaction details.
        """
        mock_send_mail = mocker.patch("apps.notifications.providers.email.send_mail")
        monkeypatch.setenv("BACKEND_VIRTUAL_HOST", "test.localhost")

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

        fake_tx.order.id = "order-123"
        fake_tx.order.delivery.delivery_data = None

        provider = EmailAdminProvider(target_emails=["admin@test.com"], from_email="system@test.com")

        provider.send_transaction_failed_alert(transaction_data=fake_tx)

        mock_send_mail.assert_called_once()
        call_kwargs = mock_send_mail.call_args.kwargs

        assert "txn-1" in call_kwargs["subject"]
        assert "txn-1" in call_kwargs["message"]
        assert "order-123" in call_kwargs["message"]
        assert "test.localhost" in call_kwargs["message"]

    def test_send_transaction_failed_alert_failure(self, mocker: MockerFixture) -> None:
        """
        Failure: send_mail raises an exception during transaction failure alert.

        **Setup:**
        - Mock Django's send_mail to raise an Exception.

        **Expected:**
        - The exception is caught, logged, and re-raised as a NotificationEmailError.
        """
        mock_send_mail = mocker.patch("apps.notifications.providers.email.send_mail")
        mock_send_mail.side_effect = Exception("Email relay down")

        fake_tx = MagicMock(id="txn-1")

        provider = EmailAdminProvider(target_emails=["admin@test.com"], from_email="system@test.com")

        with pytest.raises(NotificationEmailError) as exc_info:
            provider.send_transaction_failed_alert(transaction_data=fake_tx)

        assert "Failed to send Email message for transaction id: txn-1" in str(exc_info.value)
        assert "Email relay down" in str(exc_info.value)

    def test_send_system_alert_success(self, mocker: MockerFixture) -> None:
        """
        Happy path: Successfully format and send a system alert via email.

        **Setup:**
        - Mock Django's send_mail function.

        **Expected:**
        - The subject and message correctly include the source, error level, and error message.
        """
        mock_send_mail = mocker.patch("apps.notifications.providers.email.send_mail")

        provider = EmailAdminProvider(target_emails=["admin@test.com"], from_email="system@test.com")

        provider.send_system_alert(source="CeleryWorker", error_message="Redis Connection Error", level="CRITICAL")

        mock_send_mail.assert_called_once()
        call_kwargs = mock_send_mail.call_args.kwargs

        assert "CRITICAL" in call_kwargs["subject"]
        assert "CeleryWorker" in call_kwargs["subject"]
        assert "Redis Connection Error" in call_kwargs["message"]
        assert "CRITICAL" in call_kwargs["message"]

    def test_send_system_alert_failure(self, mocker: MockerFixture) -> None:
        """
        Failure: send_mail raises an exception during system alert.

        **Setup:**
        - Mock Django's send_mail to raise an Exception.

        **Expected:**
        - The exception is caught and re-raised as a NotificationEmailError.
        """
        mock_send_mail = mocker.patch("apps.notifications.providers.email.send_mail")
        mock_send_mail.side_effect = Exception("SMTP Error")

        provider = EmailAdminProvider(target_emails=["admin@test.com"], from_email="system@test.com")

        with pytest.raises(NotificationEmailError) as exc_info:
            provider.send_system_alert(source="CeleryWorker", error_message="Redis Connection Error")

        assert "Failed to send system alert via Email" in str(exc_info.value)
        assert "SMTP Error" in str(exc_info.value)
