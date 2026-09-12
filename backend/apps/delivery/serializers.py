from rest_framework import serializers

from apps.delivery.models import Delivery


class DeliveryEstimateRequestSerializer(serializers.Serializer):
    destination_code = serializers.CharField(
        max_length=10,
        required=False,
        allow_blank=True,
    )
    region_code = serializers.CharField(
        max_length=10,
        required=False,
        allow_blank=True,
    )


class DeliveryEstimateResponseSerializer(serializers.Serializer):
    cost = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
    )
    is_free = serializers.BooleanField()
    amount_left_for_free = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
    )
    is_free_available = serializers.BooleanField()


class DeliveryDataResponse(serializers.ModelSerializer):
    class Meta:
        model = Delivery
        fields = ["id", "state", "order", "provider_code", "tracking_number", "cost", "delivery_data"]
