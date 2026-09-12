import logging
import uuid
from collections.abc import Mapping
from decimal import Decimal
from typing import Any

from celery import current_app
from django.db import transaction as ts

from apps.orders.repo import OrderRepository
from apps.payments.domain.dto import PaymentTransactionDTO
from apps.payments.domain.exceptions import PaymentGatewayBadRequestError
from apps.payments.domain.interfaces import PaymentGatewayProtocol
from apps.payments.domain.services import PaymentProcessingService
from apps.payments.domain.value_objects import CryptoMoney
from apps.payments.models import PaymentTransaction
from apps.payments.repo import PaymentTransactionRepository

logger = logging.getLogger(__name__)


class ProcessWebhookCase:
    """
    Process incoming webhooks from payment gateways.

    **Business Rules:**
    - Verifies the webhook signature using the specific gateway implementation.
    - Delegates complex state transitions to PaymentProcessingService.
    - Persists mutated state strictly within an atomic transaction.
    - Orchestrates side-effects (Fulfillment or Admin Alerts) via Celery tasks on commit.

    **Required:**
    - The webhook signature must be valid. Otherwise error — **PaymentGatewayBadRequestError**.
    """

    def __init__(
        self,
        order_repo: OrderRepository,
        payment_repo: PaymentTransactionRepository,
        gateway: PaymentGatewayProtocol,
    ) -> None:
        self._order_repo = order_repo
        self._payment_repo = payment_repo
        self._gateway = gateway
        self._payment_service = PaymentProcessingService()

    def execute(self, payload: Mapping[str, Any], signature: str) -> None:
        if not self._gateway.verify_webhook(payload=payload, signature=signature):
            logger.error("Invalid webhook signature!")
            raise PaymentGatewayBadRequestError()

        normalized_data = self._gateway.normalize_webhook_data(payload=payload)
        invoice_id = normalized_data["invoice_id"]
        payment_status = normalized_data["payment_status"]

        logger.info(f"Received webhook for Invoice: {invoice_id}, Status: {payment_status}")

        with ts.atomic():
            transaction = self._payment_repo.get_for_update_by(invoice_id=invoice_id)
            order = self._order_repo.get_for_update_by(id=transaction.order.id)

            total_paid_vo = CryptoMoney(
                amount=Decimal(normalized_data["actually_paid"]),
                currency=transaction.payment_currency,
                network=transaction.network,
            )
            target_amount_vo = CryptoMoney(
                amount=Decimal(normalized_data["pay_amount"]),
                currency=transaction.payment_currency,
                network=transaction.network,
            )

            dto = PaymentTransactionDTO(
                invoice_id=normalized_data["invoice_id"] or transaction.invoice_id,
                receiver_address=normalized_data["pay_address"] or transaction.receiver_address,
                sender_address=normalized_data["sender_address"] or transaction.sender_address,
                tx_hash=normalized_data["payin_hash"] or transaction.tx_hash,
                raw_response=dict(payload),
            )

            payment_update_fields, order_update_fields = self._payment_service.process_webhook_update(
                transaction=transaction,
                order=order,
                payment_status=payment_status,
                total_paid=total_paid_vo,
                target_amount=target_amount_vo,
                dto=dto,
            )

            if payment_update_fields:
                self._payment_repo.save(transaction, update_fields=payment_update_fields)
            if order_update_fields:
                self._order_repo.save(order, update_fields=order_update_fields)

            self._dispatch_side_effects(
                transaction=transaction,
                order_id=order.id,
                task_id=order.task_id,
            )

    def _dispatch_side_effects(
        self,
        transaction: PaymentTransaction,
        order_id: str | uuid.UUID,
        task_id: str | uuid.UUID | None,
    ) -> None:
        """
        Internal helper to schedule Celery tasks based on the resolved transaction state.
        Executes strictly on successful transaction commit.
        """
        if transaction.state == PaymentTransaction.Status.PAID:
            if task_id:
                current_app.control.revoke(str(task_id), terminate=True)

            def process_order_fulfillment() -> None:
                current_app.send_task("orders.process_order_fulfillment_task", args=[str(order_id)])

            ts.on_commit(process_order_fulfillment)
            logger.info(f"Order {order_id} marked as PAID. Fulfillment task scheduled.")

        elif transaction.state == PaymentTransaction.Status.WRONG_AMOUNT:
            if task_id:
                current_app.control.revoke(str(task_id), terminate=True)

            def dispatch_admin() -> None:
                current_app.send_task(
                    "notifications.dispatch_admin_stuck_funds_transaction_notifications",
                    args=[str(transaction.id)],
                )

            ts.on_commit(dispatch_admin)
            logger.warning(f"Transaction {transaction.id} got WRONG_AMOUNT. Order {order_id} flagged FAILED.")
