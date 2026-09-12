import uuid
from collections.abc import Sequence

from django.db.models.query import QuerySet

from apps.core.domain.exceptions import CoreObjectNotFoundError
from apps.core.repo import BaseRepository
from apps.orders.models import Order, OrderItem, PromoCode
from apps.users.models import User


class OrderRepository(BaseRepository[Order]):
    def __init__(self) -> None:
        super().__init__(model_class=Order)

    def get_orders_queryset(self, user: User) -> QuerySet[Order]:
        """Fetch user orders queryset with preloaded relations to avoid N+1."""
        return (
            self.model_class.objects.filter(user=user)
            .select_related("promocode", "delivery")
            .prefetch_related(
                "items",
                "items__variant",
                "items__variant__product",
            )
            .order_by("-created_at")
        )

    def get_order_with_full_details(self, order_id: uuid.UUID | str, user: User) -> Order:
        """Fetch a specific user order with preloaded details or raise CoreObjectNotFoundError."""
        try:
            return (
                self.model_class.objects.select_related("promocode", "delivery")
                .prefetch_related(
                    "items",
                    "items__variant",
                    "items__variant__product",
                )
                .get(id=order_id, user=user)
            )
        except self.model_class.DoesNotExist:
            raise CoreObjectNotFoundError("Order not found!")

    def get_pending_orders_count(self, user: User) -> int:
        """Count pending orders for the specified user."""
        return self.model_class.objects.filter(user=user, state=Order.Status.PENDING).count()

    def get_order_with_delivery_data(self, order_id: uuid.UUID | str) -> Order:
        """Fetch an order with user and delivery relation or raise CoreObjectNotFoundError."""
        try:
            return self.model_class.objects.select_related("delivery", "user").get(id=order_id)
        except self.model_class.DoesNotExist:
            raise CoreObjectNotFoundError("Order not found!")

    def get_order_items(self, order: Order) -> Sequence[OrderItem]:
        """Fetch all items related to the order with preloaded variants and products."""
        order_items = list(OrderItem.objects.select_related("variant", "variant__product").filter(order=order))
        if order_items:
            return order_items
        raise CoreObjectNotFoundError("Order items not found!")

    def check_user_purchased_product(self, user: User, product_id: int) -> bool:
        """Check if the user has a successfully paid order containing the specified product."""
        return self.model_class.objects.filter(
            user=user, state=Order.Status.PAID, items__variant__product_id=product_id
        ).exists()

    def bulk_create_items(self, items: Sequence[OrderItem]) -> Sequence[OrderItem]:
        """Bulk create order items in the database."""
        return OrderItem.objects.bulk_create(items)


class PromoCodeRepository(BaseRepository[PromoCode]):
    def __init__(self) -> None:
        super().__init__(model_class=PromoCode)
