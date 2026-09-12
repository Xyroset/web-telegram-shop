import uuid
from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.basket.domain import exceptions as e
from apps.catalog.models import ProductVariant
from apps.core.models import DefaultModel


class Basket(DefaultModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="basket",
        verbose_name=_("User"),
    )

    class Meta:
        verbose_name = _("Basket")
        verbose_name_plural = _("Baskets")

    @property
    def total_price(self) -> Decimal:
        """
        Calculates the total price of all items in the basket.
        Note: Requires 'items__variant' to be prefetched to avoid N+1 queries.
        """
        total = sum((item.variant.price * item.quantity for item in self.items.all()), Decimal("0.00"))
        return total.quantize(Decimal("0.01"))

    @property
    def is_empty(self) -> bool:
        """
        Checks whether the basket contains any items.
        """
        return self.items.all().count() < 1

    def prepare_item(self, variant: ProductVariant, quantity: int = 1, MAX: int = 25) -> "BasketItem":
        """
        Prepares a new BasketItem instance in memory without persisting it to DB.
        """
        if quantity < 1 or quantity > MAX:
            raise e.BasketItemLimitError(f"Quantity cannot be less than 1, or more than {MAX}")

        return BasketItem(basket=self, variant=variant, quantity=quantity)

    def __str__(self) -> str:
        return f"Basket - {self.user}"


class BasketItem(DefaultModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    basket = models.ForeignKey(
        Basket,
        on_delete=models.CASCADE,
        related_name="items",
        verbose_name=_("Basket"),
    )
    variant = models.ForeignKey(
        ProductVariant,
        on_delete=models.CASCADE,
        verbose_name=_("Product Variant"),
    )
    quantity = models.PositiveIntegerField(default=1, verbose_name=_("Quantity"))

    class Meta:
        verbose_name = _("Basket Item")
        verbose_name_plural = _("Basket Items")
        constraints = [models.UniqueConstraint(fields=["basket", "variant"], name="unique_basket_item")]

    def update_quantity(self, quantity: int, MAX: int = 25) -> list[str]:
        """
        Updates the quantity for this item in memory.
        """
        if quantity < 1 or quantity > MAX:
            raise e.BasketItemLimitError(f"Quantity cannot be less than 1, or more than {MAX}")

        self.quantity = quantity

        return ["quantity"]

    def __str__(self) -> str:
        return f"Basket Item - {self.variant.title}"
