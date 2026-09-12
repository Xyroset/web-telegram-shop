import logging
from dataclasses import asdict

import sentry_sdk
from celery import current_app
from django.db import transaction as ts

from apps.core.domain.exceptions import CoreObjectNotFoundError
from apps.delivery.domain.services import DeliveryValidationService
from apps.payments.domain.services import InvoiceCreationService
from apps.telegram.usecases import FetchTelegramAvatarsCase
from apps.users.domain.dto import TelegramAuthDTO, UserDeliveryDataDTO, UserSettingsDataDTO
from apps.users.models import User
from apps.users.repo import UserDeliveryDataRepository, UserRepository, UserSettingsDataRepository

logger = logging.getLogger(__name__)


class TelegramAuthUseCase:
    """
    Authorize a new user or get an existing user via Telegram credentials.

    **Business Rules:**
    - If the user does not exist, they are created.
    - If the user exists, their data (like username, name) is updated.
    - After creation or update, a background task is triggered to fetch/update their avatar.

    **Required:**
    - Valid TelegramAuthDTO payload.
    """

    def __init__(self, user_repo: UserRepository, settings_repo: UserSettingsDataRepository) -> None:
        self._user_repo = user_repo
        self._settings_repo = settings_repo

    def execute(self, dto: TelegramAuthDTO, is_dev: bool = False) -> User:
        with ts.atomic():
            user, created = self._user_repo.get_or_create(
                tg_id=dto.tg_id,
                defaults={
                    "tg_username": dto.tg_username,
                    "first_name": dto.first_name,
                    "last_name": dto.last_name,
                },
            )

            if not created:
                updated_fields = user.update_base_parameters(
                    tg_username=dto.tg_username,
                    first_name=dto.first_name,
                    last_name=dto.last_name,
                )

                self._user_repo.save(instance=user, update_fields=updated_fields)

            try:
                settings = self._settings_repo.get_by(user=user)
            except CoreObjectNotFoundError:
                settings = user.init_settings()

            update_dto = UserSettingsDataDTO(
                default_theme=dto.default_theme, default_language_code=dto.default_language_code
            )
            updated_fields_settings = settings.update_settings(dto=update_dto)

            if settings.pk is None:
                self._settings_repo.save(instance=settings)
            elif updated_fields_settings:
                self._settings_repo.save(instance=settings, update_fields=updated_fields_settings)

            if not is_dev:
                ts.on_commit(lambda: current_app.send_task("users.update_user_avatar", args=[user.tg_id]))

            return user


class UpdateUserAvatarCase:
    """
    Check if a user's Telegram photo has changed/exists, and download it.

    **Business Rules:**
    - Triggers the Telegram Avatar Fetch use case.
    - If a valid photo is fetched, the user aggregate photo is updated and persisted.
    - Errors are logged and captured in Sentry.
    """

    def __init__(self, user_repo: UserRepository, fetch_telegram_avatar_usecase: FetchTelegramAvatarsCase) -> None:
        self._user_repo = user_repo
        self._fetch_telegram_avatar_usecase = fetch_telegram_avatar_usecase

    def execute(self, tg_id: int) -> None:
        user = None
        try:
            user = self._user_repo.get_by(tg_id=tg_id)
            current_photo_name = user.photo.name if user.photo else None

            filename, avatar_file = self._fetch_telegram_avatar_usecase.execute(
                tg_id=tg_id, current_photo_path=current_photo_name
            )

            if avatar_file and filename:
                user.save_new_user_avatar(filename=filename, avatar_file=avatar_file)
                self._user_repo.save(instance=user, update_fields=["photo"])

        except Exception as e:
            tg_id_log = user.tg_id if user else tg_id
            username_log = user.username if user else "Unknown"
            logger.error(f"Error update avatar. Tg_id: {tg_id_log}, Username: {username_log}", exc_info=True)
            sentry_sdk.capture_exception(e)
            raise e


class UpdateUserSettingsCase:
    """
    Update user preferences and settings.

    **Business Rules:**
    - Validates the chosen cryptocurrency and network against the active payment provider config.
    - Persists the updated settings to the database.

    **Required:**
    - Valid UserSettingsDataDTO payload.
    - Currency and network must be supported by the provider (e.g. nowpayments).
    """

    def __init__(self, settings_repo: UserSettingsDataRepository) -> None:
        self._settings_repo = settings_repo
        self._invoice_service = InvoiceCreationService()

    def execute(self, user: User, dto: UserSettingsDataDTO) -> None:
        with ts.atomic():
            settings = self._settings_repo.get_for_update_by(user=user)

            currency = (
                dto.preferred_payment_currency
                if dto.preferred_payment_currency is not None
                else settings.preferred_payment_currency
            )
            network = dto.preferred_network if dto.preferred_network is not None else settings.preferred_network

            if currency and network:
                self._invoice_service.validate_currency_network(
                    currency=currency,
                    network=network,
                    provider_name="nowpayments",
                )

            update_fields = settings.update_settings(dto=dto)

            if update_fields:
                self._settings_repo.save(instance=settings, update_fields=update_fields)


