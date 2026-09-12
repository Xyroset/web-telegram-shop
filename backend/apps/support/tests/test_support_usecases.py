from typing import cast
from unittest.mock import MagicMock, patch

import pytest
from pytest_mock import MockerFixture

from apps.core.domain.exceptions import CoreObjectNotFoundError
from apps.support.domain.exceptions import SupportInvalidTicketStateError, SupportTicketLimitExceededError
from apps.support.models import Ticket, TicketMessage
from apps.support.repo import TicketRepository
from apps.support.usecases import (
    AcceptTicketCase,
    AdminReplyCase,
    CloseTicketCase,
    CreateTicketCase,
    DeleteClosedTopicsCase,
    RejectTicketCase,
    UserReplyCase,
)
from apps.telegram.domain.interfaces import TelegramClientProtocol
from apps.users.models import User
from apps.users.repo import UserSettingsDataRepository


class TestCreateTicketCase:
    def test_create_ticket_success(self, mocker: MockerFixture) -> None:
        mocker.patch("django.db.transaction.atomic", MagicMock())
        mocker.patch("django.db.transaction.on_commit", side_effect=lambda f: f())
        mock_send_task = mocker.patch("apps.support.usecases.lifecycle.current_app.send_task")

        mock_repo: TicketRepository | MagicMock = MagicMock(spec=TicketRepository)
        mock_repo.get_active_tickets_count.return_value = 0  # type: ignore[union-attr]

        mock_ticket = MagicMock(spec=Ticket)
        mock_ticket.id = 1
        mock_repo.create.return_value = mock_ticket  # type: ignore[union-attr]

        mock_msg = MagicMock(spec=TicketMessage)
        mock_ticket.prepare_message.return_value = mock_msg

        mock_user = MagicMock(spec=User)
        usecase = CreateTicketCase(ticket_repo=mock_repo)

        usecase.execute(user=mock_user, category="bug", message_text="Help me")

        mock_repo.create.assert_called_once_with(user=mock_user, category="bug")  # type: ignore[union-attr]
        mock_ticket.prepare_message.assert_called_once_with(text="Help me", sender_is_admin=False)
        mock_repo.save_message.assert_called_once_with(message=mock_msg)  # type: ignore[union-attr]
        mock_send_task.assert_called_once_with(
            "notifications.dispatch_admin_support_ticket_notifications",
            args=["1"],
        )

    def test_create_ticket_limit_exceeded(self) -> None:
        mock_repo: TicketRepository | MagicMock = MagicMock(spec=TicketRepository)
        mock_repo.get_active_tickets_count.return_value = 3  # type: ignore[union-attr]

        mock_user = MagicMock(spec=User)
        usecase = CreateTicketCase(ticket_repo=mock_repo)

        with pytest.raises(SupportTicketLimitExceededError):
            usecase.execute(user=mock_user, category="bug", message_text="Help me")


