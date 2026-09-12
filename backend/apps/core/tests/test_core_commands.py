import io
from unittest.mock import MagicMock, patch

from django.core.management import call_command


@patch("apps.core.management.commands.reload_shop_config.shop_config.reload")
class TestReloadShopConfig:
    def test_reload_shop_config_success(self, mock_reload: MagicMock) -> None:
        mock_reload.return_value = {"locales": {"en": "English"}}
        stdout = io.StringIO()

        call_command("reload_shop_config", stdout=stdout)

        assert "Successfully reloaded all configuration files" in stdout.getvalue()
        mock_reload.assert_called_once()

    def test_reload_shop_config_empty_warning(self, mock_reload: MagicMock) -> None:
        mock_reload.return_value = {}
        stdout = io.StringIO()

        call_command("reload_shop_config", stdout=stdout)

        assert "Config directory is empty or missing active YAML files." in stdout.getvalue()
        mock_reload.assert_called_once()

    def test_reload_shop_config_handles_exception(self, mock_reload: MagicMock) -> None:
        mock_reload.side_effect = ValueError("File parsing failed")
        stderr = io.StringIO()
        stdout = io.StringIO()

        call_command("reload_shop_config", stdout=stdout, stderr=stderr)

        assert "Critical error during configuration reload: File parsing failed" in stderr.getvalue()
        mock_reload.assert_called_once()
