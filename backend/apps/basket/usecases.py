import logging

from django.db import transaction as ts

from apps.basket.domain.exceptions import BasketItemLimitError
from apps.basket.domain.services import BasketCalculationResult, BasketCalculationService
from apps.basket.repo import BasketRepository
from apps.catalog.domain.exceptions import CatalogOutOfStockError
from apps.catalog.repo import ProductRepository
from apps.core.config_manager import shop_config
from apps.core.domain.exceptions import CoreObjectNotFoundError
from apps.orders.repo import PromoCodeRepository
from apps.users.models import User
from apps.users.repo import UserRepository

logger = logging.getLogger(__name__)


class BasketCreateUpdateItemCase:
    """
    Create or update one item in a user's basket.

    **Business Rules:**
    - If the basket item is missing from the user's basket, **create** a new basket item.
    - If the basket item already exists in the user's basket, **update** the quantity.

    **Required:**
    - The quantity cannot exceed the configuration limit (`limit_on_the_number_of_items`).
      Otherwise error — **BasketItemLimitError**.
    """

    def __init__(self, basket_repo: BasketRepository, product_repo: ProductRepository) -> None:
        self._basket_repo = basket_repo
        self._product_repo = product_repo

    def execute(self, user: User, variant_id: int, quantity: int) -> None:
        MAX = shop_config.get("basket", "basket_settings.limit_on_the_number_of_items", 25)

        with ts.atomic():
            basket, _ = self._basket_repo.get_or_create(user=user)
            variant = self._product_repo.get_variant(variant_id=variant_id)

            try:
                existing_item = self._basket_repo.get_basket_item(basket=basket, variant_id=variant_id)

                if quantity > MAX:
                    raise BasketItemLimitError(f"Cannot exceed {MAX} items.")

                if quantity > variant.available_stock:
                    raise CatalogOutOfStockError(
                        f"Not enough stock for {variant.title}. Available: {variant.available_stock}. "
                        f"Your quantity: {quantity}"
                    )

                updated_fields = existing_item.update_quantity(quantity=quantity, MAX=MAX)
                self._basket_repo.save_item(item=existing_item, update_fields=updated_fields)

            except CoreObjectNotFoundError:
                if quantity > MAX:
                    raise BasketItemLimitError(f"Cannot exceed {MAX} items.")

                if quantity > variant.available_stock:
                    raise CatalogOutOfStockError(
                        f"Not enough stock for {variant.title}. Available: {variant.available_stock}. "
                        f"Your quantity: {quantity}"
                    )

                new_item = basket.prepare_item(variant=variant, quantity=quantity, MAX=MAX)
                self._basket_repo.save_item(item=new_item)

        logger.info(f"Updated basket for user {user.tg_id}, variant {variant_id}, quantity {quantity}.")


class BasketDeleteItemCase:
    """
    Deletes an item from the user's basket.

    **Business Rules:**
    - Fetch the user's basket and the specific basket item.
    - Remove the item from the basket.

    **Required:**
    - The basket and the item must exist. Otherwise error — **CoreObjectNotFoundError**.
    """

    def __init__(self, basket_repo: BasketRepository) -> None:
        self._basket_repo = basket_repo

    def execute(self, user: User, variant_id: int) -> None:
        with ts.atomic():
            basket = self._basket_repo.get_by(user=user)
            basket_item = self._basket_repo.get_basket_item(basket=basket, variant_id=variant_id)
            self._basket_repo.delete_item(item=basket_item)


class BasketCalculateCase:
    """
    Calculate the total price of the user's basket, applying any promo code.

    **Business Rules:**
    - Retrieves the user's basket and items.
    - Validates the promo code if provided.
    - Delegates the actual calculation logic to `BasketCalculationService`.
    """

    def __init__(
        self, basket_repo: BasketRepository, user_repo: UserRepository, promocode_repo: PromoCodeRepository
    ) -> None:
        self._basket_repo = basket_repo
        self._user_repo = user_repo
        self._promocode_repo = promocode_repo
        self._calc_service = BasketCalculationService()

    def execute(self, user: User, code: str | None = None) -> BasketCalculationResult:
        try:
            basket = self._basket_repo.get_basket_with_items(user=user)
            basket_items = list(basket.items.all())
        except CoreObjectNotFoundError:
            basket = None
            basket_items = []

        promocode = None
        if code:
            promocode = self._promocode_repo.get_by(code=code)

            try:
                user_promocode = self._user_repo.get_user_promocode(user=user, promocode=promocode)
                user_used = user_promocode.used
            except CoreObjectNotFoundError:
                user_used = 0
        else:
            user_used = 0

        return self._calc_service.calculate(
            user=user,
            basket=basket,
            basket_items=basket_items,
            user_used=user_used,
            promocode=promocode,
        )
