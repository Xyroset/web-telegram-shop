from typing import Any

from django.contrib import admin
from django.http import HttpRequest
from django.utils.translation import gettext_lazy as _
from unfold.admin import ModelAdmin, TabularInline

from apps.support.models import Ticket, TicketMessage


class TicketMessageInline(TabularInline):
    model = TicketMessage
    extra = 0
    fields = ("created_at", "sender_is_admin", "text", "telegram_message_id")
    readonly_fields = ("created_at", "sender_is_admin", "text", "telegram_message_id")

    def has_add_permission(self, request: HttpRequest, obj: Any | None = None) -> bool:
        """Messages must only be created via bot/API Use Cases."""
        return False

    def has_change_permission(self, request: HttpRequest, obj: Any | None = None) -> bool:
        """Message history is immutable."""
        return False

    def has_delete_permission(self, request: HttpRequest, obj: Any | None = None) -> bool:
        """Message history cannot be deleted manually."""
        return False


@admin.register(Ticket)
class TicketAdmin(ModelAdmin):
    list_display = (
        "id",
        "user",
        "category",
        "state",
        "created_at",
    )
    list_filter = (
        "state",
        "category",
        "created_at",
    )
    search_fields = (
        "id",
        "user__tg_id",
        "user__tg_username",
    )
    list_select_related = ("user",)
    readonly_fields = (
        "id",
        "user",
        "category",
        "state",
        "forum_topic_id",
        "triage_message_id",
        "first_copy_triage_message_id",
        "created_at",
        "updated_at",
    )
    inlines = [TicketMessageInline]

    fieldsets = (
        (
            _("Ticket Information"),
            {
                "fields": (
                    "id",
                    "user",
                    "category",
                    "state",
                )
            },
        ),
        (
            _("Telegram Integration"),
            {
                "fields": (
                    "forum_topic_id",
                    "triage_message_id",
                    "first_copy_triage_message_id",
                )
            },
        ),
        (
            _("Timestamps"),
            {
                "fields": (
                    "created_at",
                    "updated_at",
                ),
                "classes": ("collapse",),
            },
        ),
    )

    def has_add_permission(self, request: HttpRequest) -> bool:
        """Tickets must only be created via the API/Use Cases."""
        return False

    def has_change_permission(self, request: HttpRequest, obj: Any | None = None) -> bool:
        """Ticket state transitions are managed exclusively via Use Cases."""
        return False
