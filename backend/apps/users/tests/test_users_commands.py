from io import StringIO
from unittest.mock import MagicMock, patch

from django.core.management.base import OutputWrapper
from pytest_mock import MockerFixture

from apps.users.management.commands.promotesuperuser import Command
from apps.users.repo import UserRepository


@patch("django.db.transaction.atomic", MagicMock())
class TestPromoteSuperuserCommand:
    """
    Verify CLI management command behavior for granting superuser status.
    """

    def test_handle_promote_superuser_success(self, mocker: MockerFixture) -> None:
        """
        Happy path: Successfully find user, promote to superuser with password, and save.
        """
        mock_repo: UserRepository | MagicMock = MagicMock()
        mock_user = MagicMock()
        mock_user.promote_superuser.return_value = ["is_superuser", "is_staff", "password"]
        mock_repo.get_for_update_by.return_value = mock_user  # type: ignore[union-attr]

        mocker.patch("builtins.input", return_value="123456789")
        mocker.patch("getpass.getpass", return_value="secure_password_123")

        cmd = Command()
        cmd._user_repo = mock_repo
        out = StringIO()
        cmd.stdout = OutputWrapper(out)

        cmd.handle()

        mock_repo.get_for_update_by.assert_called_once_with(tg_id=123456789)  # type: ignore[union-attr]
        mock_user.promote_superuser.assert_called_once_with(password="secure_password_123")
        mock_repo.save.assert_called_once_with(  # type: ignore[union-attr]
            instance=mock_user,
            update_fields=["is_superuser", "is_staff", "password"],
        )
        assert "Success! User with TG_ID 123456789" in out.getvalue()
