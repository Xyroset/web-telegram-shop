from datetime import timedelta
from typing import Any

import django_filters
from django.db.models import Q, QuerySet
from django.utils import timezone
from django.utils.functional import cached_property

from apps.catalog.models import Product
from apps.catalog.repo import FavoriteItemRepository, ProductRepository


class ProductFilter(django_filters.FilterSet):
    """
    FilterSet for Product catalog.
    Handles parameter parsing and delegates DB logic to Repositories.
    """

    ordering = django_filters.OrderingFilter(
        fields=(
            ("created_at", "date"),
            ("min_variant_price", "price"),
            ("name", "name"),
        ),
        field_labels={
            "date": "Sort by creation date",
            "price": "Sort by price",
            "name": "Sort alphabetically",
        },
    )

    category = django_filters.CharFilter(method="filter_categories")
    tag = django_filters.CharFilter(method="filter_tags")

    min_price = django_filters.NumberFilter(field_name="variants__price", lookup_expr="gte")
    max_price = django_filters.NumberFilter(field_name="variants__price", lookup_expr="lte")

    search = django_filters.CharFilter(method="filter_search")
    is_favorite = django_filters.BooleanFilter(method="filter_is_favorite")
    is_new = django_filters.BooleanFilter(method="filter_is_new")
    in_stock = django_filters.BooleanFilter(method="filter_in_stock")
    is_promotion = django_filters.BooleanFilter(method="filter_is_promotion")
    min_discount = django_filters.NumberFilter(method="filter_min_discount")
    min_rating = django_filters.NumberFilter(method="filter_min_rating")
    product_type = django_filters.ChoiceFilter(choices=Product.Type.choices)

    class Meta:
        model = Product
        fields = ["category", "tag", "min_price", "max_price", "product_type"]

    @cached_property
    def _product_repo(self) -> ProductRepository:
        return ProductRepository()

    @cached_property
    def _favorite_repo(self) -> FavoriteItemRepository:
        return FavoriteItemRepository()

    def filter_categories(self, queryset: QuerySet[Product], name: str, value: str) -> QuerySet[Product]:
        categories = [c.strip() for c in value.split(",") if c.strip()]
        if not categories:
            return queryset

        q = Q()
        for cat in categories:
            q |= Q(category__slug__iexact=cat)
        return queryset.filter(q)

    def filter_tags(self, queryset: QuerySet[Product], name: str, value: str) -> QuerySet[Product]:
        tags = [t.strip() for t in value.split(",") if t.strip()]
        if not tags:
            return queryset

        q = Q()
        for tag_name in tags:
            q |= Q(variants__tags__slug__iexact=tag_name)
        return queryset.filter(q).distinct()

    def filter_min_rating(self, queryset: QuerySet[Product], name: str, value: float) -> QuerySet[Product]:
        if value:
            return self._product_repo.filter_min_rating(queryset, value)
        return queryset

    def filter_strict_search(self, queryset: QuerySet[Product], name: str, value: bool) -> QuerySet[Product]:
        return queryset

    def filter_search(self, queryset: QuerySet[Product], name: str, value: str) -> QuerySet[Product]:
        is_strict = str(self.data.get("strict_search", "false")).lower() in ("true", "1")
        return self._product_repo.filter_by_search_term(queryset, value, is_strict=is_strict)

    def filter_is_favorite(self, queryset: QuerySet[Product], name: str, value: bool) -> QuerySet[Product]:
        request = getattr(self, "request", None)
        if value and request and request.user.is_authenticated:
            user_favorites_mapping = self._favorite_repo.get_favorites_mapping(user=request.user)
            favorite_product_ids = [pid for pid, is_fav in user_favorites_mapping.items() if is_fav]
            return queryset.filter(id__in=favorite_product_ids)
        return queryset

    def filter_is_new(self, queryset: QuerySet[Product], name: str, value: bool) -> QuerySet[Product]:
        if value:
            seven_days_ago = timezone.now() - timedelta(days=7)
            return queryset.filter(created_at__gte=seven_days_ago)
        return queryset

    def filter_in_stock(self, queryset: QuerySet[Product], name: str, value: bool) -> QuerySet[Product]:
        if value:
            return queryset.filter(variants__available_stock__gt=0).distinct()
        return queryset

    def filter_is_promotion(self, queryset: QuerySet[Product], name: str, value: bool) -> QuerySet[Product]:
        if value:
            return self._product_repo.filter_is_promotion(queryset)
        return queryset

    def filter_min_discount(self, queryset: QuerySet[Product], name: str, value: int | float) -> QuerySet[Product]:
        if value:
            return self._product_repo.filter_min_discount(queryset, value)
        return queryset

    @property
    def qs(self) -> QuerySet[Product]:
        """
        Overrides default queryset property to inject dynamic variant prefetching
        based on active filters, ensuring the display variant matches user search.
        """
        queryset = super().qs

        is_strict = str(self.data.get("strict_search", "false")).lower() in ("true", "1")

        variant_filters: dict[str, Any] = {
            "tag": self.data.get("tag"),
            "min_price": self.data.get("min_price"),
            "max_price": self.data.get("max_price"),
            "search": self.data.get("search"),
            "is_promotion": self.data.get("is_promotion"),
            "min_discount": self.data.get("min_discount"),
            "strict_search": is_strict,
        }

        return self._product_repo.apply_dynamic_variant_prefetch(queryset, variant_filters)
