from rest_framework import serializers


class CreateTicketRequestSerializer(serializers.Serializer):
    category = serializers.CharField()
    message_text = serializers.CharField()
