import os
from collections.abc import Mapping
from typing import Any

import requests
from django.core.management.base import BaseCommand

from apps.core.utils import get_base_url


class Command(BaseCommand):
    """
    Automatically registers the active URL as a Telegram Bot Webhook
    and configures the main menu button to open the Telegram Mini App (Web App).
    """

    help = "Configures Telegram Bot Webhook and Web App menu button."

    def handle(self, *args: Any, **options: Any) -> None:
        """
        Execute the management command.
        """
        bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
        secret_token = os.getenv("TELEGRAM_WEBHOOK_SECRET", "")

        if not bot_token or not secret_token:
            self.stderr.write("Error: TELEGRAM_BOT_TOKEN or TELEGRAM_WEBHOOK_SECRET not configured.")
            return

        backend_domain = get_base_url(name="backend")
        frontend_domain = get_base_url(name="frontend")

        self._set_webhook(
            bot_token=bot_token,
            secret_token=secret_token,
            domain=backend_domain,
        )
        self._set_menu_button(
            bot_token=bot_token,
            domain=frontend_domain,
        )

    def _set_webhook(self, bot_token: str, secret_token: str, domain: str) -> None:
        """
        Configure the Telegram Bot to send updates to the backend webhook URL.
        """
        webhook_url = f"{domain}/api/v1/webhook/telegram/"
        telegram_api_url = f"https://api.telegram.org/bot{bot_token}/setWebhook"

        payload: dict[str, Any] = {
            "url": webhook_url,
            "secret_token": secret_token,
            "allowed_updates": ["message", "callback_query"],
        }

        self.stdout.write(f"Attempting to set Telegram Webhook to: {webhook_url}")
        self._make_telegram_request(
            url=telegram_api_url,
            payload=payload,
            action_name="Webhook",
        )

    def _set_menu_button(self, bot_token: str, domain: str) -> None:
        """
        Configure the Telegram Bot's bottom-left menu button to open the TMA.
        """
        telegram_api_url = f"https://api.telegram.org/bot{bot_token}/setChatMenuButton"

        payload: dict[str, Any] = {
            "menu_button": {
                "type": "web_app",
                "text": "Shop",
                "web_app": {"url": domain},
            }
        }

        self.stdout.write(f"Attempting to set Telegram Menu Button to URL: {domain}")
        self._make_telegram_request(
            url=telegram_api_url,
            payload=payload,
            action_name="Menu Button",
        )

    def _make_telegram_request(
        self,
        url: str,
        payload: Mapping[str, Any],
        action_name: str,
    ) -> None:
        """
        Helper method to execute HTTP POST requests to the Telegram Bot API.
        """
        try:
            response = requests.post(url=url, json=payload, timeout=10.0)
            response.raise_for_status()
            data: dict[str, Any] = response.json()

            if data.get("ok"):
                description = data.get("description", "OK")
                self.stdout.write(self.style.SUCCESS(f"Successfully set {action_name}! Description: {description}"))
            else:
                description = data.get("description", "Unknown error")
                self.stderr.write(f"Telegram rejected {action_name} request: {description}")

        except requests.RequestException as exc:
            self.stderr.write(f"Network error while setting {action_name}: {exc}")
