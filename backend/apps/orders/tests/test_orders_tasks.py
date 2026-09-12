import logging
import uuid

import pytest
from celery.exceptions import Retry
from django.db import OperationalError
from pytest_mock import MockerFixture

from apps.core.domain.exceptions import CoreObjectNotFoundError
from apps.orders.domain.exceptions import (
    OrderConflictDataError,
)
from apps.orders.tasks import expire_order_task, process_order_fulfillment_task


class TestExpireOrderTask:
    """
    Verify business rules and error handling for order expiration background task.
    """

    def test_expire_order_task_success(self, mocker: MockerFixture) -> None:
        """
        Happy path: Successfully delegates execution to ExpireOrderCase.
        """
        mock_execute = mocker.patch("apps.orders.tasks.ExpireOrderCase.execute")
        fake_order_id = str(uuid.uuid4())

        expire_order_task(order_id=fake_order_id)

        mock_execute.assert_called_once_with(order_id=fake_order_id)

    def test_expire_order_task_handles_missing_order(
        self, mocker: MockerFixture, caplog: pytest.LogCaptureFixture
    ) -> None:
        """
        Failure: Order does not exist, logs warning and terminates without retrying.
        """
        mocker.patch(
            "apps.orders.tasks.ExpireOrderCase.execute",
            side_effect=CoreObjectNotFoundError("Order missing"),
        )
        mock_retry = mocker.patch.object(expire_order_task, "retry")
        fake_order_id = str(uuid.uuid4())

        with caplog.at_level(logging.WARNING):
            expire_order_task(order_id=fake_order_id)

        mock_retry.assert_not_called()
        assert any(
            f"Order {fake_order_id} not found for expiration" in record.message and record.levelname == "WARNING"
            for record in caplog.records
        )

    def test_expire_order_task_handles_state_conflict(
        self, mocker: MockerFixture, caplog: pytest.LogCaptureFixture
    ) -> None:
        """
        Failure: Order is no longer PENDING, logs info and terminates gracefully.
        """
        mocker.patch(
            "apps.orders.tasks.ExpireOrderCase.execute",
            side_effect=OrderConflictDataError("Only PENDING order can be expired"),
        )
        mock_retry = mocker.patch.object(expire_order_task, "retry")
        fake_order_id = str(uuid.uuid4())

        with caplog.at_level(logging.INFO):
            expire_order_task(order_id=fake_order_id)

        mock_retry.assert_not_called()
        assert any(
            f"Order {fake_order_id} state changed, expiration aborted" in record.message and record.levelname == "INFO"
            for record in caplog.records
        )

    def test_expire_order_task_retries_on_operational_error(
        self, mocker: MockerFixture, caplog: pytest.LogCaptureFixture
    ) -> None:
        """
        Failure: Database connection drop triggers Celery retry.
        """
        db_error = OperationalError("DB connection lost")
        mocker.patch(
            "apps.orders.tasks.ExpireOrderCase.execute",
            side_effect=db_error,
        )
        mock_retry = mocker.patch.object(expire_order_task, "retry", side_effect=Retry("Task retrying"))
        fake_order_id = str(uuid.uuid4())

        with caplog.at_level(logging.ERROR):
            with pytest.raises(Retry):
                expire_order_task(order_id=fake_order_id)

        mock_retry.assert_called_once_with(exc=db_error)
        assert any(
            f"Database operational error during order {fake_order_id} expiration" in record.message
            and record.levelname == "ERROR"
            for record in caplog.records
        )


class TestProcessOrderFulfillmentTask:
    """
    Verify business rules for post-payment fulfillment background task.
    """

    def test_process_order_fulfillment_task_success(self, mocker: MockerFixture) -> None:
        """
        Happy path: Successfully delegates fulfillment to ProcessOrderFulfillmentCase.
        """
        mock_execute = mocker.patch("apps.orders.tasks.ProcessOrderFulfillmentCase.execute")
        fake_order_id = str(uuid.uuid4())

        process_order_fulfillment_task(order_id=fake_order_id)

        mock_execute.assert_called_once_with(order_id=fake_order_id)
