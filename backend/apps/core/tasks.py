import logging
from typing import Any

from celery import Task, shared_task
from django.core.management import call_command

logger = logging.getLogger(__name__)


class ErrorHandlingTask(Task):
    """
    Base Celery task class that logs errors on failure.
    """

    def on_failure(
        self,
        exc: Exception,
        task_id: str,
        args: tuple[Any, ...],
        kwargs: dict[str, Any],
        einfo: Any,
    ) -> None:
        logger.error(f"Task {self.name} [{task_id}] failed! Error: {exc}")

        super().on_failure(exc, task_id, args, kwargs, einfo)


@shared_task(
    name="core.cleanup_django_sessions_task",
    base=ErrorHandlingTask,
    ignore_result=True,
)
def cleanup_sessions() -> None:
    """Background task to clear expired Django sessions."""
    call_command("clearsessions")
