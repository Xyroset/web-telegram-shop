import logging

from django.contrib import admin
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect
from django.utils.translation import gettext_lazy as _
from unfold.admin import ModelAdmin
from unfold.decorators import action, display

from apps.delivery.domain.exceptions import DeliveryConflictDataError
from apps.delivery.models import Delivery
from apps.delivery.repo import DeliveryRepository
from apps.delivery.usecases import DeliverDeliveryCase, ReturnDeliveryCase, ShipDeliveryCase

logger = logging.getLogger(__name__)


@admin.register(Delivery)
class DeliveryAdmin(ModelAdmin):
    list_display = (
        "id",
        "display_order_link",
        "state",
        "provider_code",
        "cost",
        "tracking_number",
        "created_at",
    )

    list_filter = ("state", "provider_code", "created_at")
    search_fields = ("id", "order__id", "tracking_number")

    readonly_fields = ("id", "order", "state", "cost", "delivery_data", "created_at", "updated_at")

    fieldsets = (
        (
            _("General Information"),
            {
                "fields": ("id", "order", "state", "cost"),
            },
        ),
        (
            _("Fulfillment Details"),
            {
                "fields": ("provider_code", "tracking_number"),
                "description": _("Update the provider and tracking number before marking as shipped."),
            },
        ),
        (
            _("Snapshot Data"),
            {
                "fields": ("delivery_data",),
                "classes": ("collapse",),
                "description": _("Immutable snapshot of the shipping address at the time of checkout."),
            },
        ),
        (
            _("Timestamps"),
            {
                "fields": ("created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )

    actions_detail = ["mark_as_shipped_action", "mark_as_delivered_action", "mark_as_returned_action"]

    @display(description=_("Order ID"))
    def display_order_link(self, obj: Delivery) -> str:
        """Returns a clean representation of the linked order."""
        return str(obj.order_id)

    @action(description=_("Mark as Shipped"), url_path="mark-shipped")
    def mark_as_shipped_action(self, request: HttpRequest, object_id: str) -> HttpResponse:
        delivery_repo = DeliveryRepository()
        use_case = ShipDeliveryCase(delivery_repo=delivery_repo)

        try:
            use_case.execute(delivery_id=object_id)
            self.message_user(request, _("Delivery successfully marked as shipped."), level="SUCCESS")
        except DeliveryConflictDataError as e:
            self.message_user(request, _("Conflict: ") + str(e), level="WARNING")
        except Exception:
            logger.exception("Failed to mark delivery %s as shipped", object_id)
            self.message_user(request, _("An unexpected error occurred."), level="ERROR")

        return redirect(request.META.get("HTTP_REFERER", "."))

    @action(description=_("Mark as Delivered"), url_path="mark-delivered")
    def mark_as_delivered_action(self, request: HttpRequest, object_id: str) -> HttpResponse:
        delivery_repo = DeliveryRepository()
        use_case = DeliverDeliveryCase(delivery_repo=delivery_repo)

        try:
            use_case.execute(delivery_id=object_id)
            self.message_user(request, _("Delivery successfully marked as delivered."), level="SUCCESS")
        except DeliveryConflictDataError as e:
            self.message_user(request, _("Conflict: %(error)s") % {"error": e}, level="WARNING")
        except Exception:
            logger.exception("Failed to mark delivery %s as delivered", object_id)
            self.message_user(request, _("An unexpected error occurred."), level="ERROR")

        return redirect(request.META.get("HTTP_REFERER", "."))

    @action(description=_("Mark as Returned"), url_path="mark-returned")
    def mark_as_returned_action(self, request: HttpRequest, object_id: str) -> HttpResponse:
        delivery_repo = DeliveryRepository()
        use_case = ReturnDeliveryCase(delivery_repo=delivery_repo)

        try:
            use_case.execute(delivery_id=object_id)
            self.message_user(request, _("Delivery successfully marked as returned."), level="WARNING")
        except DeliveryConflictDataError as e:
            self.message_user(request, _("Conflict: %(error)s") % {"error": e}, level="WARNING")
        except Exception:
            logger.exception("Failed to mark delivery %s as returned", object_id)
            self.message_user(request, _("An unexpected error occurred."), level="ERROR")

        return redirect(request.META.get("HTTP_REFERER", "."))
