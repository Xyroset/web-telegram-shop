import logging
from typing import Final

from celery import current_app
from django.db import transaction as ts

from apps.core.config_manager import shop_config
from apps.core.utils import safe_format
from apps.support.domain.exceptions import SupportInvalidTicketStateError, SupportTicketLimitExceededError
from apps.support.models import Ticket
from apps.support.repo import TicketRepository
from apps.telegram.domain.interfaces import TelegramClientProtocol
from apps.users.models import User

logger: Final[logging.Logger] = logging.getLogger(__name__)


class CreateTicketCase:
    """
    Creates a new support ticket initiated by a customer.

    **Business Rules:**
    - Checks the maximum active tickets limit per user (OPEN and IN_PROGRESS).
    - Persists the new Ticket and initial customer message.
    - Dispatches a Celery notification task for administrators upon transaction commit.

    **Required:**
    - Active tickets count must NOT exceed the configured limit. Otherwise error — **SupportTicketLimitExceededError**.
    """

    def __init__(self, ticket_repo: TicketRepository) -> None:
        self._ticket_repo = ticket_repo

    def execute(self, user: User, category: str, message_text: str) -> None:
        limit = int(shop_config.get("support", "support_settings.limit_active_tickets_per_user", 1))
        active_count = self._ticket_repo.get_active_tickets_count(user=user)

        if active_count >= limit:
            raise SupportTicketLimitExceededError(
                f"You can only have {limit} active tickets at a time. Please wait for a response."
            )

        with ts.atomic():
            ticket = self._ticket_repo.create(user=user, category=category)
            ticket_msg = ticket.prepare_message(text=message_text, sender_is_admin=False)
            self._ticket_repo.save_message(message=ticket_msg)

        ts.on_commit(
            lambda: current_app.send_task(
                "notifications.dispatch_admin_support_ticket_notifications",
                args=[str(ticket.id)],
            )
        )


class AcceptTicketCase:
    """
    Accepts an open support ticket and initializes a 2-Way Chat forum topic.

    **Business Rules:**
    - External API calls must execute OUTSIDE the database transaction to prevent blocking.
    - Locks the ticket row (`select_for_update`) ONLY during state mutation.
    - Updates the ticket state to IN_PROGRESS and saves the topic ID using `update_fields`.
    - Fails strictly if the initial user message lacks a `telegram_message_id`.

    **Required:**
    - The initial message and triage message ID MUST exist on the ticket.
    Otherwise error — **SupportInvalidTicketStateError**.
    - The ticket MUST be in OPEN state before accepting. Otherwise error — **SupportInvalidTicketStateError**.
    """

    def __init__(self, ticket_repo: TicketRepository, bot_client: TelegramClientProtocol) -> None:
        self._ticket_repo = ticket_repo
        self._bot_client = bot_client
        self._lang = shop_config.get("support", "support_language", "en")

    def execute(self, ticket_id: int, message_id: int, chat_id: int | str) -> None:
        ticket = self._ticket_repo.get_by_id_with_full_details(for_update=False, id=ticket_id)
        first_msg = ticket.first_message

        if not first_msg or not ticket.triage_message_id:
            raise SupportInvalidTicketStateError(f"Initial message for ticket {ticket.id} lacks telegram_message_id.")

        user_tg_id = ticket.user.tg_id
        user_tg_username = ticket.user.tg_username
        user_language = ticket.user.settings.current_language_code
        msg_telegram_id = ticket.triage_message_id
        message_text = first_msg.text
        category = ticket.category.upper()

        topic_template = shop_config.get(
            "locales",
            f"{self._lang}.support.topic_name",
            "[{state}] #{ticket_id} - @{tg_username}",
        )
        topic_name = safe_format(
            topic_template,
            {"state": "OPEN", "ticket_id": ticket.id, "tg_username": user_tg_username},
        )

        forum_topic_id = self._bot_client.create_forum_topic(chat_id=chat_id, name=topic_name)

        clean_chat_id = str(chat_id).replace("-100", "")
        topic_url = f"https://t.me/c/{clean_chat_id}/{forum_topic_id}"
        context = {
            "ticket_id": ticket_id,
            "tg_username": user_tg_username,
            "tg_id": user_tg_id,
            "category": category,
            "message": message_text,
            "topic_url": topic_url,
        }

        accept_template = shop_config.get(
            "locales",
            f"{self._lang}.support.ticket_accepted_edit",
            "<b>Ticket #{ticket_id} Accepted</b>\n"
            "<b>User:</b> @{tg_username} (ID: <code>{tg_id}</code>)\n"
            "<b>Category:</b> {category}\n\n<i>{message}</i>",
        )
        btn_text = shop_config.get("locales", f"{self._lang}.support.buttons.go_to_topic", "Go to Topic")

        reply_markup = {"inline_keyboard": [[{"text": f"➡️ {btn_text}", "url": topic_url}]]}

        admin_close_text = shop_config.get("locales", f"{self._lang}.support.buttons.close_ticket", "Close Ticket")
        admin_keyboard = {
            "inline_keyboard": [[{"text": f"❌ {admin_close_text}", "callback_data": f"ticket_close_{ticket_id}"}]]
        }

        try:
            self._bot_client.edit_message(
                chat_id=chat_id,
                message_id=message_id,
                text=safe_format(f"✅ {accept_template}", context),
                reply_markup=reply_markup,
            )
        except Exception as exc:
            logger.error(f"Failed to edit Triage message for ticket {ticket_id}: {exc}")

        first_copy_triage_message_id: int | None = None
        try:
            first_copy_triage_message_id = self._bot_client.copy_message(
                chat_id=chat_id,
                from_chat_id=chat_id,
                message_id=msg_telegram_id,
                message_thread_id=forum_topic_id,
                reply_markup=admin_keyboard,
                disable_notification=True,
            )
        except Exception as exc:
            logger.error(f"Failed to copy user message to Topic for ticket {ticket_id}: {exc}")

        with ts.atomic():
            locked_ticket = self._ticket_repo.get_by_id_with_full_details(for_update=True, id=ticket_id)
            update_fields = locked_ticket.mark_as_in_progress(
                forum_topic_id=forum_topic_id,
                first_copy_triage_message_id=first_copy_triage_message_id,
            )
            self._ticket_repo.save(instance=locked_ticket, update_fields=update_fields)

        notify_template = shop_config.get(
            "locales",
            f"{user_language}.support.ticket_accepted_user_notify",
            "Your support ticket <b>#{ticket_id}</b> has been accepted.",
        )

        user_cancel_text = shop_config.get(
            "locales", f"{user_language}.support.buttons.cancel_request", "Cancel Request"
        )
        user_keyboard = {
            "inline_keyboard": [[{"text": f"❌ {user_cancel_text}", "callback_data": f"ticket_close_{ticket_id}"}]]
        }

        try:
            self._bot_client.send_message(
                chat_id=user_tg_id,
                text=safe_format(f"✅ {notify_template}", context),
                reply_markup=user_keyboard,
            )
        except Exception as exc:
            logger.error(f"Failed to notify user {user_tg_id} of ticket acceptance: {exc}")


