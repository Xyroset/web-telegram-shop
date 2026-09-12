from typing import Any, cast

from django.conf import settings
from django.core.files.storage import default_storage
from django.http import QueryDict
from rest_framework import serializers

from apps.catalog.models import Review, ReviewPhoto
from apps.core.utils import get_base_url


class ReviewPhotoSerializer(serializers.ModelSerializer[ReviewPhoto]):
    class Meta:
        model = ReviewPhoto
        fields = ["id", "image"]


class ReviewSerializer(serializers.ModelSerializer[Review]):
    photos = ReviewPhotoSerializer(many=True, read_only=True)
    user = serializers.SerializerMethodField()
    is_author = serializers.SerializerMethodField()

    class Meta:
        model = Review
        fields = [
            "id",
            "user",
            "is_author",
            "rating",
            "text",
            "photos",
            "admin_reply_text",
            "created_at",
            "admin_reply_created_at",
        ]

    def get_user(self, obj: Review) -> dict[str, Any]:
        display_username = getattr(obj, "display_username", obj.user.tg_username)
        display_tg_id = getattr(obj, "display_tg_id", obj.user.tg_id)
        photo = getattr(obj, "display_photo", obj.user.photo)

        photo_url = None
        if photo:
            if hasattr(photo, "url"):
                photo_url = photo.url
            elif isinstance(photo, str):
                photo_url = default_storage.url(photo)

            if getattr(settings, "DEBUG", False) and photo_url and photo_url.startswith("/"):
                photo_url = f"{get_base_url()}{photo_url}"

        return {
            "tg_id": display_tg_id,
            "tg_username": display_username,
            "photo": photo_url,
        }

    def get_is_author(self, obj: Review) -> bool:
        return bool(getattr(obj, "is_author", False))


class ReviewCreateRequestSerializer(serializers.Serializer):
    product_id = serializers.IntegerField()
    rating = serializers.IntegerField(min_value=1, max_value=5)
    text = serializers.CharField(max_length=2000, required=False, allow_blank=False)
    is_anonymous = serializers.BooleanField(default=False)

    photos = serializers.ListField(
        child=serializers.ImageField(allow_empty_file=False),
        required=False,
        default=list,
        max_length=5,
    )

    def to_internal_value(self, data: Any) -> dict[str, Any]:
        if isinstance(data, QueryDict):
            data_dict: dict[str, Any] = data.dict()

            if "photos" in data:
                data_dict["photos"] = [photo for photo in data.getlist("photos") if photo != ""]

            data = data_dict

        return cast(dict[str, Any], super().to_internal_value(data))


class ReviewUpdateRequestSerializer(serializers.ModelSerializer[Review]):
    class Meta:
        model = Review
        fields = ["text", "rating"]
