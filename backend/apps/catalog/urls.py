from django.urls import path

from apps.catalog.views import (
    CreateReviewAPIView,
    FavoriteItemAPIView,
    GetCategoriesView,
    GetProductsAPIView,
    GetProductVariantsAPIView,
    GetReviewsAPIView,
    GetTagsView,
    ReviewDetailAPIView,
    SearchSuggestionsView,
)

urlpatterns = [
    path("products/", GetProductsAPIView.as_view(), name="products_get_api"),
    path("products/variants/<int:product_id>/", GetProductVariantsAPIView.as_view(), name="variant_get_api"),
    path("products/suggestions/", SearchSuggestionsView.as_view(), name="products_suggestions_api"),
    path("categories/", GetCategoriesView.as_view(), name="get_categories_api"),
    path("tags/", GetTagsView.as_view(), name="get_tags_api"),
    path("favorites/<int:product_id>/", FavoriteItemAPIView.as_view(), name="favorites_items_api"),
    path("reviews/<int:product_id>/", GetReviewsAPIView.as_view(), name="reviews_get_api"),
    path("reviews/", CreateReviewAPIView.as_view(), name="reviews_create_api"),
    path("reviews/<uuid:id>/", ReviewDetailAPIView.as_view(), name="reviews_detail_api"),
]