class TestAcceptTicketCase:
    @patch("django.db.transaction.atomic", MagicMock())
    def test_accept_ticket_success(self) -> None:
        mock_repo: TicketRepository | MagicMock = MagicMock(spec=TicketRepository)
        mock_bot: TelegramClientProtocol | MagicMock = MagicMock(spec=TelegramClientProtocol)

        mock_ticket = MagicMock(spec=Ticket)
        mock_ticket.id = 10
        mock_ticket.triage_message_id = 999
        mock_ticket.first_message = MagicMock(spec=TicketMessage, text="Issue text")
        mock_ticket.category = "general"
        mock_ticket.user.tg_id = 12345
        mock_ticket.user.tg_username = "testuser"
        mock_ticket.user.settings.current_language_code = "en"
        mock_ticket.mark_as_in_progress.return_value = ["state", "forum_topic_id"]

        mock_repo.get_by_id_with_full_details.return_value = mock_ticket  # type: ignore[union-attr]
        mock_bot.create_forum_topic.return_value = 555  # type: ignore[union-attr]
        mock_bot.copy_message.return_value = 777  # type: ignore[union-attr]

        usecase = AcceptTicketCase(ticket_repo=mock_repo, bot_client=mock_bot)

        usecase.execute(ticket_id=10, message_id=100, chat_id=-100123)

        mock_bot.create_forum_topic.assert_called_once()  # type: ignore[union-attr]
        mock_bot.edit_message.assert_called_once()  # type: ignore[union-attr]
        mock_bot.copy_message.assert_called_once()  # type: ignore[union-attr]
        mock_bot.send_message.assert_called_once()  # type: ignore[union-attr]
        mock_ticket.mark_as_in_progress.assert_called_once_with(forum_topic_id=555, first_copy_triage_message_id=777)
        mock_repo.save.assert_called_once_with(instance=mock_ticket, update_fields=["state", "forum_topic_id"])  # type: ignore[union-attr]

    def test_accept_ticket_missing_triage_message(self) -> None:
        mock_repo: TicketRepository | MagicMock = MagicMock(spec=TicketRepository)
        mock_bot: TelegramClientProtocol | MagicMock = MagicMock(spec=TelegramClientProtocol)

        mock_ticket = MagicMock(spec=Ticket)
        mock_ticket.triage_message_id = None
        mock_ticket.first_message = MagicMock(spec=TicketMessage)

        mock_repo.get_by_id_with_full_details.return_value = mock_ticket  # type: ignore[union-attr]
        usecase = AcceptTicketCase(ticket_repo=mock_repo, bot_client=mock_bot)

        with pytest.raises(SupportInvalidTicketStateError):
            usecase.execute(ticket_id=10, message_id=100, chat_id=-100123)


class TestRejectTicketCase:
    @patch("django.db.transaction.atomic", MagicMock())
    def test_reject_ticket_success(self) -> None:
        mock_repo: TicketRepository | MagicMock = MagicMock(spec=TicketRepository)
        mock_bot: TelegramClientProtocol | MagicMock = MagicMock(spec=TelegramClientProtocol)

        mock_ticket = MagicMock(spec=Ticket)
        mock_ticket.first_message = MagicMock(spec=TicketMessage, text="Issue text")
        mock_ticket.category = "general"
        mock_ticket.user.tg_id = 12345
        mock_ticket.user.tg_username = "testuser"
        mock_ticket.user.settings.current_language_code = "en"
        mock_ticket.mark_as_closed.return_value = ["state"]

        mock_repo.get_by_id_with_full_details.return_value = mock_ticket  # type: ignore[union-attr]
        usecase = RejectTicketCase(ticket_repo=mock_repo, bot_client=mock_bot)

        usecase.execute(ticket_id=10, message_id=100, chat_id=-100123)

        mock_ticket.mark_as_closed.assert_called_once()
        mock_repo.save.assert_called_once_with(instance=mock_ticket, update_fields=["state"])  # type: ignore[union-attr]
        mock_bot.edit_message.assert_called_once()  # type: ignore[union-attr]
        mock_bot.send_message.assert_called_once()  # type: ignore[union-attr]


