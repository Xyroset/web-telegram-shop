from collections.abc import Sequence
from decimal import Decimal

from apps.core.config_manager import shop_config
from apps.orders.models import Order
from apps.payments.domain.dto import PaymentTransactionDTO
from apps.payments.domain.exceptions import PaymentUnsupportedCurrencyNetworkError
from apps.payments.domain.value_objects import CryptoMoney, FiatMoney
from apps.payments.models import PaymentTransaction


class InvoiceCreationService:
    """
    Domain service responsible for validating networks and calculating target
    invoice amounts including potential provider fees.
    """

    def validate_currency_network(self, currency: str, network: str, provider_name: str) -> None:
        provider_config = shop_config.get("payments", f"payments_settings.providers.{provider_name}", {})
        accepted_coins = provider_config.get("accepted_coins", {})
        allowed_networks = accepted_coins.get(currency.lower(), [])

        if network.lower() not in allowed_networks:
            raise PaymentUnsupportedCurrencyNetworkError(
                f"Network {network} is not supported for {currency} on {provider_name}."
            )

    def calculate_target_amount(self, base_fiat: FiatMoney, provider_name: str) -> FiatMoney:
        """
        Calculates the final USD amount to bill the customer, applying markup
        if the shop policy delegates fee payments to the buyer.
        """
        provider_config = shop_config.get("payments", f"payments_settings.providers.{provider_name}", {})
        target_amount_usd = base_fiat.amount

        global_fee_policy = shop_config.get("payments", "payments_settings.fee_paid_by_buyer", True)
        supports_native_delegation = provider_config.get("supports_native_fee_delegation", False)

        if global_fee_policy and not supports_native_delegation:
            buyer_fee_percent = Decimal(str(provider_config.get("buyer_fee_percent", "0.0")))
            markup = base_fiat.amount * (buyer_fee_percent / Decimal("100"))
            target_amount_usd += markup

        return FiatMoney(amount=target_amount_usd)

    def cancel_active_transaction(self, active_tx: PaymentTransaction) -> Sequence[str]:
        """Mutates the active transaction state to FAILED and returns updated fields."""
        return active_tx.mark_as_failed()


class PaymentProcessingService:
    """
    Domain service responsible for resolving the state of a payment transaction
    and its associated order based on incoming webhook data.

    **Business Rules:**
    - Updates transaction details from the provided DTO.
    - Resolves crypto amount mismatches between target and actually paid funds.
    - Transitions transaction and order states based on gateway payment status.
    """

    def process_webhook_update(
        self,
        transaction: PaymentTransaction,
        order: Order,
        payment_status: str,
        total_paid: CryptoMoney,
        target_amount: CryptoMoney,
        dto: PaymentTransactionDTO,
    ) -> tuple[Sequence[str], Sequence[str]]:
        payment_update_fields = transaction.update_payment(dto=dto)
        order_update_fields: list[str] = []

        if target_amount.amount > Decimal("0") and transaction.target_crypto_money.amount != target_amount.amount:
            transaction.amount_crypto = target_amount.amount
            payment_update_fields.append("amount_crypto")

        incremental_amount = total_paid.amount - transaction.current_crypto_money.amount
        if incremental_amount > Decimal("0"):
            payment_update_fields.extend(transaction.register_funds(received_amount=incremental_amount))

        if payment_status == "refunded":
            payment_update_fields.extend(transaction.mark_as_refunded())
            if order.state not in [Order.Status.FAILED, Order.Status.CANCELLED, Order.Status.EXPIRED]:
                order_update_fields.extend(order.mark_as_failed())

        elif transaction.state in [PaymentTransaction.Status.PENDING, PaymentTransaction.Status.PARTIALLY_PAID]:
            if payment_status in ["finished", "confirmed"]:
                payment_update_fields.extend(transaction.mark_as_paid())
                if transaction.current_crypto_money.amount < transaction.target_crypto_money.amount:
                    transaction.current_amount_crypto = transaction.target_crypto_money.amount
                    payment_update_fields.append("current_amount_crypto")

            elif payment_status == "failed":
                payment_update_fields.extend(transaction.mark_as_failed())
            elif payment_status == "expired":
                payment_update_fields.extend(transaction.mark_as_expired())

        if transaction.state == PaymentTransaction.Status.PAID and order.state != Order.Status.PAID:
            order_update_fields.extend(order.mark_as_paid())

        elif transaction.state == PaymentTransaction.Status.WRONG_AMOUNT and order.state != Order.Status.FAILED:
            order_update_fields.extend(order.mark_as_failed())

        return list(set(payment_update_fields)), list(set(order_update_fields))
