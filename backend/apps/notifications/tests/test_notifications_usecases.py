from unittest.mock import MagicMock, patch

import pytest

from apps.catalog.repo import DigitalAssetRepository
from apps.notifications.domain.exceptions import (
    NotificationProviderRunTimeError,
    NotificationProvidersNotFound,
)
from apps.notifications.domain.interfaces import (
    OrderAlertProvider,
    SupportAlertProvider,
    SystemAlertProvider,
    TransactionAlertProvider,
    UserNotificationProvider,
)
from apps.notifications.usecases import (
    NotifyAdminOrderPaidCase,
    NotifyAdminSupportTicketCase,
    NotifyAdminSystemAlertCase,
    NotifyAdminTransactionFailedCase,
    NotifyUserDigitalDeliveryCase,
)
from apps.orders.repo import OrderRepository
from apps.payments.repo import PaymentTransactionRepository
from apps.support.repo import TicketRepository
from apps.users.repo import UserSettingsDataRepository


class TestNotifyAdminOrderPaidCase:
    """
    Unit tests for NotifyAdminOrderPaidCase orchestrating order alert dispatches.
    """

    def test_notify_admin_order_paid_success(self) -> None:
        mock_order_repo: MagicMock | OrderRepository = MagicMock()
        fake_user = MagicMock(tg_username="john_doe", tg_id=12345)
        fake_delivery = MagicMock(provider_code="nova_poshta", cost="50.00", delivery_data={})
        fake_order = MagicMock(
            id="order-uuid-123",
            user=fake_user,
            amount_usd="100.00",
            state="PAID",
            delivery=fake_delivery,
        )
        fake_variant = MagicMock(title="Standard Edition", product=MagicMock(name="Game"))
        fake_physical_item = MagicMock(is_digital=False, variant=fake_variant, quantity=1)
        fake_digital_item = MagicMock(is_digital=True, variant=fake_variant, quantity=1)

        mock_order_repo.get_order_with_delivery_data.return_value = fake_order  # type: ignore[union-attr]
        mock_order_repo.get_order_items.return_value = [fake_physical_item, fake_digital_item]  # type: ignore[union-attr]
        provider_1: MagicMock | OrderAlertProvider = MagicMock()
        provider_2: MagicMock | OrderAlertProvider = MagicMock()
        usecase = NotifyAdminOrderPaidCase(order_repo=mock_order_repo, providers=[provider_1, provider_2])

        usecase.execute(order_id="order-uuid-123")

        mock_order_repo.get_order_with_delivery_data.assert_called_once_with(order_id="order-uuid-123")  # type: ignore[union-attr]
        mock_order_repo.get_order_items.assert_called_once_with(order=fake_order)  # type: ignore[union-attr]
        assert provider_1.send_order_paid_alert.call_count == 1  # type: ignore[union-attr]
        assert provider_2.send_order_paid_alert.call_count == 1  # type: ignore[union-attr]

    def test_notify_admin_order_paid_raises_when_no_providers(self) -> None:
        mock_order_repo: MagicMock | OrderRepository = MagicMock()
        fake_user = MagicMock(tg_username="john_doe", tg_id=12345)
        fake_delivery = MagicMock(provider_code="nova_poshta", cost="50.00", delivery_data={})
        fake_order = MagicMock(
            id="order-uuid-123",
            user=fake_user,
            amount_usd="100.00",
            state="PAID",
            delivery=fake_delivery,
        )

        mock_order_repo.get_order_with_delivery_data.return_value = fake_order  # type: ignore[union-attr]
        mock_order_repo.get_order_items.return_value = []  # type: ignore[union-attr]
        usecase = NotifyAdminOrderPaidCase(order_repo=mock_order_repo, providers=[])

        with pytest.raises(NotificationProvidersNotFound):
            usecase.execute(order_id="order-uuid-123")

    def test_notify_admin_order_paid_partial_failure_collects_errors(self) -> None:
        mock_order_repo: MagicMock | OrderRepository = MagicMock()
        fake_user = MagicMock(tg_username="john_doe", tg_id=12345)
        fake_delivery = MagicMock(provider_code="nova_poshta", cost="50.00", delivery_data={})
        fake_order = MagicMock(
            id="order-uuid-123",
            user=fake_user,
            amount_usd="100.00",
            state="PAID",
            delivery=fake_delivery,
        )

        mock_order_repo.get_order_with_delivery_data.return_value = fake_order  # type: ignore[union-attr]
        mock_order_repo.get_order_items.return_value = []  # type: ignore[union-attr]
        provider_success: MagicMock | OrderAlertProvider = MagicMock()
        provider_success.__class__.__name__ = "TelegramAdminProvider"
        provider_failed: MagicMock | OrderAlertProvider = MagicMock()
        provider_failed.__class__.__name__ = "EmailAdminProvider"
        provider_failed.send_order_paid_alert.side_effect = Exception("SMTP timeout")  # type: ignore[union-attr]
        usecase = NotifyAdminOrderPaidCase(
            order_repo=mock_order_repo,
            providers=[provider_success, provider_failed],
        )

        with pytest.raises(NotificationProviderRunTimeError) as exc_info:
            usecase.execute(order_id="order-uuid-123")

        assert provider_success.send_order_paid_alert.call_count == 1  # type: ignore[union-attr]
        assert provider_failed.send_order_paid_alert.call_count == 1  # type: ignore[union-attr]
        assert "EmailAdminProvider" in str(exc_info.value)


