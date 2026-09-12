from celery import shared_task

from apps.catalog.repo import ProductRepository
from apps.core.tasks import ErrorHandlingTask


@shared_task(base=ErrorHandlingTask, name="catalog.cleanup_expired_discounts", ignore_result=True)
def cleanup_expired_discounts_task() -> str:
    product_repo = ProductRepository()
    count = product_repo.cleanup_expired_discounts()

    return f"Cleared {count} expired discounts."
