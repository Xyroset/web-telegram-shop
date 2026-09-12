from typing import Any, cast

from django.contrib import admin
from django.db.models import QuerySet
from django.http import HttpRequest
from django.utils.translation import gettext_lazy as _
from unfold.admin import ModelAdmin, StackedInline, TabularInline

from apps.users.models import User, UserDeliveryData, UserSettingsData


class SettingsDataInline(StackedInline):
    """
    Inline representation for user settings configuration in Django Admin.
    """

    model = UserSettingsData
    can_delete = False
    classes = ["collapse"]

    readonly_fields = [
        "preferred_payment_currency",
        "preferred_network",
        "particles_style",
        "default_theme",
        "custom_theme",
        "default_language_code",
        "custom_language_code",
        "created_at",
        "updated_at",
    ]

    def has_add_permission(self, request: HttpRequest, obj: Any | None = None) -> bool:
        return False


class UserDeliveryDataInline(TabularInline):
    """
    Inline representation for user delivery addresses in Django Admin.
    """

    model = UserDeliveryData
    extra = 0
    can_delete = False

    readonly_fields = [
        "is_current",
        "full_name",
        "email",
        "phone",
        "zip_code",
        "address_line",
        "destination_code",
        "region_code",
        "created_at",
        "updated_at",
    ]

    def has_add_permission(self, request: HttpRequest, obj: Any | None = None) -> bool:
        return False


@admin.register(User)
class UserAdmin(ModelAdmin):
    """
    Admin model representation for Telegram user aggregate root.
    """

    list_display = [
        "tg_id",
        "tg_username",
        "first_name",
        "get_current_theme",
        "is_superuser",
        "is_active",
    ]
    list_display_links = ["tg_id", "tg_username"]
    list_select_related = ["settings"]

    search_fields = ["tg_id", "tg_username", "first_name", "last_name"]
    list_filter = ["is_superuser", "is_active", "settings__default_theme"]

    inlines = [SettingsDataInline, UserDeliveryDataInline]

    readonly_fields = [
        "tg_id",
        "tg_username",
        "first_name",
        "last_name",
        "photo",
        "last_login",
        "date_joined",
        "created_at",
        "updated_at",
    ]

    fieldsets = (
        (
            _("Telegram Information"),
            {
                "fields": ("tg_id", "tg_username", "first_name", "last_name", "photo"),
                "description": _("Data automatically synchronized from Telegram. Strictly Read-Only."),
            },
        ),
        (
            _("Access Control"),
            {
                "fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions"),
                "description": _("Manage user permissions and access to the admin panel."),
                "classes": ("collapse",),
            },
        ),
        (
            _("Timestamps"),
            {
                "fields": ("last_login", "date_joined", "created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )

    def get_queryset(self, request: HttpRequest) -> QuerySet[User]:
        return cast(QuerySet[User], super().get_queryset(request).select_related("settings"))

    @admin.display(description=_("Current Theme"))
    def get_current_theme(self, obj: User) -> str:
        """Safely retrieve the resolved active theme from related SettingsData."""
        if hasattr(obj, "settings"):
            return str(obj.settings.current_theme)
        return "-"

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False
