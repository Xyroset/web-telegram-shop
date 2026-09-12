from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from apps.basket.domain.services import BasketCalculationService
from apps.orders.domain.exceptions import PromoCodeMinAmountError
from apps.orders.models import PromoCode
from apps.users.models import User


class TestBasketCalculationService:
    """
    Verify pure domain logic for basket totals and discounts.
    """

    def test_calculate_empty_basket(self, user: User) -> None:
        """
        Happy path: Empty user basket.
        """
        service = BasketCalculationService()

        result = service.calculate(user=user, basket=None, basket_items=[], promocode=None)

        assert result["total_price"] == Decimal("0.00")
        assert result["total_weight_kg"] == Decimal("0.00")
        assert result["valid_promocode"] is False

    @pytest.mark.parametrize(
        "has_promocode, promocode_type, base_total, discount_value, final_total, work_for_all",
        [
            (False, None, Decimal("100.00"), Decimal("0.00"), Decimal("100.00"), False),
            (True, PromoCode.Type.AMOUNT, Decimal("100.00"), Decimal("20.00"), Decimal("80.00"), True),
            (True, PromoCode.Type.PERCENT, Decimal("100.00"), Decimal("25.00"), Decimal("75.00"), True),
            (True, PromoCode.Type.AMOUNT, Decimal("10.00"), Decimal("20.00"), Decimal("0.00"), True),
        ],
    )
    def test_calculate_success_paths(
        self,
        user: User,
        has_promocode: bool,
        promocode_type: str | None,
        base_total: Decimal,
        discount_value: Decimal,
        final_total: Decimal,
        work_for_all: bool,
    ) -> None:
        """
        Happy path: Calculate totals with different configurations.
        """
        fake_basket = MagicMock()
        fake_basket.total_price = base_total

        fake_item = MagicMock()
        fake_item.variant.price = base_total
        fake_item.quantity = 1
        fake_item.variant.weight_kg = Decimal("1.5")
        fake_item.variant.volumetric_weight_kg = Decimal("1.0")

        fake_promocode = None
        if has_promocode:
            fake_promocode = MagicMock()
            fake_promocode.discount_type = promocode_type
            fake_promocode.work_for_everything = work_for_all
            fake_promocode.variants.all.return_value = []
            fake_promocode.categories.all.return_value = []
            fake_promocode.tags.all.return_value = []

            if promocode_type == PromoCode.Type.AMOUNT:
                fake_promocode.discount_amount = discount_value
            elif promocode_type == PromoCode.Type.PERCENT:
                fake_promocode.discount_percent = discount_value / base_total * 100

        service = BasketCalculationService()

        result = service.calculate(
            user=user,
            basket=fake_basket,
            basket_items=[fake_item],
            promocode=fake_promocode,
        )

        assert result["total_weight_kg"] == Decimal("1.5")
        assert result["total_price"] == final_total

    def test_calculate_min_order_amount_error(self, user: User) -> None:
        """
        Failure: Promo code min_order_amount not met.
        """
        fake_basket = MagicMock()
        fake_basket.total_price = Decimal("10.00")

        fake_item = MagicMock()
        fake_item.variant.weight_kg = Decimal("1.0")
        fake_item.variant.volumetric_weight_kg = Decimal("1.0")
        fake_item.quantity = 1

        fake_promocode = MagicMock()
        fake_promocode.check_is_valid.side_effect = PromoCodeMinAmountError("Min amount not met.")

        service = BasketCalculationService()

        with pytest.raises(PromoCodeMinAmountError):
            service.calculate(
                user=user,
                basket=fake_basket,
                basket_items=[fake_item],
                promocode=fake_promocode,
            )