class RejectTicketCase:
    """
    Rejects an open support ticket and notifies the user.

    **Business Rules:**
    - Closes the ticket domain entity in the database within a row-lock transaction.
    - Edits the triage admin message to reflect the rejected status.
    - Sends a rejection notification directly to the user in their preferred language.

    **Required:**
    - Ticket must contain linked messages. Otherwise error — **SupportInvalidTicketStateError**.
    - Ticket must not be already closed or resolved. Otherwise error — **SupportInvalidTicketStateError**.
    """

    def __init__(self, ticket_repo: TicketRepository, bot_client: TelegramClientProtocol) -> None:
        self._ticket_repo = ticket_repo
        self._bot_client = bot_client
        self._lang = shop_config.get("support", "language", "en")

    def execute(self, ticket_id: int, message_id: int, chat_id: int | str) -> None:
        ticket = self._ticket_repo.get_by_id_with_full_details(for_update=False, id=ticket_id)
        first_msg = ticket.first_message

        if not first_msg:
            raise SupportInvalidTicketStateError(f"Ticket {ticket.id} has no linked messages.")

        user_tg_id = ticket.user.tg_id
        user_tg_username = ticket.user.tg_username
        user_language = ticket.user.settings.current_language_code
        message_text = first_msg.text
        category = ticket.category.upper()

        with ts.atomic():
            locked_ticket = self._ticket_repo.get_by_id_with_full_details(for_update=True, id=ticket_id)
            update_fields = locked_ticket.mark_as_closed()
            self._ticket_repo.save(instance=locked_ticket, update_fields=update_fields)

        context = {
            "ticket_id": ticket_id,
            "tg_username": user_tg_username,
            "tg_id": user_tg_id,
            "category": category,
            "message": message_text,
        }

        reject_template = shop_config.get(
            "locales",
            f"{self._lang}.support.ticket_rejected_edit",
            "<b>Ticket #{ticket_id} Rejected</b>\n"
            "<b>User:</b> @{tg_username} (ID: <code>{tg_id}</code>)\n"
            "<b>Category:</b> {category}\n\n<i>{message}</i>",
        )

        try:
            self._bot_client.edit_message(
                chat_id=chat_id,
                message_id=message_id,
                text=safe_format(f"❌ {reject_template}", context),
                reply_markup=None,
            )
        except Exception as exc:
            logger.error(f"Failed to edit Triage message for rejected ticket {ticket_id}: {exc}")

        notify_template = shop_config.get(
            "locales",
            f"{user_language}.support.ticket_rejected_user_notify",
            "Your support ticket <b>#{ticket_id}</b> was rejected.",
        )
        try:
            self._bot_client.send_message(
                chat_id=user_tg_id,
                text=safe_format(f"❌ {notify_template}", context),
            )
        except Exception as exc:
            logger.error(f"Failed to notify user {user_tg_id} of ticket rejection: {exc}")


