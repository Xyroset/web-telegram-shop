from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("api/v1/core/", include("apps.core.urls")),
    path("api/v1/users/", include("apps.users.urls")),
    path("api/v1/catalog/", include("apps.catalog.urls")),
    path("api/v1/orders/", include("apps.orders.urls")),
    path("api/v1/basket/", include("apps.basket.urls")),
    path("api/v1/delivery/", include("apps.delivery.urls")),
    path("api/v1/payments/", include("apps.payments.urls")),
    path("api/v1/support/", include("apps.support.urls")),
    path("api/v1/webhook/telegram/", include("apps.telegram.urls")),
    path("api/v1/i18n/", include("django.conf.urls.i18n")),
    path("admin/", admin.site.urls),
]
