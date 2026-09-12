from django.urls import path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from apps.core.views import GetWebAppInitConfigView

urlpatterns = [
    path("schema/", SpectacularAPIView.as_view(), name="schema"),
    path("docs/", SpectacularSwaggerView.as_view(), name="docs"),
    path("config/init/", GetWebAppInitConfigView.as_view(), name="config_init_api"),
]
