from collections.abc import Mapping, Sequence
from decimal import Decimal, InvalidOperation
from typing import Any

from django.contrib.postgres.search import TrigramWordSimilarity
from django.db.models import (
    Avg,
    BooleanField,
    Case,
    CharField,
    DecimalField,
    ExpressionWrapper,
    F,
    ImageField,
    IntegerField,
    Max,
    Min,
    Prefetch,
    Q,
    QuerySet,
    Sum,
    Value,
    When,
)
from django.db.models.functions import Coalesce, Greatest
from django.utils import timezone

from apps.catalog.models import (
    Category,
    DigitalAsset,
    FavoriteItem,
    Product,
    ProductVariant,
    Review,
    ReviewPhoto,
    Tag,
)
from apps.core.domain.exceptions import CoreObjectNotFoundError
from apps.core.repo import BaseRepository
from apps.users.models import User


class ProductRepository(BaseRepository[Product]):
    def __init__(self) -> None:
        super().__init__(model_class=Product)

    def get_shop_products_list(self) -> QuerySet[Product]:
        return (
            Product.objects.filter(is_active=True)
            .annotate(
                min_variant_price=Min("variants__price"),
                annotated_avg_rating=Coalesce(Avg("reviews__rating"), 0.0),
                annotated_purchases_count=Coalesce(Sum("variants__order_items__quantity"), 0),
            )
            .prefetch_related("category", "gallery_photos")
        )

    def filter_is_promotion(self, queryset: QuerySet[Product]) -> QuerySet[Product]:
        return queryset.filter(variants__old_price__gt=F("variants__price")).distinct()

    def filter_min_discount(self, queryset: QuerySet[Product], min_discount: int | float) -> QuerySet[Product]:
        try:
            discount_val = Decimal(str(min_discount))
            multiplier = Decimal("1.00") - (discount_val / Decimal("100.00"))
            discount_limit = ExpressionWrapper(F("variants__old_price") * multiplier, output_field=DecimalField())
            return queryset.filter(variants__old_price__isnull=False, variants__price__lte=discount_limit).distinct()
        except InvalidOperation:
            return queryset

    def filter_min_rating(self, queryset: QuerySet[Product], min_rating: float) -> QuerySet[Product]:
        return queryset.annotate(avg_rating=Avg("reviews__rating")).filter(avg_rating__gte=min_rating)

    def filter_by_search_term(
        self, queryset: QuerySet[Product], search_term: str, is_strict: bool = False
    ) -> QuerySet[Product]:
        if not search_term:
            return queryset

        exact_lookups = (
            Q(name__icontains=search_term)
            | Q(base_description__icontains=search_term)
            | Q(category__name__icontains=search_term)
            | Q(variants__title__icontains=search_term)
        )

        if is_strict:
            return queryset.filter(exact_lookups).distinct()

        queryset = queryset.annotate(
            variant_sim=Max(TrigramWordSimilarity(search_term, "variants__title")),
            base_sim=Greatest(
                TrigramWordSimilarity(search_term, "name"),
                TrigramWordSimilarity(search_term, "base_description"),
                TrigramWordSimilarity(search_term, "category__name"),
            ),
        ).annotate(best_sim=Greatest("variant_sim", "base_sim"))

        return queryset.filter(exact_lookups | Q(best_sim__gt=0.25)).order_by("-best_sim").distinct()

    def apply_dynamic_variant_prefetch(
        self, queryset: QuerySet[Product], filters: Mapping[str, Any]
    ) -> QuerySet[Product]:
        variant_qs = ProductVariant.objects.filter(is_active=True)

        tags = filters.get("tag")
        if tags:
            tag_list = [t.strip() for t in str(tags).split(",") if t.strip()]
            q = Q()
            for t in tag_list:
                q |= Q(tags__slug__iexact=t)
            variant_qs = variant_qs.filter(q)

        min_price = filters.get("min_price")
        if min_price:
            variant_qs = variant_qs.filter(price__gte=min_price)

        max_price = filters.get("max_price")
        if max_price:
            variant_qs = variant_qs.filter(price__lte=max_price)

        is_promotion = filters.get("is_promotion")
        if is_promotion and str(is_promotion).lower() in ("true", "1"):
            variant_qs = variant_qs.filter(old_price__gt=F("price"))

        min_discount = filters.get("min_discount")
        if min_discount:
            try:
                discount_val = Decimal(str(min_discount))
                multiplier = Decimal("1.00") - (discount_val / Decimal("100.00"))
                discount_limit = ExpressionWrapper(F("old_price") * multiplier, output_field=DecimalField())
                variant_qs = variant_qs.filter(old_price__isnull=False, price__lte=discount_limit)
            except InvalidOperation:
                pass

        search_term = filters.get("search")
        is_strict = filters.get("strict_search", False)

        if search_term:
            search_term_str = str(search_term)
            if is_strict:
                variant_qs = variant_qs.annotate(
                    exact_match=Case(
                        When(title__icontains=search_term_str, then=Value(1)),
                        default=Value(0),
                        output_field=IntegerField(),
                    )
                ).order_by("-exact_match", "price")
            else:
                variant_qs = variant_qs.annotate(
                    exact_match=Case(
                        When(title__icontains=search_term_str, then=Value(1)),
                        default=Value(0),
                        output_field=IntegerField(),
                    ),
                    sim=TrigramWordSimilarity(search_term_str, "title"),
                ).order_by("-exact_match", "-sim", "price")
        else:
            variant_qs = variant_qs.order_by("price")

        best_variant_prefetch = Prefetch(
            "variants",
            queryset=variant_qs,
            to_attr="display_variants",
        )

        return queryset.prefetch_related(best_variant_prefetch).distinct()

    def get_digital_variants_for_update(self) -> Sequence[ProductVariant]:
        return list(
            ProductVariant.objects.select_for_update(of=("self",)).filter(product__product_type=Product.Type.DIGITAL)
        )

    def bulk_update_stock(self, variants: Sequence[ProductVariant]) -> None:
        if variants:
            ProductVariant.objects.bulk_update(variants, ["available_stock", "reserved_stock"])

    def get_product_variants(self, product_id: int) -> QuerySet[ProductVariant]:
        return ProductVariant.objects.filter(product_id=product_id, is_active=True).order_by("price")

    def get_variant(self, variant_id: int) -> ProductVariant:
        try:
            return ProductVariant.objects.get(id=variant_id)
        except ProductVariant.DoesNotExist as e:
            raise CoreObjectNotFoundError("Product variant not found!") from e

    def save_variant(self, variant: ProductVariant, update_fields: list[str] | None = None) -> ProductVariant:
        variant.save(update_fields=update_fields)
        return variant

    def cleanup_expired_discounts(self) -> int:
        expired_variants = ProductVariant.objects.filter(
            discount_expires_at__lte=timezone.now(), old_price__isnull=False
        )
        return expired_variants.update(old_price=None, discount_expires_at=None, badge=None)

    def get_variants_for_update(self, variant_ids: Sequence[int]) -> Sequence[ProductVariant]:
        if not variant_ids:
            return []
        return list(ProductVariant.objects.select_for_update().filter(id__in=variant_ids))

    def get_all_categories(self) -> QuerySet[Category]:
        return Category.objects.filter(is_active=True)

    def get_all_tags(self) -> QuerySet[Tag]:
        return Tag.objects.filter(is_active=True)

    def get_search_suggestions(self, search_term: str, limit: int = 5) -> QuerySet[Product]:
        if not search_term or len(search_term) < 2:
            return Product.objects.none()

        queryset = Product.objects.filter(is_active=True)
        queryset = self.filter_by_search_term(queryset, search_term=search_term)

        return queryset.only("id", "name")[:limit]


