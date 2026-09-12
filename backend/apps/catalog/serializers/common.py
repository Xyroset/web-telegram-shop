from rest_framework import serializers

from apps.catalog.models import Category, Photo, Tag


class TagSerializer(serializers.ModelSerializer[Tag]):
    class Meta:
        model = Tag
        fields = ["id", "name", "slug"]


class PhotoSerializer(serializers.ModelSerializer[Photo]):
    class Meta:
        model = Photo
        fields = ["id", "image", "ordering"]


class CategorySerializer(serializers.ModelSerializer[Category]):
    class Meta:
        model = Category
        fields = ["id", "name", "slug"]
