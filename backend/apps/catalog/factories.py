import uuid
from decimal import Decimal

import factory

from apps.catalog.models import (
    Category,
    DigitalAsset,
    FavoriteItem,
    Photo,
    Product,
    ProductVariant,
    Review,
    ReviewPhoto,
    Tag,
)
from apps.users.factories import UserFactory


class CategoryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Category

    name = factory.Sequence(lambda n: f"Category {n}")
    slug = factory.Sequence(lambda n: f"category-{n}")


class TagFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Tag

    name = factory.Sequence(lambda n: f"Tag {n}")
    slug = factory.Sequence(lambda n: f"tag-{n}")


class ProductFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Product

    name = factory.Sequence(lambda n: f"Product {n}")
    category = factory.SubFactory(CategoryFactory)
    product_type = Product.Type.PHYSICAL
    base_description = factory.Faker("text")


class ProductVariantFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ProductVariant

    product = factory.SubFactory(ProductFactory)
    title = factory.Sequence(lambda n: f"Variant {n}")
    price = Decimal("100.00")
    available_stock = 50
    reserved_stock = 0
    weight_kg = Decimal("1.00")
    length_cm = Decimal("10.00")
    width_cm = Decimal("10.00")
    height_cm = Decimal("10.00")


class DigitalAssetFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = DigitalAsset

    id = factory.LazyFunction(uuid.uuid4)
    variant = factory.SubFactory(
        ProductVariantFactory,
        product__product_type=Product.Type.DIGITAL,
    )
    content = factory.Sequence(lambda n: f"SECRET-KEY-{n}")
    is_used = False


class PhotoFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Photo

    product = factory.SubFactory(ProductFactory)
    image = factory.django.ImageField(filename="test_photo.jpg")
    ordering = factory.Sequence(lambda n: n)


class ReviewFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Review

    id = factory.LazyFunction(uuid.uuid4)
    user = factory.SubFactory(UserFactory)
    product = factory.SubFactory(ProductFactory)
    rating = 5
    text = "Great product!"
    is_anonymous = False


class ReviewPhotoFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ReviewPhoto

    review = factory.SubFactory(ReviewFactory)
    image = factory.django.ImageField(filename="review_photo.jpg")


class FavoriteItemFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = FavoriteItem

    user = factory.SubFactory(UserFactory)
    product = factory.SubFactory(ProductFactory)
