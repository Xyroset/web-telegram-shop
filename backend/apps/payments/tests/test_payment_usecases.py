import uuid
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from apps.orders.repo import OrderRepository
from apps.payments.domain.dto import InputInvoiceDTO
from apps.payments.domain.exceptions import (
    PaymentGatewayBadRequestError,
    PaymentGatewayUnavailableError,
)
from apps.payments.domain.interfaces import PaymentGatewayProtocol
from apps.payments.models import PaymentTransaction
from apps.payments.repo import PaymentTransactionRepository
from apps.payments.usecases import (
    CancelTransactionCase,
    CreateInvoiceCase,
    ExpireTransactionCase,
    ProcessWebhookCase,
    RefundTransactionCase,
    ResolveOverpaymentCase,
)
from apps.users.repo import UserSettingsDataRepository


@patch("django.db.transaction.atomic", MagicMock())
class TestExpireTransactionCase:
    """
    Verify business rules for expiring payment transactions.
    """

    def test_expire_pending_transaction_success(self) -> None:
        """
        Happy path: Mark a fully pending transaction as expired.
        """
        mock_payment_repo: MagicMock | PaymentTransactionRepository = MagicMock()
        fake_transaction = MagicMock()
        fake_transaction.state = PaymentTransaction.Status.PENDING
        fake_transaction.current_crypto_money.amount = Decimal("0.00")
        fake_transaction.mark_as_expired.return_value = ["state"]
        mock_payment_repo.get_for_update_by.return_value = fake_transaction  # type: ignore[union-attr]
        usecase = ExpireTransactionCase(payment_repo=mock_payment_repo)

        usecase.execute(transaction_id="tx_123")

        fake_transaction.mark_as_expired.assert_called_once()
        mock_payment_repo.save.assert_called_once_with(instance=fake_transaction, update_fields=["state"])  # type: ignore[union-attr]

    def test_expire_transaction_with_captured_funds_marks_as_wrong_amount(self) -> None:
        """
        Happy path (edge case): Transaction has some funds captured, so it's marked as WRONG_AMOUNT instead.
        """
        mock_payment_repo: MagicMock | PaymentTransactionRepository = MagicMock()
        fake_transaction = MagicMock()
        fake_transaction.state = PaymentTransaction.Status.PARTIALLY_PAID
        fake_transaction.mark_as_wrong_amount.return_value = ["state"]
        mock_payment_repo.get_for_update_by.return_value = fake_transaction  # type: ignore[union-attr]
        usecase = ExpireTransactionCase(payment_repo=mock_payment_repo)

        usecase.execute(transaction_id="tx_123")

        fake_transaction.mark_as_wrong_amount.assert_called_once()
        mock_payment_repo.save.assert_called_once_with(instance=fake_transaction, update_fields=["state"])  # type: ignore[union-attr]


@patch("django.db.transaction.atomic", MagicMock())
class TestCancelTransactionCase:
    """
    Verify business rules for user/system initiated transaction cancellation.
    """

    @patch("apps.payments.usecases.base.current_app")
    def test_cancel_pending_transaction_by_user(self, mock_celery_app: MagicMock) -> None:
        """
        Happy path: Cancel pending transaction and revoke background tasks.
        """
        mock_payment_repo: MagicMock | PaymentTransactionRepository = MagicMock()
        fake_user = MagicMock()
        fake_transaction = MagicMock()
        fake_transaction.state = PaymentTransaction.Status.PENDING
        fake_transaction.current_crypto_money.amount = Decimal("0.00")
        fake_transaction.task_id = uuid.uuid4()
        fake_transaction.mark_as_cancelled.return_value = ["state"]
        mock_payment_repo.get_for_update_by.return_value = fake_transaction  # type: ignore[union-attr]
        usecase = CancelTransactionCase(payment_repo=mock_payment_repo)

        usecase.execute(transaction_id="tx_123", user=fake_user)

        mock_payment_repo.get_for_update_by.assert_called_once_with(id="tx_123", order__user=fake_user)  # type: ignore[union-attr]
        fake_transaction.mark_as_cancelled.assert_called_once()
        mock_payment_repo.save.assert_called_once_with(instance=fake_transaction, update_fields=["state"])  # type: ignore[union-attr]
        mock_celery_app.control.revoke.assert_called_once_with(str(fake_transaction.task_id), terminate=True)


