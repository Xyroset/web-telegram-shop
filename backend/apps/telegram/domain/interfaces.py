from collections.abc import Mapping
from typing import Any, Protocol

from django.core.files.base import ContentFile


class TelegramClientProtocol(Protocol):
    """Protocol defining the interface for Telegram Bot API operations."""

    def send_message(
        self,
        chat_id: int | str,
        text: str,
        parse_mode: str = "HTML",
        message_thread_id: int | None = None,
        reply_markup: Mapping[str, Any] | None = None,
        disable_notification: bool = False,
    ) -> int: ...

    def edit_message(
        self,
        chat_id: int | str,
        message_id: int,
        text: str,
        parse_mode: str = "HTML",
        reply_markup: Mapping[str, Any] | None = None,
    ) -> None: ...

    def edit_message_reply_markup(
        self,
        chat_id: int | str,
        message_id: int,
        reply_markup: Mapping[str, Any] | None = None,
    ) -> None: ...

    def create_forum_topic(self, chat_id: int | str, name: str) -> int: ...

    def close_forum_topic(self, chat_id: int | str, message_thread_id: int, name: str) -> None: ...

    def delete_forum_topic(self, chat_id: int | str, message_thread_id: int) -> None: ...

    def copy_message(
        self,
        chat_id: int | str,
        from_chat_id: int | str,
        message_id: int,
        message_thread_id: int | None = None,
        reply_markup: Mapping[str, Any] | None = None,
        disable_notification: bool = False,
    ) -> int: ...

    def answer_callback_query(self, callback_query_id: str) -> None: ...

    def fetch_telegram_avatar(
        self,
        tg_id: int,
        current_photo_path: str | None = None,
    ) -> tuple[str | None, ContentFile | None]: ...

    def validate_telegram_init_data(self, init_data: str) -> dict[str, Any]: ...
