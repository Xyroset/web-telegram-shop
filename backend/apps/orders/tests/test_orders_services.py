from unittest.mock import MagicMock

import pytest

from apps.catalog.domain.exceptions import (
    CatalogDigitalAssetOutOfStockError,
    CatalogStockInconsistencyError,
)
from apps.catalog.models import DigitalAsset, ProductVariant
from apps.catalog.repo import DigitalAssetRepository, ProductRepository
from apps.orders.domain.services import (
    DigitalAssetManagementService,
    StockManagementService,
)
from apps.orders.models import OrderItem


class TestStockManagementService:
    """
    Tests for pure domain logic of physical and general stock management.
    """

    def test_reserve_physical_happy_path(self) -> None:
        mock_product_repo: ProductRepository | MagicMock = MagicMock()
        service = StockManagementService(product_repo=mock_product_repo)

        mock_variant = MagicMock(spec=ProductVariant)
        mock_variant.id = 1
        mock_variant.is_digital = False

        mock_item = MagicMock(spec=OrderItem)
        mock_item.variant_id = 1
        mock_item.quantity = 2

        mock_product_repo.get_variants_for_update.return_value = [mock_variant]  # type: ignore[union-attr]

        service.reserve_physical(order_items=[mock_item])

        mock_product_repo.get_variants_for_update.assert_called_once_with(variant_ids=[1])  # type: ignore[union-attr]
        mock_variant.reserve_stock.assert_called_once_with(quantity=2)
        mock_product_repo.bulk_update_stock.assert_called_once_with(variants=[mock_variant])  # type: ignore[union-attr]

    def test_reserve_physical_ignores_digital_variants(self) -> None:
        mock_product_repo: ProductRepository | MagicMock = MagicMock()
        service = StockManagementService(product_repo=mock_product_repo)

        mock_variant = MagicMock(spec=ProductVariant)
        mock_variant.id = 1
        mock_variant.is_digital = True

        mock_item = MagicMock(spec=OrderItem)
        mock_item.variant_id = 1
        mock_item.quantity = 1

        mock_product_repo.get_variants_for_update.return_value = [mock_variant]  # type: ignore[union-attr]

        service.reserve_physical(order_items=[mock_item])

        mock_variant.reserve_stock.assert_not_called()
        mock_product_repo.bulk_update_stock.assert_not_called()  # type: ignore[union-attr]

    def test_reserve_physical_raises_inconsistency_error_and_aborts(self) -> None:
        mock_product_repo: ProductRepository | MagicMock = MagicMock()
        service = StockManagementService(product_repo=mock_product_repo)

        mock_variant = MagicMock(spec=ProductVariant)
        mock_variant.id = 1
        mock_variant.is_digital = False
        mock_variant.reserve_stock.side_effect = CatalogStockInconsistencyError("Not enough stock")

        mock_item = MagicMock(spec=OrderItem)
        mock_item.variant_id = 1
        mock_item.quantity = 100

        mock_product_repo.get_variants_for_update.return_value = [mock_variant]  # type: ignore[union-attr]

        with pytest.raises(CatalogStockInconsistencyError):
            service.reserve_physical(order_items=[mock_item])


class TestDigitalAssetManagementService:
    """
    Tests for pure domain logic of allocating and releasing digital assets.
    """

    def test_allocate_and_reserve_happy_path(self) -> None:
        mock_product_repo: ProductRepository | MagicMock = MagicMock()
        mock_digital_asset_repo: DigitalAssetRepository | MagicMock = MagicMock()
        service = DigitalAssetManagementService(
            digital_asset_repo=mock_digital_asset_repo, product_repo=mock_product_repo
        )

        mock_variant = MagicMock(spec=ProductVariant)
        mock_variant.id = 1
        mock_variant.is_digital = True

        mock_item = MagicMock(spec=OrderItem)
        mock_item.id = "item-uuid-123"
        mock_item.variant_id = 1
        mock_item.quantity = 1

        mock_asset = MagicMock(spec=DigitalAsset)

        mock_product_repo.get_variants_for_update.return_value = [mock_variant]  # type: ignore[union-attr]
        mock_digital_asset_repo.filter_for_update_by.return_value = [mock_asset]  # type: ignore[union-attr]

        service.allocate_and_reserve(order_items=[mock_item])

        mock_asset.allocate_to_order.assert_called_once_with(order_item_id="item-uuid-123")
        mock_variant.reserve_stock.assert_called_once_with(quantity=1)
        mock_digital_asset_repo.bulk_update.assert_called_once_with(  # type: ignore[union-attr]
            objects=[mock_asset], update_fields=["is_used", "order_item_id"]
        )
        mock_product_repo.bulk_update_stock.assert_called_once_with(variants=[mock_variant])  # type: ignore[union-attr]

    def test_allocate_and_reserve_raises_out_of_stock(self) -> None:
        mock_product_repo: ProductRepository | MagicMock = MagicMock()
        mock_digital_asset_repo: DigitalAssetRepository | MagicMock = MagicMock()
        service = DigitalAssetManagementService(
            digital_asset_repo=mock_digital_asset_repo, product_repo=mock_product_repo
        )

        mock_variant = MagicMock(spec=ProductVariant)
        mock_variant.id = 1
        mock_variant.is_digital = True

        mock_item = MagicMock(spec=OrderItem)
        mock_item.id = "item-uuid-123"
        mock_item.variant_id = 1
        mock_item.quantity = 2

        mock_asset = MagicMock(spec=DigitalAsset)

        mock_product_repo.get_variants_for_update.return_value = [mock_variant]  # type: ignore[union-attr]
        mock_digital_asset_repo.filter_for_update_by.return_value = [mock_asset]  # type: ignore[union-attr]

        with pytest.raises(CatalogDigitalAssetOutOfStockError):
            service.allocate_and_reserve(order_items=[mock_item])

    def test_release_assets_and_stock_happy_path(self) -> None:
        mock_product_repo: ProductRepository | MagicMock = MagicMock()
        mock_digital_asset_repo: DigitalAssetRepository | MagicMock = MagicMock()
        service = DigitalAssetManagementService(
            digital_asset_repo=mock_digital_asset_repo, product_repo=mock_product_repo
        )

        mock_variant = MagicMock(spec=ProductVariant)
        mock_variant.id = 1
        mock_variant.is_digital = True

        mock_item = MagicMock(spec=OrderItem)
        mock_item.id = "item-uuid-123"
        mock_item.variant_id = 1
        mock_item.quantity = 1

        mock_asset = MagicMock(spec=DigitalAsset)

        mock_product_repo.get_variants_for_update.return_value = [mock_variant]  # type: ignore[union-attr]
        mock_digital_asset_repo.filter_for_update_by.return_value = [mock_asset]  # type: ignore[union-attr]

        service.release_assets_and_stock(order_items=[mock_item])

        mock_asset.release_asset.assert_called_once()
        mock_variant.release_stock.assert_called_once_with(quantity=1)
        mock_digital_asset_repo.bulk_update.assert_called_once_with(  # type: ignore[union-attr]
            objects=[mock_asset], update_fields=["is_used", "order_item_id"]
        )
        mock_product_repo.bulk_update_stock.assert_called_once_with(variants=[mock_variant])  # type: ignore[union-attr]
