import uuid
from typing import Any

from django.db.models.query import QuerySet
from django.utils.functional import cached_property
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import status
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.pagination import TransactionListPagination
from apps.orders.repo import OrderRepository
from apps.payments.domain.dto import InputInvoiceDTO
from apps.payments.gateways.factory import get_payment_gateway
from apps.payments.models import PaymentTransaction
from apps.payments.repo import PaymentTransactionRepository
from apps.payments.serializers import (
    CreateInvoiceRequestSerializer,
    TransactionCreateResponseSerializer,
    TransactionResponseSerializer,
)
from apps.payments.usecases import CancelTransactionCase, CreateInvoiceCase
from apps.users.repo import UserSettingsDataRepository


@extend_schema_view(
    get=extend_schema(
        summary="Receive user's entire list transactions",
        tags=["Payment"],
        request=None,
        responses={200: TransactionResponseSerializer(many=True)},
    ),
)
class GetTransactionsView(ListAPIView):
    """
    Handles retrieval of paginated payment transactions for a specific user's order.

    Permissions:
    - Requires an authenticated user.
    - User can only view transactions associated with their own orders.

    Delegation:
    - **GET**: Uses `PaymentTransactionRepository` to fetch filtered QuerySet for pagination.
    """

    permission_classes = [IsAuthenticated]
    pagination_class = TransactionListPagination
    serializer_class = TransactionResponseSerializer

    @cached_property
    def _payment_repo(self) -> PaymentTransactionRepository:
        return PaymentTransactionRepository()

    def get_queryset(self) -> QuerySet[PaymentTransaction]:
        return self._payment_repo.filter_by(
            order__user=self.request.user,
            order_id=self.kwargs.get("order_id"),
        )


@extend_schema_view(
    post=extend_schema(
        summary="Create a new payment invoice",
        tags=["Payment"],
        request=CreateInvoiceRequestSerializer,
        responses={201: TransactionCreateResponseSerializer},
    ),
)
class CreateTransactionView(APIView):
    """
    Handles payment transaction creation and invoice generation with external gateways.

    Permissions:
    - Requires an authenticated user.

    Delegation:
    - **POST**: Validates input data via `CreateInvoiceRequestSerializer`, resolves gateway,
      and delegates orchestrations to `CreateInvoiceCase`.
    """

    permission_classes = [IsAuthenticated]

    @cached_property
    def _order_repo(self) -> OrderRepository:
        return OrderRepository()

    @cached_property
    def _payment_repo(self) -> PaymentTransactionRepository:
        return PaymentTransactionRepository()

    @cached_property
    def _user_settings_repo(self) -> UserSettingsDataRepository:
        return UserSettingsDataRepository()

    def post(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        request_serializer = CreateInvoiceRequestSerializer(data=request.data)
        request_serializer.is_valid(raise_exception=True)
        validated_data = request_serializer.validated_data

        dto = InputInvoiceDTO(
            order_id=validated_data.get("order_id"),
            currency=validated_data.get("currency"),
            network=validated_data.get("network"),
        )

        gateway = get_payment_gateway(provider_name=validated_data.get("provider_name"))

        usecase = CreateInvoiceCase(
            payment_repo=self._payment_repo,
            order_repo=self._order_repo,
            gateway=gateway,
            user_settings_repo=self._user_settings_repo,
        )

        raw_data = usecase.execute(user=request.user, dto=dto)

        response_serializer = TransactionCreateResponseSerializer(raw_data)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)


@extend_schema_view(
    get=extend_schema(
        summary="Get a transaction",
        tags=["Payment"],
        request=None,
        responses={200: TransactionResponseSerializer},
    ),
    put=extend_schema(
        summary="Cancel user transaction",
        tags=["Payment"],
        request=None,
        responses={200: None},
    ),
)
class TransactionDetailsAPIView(APIView):
    """
    Handles retrieving details and cancellation of a single payment transaction.

    Permissions:
    - Requires an authenticated user.
    - User can only view or cancel transactions associated with their own orders.

    Delegation:
    - **GET**: Uses `PaymentTransactionRepository` to fetch single transaction by ID and user ownership.
    - **PUT**: Delegates transaction cancellation and task revocation to `CancelTransactionCase`.
    """

    permission_classes = [IsAuthenticated]

    @cached_property
    def _payment_repo(self) -> PaymentTransactionRepository:
        return PaymentTransactionRepository()

    @cached_property
    def _cancel_usecase(self) -> CancelTransactionCase:
        return CancelTransactionCase(payment_repo=self._payment_repo)

    def get(self, request: Request, transaction_id: uuid.UUID, *args: Any, **kwargs: Any) -> Response:
        transaction = self._payment_repo.get_by(
            id=str(transaction_id),
            order__user=request.user,
        )

        response_serializer = TransactionResponseSerializer(transaction)
        return Response(response_serializer.data, status=status.HTTP_200_OK)

    def put(self, request: Request, transaction_id: uuid.UUID, *args: Any, **kwargs: Any) -> Response:
        self._cancel_usecase.execute(transaction_id=str(transaction_id), user=request.user)

        return Response(status=status.HTTP_200_OK)
