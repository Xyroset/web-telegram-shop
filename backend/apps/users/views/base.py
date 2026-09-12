from typing import Any

from django.utils.functional import cached_property
from drf_spectacular.utils import OpenApiResponse, extend_schema, extend_schema_view
from rest_framework import status
from rest_framework.generics import RetrieveAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.config_manager import shop_config
from apps.users.domain.dto import UserDeliveryDataDTO, UserSettingsDataDTO
from apps.users.models import User
from apps.users.repo import UserDeliveryDataRepository, UserSettingsDataRepository
from apps.users.serializers import (
    GetUserDataResponseSerializer,
    UserDeliveryDataRequestSerializer,
    UserDeliveryDataResponseSerializer,
    UserSettingsSerializer,
)
from apps.users.usecases import (
    CreateUserDeliveryDataCase,
    DeleteUserDeliveryDataCase,
    SetCurrentUserDeliveryDataCase,
    UnSetCurrentUserDeliveryDataCase,
    UpdateUserDeliveryDataCase,
    UpdateUserSettingsCase,
)


@extend_schema_view(
    get=extend_schema(
        summary="Get current user data",
        tags=["User"],
        responses={200: GetUserDataResponseSerializer},
    )
)
class GetUserDataView(RetrieveAPIView):
    """
    API View for retrieving the current authenticated user's profile.

    Permissions:
    - Requires an authenticated user (IsAuthenticated).

    Delegation:
    - **GET**: Returns the serialized profile of `request.user`.
    """

    permission_classes = [IsAuthenticated]
    serializer_class = GetUserDataResponseSerializer

    def get_object(self) -> User:
        return self.request.user  # type: ignore[no-any-return]


