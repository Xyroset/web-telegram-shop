from pathlib import Path

import pytest
from django.conf import settings
from rest_framework.test import APIClient

from apps.basket.factories import BasketItemFactory
from apps.basket.models import BasketItem
from apps.catalog.factories import ProductFactory, ProductVariantFactory
from apps.catalog.models import Product, ProductVariant
from apps.core.config_manager import shop_config
from apps.users.factories import UserFactory
from apps.users.models import User


@pytest.fixture
def api_client() -> APIClient:
    """Provides a DRF APIClient instance for integration tests."""
    return APIClient()


@pytest.fixture
def user(db: None) -> User:
    """Generates a fake user for tests"""
    return UserFactory.create()  # type: ignore [no-any-return]


@pytest.fixture
def product(db: None) -> Product:
    """Generates a fake product for tests"""
    return ProductFactory.create()  # type: ignore [no-any-return]


@pytest.fixture
def product_variant(db: None) -> ProductVariant:
    """Generates a fake product variant for tests"""
    return ProductVariantFactory.create()  # type: ignore [no-any-return]


@pytest.fixture
def user_with_filled_basket(user: User, product_variant: ProductVariant) -> BasketItem:
    """Creates a basket item explicitly linked to the `user` and `product_variant` fixtures."""
    basket_item = BasketItemFactory.create(basket__user=user, variant=product_variant, quantity=2)

    return basket_item  # type: ignore [no-any-return]


@pytest.fixture(autouse=True, scope="session")
def setup_test_config() -> None:
    base_dir = Path(settings.BASE_DIR)

    settings.SHOP_CONFIG_DIR = str(base_dir.parent / "config")

    shop_config.reload()
