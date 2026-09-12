from unittest.mock import MagicMock, patch

from apps.core.tasks import ErrorHandlingTask, cleanup_sessions


class TestCoreTasks:
    @patch("apps.core.tasks.call_command")
    def test_cleanup_sessions_task_calls_django_command(self, mock_call_command: MagicMock) -> None:
        cleanup_sessions()

        mock_call_command.assert_called_once_with("clearsessions")

    @patch("apps.core.tasks.logger.error")
    def test_error_handling_task_logs_on_failure(self, mock_logger_error: MagicMock) -> None:
        task = ErrorHandlingTask()
        task.name = "core.test_mock_task"
        exception = ValueError("Test exception occurred")
        task_id = "test-task-id-123"

        task.on_failure(
            exc=exception,
            task_id=task_id,
            args=(),
            kwargs={},
            einfo=None,
        )

        mock_logger_error.assert_called_once_with(f"Task {task.name} [{task_id}] failed! Error: {exception}")
