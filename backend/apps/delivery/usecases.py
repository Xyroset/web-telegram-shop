import logging

from django.db import transaction as ts

from apps.basket.domain.services import BasketCalculationService
from apps.basket.repo import BasketRepository
from apps.core.domain.exceptions import CoreObjectNotFoundError
from apps.delivery.domain.exceptions import DeliveryConflictDataError
from apps.delivery.domain.interfaces import ShippingPricingStrategy
from apps.delivery.domain.services import DeliveryCalculationResult, DeliveryValidationService
from apps.delivery.repo import DeliveryRepository
from apps.users.models import User
from apps.users.repo import UserDeliveryDataRepository

logger = logging.getLogger(__name__)


class CalculateDeliveryEstimateCase:
    """
    Orchestrates the calculation of an estimated delivery cost.

    **Business Rules:**
    - Validates destination and region codes against configuration via `DeliveryValidationService`.
    - Fetches the user's basket and its items via `BasketRepository`.
    - Calculates the current basket totals (price and weight) using `BasketCalculationService`.
    - Retrieves the user's default delivery address if destination code is omitted.
    - Applies the pricing strategy to determine final shipping cost, free shipping status, and gamification amount.

    **Required:**
    - `user`: An authenticated User instance.
    - Destination and region codes must be supported by the shop configuration.
    Otherwise error — **DeliveryUnsupportedDestinationError**.
    - If the user has no basket or no saved delivery data, graceful fallbacks are applied.
    """

    def __init__(
        self,
        strategy: ShippingPricingStrategy,
        basket_repo: BasketRepository,
        user_delivery_data_repo: UserDeliveryDataRepository,
    ) -> None:
        self._strategy = strategy
        self._basket_repo = basket_repo
        self._user_delivery_data_repo = user_delivery_data_repo
        self._basket_calc_service = BasketCalculationService()
        self._validate_delivery_data_service = DeliveryValidationService()

    def execute(
        self, user: User, destination_code: str | None = None, region_code: str | None = None
    ) -> DeliveryCalculationResult:
        try:
            basket = self._basket_repo.get_basket_with_items(user=user)
            basket_items = list(basket.items.all())
        except CoreObjectNotFoundError:
            basket = None
            basket_items = []

        basket_result = self._basket_calc_service.calculate(
            user=user,
            basket=basket,
            basket_items=basket_items,
            promocode=None,
        )

        if not destination_code:
            try:
                delivery_data = self._user_delivery_data_repo.get_by(user=user, is_current=True)
                destination_code = delivery_data.destination_code
                region_code = delivery_data.region_code
            except CoreObjectNotFoundError:
                destination_code = None
                region_code = None

        self._validate_delivery_data_service.validate_against_config(
            destination_code=destination_code, region_code=region_code
        )

        return self._strategy.calculate(
            total_price=basket_result["total_price"],
            billable_weight_kg=basket_result["total_weight_kg"],
            destination_code=destination_code,
            region_code=region_code,
        )


class ShipDeliveryCase:
    """
    Mark a delivery as shipped.

    **Business Rules:**
    - Transitions the delivery state to SHIPPED.
    - Fails if no tracking number is provided.
    """

    def __init__(self, delivery_repo: DeliveryRepository) -> None:
        self._delivery_repo = delivery_repo

    def execute(self, delivery_id: str) -> None:
        with ts.atomic():
            delivery = self._delivery_repo.get_for_update_by(id=delivery_id)

            if not delivery.tracking_number:
                raise DeliveryConflictDataError("Cannot ship without a tracking number.")

            update_fields = delivery.mark_as_shipped()
            self._delivery_repo.save(delivery, update_fields=update_fields)

        logger.info(f"Delivery {delivery.id} marked as SHIPPED.")


class DeliverDeliveryCase:
    """
    Mark a delivery as successfully delivered to the customer.

    **Business Rules:**
    - Transitions the delivery state to DELIVERED.
    """

    def __init__(self, delivery_repo: DeliveryRepository) -> None:
        self._delivery_repo = delivery_repo

    def execute(self, delivery_id: str) -> None:
        with ts.atomic():
            delivery = self._delivery_repo.get_for_update_by(id=delivery_id)

            update_fields = delivery.mark_as_delivered()
            self._delivery_repo.save(delivery, update_fields=update_fields)

        logger.info(f"Delivery {delivery.id} marked as DELIVERED.")


class ReturnDeliveryCase:
    """
    Mark a delivery as returned.

    **Business Rules:**
    - Transitions the delivery state to RETURNED.
    - Used when the physical item is sent back to the store.
    """

    def __init__(self, delivery_repo: DeliveryRepository) -> None:
        self._delivery_repo = delivery_repo

    def execute(self, delivery_id: str) -> None:
        with ts.atomic():
            delivery = self._delivery_repo.get_for_update_by(id=delivery_id)

            update_fields = delivery.mark_as_returned()
            self._delivery_repo.save(delivery, update_fields=update_fields)

        logger.info(f"Delivery {delivery.id} marked as RETURNED.")
