from unittest.mock import MagicMock, patch

import pytest
from celery.exceptions import Retry
from django.db import OperationalError

from apps.core.domain.exceptions import CoreObjectNotFoundError
from apps.payments.tasks import expire_transaction_task
from apps.payments.usecases import ExpireTransactionCase


class TestExpireTransactionTask:
    """
    Verify background task execution for expiring payment transactions.
    """

    @patch("apps.payments.tasks.ExpireTransactionCase")
    def test_expire_transaction_task_success(self, mock_usecase_class: MagicMock) -> None:
        """
        Happy path: Successfully delegates transaction expiration to ExpireTransactionCase.
        """
        mock_usecase: MagicMock | ExpireTransactionCase = MagicMock()
        mock_usecase_class.return_value = mock_usecase

        expire_transaction_task.apply(args=["tx_123"])

        mock_usecase.execute.assert_called_once_with(transaction_id="tx_123")  # type: ignore[union-attr]

    @patch("apps.payments.tasks.logger.error")
    @patch("apps.payments.tasks.ExpireTransactionCase")
    def test_expire_transaction_task_handles_not_found_without_retry(
        self, mock_usecase_class: MagicMock, mock_logger_error: MagicMock
    ) -> None:
        """
        Failure: If transaction does not exist, log error and do not retry.
        """
        mock_usecase: MagicMock | ExpireTransactionCase = MagicMock()
        mock_usecase.execute.side_effect = CoreObjectNotFoundError("Not found")  # type: ignore[union-attr]
        mock_usecase_class.return_value = mock_usecase

        expire_transaction_task.apply(args=["missing_tx_id"])

        mock_usecase.execute.assert_called_once_with(transaction_id="missing_tx_id")  # type: ignore[union-attr]
        mock_logger_error.assert_called_once()

    @patch("apps.payments.tasks.expire_transaction_task.retry")
    @patch("apps.payments.tasks.ExpireTransactionCase")
    def test_expire_transaction_task_retries_on_operational_error(
        self, mock_usecase_class: MagicMock, mock_retry: MagicMock
    ) -> None:
        """
        Failure: Trigger Celery task retry when a database OperationalError occurs.
        """
        db_error = OperationalError("DB connection lost")
        mock_usecase: MagicMock | ExpireTransactionCase = MagicMock()
        mock_usecase.execute.side_effect = db_error  # type: ignore[union-attr]
        mock_usecase_class.return_value = mock_usecase
        mock_retry.side_effect = Retry()

        with pytest.raises(Retry):
            expire_transaction_task.apply(args=["tx_123"], throw=True)

        mock_retry.assert_called_once_with(exc=db_error)
