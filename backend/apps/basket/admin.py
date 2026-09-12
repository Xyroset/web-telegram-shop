from django.contrib import admin
from django.http import HttpRequest
from unfold.admin import ModelAdmin, TabularInline

from apps.basket.models import Basket, BasketItem


class BasketItemInline(TabularInline):
    """
    Inline representation of BasketItems for Basket view in Django Admin.
    """

    model = BasketItem
    extra = 0
    can_delete = False
    readonly_fields = ["variant", "quantity", "created_at", "updated_at"]

    def has_add_permission(self, request: HttpRequest, obj: Basket | None = None) -> bool:
        return False


@admin.register(Basket)
class BasketAdmin(ModelAdmin):
    """
    Admin interface management for User Baskets.
    Read-only display to prevent manual corruptions of domain state.
    """

    list_display = ["id", "user", "created_at"]
    search_fields = ["user__tg_id", "user__username"]
    inlines = [BasketItemInline]
    readonly_fields = ["user", "created_at", "updated_at"]

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def has_change_permission(self, request: HttpRequest, obj: Basket | None = None) -> bool:
        return False
