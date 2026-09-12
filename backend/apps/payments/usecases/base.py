import logging
import uuid
from decimal import Decimal

from celery import current_app
from django.db import transaction as ts

from apps.orders.repo import OrderRepository
from apps.payments.models import PaymentTransaction
from apps.payments.repo import PaymentTransactionRepository
from apps.users.models import User

logger = logging.getLogger(__name__)


class ExpireTransactionCase:
    """
    Expire an active payment transaction when the payment window has elapsed.

    **Business Rules:**
    - Only transactions in PENDING or PARTIALLY_PAID status can be processed.
    - If the transaction has captured funds, transition to WRONG_AMOUNT.
    - If no funds were received, transition to EXPIRED.
    - Update state via repository.

    **Required:**
    - Valid transaction ID.
    """

    def __init__(self, payment_repo: PaymentTransactionRepository) -> None:
        self._payment_repo = payment_repo

    def execute(self, transaction_id: str | uuid.UUID) -> None:
        with ts.atomic():
            transaction = self._payment_repo.get_for_update_by(id=transaction_id)

            if transaction.state not in [PaymentTransaction.Status.PENDING, PaymentTransaction.Status.PARTIALLY_PAID]:
                logger.info(f"Transaction {transaction_id} expiration skipped. Already in state: {transaction.state}.")
                return

            if (
                transaction.state == PaymentTransaction.Status.PARTIALLY_PAID
                or transaction.current_crypto_money.amount > Decimal("0")
            ):
                tx_updates = transaction.mark_as_wrong_amount()
                logger.warning(f"Transaction {transaction_id} expired with captured funds. Marked as WRONG_AMOUNT.")
            else:
                tx_updates = transaction.mark_as_expired()
                logger.info(f"Transaction {transaction_id} successfully marked as EXPIRED.")

            self._payment_repo.save(instance=transaction, update_fields=tx_updates)


class CancelTransactionCase:
    """
    Cancel an active payment transaction initiated by user or system action.

    **Business Rules:**
    - Only transactions in PENDING or PARTIALLY_PAID status can be cancelled.
    - If the transaction has captured funds, transition to WRONG_AMOUNT.
    - If no funds were received, transition to CANCELLED.
    - Revoke associated Celery background task if present.

    **Required:**
    - Valid transaction ID.
    - If a user is provided, the transaction must belong to that user's order.
    """

    def __init__(self, payment_repo: PaymentTransactionRepository) -> None:
        self._payment_repo = payment_repo

    def execute(self, transaction_id: str | uuid.UUID, user: User | None = None) -> None:
        with ts.atomic():
            if user is not None:
                transaction = self._payment_repo.get_for_update_by(id=transaction_id, order__user=user)
            else:
                transaction = self._payment_repo.get_for_update_by(id=transaction_id)

            if transaction.state not in [PaymentTransaction.Status.PENDING, PaymentTransaction.Status.PARTIALLY_PAID]:
                logger.info(
                    f"Transaction {transaction_id} cancellation skipped. Already in state: {transaction.state}."
                )
                return

            if (
                transaction.state == PaymentTransaction.Status.PARTIALLY_PAID
                or transaction.current_crypto_money.amount > Decimal("0")
            ):
                tx_updates = transaction.mark_as_wrong_amount()
                logger.warning(f"Transaction {transaction_id} cancelled with captured funds. Marked as WRONG_AMOUNT.")
            else:
                tx_updates = transaction.mark_as_cancelled()
                logger.info(f"Transaction {transaction_id} successfully marked as CANCELLED.")

            self._payment_repo.save(instance=transaction, update_fields=tx_updates)

            if transaction.task_id:
                current_app.control.revoke(str(transaction.task_id), terminate=True)


class ResolveOverpaymentCase:
    """
    Resolve a transaction that received a wrong amount (overpayment)
    after the admin has manually refunded the excess crypto.

    **Business Rules:**
    - The transaction status must be WRONG_AMOUNT.
    - Change transaction status to PAID.
    - Update the associated Order status to PAID.
    - Revoke any pending expiration tasks.
    - Dispatch fulfillment task strictly on commit to release digital assets.

    **Required:**
    - Transaction must exist and be in WRONG_AMOUNT state.
    """

    def __init__(self, payment_repo: PaymentTransactionRepository, order_repo: OrderRepository) -> None:
        self._payment_repo = payment_repo
        self._order_repo = order_repo

    def execute(self, transaction_id: str | uuid.UUID) -> None:
        with ts.atomic():
            transaction = self._payment_repo.get_for_update_by(id=transaction_id)

            update_fields = transaction.resolve_overpayment()
            self._payment_repo.save(transaction, update_fields=update_fields)

            order = self._order_repo.get_for_update_by(id=transaction.order_id)
            update_fields = order.mark_as_paid()
            self._order_repo.save(order, update_fields=update_fields)

            if order.task_id:
                current_app.control.revoke(str(order.task_id), terminate=True)

            def process_order_fulfillment() -> None:
                current_app.send_task("orders.process_order_fulfillment_task", args=[str(order.id)])

            ts.on_commit(process_order_fulfillment)

            logger.info(f"Transaction {transaction_id} manually resolved to PAID by admin. Fulfillment dispatched.")


class RefundTransactionCase:
    """
    Mark a transaction as completely refunded after the admin
    has manually sent the funds back to the user.

    **Business Rules:**
    - Change transaction status to REFUNDED.
    - Cancel the associated Order.
    - Dispatch order reversion task to release reserved stock.

    **Required:**
    - Transaction must exist and be eligible for refund (PAID, PARTIALLY_PAID, WRONG_AMOUNT).
    """

    def __init__(self, payment_repo: PaymentTransactionRepository, order_repo: OrderRepository) -> None:
        self._payment_repo = payment_repo
        self._order_repo = order_repo

    def execute(self, transaction_id: str | uuid.UUID) -> None:
        with ts.atomic():
            transaction = self._payment_repo.get_for_update_by(id=transaction_id)

            update_fields = transaction.mark_as_refunded()
            self._payment_repo.save(transaction, update_fields=update_fields)

            order = self._order_repo.get_for_update_by(id=transaction.order_id)
            update_fields = order.mark_as_cancelled()
            self._order_repo.save(order, update_fields=update_fields)

            if order.task_id:
                current_app.control.revoke(str(order.task_id), terminate=True)

            def process_order_reversion() -> None:
                current_app.send_task("orders.tasks.process_order_reversion_task", args=[str(order.id), "cancel"])

            ts.on_commit(process_order_reversion)

            logger.info(f"Transaction {transaction_id} marked as REFUNDED by admin. Stock reversion dispatched.")
