from unittest.mock import MagicMock, patch

from pytest_mock import MockerFixture

from apps.support.tasks import cleanup_old_closed_topics_task


class TestCleanupOldClosedTopicsTask:
    """
    Unit tests for the Celery cleanup background task.

    **Rules:**
    - Must retrieve required configuration from environment and shop_config.
    - If credentials are missing, terminates gracefully without executing the cleanup case.
    - Instantiates DeleteClosedTopicsCase and executes the cleanup workflow.
    """

    @patch("apps.support.tasks.os.getenv", return_value="fake_bot_token")
    @patch("apps.support.tasks.shop_config.get")
    @patch("apps.support.tasks.TelegramBotClient")
    @patch("apps.support.tasks.TicketRepository")
    @patch("apps.support.tasks.DeleteClosedTopicsCase")
    def test_cleanup_old_closed_topics_task_success(
        self,
        mock_usecase_class: MagicMock,
        mock_repo_class: MagicMock,
        mock_client_class: MagicMock,
        mock_shop_config_get: MagicMock,
        mock_getenv: MagicMock,
    ) -> None:
        def config_side_effect(section: str, key: str, default: int | None = None) -> str | int | None:
            if key == "notifications_settings.providers_settings.telegram.admin_chat_id":
                return "-100123456789"
            if key == "support_settings.max_topic_older_than_days":
                return 14
            return default

        mock_shop_config_get.side_effect = config_side_effect
        mock_usecase_instance = MagicMock()
        mock_usecase_class.return_value = mock_usecase_instance

        cleanup_old_closed_topics_task.apply()

        mock_getenv.assert_called_once_with("TELEGRAM_BOT_TOKEN")
        mock_client_class.assert_called_once_with(token="fake_bot_token")
        mock_repo_class.assert_called_once()
        mock_usecase_class.assert_called_once_with(
            ticket_repo=mock_repo_class.return_value,
            bot_client=mock_client_class.return_value,
            admin_chat_id="-100123456789",
        )
        mock_usecase_instance.execute.assert_called_once_with(older_than_days=14)

    @patch("apps.support.tasks.os.getenv", return_value=None)
    @patch("apps.support.tasks.shop_config.get", return_value=None)
    @patch("apps.support.tasks.DeleteClosedTopicsCase")
    def test_cleanup_old_closed_topics_task_missing_credentials_early_exit(
        self,
        mock_usecase_class: MagicMock,
        mock_shop_config_get: MagicMock,
        mock_getenv: MagicMock,
        mocker: MockerFixture,
    ) -> None:
        mock_logger_error = mocker.patch("apps.support.tasks.logger.error")

        cleanup_old_closed_topics_task.apply()

        mock_logger_error.assert_called_once_with(
            "Missing Telegram configuration or credentials. Skipping cleanup task."
        )
        mock_usecase_class.assert_not_called()
