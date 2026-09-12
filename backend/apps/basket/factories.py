import factory

from apps.basket.models import Basket, BasketItem
from apps.catalog.factories import ProductVariantFactory
from apps.users.factories import UserFactory


class BasketFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Basket

    user = factory.SubFactory(UserFactory)


class BasketItemFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = BasketItem

    basket = factory.SubFactory(BasketFactory)
    variant = factory.SubFactory(ProductVariantFactory)
    quantity = 1
