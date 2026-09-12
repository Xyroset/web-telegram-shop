import hashlib
import hmac
import json
from typing import cast
from unittest.mock import MagicMock, call

import pytest
import requests
from django.core.files.base import ContentFile
from pytest_mock import MockerFixture
from rest_framework.exceptions import AuthenticationFailed

from apps.telegram.client import TelegramBotClient
from apps.telegram.domain.exceptions import TelegramAPIError


class TestTelegramBotClient:
    """Verify infrastructure, API communication, and cryptographic rules for the Telegram client."""

    @pytest.fixture
    def client(self, mocker: MockerFixture) -> TelegramBotClient:
        mocker.patch("apps.telegram.client.requests.Session")
        return TelegramBotClient(token="test_token", timeout=10.0)

    def test_make_request_success(self, client: TelegramBotClient) -> None:
        """
        Ensure _make_request successfully sends an HTTP request and parses the JSON response.
        """
        mock_response = MagicMock()
        mock_response.json.return_value = {"ok": True, "result": {"key": "value"}}
        cast(MagicMock, client._session.request).return_value = mock_response

        result = client._make_request(endpoint="testEndpoint", method="POST", payload={"param": "value"})

        assert result == {"key": "value"}
        cast(MagicMock, client._session.request).assert_called_once_with(
            method="POST",
            url="https://api.telegram.org/bottest_token/testEndpoint",
            json={"param": "value"},
            timeout=10.0,
        )

    def test_make_request_telegram_error(self, client: TelegramBotClient) -> None:
        """
        Ensure _make_request raises TelegramAPIError when the Telegram response returns ok: False.
        """
        mock_response = MagicMock()
        mock_response.json.return_value = {"ok": False, "description": "Bad Request: chat not found"}
        cast(MagicMock, client._session.request).return_value = mock_response

        with pytest.raises(TelegramAPIError, match="Telegram API Error: Bad Request: chat not found"):
            client._make_request(endpoint="testEndpoint", method="GET")

    def test_make_request_network_error(self, client: TelegramBotClient) -> None:
        """
        Ensure _make_request wraps request-level exceptions into TelegramAPIError.
        """
        cast(MagicMock, client._session.request).side_effect = requests.RequestException("Connection timeout")

        with pytest.raises(TelegramAPIError, match="Network error communicating with Telegram: Connection timeout"):
            client._make_request(endpoint="testEndpoint", method="GET")

    def test_send_message(self, client: TelegramBotClient, mocker: MockerFixture) -> None:
        """
        Ensure send_message dispatches correct payload and returns message_id.
        """
        mock_make_request = mocker.patch.object(client, "_make_request", return_value={"message_id": 42})

        result = client.send_message(
            chat_id=123456,
            text="Hello world",
            parse_mode="HTML",
            message_thread_id=10,
            reply_markup={"inline_keyboard": []},
            disable_notification=True,
        )

        assert result == 42
        mock_make_request.assert_called_once_with(
            endpoint="sendMessage",
            method="POST",
            payload={
                "chat_id": 123456,
                "text": "Hello world",
                "parse_mode": "HTML",
                "message_thread_id": 10,
                "reply_markup": {"inline_keyboard": []},
                "disable_notification": True,
            },
        )

    def test_answer_callback_query(self, client: TelegramBotClient, mocker: MockerFixture) -> None:
        """
        Ensure answer_callback_query dispatches the callback_query_id.
        """
        mock_make_request = mocker.patch.object(client, "_make_request", return_value={"result": True})

        client.answer_callback_query(callback_query_id="query_123")

        mock_make_request.assert_called_once_with(
            endpoint="answerCallbackQuery",
            method="POST",
            payload={"callback_query_id": "query_123"},
        )

    def test_edit_message(self, client: TelegramBotClient, mocker: MockerFixture) -> None:
        """
        Ensure edit_message dispatches correct payload to editMessageText.
        """
        mock_make_request = mocker.patch.object(client, "_make_request", return_value={"message_id": 42})

        client.edit_message(
            chat_id=123456,
            message_id=42,
            text="Updated text",
            parse_mode="HTML",
            reply_markup={"inline_keyboard": []},
        )

        mock_make_request.assert_called_once_with(
            endpoint="editMessageText",
            method="POST",
            payload={
                "chat_id": 123456,
                "message_id": 42,
                "text": "Updated text",
                "parse_mode": "HTML",
                "reply_markup": {"inline_keyboard": []},
            },
        )

    def test_edit_message_reply_markup(self, client: TelegramBotClient, mocker: MockerFixture) -> None:
        """
        Ensure edit_message_reply_markup dispatches default empty inline keyboard if None is passed.
        """
        mock_make_request = mocker.patch.object(client, "_make_request", return_value={"message_id": 42})

        client.edit_message_reply_markup(chat_id=123456, message_id=42, reply_markup=None)

        mock_make_request.assert_called_once_with(
            endpoint="editMessageReplyMarkup",
            method="POST",
            payload={
                "chat_id": 123456,
                "message_id": 42,
                "reply_markup": {"inline_keyboard": []},
            },
        )

    def test_create_forum_topic(self, client: TelegramBotClient, mocker: MockerFixture) -> None:
        """
        Ensure create_forum_topic returns message_thread_id.
        """
        mock_make_request = mocker.patch.object(client, "_make_request", return_value={"message_thread_id": 777})

        result = client.create_forum_topic(chat_id=-100123456, name="Topic 1")

        assert result == 777
        mock_make_request.assert_called_once_with(
            endpoint="createForumTopic",
            method="POST",
            payload={"chat_id": -100123456, "name": "Topic 1"},
        )

    def test_close_forum_topic(self, client: TelegramBotClient, mocker: MockerFixture) -> None:
        """
        Ensure close_forum_topic calls closeForumTopic endpoint.
        """
        mock_make_request = mocker.patch.object(client, "_make_request", return_value={"result": True})

        client.close_forum_topic(chat_id=-100123456, message_thread_id=777, name="test")

        assert mock_make_request.call_count == 2
        mock_make_request.assert_has_calls(
            [
                call(
                    endpoint="editForumTopic",
                    method="POST",
                    payload={
                        "chat_id": -100123456,
                        "message_thread_id": 777,
                        "name": "test",
                    },
                ),
                call(
                    endpoint="closeForumTopic",
                    method="POST",
                    payload={
                        "chat_id": -100123456,
                        "message_thread_id": 777,
                    },
                ),
            ],
            any_order=False,
        )

    def test_delete_forum_topic(self, client: TelegramBotClient, mocker: MockerFixture) -> None:
        """
        Ensure delete_forum_topic calls deleteForumTopic endpoint.
        """
        mock_make_request = mocker.patch.object(client, "_make_request", return_value={"result": True})

        client.delete_forum_topic(chat_id=-100123456, message_thread_id=777)

        mock_make_request.assert_called_once_with(
            endpoint="deleteForumTopic",
            method="POST",
            payload={"chat_id": -100123456, "message_thread_id": 777},
        )

    def test_copy_message(self, client: TelegramBotClient, mocker: MockerFixture) -> None:
        """
        Ensure copy_message dispatches correct payload and returns message_id.
        """
        mock_make_request = mocker.patch.object(client, "_make_request", return_value={"message_id": 100})

        result = client.copy_message(
            chat_id=-100123,
            from_chat_id=555,
            message_id=1,
            message_thread_id=12,
            reply_markup={"inline_keyboard": []},
            disable_notification=True,
        )

        assert result == 100
        mock_make_request.assert_called_once_with(
            endpoint="copyMessage",
            method="POST",
            payload={
                "chat_id": -100123,
                "from_chat_id": 555,
                "message_id": 1,
                "message_thread_id": 12,
                "reply_markup": {"inline_keyboard": []},
                "disable_notification": True,
            },
        )

    def test_fetch_telegram_avatar_success(self, client: TelegramBotClient, mocker: MockerFixture) -> None:
        """
        Happy path: Fetch user profile photo bytes.
        """
        mock_make_request = mocker.patch.object(client, "_make_request")
        mock_make_request.side_effect = [
            {"photo": {"big_file_id": "file123"}},
            {"file_path": "photos/file123.jpg"},
        ]
        mock_image_resp = MagicMock()
        mock_image_resp.content = b"fake_image_bytes"
        cast(MagicMock, client._session.get).return_value = mock_image_resp

        filename, file_content = client.fetch_telegram_avatar(tg_id=999)

        expected_hash = hashlib.md5("file123".encode("utf-8")).hexdigest()[:8]
        assert filename == f"999_avatar_{expected_hash}.jpg"
        assert isinstance(file_content, ContentFile)
        assert file_content.read() == b"fake_image_bytes"

    def test_fetch_telegram_avatar_cache_hit(self, client: TelegramBotClient, mocker: MockerFixture) -> None:
        """
        Happy path: Avoid downloading if photo is unchanged.
        """
        mock_make_request = mocker.patch.object(client, "_make_request")
        mock_make_request.return_value = {"photo": {"big_file_id": "file123"}}
        expected_hash = hashlib.md5("file123".encode("utf-8")).hexdigest()[:8]

        filename, file_content = client.fetch_telegram_avatar(
            tg_id=999, current_photo_path=f"avatars/999_avatar_{expected_hash}.jpg"
        )

        assert filename is None
        assert file_content is None
        assert mock_make_request.call_count == 1

    def test_fetch_telegram_avatar_missing_photo(self, client: TelegramBotClient, mocker: MockerFixture) -> None:
        """
        Edge case: Return None when chat does not contain a photo.
        """
        mocker.patch.object(client, "_make_request", return_value={})

        filename, file_content = client.fetch_telegram_avatar(tg_id=999)

        assert filename is None
        assert file_content is None

    def test_fetch_telegram_avatar_download_failure(self, client: TelegramBotClient, mocker: MockerFixture) -> None:
        """
        Edge case: Return None when avatar download encounters a network error.
        """
        mock_make_request = mocker.patch.object(client, "_make_request")
        mock_make_request.side_effect = [
            {"photo": {"big_file_id": "file123"}},
            {"file_path": "photos/file123.jpg"},
        ]
        cast(MagicMock, client._session.get).side_effect = requests.RequestException("Download error")

        filename, file_content = client.fetch_telegram_avatar(tg_id=999)

        assert filename is None
        assert file_content is None

    def test_validate_telegram_init_data_success(self, client: TelegramBotClient, mocker: MockerFixture) -> None:
        """
        Happy path: Validate legitimate Telegram WebApp init_data.
        """
        mocker.patch("apps.telegram.client.time.time", return_value=1000.0)
        user_json = json.dumps({"id": 123, "first_name": "Test"})
        auth_date = "1000"
        data_check_string = f"auth_date={auth_date}\nuser={user_json}"
        secret_key = hmac.new(b"WebAppData", b"test_token", hashlib.sha256).digest()
        valid_hash = hmac.new(secret_key, data_check_string.encode("utf-8"), hashlib.sha256).hexdigest()
        init_data = f"user={user_json}&auth_date={auth_date}&hash={valid_hash}"

        result = client.validate_telegram_init_data(init_data=init_data)

        assert result == {"id": 123, "first_name": "Test"}

    @pytest.mark.parametrize(
        ("payload", "expected_error"),
        [
            ("user=123", "Hash is missing from initData"),
            ("user=123&hash=invalidhash", "Invalid Telegram hash"),
            ("user=123&auth_date=0&hash=forged", "Invalid Telegram hash"),
        ],
    )
    def test_validate_telegram_init_data_failures(
        self, client: TelegramBotClient, payload: str, expected_error: str
    ) -> None:
        """
        Failure: init_data validation fails due to bad signature or missing hash.
        """
        with pytest.raises(AuthenticationFailed, match=expected_error):
            client.validate_telegram_init_data(init_data=payload)

    def test_validate_telegram_init_data_expired(self, client: TelegramBotClient, mocker: MockerFixture) -> None:
        """
        Failure: init_data is older than 48 hours.
        """
        current_time = 200000.0
        mocker.patch("apps.telegram.client.time.time", return_value=current_time)
        user_json = json.dumps({"id": 123})
        expired_auth_date = str(int(current_time) - 172801)
        data_check_string = f"auth_date={expired_auth_date}\nuser={user_json}"
        secret_key = hmac.new(b"WebAppData", b"test_token", hashlib.sha256).digest()
        valid_hash = hmac.new(secret_key, data_check_string.encode("utf-8"), hashlib.sha256).hexdigest()
        init_data = f"user={user_json}&auth_date={expired_auth_date}&hash={valid_hash}"

        with pytest.raises(AuthenticationFailed, match="Telegram auth_date expired."):
            client.validate_telegram_init_data(init_data=init_data)

    def test_context_manager_closes_session(self, mocker: MockerFixture) -> None:
        """
        Ensure TelegramBotClient closes session upon exiting context manager.
        """
        mock_session_class = mocker.patch("apps.telegram.client.requests.Session")
        mock_session_instance = MagicMock()
        mock_session_class.return_value = mock_session_instance

        with TelegramBotClient(token="test_token") as client:
            assert client is not None

        mock_session_instance.close.assert_called_once()
