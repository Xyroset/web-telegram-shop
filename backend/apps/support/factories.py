import factory

from apps.support.models import Ticket
from apps.users.factories import UserFactory


class TicketFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Ticket

    user = factory.SubFactory(UserFactory)
    state = Ticket.Status.OPEN
    category = Ticket.Category.GENERAL
