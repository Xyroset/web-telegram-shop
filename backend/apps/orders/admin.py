import uuid

from django.contrib import admin, messages
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect
from django.utils.translation import gettext_lazy as _
from unfold.admin import ModelAdmin, TabularInline
from unfold.decorators import action

from apps.catalog.repo import DigitalAssetRepository, ProductRepository
from apps.delivery.repo import DeliveryRepository
from apps.orders.models import Order, OrderItem, PromoCode
from apps.orders.repo import OrderRepository, PromoCodeRepository
from apps.orders.usecases.cancellation import CancelOrderCase
from apps.payments.repo import PaymentTransactionRepository
from apps.users.repo import UserRepository


class OrderItemInline(TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ["variant", "quantity", "fixed_price"]
    fields = ["variant", "quantity", "fixed_price"]
    can_delete = False

    def has_add_permission(self, request: HttpRequest, obj: OrderItem | None = None) -> bool:
        return False


@admin.register(Order)
class OrderAdmin(ModelAdmin):
    list_display = ["id", "user", "state", "amount_usd", "created_at"]
    list_filter = ["state"]
    search_fields = ["id", "user__tg_id", "user__tg_username"]

    readonly_fields = [
        "id",
        "user",
        "state",
        "amount_usd",
        "promocode",
        "payload_url",
        "task_id",
        "metadata",
        "created_at",
        "updated_at",
    ]

    inlines = [OrderItemInline]

    fieldsets = (
        (
            _("Basic information"),
            {"fields": ("id", "user", "state", "amount_usd", "promocode")},
        ),
        (
            _("System information"),
            {
                "fields": ("payload_url", "task_id", "metadata", "created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )

    actions_detail = ["cancel_order_action"]

    @action(description=_("Cancel Order"), url_path="cancel-order")
    def cancel_order_action(self, request: HttpRequest, object_id: str) -> HttpResponse:
        """
        Safely cancels the order via Use Case, ensuring stock is returned,
        promocodes are rolled back, and Celery tasks are revoked.
        """
        usecase = CancelOrderCase(
            order_repo=OrderRepository(),
            user_repo=UserRepository(),
            delivery_repo=DeliveryRepository(),
            payment_repo=PaymentTransactionRepository(),
            promocode_repo=PromoCodeRepository(),
            product_repo=ProductRepository(),
            digital_asset_repo=DigitalAssetRepository(),
        )

        try:
            usecase.execute(order_id=uuid.UUID(object_id))
            self.message_user(
                request,
                _("Order successfully cancelled and inventory returned."),
                level=messages.SUCCESS,
            )
        except Exception as exc:
            self.message_user(request, _("Error: %(error)s") % {"error": exc}, level=messages.ERROR)

        referer = request.META.get("HTTP_REFERER", ".")
        return redirect(referer)


@admin.register(PromoCode)
class PromoCodeAdmin(ModelAdmin):
    list_display_links = ["id", "code"]
    list_display = ["id", "code", "discount_value", "min_order_amount", "used_count", "work_for_everything"]
    list_filter = ["discount_type", "work_for_everything"]
    search_fields = ["code"]
    readonly_fields = ["used_count"]

    @admin.display(description=_("Size promotion"))
    def discount_value(self, obj: PromoCode) -> str:
        if obj.discount_type == PromoCode.Type.AMOUNT:
            return f"${obj.discount_amount} {_('Fix')}"
        return f"{obj.discount_percent}% {_('Percent')}"
