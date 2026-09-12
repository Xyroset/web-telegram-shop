import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.basket.factories import BasketFactory, BasketItemFactory
from apps.basket.repo import BasketRepository
from apps.catalog.factories import ProductVariantFactory
from apps.orders.models import PromoCode
from apps.users.models import User


@pytest.mark.django_db
class TestBasketAPIView:
    """
    Verify HTTP lifecycle of basket item retrieval and creation via GET and POST /api/v1/basket/.
    """

    def test_get_basket_success(self, api_client: APIClient, user: User) -> None:
        """
        Happy path: Retrieve user's basket.
        """
        api_client.force_authenticate(user=user)
        basket = BasketFactory.create(user=user)
        BasketItemFactory.create_batch(2, basket=basket)
        url = reverse("basket_api")

        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert isinstance(response.data, list)
        assert len(response.data) == 2

    def test_create_basket_item_success(self, api_client: APIClient, user: User) -> None:
        """
        Happy path: Create or update basket item.
        """
        api_client.force_authenticate(user=user)
        variant = ProductVariantFactory.create()
        url = reverse("basket_api")
        payload = {"variant_id": variant.id, "quantity": 2}

        response = api_client.post(url, data=payload, format="json")

        assert response.status_code == status.HTTP_200_OK

        repo = BasketRepository()
        basket_qs = repo.get_basket_queryset(user=user)
        assert basket_qs.count() == 1
        assert basket_qs.first().quantity == 2  # type: ignore[union-attr]

    def test_unauthorized_access(self, api_client: APIClient) -> None:
        """
        Failure: Unauthenticated user attempts to access basket.
        """
        url = reverse("basket_api")

        get_response = api_client.get(url)
        post_response = api_client.post(url, data={"variant_id": 1, "quantity": 1}, format="json")

        assert get_response.status_code == status.HTTP_401_UNAUTHORIZED
        assert post_response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestBasketDetailAPIView:
    """
    Verify HTTP lifecycle of deleting a basket item via DELETE /api/v1/basket/{variant_id}/.
    """

    def test_delete_basket_item_success(self, api_client: APIClient, user: User) -> None:
        """
        Happy path: Delete an existing item from the basket.
        """
        api_client.force_authenticate(user=user)
        variant = ProductVariantFactory.create()
        BasketItemFactory.create(basket__user=user, variant=variant)
        url = reverse("basket_detail_api", kwargs={"variant_id": variant.id})

        response = api_client.delete(url)

        assert response.status_code == status.HTTP_204_NO_CONTENT

        repo = BasketRepository()
        basket_qs = repo.get_basket_queryset(user=user)
        assert basket_qs.count() == 0

    def test_delete_basket_item_failure_not_found(self, api_client: APIClient, user: User) -> None:
        """
        Failure: Attempt to delete a non-existent item.
        """
        api_client.force_authenticate(user=user)
        url = reverse("basket_detail_api", kwargs={"variant_id": 9999})

        response = api_client.delete(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
class TestBasketCalculatePriceView:
    """
    Verify HTTP lifecycle of calculating basket price via GET /api/v1/basket/calculate/.
    """

    def test_calculate_price_empty_basket(self, api_client: APIClient, user: User) -> None:
        """
        Happy path: Calculate price for an empty basket.
        """
        api_client.force_authenticate(user=user)
        url = reverse("basket_calculate_api")

        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["total_price"] == "0.00"
        assert response.data["valid_promocode"] is False

    def test_calculate_price_with_items_no_promo(self, api_client: APIClient, user: User) -> None:
        """
        Happy path: Calculate price for filled basket without promocode.
        """
        api_client.force_authenticate(user=user)
        variant = ProductVariantFactory.create(price="50.00")
        BasketItemFactory.create(basket__user=user, variant=variant, quantity=2)
        url = reverse("basket_calculate_api")

        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["total_price"] == "100.00"
        assert response.data["valid_promocode"] is False

    def test_calculate_price_with_valid_promo(self, api_client: APIClient, user: User) -> None:
        """
        Happy path: Calculate price for filled basket with a valid promocode.
        """
        api_client.force_authenticate(user=user)
        variant = ProductVariantFactory.create(price="100.00")
        BasketItemFactory.create(basket__user=user, variant=variant, quantity=1)
        promo = PromoCode.objects.create(
            code="SUMMER20",
            discount_type=PromoCode.Type.AMOUNT,
            discount_amount="20.00",
            min_order_amount="50.00",
            work_for_everything=True,
        )
        url = f"/api/v1/basket/calculate/?promocode={promo.code}"

        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["base_price"] == "100.00"
        assert response.data["total_price"] == "80.00"
        assert response.data["discount_value"] == "20.00"
        assert response.data["valid_promocode"] is True
