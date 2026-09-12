from contextlib import nullcontext as does_not_raise
from typing import ContextManager
from unittest.mock import MagicMock, patch

import pytest

from apps.basket.domain.exceptions import BasketItemLimitError
from apps.basket.repo import BasketRepository
from apps.basket.usecases import BasketCalculateCase, BasketCreateUpdateItemCase, BasketDeleteItemCase
from apps.catalog.repo import ProductRepository
from apps.core.domain.exceptions import CoreObjectNotFoundError
from apps.orders.repo import PromoCodeRepository
from apps.users.repo import UserRepository


@patch("django.db.transaction.atomic", MagicMock())
class TestBasketCreateUpdateItemCase:
    """
    Verify orchestration for updating or creating a basket item.
    """

    @pytest.mark.parametrize(
        "input_quantity, expected_context",
        [
            (10, does_not_raise()),
            (100, pytest.raises(BasketItemLimitError)),
        ],
    )
    def test_create_update_item_orchestration(
        self,
        input_quantity: int,
        expected_context: ContextManager,
    ) -> None:
        """
        Happy path and Failure scenarios: Create or update basket item quantity.
        """
        user = MagicMock()
        mock_basket_repo: MagicMock | BasketRepository = MagicMock()
        mock_product_repo: MagicMock | ProductRepository = MagicMock()
        fake_basket = MagicMock()
        fake_variant = MagicMock()
        fake_existing_item = MagicMock()

        mock_basket_repo.get_or_create.return_value = (fake_basket, False)  # type: ignore[union-attr]
        mock_product_repo.get_variant.return_value = fake_variant  # type: ignore[union-attr]
        mock_basket_repo.get_basket_item.return_value = fake_existing_item  # type: ignore[union-attr]
        fake_variant.available_stock = 100

        usecase = BasketCreateUpdateItemCase(
            basket_repo=mock_basket_repo,
            product_repo=mock_product_repo,
        )

        with expected_context:
            usecase.execute(user=user, variant_id=1, quantity=input_quantity)

        if isinstance(expected_context, does_not_raise):
            fake_existing_item.update_quantity.assert_called_once()
            mock_basket_repo.save_item.assert_called_once()  # type: ignore[union-attr]


@patch("django.db.transaction.atomic", MagicMock())
class TestBasketDeleteItemCase:
    """
    Verify orchestration for deleting a basket item.
    """

    @pytest.mark.parametrize(
        "item_exists, expected_context",
        [
            (True, does_not_raise()),
            (False, pytest.raises(CoreObjectNotFoundError)),
        ],
    )
    def test_delete_item_orchestration(
        self,
        item_exists: bool,
        expected_context: ContextManager,
    ) -> None:
        """
        Happy path and Failure scenarios: Delete an item from the basket.
        """
        user = MagicMock()
        mock_basket_repo: MagicMock | BasketRepository = MagicMock()
        fake_basket = MagicMock()
        fake_basket_item = MagicMock()

        mock_basket_repo.get_by.return_value = fake_basket  # type: ignore[union-attr]

        if item_exists:
            mock_basket_repo.get_basket_item.return_value = fake_basket_item  # type: ignore[union-attr]
        else:
            mock_basket_repo.get_basket_item.side_effect = CoreObjectNotFoundError  # type: ignore[union-attr]

        usecase = BasketDeleteItemCase(basket_repo=mock_basket_repo)

        with expected_context:
            usecase.execute(user=user, variant_id=1)

        if item_exists:
            mock_basket_repo.delete_item.assert_called_once_with(item=fake_basket_item)  # type: ignore[union-attr]


class TestBasketCalculateCase:
    """
    Verify orchestration for calculating total price in user basket.
    """

    def test_calculate_orchestration_with_empty_basket(
        self,
    ) -> None:
        """
        Failure path simulation: Basket not found results in empty calculation passed to service.
        """
        user = MagicMock()
        mock_basket_repo: MagicMock | BasketRepository = MagicMock()
        mock_user_repo: MagicMock | UserRepository = MagicMock()
        mock_promocode_repo: MagicMock | PromoCodeRepository = MagicMock()

        mock_basket_repo.get_basket_with_items.side_effect = CoreObjectNotFoundError  # type: ignore[union-attr]

        usecase = BasketCalculateCase(
            basket_repo=mock_basket_repo,
            user_repo=mock_user_repo,
            promocode_repo=mock_promocode_repo,
        )

        result = usecase.execute(user=user)

        assert result["total_price"] == 0
        assert result["valid_promocode"] is False
        mock_promocode_repo.get_by.assert_not_called()  # type: ignore[union-attr]
