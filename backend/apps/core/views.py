from django.utils.functional import cached_property
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.serializers import GetWebAppInitConfigResponseSerializer
from apps.core.usecases import GetWebAppInitConfigCase
from apps.users.repo import UserSettingsDataRepository


@extend_schema_view(
    get=extend_schema(
        summary="Get init data for WebApp",
        tags=["Config"],
        request=None,
        responses={200: GetWebAppInitConfigResponseSerializer},
    )
)
class GetWebAppInitConfigView(APIView):
    """
    Provides initial configuration payload for the WebApp.

    Permissions:
    - Requires an authenticated user.

    Delegation:
    - **GET**: Delegates config generation to `GetWebAppInitConfigCase`.
    """

    permission_classes = [IsAuthenticated]

    @cached_property
    def _init_usecase(self) -> GetWebAppInitConfigCase:
        return GetWebAppInitConfigCase(settings_repo=UserSettingsDataRepository())

    @extend_schema(
        summary="Get init data for WebApp",
        tags=["Config"],
        request=None,
        responses={200: GetWebAppInitConfigResponseSerializer},
    )
    def get(self, request, *args, **kwargs) -> Response:
        config_data = self._init_usecase.execute(user=request.user)
        response_serializer = GetWebAppInitConfigResponseSerializer(config_data)

        return Response(response_serializer.data, status=status.HTTP_200_OK)
