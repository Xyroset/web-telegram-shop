from collections.abc import Mapping
from typing import Any
from unittest.mock import MagicMock

import pytest
from django.core.files.base import ContentFile
from pytest_mock import MockerFixture

from apps.support.usecases.chat import AdminReplyCase, UserReplyCase
from apps.support.usecases.lifecycle import AcceptTicketCase, CloseTicketCase, RejectTicketCase
from apps.telegram.domain.interfaces import TelegramClientProtocol
from apps.telegram.usecases import (
    FetchTelegramAvatarsCase,
    ProcessTelegramWebhookCase,
    SendTelegramMessageCase,
    ValidateInitTelegramDataCase,
)


class TestSendTelegramMessageCase:
    """Verify business rules for dispatching messages via Telegram."""

    def test_send_message_success(self) -> None:
        """
        Happy path: Successfully dispatch a message and return the message ID.
        """
        mock_client: TelegramClientProtocol | MagicMock = MagicMock()
        mock_client.send_message.return_value = 100  # type: ignore[union-attr]
        usecase = SendTelegramMessageCase(client=mock_client)

        result = usecase.execute(
            chat_id=123456,
            text="Test message",
            parse_mode="HTML",
            message_thread_id=5,
            reply_markup={"inline_keyboard": []},
        )

        assert result == 100
        mock_client.send_message.assert_called_once_with(  # type: ignore[union-attr]
            chat_id=123456,
            text="Test message",
            parse_mode="HTML",
            message_thread_id=5,
            reply_markup={"inline_keyboard": []},
        )

    def test_send_message_failure_raises_and_logs(self, mocker: MockerFixture) -> None:
        """
        Failure: Re-raise exception and log error when client dispatch fails.
        """
        mock_client: TelegramClientProtocol | MagicMock = MagicMock()
        mock_client.send_message.side_effect = RuntimeError("Telegram network failure")  # type: ignore[union-attr]
        mock_logger = mocker.patch("apps.telegram.usecases.logger")
        usecase = SendTelegramMessageCase(client=mock_client)

        with pytest.raises(RuntimeError, match="Telegram network failure"):
            usecase.execute(chat_id=123456, text="Test message")

        mock_logger.error.assert_called_once()


class TestFetchTelegramAvatarsCase:
    """Verify business rules for retrieving user profile avatars."""

    def test_fetch_avatar_success(self) -> None:
        """
        Happy path: Retrieve avatar filename and content file successfully.
        """
        mock_client: TelegramClientProtocol | MagicMock = MagicMock()
        fake_content = ContentFile(b"fake_image_bytes")
        mock_client.fetch_telegram_avatar.return_value = ("avatar_123.jpg", fake_content)  # type: ignore[union-attr]
        usecase = FetchTelegramAvatarsCase(client=mock_client)

        filename, content = usecase.execute(tg_id=123, current_photo_path="old_path.jpg")

        assert filename == "avatar_123.jpg"
        assert content == fake_content
        mock_client.fetch_telegram_avatar.assert_called_once_with(  # type: ignore[union-attr]
            tg_id=123,
            current_photo_path="old_path.jpg",
        )

    def test_fetch_avatar_failure_raises_and_logs(self, mocker: MockerFixture) -> None:
        """
        Failure: Re-raise exception and log error when avatar fetch fails.
        """
        mock_client: TelegramClientProtocol | MagicMock = MagicMock()
        mock_client.fetch_telegram_avatar.side_effect = RuntimeError("Download error")  # type: ignore[union-attr]
        mock_logger = mocker.patch("apps.telegram.usecases.logger")
        usecase = FetchTelegramAvatarsCase(client=mock_client)

        with pytest.raises(RuntimeError, match="Download error"):
            usecase.execute(tg_id=123)

        mock_logger.error.assert_called_once()


class TestValidateInitTelegramDataCase:
    """Verify cryptographic validation delegation for Telegram Mini App initData."""

    def test_validate_init_data_delegation(self) -> None:
        """
        Happy path: Successfully validate and return parsed initData dictionary.
        """
        mock_client: TelegramClientProtocol | MagicMock = MagicMock()
        expected_user_data = {"id": 12345, "first_name": "Test"}
        mock_client.validate_telegram_init_data.return_value = expected_user_data  # type: ignore[union-attr]
        usecase = ValidateInitTelegramDataCase(client=mock_client)

        result = usecase.execute(init_data="raw_init_data_string")

        assert result == expected_user_data
        mock_client.validate_telegram_init_data.assert_called_once_with(  # type: ignore[union-attr]
            init_data="raw_init_data_string"
        )


