from rest_framework import serializers

from apps.catalog.serializers import ShortVariantProductSerializer
from apps.orders.models import Order, OrderItem, PromoCode


class PromoCodeSerializer(serializers.ModelSerializer):
    class Meta:
        model = PromoCode
        fields = ["id", "code", "discount_type", "discount_percent", "discount_amount"]


class OrderItemSerializer(serializers.ModelSerializer):
    variant = ShortVariantProductSerializer(read_only=True)

    class Meta:
        model = OrderItem
        fields = ["id", "variant", "quantity", "fixed_price"]


class OrderResponseSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    promocode = PromoCodeSerializer(read_only=True)

    class Meta:
        model = Order
        fields = [
            "id",
            "amount_usd",
            "state",
            "paid_at",
            "created_at",
            "promocode",
            "payload_url",
            "items",
        ]


class DeliveryAddressSerializer(serializers.Serializer):
    full_name = serializers.CharField(max_length=255, default="-")
    email = serializers.CharField(max_length=255, default="-")
    phone = serializers.CharField(max_length=20, default="-")
    zip_code = serializers.CharField(max_length=20, default="-")
    address_line = serializers.CharField(max_length=255, default="-")
    destination_code = serializers.CharField(max_length=10, required=False, allow_null=True, allow_blank=True)
    region_code = serializers.CharField(max_length=10, required=False, allow_null=True, allow_blank=True)


class OrderCreateRequestSerializer(serializers.Serializer):
    code = serializers.CharField(max_length=50, required=False)
    delivery_data = DeliveryAddressSerializer(required=False)


class OrderCreateResponseSerializer(serializers.Serializer):
    order_id = serializers.CharField(required=True)
