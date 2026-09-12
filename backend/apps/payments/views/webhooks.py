import logging
from typing import Any

from django.utils.functional import cached_property
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.serializers import BaseResponseSerializer
from apps.orders.repo import OrderRepository
from apps.payments.gateways.factory import get_payment_gateway
from apps.payments.repo import PaymentTransactionRepository
from apps.payments.usecases import ProcessWebhookCase

logger = logging.getLogger(__name__)


@extend_schema_view(
    post=extend_schema(
        summary="Webhook for gateway nowpayments",
        tags=["Webhook", "Payment Providers"],
        request=None,
        responses={200: BaseResponseSerializer},
    )
)
class NOWPaymentsWebhookView(APIView):
    """
    Handles incoming payment status updates from the NOWPayments webhook.

    Permissions:
    - Allows any user (AllowAny). Signature validation is handled internally by the gateway.

    Delegation:
    - **POST**: Delegates webhook signature verification, state mutation, and side-effects to `ProcessWebhookCase`.
    """

    permission_classes = [AllowAny]
    authentication_classes = []  # type: ignore[var-annotated]

    @cached_property
    def _webhook_usecase(self) -> ProcessWebhookCase:
        return ProcessWebhookCase(
            order_repo=OrderRepository(),
            payment_repo=PaymentTransactionRepository(),
            gateway=get_payment_gateway(provider_name="nowpayments"),
        )

    def post(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        signature = request.headers.get("x-nowpayments-sig", "")

        try:
            self._webhook_usecase.execute(payload=request.data, signature=signature)
            return Response({"message": "Ok"}, status=status.HTTP_200_OK)
        except Exception as exc:
            logger.warning(f"NOWPayments webhook processing failed: {exc}")
            return Response({"message": str(exc)}, status=status.HTTP_400_BAD_REQUEST)


@extend_schema_view(
    post=extend_schema(
        summary="Webhook for gateway CryptoBot",
        tags=["Webhook", "Payment Providers"],
        request=None,
        responses={200: BaseResponseSerializer},
    )
)
class CryptoBotWebhookView(APIView):
    """
    Handles incoming payment status updates from the CryptoBot (Crypto Pay) webhook.

    Permissions:
    - Allows any user (AllowAny). Signature validation is handled internally by the gateway.

    Delegation:
    - **POST**: Delegates webhook signature verification, state mutation, and side-effects to `ProcessWebhookCase`.
    """

    permission_classes = [AllowAny]
    authentication_classes = []  # type: ignore[var-annotated]

    @cached_property
    def _webhook_usecase(self) -> ProcessWebhookCase:
        return ProcessWebhookCase(
            order_repo=OrderRepository(),
            payment_repo=PaymentTransactionRepository(),
            gateway=get_payment_gateway(provider_name="cryptobot"),
        )

    def post(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        signature = request.headers.get("crypto-pay-api-signature", "")

        try:
            self._webhook_usecase.execute(payload=request.data, signature=signature)
            return Response({"message": "Ok"}, status=status.HTTP_200_OK)
        except Exception as exc:
            logger.warning(f"CryptoBot webhook processing failed: {exc}")
            return Response({"message": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
