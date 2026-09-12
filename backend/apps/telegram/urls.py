from django.urls import path

from apps.telegram.views import TelegramWebhookView

urlpatterns = [path("", TelegramWebhookView.as_view(), name="handle_telegram_bot")]
