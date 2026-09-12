from typing import Any

from django.utils.functional import cached_property
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import status
from rest_framework.generics import RetrieveAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.basket.repo import BasketRepository
from apps.delivery.config import get_active_pricing_strategy
from apps.delivery.models import Delivery
from apps.delivery.repo import DeliveryRepository
from apps.delivery.serializers import (
    DeliveryDataResponse,
    DeliveryEstimateRequestSerializer,
    DeliveryEstimateResponseSerializer,
)
from apps.delivery.usecases import CalculateDeliveryEstimateCase
from apps.users.repo import UserDeliveryDataRepository


@extend_schema_view(
    get=extend_schema(
        parameters=[DeliveryEstimateRequestSerializer],
        responses={200: DeliveryEstimateResponseSerializer},
        summary="Calculate Delivery Estimate",
        tags=["Delivery"],
    )
)
class DeliveryEstimateView(APIView):
    """
    API View to retrieve estimated delivery costs and gamification thresholds.

    Permissions:
    - Requires an authenticated user.

    Delegation:
    - GET: Validates query parameters using `DeliveryEstimateRequestSerializer`,
      delegates calculation to `CalculateDeliveryEstimateCase`,
      and serializes the result with `DeliveryEstimateResponseSerializer`.
    """

    permission_classes = [IsAuthenticated]

    @cached_property
    def _calculate_delivery_usecase(self) -> CalculateDeliveryEstimateCase:
        return CalculateDeliveryEstimateCase(
            strategy=get_active_pricing_strategy(),
            basket_repo=BasketRepository(),
            user_delivery_data_repo=UserDeliveryDataRepository(),
        )

    def get(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        request_serializer = DeliveryEstimateRequestSerializer(data=request.query_params)
        request_serializer.is_valid(raise_exception=True)

        validated_data = request_serializer.validated_data
        destination_code = validated_data.get("destination_code")
        region_code = validated_data.get("region_code")

        result_dto = self._calculate_delivery_usecase.execute(
            user=request.user,
            destination_code=destination_code,
            region_code=region_code,
        )

        response_serializer = DeliveryEstimateResponseSerializer(instance=result_dto)
        return Response(response_serializer.data, status=status.HTTP_200_OK)


@extend_schema_view(
    get=extend_schema(
        summary="Get delivery data on order id",
        tags=["Delivery"],
        request=None,
        responses={200: DeliveryDataResponse},
    )
)
class GetDeliveryView(RetrieveAPIView):
    """
    API View to retrieve delivery details for a specific order.

    Permissions:
    - Requires an authenticated user.
    - User can only access delivery data associated with their own order.

    Delegation:
    - GET: Fetches delivery details directly via `DeliveryRepository` using `order_id` and `user`.
    """

    permission_classes = [IsAuthenticated]
    serializer_class = DeliveryDataResponse

    @cached_property
    def _delivery_repo(self) -> DeliveryRepository:
        return DeliveryRepository()

    def get_object(self) -> Delivery:
        return self._delivery_repo.get_by(
            order__user=self.request.user,
            order_id=self.kwargs.get("order_id"),
        )
