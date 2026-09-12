from django.urls import path

from apps.delivery.views import DeliveryEstimateView, GetDeliveryView

urlpatterns = [
    path("estimate/", DeliveryEstimateView.as_view(), name="delivery_estimate_api"),
    path("<uuid:order_id>", GetDeliveryView.as_view(), name="delivery_get_api"),
]
