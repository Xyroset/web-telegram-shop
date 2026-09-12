from typing import Any

from django.db.models.query import QuerySet
from django.utils.functional import cached_property
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from rest_framework import status
from rest_framework.generics import ListCreateAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.basket.models import BasketItem
from apps.basket.repo import BasketRepository
from apps.basket.serializers import (
    BasketCalculatePriceResponseSerializer,
    BasketShopUpdateRequestSerializer,
    BasketUpdatePageResponseSerializer,
)
from apps.basket.usecases import (
    BasketCalculateCase,
    BasketCreateUpdateItemCase,
    BasketDeleteItemCase,
)
from apps.catalog.repo import ProductRepository
from apps.orders.repo import PromoCodeRepository
from apps.users.repo import UserRepository


@extend_schema_view(
    get=extend_schema(
        summary="Receive the user's entire basket",
        tags=["Basket"],
        request=None,
        responses={200: BasketUpdatePageResponseSerializer(many=True)},
    ),
    post=extend_schema(
        summary="Update/Create a basket item",
        tags=["Basket"],
        request=BasketShopUpdateRequestSerializer,
        responses={200: None},
    ),
)
class BasketAPIView(ListCreateAPIView):
    """
    Handles retrieval of the user's entire basket and creation/updating of basket items.

    Permissions:
    - Requires an authenticated user.

    Delegation:
    - **GET**: Uses `BasketRepository` to fetch the user's basket items for listing.
    - **POST**: Delegates item creation or quantity updates to `BasketCreateUpdateItemCase`.
    """

    permission_classes = [IsAuthenticated]

    @cached_property
    def _basket_repo(self) -> BasketRepository:
        return BasketRepository()

    @cached_property
    def _basket_update_usecase(self) -> BasketCreateUpdateItemCase:
        return BasketCreateUpdateItemCase(basket_repo=self._basket_repo, product_repo=ProductRepository())

    def get_queryset(self) -> QuerySet[BasketItem]:
        return self._basket_repo.get_basket_queryset(user=self.request.user)

    def get_serializer_class(
        self,
    ) -> type[BasketShopUpdateRequestSerializer] | type[BasketUpdatePageResponseSerializer]:
        if self.request.method == "POST":
            return BasketShopUpdateRequestSerializer
        return BasketUpdatePageResponseSerializer

    def create(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        request_serializer = self.get_serializer(data=request.data)
        request_serializer.is_valid(raise_exception=True)
        valid_data = request_serializer.validated_data

        usecase = self._basket_update_usecase
        usecase.execute(
            user=request.user,
            variant_id=valid_data["variant_id"],
            quantity=valid_data["quantity"],
        )

        return Response(status=status.HTTP_200_OK)


@extend_schema_view(
    delete=extend_schema(
        summary="Delete a basket item",
        responses={204: None},
        tags=["Basket"],
    )
)
class BasketDetailAPIView(APIView):
    """
    Handles deletion of a specific basket item.

    Permissions:
    - Requires an authenticated user.

    Delegation:
    - **DELETE**: Delegates item deletion to `BasketDeleteItemCase` using variant_id.
    """

    permission_classes = [IsAuthenticated]

    @cached_property
    def _delete_item_usecase(self) -> BasketDeleteItemCase:
        return BasketDeleteItemCase(basket_repo=BasketRepository())

    def delete(self, request: Request, variant_id: int, *args: Any, **kwargs: Any) -> Response:
        self._delete_item_usecase.execute(user=request.user, variant_id=variant_id)
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema_view(
    get=extend_schema(
        summary="Receive total price of the user's entire shopping basket",
        tags=["Basket"],
        responses={200: BasketCalculatePriceResponseSerializer},
        parameters=[
            OpenApiParameter(
                name="promocode",
                description="Optional promotional code to apply a discount",
                required=False,
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
            )
        ],
    )
)
class BasketCalculatePriceView(APIView):
    """
    Handles calculating the total price of the user's basket.

    Permissions:
    - Requires an authenticated user.

    Delegation:
    - **GET**: Computes basket totals including promo code discounts using `BasketCalculateCase`.
    """

    permission_classes = [IsAuthenticated]

    @cached_property
    def _calculate_usecase(self) -> BasketCalculateCase:
        return BasketCalculateCase(
            basket_repo=BasketRepository(), user_repo=UserRepository(), promocode_repo=PromoCodeRepository()
        )

    def get(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        promocode = request.query_params.get("promocode")

        raw_response = self._calculate_usecase.execute(user=request.user, code=promocode)

        response_serializer = BasketCalculatePriceResponseSerializer(raw_response)
        return Response(response_serializer.data, status=status.HTTP_200_OK)
