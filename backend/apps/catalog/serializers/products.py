from typing import Any, cast

from rest_framework import serializers

from apps.catalog.models import Product, ProductVariant
from apps.catalog.serializers.common import (
    CategorySerializer,
    PhotoSerializer,
    TagSerializer,
)


class ProductSerializer(serializers.ModelSerializer[Product]):
    category = CategorySerializer(read_only=True)
    photos = PhotoSerializer(source="gallery_photos", many=True, read_only=True)

    class Meta:
        model = Product
        fields = [
            "id",
            "name",
            "category",
            "base_description",
            "main_image",
            "video_source",
            "photos",
            "is_active",
        ]


class ProductVariantListSerializer(serializers.ModelSerializer[ProductVariant]):
    stock_status = serializers.ReadOnlyField()
    basket_quantity = serializers.SerializerMethodField()

    class Meta:
        model = ProductVariant
        fields = [
            "id",
            "badge",
            "price",
            "old_price",
            "title",
            "image",
            "stock_status",
            "is_new",
            "is_promotion",
            "promotion_discount",
            "basket_quantity",
        ]

    def get_basket_quantity(self, obj: ProductVariant) -> int:
        user_basket: dict[int, int] = self.context.get("user_basket", {})
        return user_basket.get(obj.id, 0)


class ProductVariantDetailSerializer(ProductVariantListSerializer):
    tags = TagSerializer(many=True, read_only=True)
    volumetric_weight_kg = serializers.ReadOnlyField()

    class Meta(ProductVariantListSerializer.Meta):
        fields = ProductVariantListSerializer.Meta.fields + [
            "specific_description",
            "tags",
            "weight_kg",
            "length_cm",
            "width_cm",
            "height_cm",
            "volumetric_weight_kg",
            "metadata",
        ]


class ShortProductSerializer(serializers.ModelSerializer[Product]):
    class Meta:
        model = Product
        fields = [
            "id",
            "name",
        ]


class ShortVariantProductSerializer(serializers.ModelSerializer[ProductVariant]):
    product = ShortProductSerializer(read_only=True)

    class Meta:
        model = ProductVariant
        fields = ["id", "title", "image", "price", "old_price", "product", "stock_status"]


class ShopProductListResponseSerializer(serializers.ModelSerializer[Product]):
    photos = PhotoSerializer(source="gallery_photos", many=True, read_only=True)
    category = CategorySerializer(read_only=True)
    is_favorite = serializers.SerializerMethodField()
    display_variant = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            "id",
            "name",
            "category",
            "base_description",
            "is_favorite",
            "main_image",
            "attributes",
            "video_source",
            "display_variant",
            "photos",
            "is_active",
            "average_rating",
            "purchases_count",
        ]

    def get_is_favorite(self, obj: Product) -> bool:
        user_favorites: dict[int, bool] = self.context.get("user_favorites", {})
        return user_favorites.get(obj.id, False)

    def get_display_variant(self, obj: Product) -> dict[str, Any] | None:
        display_variants = getattr(obj, "display_variants", [])
        if display_variants:
            data = ProductVariantListSerializer(display_variants[0], context=self.context).data
            return cast(dict[str, Any], data)
        return None


class ProductSuggestionResponseSerializer(serializers.ModelSerializer[Product]):
    class Meta:
        model = Product
        fields = ["id", "name"]
