from typing import Any
from unittest.mock import MagicMock, patch

from apps.core.usecases import GetWebAppInitConfigCase
from apps.users.models import User
from apps.users.repo import UserSettingsDataRepository


@patch("django.db.transaction.atomic", MagicMock())
@patch("apps.core.usecases.shop_config.get")
class TestGetWebAppInitConfigCase:
    def test_get_config_with_valid_user_language(self, mock_config_get: MagicMock) -> None:
        def shop_config_side_effect(key: str, _arg: Any, default: Any) -> Any:
            config_data = {
                "locales": {"en": {"txt": "Hello"}, "es": {"txt": "Hola"}},
                "mapper_locales": {"en": "English", "es": "Español"},
                "particles": {"enabled": True},
            }
            return config_data.get(key, default)

        mock_config_get.side_effect = shop_config_side_effect
        mock_user = MagicMock(spec=User)
        mock_settings = MagicMock()
        mock_settings.current_language_code = "es"

        mock_repo: UserSettingsDataRepository | MagicMock = MagicMock()
        mock_repo.get_by.return_value = mock_settings  # type: ignore[union-attr]
        use_case = GetWebAppInitConfigCase(settings_repo=mock_repo)

        result = use_case.execute(user=mock_user)

        assert result["current_language"] == "es"
        assert result["translations"] == {"txt": "Hola"}
        assert result["particles"] == {"enabled": True}
        assert {"es": "Español"} in result["available_languages"]
        assert {"en": "English"} in result["available_languages"]
        mock_repo.get_by.assert_called_once_with(user=mock_user)  # type: ignore[union-attr]

    def test_get_config_fallback_to_en_if_language_unsupported(self, mock_config_get: MagicMock) -> None:
        def shop_config_side_effect(key: str, _arg: Any, default: Any) -> Any:
            config_data = {
                "locales": {"en": {"txt": "Hello"}},
                "mapper_locales": {"en": "English"},
            }
            return config_data.get(key, default)

        mock_config_get.side_effect = shop_config_side_effect
        mock_user = MagicMock(spec=User)
        mock_settings = MagicMock()
        mock_settings.current_language_code = "fr"

        mock_repo: UserSettingsDataRepository | MagicMock = MagicMock()
        mock_repo.get_by.return_value = mock_settings  # type: ignore[union-attr]
        use_case = GetWebAppInitConfigCase(settings_repo=mock_repo)

        result = use_case.execute(user=mock_user)

        assert result["current_language"] == "en"
        assert result["translations"] == {"txt": "Hello"}
        assert result["available_languages"] == [{"en": "English"}]
        mock_repo.get_by.assert_called_once_with(user=mock_user)  # type: ignore[union-attr]

    def test_get_config_with_empty_shop_config(self, mock_config_get: MagicMock) -> None:
        mock_config_get.return_value = {}
        mock_user = MagicMock(spec=User)
        mock_settings = MagicMock()
        mock_settings.current_language_code = "es"

        mock_repo: UserSettingsDataRepository | MagicMock = MagicMock()
        mock_repo.get_by.return_value = mock_settings  # type: ignore[union-attr]
        use_case = GetWebAppInitConfigCase(settings_repo=mock_repo)

        result = use_case.execute(user=mock_user)

        assert result["current_language"] == "en"
        assert result["translations"] == {}
        assert result["available_languages"] == [{"en": "English"}]
        assert result["particles"] == {}
        mock_repo.get_by.assert_called_once_with(user=mock_user)  # type: ignore[union-attr]