class DigitalAssetRepository(BaseRepository[DigitalAsset]):
    def __init__(self) -> None:
        super().__init__(model_class=DigitalAsset)


class FavoriteItemRepository(BaseRepository[FavoriteItem]):
    def __init__(self) -> None:
        super().__init__(model_class=FavoriteItem)

    def get_favorites_mapping(self, user: User) -> Mapping[int, bool]:
        favorite_product_ids = self.model_class.objects.filter(user=user).values_list("product_id", flat=True)
        return {product_id: True for product_id in favorite_product_ids}

    def create_favorite_item(self, user: User, product: Product) -> bool:
        _, created = self.model_class.objects.get_or_create(user=user, product=product)
        return created

    def delete_favorite_item(self, user: User, product_id: int) -> None:
        deleted_count, _ = self.model_class.objects.filter(user=user, product_id=product_id).delete()
        if deleted_count == 0:
            raise CoreObjectNotFoundError(f"Favorite item for product {product_id} not found!")


class ReviewRepository(BaseRepository[Review]):
    def __init__(self) -> None:
        super().__init__(model_class=Review)

    def exists_by(self, user: User, product: Product) -> bool:
        return self.model_class.objects.filter(user=user, product=product).exists()

    def get_product_reviews(self, user: User, product_id: int) -> QuerySet[Review]:
        return (
            self.model_class.objects.filter(product_id=product_id)
            .select_related("user")
            .prefetch_related("photos")
            .annotate(
                display_username=Case(
                    When(is_anonymous=True, then=Value("Anonymous")),
                    default=F("user__tg_username"),
                    output_field=CharField(),
                ),
                display_tg_id=Case(
                    When(is_anonymous=True, then=Value(0)),
                    default=F("user__tg_id"),
                    output_field=IntegerField(),
                ),
                display_photo=Case(
                    When(is_anonymous=True, then=Value(None)),
                    default=F("user__photo"),
                    output_field=ImageField(),
                ),
                is_author=Case(When(user=user, then=Value(True)), default=False, output_field=BooleanField()),
            )
            .order_by("-created_at")
        )

    def save_photos(self, photos: Sequence[ReviewPhoto]) -> None:
        ReviewPhoto.objects.bulk_create(photos)
