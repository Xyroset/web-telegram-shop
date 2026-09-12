from typing import Any

from django.utils.functional import cached_property
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.support.repo import TicketRepository
from apps.support.serializers import CreateTicketRequestSerializer
from apps.support.usecases import CreateTicketCase


@extend_schema_view(
    post=extend_schema(
        summary="Create support ticket for admin",
        tags=["Support"],
        request=CreateTicketRequestSerializer,
        responses={status.HTTP_201_CREATED: None},
    )
)
class CreateSupportTicketView(APIView):
    """
    Handles customer support ticket creation.

    Permissions:
    - Requires an authenticated user (IsAuthenticated).

    Delegation:
    - **POST**: Validates input payload and delegates ticket creation and admin notification to `CreateTicketCase`.
    """

    permission_classes = [IsAuthenticated]

    @cached_property
    def _create_usecase(self) -> CreateTicketCase:
        ticket_repo = TicketRepository()
        return CreateTicketCase(ticket_repo=ticket_repo)

    def post(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        request_serializer = CreateTicketRequestSerializer(data=request.data)
        request_serializer.is_valid(raise_exception=True)
        valid_data = request_serializer.validated_data

        print(valid_data["category"])
        print(valid_data["message_text"])

        self._create_usecase.execute(
            user=request.user,
            category=valid_data["category"],
            message_text=valid_data["message_text"],
        )

        return Response(status=status.HTTP_201_CREATED)
