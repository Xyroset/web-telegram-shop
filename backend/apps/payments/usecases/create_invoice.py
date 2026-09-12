import logging
import uuid
from collections.abc import Mapping
from decimal import Decimal

from celery import current_app
from django.db import transaction as ts

from apps.core.config_manager import shop_config
from apps.orders.domain.dto import OrderDTO
from apps.orders.domain.exceptions import OrderStatusInvalidError
from apps.orders.models import Order
from apps.orders.repo import OrderRepository
from apps.payments.domain.dto import InputInvoiceDTO, PaymentTransactionDTO
from apps.payments.domain.exceptions import (
    PaymentConflictDataError,
    PaymentGatewayUnavailableError,
)
from apps.payments.domain.interfaces import PaymentGatewayProtocol
from apps.payments.domain.services import InvoiceCreationService
from apps.payments.domain.value_objects import FiatMoney
from apps.payments.repo import PaymentTransactionRepository
from apps.users.models import User
from apps.users.repo import UserSettingsDataRepository

logger = logging.getLogger(__name__)


class CreateInvoiceCase:
    """
    Create an invoice via an automated payment gateway.

    **Business Rules:**
    - Allows creation of invoices for PENDING orders.
    - Delegates network validation and fee markup calculation to InvoiceCreationService.
    - Cancels any existing active transactions to enforce the "one active invoice" rule.
    - Performs the external network request strictly outside DB transactions.
    - Handles gateway failures gracefully, maintaining a history of failed attempts.

    **Required:**
    - Order must belong to user and be in PENDING status. Otherwise raises **OrderStatusInvalidError**.
    - Order must not be fully paid. Otherwise raises **PaymentConflictDataError**.
    - Selected currency and network must be supported by the provider.
    Otherwise raises **PaymentUnsupportedCurrencyNetworkError**.
    """

    def __init__(
        self,
        payment_repo: PaymentTransactionRepository,
        order_repo: OrderRepository,
        gateway: PaymentGatewayProtocol,
        user_settings_repo: UserSettingsDataRepository,
    ) -> None:
        self._payment_repo = payment_repo
        self._order_repo = order_repo
        self._gateway = gateway
        self._user_settings_repo = user_settings_repo
        self._invoice_service = InvoiceCreationService()

    def execute(self, user: User, dto: InputInvoiceDTO) -> Mapping[str, str]:
        provider_name = str(self._gateway).lower()

        with ts.atomic():
            order = self._order_repo.get_for_update_by(id=dto.order_id, user=user)

            if dto.currency is None or dto.network is None:
                user_settings = self._user_settings_repo.get_by(user=user)
                dto.currency = dto.currency or user_settings.preferred_payment_currency
                dto.network = dto.network or user_settings.preferred_network

            self._invoice_service.validate_currency_network(
                currency=dto.currency, network=dto.network, provider_name=provider_name
            )

            if order.state != Order.Status.PENDING:
                raise OrderStatusInvalidError(f"Cannot create invoice for order in {order.state} state.")

            active_tx = order.get_active_transaction()
            if active_tx:
                active_tx = self._payment_repo.get_for_update_by(id=active_tx.id)
                tx_updates = self._invoice_service.cancel_active_transaction(active_tx=active_tx)
                self._payment_repo.save(instance=active_tx, update_fields=list(tx_updates))
                logger.info(f"Canceled previous active transaction {active_tx.id} for Order {order.id}")

            base_usd_amount = order.get_remaining_usd_balance()
            if base_usd_amount <= Decimal("0.00"):
                raise PaymentConflictDataError("Order is already fully paid. No new invoice needed.")

            base_fiat = FiatMoney(amount=base_usd_amount)

            target_fiat = self._invoice_service.calculate_target_amount(
                base_fiat=base_fiat, provider_name=provider_name
            )

            expire_task_id = uuid.uuid4()
            transaction = self._payment_repo.create(
                order=order,
                payment_currency=dto.currency,
                network=dto.network,
                target_amount_usd=target_fiat.amount,
                task_id=expire_task_id,
            )

        try:
            invoice_dto = self._gateway.create_invoice(
                amount=target_fiat.amount, currency=dto.currency, network=dto.network, order_id=str(dto.order_id)
            )
        except Exception as exc:
            with ts.atomic():
                transaction = self._payment_repo.get_for_update_by(id=transaction.id)
                payment_updated_dto = PaymentTransactionDTO(raw_response={"error": str(exc)})

                payment_updated = transaction.mark_as_failed()
                payment_updated.extend(transaction.update_payment(payment_updated_dto))

                self._payment_repo.save(instance=transaction, update_fields=list(set(payment_updated)))

            raise PaymentGatewayUnavailableError(str(exc)) from exc

        with ts.atomic():
            transaction = self._payment_repo.get_for_update_by(id=transaction.id)
            order = self._order_repo.get_for_update_by(id=dto.order_id)

            raw_response = {"pay_url": invoice_dto.pay_url, "gateway": provider_name}
            payment_updated_dto = PaymentTransactionDTO(invoice_id=invoice_dto.invoice_id, raw_response=raw_response)

            payment_updated = transaction.update_payment(dto=payment_updated_dto)
            self._payment_repo.save(instance=transaction, update_fields=payment_updated)

            order_updated_dto = OrderDTO(payload_url=invoice_dto.pay_url)
            order_updated = order.update_order(dto=order_updated_dto)
            self._order_repo.save(instance=order, update_fields=order_updated)

        invoice_lifetime = shop_config.get("payments", "payments_settings.default_payment_lifetime_minutes", 20)
        countdown_seconds = (invoice_lifetime + 2) * 60

        ts.on_commit(
            lambda: current_app.send_task(
                "payments.expire_transaction",
                args=[str(transaction.id)],
                task_id=str(expire_task_id),
                countdown=countdown_seconds,
            )
        )

        return {"payload_url": invoice_dto.pay_url, "transaction_id": str(transaction.id)}
