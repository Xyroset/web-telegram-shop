import os
from typing import Any

from django.conf import settings
from django.utils.functional import cached_property
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import status
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from apps.telegram.client import TelegramBotClient
from apps.telegram.usecases import ValidateInitTelegramDataCase
from apps.users.domain.dto import TelegramAuthDTO
from apps.users.repo import UserRepository, UserSettingsDataRepository
from apps.users.serializers import (
    CookieTokenRefreshSerializer,
    DevAuthRequestSerializer,
    TelegramAuthRequestSerializer,
    TelegramAuthResponseSerializer,
)
from apps.users.usecases import TelegramAuthUseCase


@extend_schema_view(
    post=extend_schema(
        summary="User authorization via Telegram",
        tags=["Auth"],
        request=TelegramAuthRequestSerializer,
        responses={200: TelegramAuthResponseSerializer},
    )
)
class TelegramAuthView(APIView):
    """
    API View for user authorization via Telegram.

    Permissions:
    - Allows any user (AllowAny). Payload authenticity is verified via Telegram HMAC.

    Delegation:
    - **POST**: Validates Telegram init data via `ValidateInitTelegramDataCase`
      and delegates authentication/creation to `TelegramAuthUseCase`.
    """

    permission_classes = [AllowAny]

    @cached_property
    def _telegram_client(self) -> TelegramBotClient:
        return TelegramBotClient(token=os.getenv("TELEGRAM_BOT_TOKEN", ""))

    @cached_property
    def _validate_init_data_usecase(self) -> ValidateInitTelegramDataCase:
        return ValidateInitTelegramDataCase(self._telegram_client)

    @cached_property
    def _auth_usecase(self) -> TelegramAuthUseCase:
        user_repo = UserRepository()
        settings_repo = UserSettingsDataRepository()
        return TelegramAuthUseCase(user_repo=user_repo, settings_repo=settings_repo)

    def post(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        request_serializer = TelegramAuthRequestSerializer(data=request.data)
        request_serializer.is_valid(raise_exception=True)

        init_data_string = request_serializer.validated_data["initData"]
        theme = request_serializer.validated_data.get("theme", "light")

        tg_user_dict = self._validate_init_data_usecase.execute(init_data=init_data_string)

        valid_data = {
            "tg_id": tg_user_dict.get("id"),
            "tg_username": tg_user_dict.get("username", ""),
            "first_name": tg_user_dict.get("first_name", ""),
            "last_name": tg_user_dict.get("last_name", ""),
            "default_language_code": tg_user_dict.get("language_code", "en"),
            "default_theme": theme,
        }
        dto = TelegramAuthDTO(**valid_data)

        user = self._auth_usecase.execute(dto=dto)

        refresh = RefreshToken.for_user(user)

        response_data = {
            "access_token": str(refresh.access_token),
            "photo": user.photo.url if user.photo else None,
        }

        response_serializer = TelegramAuthResponseSerializer(response_data)
        response = Response(response_serializer.data, status=status.HTTP_200_OK)

        response.set_cookie(
            key="refresh_token",
            value=str(refresh),
            httponly=True,
            secure=not settings.DEBUG,
            samesite="None",
            max_age=30 * 24 * 60 * 60,
        )

        return response


@extend_schema_view(
    post=extend_schema(
        summary="Update access token via HttpOnly Cookie",
        tags=["Auth"],
        request=None,
        responses={200: CookieTokenRefreshSerializer},
    )
)
class UserTokenRefreshView(APIView):
    """
    API View for refreshing JWT access tokens.

    Permissions:
    - Allows any user (AllowAny).

    Delegation:
    - **POST**: Validates the HttpOnly refresh cookie via `CookieTokenRefreshSerializer` and issues a new access token.
    """

    permission_classes = [AllowAny]

    def post(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        serializer = CookieTokenRefreshSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)

        return Response(serializer.validated_data, status=status.HTTP_200_OK)


@extend_schema_view(
    post=extend_schema(
        summary="DEV ONLY: Login without Telegram auth",
        description="Creates or logs in a user using only tg_id. Disabled in production.",
        tags=["Auth"],
        request=DevAuthRequestSerializer,
        responses={200: TelegramAuthResponseSerializer},
    )
)
class DevAuthView(APIView):
    """
    Backdoor API View for local development testing via Swagger.

    Permissions:
    - Allows any user (AllowAny), but strictly guarded by the `settings.DEBUG` flag.

    Delegation:
    - **POST**: Bypasses Telegram HMAC validation and directly delegates creation/login to `TelegramAuthUseCase`.
    """

    permission_classes = [AllowAny]

    @cached_property
    def _auth_usecase(self) -> TelegramAuthUseCase:
        user_repo = UserRepository()
        settings_repo = UserSettingsDataRepository()
        return TelegramAuthUseCase(user_repo=user_repo, settings_repo=settings_repo)

    def post(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        if not getattr(settings, "DEBUG", False):
            raise PermissionDenied("This endpoint is strictly disabled in production mode.")

        request_serializer = DevAuthRequestSerializer(data=request.data)
        request_serializer.is_valid(raise_exception=True)
        tg_id = request_serializer.validated_data["tg_id"]

        valid_data = {
            "tg_id": tg_id,
            "tg_username": f"dev_user_{tg_id}",
            "first_name": "Dev",
            "last_name": "Tester",
            "default_language_code": "en",
            "default_theme": "dark",
        }

        dto = TelegramAuthDTO(**valid_data)

        user = self._auth_usecase.execute(dto=dto, is_dev=getattr(settings, "DEBUG", False))

        refresh = RefreshToken.for_user(user)

        response_data = {
            "access_token": str(refresh.access_token),
            "photo": user.photo.url if user.photo else None,
        }

        response_serializer = TelegramAuthResponseSerializer(response_data)
        response = Response(response_serializer.data, status=status.HTTP_200_OK)

        response.set_cookie(
            key="refresh_token",
            value=str(refresh),
            httponly=True,
            secure=not getattr(settings, "DEBUG", False),
            samesite="None",
            max_age=30 * 24 * 60 * 60,
        )

        return response
