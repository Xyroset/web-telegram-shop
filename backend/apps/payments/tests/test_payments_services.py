from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from apps.orders.models import Order
from apps.payments.domain.dto import PaymentTransactionDTO
from apps.payments.domain.exceptions import PaymentUnsupportedCurrencyNetworkError
from apps.payments.domain.services import (
    InvoiceCreationService,
    PaymentProcessingService,
)
from apps.payments.domain.value_objects import CryptoMoney, FiatMoney
from apps.payments.models import PaymentTransaction


class TestInvoiceCreationService:
    """
    Verify business rules for currency network validation and invoice amount calculation.
    """

    @patch("apps.payments.domain.services.shop_config.get")
    def test_validate_currency_network_success(self, mock_shop_config_get: MagicMock) -> None:
        """
        Happy path: Successfully validate when currency and network are supported.
        """
        mock_shop_config_get.return_value = {"accepted_coins": {"usdt": ["trc20", "erc20"]}}
        service = InvoiceCreationService()

        service.validate_currency_network(currency="usdt", network="trc20", provider_name="nowpayments")

        mock_shop_config_get.assert_called_once_with("payments", "payments_settings.providers.nowpayments", {})

    @patch("apps.payments.domain.services.shop_config.get")
    def test_validate_currency_network_fails_on_unsupported_network(self, mock_shop_config_get: MagicMock) -> None:
        """
        Failure: Raise PaymentUnsupportedCurrencyNetworkError if network is not supported.
        """
        mock_shop_config_get.return_value = {"accepted_coins": {"usdt": ["erc20"]}}
        service = InvoiceCreationService()

        with pytest.raises(
            PaymentUnsupportedCurrencyNetworkError,
            match="Network trc20 is not supported for usdt on nowpayments.",
        ):
            service.validate_currency_network(currency="usdt", network="trc20", provider_name="nowpayments")

    @patch("apps.payments.domain.services.shop_config.get")
    def test_calculate_target_amount_with_buyer_fee_markup(self, mock_shop_config_get: MagicMock) -> None:
        """
        Happy path: Apply markup when fee is paid by buyer and native delegation is unsupported.
        """

        def shop_config_side_effect(section: str, key: str, default: object = None) -> object:
            if key == "payments_settings.providers.nowpayments":
                return {
                    "supports_native_fee_delegation": False,
                    "buyer_fee_percent": "1.5",
                }
            if key == "payments_settings.fee_paid_by_buyer":
                return True
            return default

        mock_shop_config_get.side_effect = shop_config_side_effect
        base_fiat = FiatMoney(amount=Decimal("100.00"), currency="USD")
        service = InvoiceCreationService()

        result = service.calculate_target_amount(base_fiat=base_fiat, provider_name="nowpayments")

        assert result.amount == Decimal("101.50")
        assert result.currency == "USD"

    @patch("apps.payments.domain.services.shop_config.get")
    def test_calculate_target_amount_without_markup_when_native_delegation_supported(
        self, mock_shop_config_get: MagicMock
    ) -> None:
        """
        Happy path: Do not apply markup if provider supports native fee delegation.
        """

        def shop_config_side_effect(section: str, key: str, default: object = None) -> object:
            if key == "payments_settings.providers.nowpayments":
                return {
                    "supports_native_fee_delegation": True,
                    "buyer_fee_percent": "1.5",
                }
            if key == "payments_settings.fee_paid_by_buyer":
                return True
            return default

        mock_shop_config_get.side_effect = shop_config_side_effect
        base_fiat = FiatMoney(amount=Decimal("100.00"), currency="USD")
        service = InvoiceCreationService()

        result = service.calculate_target_amount(base_fiat=base_fiat, provider_name="nowpayments")

        assert result.amount == Decimal("100.00")
        assert result.currency == "USD"

    def test_cancel_active_transaction(self) -> None:
        """
        Happy path: Mark active transaction as failed and return updated fields.
        """
        fake_tx = MagicMock(spec=PaymentTransaction)
        fake_tx.mark_as_failed.return_value = ["state", "updated_at"]
        service = InvoiceCreationService()

        updated_fields = service.cancel_active_transaction(active_tx=fake_tx)

        assert updated_fields == ["state", "updated_at"]
        fake_tx.mark_as_failed.assert_called_once()