@patch("django.db.transaction.atomic", MagicMock())
class TestResolveOverpaymentCase:
    """
    Verify business rules for admin-resolved overpayments.
    """

    @patch("django.db.transaction.on_commit", side_effect=lambda hook: hook())
    @patch("apps.payments.usecases.base.current_app")
    def test_resolve_overpayment_success(self, mock_celery_app: MagicMock, mock_on_commit: MagicMock) -> None:
        """
        Happy path: Successfully marks transaction/order as PAID and triggers fulfillment.
        """
        mock_payment_repo: MagicMock | PaymentTransactionRepository = MagicMock()
        mock_order_repo: MagicMock | OrderRepository = MagicMock()

        fake_transaction = MagicMock()
        fake_transaction.order_id = "ord_1"
        fake_transaction.resolve_overpayment.return_value = ["state"]
        mock_payment_repo.get_for_update_by.return_value = fake_transaction  # type: ignore[union-attr]

        fake_order = MagicMock()
        fake_order.id = "ord_1"
        fake_order.task_id = "task_99"
        fake_order.mark_as_paid.return_value = ["state"]
        mock_order_repo.get_for_update_by.return_value = fake_order  # type: ignore[union-attr]

        usecase = ResolveOverpaymentCase(payment_repo=mock_payment_repo, order_repo=mock_order_repo)

        usecase.execute(transaction_id="tx_123")

        fake_transaction.resolve_overpayment.assert_called_once()
        fake_order.mark_as_paid.assert_called_once()
        mock_payment_repo.save.assert_called_once_with(fake_transaction, update_fields=["state"])  # type: ignore[union-attr]
        mock_order_repo.save.assert_called_once_with(fake_order, update_fields=["state"])  # type: ignore[union-attr]
        mock_celery_app.control.revoke.assert_called_once_with("task_99", terminate=True)
        mock_celery_app.send_task.assert_called_once_with("orders.process_order_fulfillment_task", args=["ord_1"])


@patch("django.db.transaction.atomic", MagicMock())
class TestRefundTransactionCase:
    """
    Verify business rules for admin-refunded transactions.
    """

    @patch("django.db.transaction.on_commit", side_effect=lambda hook: hook())
    @patch("apps.payments.usecases.base.current_app")
    def test_refund_transaction_success(self, mock_celery_app: MagicMock, mock_on_commit: MagicMock) -> None:
        """
        Happy path: Mark transaction as REFUNDED, cancel order, and release stock.
        """
        mock_payment_repo: MagicMock | PaymentTransactionRepository = MagicMock()
        mock_order_repo: MagicMock | OrderRepository = MagicMock()

        fake_transaction = MagicMock()
        fake_transaction.order_id = "ord_1"
        fake_transaction.mark_as_refunded.return_value = ["state"]
        mock_payment_repo.get_for_update_by.return_value = fake_transaction  # type: ignore[union-attr]

        fake_order = MagicMock()
        fake_order.id = "ord_1"
        fake_order.task_id = "task_99"
        fake_order.mark_as_cancelled.return_value = ["state"]
        mock_order_repo.get_for_update_by.return_value = fake_order  # type: ignore[union-attr]

        usecase = RefundTransactionCase(payment_repo=mock_payment_repo, order_repo=mock_order_repo)

        usecase.execute(transaction_id="tx_123")

        fake_transaction.mark_as_refunded.assert_called_once()
        fake_order.mark_as_cancelled.assert_called_once()
        mock_celery_app.send_task.assert_called_once_with(
            "orders.tasks.process_order_reversion_task", args=["ord_1", "cancel"]
        )


