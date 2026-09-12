from decimal import Decimal
from typing import Any, cast
from unittest.mock import MagicMock, patch

import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.orders.factories import OrderFactory
from apps.orders.models import Order
from apps.payments.domain.dto import InvoiceDTO
from apps.payments.factories import PaymentTransactionFactory
from apps.payments.models import PaymentTransaction
from apps.users.models import User


@pytest.mark.django_db
class TestCreateTransactionView:
    """
    Verify HTTP lifecycle of creating a new payment invoice via CreateTransactionView.
    """

    @patch("apps.core.config_manager.shop_config.get")
    @patch("apps.orders.models.Order.get_remaining_usd_balance", return_value=Decimal("150.00"))
    @patch("apps.payments.usecases.create_invoice.current_app.send_task")
    @patch("apps.payments.views.base.get_payment_gateway")
    def test_create_transaction_success(
        self,
        mock_get_gateway: MagicMock,
        mock_send_task: MagicMock,
        mock_balance: MagicMock,
        mock_shop_config_get: MagicMock,
        api_client: APIClient,
        user: User,
    ) -> None:
        """
        Happy path: Successfully create a transaction and gateway invoice.
        """

        def shop_config_side_effect(section: str, key: str, default: object = None) -> object:
            if "accepted_coins" in key or "providers.nowpayments" in key:
                return {
                    "accepted_coins": {"usdt": ["trc20"]},
                    "supports_native_fee_delegation": True,
                }
            if key == "payments_settings.default_payment_lifetime_minutes":
                return 20
            if key == "payments_settings.fee_paid_by_buyer":
                return False
            return default

        mock_shop_config_get.side_effect = shop_config_side_effect
        mock_gateway = MagicMock()
        cast(MagicMock, mock_gateway.__str__).return_value = "nowpayments"
        fake_invoice = InvoiceDTO(invoice_id="inv_999", pay_url="https://pay.example.com", currency="USDT")
        mock_gateway.create_invoice.return_value = fake_invoice
        mock_get_gateway.return_value = mock_gateway
        order = cast(Order, OrderFactory(user=user, state=Order.Status.PENDING))
        api_client.force_authenticate(user=user)
        url = reverse("create_transaction_api")
        payload = {
            "order_id": str(order.id),
            "currency": "USDT",
            "network": "TRC20",
            "provider_name": "nowpayments",
        }

        response = api_client.post(url, data=payload, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        assert "payload_url" in response.data
        assert PaymentTransaction.objects.filter(order=order).exists()

    def test_unauthorized_access(self, api_client: APIClient) -> None:
        """
        Failure: Unauthenticated user attempts to create a transaction.
        """
        url = reverse("create_transaction_api")
        payload: dict[str, Any] = {}

        response = api_client.post(url, data=payload, format="json")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestGetTransactionsView:
    """
    Verify HTTP lifecycle of retrieving a list of transactions.
    """

    def test_get_transactions_success(self, api_client: APIClient, user: User) -> None:
        """
        Happy path: Retrieve a paginated list of transactions for a specific order.
        """
        order = cast(Order, OrderFactory(user=user))
        PaymentTransactionFactory.create_batch(3, order=order)
        api_client.force_authenticate(user=user)
        url = reverse("reviews_transactions_api", kwargs={"order_id": order.id})

        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data.get("results", response.data)) == 3

    def test_get_transactions_for_other_user_is_empty(self, api_client: APIClient, user: User) -> None:
        """
        Failure (Security): User cannot see transactions from an order belonging to someone else.
        """
        other_order = cast(Order, OrderFactory())
        PaymentTransactionFactory(order=other_order)
        api_client.force_authenticate(user=user)
        url = reverse("reviews_transactions_api", kwargs={"order_id": other_order.id})

        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data.get("results", response.data)) == 0


@pytest.mark.django_db
class TestTransactionDetailsAPIView:
    """
    Verify HTTP lifecycle of retrieving and canceling a specific transaction.
    """

    def test_get_transaction_details_success(self, api_client: APIClient, user: User) -> None:
        """
        Happy path: Retrieve specific transaction details.
        """
        order = cast(Order, OrderFactory(user=user))
        transaction = cast(PaymentTransaction, PaymentTransactionFactory(order=order))
        api_client.force_authenticate(user=user)
        url = reverse("cancel_get_transaction_api", kwargs={"transaction_id": transaction.id})

        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert "state" in response.data

    @patch("apps.payments.usecases.base.current_app.control.revoke")
    def test_cancel_transaction_success(self, mock_revoke: MagicMock, api_client: APIClient, user: User) -> None:
        """
        Happy path: Cancel a pending transaction via PUT request.
        """
        order = cast(Order, OrderFactory(user=user))
        transaction = cast(
            PaymentTransaction,
            PaymentTransactionFactory(
                order=order, state=PaymentTransaction.Status.PENDING, current_amount_crypto=Decimal("0.00")
            ),
        )
        api_client.force_authenticate(user=user)
        url = reverse("cancel_get_transaction_api", kwargs={"transaction_id": transaction.id})

        response = api_client.put(url, data={}, format="json")

        assert response.status_code == status.HTTP_200_OK
        transaction.refresh_from_db()
        assert transaction.state == PaymentTransaction.Status.CANCELLED


