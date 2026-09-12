from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.config_manager import shop_config
from apps.core.models import DefaultModel
from apps.delivery.domain.exceptions import DeliveryConflictDataError
from apps.orders.models import Order


def get_default_provider_code() -> str:
    return str(shop_config.get("delivery", "delivery_settings.default_provider_code", "AUTO"))


class Delivery(DefaultModel):
    class Status(models.TextChoices):
        PENDING = "PENDING", _("Pending")
        PROCESSING = "PROCESSING", _("Processing")
        SHIPPED = "SHIPPED", _("Shipped")
        DELIVERED = "DELIVERED", _("Delivered")
        FAILED = "FAILED", _("Failed")
        CANCELLED = "CANCELLED", _("Cancelled")
        RETURNED = "RETURNED", _("Returned")

    order = models.OneToOneField(
        Order,
        on_delete=models.CASCADE,
        related_name="delivery",
        verbose_name=_("Order"),
    )
    state = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        verbose_name=_("State"),
    )
    provider_code = models.CharField(
        default=get_default_provider_code,
        max_length=50,
        verbose_name=_("Provider Code"),
    )
    tracking_number = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name=_("Tracking Number"),
    )
    cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name=_("Cost"),
    )
    delivery_data = models.JSONField(
        verbose_name=_("Delivery Data"),
    )

    class Meta(DefaultModel.Meta):
        verbose_name = _("Delivery")
        verbose_name_plural = _("Deliveries")
        indexes = DefaultModel.Meta.indexes + [
            models.Index(
                fields=["state", "provider_code"],
                condition=models.Q(state="pending"),
                name="pending_provider_code_delivery",
            ),
        ]

    def mark_as_processing(self) -> list[str]:
        if self.state == self.Status.PENDING:
            self.state = self.Status.PROCESSING
            return ["state"]

        raise DeliveryConflictDataError(f"Only PENDING delivery can be processing. Current status: {self.state}")

    def mark_as_shipped(self) -> list[str]:
        if self.state == self.Status.PROCESSING:
            self.state = self.Status.SHIPPED
            return ["state"]

        raise DeliveryConflictDataError(f"Only PROCESSING delivery can be shipped. Current status: {self.state}")

    def mark_as_delivered(self) -> list[str]:
        if self.state == self.Status.SHIPPED:
            self.state = self.Status.DELIVERED
            return ["state"]

        raise DeliveryConflictDataError(f"Only SHIPPED delivery can be DELIVERED. Current status: {self.state}")

    def mark_as_canceled(self) -> list[str]:
        if self.state in [self.Status.PENDING, self.Status.PROCESSING]:
            self.state = self.Status.CANCELLED
            return ["state"]

        raise DeliveryConflictDataError(
            f"Only PENDING or PROCESSING delivery can be cancelled. Current status: {self.state}"
        )

    def mark_as_failed(self) -> list[str]:
        if self.state in [self.Status.PENDING, self.Status.PROCESSING, self.Status.SHIPPED]:
            self.state = self.Status.FAILED
            return ["state"]

        raise DeliveryConflictDataError(
            f"Only PENDING, PROCESSING or SHIPPED delivery can be failed. Current status: {self.state}"
        )

    def mark_as_returned(self) -> list[str]:
        if self.state in [self.Status.SHIPPED, self.Status.DELIVERED]:
            self.state = self.Status.RETURNED
            return ["state"]

        raise DeliveryConflictDataError(
            f"Only SHIPPED or DELIVERED delivery can be returned. Current status: {self.state}"
        )

    def __str__(self) -> str:
        return f"Delivery for Order {self.order_id} - {self.state}"
