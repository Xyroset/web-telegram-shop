from typing import cast

import pytest
from django.urls import reverse
from pytest_mock import MockerFixture
from rest_framework import status
from rest_framework.test import APIClient

from apps.users.factories import UserDeliveryDataFactory, UserSettingsFactory
from apps.users.models import User, UserDeliveryData


@pytest.mark.django_db
class TestTelegramAuthView:
    """
    Verify HTTP lifecycle of Telegram authorization via POST auth_telegram_api.
    """

    def test_auth_success_new_user(self, api_client: APIClient, mocker: MockerFixture) -> None:
        """
        Happy path: Authenticate a new user via mocked Telegram initData.
        """
        url = reverse("auth_telegram_api")
        payload = {"initData": "query_id=fake_data", "theme": "dark"}
        mock_validate = mocker.patch("apps.telegram.usecases.ValidateInitTelegramDataCase.execute")
        mock_validate.return_value = {"id": 123456789, "username": "new_user", "first_name": "Test"}
        mocker.patch("django.db.transaction.on_commit")

        response = api_client.post(url, payload)

        assert response.status_code == status.HTTP_200_OK
        assert "access_token" in response.data
        assert "refresh_token" in response.cookies
        assert User.objects.filter(tg_id=123456789).exists()


@pytest.mark.django_db
class TestUserTokenRefreshView:
    """
    Verify HTTP lifecycle of JWT token refresh via POST token_refresh_api.
    """

    def test_refresh_token_success(self, api_client: APIClient, user: User) -> None:
        """
        Happy path: Successfully refresh access token using valid HttpOnly cookie.
        """
        from rest_framework_simplejwt.tokens import RefreshToken

        refresh = RefreshToken.for_user(user)
        api_client.cookies["refresh_token"] = str(refresh)
        url = reverse("token_refresh_api")

        response = api_client.post(url)

        assert response.status_code == status.HTTP_200_OK
        assert "access_token" in response.data


@pytest.mark.django_db
class TestGetUserDataView:
    """
    Verify HTTP lifecycle of retrieving user profile via GET get_data_user_api.
    """

    def test_get_user_data_success(self, api_client: APIClient, user: User) -> None:
        """
        Happy path: Retrieve authenticated user data.
        """
        api_client.force_authenticate(user=user)
        url = reverse("get_data_user_api")

        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["tg_id"] == user.tg_id

    def test_get_user_data_unauthorized(self, api_client: APIClient) -> None:
        """
        Failure: Unauthenticated user access blocked.
        """
        url = reverse("get_data_user_api")

        response = api_client.get(url)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestUserSettingsAPIView:
    """
    Verify HTTP lifecycle of retrieving and updating settings via settings_data_api.
    """

    def test_get_settings_success(self, api_client: APIClient, user: User) -> None:
        """
        Happy path: Retrieve user settings.
        """
        UserSettingsFactory(user=user, preferred_network="trc20", preferred_payment_currency="usdt")
        api_client.force_authenticate(user=user)
        url = reverse("settings_data_api")

        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["preferred_network"] == "trc20"
        assert response.data["preferred_payment_currency"] == "usdt"

    def test_update_settings_success(self, api_client: APIClient, user: User, mocker: MockerFixture) -> None:
        """
        Happy path: Update user settings successfully.
        """
        UserSettingsFactory(user=user)
        api_client.force_authenticate(user=user)
        url = reverse("settings_data_api")
        payload = {"preferred_network": "erc20", "preferred_payment_currency": "eth"}
        mocker.patch("apps.users.usecases.InvoiceCreationService.validate_currency_network")

        response = api_client.put(url, payload)

        assert response.status_code == status.HTTP_200_OK
        user.settings.refresh_from_db()
        assert user.settings.preferred_network == "erc20"


@pytest.mark.django_db
class TestUserSettingsResetToDefaultView:
    """
    Verify HTTP lifecycle of resetting user settings via settings_data_reset_to_default_api.
    """

    def test_reset_settings_success(self, api_client: APIClient, user: User, mocker: MockerFixture) -> None:
        """
        Happy path: Reset user settings to shop configuration defaults.
        """
        UserSettingsFactory(user=user, preferred_network="weird_net")
        api_client.force_authenticate(user=user)
        url = reverse("settings_data_reset_to_default_api")
        mock_config = mocker.patch("apps.users.views.base.shop_config.get")
        mock_config.return_value = {"preferred_network": "trc20", "preferred_payment_currency": "usdt"}
        mocker.patch("apps.users.usecases.InvoiceCreationService.validate_currency_network")

        response = api_client.put(url)

        assert response.status_code == status.HTTP_200_OK
        user.settings.refresh_from_db()
        assert user.settings.preferred_network == "trc20"


