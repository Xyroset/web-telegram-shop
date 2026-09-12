from collections.abc import Sequence
from datetime import datetime
from typing import Any

from apps.core.domain.exceptions import CoreMultipleObjectsFoundError, CoreObjectNotFoundError
from apps.core.repo import BaseRepository
from apps.support.models import Ticket, TicketMessage
from apps.users.models import User


class TicketRepository(BaseRepository[Ticket]):
    def __init__(self) -> None:
        super().__init__(model_class=Ticket)

    def save_message(self, message: TicketMessage, update_fields: Sequence[str] | None = None) -> None:
        """Save a ticket message instance with optional field constraints."""
        message.save(update_fields=update_fields)

    def get_active_tickets_count(self, user: User) -> int:
        """Count all active tickets (OPEN or IN_PROGRESS) for a given user."""
        return self.model_class.objects.filter(
            user=user,
            state__in=[self.model_class.Status.OPEN, self.model_class.Status.IN_PROGRESS],
        ).count()

    def get_first_active_user_tickets(self, user_tg_id: int) -> tuple[Ticket | None, bool]:
        """Fetch the single active user ticket if exactly one exists."""
        active_tickets = list(
            self.model_class.objects.filter(
                user_id=user_tg_id,
                state__in=[self.model_class.Status.OPEN, self.model_class.Status.IN_PROGRESS],
            )[:2]
        )

        if len(active_tickets) == 1:
            return active_tickets[0], True
        return None, False

    def get_by_id_with_full_details(self, for_update: bool = False, **filters: Any) -> Ticket:
        """Retrieve a single ticket with related relations and optional row-level locking."""
        if not filters:
            raise ValueError("At least one filter parameter must be provided to get_by_id_with_full_details().")

        try:
            if for_update:
                return (
                    self.model_class.objects.select_related("user", "user__settings")
                    .prefetch_related("messages")
                    .select_for_update(of=("self",))
                    .get(**filters)
                )
            return self.model_class.objects.select_related("user").prefetch_related("messages").get(**filters)
        except self.model_class.DoesNotExist:
            filters_str = ", ".join(f"{key}={value}" for key, value in filters.items())
            raise CoreObjectNotFoundError(f"Object not found! Filters: {filters_str}")
        except self.model_class.MultipleObjectsReturned:
            filters_str = ", ".join(f"{key}={value}" for key, value in filters.items())
            raise CoreMultipleObjectsFoundError(f"Expected 1 object, but found multiple! Filters: {filters_str}")

    def get_closed_tickets_with_topics(self, closed_before: datetime) -> Sequence[Ticket]:
        """Retrieve closed tickets with assigned forum topics updated prior to a given timestamp."""
        return list(
            self.model_class.objects.filter(
                state=self.model_class.Status.CLOSED,
                forum_topic_id__isnull=False,
                updated_at__lte=closed_before,
            )
        )
