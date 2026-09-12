import uuid
from collections.abc import Sequence
from datetime import datetime, timedelta
from decimal import Decimal
from typing import TYPE_CHECKING

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.core.config_manager import shop_config
from apps.core.models import DefaultModel
from apps.orders.domain.dto import OrderDTO, OrderItemDTO
from apps.orders.domain.exceptions import (
    OrderConflictDataError,
    PromoCodeAlreadyUsedError,
    PromoCodeExpiredError,
    PromoCodeInactiveError,
    PromoCodeLimitReachedError,
    PromoCodeMinAmountError,
    PromoCodeNotYetValidError,
)
from apps.orders.domain.value_objects import FiatMoney
from apps.payments.domain.exceptions import PaymentConflictDataError
from apps.users.models import User

if TYPE_CHECKING:
    from apps.payments.models import PaymentTransaction


def get_default_promo_expiration() -> datetime:
    return timezone.now() + timedelta(days=shop_config.get("order", "promocode_settings.default_promo_expiration", 30))


class PromoCode(DefaultModel):
    class Type(models.TextChoices):
        AMOUNT = "amount", _("Fixed amount")
        PERCENT = "percent", _("Fixed percent")

    class Meta(DefaultModel.Meta):
        verbose_name = _("Promo code")
        verbose_name_plural = _("Promo codes")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=20, unique=True, verbose_name=_("Code"))

    valid_from = models.DateTimeField(auto_now_add=True, verbose_name=_("Valid from"))
    valid_to = models.DateTimeField(default=get_default_promo_expiration, verbose_name=_("Valid to"))

    min_order_amount = models.DecimalField(
        max_digits=10, decimal_places=2, default=0, verbose_name=_("Min order amount")
    )

    variants = models.ManyToManyField(
        "catalog.ProductVariant", related_name="promocodes", blank=True, verbose_name=_("Variants")
    )
    categories = models.ManyToManyField(
        "catalog.Category", related_name="promocodes", blank=True, verbose_name=_("Categories")
    )
    tags = models.ManyToManyField("catalog.Tag", related_name="promocodes", blank=True, verbose_name=_("Tags"))

    work_for_everything = models.BooleanField(default=False, verbose_name=_("Work for everything"))

    discount_type = models.CharField(
        max_length=20, choices=Type.choices, default=Type.PERCENT, verbose_name=_("Discount type")
    )
    discount_percent = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(100)],
        null=True,
        blank=True,
        verbose_name=_("Discount percent"),
    )
    discount_amount = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True, verbose_name=_("Discount amount")
    )

    max_uses = models.PositiveIntegerField(default=100, verbose_name=_("Max uses"))
    used_count = models.PositiveIntegerField(default=0, verbose_name=_("Used count"))
    max_uses_per_user = models.PositiveIntegerField(default=1, verbose_name=_("Max uses per user"))

    def update_promocode_usage(self) -> list[str]:
        self.used_count += 1
        return ["used_count"]

    def rollback_promocode_usage(self) -> list[str]:
        if self.used_count > 0:
            self.used_count -= 1
        return ["used_count"]

    def calculate_discount(self, total_amount: Decimal) -> Decimal:
        """
        Calculate the exact discount amount based on the promo type.

        Args:
            total_amount (Decimal): The original total price of the basket/order.

        Returns:
            Decimal: The amount to be subtracted from the total.
        """
        if self.discount_type == self.Type.AMOUNT and self.discount_amount:
            return min(self.discount_amount, total_amount)

        elif self.discount_type == self.Type.PERCENT and self.discount_percent:
            discount = total_amount * (Decimal(self.discount_percent) / Decimal(100))
            return discount.quantize(Decimal("0.01"))

        return Decimal("0.00")

    def clean(self) -> None:
        """
        Admin validation to ensure logical integrity of the promo code settings.
        """
        if self.discount_amount and self.discount_percent:
            raise ValidationError("You can only set either amount or percent, not both.")

        if self.discount_type == self.Type.AMOUNT and not self.discount_amount:
            raise ValidationError("For AMOUNT type, discount_amount is required.")

        if self.discount_type == self.Type.PERCENT and not self.discount_percent:
            raise ValidationError("For PERCENT type, discount_percent is required.")

        if self.pk:
            has_specifics = self.variants.exists() or self.categories.exists() or self.tags.exists()
            if self.work_for_everything and has_specifics:
                raise ValidationError("Promo code cannot be for everything AND have specific targets.")
            if not self.work_for_everything and not has_specifics:
                raise ValidationError("Promo code must apply to everything or specific variants/categories/tags.")

    def check_is_valid(self, user: User, user_used: int, order_total: Decimal) -> None:
        """
        Validates if the promo code can be applied by the specific user for a specific amount.
        """
        if getattr(self, "is_active", True) is False:
            raise PromoCodeInactiveError()

        if self.used_count >= self.max_uses:
            raise PromoCodeLimitReachedError()

        if user_used + 1 > self.max_uses_per_user:
            raise PromoCodeAlreadyUsedError()

        if order_total < self.min_order_amount:
            raise PromoCodeMinAmountError(f"Minimum order amount is {self.min_order_amount}")

        now = timezone.now()
        if self.valid_from and now < self.valid_from:
            raise PromoCodeNotYetValidError()
        if self.valid_to and now > self.valid_to:
            raise PromoCodeExpiredError()

    def __str__(self) -> str:
        return f"Code - {self.code}"


