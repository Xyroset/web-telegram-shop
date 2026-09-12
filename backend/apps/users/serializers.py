from rest_framework import serializers
from rest_framework_simplejwt.exceptions import InvalidToken
from rest_framework_simplejwt.tokens import RefreshToken

from apps.orders.serializers import DeliveryAddressSerializer
from apps.users.models import User


class TelegramAuthRequestSerializer(serializers.Serializer):
    initData = serializers.CharField(required=True)
    theme = serializers.CharField(required=False, default="light")


class TelegramAuthResponseSerializer(serializers.Serializer):
    access_token = serializers.CharField(required=True)


class CookieTokenRefreshSerializer(serializers.Serializer):
    access_token = serializers.CharField(read_only=True)

    def validate(self, attrs):
        request = self.context.get("request")
        refresh_token = request.COOKIES.get("refresh_token")

        if not refresh_token:
            raise InvalidToken("No refresh token found in cookies")

        try:
            refresh = RefreshToken(refresh_token)
        except Exception:
            raise InvalidToken("Refresh token is invalid or expired")

        return {"access_token": str(refresh.access_token)}


class GetUserDataResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "tg_id",
            "tg_username",
            "first_name",
            "last_name",
            "photo",
        ]


class UserSettingsSerializer(serializers.Serializer):
    preferred_payment_currency = serializers.CharField(required=False)
    preferred_network = serializers.CharField(required=False)
    language_code = serializers.CharField(required=False)
    theme = serializers.CharField(required=False)
    particles_style = serializers.CharField(required=False)


class UserDeliveryDataRequestSerializer(serializers.Serializer):
    full_name = serializers.CharField(required=False)
    email = serializers.CharField(required=False)
    phone = serializers.CharField(required=False)
    zip_code = serializers.CharField(required=False)
    address_line = serializers.CharField(required=False)
    destination_code = serializers.CharField(required=False)
    region_code = serializers.CharField(required=False, allow_blank=True)


class UserDeliveryDataResponseSerializer(UserDeliveryDataRequestSerializer):
    id = serializers.IntegerField()
    is_current = serializers.BooleanField(required=False)


class DevAuthRequestSerializer(serializers.Serializer):
    tg_id = serializers.IntegerField(default=1, help_text="Test user Telegram ID")


class UpdateDeliveryDataRequestSerializer(serializers.Serializer):
    delivery_data = DeliveryAddressSerializer()