class TestNotifyAdminTransactionFailedCase:
    """
    Unit tests for NotifyAdminTransactionFailedCase.
    """

    def test_notify_admin_transaction_failed_success(self) -> None:
        mock_payment_repo: MagicMock | PaymentTransactionRepository = MagicMock()
        fake_user = MagicMock(tg_username="jane_doe", tg_id=54321)
        fake_delivery = MagicMock(provider_code="none", cost="0.00", delivery_data={})
        fake_order = MagicMock(id="ord-1", user=fake_user, amount_usd="25.00", state="PENDING", delivery=fake_delivery)
        fake_tx = MagicMock(
            id="tx-123",
            order=fake_order,
            invoice_id="inv-123",
            payment_currency="USDT",
            network="TRX",
            target_amount_usd="25.00",
            amount_crypto="24.99",
            current_amount_crypto="0.00",
            captured_amount_usd="0.00",
            receiver_address="addr1",
            sender_address="addr2",
            tx_hash="hash123",
            state="FAILED",
            raw_response={},
        )

        mock_payment_repo.get_by_id_with_full_details.return_value = fake_tx  # type: ignore[union-attr]
        provider: MagicMock | TransactionAlertProvider = MagicMock()
        usecase = NotifyAdminTransactionFailedCase(payment_repo=mock_payment_repo, providers=[provider])

        usecase.execute(transaction_id="tx-123")

        mock_payment_repo.get_by_id_with_full_details.assert_called_once_with(transaction_id="tx-123")  # type: ignore[union-attr]
        assert provider.send_transaction_failed_alert.call_count == 1  # type: ignore[union-attr]

    def test_notify_admin_transaction_failed_raises_when_no_providers(self) -> None:
        mock_payment_repo: MagicMock | PaymentTransactionRepository = MagicMock()
        fake_user = MagicMock(tg_username="jane_doe", tg_id=54321)
        fake_delivery = MagicMock(provider_code="none", cost="0.00", delivery_data={})
        fake_order = MagicMock(id="ord-1", user=fake_user, amount_usd="25.00", state="PENDING", delivery=fake_delivery)
        fake_tx = MagicMock(
            id="tx-123",
            order=fake_order,
            invoice_id="inv-123",
            payment_currency="USDT",
            network="TRX",
            target_amount_usd="25.00",
            amount_crypto="24.99",
            current_amount_crypto="0.00",
            captured_amount_usd="0.00",
            receiver_address="addr1",
            sender_address="addr2",
            tx_hash="hash123",
            state="FAILED",
            raw_response={},
        )

        mock_payment_repo.get_by_id_with_full_details.return_value = fake_tx  # type: ignore[union-attr]
        usecase = NotifyAdminTransactionFailedCase(payment_repo=mock_payment_repo, providers=[])

        with pytest.raises(NotificationProvidersNotFound):
            usecase.execute(transaction_id="tx-123")

    def test_notify_admin_transaction_failed_raises_on_provider_error(self) -> None:
        mock_payment_repo: MagicMock | PaymentTransactionRepository = MagicMock()
        fake_user = MagicMock(tg_username="jane_doe", tg_id=54321)
        fake_delivery = MagicMock(provider_code="none", cost="0.00", delivery_data={})
        fake_order = MagicMock(id="ord-1", user=fake_user, amount_usd="25.00", state="PENDING", delivery=fake_delivery)
        fake_tx = MagicMock(
            id="tx-123",
            order=fake_order,
            invoice_id="inv-123",
            payment_currency="USDT",
            network="TRX",
            target_amount_usd="25.00",
            amount_crypto="24.99",
            current_amount_crypto="0.00",
            captured_amount_usd="0.00",
            receiver_address="addr1",
            sender_address="addr2",
            tx_hash="hash123",
            state="FAILED",
            raw_response={},
        )

        mock_payment_repo.get_by_id_with_full_details.return_value = fake_tx  # type: ignore[union-attr]
        failed_provider: MagicMock | TransactionAlertProvider = MagicMock()
        failed_provider.__class__.__name__ = "WebhookAdminProvider"
        failed_provider.send_transaction_failed_alert.side_effect = Exception("Connection refused")  # type: ignore[union-attr]
        usecase = NotifyAdminTransactionFailedCase(payment_repo=mock_payment_repo, providers=[failed_provider])

        with pytest.raises(NotificationProviderRunTimeError) as exc_info:
            usecase.execute(transaction_id="tx-123")

        assert "WebhookAdminProvider" in str(exc_info.value)


