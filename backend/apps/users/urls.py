from django.conf import settings
from django.urls import path

from apps.users.views import (
    DevAuthView,
    GetUserDataView,
    TelegramAuthView,
    UserDeliveryDataAPIView,
    UserDeliveryDataDetailsAPIView,
    UserDeliveryDataManagementAPIView,
    UserSettingsAPIView,
    UserSettingsResetToDefaultView,
    UserTokenRefreshView,
)

urlpatterns = [
    path("auth/telegram/", TelegramAuthView.as_view(), name="auth_telegram_api"),
    path("token/refresh/", UserTokenRefreshView.as_view(), name="token_refresh_api"),
    path("me/", GetUserDataView.as_view(), name="get_data_user_api"),
    path("me/settings/", UserSettingsAPIView.as_view(), name="settings_data_api"),
    path(
        "me/settings/reset_to_default/",
        UserSettingsResetToDefaultView.as_view(),
        name="settings_data_reset_to_default_api",
    ),
    path("me/delivery_data/", UserDeliveryDataAPIView.as_view(), name="delivery_data_api"),
    path(
        "me/delivery_data/details/<int:id>/",
        UserDeliveryDataDetailsAPIView.as_view(),
        name="delivery_data_details_api",
    ),
    path(
        "me/delivery_data/management/<int:id>/",
        UserDeliveryDataManagementAPIView.as_view(),
        name="delivery_data_management_api",
    ),
]

if getattr(settings, "DEBUG", False):
    urlpatterns += [
        path("auth/dev/", DevAuthView.as_view(), name="auth_dev_api"),
    ]
