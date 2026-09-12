import logging
from collections.abc import Sequence

from apps.catalog.domain.exceptions import (
    CatalogDigitalAssetOutOfStockError,
    CatalogStockInconsistencyError,
)
from apps.catalog.models import DigitalAsset, ProductVariant
from apps.catalog.repo import DigitalAssetRepository, ProductRepository
from apps.orders.models import OrderItem

logger = logging.getLogger(__name__)


class StockManagementService:
    """
    Domain service responsible for physical stock operations.
    """

    def __init__(self, product_repo: ProductRepository) -> None:
        self._product_repo = product_repo

    def reserve_physical(self, order_items: Sequence[OrderItem]) -> None:
        """Reserve stock for all physical items in the order."""
        self._process_stock_mutation(order_items=order_items, action="reserve")

    def release_physical(self, order_items: Sequence[OrderItem]) -> None:
        """Release reserved stock for all physical items in the order."""
        self._process_stock_mutation(order_items=order_items, action="release")

    def commit_all(self, order_items: Sequence[OrderItem]) -> None:
        """Commit stock deductions for both physical and digital items."""
        self._process_stock_mutation(order_items=order_items, action="commit", ignore_digital=False)

    def _process_stock_mutation(
        self, order_items: Sequence[OrderItem], action: str, ignore_digital: bool = True
    ) -> None:
        variant_ids = [item.variant_id for item in order_items if item.variant_id is not None]
        if not variant_ids:
            return

        locked_variants = {v.id: v for v in self._product_repo.get_variants_for_update(variant_ids=variant_ids)}
        update_variants: list[ProductVariant] = []

        for item in order_items:
            if item.variant_id is None:
                continue

            variant = locked_variants.get(item.variant_id)
            if variant is None:
                continue
            if ignore_digital and variant.is_digital:
                continue

            try:
                if action == "reserve":
                    variant.reserve_stock(quantity=item.quantity)
                elif action == "release":
                    variant.release_stock(quantity=item.quantity)
                elif action == "commit":
                    variant.commit_stock(quantity=item.quantity)

                update_variants.append(variant)
            except CatalogStockInconsistencyError as exc:
                logger.error(
                    f"Stock inconsistency for variant {variant.id} during {action}. "
                    f"Item quantity: {item.quantity}. Error: {exc}"
                )
                raise

        if update_variants:
            self._product_repo.bulk_update_stock(variants=update_variants)


class DigitalAssetManagementService:
    """
    Domain service responsible for allocating and releasing digital keys.
    Handles digital asset assignment and stock mutations for digital variants.
    """

    def __init__(self, digital_asset_repo: DigitalAssetRepository, product_repo: ProductRepository) -> None:
        self._digital_asset_repo = digital_asset_repo
        self._product_repo = product_repo

    def allocate_and_reserve(self, order_items: Sequence[OrderItem]) -> None:
        """Allocate available digital keys to order items and reserve variant stock."""
        variant_ids = [item.variant_id for item in order_items if item.variant_id is not None]
        if not variant_ids:
            return

        locked_variants = {v.id: v for v in self._product_repo.get_variants_for_update(variant_ids=variant_ids)}
        digital_assets_to_update: list[DigitalAsset] = []
        variants_to_update: list[ProductVariant] = []

        for item in order_items:
            if item.variant_id is None:
                continue

            variant = locked_variants.get(item.variant_id)
            if variant is None or not variant.is_digital:
                continue

            available_assets = list(
                self._digital_asset_repo.filter_for_update_by(order_item=None, variant_id=variant.id)
            )

            if item.quantity > len(available_assets):
                raise CatalogDigitalAssetOutOfStockError(
                    f"Out of stock! Order item needs {item.quantity}, but only {len(available_assets)} available."
                )

            assets_to_allocate = available_assets[: item.quantity]
            for digital_asset in assets_to_allocate:
                digital_asset.allocate_to_order(order_item_id=str(item.id))
                digital_assets_to_update.append(digital_asset)

            try:
                variant.reserve_stock(quantity=item.quantity)
                variants_to_update.append(variant)
            except CatalogStockInconsistencyError as exc:
                logger.error(f"Failed to reserve digital stock for variant {variant.id}. Error: {exc}")
                raise

        if digital_assets_to_update:
            self._digital_asset_repo.bulk_update(
                objects=digital_assets_to_update, update_fields=["is_used", "order_item_id"]
            )
        if variants_to_update:
            self._product_repo.bulk_update_stock(variants=variants_to_update)

    def release_assets_and_stock(self, order_items: Sequence[OrderItem]) -> None:
        """Release allocated digital keys back to pool and restore variant stock."""
        variant_ids = [item.variant_id for item in order_items if item.variant_id is not None]
        if not variant_ids:
            return

        locked_variants = {v.id: v for v in self._product_repo.get_variants_for_update(variant_ids=variant_ids)}
        digital_assets_to_update: list[DigitalAsset] = []
        variants_to_update: list[ProductVariant] = []

        for item in order_items:
            if item.variant_id is None:
                continue

            variant = locked_variants.get(item.variant_id)
            if variant is None or not variant.is_digital:
                continue

            used_assets = list(self._digital_asset_repo.filter_for_update_by(order_item_id=item.id))
            for digital_asset in used_assets:
                digital_asset.release_asset()
                digital_assets_to_update.append(digital_asset)

            try:
                variant.release_stock(quantity=item.quantity)
                variants_to_update.append(variant)
            except CatalogStockInconsistencyError as exc:
                logger.error(f"Failed to release digital stock for variant {variant.id}. Error: {exc}")
                raise

        if digital_assets_to_update:
            self._digital_asset_repo.bulk_update(
                objects=digital_assets_to_update, update_fields=["is_used", "order_item_id"]
            )
        if variants_to_update:
            self._product_repo.bulk_update_stock(variants=variants_to_update)
