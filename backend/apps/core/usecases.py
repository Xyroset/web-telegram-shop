from collections.abc import Mapping, Sequence
from typing import Any

from django.conf import settings as django_settings

from apps.core.config_manager import shop_config
from apps.core.domain.exceptions import CoreObjectNotFoundError
from apps.users.models import User
from apps.users.repo import UserSettingsDataRepository


class GetWebAppInitConfigCase:
    """
    Retrieve initial WebApp configuration payload for the user.

    **Business Rules:**
    - Extract UI and system configurations (locales, particles, background, payments visual, etc.) from `shop_config`.
    - Determine available language options and default to 'en' if user's language is unsupported or invalid.
    - Retrieve user-specific language preferences via `UserSettingsDataRepository`.
    - Provide initial translation dictionary corresponding to the target language.

    **Required:**
    - Valid `User` domain model instance to fetch user settings.
    """

    def __init__(self, settings_repo: UserSettingsDataRepository) -> None:
        self._settings_repo = settings_repo

    def execute(self, user: User) -> Mapping[str, Any]:
        all_locales: Mapping[str, Any] = shop_config.get("locales", "", {})
        languages: Sequence[Any] = getattr(django_settings, "LANGUAGES", [])
        mapper_locales = {}
        for lang in languages:
            mapper_locales[lang[0]] = lang[1]

        available_languages: Sequence[Mapping[str, str]]
        if all_locales:
            available_languages = [{language: mapper_locales.get(language, "Unknown")} for language in all_locales]
        else:
            available_languages = [{"en": mapper_locales.get("en", "English")}]

        try:
            settings = self._settings_repo.get_by(user=user)
            default_lang = getattr(settings, "current_language_code", "en") or "en"
        except CoreObjectNotFoundError:
            default_lang = "en"

        if default_lang not in all_locales:
            default_lang = "en"

        initial_translations = all_locales.get(default_lang, {})
        particles_settings = shop_config.get("particles", "", {})
        background_settings = shop_config.get("background", "", {})
        payments_settings = shop_config.get("payments_visual", "", {})
        zone_names_extra = shop_config.get("zone_names_extra", "", {})
        footer = shop_config.get("footer", "", {})

        return {
            "available_languages": available_languages,
            "current_language": default_lang,
            "translations": initial_translations,
            "particles": particles_settings,
            "background": background_settings,
            "payments_visual": payments_settings,
            "zone_names_extra": zone_names_extra,
            "footer": footer,
        }