@patch("django.db.transaction.atomic")
class TestNotifyAdminSupportTicketCase:
    """
    Unit tests for NotifyAdminSupportTicketCase.
    """

    def test_notify_admin_support_ticket_success_updates_triage_message(self, _mock_atomic: MagicMock) -> None:
        mock_ticket_repo: MagicMock | TicketRepository = MagicMock()
        fake_user = MagicMock(tg_username="bob", tg_id=111)
        fake_msg = MagicMock(text="Help me")
        fake_ticket_read = MagicMock(
            id="ticket-1", user=fake_user, category="GENERAL", state="OPEN", first_message=fake_msg
        )
        fake_ticket_update = MagicMock(
            id="ticket-1", user=fake_user, category="GENERAL", state="OPEN", first_message=fake_msg
        )
        fake_ticket_update.update_triage_message.return_value = ["triage_message_id"]

        mock_ticket_repo.get_by_id_with_full_details.side_effect = [fake_ticket_read, fake_ticket_update]  # type: ignore[union-attr]
        provider: MagicMock | SupportAlertProvider = MagicMock()
        provider.send_support_alert.return_value = 999  # type: ignore[union-attr]
        usecase = NotifyAdminSupportTicketCase(ticket_repo=mock_ticket_repo, providers=[provider])

        usecase.execute(ticket_id="ticket-1")

        assert provider.send_support_alert.call_count == 1  # type: ignore[union-attr]
        fake_ticket_update.update_triage_message.assert_called_once_with(triage_message_id=999)
        mock_ticket_repo.save.assert_called_once_with(  # type: ignore[union-attr]
            instance=fake_ticket_update, update_fields=["triage_message_id"]
        )

    def test_notify_admin_support_ticket_raises_when_no_providers(self, _mock_atomic: MagicMock) -> None:
        mock_ticket_repo: MagicMock | TicketRepository = MagicMock()
        fake_user = MagicMock(tg_username="bob", tg_id=111)
        fake_msg = MagicMock(text="Help me")
        fake_ticket = MagicMock(id="ticket-1", user=fake_user, category="GENERAL", state="OPEN", first_message=fake_msg)

        mock_ticket_repo.get_by_id_with_full_details.return_value = fake_ticket  # type: ignore[union-attr]
        usecase = NotifyAdminSupportTicketCase(ticket_repo=mock_ticket_repo, providers=[])

        with pytest.raises(NotificationProvidersNotFound):
            usecase.execute(ticket_id="ticket-1")

    def test_notify_admin_support_ticket_raises_on_provider_error(self, _mock_atomic: MagicMock) -> None:
        mock_ticket_repo: MagicMock | TicketRepository = MagicMock()
        fake_user = MagicMock(tg_username="bob", tg_id=111)
        fake_msg = MagicMock(text="Help me")
        fake_ticket = MagicMock(id="ticket-1", user=fake_user, category="GENERAL", state="OPEN", first_message=fake_msg)

        mock_ticket_repo.get_by_id_with_full_details.return_value = fake_ticket  # type: ignore[union-attr]
        failed_provider: MagicMock | SupportAlertProvider = MagicMock()
        failed_provider.__class__.__name__ = "TelegramAdminProvider"
        failed_provider.send_support_alert.side_effect = Exception("Telegram API timeout")  # type: ignore[union-attr]
        usecase = NotifyAdminSupportTicketCase(ticket_repo=mock_ticket_repo, providers=[failed_provider])

        with pytest.raises(NotificationProviderRunTimeError) as exc_info:
            usecase.execute(ticket_id="ticket-1")

        assert "TelegramAdminProvider" in str(exc_info.value)


