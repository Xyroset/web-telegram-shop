from rest_framework import serializers

from apps.payments.models import PaymentTransaction


class CreateInvoiceRequestSerializer(serializers.Serializer):
    order_id = serializers.UUIDField()
    currency = serializers.CharField(required=False)
    network = serializers.CharField(required=False, allow_blank=True)
    provider_name = serializers.CharField(required=False)


class TransactionCreateResponseSerializer(serializers.Serializer):
    transaction_id = serializers.CharField()
    payload_url = serializers.CharField()


class TransactionResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentTransaction
        fields = [
            "id",
            "state",
            "order",
            "created_at",
            "invoice_id",
            "payment_currency",
            "network",
            "target_amount_usd",
            "amount_crypto",
            "current_amount_crypto",
            "receiver_address",
            "sender_address",
            "tx_hash",
            "raw_response",
        ]
