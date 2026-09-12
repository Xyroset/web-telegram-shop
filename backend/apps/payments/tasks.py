import logging
import uuid

from celery import shared_task
from django.db import OperationalError

from apps.core.domain.exceptions import CoreObjectNotFoundError
from apps.core.tasks import ErrorHandlingTask
from apps.payments.repo import PaymentTransactionRepository
from apps.payments.usecases import ExpireTransactionCase

logger = logging.getLogger(__name__)


@shared_task(
    base=ErrorHandlingTask,
    name="payments.expire_transaction",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def expire_transaction_task(self, transaction_id: str | uuid.UUID) -> None:
    """
    Execute the transaction expiration use case as a background task.

    **Business Rules:**
    - Delegates execution to the ExpireTransactionCase.
    - Silently catches CoreObjectNotFoundError and logs it (avoids endless retries for deleted/missing transactions).
    - Triggers a Celery task retry for database OperationalErrors.

    **Required:**
    - A valid transaction_id representing an existing transaction.
    """
    usecase = ExpireTransactionCase(payment_repo=PaymentTransactionRepository())

    try:
        usecase.execute(transaction_id=str(transaction_id))

    except CoreObjectNotFoundError:
        logger.error(f"Transaction not found for expiration. Transaction ID: {transaction_id}")

    except OperationalError as exc:
        logger.error(f"Database error during transaction expiration. Retrying... Error: {exc}")
        raise self.retry(exc=exc)
