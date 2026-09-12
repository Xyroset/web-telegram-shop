import logging

from celery import shared_task
from django.db import OperationalError

from apps.catalog.repo import DigitalAssetRepository, ProductRepository
from apps.core.domain.exceptions import CoreObjectNotFoundError
from apps.core.tasks import ErrorHandlingTask
from apps.delivery.repo import DeliveryRepository
from apps.orders.domain.exceptions import (
    OrderConflictDataError,
    OrderNotFoundError,
    OrderStatusInvalidError,
)
from apps.orders.repo import OrderRepository, PromoCodeRepository
from apps.orders.usecases.cancellation import ExpireOrderCase
from apps.orders.usecases.fulfillment import ProcessOrderFulfillmentCase
from apps.payments.repo import PaymentTransactionRepository
from apps.users.repo import UserRepository

logger = logging.getLogger(__name__)


@shared_task(
    base=ErrorHandlingTask,
    name="orders.expire_order",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def expire_order_task(self: ErrorHandlingTask, order_id: str) -> None:
    """
    Execute the order expiration use case as a background task.

    **Business Rules:**
    - Delegates execution to ExpireOrderCase.
    - Catches CoreObjectNotFoundError/OrderNotFoundError and logs warning (avoids retry loops for deleted orders).
    - Catches OrderStatusInvalidError/OrderConflictDataError when order state changed before expiration.
    - Retries task automatically upon database OperationalError.

    **Required:**
    - Valid order_id representing an existing order.
    """
    usecase = ExpireOrderCase(
        order_repo=OrderRepository(),
        user_repo=UserRepository(),
        delivery_repo=DeliveryRepository(),
        payment_repo=PaymentTransactionRepository(),
        promocode_repo=PromoCodeRepository(),
        product_repo=ProductRepository(),
        digital_asset_repo=DigitalAssetRepository(),
    )

    try:
        usecase.execute(order_id=order_id)

    except (CoreObjectNotFoundError, OrderNotFoundError):
        logger.warning(f"Order {order_id} not found for expiration, task skipped.")

    except (OrderStatusInvalidError, OrderConflictDataError) as exc:
        logger.info(f"Order {order_id} state changed, expiration aborted: {exc}")

    except OperationalError as exc:
        logger.error(f"Database operational error during order {order_id} expiration. Retrying: {exc}")
        raise self.retry(exc=exc)


@shared_task(base=ErrorHandlingTask, name="orders.process_order_fulfillment_task")
def process_order_fulfillment_task(order_id: str) -> None:
    """
    Execute post-payment fulfillment orchestration as a background task.

    **Business Rules:**
    - Delegates fulfillment execution to ProcessOrderFulfillmentCase.
    """
    usecase = ProcessOrderFulfillmentCase(
        order_repo=OrderRepository(),
        delivery_repo=DeliveryRepository(),
        product_repo=ProductRepository(),
        digital_asset_repo=DigitalAssetRepository(),
    )

    usecase.execute(order_id=order_id)
