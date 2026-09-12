import hmac
import logging
import os
from typing import Any

from django.utils.functional import cached_property
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.config_manager import shop_config
from apps.support.repo import TicketRepository
from apps.support.usecases.chat import AdminReplyCase, UserReplyCase
from apps.support.usecases.lifecycle import AcceptTicketCase, CloseTicketCase, RejectTicketCase
from apps.telegram.client import TelegramBotClient
from apps.telegram.usecases import ProcessTelegramWebhookCase
from apps.users.repo import UserSettingsDataRepository

logger = logging.getLogger(__name__)


@extend_schema_view(
    post=extend_schema(
        summary="Webhook for Telegram API communication",
        tags=["Webhook", "Telegram"],
        request=None,
        responses={200: None},
    ),
)
class TelegramWebhookView(APIView):
    """
    Endpoint for receiving inbound updates from Telegram.

    Permissions:
    - Allows any client (AllowAny).
    Request authenticity is verified securely via the X-Telegram-Bot-Api-Secret-Token header.

    Delegation:
    - **POST**: Validates the webhook secret token and delegates the payload to `ProcessTelegramWebhookCase`.
    """

    permission_classes = [AllowAny]
    authentication_classes = []  # type: ignore[var-annotated]

    @cached_property
    def _process_webhook_usecase(self) -> ProcessTelegramWebhookCase:
        bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
        admin_chat_id = shop_config.get(
            "notifications",
            "notifications_settings.providers_settings.telegram.admin_chat_id",
        )
        client = TelegramBotClient(token=bot_token)
        ticket_repo = TicketRepository()
        user_settings_repo = UserSettingsDataRepository()

        accept_ticket_case = AcceptTicketCase(ticket_repo=ticket_repo, bot_client=client)
        reject_ticket_case = RejectTicketCase(ticket_repo=ticket_repo, bot_client=client)
        close_ticket_case = CloseTicketCase(
            ticket_repo=ticket_repo,
            bot_client=client,
            admin_chat_id=admin_chat_id,
        )
        admin_reply_case = AdminReplyCase(ticket_repo=ticket_repo, bot_client=client)
        user_reply_case = UserReplyCase(
            ticket_repo=ticket_repo,
            user_settings_repo=user_settings_repo,
            bot_client=client,
            admin_chat_id=admin_chat_id,
        )

        return ProcessTelegramWebhookCase(
            client=client,
            accept_ticket_case=accept_ticket_case,
            reject_ticket_case=reject_ticket_case,
            close_ticket_case=close_ticket_case,
            admin_reply_case=admin_reply_case,
            user_reply_case=user_reply_case,
        )

    def post(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        secret_token = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
        expected_token = os.getenv("TELEGRAM_WEBHOOK_SECRET", "")

        if not expected_token or not hmac.compare_digest(secret_token, expected_token):
            return Response({"error": "Unauthorized"}, status=status.HTTP_403_FORBIDDEN)

        try:
            self._process_webhook_usecase.execute(update_data=request.data)
        except Exception as exc:
            logger.error("Telegram Webhook Error: %s", exc)

        return Response(status=status.HTTP_200_OK)
