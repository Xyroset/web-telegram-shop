import uuid

import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.delivery.factories import DeliveryFactory
from apps.orders.factories import OrderFactory
from apps.users.models import User


@pytest.mark.django_db
class TestDeliveryEstimateView:
    """
    Verify HTTP lifecycle of delivery estimation retrieval via GET delivery_estimate_api.
    """

    def test_get_delivery_estimate_success(self, api_client: APIClient, user: User) -> None:
        """
        Happy path: Retrieve delivery estimate successfully.

        **Setup:**
        - Authenticated user.
        - Valid destination code provided as a query parameter.
        - Internal UseCases and Repositories are executed natively (no mocking).

        **Expected:**
        - HTTP 200 OK.
        - Response contains serialized delivery estimate data as a dictionary.
        """
        api_client.force_authenticate(user=user)
        url = reverse("delivery_estimate_api")

        response = api_client.get(url, {"destination_code": "eu"})
        print(response)

        assert response.status_code == status.HTTP_200_OK
        assert isinstance(response.data, dict)
        assert "cost" in response.data
        assert "is_free" in response.data

    def test_unauthorized_access(self, api_client: APIClient) -> None:
        """
        Failure: Unauthenticated user attempts to get an estimate.

        **Expected:**
        - HTTP 401 Unauthorized.
        """
        url = reverse("delivery_estimate_api")

        response = api_client.get(url)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestGetDeliveryView:
    """
    Verify HTTP lifecycle of retrieving delivery details via GET delivery_get_api.
    """

    def test_get_delivery_success(self, api_client: APIClient, user: User) -> None:
        """
        Happy path: Retrieve delivery data for a user's own order.
        """
        order = OrderFactory(user=user)
        delivery = DeliveryFactory(order=order)
        api_client.force_authenticate(user=user)
        url = reverse("delivery_get_api", kwargs={"order_id": order.id})

        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["id"] == delivery.id

    def test_get_delivery_not_found_for_other_user_order(self, api_client: APIClient, user: User) -> None:
        """
        Failure: Cannot retrieve delivery data for another user's order.
        Repository filters by order__user=request.user, so it should return 404.
        """
        other_order = OrderFactory()
        DeliveryFactory(order=other_order)
        api_client.force_authenticate(user=user)
        url = reverse("delivery_get_api", kwargs={"order_id": other_order.id})

        response = api_client.get(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_unauthorized_access(self, api_client: APIClient) -> None:
        """
        Failure: Unauthenticated user attempts to get delivery details.
        """
        url = reverse("delivery_get_api", kwargs={"order_id": uuid.uuid4()})

        response = api_client.get(url)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