@patch("django.db.transaction.atomic", MagicMock())
class TestCloseTicketCase:
    def test_close_ticket_by_admin_in_progress(self) -> None:
        mock_repo: TicketRepository | MagicMock = MagicMock(spec=TicketRepository)
        mock_bot: TelegramClientProtocol | MagicMock = MagicMock(spec=TelegramClientProtocol)

        mock_ticket = MagicMock(spec=Ticket)
        mock_ticket.state = Ticket.Status.IN_PROGRESS
        mock_ticket.user.tg_id = 12345
        mock_ticket.user.tg_username = "testuser"
        mock_ticket.user.settings.current_language_code = "en"
        mock_ticket.forum_topic_id = 555
        mock_ticket.mark_as_closed.return_value = ["state"]

        mock_repo.get_by_id_with_full_details.return_value = mock_ticket  # type: ignore[union-attr]
        usecase = CloseTicketCase(ticket_repo=mock_repo, bot_client=mock_bot, admin_chat_id=-100123)

        usecase.execute(ticket_id=10, message_id=100, chat_id=-100123, closed_by_admin=True)

        mock_ticket.mark_as_closed.assert_called_once()
        mock_repo.save.assert_called_once_with(instance=mock_ticket, update_fields=["state"])  # type: ignore[union-attr]
        mock_bot.edit_message_reply_markup.assert_called_once()  # type: ignore[union-attr]
        mock_bot.close_forum_topic.assert_called_once()  # type: ignore[union-attr]
        mock_bot.send_message.assert_called()  # type: ignore[union-attr]

    def test_close_already_closed_ticket_returns_early(self) -> None:
        mock_repo: TicketRepository | MagicMock = MagicMock(spec=TicketRepository)
        mock_bot: TelegramClientProtocol | MagicMock = MagicMock(spec=TelegramClientProtocol)

        mock_ticket = MagicMock(spec=Ticket)
        mock_ticket.state = Ticket.Status.CLOSED
        mock_repo.get_by_id_with_full_details.return_value = mock_ticket  # type: ignore[union-attr]

        usecase = CloseTicketCase(ticket_repo=mock_repo, bot_client=mock_bot, admin_chat_id=-100123)

        usecase.execute(ticket_id=10, message_id=100, chat_id=-100123, closed_by_admin=True)

        mock_bot.edit_message_reply_markup.assert_called_once()  # type: ignore[union-attr]
        mock_ticket.mark_as_closed.assert_not_called()
        mock_repo.save.assert_not_called()  # type: ignore[union-attr]


@patch("django.db.transaction.atomic", MagicMock())
class TestAdminReplyCase:
    def test_admin_reply_success(self) -> None:
        mock_repo: TicketRepository | MagicMock = MagicMock(spec=TicketRepository)
        mock_bot: TelegramClientProtocol | MagicMock = MagicMock(spec=TelegramClientProtocol)

        mock_ticket = MagicMock(spec=Ticket)
        mock_ticket.state = Ticket.Status.IN_PROGRESS
        mock_ticket.user.tg_id = 12345
        mock_ticket.category = "general"
        mock_ticket.user.settings.current_language_code = "en"

        mock_msg = MagicMock(spec=TicketMessage)
        mock_ticket.prepare_message.return_value = mock_msg

        mock_repo.get_by_id_with_full_details.return_value = mock_ticket  # type: ignore[union-attr]
        mock_bot.copy_message.return_value = 999  # type: ignore[union-attr]

        usecase = AdminReplyCase(ticket_repo=mock_repo, bot_client=mock_bot)

        usecase.execute(topic_id=555, message_id=100, admin_chat_id=-100123, text="Reply")

        mock_bot.send_message.assert_called_once()  # type: ignore[union-attr]
        mock_bot.copy_message.assert_called_once_with(chat_id=12345, from_chat_id=-100123, message_id=100)  # type: ignore[union-attr]
        mock_ticket.prepare_message.assert_called_once_with(text="Reply", sender_is_admin=True, telegram_message_id=999)
        mock_repo.save_message.assert_called_once_with(message=mock_msg)  # type: ignore[union-attr]

    def test_admin_reply_ignores_not_found(self) -> None:
        mock_repo: TicketRepository | MagicMock = MagicMock(spec=TicketRepository)
        mock_bot: TelegramClientProtocol | MagicMock = MagicMock(spec=TelegramClientProtocol)

        mock_repo.get_by_id_with_full_details.side_effect = CoreObjectNotFoundError  # type: ignore[union-attr]
        usecase = AdminReplyCase(ticket_repo=mock_repo, bot_client=mock_bot)

        usecase.execute(topic_id=555, message_id=100, admin_chat_id=-100123, text="Reply")

        mock_bot.copy_message.assert_not_called()  # type: ignore[union-attr]
        mock_repo.save_message.assert_not_called()  # type: ignore[union-attr]


