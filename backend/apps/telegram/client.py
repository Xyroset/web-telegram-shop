import hashlib
import hmac
import json
import logging
import time
from collections.abc import Mapping
from typing import Any, cast
from urllib.parse import parse_qsl, urljoin

import requests
from django.core.files.base import ContentFile
from rest_framework.exceptions import AuthenticationFailed

from apps.telegram.domain.exceptions import TelegramAPIError

logger = logging.getLogger(__name__)


class TelegramBotClient:
    """Concrete implementation of the Telegram Bot API client."""

    def __init__(self, token: str, timeout: float = 10.0) -> None:
        self._token = token
        self._timeout = timeout
        self._base_url = f"https://api.telegram.org/bot{self._token}/"
        self._session = requests.Session()

    def close(self) -> None:
        """Close the underlying requests session."""
        self._session.close()

    def __enter__(self) -> "TelegramBotClient":
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.close()

    def _make_request(
        self,
        endpoint: str,
        method: str = "POST",
        payload: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        url = urljoin(self._base_url, endpoint)

        try:
            response = self._session.request(
                method=method,
                url=url,
                json=payload,
                timeout=self._timeout,
            )
            response.raise_for_status()

            data: dict[str, Any] = response.json()
            if not data.get("ok"):
                error_msg = data.get("description", "Unknown Telegram Error")
                raise TelegramAPIError(f"Telegram API Error: {error_msg}")

            result = data.get("result")
            if isinstance(result, dict):
                return result
            if isinstance(result, bool | int | str | list):
                return {"result": result}
            return {}

        except requests.RequestException as exc:
            logger.error("HTTP Request to Telegram failed: %s", exc)
            raise TelegramAPIError(f"Network error communicating with Telegram: {exc}") from exc

    def send_message(
        self,
        chat_id: int | str,
        text: str,
        parse_mode: str = "HTML",
        message_thread_id: int | None = None,
        reply_markup: Mapping[str, Any] | None = None,
        disable_notification: bool = False,
    ) -> int:
        payload: dict[str, Any] = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": parse_mode,
        }
        if message_thread_id is not None:
            payload["message_thread_id"] = message_thread_id

        if reply_markup is not None:
            payload["reply_markup"] = reply_markup

        if disable_notification:
            payload["disable_notification"] = True

        result = self._make_request(endpoint="sendMessage", method="POST", payload=payload)
        return int(result["message_id"])

    def answer_callback_query(self, callback_query_id: str) -> None:
        payload = {"callback_query_id": callback_query_id}
        self._make_request(endpoint="answerCallbackQuery", method="POST", payload=payload)

    def edit_message(
        self,
        chat_id: int | str,
        message_id: int,
        text: str,
        parse_mode: str = "HTML",
        reply_markup: Mapping[str, Any] | None = None,
    ) -> None:
        payload: dict[str, Any] = {
            "chat_id": chat_id,
            "message_id": message_id,
            "text": text,
            "parse_mode": parse_mode,
        }
        if reply_markup is not None:
            payload["reply_markup"] = reply_markup

        self._make_request(endpoint="editMessageText", method="POST", payload=payload)

    def edit_message_reply_markup(
        self,
        chat_id: int | str,
        message_id: int,
        reply_markup: Mapping[str, Any] | None = None,
    ) -> None:
        payload: dict[str, Any] = {
            "chat_id": chat_id,
            "message_id": message_id,
            "reply_markup": reply_markup if reply_markup is not None else {"inline_keyboard": []},
        }
        self._make_request(endpoint="editMessageReplyMarkup", method="POST", payload=payload)

    def create_forum_topic(self, chat_id: int | str, name: str) -> int:
        payload = {
            "chat_id": chat_id,
            "name": name,
        }
        result = self._make_request(endpoint="createForumTopic", method="POST", payload=payload)
        return int(result["message_thread_id"])

    def close_forum_topic(self, chat_id: int | str, message_thread_id: int, name: str) -> None:
        self._make_request(
            endpoint="editForumTopic",
            method="POST",
            payload={
                "chat_id": chat_id,
                "message_thread_id": message_thread_id,
                "name": name,
            },
        )
        self._make_request(
            endpoint="closeForumTopic",
            method="POST",
            payload={
                "chat_id": chat_id,
                "message_thread_id": message_thread_id,
            },
        )

    def delete_forum_topic(self, chat_id: int | str, message_thread_id: int) -> None:
        payload = {
            "chat_id": chat_id,
            "message_thread_id": message_thread_id,
        }
        self._make_request(endpoint="deleteForumTopic", method="POST", payload=payload)

    def copy_message(
        self,
        chat_id: int | str,
        from_chat_id: int | str,
        message_id: int,
        message_thread_id: int | None = None,
        reply_markup: Mapping[str, Any] | None = None,
        disable_notification: bool = False,
    ) -> int:
        payload: dict[str, Any] = {
            "chat_id": chat_id,
            "from_chat_id": from_chat_id,
            "message_id": message_id,
        }
        if message_thread_id is not None:
            payload["message_thread_id"] = message_thread_id

        if reply_markup is not None:
            payload["reply_markup"] = reply_markup

        if disable_notification:
            payload["disable_notification"] = True

        result = self._make_request(endpoint="copyMessage", method="POST", payload=payload)
        return int(result["message_id"])

    def fetch_telegram_avatar(
        self,
        tg_id: int,
        current_photo_path: str | None = None,
    ) -> tuple[str | None, ContentFile | None]:
        chat_resp = self._make_request(endpoint="getChat", method="GET", payload={"chat_id": tg_id})

        if "photo" not in chat_resp:
            return None, None

        file_id = chat_resp["photo"]["big_file_id"]
        file_hash = hashlib.md5(file_id.encode("utf-8")).hexdigest()[:8]
        filename = f"{tg_id}_avatar_{file_hash}.jpg"

        if current_photo_path and file_hash in current_photo_path:
            return None, None

        file_resp = self._make_request(endpoint="getFile", method="GET", payload={"file_id": file_id})
        file_path = file_resp.get("file_path")
        if not file_path:
            return None, None

        download_url = f"https://api.telegram.org/file/bot{self._token}/{file_path}"
        try:
            image_resp = self._session.get(download_url, timeout=self._timeout)
            image_resp.raise_for_status()
            return filename, ContentFile(image_resp.content)
        except requests.RequestException as exc:
            logger.error("Failed to download avatar bytes for %s: %s", tg_id, exc)
            return None, None

    def validate_telegram_init_data(self, init_data: str) -> dict[str, Any]:
        parsed_data = dict(parse_qsl(init_data, keep_blank_values=True))

        if "hash" not in parsed_data:
            raise AuthenticationFailed("Hash is missing from initData")

        hash_value = parsed_data.pop("hash")
        data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(parsed_data.items()))

        secret_key = hmac.new(b"WebAppData", self._token.encode("utf-8"), hashlib.sha256).digest()
        calculated_hash = hmac.new(secret_key, data_check_string.encode("utf-8"), hashlib.sha256).hexdigest()

        if not hmac.compare_digest(calculated_hash, hash_value):
            raise AuthenticationFailed("Invalid Telegram hash. Data might be forged.")

        auth_date = int(parsed_data.get("auth_date", 0))
        if time.time() - auth_date > 172800:
            raise AuthenticationFailed("Telegram auth_date expired.")

        user_data = parsed_data.get("user")
        if not user_data:
            raise AuthenticationFailed("User data is missing in initData.")

        parsed_user_data = json.loads(user_data)
        if not isinstance(parsed_user_data, dict):
            raise AuthenticationFailed("User data is invalid.")

        return cast(dict[str, Any], parsed_user_data)
