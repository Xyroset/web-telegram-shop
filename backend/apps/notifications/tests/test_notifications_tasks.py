import pytest
from celery.exceptions import Retry
from pytest_mock import MockerFixture

from apps.core.domain.exceptions import CoreObjectNotFoundError
from apps.notifications.domain import exceptions
from apps.notifications.tasks import dispatch_admin_order_paid_notifications_task


class TestDispatchAdminOrderPaidNotificationsTask:
    """
    Verify business rules for dispatching order notifications via Celery.
    """

    def test_dispatch_success(self, mocker: MockerFixture) -> None:
        """
        Happy path: Task executes use case without errors.

        **Setup:**
        - Mock NotifyAdminOrderPaidCase to execute normally.
        - Mock task dependencies (repositories and config).

        **Expected:**
        - The use case executes exactly once.
        - Task does not trigger a retry.
        """
        mocker.patch("apps.notifications.tasks.OrderRepository")
        mocker.patch("apps.notifications.tasks.get_order_alert_providers")
        mock_usecase = mocker.patch("apps.notifications.tasks.NotifyAdminOrderPaidCase")
        mock_usecase_instance = mock_usecase.return_value
        mock_retry = mocker.patch.object(dispatch_admin_order_paid_notifications_task, "retry")

        dispatch_admin_order_paid_notifications_task(order_id="123")

        mock_usecase_instance.execute.assert_called_once_with(order_id="123")
        mock_retry.assert_not_called()

    def test_dispatch_object_not_found(self, mocker: MockerFixture) -> None:
        """
        Failure: Target order does not exist in the database.

        **Setup:**
        - Mock NotifyAdminOrderPaidCase to raise CoreObjectNotFoundError.
        - Mock logger to capture error logs.

        **Expected:**
        - An error is logged.
        - Task retry is NOT triggered (we do not retry unrecoverable errors).
        """
        mocker.patch("apps.notifications.tasks.OrderRepository")
        mocker.patch("apps.notifications.tasks.get_order_alert_providers")
        mock_usecase = mocker.patch("apps.notifications.tasks.NotifyAdminOrderPaidCase")
        mock_usecase_instance = mock_usecase.return_value
        mock_usecase_instance.execute.side_effect = CoreObjectNotFoundError()

        mock_logger = mocker.patch("apps.notifications.tasks.logger")
        mock_retry = mocker.patch.object(dispatch_admin_order_paid_notifications_task, "retry")

        dispatch_admin_order_paid_notifications_task(order_id="123")

        mock_logger.error.assert_called_once_with("Order not found for notification dispatch: 123")
        mock_retry.assert_not_called()

    @pytest.mark.parametrize(
        "exception_class",
        [
            exceptions.NotificationProvidersNotFound,
            exceptions.NotificationProviderRunTimeError,
        ],
    )
    def test_dispatch_triggers_retry(self, mocker: MockerFixture, exception_class: type[Exception]) -> None:
        """
        Failure: Providers fail or are missing, requiring a task retry.

        **Setup:**
        - Parameterized exceptions representing recoverable notification errors.
        - Mock NotifyAdminOrderPaidCase to raise these exceptions.
        - Mock the Celery task 'retry' mechanism to raise Celery's native Retry.

        **Expected:**
        - self.retry() is called with the caught exception.
        """
        mocker.patch("apps.notifications.tasks.OrderRepository")
        mocker.patch("apps.notifications.tasks.get_order_alert_providers")
        mock_usecase = mocker.patch("apps.notifications.tasks.NotifyAdminOrderPaidCase")
        mock_usecase_instance = mock_usecase.return_value

        fake_exc = exception_class("Test error")
        mock_usecase_instance.execute.side_effect = fake_exc

        mock_retry = mocker.patch.object(dispatch_admin_order_paid_notifications_task, "retry")
        mock_retry.side_effect = Retry("Retrying task")

        with pytest.raises(Retry):
            dispatch_admin_order_paid_notifications_task(order_id="123")

        mock_retry.assert_called_once_with(exc=fake_exc)
