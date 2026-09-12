from django.urls import path

from apps.basket.views import BasketAPIView, BasketCalculatePriceView, BasketDetailAPIView

urlpatterns = [
    path("", BasketAPIView.as_view(), name="basket_api"),
    path("<int:variant_id>/", BasketDetailAPIView.as_view(), name="basket_detail_api"),
    path("calculate/", BasketCalculatePriceView.as_view(), name="basket_calculate_api"),
]
