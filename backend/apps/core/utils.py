import logging
import os
from typing import Any

from django.conf import settings

logger = logging.getLogger(__name__)


def get_base_url(name: str = "backend") -> str:
    """
    Get the base URL for the given service (backend or frontend).

    Business Rules:
    - In production (DEBUG=False), resolves to the respective VIRTUAL_HOST.
    - In development (DEBUG=True), resolves to the shared NGROK_STATIC_DOMAIN
      since local Nginx proxies all traffic (frontend, backend, minio)
      through a single domain.
    """
    if not getattr(settings, "DEBUG", False):
        if name == "backend":
            url = os.getenv("BACKEND_VIRTUAL_HOST", "")
        else:
            url = os.getenv("FRONTEND_VIRTUAL_HOST", "")

        if url:
            return f"https://{str(url).split(',')[0].strip()}"
        return ""

    ngrok_domain = os.getenv("NGROK_STATIC_DOMAIN", "").strip()
    if ngrok_domain:
        return f"https://{ngrok_domain}"

    return ""


def safe_format(template: str, context: dict[str, Any]) -> str:
    """
    Safely formats a string template with the provided context.

    If a required key is missing in the context, or positional formatting fails,
    it logs an error and returns the original unformatted template to prevent crashes.
    """
    try:
        return template.format(**context)
    except KeyError as exc:
        logger.error(f"Missing format key {exc} in localized template: '{template}'")
        return template
    except IndexError as exc:
        logger.error(f"Positional formatting error {exc} in template: '{template}'")
        return template
