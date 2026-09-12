import logging
import uuid

from celery import current_app
from django.db import transaction as ts

from apps.catalog.repo import DigitalAssetRepository, ProductRepository
from apps.delivery.repo import DeliveryRepository
from apps.orders.domain.services import DigitalAssetManagementService, StockManagementService
from apps.orders.models import Order
from apps.orders.repo import OrderRepository

logger = logging.getLogger(__name__)


class ProcessOrderFulfillmentCase:
    """
    Orchestrates the fulfillment process for an order after successful payment.

    **Business Rules:**
    - Retrieves the order and guarantees it is in the PAID state.
    - Segregates order items into physical and digital categories.
    - Commits final stock mutations for all items via StockManagementService.
    - Updates delivery state to PROCESSING.
    - Schedules background notifications for physical (Admin dispatch)
      and digital (User delivery) items via Celery tasks on transaction commit.

    **Required:**
    - Order must exist. Otherwise raises **CoreObjectNotFoundError**.
    - Order state must be **PAID** to proceed with fulfillment.
    """

    def __init__(
        self,
        order_repo: OrderRepository,
        delivery_repo: DeliveryRepository,
        product_repo: ProductRepository,
        digital_asset_repo: DigitalAssetRepository,
    ) -> None:
        self._order_repo = order_repo
        self._delivery_repo = delivery_repo
        self._stock_service = StockManagementService(product_repo=product_repo)
        self._digital_asset_service = DigitalAssetManagementService(
            digital_asset_repo=digital_asset_repo,
            product_repo=product_repo,
        )

    def execute(self, order_id: uuid.UUID | str) -> None:
        with ts.atomic():
            order = self._order_repo.get_for_update_by(id=order_id)

            if order.state != Order.Status.PAID:
                logger.warning(
                    f"Fulfillment skipped for order {order_id}. Expected state {Order.Status.PAID}, got {order.state}."
                )
                return

            order_items = self._order_repo.get_order_items(order=order)

            if not order_items:
                logger.error(f"Fulfillment failed. Order {order_id} has no items.")
                return

            physical_items = [item for item in order_items if not item.is_digital]
            digital_items = [item for item in order_items if item.is_digital]

            self._stock_service.commit_all(order_items=order_items)

            delivery = self._delivery_repo.get_for_update_by(order=order)
            delivery_update_fields = delivery.mark_as_processing()
            self._delivery_repo.save(instance=delivery, update_fields=delivery_update_fields)

            self._dispatch_side_effects(
                order_id=order.id,
                has_physical=bool(physical_items),
                has_digital=bool(digital_items),
            )

            logger.info(f"Order {order_id} fulfillment processed successfully.")

    def _dispatch_side_effects(self, order_id: uuid.UUID | str, has_physical: bool, has_digital: bool) -> None:
        if has_physical:

            def dispatch_physical() -> None:
                current_app.send_task(
                    "notifications.dispatch_order_paid_notifications",
                    args=[str(order_id)],
                )

            ts.on_commit(dispatch_physical)

        if has_digital:

            def dispatch_digital() -> None:
                current_app.send_task(
                    "notifications.dispatch_user_digital_delivery_task",
                    args=[str(order_id)],
                )

            ts.on_commit(dispatch_digital)