class TestProcessTelegramWebhookCase:
    """Verify webhook router orchestration and sub-usecase dispatching."""

    @pytest.fixture
    def mock_client(self) -> TelegramClientProtocol | MagicMock:
        return MagicMock()

    @pytest.fixture
    def mock_accept_ticket(self) -> AcceptTicketCase | MagicMock:
        return MagicMock()

    @pytest.fixture
    def mock_reject_ticket(self) -> RejectTicketCase | MagicMock:
        return MagicMock()

    @pytest.fixture
    def mock_close_ticket(self) -> CloseTicketCase | MagicMock:
        return MagicMock()

    @pytest.fixture
    def mock_admin_reply(self) -> AdminReplyCase | MagicMock:
        return MagicMock()

    @pytest.fixture
    def mock_user_reply(self) -> UserReplyCase | MagicMock:
        return MagicMock()

    @pytest.fixture
    def usecase(
        self,
        mock_client: TelegramClientProtocol | MagicMock,
        mock_accept_ticket: AcceptTicketCase | MagicMock,
        mock_reject_ticket: RejectTicketCase | MagicMock,
        mock_close_ticket: CloseTicketCase | MagicMock,
        mock_admin_reply: AdminReplyCase | MagicMock,
        mock_user_reply: UserReplyCase | MagicMock,
    ) -> ProcessTelegramWebhookCase:
        return ProcessTelegramWebhookCase(
            client=mock_client,
            accept_ticket_case=mock_accept_ticket,
            reject_ticket_case=mock_reject_ticket,
            close_ticket_case=mock_close_ticket,
            admin_reply_case=mock_admin_reply,
            user_reply_case=mock_user_reply,
        )

    def test_process_webhook_accept_callback_query(
        self,
        usecase: ProcessTelegramWebhookCase,
        mock_client: TelegramClientProtocol | MagicMock,
        mock_accept_ticket: AcceptTicketCase | MagicMock,
    ) -> None:
        """
        Happy path: Route accept ticket callback query and answer the callback query.
        """
        payload: Mapping[str, Any] = {
            "callback_query": {
                "id": "query_1",
                "data": "ticket_accept_42",
                "message": {
                    "message_id": 100,
                    "chat": {"id": -100123, "type": "supergroup"},
                },
            }
        }

        usecase.execute(update_data=payload)

        mock_accept_ticket.execute.assert_called_once_with(  # type: ignore[union-attr]
            ticket_id=42,
            message_id=100,
            chat_id=-100123,
        )
        mock_client.answer_callback_query.assert_called_once_with(callback_query_id="query_1")  # type: ignore[union-attr]

    def test_process_webhook_reject_callback_query(
        self,
        usecase: ProcessTelegramWebhookCase,
        mock_client: TelegramClientProtocol | MagicMock,
        mock_reject_ticket: RejectTicketCase | MagicMock,
    ) -> None:
        """
        Happy path: Route reject ticket callback query.
        """
        payload: Mapping[str, Any] = {
            "callback_query": {
                "id": "query_2",
                "data": "ticket_reject_55",
                "message": {
                    "message_id": 101,
                    "chat": {"id": -100123, "type": "supergroup"},
                },
            }
        }

        usecase.execute(update_data=payload)

        mock_reject_ticket.execute.assert_called_once_with(  # type: ignore[union-attr]
            ticket_id=55,
            message_id=101,
            chat_id=-100123,
        )
        mock_client.answer_callback_query.assert_called_once_with(callback_query_id="query_2")  # type: ignore[union-attr]

    def test_process_webhook_close_callback_query_by_admin(
        self,
        usecase: ProcessTelegramWebhookCase,
        mock_client: TelegramClientProtocol | MagicMock,
        mock_close_ticket: CloseTicketCase | MagicMock,
    ) -> None:
        """
        Happy path: Route close ticket callback query when initiated inside a supergroup.
        """
        payload: Mapping[str, Any] = {
            "callback_query": {
                "id": "query_3",
                "data": "ticket_close_77",
                "message": {
                    "message_id": 102,
                    "chat": {"id": -100123, "type": "supergroup"},
                },
            }
        }

        usecase.execute(update_data=payload)

        mock_close_ticket.execute.assert_called_once_with(  # type: ignore[union-attr]
            ticket_id=77,
            message_id=102,
            chat_id=-100123,
            closed_by_admin=True,
        )
        mock_client.answer_callback_query.assert_called_once_with(callback_query_id="query_3")  # type: ignore[union-attr]

    def test_process_webhook_callback_query_missing_identifiers_is_ignored(
        self,
        usecase: ProcessTelegramWebhookCase,
        mock_client: TelegramClientProtocol | MagicMock,
        mock_accept_ticket: AcceptTicketCase | MagicMock,
    ) -> None:
        """
        Edge case: Callback queries without message_id or chat_id are dropped.
        """
        payload: Mapping[str, Any] = {
            "callback_query": {
                "id": "query_4",
                "data": "ticket_accept_42",
                "message": {},
            }
        }

        usecase.execute(update_data=payload)

        mock_accept_ticket.execute.assert_not_called()  # type: ignore[union-attr]
        mock_client.answer_callback_query.assert_not_called()  # type: ignore[union-attr]

    def test_process_webhook_private_start_command(
        self,
        usecase: ProcessTelegramWebhookCase,
        mock_client: TelegramClientProtocol | MagicMock,
        mocker: MockerFixture,
    ) -> None:
        """
        Happy path: Route /start command in private chat and dispatch welcome message.
        """
        mocker.patch("apps.telegram.usecases.get_base_url", return_value="https://shop.test")
        mocker.patch("apps.telegram.usecases.shop_config.get", return_value="Welcome to shop!")
        payload: Mapping[str, Any] = {
            "message": {
                "message_id": 10,
                "chat": {"id": 12345, "type": "private"},
                "text": "/start",
            }
        }

        usecase.execute(update_data=payload)

        mock_client.send_message.assert_called_once_with(  # type: ignore[union-attr]
            chat_id=12345,
            text="Welcome to shop!",
            reply_markup={"inline_keyboard": [[{"text": "Open", "web_app": {"url": "https://shop.test"}}]]},
        )

    def test_process_webhook_private_user_reply(
        self,
        usecase: ProcessTelegramWebhookCase,
        mock_user_reply: UserReplyCase | MagicMock,
    ) -> None:
        """
        Happy path: Route regular text message in private chat to UserReplyCase.
        """
        payload: Mapping[str, Any] = {
            "message": {
                "message_id": 15,
                "chat": {"id": 12345, "type": "private"},
                "text": "Hello support",
                "reply_to_message": {"message_id": 12},
            }
        }

        usecase.execute(update_data=payload)

        mock_user_reply.execute.assert_called_once_with(  # type: ignore[union-attr]
            user_tg_id=12345,
            message_id=15,
            reply_to_message_id=12,
            text="Hello support",
        )

    def test_process_webhook_group_admin_reply(
        self,
        usecase: ProcessTelegramWebhookCase,
        mock_admin_reply: AdminReplyCase | MagicMock,
    ) -> None:
        """
        Happy path: Route topic reply in supergroup to AdminReplyCase.
        """
        payload: Mapping[str, Any] = {
            "message": {
                "message_id": 20,
                "chat": {"id": -100999, "type": "supergroup"},
                "message_thread_id": 555,
                "text": "Support response here",
                "from": {"is_bot": False},
            }
        }

        usecase.execute(update_data=payload)

        mock_admin_reply.execute.assert_called_once_with(  # type: ignore[union-attr]
            topic_id=555,
            message_id=20,
            admin_chat_id=-100999,
            text="Support response here",
        )

    def test_process_webhook_group_bot_message_ignored(
        self,
        usecase: ProcessTelegramWebhookCase,
        mock_admin_reply: AdminReplyCase | MagicMock,
    ) -> None:
        """
        Edge case: Ignore messages sent by other bots in group topics.
        """
        payload: Mapping[str, Any] = {
            "message": {
                "message_id": 21,
                "chat": {"id": -100999, "type": "supergroup"},
                "message_thread_id": 555,
                "text": "Bot automated notification",
                "from": {"is_bot": True},
            }
        }

        usecase.execute(update_data=payload)

        mock_admin_reply.execute.assert_not_called()  # type: ignore[union-attr]

    def test_process_webhook_unsupported_update_ignored(
        self,
        usecase: ProcessTelegramWebhookCase,
        mock_client: TelegramClientProtocol | MagicMock,
    ) -> None:
        """
        Edge case: Ignore unsupported or empty payloads gracefully.
        """
        payload: Mapping[str, Any] = {"poll_answer": {"poll_id": "123"}}

        usecase.execute(update_data=payload)

        mock_client.send_message.assert_not_called()  # type: ignore[union-attr]
        mock_client.answer_callback_query.assert_not_called()  # type: ignore[union-attr]