class TestNotifyAdminSystemAlertCase:
    """
    Unit tests for NotifyAdminSystemAlertCase.
    """

    def test_notify_admin_system_alert_success(self) -> None:
        provider_1: MagicMock | SystemAlertProvider = MagicMock()
        provider_2: MagicMock | SystemAlertProvider = MagicMock()

        usecase = NotifyAdminSystemAlertCase(providers=[provider_1, provider_2])

        usecase.execute(source="celery.worker", error_message="Memory leak detected", level="CRITICAL")

        provider_1.send_system_alert.assert_called_once_with(  # type: ignore[union-attr]
            source="celery.worker", error_message="Memory leak detected", level="CRITICAL"
        )
        provider_2.send_system_alert.assert_called_once_with(  # type: ignore[union-attr]
            source="celery.worker", error_message="Memory leak detected", level="CRITICAL"
        )

    def test_notify_admin_system_alert_raises_when_no_providers(self) -> None:
        usecase = NotifyAdminSystemAlertCase(providers=[])

        with pytest.raises(NotificationProvidersNotFound):
            usecase.execute(source="celery.worker", error_message="Error")

    def test_notify_admin_system_alert_raises_on_provider_error(self) -> None:
        failed_provider: MagicMock | SystemAlertProvider = MagicMock()
        failed_provider.__class__.__name__ = "WebhookAdminProvider"
        failed_provider.send_system_alert.side_effect = Exception("HTTP 500")  # type: ignore[union-attr]

        usecase = NotifyAdminSystemAlertCase(providers=[failed_provider])

        with pytest.raises(NotificationProviderRunTimeError) as exc_info:
            usecase.execute(source="celery.worker", error_message="Error")

        assert "WebhookAdminProvider" in str(exc_info.value)


class TestNotifyUserDigitalDeliveryCase:
    """
    Unit tests for NotifyUserDigitalDeliveryCase delivering keys to users.
    """

    def test_notify_user_digital_delivery_success(self) -> None:
        mock_order_repo: MagicMock | OrderRepository = MagicMock()
        mock_digital_asset_repo: MagicMock | DigitalAssetRepository = MagicMock()
        mock_user_settings_repo: MagicMock | UserSettingsDataRepository = MagicMock()
        fake_user = MagicMock(tg_username="alice", tg_id=999)
        fake_delivery = MagicMock(provider_code="none", cost="0.00", delivery_data={})
        fake_order = MagicMock(id="order-1", user=fake_user, amount_usd="20.00", state="PAID", delivery=fake_delivery)
        fake_settings = MagicMock(current_language_code="en")
        fake_variant = MagicMock(title="Standard Key", product=MagicMock(name="App"))
        fake_digital_item = MagicMock(id="item-uuid-1", is_digital=True, variant=fake_variant, quantity=1)
        fake_asset = MagicMock(order_item_id="item-uuid-1", content="KEY-123-ABC")

        mock_order_repo.get_by.return_value = fake_order  # type: ignore[union-attr]
        mock_user_settings_repo.get_by.return_value = fake_settings  # type: ignore[union-attr]
        mock_order_repo.get_order_items.return_value = [fake_digital_item]  # type: ignore[union-attr]
        mock_digital_asset_repo.filter_by.return_value = [fake_asset]  # type: ignore[union-attr]
        provider: MagicMock | UserNotificationProvider = MagicMock()
        usecase = NotifyUserDigitalDeliveryCase(
            order_repo=mock_order_repo,
            digital_asset_repo=mock_digital_asset_repo,
            user_settings_repo=mock_user_settings_repo,
            providers=[provider],
        )

        usecase.execute(order_id="order-1")

        mock_order_repo.get_by.assert_called_once_with(id="order-1")  # type: ignore[union-attr]
        mock_user_settings_repo.get_by.assert_called_once_with(user=fake_user)  # type: ignore[union-attr]
        mock_digital_asset_repo.filter_by.assert_called_once_with(order_item_id__in=["item-uuid-1"])  # type: ignore[union-attr]
        assert provider.send_digital_delivery.call_count == 1  # type: ignore[union-attr]

    def test_notify_user_digital_delivery_early_returns_when_no_digital_items(self) -> None:
        mock_order_repo: MagicMock | OrderRepository = MagicMock()
        mock_digital_asset_repo: MagicMock | DigitalAssetRepository = MagicMock()
        mock_user_settings_repo: MagicMock | UserSettingsDataRepository = MagicMock()
        fake_user = MagicMock()
        fake_order = MagicMock(id="order-1", user=fake_user)
        fake_settings = MagicMock(current_language_code="en")
        fake_physical_item = MagicMock(is_digital=False)

        mock_order_repo.get_by.return_value = fake_order  # type: ignore[union-attr]
        mock_user_settings_repo.get_by.return_value = fake_settings  # type: ignore[union-attr]
        mock_order_repo.get_order_items.return_value = [fake_physical_item]  # type: ignore[union-attr]
        provider: MagicMock | UserNotificationProvider = MagicMock()
        usecase = NotifyUserDigitalDeliveryCase(
            order_repo=mock_order_repo,
            digital_asset_repo=mock_digital_asset_repo,
            user_settings_repo=mock_user_settings_repo,
            providers=[provider],
        )

        usecase.execute(order_id="order-1")

        mock_digital_asset_repo.filter_by.assert_not_called()  # type: ignore[union-attr]
        provider.send_digital_delivery.assert_not_called()  # type: ignore[union-attr]
