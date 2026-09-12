import uuid
from typing import Any

from django.db.models.query import QuerySet
from django.utils.functional import cached_property
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import status
from rest_framework.generics import ListCreateAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.basket.repo import BasketRepository
from apps.catalog.repo import DigitalAssetRepository, ProductRepository
from apps.core.pagination import OrderListPagination
from apps.delivery.config import get_active_pricing_strategy
from apps.delivery.repo import DeliveryRepository
from apps.orders import serializers
from apps.orders.models import Order
from apps.orders.repo import OrderRepository, PromoCodeRepository
from apps.orders.usecases.cancellation import CancelOrderCase
from apps.orders.usecases.creation import CreateOrderCase
from apps.payments.repo import PaymentTransactionRepository
from apps.users.repo import UserDeliveryDataRepository, UserRepository


@extend_schema_view(
    get=extend_schema(
        summary="Receive user's entire list orders",
        tags=["Order"],
        request=None,
        responses={200: serializers.OrderResponseSerializer(many=True)},
    ),
    post=extend_schema(
        summary="Create a new user order from user basket",
        tags=["Order"],
        request=serializers.OrderCreateRequestSerializer,
        responses={201: serializers.OrderCreateResponseSerializer},
    ),
)
class OrderAPIView(ListCreateAPIView):
    """
    Handles listing of user's orders and creation of new orders.

    Permissions:
    - Requires an authenticated user.
    - User can only access or modify their own orders (Ownership check).

    Delegation:
    - **GET**: Uses `OrderRepository` to fetch the user's order queryset for pagination.
    - **POST**: Delegates order creation, product reservation, and invoice generation to `CreateOrderCase`
    """

    permission_classes = [IsAuthenticated]
    pagination_class = OrderListPagination

    @cached_property
    def _order_repo(self) -> OrderRepository:
        return OrderRepository()

    @cached_property
    def _create_usecase(self) -> CreateOrderCase:
        return CreateOrderCase(
            order_repo=self._order_repo,
            user_repo=UserRepository(),
            user_delivery_data_repo=UserDeliveryDataRepository(),
            basket_repo=BasketRepository(),
            promocode_repo=PromoCodeRepository(),
            delivery_repo=DeliveryRepository(),
            product_repo=ProductRepository(),
            digital_asset_repo=DigitalAssetRepository(),
            shipping_strategy=get_active_pricing_strategy(),
        )

    def get_queryset(self) -> QuerySet[Order]:
        return self._order_repo.get_orders_queryset(user=self.request.user)

    def get_serializer_class(
        self,
    ) -> type[serializers.OrderCreateRequestSerializer] | type[serializers.OrderResponseSerializer]:
        if self.request.method == "POST":
            return serializers.OrderCreateRequestSerializer
        return serializers.OrderResponseSerializer

    def create(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        request_serializer = self.get_serializer(data=request.data)
        request_serializer.is_valid(raise_exception=True)
        validated_data = request_serializer.validated_data

        order_id = self._create_usecase.execute(
            user=request.user,
            code=validated_data.get("code"),
            delivery_data=validated_data.get("delivery_data"),
        )

        response_serializer = serializers.OrderCreateResponseSerializer({"order_id": order_id})
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)


@extend_schema_view(
    get=extend_schema(
        summary="Get an order",
        tags=["Order"],
        request=None,
        responses={200: serializers.OrderResponseSerializer},
    ),
    put=extend_schema(summary="Cancel an order", tags=["Order"], request=None, responses={200: None}),
)
class OrderDetailAPIView(APIView):
    """
    Handles retrieval and cancellation of a specific order.

    Permissions:
    - Requires an authenticated user.

    Delegation:
    - **GET**: Fetches a single order directly via `OrderRepository`
    - **PATCH**: Delegates the cancellation process (and side effects) to `CancelOrderCase`.
    """

    permission_classes = [IsAuthenticated]

    @cached_property
    def _order_repo(self) -> OrderRepository:
        return OrderRepository()

    @cached_property
    def _cancel_usecase(self) -> CancelOrderCase:
        return CancelOrderCase(
            order_repo=self._order_repo,
            user_repo=UserRepository(),
            delivery_repo=DeliveryRepository(),
            payment_repo=PaymentTransactionRepository(),
            promocode_repo=PromoCodeRepository(),
            product_repo=ProductRepository(),
            digital_asset_repo=DigitalAssetRepository(),
        )

    def get(self, request: Request, order_id: uuid.UUID, *args: Any, **kwargs: Any) -> Response:
        order = self._order_repo.get_order_with_full_details(order_id=order_id, user=request.user)

        response_serializer = serializers.OrderResponseSerializer(order)
        return Response(response_serializer.data, status=status.HTTP_200_OK)

    def put(self, request: Request, order_id: uuid.UUID, *args: Any, **kwargs: Any) -> Response:
        self._cancel_usecase.execute(order_id=order_id, user=request.user)

        return Response(status=status.HTTP_200_OK)
