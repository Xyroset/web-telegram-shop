from django.urls import path

from apps.payments.views import (
    CreateTransactionView,
    CryptoBotWebhookView,
    GetTransactionsView,
    NOWPaymentsWebhookView,
    TransactionDetailsAPIView,
)

urlpatterns = [
    path("", CreateTransactionView.as_view(), name="create_transaction_api"),
    path("order/<uuid:order_id>/", GetTransactionsView.as_view(), name="reviews_transactions_api"),
    path("<uuid:transaction_id>/", TransactionDetailsAPIView.as_view(), name="cancel_get_transaction_api"),
    path("nowpayments/", NOWPaymentsWebhookView.as_view(), name="webhook_nowpayments_api"),
    path("cryptobot/", CryptoBotWebhookView.as_view(), name="webhook_cryptobot_api"),
]
