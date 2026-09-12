from decimal import Decimal

import factory

from apps.delivery.models import Delivery
from apps.orders.factories import OrderFactory


class DeliveryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Delivery

    id = 123
    order = factory.SubFactory(OrderFactory)
    state = Delivery.Status.PROCESSING
    provider_code = "AUTO"
    cost = Decimal("15.0")
    delivery_data = {
        "address_line": "789 Webhook St",
        "destination_code": "EU",
        "email": "wh@example.com",
        "phone": "+123456789",
    }