class CreateUserDeliveryDataCase:
    """
    Create a new delivery data entry for a user.

    **Business Rules:**
    - Validates destination_code and region_code against shop delivery zones config.
    - Unsets the currently active delivery address if it exists.
    - Creates and saves the new delivery address as current.

    **Required:**
    - Supported destination_code (and region_code if applicable).
    """

    def __init__(self, delivery_data_repo: UserDeliveryDataRepository) -> None:
        self._delivery_data_repo = delivery_data_repo
        self._delivery_validation_service = DeliveryValidationService()

    def execute(self, user: User, dto: UserDeliveryDataDTO) -> None:
        valid_data = self._delivery_validation_service.validate_and_format(raw_data=asdict(dto))

        with ts.atomic():
            try:
                current_delivery_data = self._delivery_data_repo.get_for_update_by(user=user, is_current=True)
                update_fields = current_delivery_data.unset_current()
                if update_fields:
                    self._delivery_data_repo.save(instance=current_delivery_data, update_fields=update_fields)
            except CoreObjectNotFoundError:
                logger.info("Skipped unset current delivery data.")

            self._delivery_data_repo.create(
                user=user,
                full_name=valid_data.get("full_name"),
                email=valid_data.get("email"),
                phone=valid_data.get("phone"),
                zip_code=valid_data.get("zip_code"),
                address_line=valid_data.get("address_line"),
                destination_code=valid_data.get("destination_code"),
                region_code=valid_data.get("region_code"),
            )


class UpdateUserDeliveryDataCase:
    """
    Update an existing user delivery data entry.

    **Business Rules:**
    - Re-validates the merged destination and region codes against shop configuration.
    - Updates fields on the existing delivery data record.

    **Required:**
    - Supported destination_code (and region_code if applicable).
    """

    def __init__(self, delivery_data_repo: UserDeliveryDataRepository) -> None:
        self._delivery_data_repo = delivery_data_repo
        self._delivery_validation_service = DeliveryValidationService()

    def execute(self, user: User, id: int, dto: UserDeliveryDataDTO) -> None:
        with ts.atomic():
            delivery_data = self._delivery_data_repo.get_for_update_by(user=user, id=id)

            if dto.full_name is None:
                dto.full_name = delivery_data.full_name
            if dto.email is None:
                dto.email = delivery_data.email
            if dto.phone is None:
                dto.phone = delivery_data.phone
            if dto.address_line is None:
                dto.address_line = delivery_data.address_line
            if dto.zip_code is None:
                dto.zip_code = delivery_data.zip_code
            if dto.destination_code is None:
                dto.destination_code = delivery_data.destination_code
            if dto.region_code is None:
                dto.region_code = delivery_data.region_code

            valid_dto = UserDeliveryDataDTO(
                **self._delivery_validation_service.validate_and_format(raw_data=asdict(dto))
            )

            update_fields = delivery_data.update_delivery_data(dto=valid_dto)

            if update_fields:
                self._delivery_data_repo.save(instance=delivery_data, update_fields=update_fields)


class DeleteUserDeliveryDataCase:
    """
    Delete a user's delivery data entry.

    **Business Rules:**
    - Safely removes the specified delivery address from the user's profile.
    """

    def __init__(self, delivery_data_repo: UserDeliveryDataRepository) -> None:
        self._delivery_data_repo = delivery_data_repo

    def execute(self, user: User, id: int) -> None:
        with ts.atomic():
            delivery_data = self._delivery_data_repo.get_for_update_by(user=user, id=id)
            self._delivery_data_repo.delete(objects=delivery_data)


class SetCurrentUserDeliveryDataCase:
    """
    Set a specific delivery address as the current default.

    **Business Rules:**
    - Unsets any existing active delivery address.
    - Marks the target delivery data entry as current.
    """

    def __init__(self, delivery_data_repo: UserDeliveryDataRepository) -> None:
        self._delivery_data_repo = delivery_data_repo

    def execute(self, user: User, id: int) -> None:
        with ts.atomic():
            try:
                current_delivery_data = self._delivery_data_repo.get_for_update_by(user=user, is_current=True)
                update_fields = current_delivery_data.unset_current()
                if update_fields:
                    self._delivery_data_repo.save(instance=current_delivery_data, update_fields=update_fields)
            except CoreObjectNotFoundError:
                logger.info("Skipped unset current delivery data.")

            delivery_data = self._delivery_data_repo.get_for_update_by(user=user, id=id)

            update_fields = delivery_data.mark_as_current()
            if update_fields:
                self._delivery_data_repo.save(instance=delivery_data, update_fields=update_fields)


class UnSetCurrentUserDeliveryDataCase:
    """
    Unset a specific delivery address from being the current default.

    **Business Rules:**
    - Removes the `is_current` flag from the specified delivery entry.
    """

    def __init__(self, delivery_data_repo: UserDeliveryDataRepository) -> None:
        self._delivery_data_repo = delivery_data_repo

    def execute(self, user: User, id: int) -> None:
        with ts.atomic():
            delivery_data = self._delivery_data_repo.get_for_update_by(user=user, id=id)

            update_fields = delivery_data.unset_current()
            if update_fields:
                self._delivery_data_repo.save(instance=delivery_data, update_fields=update_fields)
