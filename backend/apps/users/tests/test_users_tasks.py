from unittest.mock import MagicMock

from pytest_mock import MockerFixture

from apps.users.tasks import update_user_avatar
from apps.users.usecases import UpdateUserAvatarCase


class TestUpdateUserAvatarTask:
    """
    Verify the background task execution for updating user avatars.
    """

    def test_update_user_avatar_task_execution(self, mocker: MockerFixture) -> None:
        """
        Happy path: Ensure task instantiates dependencies and triggers usecase execution.

        **Setup:**
        - Patch the TelegramBotClient and os.getenv to avoid real external configuration.
        - Patch the UpdateUserAvatarCase class to monitor instantiation and execution.

        **Expected:**
        - UpdateUserAvatarCase is instantiated.
        - execute() method is called with the target tg_id.
        """
        mocker.patch("apps.users.tasks.os.getenv", return_value="fake_token")
        mocker.patch("apps.users.tasks.TelegramBotClient")
        mocker.patch("apps.users.tasks.FetchTelegramAvatarsCase")
        mocker.patch("apps.users.tasks.UserRepository")
        mock_usecase_cls = mocker.patch("apps.users.tasks.UpdateUserAvatarCase")
        mock_usecase_instance: MagicMock | UpdateUserAvatarCase = MagicMock()
        mock_usecase_cls.return_value = mock_usecase_instance

        update_user_avatar(tg_id=123456789)

        mock_usecase_cls.assert_called_once()
        mock_usecase_instance.execute.assert_called_once_with(tg_id=123456789)  # type: ignore[union-attr]