@patch("django.db.transaction.atomic", MagicMock())
class TestCreateInvoiceCase:
    """
    Verify orchestration of generating a payment invoice.
    """

    @patch("django.db.transaction.on_commit", side_effect=lambda hook: hook())
    @patch("apps.payments.usecases.create_invoice.InvoiceCreationService")
    @patch("apps.payments.usecases.create_invoice.current_app")
    def test_create_invoice_success(
        self, mock_celery_app: MagicMock, mock_service_class: MagicMock, mock_on_commit: MagicMock
    ) -> None:
        """
        Happy path: Invoice is generated and models are updated correctly.
        """
        mock_payment_repo: MagicMock | PaymentTransactionRepository = MagicMock()
        mock_order_repo: MagicMock | OrderRepository = MagicMock()
        mock_gateway: MagicMock | PaymentGatewayProtocol = MagicMock()
        mock_settings_repo: MagicMock | UserSettingsDataRepository = MagicMock()

        mock_invoice_service = mock_service_class.return_value
        fake_fiat = MagicMock()
        fake_fiat.amount = Decimal("100.00")
        mock_invoice_service.calculate_target_amount.return_value = fake_fiat

        fake_order = MagicMock()
        fake_order.id = "ord_1"
        fake_order.state = "pending"
        fake_order.get_active_transaction.return_value = None
        fake_order.get_remaining_usd_balance.return_value = Decimal("100.00")
        fake_order.update_order.return_value = ["payload_url"]
        mock_order_repo.get_for_update_by.return_value = fake_order  # type: ignore[union-attr]

        fake_transaction = MagicMock()
        fake_transaction.id = "tx_123"
        fake_transaction.update_payment.return_value = ["invoice_id"]
        mock_payment_repo.create.return_value = fake_transaction  # type: ignore[union-attr]
        mock_payment_repo.get_for_update_by.return_value = fake_transaction  # type: ignore[union-attr]

        fake_invoice = MagicMock()
        fake_invoice.invoice_id = "inv_123"
        fake_invoice.pay_url = "https://pay.example.com"
        mock_gateway.create_invoice.return_value = fake_invoice  # type: ignore[union-attr]

        usecase = CreateInvoiceCase(
            payment_repo=mock_payment_repo,
            order_repo=mock_order_repo,
            gateway=mock_gateway,
            user_settings_repo=mock_settings_repo,
        )
        fake_user = MagicMock()
        dto = InputInvoiceDTO(order_id=uuid.uuid4(), network="TRC20", currency="USDT")

        result = usecase.execute(user=fake_user, dto=dto)

        assert result["payload_url"] == "https://pay.example.com"
        assert result["transaction_id"] == "tx_123"
        mock_gateway.create_invoice.assert_called_once_with(  # type: ignore[union-attr]
            amount=Decimal("100.00"), currency="USDT", network="TRC20", order_id=str(dto.order_id)
        )
        mock_celery_app.send_task.assert_called_once()

    @patch("apps.payments.usecases.create_invoice.InvoiceCreationService")
    def test_create_invoice_gateway_failure(self, mock_service_class: MagicMock) -> None:
        """
        Failure: Network request to gateway fails, transaction is marked as failed.
        """
        mock_payment_repo: MagicMock | PaymentTransactionRepository = MagicMock()
        mock_order_repo: MagicMock | OrderRepository = MagicMock()
        mock_gateway: MagicMock | PaymentGatewayProtocol = MagicMock()
        mock_settings_repo: MagicMock | UserSettingsDataRepository = MagicMock()

        mock_invoice_service = mock_service_class.return_value
        fake_fiat = MagicMock()
        fake_fiat.amount = Decimal("100.00")
        mock_invoice_service.calculate_target_amount.return_value = fake_fiat

        fake_order = MagicMock()
        fake_order.state = "pending"
        fake_order.get_active_transaction.return_value = None
        fake_order.get_remaining_usd_balance.return_value = Decimal("100.00")
        mock_order_repo.get_for_update_by.return_value = fake_order  # type: ignore[union-attr]

        fake_transaction = MagicMock()
        fake_transaction.mark_as_failed.return_value = ["state"]
        fake_transaction.update_payment.return_value = ["raw_response"]
        mock_payment_repo.create.return_value = fake_transaction  # type: ignore[union-attr]
        mock_payment_repo.get_for_update_by.return_value = fake_transaction  # type: ignore[union-attr]

        mock_gateway.create_invoice.side_effect = Exception("API Down")  # type: ignore[union-attr]

        usecase = CreateInvoiceCase(
            payment_repo=mock_payment_repo,
            order_repo=mock_order_repo,
            gateway=mock_gateway,
            user_settings_repo=mock_settings_repo,
        )
        fake_user = MagicMock()
        dto = InputInvoiceDTO(order_id=uuid.uuid4(), network="TRC20", currency="USDT")

        with pytest.raises(PaymentGatewayUnavailableError, match="API Down"):
            usecase.execute(user=fake_user, dto=dto)

        fake_transaction.mark_as_failed.assert_called_once()
        mock_payment_repo.save.assert_called_once()  # type: ignore[union-attr]


