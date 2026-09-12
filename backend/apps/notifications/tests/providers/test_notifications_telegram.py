from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from apps.notifications.domain.exceptions import NotificationTelegramError
from apps.notifications.providers.telegram import TelegramAdminProvider
from apps.telegram.usecases import SendTelegramMessageCase


class TestTelegramAdminProvider:
    """
    Verify business rules for formatting and sending admin Telegram alerts.
    """

    def test_send_order_paid_alert_success(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """
        Happy path: Successfully format and send a Telegram alert for a paid order.

        **Setup:**
        - Mock SendTelegramMessageCase.
        - Create fake OrderSnapshotData and OrderItemSnapshotData instances.
        - Set environment variables for the admin panel link.

        **Expected:**
        - The usecase execute method is called exactly once with the correct chat_id and thread_id.
        - The formatted message string successfully parses the delivery payload and physical items.
        """
        monkeypatch.setenv("BACKEND_VIRTUAL_HOST", "test.localhost")

        mock_telegram_usecase: MagicMock | SendTelegramMessageCase = MagicMock()

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
        }

        fake_item = MagicMock()
        fake_item.variant.product.name = "Test Product"
        fake_item.variant.title = "Red / XL"
        fake_item.quantity = 2

        provider = TelegramAdminProvider(
            chat_id="-100123456789", telegram_usecase=mock_telegram_usecase, message_thread_id=42
        )

        provider.send_order_paid_alert(order_data=fake_order, physical_items=[fake_item])

        mock_telegram_usecase.execute.assert_called_once()  # type: ignore[union-attr]
        call_kwargs = mock_telegram_usecase.execute.call_args.kwargs  # type: ignore[union-attr]

        assert call_kwargs["chat_id"] == "-100123456789"
        assert call_kwargs["message_thread_id"] == 42
        assert "order-123" in call_kwargs["text"]
        assert "123 Main St" in call_kwargs["text"]
        assert "Test Product: <b>Red / XL (x2)</b>" in call_kwargs["text"]
        assert "test.localhost" in call_kwargs["text"]

    def test_send_order_paid_alert_missing_delivery_data(self) -> None:
        """
        Happy path (Edge Case): Handle missing delivery dictionaries safely.

        **Setup:**
        - Mock SendTelegramMessageCase.
        - Create a fake OrderSnapshotData where delivery_data is None.

        **Expected:**
        - The usecase execute method is called without crashing (no KeyError).
        - The message text applies safe fallbacks (e.g., 'Unknown', 'Not provided').
        """
        mock_telegram_usecase: MagicMock | SendTelegramMessageCase = MagicMock()

        fake_order = MagicMock()
        fake_order.id = "order-123"
        fake_order.delivery.delivery_data = None

        provider = TelegramAdminProvider(chat_id="-100123456789", telegram_usecase=mock_telegram_usecase)

        provider.send_order_paid_alert(order_data=fake_order, physical_items=[])

        mock_telegram_usecase.execute.assert_called_once()  # type: ignore[union-attr]
        call_text = mock_telegram_usecase.execute.call_args.kwargs["text"]  # type: ignore[union-attr]

        assert "Not provided" in call_text
        assert "Unknown" in call_text
        assert "No physical items" in call_text

    def test_send_order_paid_alert_failure(self) -> None:
        """
        Failure: Telegram API usecase raises an exception.

        **Setup:**
        - Mock SendTelegramMessageCase to raise an Exception (simulating API failure).

        **Expected:**
        - The exception is caught, logged, and re-raised as a NotificationTelegramError.
        """
        mock_telegram_usecase: MagicMock | SendTelegramMessageCase = MagicMock()
        mock_telegram_usecase.execute.side_effect = Exception("Telegram API timeout")  # type: ignore[union-attr]

        fake_order = MagicMock(id="order-123")

        provider = TelegramAdminProvider(chat_id="-100123456789", telegram_usecase=mock_telegram_usecase)

        with pytest.raises(NotificationTelegramError) as exc_info:
            provider.send_order_paid_alert(order_data=fake_order, physical_items=[])

        assert "Failed to send Telegram message for order id: order-123" in str(exc_info.value)
        assert "Telegram API timeout" in str(exc_info.value)

    def test_send_transaction_failed_alert_success(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """
        Happy path: Successfully format and send a Telegram alert for a failed transaction.

        **Setup:**
        - Mock SendTelegramMessageCase.
        - Build a fake TransactionSnapshotData object with nested order data.

        **Expected:**
        - The usecase execute method is called exactly once.
        - The formatted message contains transaction details and safe fallback for missing delivery data.
        """
        monkeypatch.setenv("BACKEND_VIRTUAL_HOST", "test.localhost")

        mock_telegram_usecase: MagicMock | SendTelegramMessageCase = MagicMock()

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

        provider = TelegramAdminProvider(
            chat_id="-100123456789", telegram_usecase=mock_telegram_usecase, message_thread_id=42
        )

        provider.send_transaction_failed_alert(transaction_data=fake_tx)

        mock_telegram_usecase.execute.assert_called_once()  # type: ignore[union-attr]
        call_kwargs = mock_telegram_usecase.execute.call_args.kwargs  # type: ignore[union-attr]

        assert call_kwargs["chat_id"] == "-100123456789"
        assert call_kwargs["message_thread_id"] == 42
        assert "txn-1" in call_kwargs["text"]
        assert "order-123" in call_kwargs["text"]
        assert "FAILED" in call_kwargs["text"]
        assert "test.localhost" in call_kwargs["text"]

    def test_send_support_alert_success(self) -> None:
        """
        Happy path: Successfully format and send a Telegram alert for a support ticket.

        **Setup:**
        - Mock SendTelegramMessageCase returning a message ID.
        - Create a fake TicketSnapshotData.

        **Expected:**
        - The usecase execute method is called exactly once with reply_markup buttons.
        - Returns the message ID generated by Telegram.
        """
        mock_telegram_usecase: MagicMock | SendTelegramMessageCase = MagicMock()
        mock_telegram_usecase.execute.return_value = 999  # type: ignore[union-attr]

        fake_ticket = MagicMock()
        fake_ticket.id = "ticket-123"
        fake_ticket.user.tg_id = 555
        fake_ticket.user.tg_username = "help_user"
        fake_ticket.category = "refund"
        fake_ticket.state = "open"
        fake_ticket.first_message.text = "I need a refund!"

        provider = TelegramAdminProvider(
            chat_id="-100123456789", telegram_usecase=mock_telegram_usecase, message_thread_id=3
        )

        msg_id = provider.send_support_alert(ticket_data=fake_ticket)

        mock_telegram_usecase.execute.assert_called_once()  # type: ignore[union-attr]
        call_kwargs = mock_telegram_usecase.execute.call_args.kwargs  # type: ignore[union-attr]

        assert msg_id == 999
        assert "ticket-123" in call_kwargs["text"]
        assert "help_user" in call_kwargs["text"]
        assert "I need a refund!" in call_kwargs["text"]
        assert "ticket_accept_ticket-123" in str(call_kwargs["reply_markup"])

    def test_send_system_alert_success(self) -> None:
        """
        Happy path: Successfully format and send a Telegram system alert.

        **Setup:**
        - Mock SendTelegramMessageCase.

        **Expected:**
        - The message contains the error source and level.
        """
        mock_telegram_usecase: MagicMock | SendTelegramMessageCase = MagicMock()

        provider = TelegramAdminProvider(chat_id="-100123456789", telegram_usecase=mock_telegram_usecase)

        provider.send_system_alert(source="CeleryWorker", error_message="Redis Connection Error", level="CRITICAL")

        mock_telegram_usecase.execute.assert_called_once()  # type: ignore[union-attr]
        call_text = mock_telegram_usecase.execute.call_args.kwargs["text"]  # type: ignore[union-attr]

        assert "CeleryWorker" in call_text
        assert "CRITICAL" in call_text
        assert "Redis Connection Error" in call_text