@patch("django.db.transaction.atomic", MagicMock())
class TestUserReplyCase:
    def test_user_reply_explicit_success(self) -> None:
        mock_repo: TicketRepository | MagicMock = MagicMock(spec=TicketRepository)
        mock_settings_repo: UserSettingsDataRepository | MagicMock = MagicMock(spec=UserSettingsDataRepository)
        mock_bot: TelegramClientProtocol | MagicMock = MagicMock(spec=TelegramClientProtocol)

        mock_ticket = MagicMock(spec=Ticket)
        mock_ticket.state = Ticket.Status.IN_PROGRESS
        mock_ticket.forum_topic_id = 555

        mock_msg = MagicMock(spec=TicketMessage)
        mock_ticket.prepare_message.return_value = mock_msg

        mock_settings = MagicMock()
        mock_settings.current_language_code = "en"
        mock_settings_repo.get_by.return_value = mock_settings  # type: ignore[union-attr]
        mock_repo.get_by.return_value = mock_ticket  # type: ignore[union-attr]

        usecase = UserReplyCase(
            ticket_repo=mock_repo,
            user_settings_repo=mock_settings_repo,
            bot_client=mock_bot,
            admin_chat_id=-100123,
        )

        usecase.execute(user_tg_id=12345, message_id=100, reply_to_message_id=999, text="My reply")

        mock_ticket.prepare_message.assert_called_once_with(
            text="My reply", sender_is_admin=False, telegram_message_id=100
        )
        mock_repo.save_message.assert_called_once_with(message=mock_msg)  # type: ignore[union-attr]
        cast(MagicMock, mock_bot.copy_message).assert_called_once_with(
            chat_id=-100123,
            from_chat_id=12345,
            message_id=100,
            message_thread_id=555,
            disable_notification=True,
        )

    def test_user_reply_multiple_tickets_warning(self) -> None:
        mock_repo: TicketRepository | MagicMock = MagicMock(spec=TicketRepository)
        mock_settings_repo: UserSettingsDataRepository | MagicMock = MagicMock(spec=UserSettingsDataRepository)
        mock_bot: TelegramClientProtocol | MagicMock = MagicMock(spec=TelegramClientProtocol)

        mock_settings = MagicMock()
        mock_settings.current_language_code = "en"
        mock_settings_repo.get_by.return_value = mock_settings  # type: ignore[union-attr]

        mock_repo.get_first_active_user_tickets.return_value = (None, False)  # type: ignore[union-attr]

        usecase = UserReplyCase(
            ticket_repo=mock_repo,
            user_settings_repo=mock_settings_repo,
            bot_client=mock_bot,
            admin_chat_id=-100123,
        )

        usecase.execute(user_tg_id=12345, message_id=100, reply_to_message_id=None, text="My reply")

        mock_bot.send_message.assert_called_once()  # type: ignore[union-attr]
        mock_repo.save_message.assert_not_called()  # type: ignore[union-attr]


@patch("django.db.transaction.atomic", MagicMock())
class TestDeleteClosedTopicsCase:
    def test_delete_closed_topics_success(self) -> None:
        mock_repo: TicketRepository | MagicMock = MagicMock(spec=TicketRepository)
        mock_bot: TelegramClientProtocol | MagicMock = MagicMock(spec=TelegramClientProtocol)

        mock_ticket = MagicMock(spec=Ticket)
        mock_ticket.id = 10
        mock_ticket.forum_topic_id = 555
        mock_ticket.clear_forum_topic.return_value = ["forum_topic_id"]

        mock_repo.get_closed_tickets_with_topics.return_value = [mock_ticket]  # type: ignore[union-attr]
        mock_repo.get_by_id_with_full_details.return_value = mock_ticket  # type: ignore[union-attr]

        usecase = DeleteClosedTopicsCase(ticket_repo=mock_repo, bot_client=mock_bot, admin_chat_id=-100123)

        usecase.execute(older_than_days=7)

        mock_bot.delete_forum_topic.assert_called_once_with(chat_id=-100123, message_thread_id=555)  # type: ignore[union-attr]
        mock_ticket.clear_forum_topic.assert_called_once()
        mock_repo.save.assert_called_once_with(instance=mock_ticket, update_fields=["forum_topic_id"])  # type: ignore[union-attr]
