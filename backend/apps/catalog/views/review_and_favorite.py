import uuid
from typing import Any

from django.utils.functional import cached_property
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import status
from rest_framework.generics import ListAPIView
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.catalog.domain.dto import CreateReviewDTO
from apps.catalog.repo import FavoriteItemRepository, ProductRepository, ReviewRepository
from apps.catalog.serializers import (
    ReviewCreateRequestSerializer,
    ReviewSerializer,
    ReviewUpdateRequestSerializer,
)
from apps.catalog.usecases import (
    CreateFavoriteItemCase,
    CreateReviewCase,
    DeleteFavoriteItemCase,
    DeleteReviewCase,
    GetReviewsCase,
    UpdateReviewCase,
)
from apps.core.pagination import ReviewListPagination
from apps.orders.repo import OrderRepository


@extend_schema_view(
    post=extend_schema(
        summary="Add a product in user favorites",
        tags=["Favorite"],
        request=None,
        responses={200: None},
    ),
    delete=extend_schema(
        summary="Delete a product in user favorites",
        tags=["Favorite"],
        request=None,
        responses={204: None},
    ),
)
class FavoriteItemAPIView(APIView):
    """
    API View for managing user's favorite products.

    Permissions:
    - Requires an authenticated user.

    Delegation:
    - **POST**: Delegates creation to `CreateFavoriteItemCase`.
    - **DELETE**: Delegates deletion to `DeleteFavoriteItemCase`.
    """

    permission_classes = [IsAuthenticated]

    @cached_property
    def _favorite_item_repo(self) -> FavoriteItemRepository:
        return FavoriteItemRepository()

    @cached_property
    def _create_usecase(self) -> CreateFavoriteItemCase:
        return CreateFavoriteItemCase(favorite_item_repo=self._favorite_item_repo, product_repo=ProductRepository())

    @cached_property
    def _delete_usecase(self) -> DeleteFavoriteItemCase:
        return DeleteFavoriteItemCase(favorite_item_repo=self._favorite_item_repo)

    def post(self, request: Request, product_id: int, *args: Any, **kwargs: Any) -> Response:
        self._create_usecase.execute(user=request.user, product_id=product_id)
        return Response(status=status.HTTP_200_OK)

    def delete(self, request: Request, product_id: int, *args: Any, **kwargs: Any) -> Response:
        self._delete_usecase.execute(user=request.user, product_id=product_id)
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema_view(
    get=extend_schema(
        summary="Get reviews", tags=["Review"], request=None, responses={200: ReviewSerializer(many=True)}
    )
)
class GetReviewsAPIView(ListAPIView):
    """
    API View for fetching product reviews.

    Permissions:
    - Requires an authenticated user.

    Delegation:
    - **GET**: Delegates query construction to `GetReviewsCase`.
    """

    permission_classes = [IsAuthenticated]
    serializer_class = ReviewSerializer
    pagination_class = ReviewListPagination

    @cached_property
    def _get_usecase(self) -> GetReviewsCase:
        return GetReviewsCase(review_repo=ReviewRepository(), product_repo=ProductRepository())

    def get_queryset(self) -> Any:
        return self._get_usecase.execute(user=self.request.user, product_id=self.kwargs.get("product_id"))


@extend_schema_view(
    post=extend_schema(
        summary="Create a new review",
        tags=["Review"],
        request={"multipart/form-data": ReviewCreateRequestSerializer},
        responses={201: None},
    )
)
class CreateReviewAPIView(APIView):
    """
    API View for creating a product review.

    Permissions:
    - Requires an authenticated user.

    Delegation:
    - **POST**: Validates multipart data via serializer, delegates business rules to `CreateReviewCase`.
    """

    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    @cached_property
    def _create_usecase(self) -> CreateReviewCase:
        return CreateReviewCase(
            review_repo=ReviewRepository(), product_repo=ProductRepository(), order_repo=OrderRepository()
        )

    def post(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        request_serializer = ReviewCreateRequestSerializer(data=request.data)
        request_serializer.is_valid(raise_exception=True)
        validated_data = request_serializer.validated_data

        dto = CreateReviewDTO(
            product_id=validated_data.get("product_id"),
            rating=validated_data.get("rating"),
            text=validated_data.get("text", ""),
            is_anonymous=validated_data.get("is_anonymous", False),
            photos=validated_data.get("photos"),
        )
        self._create_usecase.execute(user=request.user, dto=dto)

        return Response(status=status.HTTP_201_CREATED)


@extend_schema_view(
    put=extend_schema(
        summary="Update an old review",
        tags=["Review"],
        request=ReviewUpdateRequestSerializer,
        responses={200: None},
    ),
    delete=extend_schema(
        summary="Delete a review",
        tags=["Review"],
        request=None,
        responses={204: None},
    ),
)
class ReviewDetailAPIView(APIView):
    """
    API View for updating or deleting a product review.

    Permissions:
    - Requires an authenticated user.

    Delegation:
    - **PUT**: Validates payload, delegates to `UpdateReviewCase`.
    - **DELETE**: Delegates to `DeleteReviewCase`.
    """

    permission_classes = [IsAuthenticated]

    @cached_property
    def _review_repo(self) -> ReviewRepository:
        return ReviewRepository()

    @cached_property
    def _update_usecase(self) -> UpdateReviewCase:
        return UpdateReviewCase(review_repo=self._review_repo)

    @cached_property
    def _delete_usecase(self) -> DeleteReviewCase:
        return DeleteReviewCase(review_repo=self._review_repo)

    def put(self, request: Request, id: uuid.UUID, *args: Any, **kwargs: Any) -> Response:
        request_serializer = ReviewUpdateRequestSerializer(data=request.data)
        request_serializer.is_valid(raise_exception=True)
        validated_data = request_serializer.validated_data

        self._update_usecase.execute(
            user=request.user,
            review_id=id,
            rating=validated_data.get("rating"),
            text=validated_data.get("text"),
        )
        return Response(status=status.HTTP_200_OK)

    def delete(self, request: Request, id: uuid.UUID, *args: Any, **kwargs: Any) -> Response:
        self._delete_usecase.execute(user=request.user, review_id=id)
        return Response(status=status.HTTP_204_NO_CONTENT)
