import logging

from django.db import transaction as ts

from apps.core.config_manager import shop_config
from apps.core.domain.exceptions import CoreObjectNotFoundError
from apps.core.utils import safe_format
from apps.support.models import Ticket
from apps.support.repo import TicketRepository
from apps.telegram.domain.interfaces import TelegramClientProtocol
from apps.users.repo import UserSettingsDataRepository

logger = logging.getLogger(__name__)


class AdminReplyCase:
    """
    Routes an administrator message from the support forum topic to the user's private chat.

    **Business Rules:**
    - Resolves the ticket assigned to the specific Telegram forum topic ID.
    - Sends a contextual notification header to the user.
    - Copies the administrator's message to the user, masking the administrator's identity.
    - Stores the message in the database with the resulting user message ID.
    - Ignores reply attempts if the ticket does not exist or is not in IN_PROGRESS state.

    **Required:**
    - The ticket repository MUST retrieve tickets by forum topic ID.
    - Telegram API calls MUST execute outside the database transaction.
    """

    def __init__(self, ticket_repo: TicketRepository, bot_client: TelegramClientProtocol) -> None:
        self._ticket_repo = ticket_repo
        self._bot_client = bot_client

    def execute(self, topic_id: int, message_id: int, admin_chat_id: int | str, text: str = "") -> None:
        try:
            ticket = self._ticket_repo.get_by_id_with_full_details(for_update=False, forum_topic_id=topic_id)
        except CoreObjectNotFoundError:
            logger.warning(f"Admin reply ignored: No ticket found for forum topic {topic_id}.")
            return

        if ticket.state != Ticket.Status.IN_PROGRESS:
            logger.warning(
                f"Admin reply ignored: Ticket {ticket.id} is in '{ticket.state}' state, expected IN_PROGRESS."
            )
            return

        user_tg_id = ticket.user.tg_id
        user_language = ticket.user.settings.current_language_code

        context_template = shop_config.get(
            "locales",
            f"{user_language}.support.admin_reply_prefix",
            "<b>Reply from Admin | Ticket #{ticket_id} ({category}):</b>",
        )

        context_text = safe_format(
            f"📩 {context_template}",
            {"ticket_id": ticket.id, "category": ticket.category.upper()},
        )

        try:
            self._bot_client.send_message(chat_id=user_tg_id, text=context_text)
            user_msg_id = self._bot_client.copy_message(
                chat_id=user_tg_id,
                from_chat_id=admin_chat_id,
                message_id=message_id,
            )
        except Exception as exc:
            logger.error(f"Failed to deliver admin message {message_id} to user {user_tg_id}: {exc}")
            return

        with ts.atomic():
            ticket_message = ticket.prepare_message(
                text=text,
                sender_is_admin=True,
                telegram_message_id=user_msg_id,
            )
            self._ticket_repo.save_message(message=ticket_message)


class UserReplyCase:
    """
    Routes a user reply from their direct chat to the corresponding admin forum topic.

    **Business Rules:**
    - Resolves the ticket via smart routing:
        1. Explicitly targets a ticket if the user replies to a bot support message.
        2. Implicitly targets the single active ticket if the user has exactly one in progress/open.
        3. Prompts the user to reply to a specific message if multiple or no active tickets are found.
    - Rejects routing if the ticket is not in IN_PROGRESS state or lacks an assigned forum topic.
    - Saves the user's message record and copies the message payload to the admin forum topic.

    **Required:**
    - The repository MUST check for active user tickets and retrieve message linkage.
    - Telegram API dispatch MUST execute outside the database transaction.
    """

    def __init__(
        self,
        ticket_repo: TicketRepository,
        user_settings_repo: UserSettingsDataRepository,
        bot_client: TelegramClientProtocol,
        admin_chat_id: int | str,
    ) -> None:
        self._ticket_repo = ticket_repo
        self._user_settings_repo = user_settings_repo
        self._bot_client = bot_client
        self._admin_chat_id = admin_chat_id

    def execute(
        self,
        user_tg_id: int,
        message_id: int,
        reply_to_message_id: int | None = None,
        text: str = "",
    ) -> None:
        ticket: Ticket | None = None

        try:
            user_settings = self._user_settings_repo.get_by(user_id=user_tg_id)
            user_language = user_settings.current_language_code
        except CoreObjectNotFoundError:
            user_language = "en"

        if reply_to_message_id is not None:
            try:
                ticket = self._ticket_repo.get_by(messages__telegram_message_id=reply_to_message_id)
            except CoreObjectNotFoundError:
                ticket = None

        if ticket is None:
            ticket, is_single_active = self._ticket_repo.get_first_active_user_tickets(user_tg_id=user_tg_id)
            if not is_single_active or ticket is None:
                self._send_warning(
                    chat_id=user_tg_id,
                    config_section="locales",
                    config_key=f"{user_language}.support.reply_required",
                    fallback=(
                        "You don't have any active support requests OR "
                        "You have multiple active requests. \nPlease <b>Reply</b> to a specific message to answer."
                    ),
                )
                return

        if ticket.state != Ticket.Status.IN_PROGRESS or not ticket.forum_topic_id:
            self._send_warning(
                chat_id=user_tg_id,
                config_section="locales",
                config_key=f"{user_language}.support.ticket_closed",
                fallback=f"Ticket #{ticket.id} is closed or not yet accepted by an admin.",
            )
            return

        with ts.atomic():
            ticket_message = ticket.prepare_message(
                text=text,
                sender_is_admin=False,
                telegram_message_id=message_id,
            )
            self._ticket_repo.save_message(message=ticket_message)

        try:
            self._bot_client.copy_message(
                chat_id=self._admin_chat_id,
                from_chat_id=user_tg_id,
                message_id=message_id,
                message_thread_id=ticket.forum_topic_id,
                disable_notification=True,
            )
        except Exception as exc:
            logger.error(f"Failed to route user message {message_id} to forum topic {ticket.forum_topic_id}: {exc}")

    def _send_warning(self, chat_id: int, config_section: str, config_key: str, fallback: str) -> None:
        template = shop_config.get(config_section, config_key, fallback)
        try:
            self._bot_client.send_message(chat_id=chat_id, text=safe_format(f"⚠️ {template}", {}))
        except Exception as exc:
            logger.error(f"Failed to send support warning message to {chat_id}: {exc}")
