from dataclasses import asdict
from unittest.mock import MagicMock, patch

from pytest_mock import MockerFixture

from apps.core.domain.exceptions import CoreObjectNotFoundError
from apps.users.domain.dto import UserDeliveryDataDTO, UserSettingsDataDTO
from apps.users.repo import UserDeliveryDataRepository, UserSettingsDataRepository
from apps.users.usecases import (
    CreateUserDeliveryDataCase,
    UpdateUserDeliveryDataCase,
    UpdateUserSettingsCase,
)


@patch("django.db.transaction.atomic", MagicMock())
class TestUpdateUserSettingsCase:
    """
    Verify business rules for updating user settings and validating payment networks.
    """

    def test_execute_success_with_updates(self, mocker: MockerFixture) -> None:
        """
        Happy path: Validate currency/network and update settings successfully.
        """
        mock_repo: MagicMock | UserSettingsDataRepository = MagicMock()
        mock_settings = MagicMock()
        mock_settings.preferred_payment_currency = "btc"
        mock_settings.preferred_network = "btc"
        mock_settings.update_settings.return_value = ["preferred_payment_currency"]
        mock_repo.get_for_update_by.return_value = mock_settings  # type: ignore[union-attr]

        mock_validate_network = mocker.patch("apps.users.usecases.InvoiceCreationService.validate_currency_network")

        usecase = UpdateUserSettingsCase(settings_repo=mock_repo)
        mock_user = MagicMock()
        dto = UserSettingsDataDTO(preferred_payment_currency="usdt", preferred_network="trc20")

        usecase.execute(user=mock_user, dto=dto)

        mock_repo.get_for_update_by.assert_called_once_with(user=mock_user)  # type: ignore[union-attr]
        mock_validate_network.assert_called_once_with(
            currency="usdt",
            network="trc20",
            provider_name="nowpayments",
        )
        mock_settings.update_settings.assert_called_once_with(dto=dto)
        mock_repo.save.assert_called_once_with(instance=mock_settings, update_fields=["preferred_payment_currency"])  # type: ignore[union-attr]

    def test_execute_success_no_fields_to_update(self, mocker: MockerFixture) -> None:
        """
        Happy path: If DTO doesn't change anything, repository save is not called.
        """
        mock_repo: MagicMock | UserSettingsDataRepository = MagicMock()
        mock_settings = MagicMock()
        mock_settings.preferred_payment_currency = "usdt"
        mock_settings.preferred_network = "trc20"
        mock_settings.update_settings.return_value = []
        mock_repo.get_for_update_by.return_value = mock_settings  # type: ignore[union-attr]

        mock_validate_network = mocker.patch("apps.users.usecases.InvoiceCreationService.validate_currency_network")

        usecase = UpdateUserSettingsCase(settings_repo=mock_repo)
        mock_user = MagicMock()
        dto = UserSettingsDataDTO()

        usecase.execute(user=mock_user, dto=dto)

        mock_validate_network.assert_called_once_with(
            currency="usdt",
            network="trc20",
            provider_name="nowpayments",
        )
        mock_repo.save.assert_not_called()  # type: ignore[union-attr]


@patch("django.db.transaction.atomic", MagicMock())
class TestCreateUserDeliveryDataCase:
    """
    Verify business rules for formatting and creating new delivery data.
    """

    def test_execute_success_with_existing_current(self, mocker: MockerFixture) -> None:
        """
        Happy path: Unset previous current delivery data and create a new one.
        """
        mock_repo: MagicMock | UserDeliveryDataRepository = MagicMock()
        mock_current_data = MagicMock()
        mock_current_data.unset_current.return_value = ["is_current"]
        mock_repo.get_for_update_by.return_value = mock_current_data  # type: ignore[union-attr]

        mock_validate_format = mocker.patch("apps.users.usecases.DeliveryValidationService.validate_and_format")
        valid_data = {
            "full_name": "Vlad",
            "email": "test@test.com",
            "phone": "123456789",
            "zip_code": "00000",
            "address_line": "Street 1",
            "destination_code": "US",
            "region_code": "NY",
        }
        mock_validate_format.return_value = valid_data

        usecase = CreateUserDeliveryDataCase(delivery_data_repo=mock_repo)
        mock_user = MagicMock()
        dto = UserDeliveryDataDTO(destination_code="us", region_code="ny", full_name="Vlad")

        usecase.execute(user=mock_user, dto=dto)

        mock_validate_format.assert_called_once_with(raw_data=asdict(dto))
        mock_repo.get_for_update_by.assert_called_once_with(user=mock_user, is_current=True)  # type: ignore[union-attr]
        mock_repo.save.assert_called_once_with(instance=mock_current_data, update_fields=["is_current"])  # type: ignore[union-attr]
        mock_repo.create.assert_called_once_with(user=mock_user, **valid_data)  # type: ignore[union-attr]

    def test_execute_success_no_existing_current(self, mocker: MockerFixture) -> None:
        """
        Happy path: Create first delivery data when no current data exists.
        """
        mock_repo: MagicMock | UserDeliveryDataRepository = MagicMock()
        mock_repo.get_for_update_by.side_effect = CoreObjectNotFoundError  # type: ignore[union-attr]

        mock_validate_format = mocker.patch("apps.users.usecases.DeliveryValidationService.validate_and_format")
        mock_validate_format.return_value = {"destination_code": "US"}

        usecase = CreateUserDeliveryDataCase(delivery_data_repo=mock_repo)
        mock_user = MagicMock()
        dto = UserDeliveryDataDTO(destination_code="us")

        usecase.execute(user=mock_user, dto=dto)

        mock_repo.save.assert_not_called()  # type: ignore[union-attr]
        mock_repo.create.assert_called_once_with(  # type: ignore[union-attr]
            user=mock_user,
            full_name=None,
            email=None,
            phone=None,
            zip_code=None,
            address_line=None,
            destination_code="US",
            region_code=None,
        )


@patch("django.db.transaction.atomic", MagicMock())
class TestUpdateUserDeliveryDataCase:
    """
    Verify business rules for updating existing delivery data with domain validation.
    """

    def test_execute_success(self, mocker: MockerFixture) -> None:
        """
        Happy path: Validate merged data and update successfully.
        """
        mock_repo: MagicMock | UserDeliveryDataRepository = MagicMock()
        mock_delivery_data = MagicMock()
        mock_delivery_data.destination_code = "GB"
        mock_delivery_data.region_code = None
        mock_delivery_data.full_name = "Old Name"
        mock_delivery_data.update_delivery_data.return_value = ["full_name"]
        mock_repo.get_for_update_by.return_value = mock_delivery_data  # type: ignore[union-attr]

        mock_validate_format = mocker.patch("apps.users.usecases.DeliveryValidationService.validate_and_format")
        mock_validate_format.return_value = {"full_name": "New Name", "destination_code": "GB"}

        usecase = UpdateUserDeliveryDataCase(delivery_data_repo=mock_repo)
        mock_user = MagicMock()
        dto = UserDeliveryDataDTO(full_name="New Name")

        usecase.execute(user=mock_user, id=1, dto=dto)

        mock_repo.get_for_update_by.assert_called_once_with(user=mock_user, id=1)  # type: ignore[union-attr]
        mock_validate_format.assert_called_once()
        mock_repo.save.assert_called_once_with(instance=mock_delivery_data, update_fields=["full_name"])  # type: ignore[union-attr]
