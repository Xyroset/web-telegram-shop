import logging
from collections.abc import Mapping
from typing import Any

from django.core.files.base import ContentFile

from apps.core.config_manager import shop_config
from apps.core.utils import get_base_url
from apps.support.usecases import AcceptTicketCase, AdminReplyCase, CloseTicketCase, RejectTicketCase, UserReplyCase
from apps.telegram.domain.interfaces import TelegramClientProtocol

logger = logging.getLogger(__name__)


class SendTelegramMessageCase:
    """
    Dispatch a message to a Telegram chat.

    **Business Rules:**
    - Delegates the HTTP message dispatch to the TelegramClientProtocol.
    - Supports sending inline keyboards via reply_markup.

    **Required:**
    - Raises an exception and logs if the Telegram client fails during dispatch.
    """

    def __init__(self, client: TelegramClientProtocol) -> None:
        self._client = client

    def execute(
        self,
        chat_id: int | str,
        text: str,
        parse_mode: str = "HTML",
        message_thread_id: int | None = None,
        reply_markup: Mapping[str, Any] | None = None,
    ) -> int:
        try:
            msg_id = self._client.send_message(
                chat_id=chat_id,
                text=text,
                parse_mode=parse_mode,
                message_thread_id=message_thread_id,
                reply_markup=reply_markup,
            )
            logger.info("Successfully dispatched Telegram message to chat %s", chat_id)
            return msg_id
        except Exception as exc:
            logger.error("Failed to dispatch Telegram message to chat %s: %s", chat_id, exc)
            raise


class FetchTelegramAvatarsCase:
    """
    Fetch a user's avatar from Telegram.

    **Business Rules:**
    - Delegates the avatar fetching to the TelegramClientProtocol.
    - Returns a tuple containing the filename and the actual image file (ContentFile).
    - Logs the success or failure of the retrieval.

    **Required:**
    - Raises an exception and logs if the underlying client encounters an error.
    """

    def __init__(self, client: TelegramClientProtocol) -> None:
        self._client = client

    def execute(
        self,
        tg_id: int,
        current_photo_path: str | None = None,
    ) -> tuple[str | None, ContentFile | None]:
        try:
            filename, avatar_file = self._client.fetch_telegram_avatar(
                tg_id=tg_id,
                current_photo_path=current_photo_path,
            )
            logger.info("Successfully fetched user avatar for tg_id %s", tg_id)
            return filename, avatar_file
        except Exception as exc:
            logger.error("Failed to fetch user avatar: tg_id: %s. Error: %s", tg_id, exc)
            raise


class ValidateInitTelegramDataCase:
    """
    Validate and parse Telegram Mini App initialization data.

    **Business Rules:**
    - Delegates the cryptographic validation and parsing to the TelegramClientProtocol.

    **Required:**
    - The init_data must be a valid, unexpired string.
    - Raises AuthenticationFailed if the cryptographic hash is invalid or expired.
    """

    def __init__(self, client: TelegramClientProtocol) -> None:
        self._client = client

    def execute(self, init_data: str) -> dict[str, Any]:
        return self._client.validate_telegram_init_data(init_data=init_data)


