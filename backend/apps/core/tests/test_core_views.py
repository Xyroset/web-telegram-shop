from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.users.factories import UserFactory, UserSettingsFactory


@pytest.mark.django_db
class TestConfigInitAPI:
    @patch("apps.core.usecases.shop_config.get")
    def test_get_init_config_success(self, mock_config_get: MagicMock) -> None:
        def shop_config_side_effect(key: str, _arg: Any, default: Any) -> Any:
            config_data = {
                "locales": {"en": {"txt": "Hello"}},
                "mapper_locales": {"en": "English"},
                "particles": {"enabled": True},
            }
            return config_data.get(key, default)

        mock_config_get.side_effect = shop_config_side_effect
        user = UserFactory()
        UserSettingsFactory(user=user, custom_language_code="en")
        client = APIClient()
        client.force_authenticate(user=user)
        url = reverse("config_init_api")

        response = client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["current_language"] == "en"
        assert response.data["translations"] == {"txt": "Hello"}
        assert response.data["particles"] == {"enabled": True}

    def test_get_init_config_unauthorized(self) -> None:
        client = APIClient()
        url = reverse("config_init_api")

        response = client.get(url)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