@pytest.mark.django_db
class TestUserDeliveryDataAPIView:
    """
    Verify HTTP lifecycle of list/create user delivery data.
    """

    def test_get_delivery_data_list(self, api_client: APIClient, user: User) -> None:
        """
        Happy path: List user's delivery data.
        """
        UserDeliveryDataFactory(user=user, destination_code="US")
        UserDeliveryDataFactory(user=user, destination_code="GB", is_current=False)
        api_client.force_authenticate(user=user)
        url = reverse("delivery_data_api")

        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 2

    def test_create_delivery_data_success(self, api_client: APIClient, user: User, mocker: MockerFixture) -> None:
        """
        Happy path: Create new delivery data entry.
        """
        api_client.force_authenticate(user=user)
        url = reverse("delivery_data_api")
        payload = {"destination_code": "US", "region_code": "NY", "full_name": "Vlad"}
        mocker.patch(
            "apps.users.usecases.DeliveryValidationService.validate_and_format",
            return_value=payload,
        )

        response = api_client.post(url, payload)

        assert response.status_code == status.HTTP_201_CREATED
        assert user.delivery_data.filter(destination_code="US").exists()


@pytest.mark.django_db
class TestUserDeliveryDataDetailsAPIView:
    """
    Verify HTTP lifecycle of update/delete for specific delivery data.
    """

    def test_update_delivery_data_success(self, api_client: APIClient, user: User, mocker: MockerFixture) -> None:
        """
        Happy path: Update existing delivery data.
        """
        delivery_data = cast(
            UserDeliveryData, UserDeliveryDataFactory(user=user, full_name="Old Name", destination_code="US")
        )
        api_client.force_authenticate(user=user)
        url = reverse("delivery_data_details_api", kwargs={"id": delivery_data.id})
        payload = {"full_name": "New Name"}
        mocker.patch(
            "apps.users.usecases.DeliveryValidationService.validate_and_format",
            return_value={"full_name": "New Name", "destination_code": "US"},
        )

        response = api_client.put(url, payload)

        assert response.status_code == status.HTTP_200_OK
        delivery_data.refresh_from_db()
        assert delivery_data.full_name == "New Name"

    def test_delete_delivery_data_success(self, api_client: APIClient, user: User) -> None:
        """
        Happy path: Delete specific delivery data.
        """
        delivery_data = cast(UserDeliveryData, UserDeliveryDataFactory(user=user))
        api_client.force_authenticate(user=user)
        url = reverse("delivery_data_details_api", kwargs={"id": delivery_data.id})

        response = api_client.delete(url)

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not user.delivery_data.filter(id=delivery_data.id).exists()


@pytest.mark.django_db
class TestUserDeliveryDataManagementAPIView:
    """
    Verify HTTP lifecycle of toggling current delivery address.
    """

    def test_set_current_delivery_data(self, api_client: APIClient, user: User) -> None:
        """
        Happy path: Set a delivery address as current.
        """
        old_current = cast(UserDeliveryData, UserDeliveryDataFactory(user=user, is_current=True))
        target = cast(UserDeliveryData, UserDeliveryDataFactory(user=user, is_current=False))
        api_client.force_authenticate(user=user)
        url = reverse("delivery_data_management_api", kwargs={"id": target.id})

        response = api_client.patch(url)

        assert response.status_code == status.HTTP_200_OK
        target.refresh_from_db()
        old_current.refresh_from_db()
        assert target.is_current is True
        assert old_current.is_current is False

    def test_unset_current_delivery_data(self, api_client: APIClient, user: User) -> None:
        """
        Happy path: Unset the current delivery address.
        """
        delivery_data = cast(UserDeliveryData, UserDeliveryDataFactory(user=user, is_current=True))
        api_client.force_authenticate(user=user)
        url = reverse("delivery_data_management_api", kwargs={"id": delivery_data.id})

        response = api_client.delete(url)

        assert response.status_code == status.HTTP_204_NO_CONTENT
        delivery_data.refresh_from_db()
        assert delivery_data.is_current is False