class TestPaymentProcessingService:
    """
    Verify business rules for webhook payment reconciliation and order/transaction state transitions.
    """

    def test_process_webhook_update_finished_payment_success(self) -> None:
        """
        Happy path: Full payment received marks both transaction and order as PAID.
        """
        fake_tx = MagicMock(spec=PaymentTransaction)
        fake_tx.state = PaymentTransaction.Status.PENDING
        fake_tx.target_crypto_money = CryptoMoney(amount=Decimal("10.00000000"), currency="USDT", network="TRC20")
        fake_tx.current_crypto_money = CryptoMoney(amount=Decimal("0.00000000"), currency="USDT", network="TRC20")
        fake_tx.update_payment.return_value = ["tx_hash"]
        fake_tx.register_funds.return_value = ["current_amount_crypto"]

        def mock_mark_as_paid() -> list[str]:
            fake_tx.state = PaymentTransaction.Status.PAID
            return ["state"]

        fake_tx.mark_as_paid.side_effect = mock_mark_as_paid

        fake_order = MagicMock(spec=Order)
        fake_order.state = Order.Status.PENDING
        fake_order.mark_as_paid.return_value = ["state"]

        dto = PaymentTransactionDTO(tx_hash="0xabc123")
        total_paid = CryptoMoney(amount=Decimal("10.00000000"), currency="USDT", network="TRC20")
        target_amount = CryptoMoney(amount=Decimal("10.00000000"), currency="USDT", network="TRC20")
        service = PaymentProcessingService()

        tx_fields, order_fields = service.process_webhook_update(
            transaction=fake_tx,
            order=fake_order,
            payment_status="finished",
            total_paid=total_paid,
            target_amount=target_amount,
            dto=dto,
        )

        assert "tx_hash" in tx_fields
        assert "current_amount_crypto" in tx_fields
        assert "state" in tx_fields
        assert "state" in order_fields
        fake_tx.update_payment.assert_called_once_with(dto=dto)
        fake_tx.register_funds.assert_called_once_with(received_amount=Decimal("10.00000000"))
        fake_tx.mark_as_paid.assert_called_once()
        fake_order.mark_as_paid.assert_called_once()

    def test_process_webhook_update_updates_target_amount_mismatch(self) -> None:
        """
        Happy path: Update transaction target amount if incoming target amount is different.
        """
        fake_tx = MagicMock(spec=PaymentTransaction)
        fake_tx.state = PaymentTransaction.Status.PENDING
        fake_tx.target_crypto_money = CryptoMoney(amount=Decimal("10.00000000"), currency="USDT", network="TRC20")
        fake_tx.current_crypto_money = CryptoMoney(amount=Decimal("0.00000000"), currency="USDT", network="TRC20")
        fake_tx.update_payment.return_value = []
        fake_tx.register_funds.return_value = []

        def mock_mark_as_paid() -> list[str]:
            fake_tx.state = PaymentTransaction.Status.PAID
            return ["state"]

        fake_tx.mark_as_paid.side_effect = mock_mark_as_paid

        fake_order = MagicMock(spec=Order)
        fake_order.state = Order.Status.PENDING
        fake_order.mark_as_paid.return_value = ["state"]

        dto = PaymentTransactionDTO()
        total_paid = CryptoMoney(amount=Decimal("12.00000000"), currency="USDT", network="TRC20")
        new_target_amount = CryptoMoney(amount=Decimal("12.00000000"), currency="USDT", network="TRC20")
        service = PaymentProcessingService()

        tx_fields, _ = service.process_webhook_update(
            transaction=fake_tx,
            order=fake_order,
            payment_status="finished",
            total_paid=total_paid,
            target_amount=new_target_amount,
            dto=dto,
        )

        assert fake_tx.amount_crypto == Decimal("12.00000000")
        assert "amount_crypto" in tx_fields

    def test_process_webhook_update_refunded_fails_order(self) -> None:
        """
        Happy path: Refunded payment transitions transaction to REFUNDED and order to FAILED.
        """
        fake_tx = MagicMock(spec=PaymentTransaction)
        fake_tx.state = PaymentTransaction.Status.PENDING
        fake_tx.target_crypto_money = CryptoMoney(amount=Decimal("10.00000000"), currency="USDT", network="TRC20")
        fake_tx.current_crypto_money = CryptoMoney(amount=Decimal("10.00000000"), currency="USDT", network="TRC20")
        fake_tx.update_payment.return_value = []
        fake_tx.mark_as_refunded.return_value = ["state"]

        fake_order = MagicMock(spec=Order)
        fake_order.state = Order.Status.PAID
        fake_order.mark_as_failed.return_value = ["state"]

        dto = PaymentTransactionDTO()
        total_paid = CryptoMoney(amount=Decimal("10.00000000"), currency="USDT", network="TRC20")
        target_amount = CryptoMoney(amount=Decimal("10.00000000"), currency="USDT", network="TRC20")
        service = PaymentProcessingService()

        tx_fields, order_fields = service.process_webhook_update(
            transaction=fake_tx,
            order=fake_order,
            payment_status="refunded",
            total_paid=total_paid,
            target_amount=target_amount,
            dto=dto,
        )

        assert "state" in tx_fields
        assert "state" in order_fields
        fake_tx.mark_as_refunded.assert_called_once()
        fake_order.mark_as_failed.assert_called_once()

    def test_process_webhook_update_failed_payment_status(self) -> None:
        """
        Happy path: Gateway 'failed' status marks transaction as failed.
        """
        fake_tx = MagicMock(spec=PaymentTransaction)
        fake_tx.state = PaymentTransaction.Status.PENDING
        fake_tx.target_crypto_money = CryptoMoney(amount=Decimal("10.00000000"), currency="USDT", network="TRC20")
        fake_tx.current_crypto_money = CryptoMoney(amount=Decimal("0.00000000"), currency="USDT", network="TRC20")
        fake_tx.update_payment.return_value = []
        fake_tx.mark_as_failed.return_value = ["state"]

        fake_order = MagicMock(spec=Order)
        fake_order.state = Order.Status.PENDING

        dto = PaymentTransactionDTO()
        total_paid = CryptoMoney(amount=Decimal("0.00000000"), currency="USDT", network="TRC20")
        target_amount = CryptoMoney(amount=Decimal("10.00000000"), currency="USDT", network="TRC20")
        service = PaymentProcessingService()

        tx_fields, _ = service.process_webhook_update(
            transaction=fake_tx,
            order=fake_order,
            payment_status="failed",
            total_paid=total_paid,
            target_amount=target_amount,
            dto=dto,
        )

        assert "state" in tx_fields
        fake_tx.mark_as_failed.assert_called_once()
        fake_order.mark_as_paid.assert_not_called()

    def test_process_webhook_update_expired_payment_status(self) -> None:
        """
        Happy path: Gateway 'expired' status marks transaction as expired.
        """
        fake_tx = MagicMock(spec=PaymentTransaction)
        fake_tx.state = PaymentTransaction.Status.PENDING
        fake_tx.target_crypto_money = CryptoMoney(amount=Decimal("10.00000000"), currency="USDT", network="TRC20")
        fake_tx.current_crypto_money = CryptoMoney(amount=Decimal("0.00000000"), currency="USDT", network="TRC20")
        fake_tx.update_payment.return_value = []
        fake_tx.mark_as_expired.return_value = ["state"]

        fake_order = MagicMock(spec=Order)
        fake_order.state = Order.Status.PENDING

        dto = PaymentTransactionDTO()
        total_paid = CryptoMoney(amount=Decimal("0.00000000"), currency="USDT", network="TRC20")
        target_amount = CryptoMoney(amount=Decimal("10.00000000"), currency="USDT", network="TRC20")
        service = PaymentProcessingService()

        tx_fields, _ = service.process_webhook_update(
            transaction=fake_tx,
            order=fake_order,
            payment_status="expired",
            total_paid=total_paid,
            target_amount=target_amount,
            dto=dto,
        )

        assert "state" in tx_fields
        fake_tx.mark_as_expired.assert_called_once()
