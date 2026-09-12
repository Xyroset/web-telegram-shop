from rest_framework import serializers

from apps.basket.models import BasketItem
from apps.catalog.serializers import ShortVariantProductSerializer


class BasketUpdatePageResponseSerializer(serializers.ModelSerializer[BasketItem]):
    variant = ShortVariantProductSerializer(read_only=True)

    class Meta:
        model = BasketItem
        fields = ["id", "quantity", "variant"]


class BasketShopUpdateRequestSerializer(serializers.Serializer):
    variant_id = serializers.IntegerField()
    quantity = serializers.IntegerField(min_value=1)


class BasketUpdateRequestSerializer(serializers.Serializer):
    quantity = serializers.IntegerField(min_value=1)


class BasketUpdateResponseSerializer(serializers.Serializer):
    quantity = serializers.IntegerField()


class BasketCalculatePriceResponseSerializer(serializers.Serializer):
    base_price = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)
    total_price = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_weight_kg = serializers.DecimalField(max_digits=10, decimal_places=2)
    discount_value = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)
    promocode_type = serializers.CharField(max_length=20, required=False, allow_null=True)
    valid_promocode = serializers.BooleanField(default=False)
