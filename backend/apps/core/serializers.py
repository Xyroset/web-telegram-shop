from rest_framework import serializers


class BaseResponseSerializer(serializers.Serializer):
    message = serializers.CharField(required=False)


class GetWebAppInitConfigResponseSerializer(serializers.Serializer):
    available_languages = serializers.JSONField()
    current_language = serializers.CharField()
    translations = serializers.JSONField()
    particles = serializers.JSONField()
    background = serializers.JSONField()
    payments_visual = serializers.JSONField()
    zone_names_extra = serializers.JSONField()
    footer = serializers.JSONField()
