import pytest
from django.urls import reverse
from pytest_mock import MockerFixture
from rest_framework import status
from rest_framework.test import APIClient

from apps.catalog.factories import ProductFactory, ProductVariantFactory
from apps.catalog.models import Category, FavoriteItem, Product, Review, Tag
from apps.users.models import User


@pytest.mark.django_db
class TestGetProductsAPIView:
    """
    Integration tests for GetProductsAPIView.
    """

    def test_get_products_success(self, api_client: APIClient, user: User) -> None:
        """Happy path: Retrieve catalog products successfully."""
        Product.objects.all().delete()

        api_client.force_authenticate(user=user)
        ProductFactory.create(name="Apple")
        ProductFactory.create(name="Banana")
        url = reverse("products_get_api")

        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert "results" in response.data
        assert len(response.data["results"]) == 2

    def test_get_products_with_favorites_injection(self, api_client: APIClient, user: User) -> None:
        """Happy path: Verify user favorites are injected correctly."""
        Product.objects.all().delete()

        api_client.force_authenticate(user=user)
        p1 = ProductFactory.create()
        FavoriteItem.objects.create(user=user, product=p1)
        url = reverse("products_get_api")

        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        results = response.data["results"]
        assert len(results) == 1
        assert results[0]["is_favorite"] is True

    def test_unauthorized_access(self, api_client: APIClient) -> None:
        """Failure: Unauthenticated user attempts to get products."""
        url = reverse("products_get_api")

        response = api_client.get(url)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestGetProductVariantsAPIView:
    def test_get_product_variants_success(self, api_client: APIClient, user: User) -> None:
        api_client.force_authenticate(user=user)
        p1 = ProductFactory.create()
        ProductVariantFactory.create(product=p1, price="10.00")
        ProductVariantFactory.create(product=p1, price="20.00")
        url = reverse("variant_get_api", kwargs={"product_id": p1.id})

        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert isinstance(response.data, list)
        assert len(response.data) == 2


@pytest.mark.django_db
class TestTaxonomyViews:
    """
    Integration tests for Categories and Tags APIs.
    """

    def test_get_categories_success(self, api_client: APIClient, user: User) -> None:
        """Happy path: Get list of categories."""
        Product.objects.all().delete()
        Category.objects.all().delete()

        api_client.force_authenticate(user=user)
        Category.objects.create(name="Tech", slug="tech")
        url = reverse("get_categories_api")

        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
        assert response.data[0]["slug"] == "tech"

    def test_get_tags_success(self, api_client: APIClient, user: User) -> None:
        """Happy path: Get list of tags."""
        Product.objects.all().delete()
        Tag.objects.all().delete()

        api_client.force_authenticate(user=user)
        Tag.objects.create(name="New", slug="new")
        url = reverse("get_tags_api")

        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
        assert response.data[0]["slug"] == "new"


@pytest.mark.django_db
class TestSearchSuggestionsView:
    def test_search_suggestions_success(self, api_client: APIClient, user: User) -> None:
        """Happy path: Get suggestions for a valid search term."""
        Product.objects.all().delete()

        api_client.force_authenticate(user=user)

        ProductFactory.create(name="Smartphone Alpha", base_description="Phone description")
        ProductFactory.create(name="Laptop Beta", base_description="Laptop description")

        url = reverse("products_suggestions_api")

        response = api_client.get(url, {"search": "Smart"})

        assert response.status_code == status.HTTP_200_OK
        assert isinstance(response.data, list)
        assert len(response.data) == 1
        assert response.data[0]["name"] == "Smartphone Alpha"


@pytest.mark.django_db
class TestFavoriteItemAPIView:
    """
    Integration tests for Favorite API operations.
    """

    def test_add_favorite_success(self, api_client: APIClient, user: User) -> None:
        """Happy path: Add product to favorites."""
        api_client.force_authenticate(user=user)
        p1 = ProductFactory.create()
        url = reverse("favorites_items_api", kwargs={"product_id": p1.id})

        response = api_client.post(url)

        assert response.status_code == status.HTTP_200_OK
        assert FavoriteItem.objects.filter(user=user, product=p1).exists()

    def test_delete_favorite_success(self, api_client: APIClient, user: User) -> None:
        """Happy path: Remove product from favorites."""
        api_client.force_authenticate(user=user)
        p1 = ProductFactory.create()
        FavoriteItem.objects.create(user=user, product=p1)
        url = reverse("favorites_items_api", kwargs={"product_id": p1.id})

        response = api_client.delete(url)

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not FavoriteItem.objects.filter(user=user, product=p1).exists()


@pytest.mark.django_db
class TestReviewAPIViews:
    """
    Integration tests for Review endpoints.
    """

    def test_get_reviews_success(self, api_client: APIClient, user: User) -> None:
        """Happy path: Get reviews for a product."""
        api_client.force_authenticate(user=user)
        p1 = ProductFactory.create()
        Review.objects.create(user=user, product=p1, rating=5, text="Great!")
        url = reverse("reviews_get_api", kwargs={"product_id": p1.id})

        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert "results" in response.data
        assert len(response.data["results"]) == 1
        assert response.data["results"][0]["text"] == "Great!"

    def test_create_review_success(self, api_client: APIClient, user: User, mocker: MockerFixture) -> None:
        """
        Happy path: Create a new review.
        Mocks cross-domain `OrderRepository` to avoid building full Order structures.
        """
        api_client.force_authenticate(user=user)
        p1 = ProductFactory.create()
        mocker.patch(
            "apps.catalog.usecases.review_and_favorite.OrderRepository.check_user_purchased_product",
            return_value=True,
        )
        url = reverse("reviews_create_api")
        payload = {
            "product_id": p1.id,
            "rating": 4,
            "text": "Good product",
            "is_anonymous": False,
        }

        response = api_client.post(url, data=payload, format="multipart")

        assert response.status_code == status.HTTP_201_CREATED
        assert Review.objects.filter(user=user, product=p1).exists()

    def test_update_review_success(self, api_client: APIClient, user: User) -> None:
        """Happy path: Update an existing review."""
        api_client.force_authenticate(user=user)
        p1 = ProductFactory.create()
        review = Review.objects.create(user=user, product=p1, rating=3, text="Okay")
        url = reverse("reviews_detail_api", kwargs={"id": review.id})
        payload = {"rating": 5, "text": "Actually, it's perfect!"}

        response = api_client.put(url, data=payload, format="json")

        assert response.status_code == status.HTTP_200_OK
        review.refresh_from_db()
        assert review.rating == 5
        assert review.text == "Actually, it's perfect!"

    def test_delete_review_success(self, api_client: APIClient, user: User) -> None:
        """Happy path: Delete a review."""
        api_client.force_authenticate(user=user)
        p1 = ProductFactory.create()
        review = Review.objects.create(user=user, product=p1, rating=3, text="Okay")
        url = reverse("reviews_detail_api", kwargs={"id": review.id})

        response = api_client.delete(url)

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not Review.objects.filter(id=review.id).exists()
