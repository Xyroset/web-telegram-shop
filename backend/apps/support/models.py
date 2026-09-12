import uuid
from typing import TYPE_CHECKING, cast

from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.models import DefaultModel
from apps.support.domain.exceptions import SupportInvalidTicketStateError
from apps.users.models import User


class Ticket(DefaultModel):
    class Status(models.TextChoices):
        OPEN = "open", _("Open")
        IN_PROGRESS = "in_progress", _("In Progress")
        RESOLVED = "resolved", _("Resolved")
        CLOSED = "closed", _("Closed")

    class Category(models.TextChoices):
        BUG = "bug", _("Bug Report")
        ORDER_ISSUE = "order_issue", _("Order Issue")
        GENERAL = "general", _("General Question")

    id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="tickets",
        verbose_name=_("User"),
    )
    state = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.OPEN,
        verbose_name=_("State"),
    )
    category = models.CharField(
        max_length=20,
        choices=Category.choices,
        default=Category.GENERAL,
        verbose_name=_("Category"),
    )

    forum_topic_id = models.BigIntegerField(
        null=True,
        blank=True,
        verbose_name=_("Forum Topic ID"),
    )
    triage_message_id = models.BigIntegerField(
        null=True,
        blank=True,
        verbose_name=_("Triage Message ID"),
    )
    first_copy_triage_message_id = models.BigIntegerField(
        null=True,
        blank=True,
        verbose_name=_("First Copy Triage Message ID"),
    )

    if TYPE_CHECKING:
        messages: models.Manager["TicketMessage"]

    class Meta(DefaultModel.Meta):
        ordering = ["-created_at"]
        verbose_name = _("Ticket")
        verbose_name_plural = _("Tickets")

    def prepare_message(
        self,
        text: str,
        sender_is_admin: bool = False,
        telegram_message_id: int | None = None,
    ) -> "TicketMessage":
        return TicketMessage(
            ticket=self,
            text=text,
            sender_is_admin=sender_is_admin,
            telegram_message_id=telegram_message_id,
        )

    def mark_as_in_progress(
        self,
        forum_topic_id: int,
        first_copy_triage_message_id: int | None = None,
    ) -> list[str]:
        if self.state != self.Status.OPEN:
            raise SupportInvalidTicketStateError(f"Cannot start progress on ticket in {self.state} state.")

        self.state = self.Status.IN_PROGRESS
        self.forum_topic_id = forum_topic_id
        self.first_copy_triage_message_id = first_copy_triage_message_id
        return ["state", "forum_topic_id", "first_copy_triage_message_id"]

    def mark_as_resolved(self) -> list[str]:
        if self.state in [self.Status.RESOLVED, self.Status.CLOSED]:
            raise SupportInvalidTicketStateError("Ticket is already resolved or closed.")

        self.state = self.Status.RESOLVED
        return ["state"]

    def mark_as_closed(self) -> list[str]:
        if self.state == self.Status.CLOSED:
            raise SupportInvalidTicketStateError("Ticket is already closed.")

        self.state = self.Status.CLOSED
        return ["state"]

    def update_triage_message(self, triage_message_id: int) -> list[str]:
        self.triage_message_id = triage_message_id
        return ["triage_message_id"]

    def clear_forum_topic(self) -> list[str]:
        self.forum_topic_id = None
        return ["forum_topic_id"]

    @property
    def first_message(self) -> "TicketMessage | None":
        return cast("TicketMessage | None", self.messages.first())

    def __str__(self) -> str:
        return f"Ticket {self.id} - {self.state}"


class TicketMessage(DefaultModel):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    ticket = models.ForeignKey(
        Ticket,
        on_delete=models.CASCADE,
        related_name="messages",
        verbose_name=_("Ticket"),
    )
    sender_is_admin = models.BooleanField(
        default=False,
        verbose_name=_("Sender is Admin"),
    )
    text = models.TextField(verbose_name=_("Text"))
    telegram_message_id = models.BigIntegerField(
        null=True,
        blank=True,
        verbose_name=_("Telegram Message ID"),
    )

    class Meta(DefaultModel.Meta):
        ordering = ["created_at"]
        verbose_name = _("Ticket Message")
        verbose_name_plural = _("Ticket Messages")

    def __str__(self) -> str:
        sender = "Admin" if self.sender_is_admin else "User"
        return f"Msg {self.id} by {sender} in Ticket {self.ticket_id}"
