from unittest.mock import MagicMock

from pytest_mock import MockerFixture

from apps.catalog.repo import ProductRepository
from apps.catalog.tasks import cleanup_expired_discounts_task


class TestCleanupExpiredDiscountsTask:
    """
    Verify the behavior of the cleanup_expired_discounts_task.
    """

    def test_cleanup_with_expired_discounts(self, mocker: MockerFixture) -> None:
        """
        Happy path: There are expired discounts to clean up.
        """
        mock_repo: MagicMock | ProductRepository = MagicMock()
        mocker.patch("apps.catalog.tasks.ProductRepository", return_value=mock_repo)
        mock_repo.cleanup_expired_discounts.return_value = 5  # type: ignore[union-attr]

        result = cleanup_expired_discounts_task()

        mock_repo.cleanup_expired_discounts.assert_called_once()  # type: ignore[union-attr]
        assert result == "Cleared 5 expired discounts."

    def test_cleanup_without_expired_discounts(self, mocker: MockerFixture) -> None:
        """
        Happy path: No expired discounts found.
        """
        mock_repo: MagicMock | ProductRepository = MagicMock()
        mocker.patch("apps.catalog.tasks.ProductRepository", return_value=mock_repo)
        mock_repo.cleanup_expired_discounts.return_value = 0  # type: ignore[union-attr]

        result = cleanup_expired_discounts_task()

        mock_repo.cleanup_expired_discounts.assert_called_once()  # type: ignore[union-attr]
        assert result == "Cleared 0 expired discounts."
