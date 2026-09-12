from django.urls import path

from apps.support.views import CreateSupportTicketView

urlpatterns = [
    path("", CreateSupportTicketView.as_view(), name="create_support_ticket_api"),
]
