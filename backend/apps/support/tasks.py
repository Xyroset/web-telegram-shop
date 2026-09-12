import logging
import os

from celery import shared_task

from apps.core.config_manager import shop_config
from apps.core.tasks import ErrorHandlingTask
from apps.support.repo import TicketRepository
from apps.support.usecases import DeleteClosedTopicsCase
from apps.telegram.client import TelegramBotClient

logger = logging.getLogger(__name__)


@shared_task(base=ErrorHandlingTask, name="support.cleanup_old_closed_topics")
def cleanup_old_closed_topics_task() -> None:
    """
    Background task triggered by Celery Beat to delete old closed support topics.

    Fetches the cleanup threshold from application settings and executes
    the topic removal workflow outside the HTTP request lifecycle.
    """
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    admin_chat_id = shop_config.get(
        "notifications",
        "notifications_settings.providers_settings.telegram.admin_chat_id",
    )

    if not bot_token or not admin_chat_id:
        logger.error("Missing Telegram configuration or credentials. Skipping cleanup task.")
        return

    raw_older_than_days = shop_config.get(
        "support",
        "support_settings.max_topic_older_than_days",
        7,
    )
    max_topic_older_than_days = int(raw_older_than_days if raw_older_than_days is not None else 7)

    client = TelegramBotClient(token=bot_token)
    repo = TicketRepository()

    usecase = DeleteClosedTopicsCase(
        ticket_repo=repo,
        bot_client=client,
        admin_chat_id=admin_chat_id,
    )
    usecase.execute(older_than_days=max_topic_older_than_days)
