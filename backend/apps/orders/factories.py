import uuid
from decimal import Decimal

import factory

from apps.catalog.factories import ProductVariantFactory
from apps.orders.models import Order, OrderItem
from apps.users.factories import UserFactory


class OrderFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Order

    id = factory.LazyFunction(uuid.uuid4)
    user = factory.SubFactory(UserFactory)
    amount_usd = Decimal("150.00")
    task_id = factory.LazyFunction(uuid.uuid4)


class OrderItemFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = OrderItem

    id = factory.LazyFunction(uuid.uuid4)
    order = factory.SubFactory(OrderFactory)
    variant = factory.SubFactory(ProductVariantFactory)
    quantity = 1
    is_digital = False
