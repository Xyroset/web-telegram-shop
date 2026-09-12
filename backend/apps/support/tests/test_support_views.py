import pytest
from django.urls import reverse
from pytest_mock import MockerFixture
from rest_framework import status
from rest_framework.test import APIClient

from apps.support.factories import TicketFactory
from apps.support.models import Ticket
from apps.support.repo import TicketRepository
from apps.users.models import User


@pytest.mark.django_db
class TestCreateSupportTicketView:
    """
    Verify HTTP lifecycle of support ticket creation via /api/v1/support/.

    **Business Rules:**
    - Ticket creation requires an authenticated user.
    - User cannot exceed the configured active tickets limit.
    - Successful creation persists Ticket and initial TicketMessage records.
    - Admin notification task is scheduled via Celery upon transaction commit.
    """

    def test_create_ticket_success(
        self,
        api_client: APIClient,
        user: User,
        mocker: MockerFixture,
    ) -> None:
        """
        Happy path: Successfully create a new support ticket with an initial message.

        **Setup:**
        - Authenticated user without active tickets.
        - Celery task dispatch patched.

        **Expected:**
        - HTTP 201 Created.
        - Ticket and TicketMessage created in DB with OPEN state.
        - Celery notification dispatched with ticket ID.
        """
        api_client.force_authenticate(user=user)
        url = reverse("create_support_ticket_api")
        payload = {
            "category": Ticket.Category.BUG,
            "message_text": "I encountered an error during checkout.",
        }

        mock_send_task = mocker.patch("apps.support.usecases.lifecycle.current_app.send_task")
        mocker.patch("django.db.transaction.on_commit", side_effect=lambda hook: hook())

        response = api_client.post(url, data=payload, format="json")

        assert response.status_code == status.HTTP_201_CREATED

        repo = TicketRepository()
        assert repo.get_active_tickets_count(user=user) == 1

        created_ticket = repo.get_by_id_with_full_details(user=user)
        assert created_ticket.state == Ticket.Status.OPEN
        assert created_ticket.category == Ticket.Category.BUG
        assert created_ticket.messages.count() == 1

        first_message = created_ticket.first_message
        assert first_message is not None
        assert first_message.text == "I encountered an error during checkout."
        assert not first_message.sender_is_admin

        mock_send_task.assert_called_once_with(
            "notifications.dispatch_admin_support_ticket_notifications",
            args=[str(created_ticket.id)],
        )

    def test_create_ticket_failure_unauthorized(
        self,
        api_client: APIClient,
    ) -> None:
        """
        Failure: Unauthenticated user attempts to create a support ticket.
        """
        url = reverse("create_support_ticket_api")
        payload = {
            "category": Ticket.Category.GENERAL,
            "message_text": "Need some help.",
        }

        response = api_client.post(url, data=payload, format="json")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_create_ticket_failure_invalid_payload(
        self,
        api_client: APIClient,
        user: User,
        mocker: MockerFixture,
    ) -> None:
        """
        Failure: Request payload missing required fields or having invalid choices.
        """
        api_client.force_authenticate(user=user)
        url = reverse("create_support_ticket_api")
        payload = {
            "category": "non_existent_category",
            "message_text": "",
        }

        mock_send_task = mocker.patch("apps.support.usecases.lifecycle.current_app.send_task")

        response = api_client.post(url, data=payload, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST

        repo = TicketRepository()
        assert repo.get_active_tickets_count(user=user) == 0

        mock_send_task.assert_not_called()

    def test_create_ticket_failure_limit_exceeded(
        self,
        api_client: APIClient,
        user: User,
        mocker: MockerFixture,
    ) -> None:
        """
        Failure: User exceeds the active support tickets limit.

        **Expected:**
        - HTTP 400 Bad Request (handled domain exception).
        - No additional ticket created in the database.
        - Celery task not dispatched.
        """
        api_client.force_authenticate(user=user)

        mocker.patch("apps.support.usecases.lifecycle.shop_config.get").return_value = 1
        TicketFactory.create_batch(size=1, user=user, state=Ticket.Status.OPEN)

        url = reverse("create_support_ticket_api")
        payload = {
            "category": Ticket.Category.ORDER_ISSUE,
            "message_text": "Another issue text.",
        }

        mock_send_task = mocker.patch("apps.support.usecases.lifecycle.current_app.send_task")

        response = api_client.post(url, data=payload, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST

        repo = TicketRepository()
        assert repo.get_active_tickets_count(user=user) == 1

        mock_send_task.assert_not_called()
