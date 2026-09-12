import uuid
from decimal import Decimal

import factory

from apps.orders.factories import OrderFactory
from apps.payments.models import PaymentTransaction


class PaymentTransactionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = PaymentTransaction

    id = factory.LazyFunction(uuid.uuid4)
    order = factory.SubFactory(OrderFactory)
    payment_currency = "USDT"
    network = "TRC20"
    amount_crypto = Decimal("150.00000000")
    current_amount_crypto = Decimal("0.00000000")
    target_amount_usd = Decimal("150.00")
    state = PaymentTransaction.Status.PENDING
