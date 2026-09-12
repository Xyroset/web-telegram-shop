from typing import Any
from unittest.mock import MagicMock

import pytest
from django.urls import reverse
from pytest_mock import MockerFixture
from rest_framework import status
from rest_framework.test import APIClient

from apps.telegram.usecases import ProcessTelegramWebhookCase


@pytest.mark.django_db
class TestTelegramWebhookView:
    """Verify HTTP lifecycle and header validation for inbound Telegram webhooks."""

    def test_webhook_success(
        self,
        api_client: APIClient,
        mocker: MockerFixture,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """
        Happy path: Valid secret token triggers webhook payload processing and returns HTTP 200 OK.
        """
        monkeypatch.setenv("TELEGRAM_WEBHOOK_SECRET", "valid_secret_token")
        mock_execute: MagicMock = mocker.patch.object(ProcessTelegramWebhookCase, "execute")
        url = reverse("handle_telegram_bot")
        payload: dict[str, Any] = {
            "update_id": 12345,
            "message": {"text": "/start", "chat": {"id": 100, "type": "private"}},
        }

        response = api_client.post(
            url,
            data=payload,
            format="json",
            HTTP_X_TELEGRAM_BOT_API_SECRET_TOKEN="valid_secret_token",
        )

        assert response.status_code == status.HTTP_200_OK
        mock_execute.assert_called_once_with(update_data=payload)

    def test_webhook_forbidden_invalid_secret_token(
        self,
        api_client: APIClient,
        mocker: MockerFixture,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """
        Failure: Reject request with HTTP 403 when provided secret token does not match server secret.
        """
        monkeypatch.setenv("TELEGRAM_WEBHOOK_SECRET", "valid_secret_token")
        mock_execute: MagicMock = mocker.patch.object(ProcessTelegramWebhookCase, "execute")
        url = reverse("handle_telegram_bot")
        payload: dict[str, Any] = {"update_id": 12345}

        response = api_client.post(
            url,
            data=payload,
            format="json",
            HTTP_X_TELEGRAM_BOT_API_SECRET_TOKEN="invalid_hacker_token",
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.data == {"error": "Unauthorized"}
        mock_execute.assert_not_called()

    def test_webhook_forbidden_missing_secret_header(
        self,
        api_client: APIClient,
        mocker: MockerFixture,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """
        Failure: Reject request with HTTP 403 when secret header is completely omitted.
        """
        monkeypatch.setenv("TELEGRAM_WEBHOOK_SECRET", "valid_secret_token")
        mock_execute: MagicMock = mocker.patch.object(ProcessTelegramWebhookCase, "execute")
        url = reverse("handle_telegram_bot")
        payload: dict[str, Any] = {"update_id": 12345}

        response = api_client.post(url, data=payload, format="json")

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.data == {"error": "Unauthorized"}
        mock_execute.assert_not_called()

    def test_webhook_forbidden_unconfigured_server_secret(
        self,
        api_client: APIClient,
        mocker: MockerFixture,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """
        Failure: Reject request with HTTP 403 if server has no webhook secret configured.
        """
        monkeypatch.delenv("TELEGRAM_WEBHOOK_SECRET", raising=False)
        mock_execute: MagicMock = mocker.patch.object(ProcessTelegramWebhookCase, "execute")
        url = reverse("handle_telegram_bot")
        payload: dict[str, Any] = {"update_id": 12345}

        response = api_client.post(
            url,
            data=payload,
            format="json",
            HTTP_X_TELEGRAM_BOT_API_SECRET_TOKEN="any_token",
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.data == {"error": "Unauthorized"}
        mock_execute.assert_not_called()

    def test_webhook_swallows_execution_exceptions(
        self,
        api_client: APIClient,
        mocker: MockerFixture,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """
        Edge case: Catch downstream exceptions, log them, and return HTTP 200 to prevent Telegram retry loops.
        """
        monkeypatch.setenv("TELEGRAM_WEBHOOK_SECRET", "valid_secret_token")
        mock_logger = mocker.patch("apps.telegram.views.logger.error")
        mock_execute: MagicMock = mocker.patch.object(
            ProcessTelegramWebhookCase,
            "execute",
            side_effect=RuntimeError("Internal routing crash"),
        )
        url = reverse("handle_telegram_bot")
        payload: dict[str, Any] = {"update_id": 99999}

        response = api_client.post(
            url,
            data=payload,
            format="json",
            HTTP_X_TELEGRAM_BOT_API_SECRET_TOKEN="valid_secret_token",
        )

        assert response.status_code == status.HTTP_200_OK
        mock_execute.assert_called_once_with(update_data=payload)
        mock_logger.assert_called_once()
