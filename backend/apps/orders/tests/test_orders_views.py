import uuid
from decimal import Decimal

import pytest
from django.urls import reverse
from pytest_mock import MockerFixture
from rest_framework import status
from rest_framework.test import APIClient

from apps.catalog.factories import ProductVariantFactory
from apps.core.config_manager import shop_config
from apps.delivery.factories import DeliveryFactory
from apps.orders.factories import OrderFactory, OrderItemFactory
from apps.orders.models import Order
from apps.orders.repo import OrderRepository
from apps.users.models import User


@pytest.mark.django_db
class TestOrderAPIView:
    """
    Verify HTTP lifecycle of order creation and listing via /api/v1/orders/.

    **Business Rules:**
    - Order creation requires an authenticated user with a non-empty basket.
    - User must not exceed the maximum allowed pending orders.
    - Product stock must be available for all basket items.
    - Order expiration task is scheduled via Celery after successful creation.
    """

    @pytest.mark.usefixtures("user_with_filled_basket")
    def test_create_order_success(
        self,
        api_client: APIClient,
        user: User,
        mocker: MockerFixture,
    ) -> None:
        """
        Happy path: Create order from an existing basket.

        **Setup:**
        - Authenticated user with a filled basket.
        - Celery task scheduled via ts.on_commit is mocked.

        **Expected:**
        - HTTP 201 Created with order_id in the response.
        - Order created in PENDING status in the database.
        - Celery task dispatched.
        """
        api_client.force_authenticate(user=user)
        url = reverse("order_api")
        payload = {
            "delivery_data": {
                "full_name": "-",
                "email": "example@gmail.com",
                "phone": "+35352342",
                "zip_code": "-",
                "address_line": "-",
                "destination_code": "us",
                "region_code": "al",
            },
        }

        mock_send_task = mocker.patch("apps.orders.usecases.creation.current_app.send_task")
        mocker.patch("django.db.transaction.on_commit", side_effect=lambda hook: hook())

        response = api_client.post(url, data=payload, format="json")
        print(response)

        assert response.status_code == status.HTTP_201_CREATED
        assert "order_id" in response.data

        repo = OrderRepository()
        user_orders = repo.get_orders_queryset(user=user)

        assert user_orders.count() == 1
        assert user_orders.first().state == Order.Status.PENDING  # type: ignore[union-attr]

        mock_send_task.assert_called_once()

    def test_create_order_failure_unauthorized(
        self,
        api_client: APIClient,
    ) -> None:
        """
        Failure: Unauthenticated user attempts to create an order.
        """
        url = reverse("order_api")
        payload = {
            "delivery_data": {
                "full_name": "-",
                "email": "example@gmail.com",
                "phone": "+35352342",
                "zip_code": "-",
                "address_line": "-",
                "destination_code": "us",
                "region_code": "al",
            },
        }

        response = api_client.post(url, data=payload, format="json")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_create_order_failure_empty_basket(
        self,
        api_client: APIClient,
        user: User,
        mocker: MockerFixture,
    ) -> None:
        """
        Failure: Authenticated user with an empty basket attempts to create an order.

        **Expected:**
        - HTTP 404 Not Found (via custom domain exception handler mapping).
        - No order created in the database.
        """
        api_client.force_authenticate(user=user)
        url = reverse("order_api")
        payload = {
            "delivery_data": {
                "full_name": "-",
                "email": "example@gmail.com",
                "phone": "+35352342",
                "zip_code": "-",
                "address_line": "-",
                "destination_code": "us",
                "region_code": "al",
            },
        }

        mock_celery = mocker.patch("apps.orders.usecases.creation.current_app.send_task")

        response = api_client.post(url, data=payload, format="json")
        print(response)

        assert response.status_code == status.HTTP_404_NOT_FOUND

        repo = OrderRepository()
        assert repo.get_orders_queryset(user=user).count() == 0

        mock_celery.assert_not_called()

    @pytest.mark.usefixtures("user_with_filled_basket")
    def test_create_order_failure_pending_limit_exceeded(
        self,
        api_client: APIClient,
        user: User,
        mocker: MockerFixture,
    ) -> None:
        """
        Failure: User exceeds the maximum allowed pending orders.

        **Expected:**
        - HTTP 429 Too Many Requests.
        - No new order created.
        """
        api_client.force_authenticate(user=user)
        limit = shop_config.get("order", "order_settings.order_pending_limit", 3)

        OrderFactory.create_batch(limit, user=user, state=Order.Status.PENDING)

        url = reverse("order_api")
        payload = {
            "delivery_data": {
                "full_name": "-",
                "email": "example@gmail.com",
                "phone": "+35352342",
                "zip_code": "-",
                "address_line": "-",
                "destination_code": "us",
                "region_code": "al",
            },
        }

        mock_celery = mocker.patch("apps.orders.usecases.creation.current_app.send_task")

        response = api_client.post(url, data=payload, format="json")
        print(response)

        assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS

        repo = OrderRepository()
        assert repo.get_orders_queryset(user=user).count() == limit

        mock_celery.assert_not_called()

    def test_get_orders_success(self, api_client: APIClient, user: User) -> None:
        """
        Happy path: Retrieve user's orders list.
        """
        api_client.force_authenticate(user=user)
        OrderFactory.create_batch(2, user=user)

        url = reverse("order_api")

        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert "results" in response.data
        assert len(response.data["results"]) == 2

    def test_get_orders_failure_unauthorized(self, api_client: APIClient) -> None:
        """
        Failure: Unauthenticated user attempts to list orders.
        """
        url = reverse("order_api")

        response = api_client.get(url)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestOrderDetailAPIView:
    """
    Verify HTTP lifecycle for order retrieval and cancellation via /api/v1/orders/{id}/.

    **Business Rules:**
    - Only authenticated users can retrieve or cancel their own orders.
    - Cancellation triggers the CancelOrderCase to mutate state and revoke Celery tasks.
    """

    def test_get_order_success(self, api_client: APIClient, user: User) -> None:
        """
        Happy path: Retrieve user's own pending order.
        """
        api_client.force_authenticate(user=user)
        order = OrderFactory.create(user=user, state=Order.Status.PENDING)

        url = reverse("order_detail", kwargs={"order_id": order.id})

        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["id"] == str(order.id)
        assert response.data["state"] == Order.Status.PENDING

    @pytest.mark.parametrize(
        "is_authorized, status_code", [(False, status.HTTP_401_UNAUTHORIZED), (True, status.HTTP_404_NOT_FOUND)]
    )
    def test_get_order_failure(self, api_client: APIClient, user: User, is_authorized: bool, status_code: int) -> None:
        """
        Failure: Retrieve non-existent order or unauthenticated access.
        """
        if is_authorized:
            api_client.force_authenticate(user=user)

        fake_order_id = uuid.uuid4()
        url = reverse("order_detail", kwargs={"order_id": fake_order_id})

        response = api_client.get(url)

        assert response.status_code == status_code

    def test_cancel_order_success(self, api_client: APIClient, user: User, mocker: MockerFixture) -> None:
        """
        Happy path: Cancel user's pending order using HTTP PUT.
        """
        api_client.force_authenticate(user=user)
        order = OrderFactory.create(user=user, state=Order.Status.PENDING, task_id=uuid.uuid4())
        DeliveryFactory.create(order=order)
        variant = ProductVariantFactory.create(available_stock=5, reserved_stock=1, price=Decimal("10.0"))
        OrderItemFactory.create(order=order, variant=variant, is_digital=False, fixed_price=Decimal("10.0"), quantity=1)

        url = reverse("order_detail", kwargs={"order_id": order.id})

        mock_revoke = mocker.patch("apps.orders.usecases.cancellation.current_app.control.revoke")
        mocker.patch("django.db.transaction.on_commit", side_effect=lambda hook: hook())

        response = api_client.put(url)

        assert response.status_code == status.HTTP_200_OK

        repo = OrderRepository()
        updated_order = repo.get_order_with_full_details(order_id=order.id, user=user)
        assert updated_order.state == Order.Status.CANCELLED

        mock_revoke.assert_called_once_with(str(order.task_id), terminate=True)

    @pytest.mark.parametrize(
        "is_authorized, status_code, initial_state",
        [
            (False, status.HTTP_401_UNAUTHORIZED, Order.Status.PENDING),
            (True, status.HTTP_404_NOT_FOUND, Order.Status.PENDING),
        ],
    )
    def test_cancel_order_failure(
        self,
        api_client: APIClient,
        user: User,
        mocker: MockerFixture,
        is_authorized: bool,
        status_code: int,
        initial_state: str,
    ) -> None:
        """
        Failure: Cancel order with unauthenticated access or missing object.
        """
        if is_authorized:
            api_client.force_authenticate(user=user)

        if status_code == status.HTTP_404_NOT_FOUND:
            order_id = uuid.uuid4()
        else:
            order = OrderFactory.create(user=user, state=initial_state)
            order_id = order.id

        url = reverse("order_detail", kwargs={"order_id": order_id})

        mock_celery = mocker.patch("apps.orders.usecases.cancellation.current_app.control.revoke")

        response = api_client.put(url)

        assert response.status_code == status_code

        mock_celery.assert_not_called()