@pytest.mark.django_db
class TestNOWPaymentsWebhookView:
    """
    Verify incoming webhook processing for NOWPayments.
    """

    @patch("apps.payments.usecases.process_webhook.current_app.send_task")
    @patch("apps.payments.views.webhooks.get_payment_gateway")
    def test_nowpayments_webhook_success(
        self, mock_get_gateway: MagicMock, mock_send_task: MagicMock, api_client: APIClient
    ) -> None:
        """
        Happy path: Valid webhook payload marks transaction as PAID.
        """
        mock_gateway = MagicMock()
        mock_gateway.verify_webhook.return_value = True
        mock_gateway.normalize_webhook_data.return_value = {
            "invoice_id": "inv_123",
            "payment_status": "finished",
            "actually_paid": "100.00",
            "pay_amount": "100.00",
            "pay_address": "0x123",
            "sender_address": "0xABC",
            "payin_hash": "tx_hash",
        }
        mock_get_gateway.return_value = mock_gateway
        order = cast(Order, OrderFactory())
        transaction = cast(
            PaymentTransaction,
            PaymentTransactionFactory(
                order=order,
                invoice_id="inv_123",
                state=PaymentTransaction.Status.PENDING,
                amount_crypto=Decimal("100.00"),
                current_amount_crypto=Decimal("0.00"),
            ),
        )
        url = reverse("webhook_nowpayments_api")
        headers = {"HTTP_X_NOWPAYMENTS_SIG": "valid_signature"}
        payload = {"invoice_id": "inv_123", "payment_status": "finished"}

        response = api_client.post(url, data=payload, format="json", **headers)

        assert response.status_code == status.HTTP_200_OK
        transaction.refresh_from_db()
        assert transaction.state == PaymentTransaction.Status.PAID

    @patch("apps.payments.views.webhooks.get_payment_gateway")
    def test_nowpayments_webhook_invalid_signature(self, mock_get_gateway: MagicMock, api_client: APIClient) -> None:
        """
        Failure: Webhook with invalid signature returns 400 Bad Request.
        """
        mock_gateway = MagicMock()
        mock_gateway.verify_webhook.return_value = False
        mock_get_gateway.return_value = mock_gateway
        url = reverse("webhook_nowpayments_api")
        headers = {"HTTP_X_NOWPAYMENTS_SIG": "invalid_sig"}
        payload = {"invoice_id": "inv_123"}

        response = api_client.post(url, data=payload, format="json", **headers)

        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestCryptoBotWebhookView:
    """
    Verify incoming webhook processing for CryptoBot.
    """

    @patch("apps.payments.usecases.process_webhook.current_app.send_task")
    @patch("apps.payments.views.webhooks.get_payment_gateway")
    def test_cryptobot_webhook_success(
        self, mock_get_gateway: MagicMock, mock_send_task: MagicMock, api_client: APIClient
    ) -> None:
        """
        Happy path: Valid webhook payload from Crypto Pay marks transaction as PAID.
        """
        mock_gateway = MagicMock()
        mock_gateway.verify_webhook.return_value = True
        mock_gateway.normalize_webhook_data.return_value = {
            "invoice_id": "inv_777",
            "payment_status": "finished",
            "actually_paid": "50.00",
            "pay_amount": "50.00",
            "pay_address": "Internal",
            "sender_address": "User",
            "payin_hash": "tx_777",
        }
        mock_get_gateway.return_value = mock_gateway
        order = cast(Order, OrderFactory())
        transaction = cast(
            PaymentTransaction,
            PaymentTransactionFactory(
                order=order,
                invoice_id="inv_777",
                state=PaymentTransaction.Status.PENDING,
                amount_crypto=Decimal("50.00"),
                current_amount_crypto=Decimal("0.00"),
            ),
        )
        url = reverse("webhook_cryptobot_api")
        headers = {"HTTP_CRYPTO_PAY_API_SIGNATURE": "valid_crypto_sig"}
        payload = {"update_type": "invoice_paid"}

        response = api_client.post(url, data=payload, format="json", **headers)

        assert response.status_code == status.HTTP_200_OK
        transaction.refresh_from_db()
        assert transaction.state == PaymentTransaction.Status.PAID
