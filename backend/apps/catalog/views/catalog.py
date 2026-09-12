from typing import Any, cast

from django.utils.functional import cached_property
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated

from apps.basket.repo import BasketRepository
from apps.catalog.filters import ProductFilter
from apps.catalog.repo import FavoriteItemRepository, ProductRepository
from apps.catalog.serializers import (
    ProductSuggestionResponseSerializer,
    ProductVariantDetailSerializer,
    ShopProductListResponseSerializer,
)
from apps.catalog.serializers.common import CategorySerializer, TagSerializer
from apps.core.pagination import ProductListPagination


@extend_schema_view(
    get=extend_schema(
        summary="Get product catalog",
        tags=["Catalog"],
        parameters=[
            OpenApiParameter(
                name="strict_search",
                type=OpenApiTypes.BOOL,
                location=OpenApiParameter.QUERY,
                description="If true, disables Trigram fuzzy matching and uses exact/partial substring search only.",
                required=False,
            )
        ],
        responses={200: ShopProductListResponseSerializer(many=True)},
    )
)
class GetProductsAPIView(ListAPIView):
    """
    API View for fetching the product catalog.

    Permissions:
    - Requires an authenticated user.

    Delegation:
    - **GET**: Delegates data fetching to `ProductRepository` and uses `FavoriteItemRepository` for serializer context.
    """

    permission_classes = [IsAuthenticated]
    serializer_class = ShopProductListResponseSerializer
    pagination_class = ProductListPagination

    filter_backends = [DjangoFilterBackend]
    filterset_class = ProductFilter

    @cached_property
    def _product_repo(self) -> ProductRepository:
        return ProductRepository()

    @cached_property
    def _favorite_item_repo(self) -> FavoriteItemRepository:
        return FavoriteItemRepository()

    def get_queryset(self) -> Any:
        return self._product_repo.get_shop_products_list()

    def get_serializer_context(self) -> dict[str, Any]:
        context = cast(dict[str, Any], super().get_serializer_context())
        if self.request.user.is_authenticated:
            context["user_favorites"] = self._favorite_item_repo.get_favorites_mapping(user=self.request.user)
        else:
            context["user_favorites"] = {}
        return context


@extend_schema_view(
    get=extend_schema(
        summary="Get all variants for a specific product",
        tags=["Catalog"],
        responses={200: ProductVariantDetailSerializer(many=True)},
    )
)
class GetProductVariantsAPIView(ListAPIView):
    """
    API View for fetching product variants.

    Permissions:
    - Requires an authenticated user.

    Delegation:
    - **GET**: Delegates to `ProductRepository` to fetch variants and `BasketRepository` to enrich context.
    """

    permission_classes = [IsAuthenticated]
    serializer_class = ProductVariantDetailSerializer
    pagination_class = None

    @cached_property
    def _product_repo(self) -> ProductRepository:
        return ProductRepository()

    @cached_property
    def _basket_repo(self) -> BasketRepository:
        return BasketRepository()

    def get_queryset(self) -> Any:
        product_id = self.kwargs.get("product_id")
        return self._product_repo.get_product_variants(product_id=product_id)

    def get_serializer_context(self) -> dict[str, Any]:
        context = cast(dict[str, Any], super().get_serializer_context())
        if self.request.user.is_authenticated:
            context["user_basket"] = self._basket_repo.get_basket_mapping(user=self.request.user)
        else:
            context["user_basket"] = {}
        return context


@extend_schema_view(
    get=extend_schema(
        summary="Get all categories", tags=["Catalog"], request=None, responses={200: CategorySerializer(many=True)}
    )
)
class GetCategoriesView(ListAPIView):
    """
    API View for fetching categories.

    Permissions:
    - Requires an authenticated user.

    Delegation:
    - **GET**: Delegates to `ProductRepository`.
    """

    permission_classes = [IsAuthenticated]
    serializer_class = CategorySerializer

    @cached_property
    def _product_repo(self) -> ProductRepository:
        return ProductRepository()

    def get_queryset(self) -> Any:
        return self._product_repo.get_all_categories()


@extend_schema_view(
    get=extend_schema(summary="Get all tags", tags=["Catalog"], request=None, responses={200: TagSerializer(many=True)})
)
class GetTagsView(ListAPIView):
    """
    API View for fetching tags.

    Permissions:
    - Requires an authenticated user.

    Delegation:
    - **GET**: Delegates to `ProductRepository`.
    """

    permission_classes = [IsAuthenticated]
    serializer_class = TagSerializer

    @cached_property
    def _product_repo(self) -> ProductRepository:
        return ProductRepository()

    def get_queryset(self) -> Any:
        return self._product_repo.get_all_tags()


@extend_schema_view(
    get=extend_schema(
        summary="Get search autocomplete suggestions",
        tags=["Catalog"],
        parameters=[
            OpenApiParameter(
                name="search",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description="Search term for autocomplete suggestions.",
                required=True,
            ),
            OpenApiParameter(
                name="limit",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description="Maximum number of suggestions to return (default: 5).",
                required=False,
            ),
        ],
        responses={200: ProductSuggestionResponseSerializer(many=True)},
    )
)
class SearchSuggestionsView(ListAPIView):
    """
    API View for fetching fast autocomplete search suggestions.

    Permissions:
    - Requires an authenticated user.

    Delegation:
    - **GET**: Delegates to `ProductRepository`'s hybrid search logic.
    """

    permission_classes = [IsAuthenticated]
    serializer_class = ProductSuggestionResponseSerializer
    pagination_class = None

    @cached_property
    def _product_repo(self) -> ProductRepository:
        return ProductRepository()

    def get_queryset(self) -> Any:
        search_term = self.request.query_params.get("search", "").strip()
        try:
            limit = int(self.request.query_params.get("limit", 5))
            limit = min(limit, 20)
        except ValueError:
            limit = 5
        return self._product_repo.get_search_suggestions(search_term=search_term, limit=limit)
