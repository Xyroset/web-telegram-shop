from io import StringIO
from unittest.mock import MagicMock

import pytest
import requests
from django.core.management import call_command
from pytest_mock import MockerFixture


class TestSetupTelegramWebhookCommand:
    """Verify execution lifecycle and error handling of the setup_telegram_webhook command."""

    def test_command_fails_when_env_variables_missing(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """
        Failure: Command terminates early if bot token or webhook secret are missing.
        """
        monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
        monkeypatch.delenv("TELEGRAM_WEBHOOK_SECRET", raising=False)
        stderr = StringIO()

        call_command("setup_telegram_webhook", stderr=stderr)

        assert "Error: TELEGRAM_BOT_TOKEN or TELEGRAM_WEBHOOK_SECRET not configured." in stderr.getvalue()

    def test_command_success(
        self,
        mocker: MockerFixture,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """
        Happy path: Successfully configure webhook and chat menu button via Telegram API.
        """
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "fake_bot_token")
        monkeypatch.setenv("TELEGRAM_WEBHOOK_SECRET", "fake_webhook_secret")
        mocker.patch(
            "apps.telegram.management.commands.setup_telegram_webhook.get_base_url",
            side_effect=["https://backend.test", "https://frontend.test"],
        )
        mock_response = MagicMock()
        mock_response.json.return_value = {"ok": True, "description": "Webhook was set"}
        mock_post: MagicMock = mocker.patch(
            "apps.telegram.management.commands.setup_telegram_webhook.requests.post",
            return_value=mock_response,
        )
        stdout = StringIO()

        call_command("setup_telegram_webhook", stdout=stdout)

        output = stdout.getvalue()
        assert "Successfully set Webhook!" in output
        assert "Successfully set Menu Button!" in output
        assert mock_post.call_count == 2

    def test_command_handles_telegram_rejection(
        self,
        mocker: MockerFixture,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """
        Failure: Telegram API returns ok: False in response body.
        """
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "fake_bot_token")
        monkeypatch.setenv("TELEGRAM_WEBHOOK_SECRET", "fake_webhook_secret")
        mocker.patch(
            "apps.telegram.management.commands.setup_telegram_webhook.get_base_url",
            return_value="https://test.com",
        )
        mock_response = MagicMock()
        mock_response.json.return_value = {"ok": False, "description": "Bad Webhook: IP address not allowed"}
        mocker.patch(
            "apps.telegram.management.commands.setup_telegram_webhook.requests.post",
            return_value=mock_response,
        )
        stderr = StringIO()

        call_command("setup_telegram_webhook", stderr=stderr)

        assert "Telegram rejected Webhook request: Bad Webhook: IP address not allowed" in stderr.getvalue()

    def test_command_handles_network_exception(
        self,
        mocker: MockerFixture,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """
        Failure: Network or HTTP exception during communication with Telegram.
        """
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "fake_bot_token")
        monkeypatch.setenv("TELEGRAM_WEBHOOK_SECRET", "fake_webhook_secret")
        mocker.patch(
            "apps.telegram.management.commands.setup_telegram_webhook.get_base_url",
            return_value="https://test.com",
        )
        mocker.patch(
            "apps.telegram.management.commands.setup_telegram_webhook.requests.post",
            side_effect=requests.RequestException("Connection refused"),
        )
        stderr = StringIO()

        call_command("setup_telegram_webhook", stderr=stderr)

        assert "Network error while setting Webhook: Connection refused" in stderr.getvalue()