class Order(DefaultModel):
    class Status(models.TextChoices):
        PENDING = "pending", _("Waiting payment")
        PAID = "paid", _("Paid")
        CANCELLED = "cancelled", _("Cancelled")
        EXPIRED = "expired", _("Expired")
        FAILED = "failed", _("Failed (Needs review)")

    class Meta(DefaultModel.Meta):
        verbose_name = _("Order")
        verbose_name_plural = _("Orders")
        indexes = DefaultModel.Meta.indexes + [
            models.Index(fields=["state"], condition=models.Q(state="pending"), name="idx_pending_orders"),
        ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    payload_url = models.URLField(null=True, blank=True, verbose_name=_("Payload URL"))

    state = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING, verbose_name=_("State"))
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="order_history",
        verbose_name=_("User"),
    )
    amount_usd = models.DecimalField(max_digits=10, decimal_places=2, verbose_name=_("Amount USD"))
    promocode = models.ForeignKey(
        PromoCode, on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_("Promo code")
    )
    paid_at = models.DateTimeField(null=True, blank=True, verbose_name=_("Paid at"))
    task_id = models.UUIDField(null=True, blank=True, verbose_name=_("Task ID"))
    metadata = models.JSONField(default=dict, blank=True, null=True, verbose_name=_("Metadata"))

    def get_active_transaction(self) -> "PaymentTransaction | None":
        """
        Retrieves the currently pending payment transaction for this order, if any.
        """
        return self.transactions.filter(state="pending").first()

    def assert_no_active_transactions(self) -> None:
        """
        Business Rule: Cannot create a new payment attempt if one is already pending.
        """
        if self.get_active_transaction():
            raise PaymentConflictDataError(
                "An active pending transaction already exists for this order. "
                "Please cancel it or wait for expiration before creating a new one."
            )

    def evaluate_payment_state(self) -> list[str]:
        """
        Aggregate Root logic: Evaluates all child transactions.
        If at least one transaction is successfully PAID, the order becomes PAID.
        """
        if self.state == self.Status.PAID:
            return []

        if self.transactions.filter(state="paid").exists():
            self.state = self.Status.PAID
            self.paid_at = timezone.now()
            return ["state", "paid_at"]

        return []

    @property
    def target_fiat_money(self) -> FiatMoney:
        """Returns the base USD amount of the order as a validated Value Object."""
        return FiatMoney(amount=self.amount_usd)

    def get_remaining_usd_balance(self) -> Decimal:
        """
        Calculates how much fiat (USD) is left to pay across all transactions.
        Relies on the child transactions to report their actually captured USD amount.
        """
        if self.state == self.Status.PAID:
            return FiatMoney(amount=Decimal("0.00")).amount

        all_transactions = self.transactions.all()

        paid_so_far = sum(
            (tx.captured_amount_usd for tx in all_transactions if tx.captured_amount_usd), Decimal("0.00")
        )

        return self.target_fiat_money.subtract(paid_so_far).amount

    def add_items_from_dto(self, items_dto: Sequence[OrderItemDTO]) -> Sequence["OrderItem"]:
        items_to_create = [
            OrderItem(
                order=self,
                variant_id=dto.variant_id,
                quantity=dto.quantity,
                fixed_price=dto.fixed_price,
                is_digital=dto.is_digital,
            )
            for dto in items_dto
        ]

        return items_to_create

    def update_order(self, dto: OrderDTO) -> list[str]:
        updated_fields: list[str] = []

        if dto.payload_url is not None:
            self.payload_url = dto.payload_url
            updated_fields.append("payload_url")

        if dto.promocode is not None:
            self.promocode = dto.promocode
            updated_fields.append("promocode")

        if dto.paid_at is not None:
            self.paid_at = dto.paid_at
            updated_fields.append("paid_at")

        if dto.task_id is not None:
            self.task_id = dto.task_id
            updated_fields.append("task_id")

        if dto.metadata is not None:
            self.metadata = dto.metadata
            updated_fields.append("metadata")

        return updated_fields

    def mark_as_expired(self) -> list[str]:
        if self.state == self.Status.PENDING:
            self.state = self.Status.EXPIRED
            return ["state"]
        raise OrderConflictDataError(f"Only PENDING order can be expired. Current status: {self.state}")

    def mark_as_cancelled(self) -> list[str]:
        if self.state == self.Status.PENDING:
            self.state = self.Status.CANCELLED
            return ["state"]
        raise OrderConflictDataError(f"Only PENDING order can be cancelled. Current status: {self.state}")

    def mark_as_paid(self) -> list[str]:
        if self.state == self.Status.PENDING:
            self.state = self.Status.PAID
            return ["state"]
        raise OrderConflictDataError(f"Only PENDING order can be paid. Current status: {self.state}")

    def mark_as_failed(self) -> list[str]:
        if self.state in [self.Status.PENDING, self.Status.PAID]:
            self.state = self.Status.FAILED
            return ["state"]
        raise OrderConflictDataError(f"Only PENDING or PAID order can be paid. Current status: {self.state}")

    def __str__(self) -> str:
        return f"State - {self.state}. Amount - {self.amount_usd}"


class OrderItem(DefaultModel):
    class Meta(DefaultModel.Meta):
        verbose_name = _("Order item")
        verbose_name_plural = _("Order items")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, verbose_name=_("ID"))
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items", verbose_name=_("Order"))

    variant = models.ForeignKey(
        "catalog.ProductVariant",
        on_delete=models.SET_NULL,
        null=True,
        related_name="order_items",
        verbose_name=_("Variant"),
    )
    quantity = models.PositiveIntegerField(default=1, verbose_name=_("Quantity"))
    fixed_price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name=_("Fixed price"))

    is_digital = models.BooleanField(default=False, verbose_name=_("Is digital"))

    def __str__(self) -> str:
        return f"Variant - {self.variant.title}" if self.variant else "Deleted Variant"