class CloseTicketCase:
    """
    Closes an active or open support ticket (Cancellation or Resolution).

    **Business Rules:**
    - Can be triggered by either the User (cancellation) or the Admin (resolution).
    - Locks the ticket row (`select_for_update`) only during state mutation.
    - If the ticket was IN_PROGRESS, notifies the topic and closes the Telegram Forum Topic.
    - If the ticket was OPEN, updates the triage message in the admin group.
    - Removes inline buttons from the message that triggered the action.

    **Required:**
    - If ticket is already closed or resolved, markup is cleared and execution terminates without re-saving.
    """

    def __init__(
        self,
        ticket_repo: TicketRepository,
        bot_client: TelegramClientProtocol,
        admin_chat_id: int | str,
    ) -> None:
        self._ticket_repo = ticket_repo
        self._bot_client = bot_client
        self._admin_chat_id = admin_chat_id
        self._lang = shop_config.get("support", "language", "en")

    def execute(self, ticket_id: int, message_id: int, chat_id: int | str, closed_by_admin: bool) -> None:
        ticket = self._ticket_repo.get_by_id_with_full_details(for_update=False, id=ticket_id)
        old_state = ticket.state

        if old_state in [Ticket.Status.CLOSED, Ticket.Status.RESOLVED]:
            self._bot_client.edit_message_reply_markup(chat_id=chat_id, message_id=message_id)
            return

        user_tg_id = ticket.user.tg_id
        user_language = ticket.user.settings.current_language_code
        triage_msg_id = ticket.triage_message_id
        topic_id = ticket.forum_topic_id

        with ts.atomic():
            locked_ticket = self._ticket_repo.get_by_id_with_full_details(for_update=True, id=ticket_id)
            update_fields = locked_ticket.mark_as_closed()
            self._ticket_repo.save(instance=locked_ticket, update_fields=update_fields)

        try:
            self._bot_client.edit_message_reply_markup(chat_id=chat_id, message_id=message_id)
        except Exception as exc:
            logger.error(f"Failed to remove markup for ticket {ticket_id}: {exc}")

        if old_state == Ticket.Status.OPEN:
            if not closed_by_admin and triage_msg_id:
                template = shop_config.get(
                    "locales",
                    f"{self._lang}.support.ticket_canceled_edit",
                    "<b>Ticket #{ticket_id} Canceled by User</b>",
                )
                try:
                    self._bot_client.edit_message(
                        chat_id=self._admin_chat_id,
                        message_id=triage_msg_id,
                        text=safe_format(f"🚫 {template}", {"ticket_id": ticket_id}),
                    )
                except Exception as exc:
                    logger.error(f"Failed to update triage message for canceled ticket {ticket_id}: {exc}")

        elif old_state == Ticket.Status.IN_PROGRESS and topic_id:
            topic_msg_key = "ticket_closed_by_admin_topic" if closed_by_admin else "ticket_closed_by_user_topic"
            default_topic_msg = "<b>Ticket closed by Admin</b>" if closed_by_admin else "<b>Ticket closed by User</b>"
            topic_msg = shop_config.get("locales", f"{self._lang}.support.{topic_msg_key}", default_topic_msg)

            topic_template = shop_config.get(
                "locales",
                f"{self._lang}.support.topic_name",
                "[{state}] #{ticket_id} - @{tg_username}",
            )
            new_topic_name = safe_format(
                topic_template,
                {"state": "CLOSED", "ticket_id": ticket.id, "tg_username": ticket.user.tg_username},
            )

            if not closed_by_admin:
                if ticket.first_copy_triage_message_id:
                    try:
                        self._bot_client.edit_message_reply_markup(
                            chat_id=self._admin_chat_id,
                            message_id=int(ticket.first_copy_triage_message_id),
                        )
                    except Exception as exc:
                        logger.error(f"Failed to remove markup for ticket {ticket_id}: {exc}")
                else:
                    logger.error(f"Failed to remove markup for ticket {ticket_id}. Message id is None")

            try:
                self._bot_client.send_message(
                    chat_id=self._admin_chat_id,
                    text=f"🔒 {topic_msg}",
                    message_thread_id=topic_id,
                    disable_notification=True,
                )
                self._bot_client.close_forum_topic(
                    chat_id=self._admin_chat_id,
                    message_thread_id=topic_id,
                    name=new_topic_name,
                )
            except Exception as exc:
                logger.error(f"Failed to close topic for ticket {ticket_id}: {exc}")

            user_notify_key = (
                "ticket_closed_by_admin_user_notify" if closed_by_admin else "ticket_closed_by_user_user_notify"
            )
            default_user_notify = (
                f"Your support ticket <b>#{ticket_id}</b> has been closed."
                if closed_by_admin
                else f"You have closed support ticket <b>#{ticket_id}</b>."
            )
            user_notify = shop_config.get("locales", f"{user_language}.support.{user_notify_key}", default_user_notify)

            try:
                self._bot_client.send_message(
                    chat_id=user_tg_id,
                    text=safe_format(f"🔒 {user_notify}", {"ticket_id": ticket_id}),
                )
            except Exception as exc:
                logger.error(f"Failed to notify user about ticket closure {ticket_id}: {exc}")
