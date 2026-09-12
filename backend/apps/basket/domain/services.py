from collections.abc import Sequence
from decimal import Decimal
from typing import TypedDict

from apps.basket.models import Basket, BasketItem
from apps.orders.models import PromoCode
from apps.users.models import User


class BasketCalculationResult(TypedDict):
    base_price: Decimal
    total_price: Decimal
    discount_value: Decimal
    promocode_type: str | None
    total_weight_kg: Decimal
    valid_promocode: bool


class BasketCalculationService:
    """
    Domain service for calculating the total price and discounts of a basket.
    Purely operates on in-memory domain objects without hitting the database.
    """

    def calculate(
        self,
        user: User,
        basket: Basket | None,
        basket_items: Sequence[BasketItem],
        user_used: int = 0,
        promocode: PromoCode | None = None,
    ) -> BasketCalculationResult:
        if not basket or not basket_items:
            return {
                "base_price": Decimal("0.00"),
                "total_price": Decimal("0.00"),
                "discount_value": Decimal("0.00"),
                "promocode_type": None,
                "total_weight_kg": Decimal("0.00"),
                "valid_promocode": False,
            }

        base_total = basket.total_price

        total_weight_kg = sum(
            (max(item.variant.volumetric_weight_kg, item.variant.weight_kg) * item.quantity for item in basket_items),
            Decimal("0.00"),
        )

        if not promocode:
            return {
                "base_price": base_total,
                "total_price": base_total,
                "discount_value": Decimal("0.00"),
                "promocode_type": None,
                "total_weight_kg": total_weight_kg,
                "valid_promocode": False,
            }

        promocode.check_is_valid(user=user, user_used=user_used, order_total=base_total)

        discount_value = self._calculate_discount(basket_items=basket_items, promocode=promocode)
        final_total = max(base_total - discount_value, Decimal("0.00"))

        return {
            "base_price": base_total,
            "total_price": final_total,
            "discount_value": discount_value,
            "promocode_type": promocode.discount_type,
            "total_weight_kg": total_weight_kg,
            "valid_promocode": True,
        }

    def _calculate_discount(self, basket_items: Sequence[BasketItem], promocode: PromoCode) -> Decimal:
        promocode_variant_ids = {v.id for v in promocode.variants.all()}
        promocode_category_ids = {c.id for c in promocode.categories.all()}
        promocode_tag_ids = {t.id for t in promocode.tags.all()}

        eligible_total = Decimal("0.00")

        for item in basket_items:
            is_eligible = False

            if promocode.work_for_everything:
                is_eligible = True
            elif item.variant_id in promocode_variant_ids:
                is_eligible = True
            elif getattr(item.variant.product, "category_id", None) in promocode_category_ids:
                is_eligible = True
            else:
                item_tags = {tag.id for tag in item.variant.tags.all()}
                if not promocode_tag_ids.isdisjoint(item_tags):
                    is_eligible = True

            if is_eligible:
                eligible_total += item.variant.price * item.quantity

        if eligible_total == Decimal("0.00"):
            return Decimal("0.00")

        discount = Decimal("0.00")

        if promocode.discount_type == PromoCode.Type.PERCENT:
            discount = (eligible_total * (promocode.discount_percent or Decimal("0.00"))) / Decimal("100")
        elif promocode.discount_type == PromoCode.Type.AMOUNT:
            discount = min(promocode.discount_amount or Decimal("0.00"), eligible_total)

        return discount.quantize(Decimal("0.01"))