@patch("django.db.transaction.atomic", MagicMock())
class TestProcessWebhookCase:
    """
    Verify incoming webhook payload resolution and side effects.
    """

    @patch("django.db.transaction.on_commit", side_effect=lambda hook: hook())
    @patch("apps.payments.usecases.process_webhook.PaymentProcessingService")
    @patch("apps.payments.usecases.process_webhook.current_app")
    def test_process_webhook_success_paid(
        self, mock_celery_app: MagicMock, mock_service_class: MagicMock, mock_on_commit: MagicMock
    ) -> None:
        """
        Happy path: Valid webhook results in PAID state and triggers fulfillment.
        """
        mock_payment_repo: MagicMock | PaymentTransactionRepository = MagicMock()
        mock_order_repo: MagicMock | OrderRepository = MagicMock()
        mock_gateway: MagicMock | PaymentGatewayProtocol = MagicMock()

        mock_gateway.verify_webhook.return_value = True  # type: ignore[union-attr]
        mock_gateway.normalize_webhook_data.return_value = {  # type: ignore[union-attr]
            "invoice_id": "inv_1",
            "payment_status": "finished",
            "actually_paid": "100.00",
            "pay_amount": "100.00",
            "pay_address": "0xABC",
            "sender_address": "0xDEF",
            "payin_hash": "tx_abc",
        }

        fake_transaction = MagicMock()
        fake_transaction.id = "tx_1"
        fake_transaction.state = PaymentTransaction.Status.PAID
        mock_payment_repo.get_for_update_by.return_value = fake_transaction  # type: ignore[union-attr]

        fake_order = MagicMock()
        fake_order.id = "ord_1"
        fake_order.task_id = "task_22"
        mock_order_repo.get_for_update_by.return_value = fake_order  # type: ignore[union-attr]

        mock_processing_service = mock_service_class.return_value
        mock_processing_service.process_webhook_update.return_value = (["state"], ["state"])

        usecase = ProcessWebhookCase(order_repo=mock_order_repo, payment_repo=mock_payment_repo, gateway=mock_gateway)

        usecase.execute(payload={"id": 123}, signature="hash_sig")

        mock_processing_service.process_webhook_update.assert_called_once()
        mock_payment_repo.save.assert_called_once_with(fake_transaction, update_fields=["state"])  # type: ignore[union-attr]
        mock_order_repo.save.assert_called_once_with(fake_order, update_fields=["state"])  # type: ignore[union-attr]
        mock_celery_app.control.revoke.assert_called_once_with("task_22", terminate=True)
        mock_celery_app.send_task.assert_called_once_with("orders.process_order_fulfillment_task", args=["ord_1"])

    def test_process_webhook_invalid_signature(self) -> None:
        """
        Failure: Raise Bad Request if HMAC signature validation fails.
        """
        mock_payment_repo: MagicMock | PaymentTransactionRepository = MagicMock()
        mock_order_repo: MagicMock | OrderRepository = MagicMock()
        mock_gateway: MagicMock | PaymentGatewayProtocol = MagicMock()

        mock_gateway.verify_webhook.return_value = False  # type: ignore[union-attr]

        usecase = ProcessWebhookCase(order_repo=mock_order_repo, payment_repo=mock_payment_repo, gateway=mock_gateway)

        with pytest.raises(PaymentGatewayBadRequestError):
            usecase.execute(payload={"bad": "data"}, signature="wrong_hash")

        mock_payment_repo.get_for_update_by.assert_not_called()  # type: ignore[union-attr]