class ProcessTelegramWebhookCase:
    """
    Act as the Front Controller / Router for all incoming Telegram webhook updates.

    **Business Rules:**
    - Identifies the update type (Message vs Callback Query).
    - Routes messages based on chat type (Private vs Supergroup).
    - Silently drops unrecognized or unsupported update formats.

    **Required:**
    - Must not contain deep domain logic; strictly delegates to specialized Use Cases.
    """

    def __init__(
        self,
        client: TelegramClientProtocol,
        accept_ticket_case: AcceptTicketCase,
        reject_ticket_case: RejectTicketCase,
        close_ticket_case: CloseTicketCase,
        admin_reply_case: AdminReplyCase,
        user_reply_case: UserReplyCase,
    ) -> None:
        self._client = client
        self._accept_ticket_case = accept_ticket_case
        self._reject_ticket_case = reject_ticket_case
        self._close_ticket_case = close_ticket_case
        self._admin_reply_case = admin_reply_case
        self._user_reply_case = user_reply_case

    def execute(self, update_data: Mapping[str, Any]) -> None:
        if "callback_query" in update_data:
            self._handle_callback_query(callback_query=update_data["callback_query"])
            return

        message = update_data.get("message")
        if not isinstance(message, dict):
            return

        chat = message.get("chat", {})
        chat_type = chat.get("type")

        if chat_type == "private":
            self._route_private_message(message=message)
        elif chat_type in {"supergroup", "group"}:
            self._route_group_message(message=message)

    def _route_private_message(self, message: Mapping[str, Any]) -> None:
        text = str(message.get("text", "")).strip()
        chat_id = message.get("chat", {}).get("id")
        reply_to = message.get("reply_to_message", {}).get("message_id")
        message_id = message.get("message_id")

        if not chat_id:
            return

        if text == "/start":
            self._handle_start_command(chat_id=chat_id)
            return

        if message_id:
            self._user_reply_case.execute(
                user_tg_id=chat_id,
                message_id=int(message_id),
                reply_to_message_id=reply_to,
                text=text,
            )
        else:
            logger.error("Message id is None")

    def _route_group_message(self, message: Mapping[str, Any]) -> None:
        text = str(message.get("text", "")).strip()
        chat_id = message.get("chat", {}).get("id")
        topic_id = message.get("message_thread_id")
        is_bot = message.get("from", {}).get("is_bot")
        message_id = message.get("message_id")

        if message_id:
            if topic_id and not is_bot:
                self._admin_reply_case.execute(
                    topic_id=topic_id,
                    message_id=int(message_id),
                    admin_chat_id=chat_id,
                    text=text,
                )
        else:
            logger.error("Message id is None")

    def _handle_callback_query(self, callback_query: Mapping[str, Any]) -> None:
        callback_data = str(callback_query.get("data", ""))
        message = callback_query.get("message", {})

        message_id = message.get("message_id")
        chat_id = message.get("chat", {}).get("id")
        chat_type = message.get("chat", {}).get("type")

        if not message_id or not chat_id:
            return

        if callback_data.startswith("ticket_accept_"):
            ticket_id = int(callback_data.split("_")[-1])
            self._accept_ticket_case.execute(
                ticket_id=ticket_id,
                message_id=message_id,
                chat_id=chat_id,
            )
        elif callback_data.startswith("ticket_reject_"):
            ticket_id = int(callback_data.split("_")[-1])
            self._reject_ticket_case.execute(
                ticket_id=ticket_id,
                message_id=message_id,
                chat_id=chat_id,
            )
        elif callback_data.startswith("ticket_close_"):
            ticket_id = int(callback_data.split("_")[-1])
            closed_by_admin = chat_type in {"supergroup", "group"}
            self._close_ticket_case.execute(
                ticket_id=ticket_id,
                message_id=message_id,
                chat_id=chat_id,
                closed_by_admin=closed_by_admin,
            )

        query_id = callback_query.get("id")
        if query_id:
            try:
                self._client.answer_callback_query(callback_query_id=str(query_id))
            except Exception as exc:
                logger.error("Failed to answer callback query: %s", exc)

    def _handle_start_command(self, chat_id: int) -> None:
        webapp_url = get_base_url(name="frontend")
        language = shop_config.get(
            "notifications",
            "notifications_settings.providers_settings.telegram.language",
            "en",
        )
        welcome_text = shop_config.get(
            "locales",
            f"{language}.start_message",
            "Shop is active! Click button <b>Shop</b> or use the inline button",
        )
        keyboard = {"inline_keyboard": [[{"text": "Open", "web_app": {"url": webapp_url}}]]}

        try:
            self._client.send_message(chat_id=chat_id, text=welcome_text, reply_markup=keyboard)
        except Exception as exc:
            logger.error("Failed to send welcome message to %s: %s", chat_id, exc)
