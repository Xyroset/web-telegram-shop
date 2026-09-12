from collections.abc import Mapping

from django.db.models import QuerySet

from apps.basket.models import Basket, BasketItem
from apps.core.domain.exceptions import CoreObjectNotFoundError
from apps.core.repo import BaseRepository
from apps.users.models import User


class BasketRepository(BaseRepository[Basket]):
    def __init__(self) -> None:
        super().__init__(model_class=Basket)

    def get_basket_queryset(self, user: User) -> QuerySet[BasketItem]:
        """Fetch optimized queryset for listing basket items."""
        return (
            BasketItem.objects.filter(basket__user=user)
            .select_related("variant", "variant__product")
            .prefetch_related("variant__product__gallery_photos", "variant__promocodes")
        )

    def save_item(self, item: BasketItem, update_fields: list[str] | None = None) -> None:
        """Persist BasketItem to the database."""
        item.save(update_fields=update_fields)

    def delete_item(self, item: BasketItem) -> None:
        """Remove a specific item from the database."""
        item.delete()

    def get_basket_with_items(self, user: User) -> Basket:
        """Fetch the basket with all necessary relationships to prevent N+1."""
        try:
            return self.model_class.objects.prefetch_related(
                "items__variant",
                "items__variant__tags",
                "items__variant__product",
                "items__variant__product__category",
            ).get(user=user)
        except self.model_class.DoesNotExist:
            raise CoreObjectNotFoundError("User basket not found.")

    def get_basket_mapping(self, user: User) -> Mapping[int, int]:
        """
        Get a mapping of all variant IDs to quantities in the user's basket.
        Format: {variant_id: quantity}
        """
        items = BasketItem.objects.filter(basket__user=user).values_list("variant_id", "quantity")
        return {variant_id: quantity for variant_id, quantity in items}

    def clear_basket(self, user: User) -> None:
        """Remove all items from the user's basket."""
        BasketItem.objects.filter(basket__user=user).delete()

    def get_basket_item(self, basket: Basket, variant_id: int) -> BasketItem:
        """Fetch a specific basket item by variant ID."""
        try:
            return BasketItem.objects.get(basket=basket, variant_id=variant_id)
        except BasketItem.DoesNotExist:
            raise CoreObjectNotFoundError("Basket item not found!")
