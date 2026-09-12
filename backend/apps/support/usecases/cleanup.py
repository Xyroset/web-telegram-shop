import logging
from datetime import timedelta

from django.db import transaction as ts
from django.utils import timezone

from apps.support.repo import TicketRepository
from apps.telegram.domain.interfaces import TelegramClientProtocol

logger = logging.getLogger(__name__)


class DeleteClosedTopicsCase:
    """
    Cleans up old forum topics for closed support tickets to prevent Telegram group overflow.

    **Business Rules:**
    - Identifies tickets that are in CLOSED state and retain an active forum topic ID.
    - Filters tickets closed prior to the `older_than_days` cutoff window.
    - Sends a Telegram API request to delete each corresponding forum topic.
    - Nullifies the forum topic reference on the ticket domain entity upon processing.
    - Synchronizes the database state even if Telegram fails or the topic is already deleted.

    **Required:**
    - The repository MUST provide `get_closed_tickets_with_topics(closed_before)`.
    - Telegram API deletion MUST execute outside the database transaction.
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

    def execute(self, older_than_days: int = 7) -> None:
        cutoff_date = timezone.now() - timedelta(days=older_than_days)

        tickets = self._ticket_repo.get_closed_tickets_with_topics(closed_before=cutoff_date)

        if not tickets:
            logger.info("No old closed topics found for cleanup.")
            return

        for ticket in tickets:
            topic_id = ticket.forum_topic_id
            if not topic_id:
                continue

            try:
                self._bot_client.delete_forum_topic(
                    chat_id=self._admin_chat_id,
                    message_thread_id=topic_id,
                )
                logger.info(f"Successfully deleted forum topic {topic_id} for ticket {ticket.id}.")
            except Exception as exc:
                logger.warning(
                    f"Telegram failed to delete topic {topic_id} for ticket {ticket.id}. "
                    f"It might already be deleted. Error: {exc}"
                )

            with ts.atomic():
                locked_ticket = self._ticket_repo.get_by_id_with_full_details(for_update=True, id=ticket.id)
                update_fields = locked_ticket.clear_forum_topic()
                self._ticket_repo.save(instance=locked_ticket, update_fields=update_fields)
