from django.urls import path

from apps.orders.views import OrderAPIView, OrderDetailAPIView

urlpatterns = [
    path("", OrderAPIView.as_view(), name="order_api"),
    path("<uuid:order_id>/", OrderDetailAPIView.as_view(), name="order_detail"),
]
