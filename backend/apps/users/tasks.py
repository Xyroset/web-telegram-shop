import os

from celery import shared_task

from apps.core.tasks import ErrorHandlingTask
from apps.telegram.client import TelegramBotClient
from apps.telegram.usecases import FetchTelegramAvatarsCase
from apps.users.repo import UserRepository
from apps.users.usecases import UpdateUserAvatarCase


@shared_task(base=ErrorHandlingTask, name="users.update_user_avatar", ignore_result=True, acks_late=True, max_retries=3)
def update_user_avatar(tg_id: int) -> None:
    """
    Execute the user avatar update use case as a background task.

    **Business Rules:**
    - Instantiates the required Telegram client and repository dependencies.
    - Delegates execution to the UpdateUserAvatarCase.
    - Automatically retries on failure via the ErrorHandlingTask base class.

    **Required:**
    - A valid tg_id representing the user.
    - The TELEGRAM_BOT_TOKEN environment variable must be set.
    """
    tg_client = TelegramBotClient(token=os.getenv("TELEGRAM_BOT_TOKEN", ""))
    fetch_telegram_avatar_usecase = FetchTelegramAvatarsCase(client=tg_client)

    usecase = UpdateUserAvatarCase(
        user_repo=UserRepository(), fetch_telegram_avatar_usecase=fetch_telegram_avatar_usecase
    )

    usecase.execute(tg_id=tg_id)