@extend_schema_view(
    get=extend_schema(
        summary="Get current user settings",
        tags=["User Settings"],
        request=None,
        responses={200: UserSettingsSerializer},
    ),
    put=extend_schema(
        summary="Update user settings",
        tags=["User Settings"],
        request=UserSettingsSerializer,
        responses={200: OpenApiResponse(description="Settings updated successfully.")},
    ),
)
class UserSettingsAPIView(APIView):
    """
    API View for retrieving and updating user application settings.

    Permissions:
    - Requires an authenticated user (IsAuthenticated).

    Delegation:
    - **GET**: Fetches settings via `UserSettingsDataRepository` and serializes them.
    - **PUT**: Validates payload via `UserSettingsSerializer` and delegates update to `UpdateUserSettingsCase`.
    """

    permission_classes = [IsAuthenticated]

    @cached_property
    def _settings_repo(self) -> UserSettingsDataRepository:
        return UserSettingsDataRepository()

    @cached_property
    def _update_usecase(self) -> UpdateUserSettingsCase:
        return UpdateUserSettingsCase(settings_repo=self._settings_repo)

    def get(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        settings = self._settings_repo.get_by(user=request.user)

        raw_data = {
            "preferred_network": settings.preferred_network,
            "preferred_payment_currency": settings.preferred_payment_currency,
            "particles_style": settings.particles_style,
            "language_code": settings.current_language_code,
            "theme": settings.current_theme,
        }

        response_serializer = UserSettingsSerializer(raw_data)
        return Response(response_serializer.data, status=status.HTTP_200_OK)

    def put(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        request_serializer = UserSettingsSerializer(data=request.data)
        request_serializer.is_valid(raise_exception=True)
        valid_data = request_serializer.validated_data

        dto = UserSettingsDataDTO(
            preferred_network=valid_data.get("preferred_network"),
            preferred_payment_currency=valid_data.get("preferred_payment_currency"),
            particles_style=valid_data.get("particles_style"),
            custom_language_code=valid_data.get("language_code"),
            custom_theme=valid_data.get("theme"),
        )

        self._update_usecase.execute(user=request.user, dto=dto)

        return Response(status=status.HTTP_200_OK)


@extend_schema_view(
    put=extend_schema(
        summary="Reset user settings to default state",
        tags=["User Settings"],
        request=None,
        responses={200: OpenApiResponse(description="Settings reset to defaults successfully.")},
    ),
)
class UserSettingsResetToDefaultView(APIView):
    """
    API View for resetting user settings to system defaults.

    Permissions:
    - Requires an authenticated user (IsAuthenticated).

    Delegation:
    - **PUT**: Loads defaults from `shop_config` and delegates updates to `UpdateUserSettingsCase`.
    """

    permission_classes = [IsAuthenticated]

    @cached_property
    def _settings_repo(self) -> UserSettingsDataRepository:
        return UserSettingsDataRepository()

    @cached_property
    def _update_usecase(self) -> UpdateUserSettingsCase:
        return UpdateUserSettingsCase(settings_repo=self._settings_repo)

    def put(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        default_settings = dict(shop_config.get("user", "user_settings.settings_default"))

        dto = UserSettingsDataDTO(
            preferred_network=default_settings.get("preferred_network"),
            preferred_payment_currency=default_settings.get("preferred_payment_currency"),
            particles_style=default_settings.get("particles_style"),
            custom_language_code=default_settings.get("custom_language_code"),
            custom_theme=default_settings.get("custom_theme"),
        )

        self._update_usecase.execute(user=request.user, dto=dto)

        return Response(status=status.HTTP_200_OK)


@extend_schema_view(
    get=extend_schema(
        summary="Get user's delivery data",
        tags=["User Delivery Data"],
        request=None,
        responses={200: UserDeliveryDataResponseSerializer(many=True)},
    ),
    post=extend_schema(
        summary="Create a new user delivery data",
        tags=["User Delivery Data"],
        request=UserDeliveryDataRequestSerializer,
        responses={201: OpenApiResponse(description="Delivery data created successfully.")},
    ),
)
class UserDeliveryDataAPIView(APIView):
    """
    API View for managing user delivery records collection.

    Permissions:
    - Requires an authenticated user (IsAuthenticated).

    Delegation:
    - **GET**: Retrieves list of delivery addresses via `UserDeliveryDataRepository`.
    - **POST**: Validates input data and delegates creation to `CreateUserDeliveryDataCase`.
    """

    permission_classes = [IsAuthenticated]

    @cached_property
    def _delivery_data_repo(self) -> UserDeliveryDataRepository:
        return UserDeliveryDataRepository()

    @cached_property
    def _create_delivery_data(self) -> CreateUserDeliveryDataCase:
        return CreateUserDeliveryDataCase(delivery_data_repo=self._delivery_data_repo)

    def get(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        all_delivery_data = self._delivery_data_repo.filter_by(user=request.user)

        response_serializer = UserDeliveryDataResponseSerializer(all_delivery_data, many=True)
        return Response(response_serializer.data, status=status.HTTP_200_OK)

    def post(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        request_serializer = UserDeliveryDataRequestSerializer(data=request.data)
        request_serializer.is_valid(raise_exception=True)
        valid_data = request_serializer.validated_data

        dto = UserDeliveryDataDTO(
            full_name=valid_data.get("full_name"),
            email=valid_data.get("email"),
            phone=valid_data.get("phone"),
            zip_code=valid_data.get("zip_code"),
            address_line=valid_data.get("address_line"),
            destination_code=valid_data.get("destination_code"),
            region_code=valid_data.get("region_code"),
        )

        self._create_delivery_data.execute(user=request.user, dto=dto)

        return Response(status=status.HTTP_201_CREATED)


@extend_schema_view(
    put=extend_schema(
        summary="Update one item user delivery data",
        tags=["User Delivery Data"],
        request=UserDeliveryDataRequestSerializer,
        responses={200: OpenApiResponse(description="Delivery data updated successfully.")},
    ),
    delete=extend_schema(
        summary="Delete one item user delivery data",
        tags=["User Delivery Data"],
        request=None,
        responses={204: OpenApiResponse(description="Delivery data deleted successfully.")},
    ),
)
class UserDeliveryDataDetailsAPIView(APIView):
    """
    API View for updating and deleting a specific delivery data entry.

    Permissions:
    - Requires an authenticated user (IsAuthenticated).

    Delegation:
    - **PUT**: Validates input data and delegates update to `UpdateUserDeliveryDataCase`.
    - **DELETE**: Delegates deletion to `DeleteUserDeliveryDataCase`.
    """

    permission_classes = [IsAuthenticated]

    @cached_property
    def _delivery_data_repo(self) -> UserDeliveryDataRepository:
        return UserDeliveryDataRepository()

    @cached_property
    def _update_delivery_data(self) -> UpdateUserDeliveryDataCase:
        return UpdateUserDeliveryDataCase(delivery_data_repo=self._delivery_data_repo)

    @cached_property
    def _delete_delivery_data(self) -> DeleteUserDeliveryDataCase:
        return DeleteUserDeliveryDataCase(delivery_data_repo=self._delivery_data_repo)

    def put(self, request: Request, id: int, *args: Any, **kwargs: Any) -> Response:
        request_serializer = UserDeliveryDataRequestSerializer(data=request.data)
        request_serializer.is_valid(raise_exception=True)
        valid_data = request_serializer.validated_data

        dto = UserDeliveryDataDTO(
            full_name=valid_data.get("full_name"),
            email=valid_data.get("email"),
            phone=valid_data.get("phone"),
            zip_code=valid_data.get("zip_code"),
            address_line=valid_data.get("address_line"),
            destination_code=valid_data.get("destination_code"),
            region_code=valid_data.get("region_code"),
        )

        self._update_delivery_data.execute(user=request.user, id=id, dto=dto)

        return Response(status=status.HTTP_200_OK)

    def delete(self, request: Request, id: int, *args: Any, **kwargs: Any) -> Response:
        self._delete_delivery_data.execute(user=request.user, id=id)

        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema_view(
    patch=extend_schema(
        summary="Set is current one item user delivery data",
        tags=["User Delivery Data"],
        request=None,
        responses={200: OpenApiResponse(description="Delivery data marked as current.")},
    ),
    delete=extend_schema(
        summary="Unset is current one item user delivery data",
        tags=["User Delivery Data"],
        request=None,
        responses={204: OpenApiResponse(description="Delivery data unmarked as current.")},
    ),
)
class UserDeliveryDataManagementAPIView(APIView):
    """
    API View for toggling the active status of a user's delivery address.

    Permissions:
    - Requires an authenticated user (IsAuthenticated).

    Delegation:
    - **PATCH**: Delegates marking the record as current to `SetCurrentUserDeliveryDataCase`.
    - **DELETE**: Delegates unsetting the record as current to `UnSetCurrentUserDeliveryDataCase`.
    """

    permission_classes = [IsAuthenticated]

    @cached_property
    def _delivery_data_repo(self) -> UserDeliveryDataRepository:
        return UserDeliveryDataRepository()

    @cached_property
    def _set_current_delivery_data(self) -> SetCurrentUserDeliveryDataCase:
        return SetCurrentUserDeliveryDataCase(delivery_data_repo=self._delivery_data_repo)

    @cached_property
    def _unset_current_delivery_data(self) -> UnSetCurrentUserDeliveryDataCase:
        return UnSetCurrentUserDeliveryDataCase(delivery_data_repo=self._delivery_data_repo)

    def patch(self, request: Request, id: int, *args: Any, **kwargs: Any) -> Response:
        self._set_current_delivery_data.execute(user=request.user, id=id)

        return Response(status=status.HTTP_200_OK)

    def delete(self, request: Request, id: int, *args: Any, **kwargs: Any) -> Response:
        self._unset_current_delivery_data.execute(user=request.user, id=id)

        return Response(status=status.HTTP_204_NO_CONTENT)
