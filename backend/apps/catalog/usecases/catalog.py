import logging
from collections.abc import Mapping, Sequence
from typing import Any

from django.db import transaction as ts

from apps.catalog.models import DigitalAsset, ProductVariant
from apps.catalog.repo import DigitalAssetRepository, ProductRepository

logger = logging.getLogger(__name__)


class BulkCreateDigitalAssetsCase:
    """
    Process and securely save a batch of digital keys for a specific variant.

    **Business Rules:**
    - Clean raw keys by stripping leading and trailing whitespace.
    - Ignore empty or blank strings.
    - Delegate bulk creation to the DigitalAssetRepository.
    - Synchronize the variant's available_stock with the new keys.
    - Execute strictly within an atomic database transaction.

    **Required:**
    - Variant object must be provided.
    """

    def __init__(self, digital_asset_repo: DigitalAssetRepository, product_repo: ProductRepository) -> None:
        self._digital_asset_repo = digital_asset_repo
        self._product_repo = product_repo

    def execute(self, variant: ProductVariant, raw_keys: Sequence[str]) -> int:
        with ts.atomic():
            valid_keys = [k.strip() for k in raw_keys if k.strip()]

            if not valid_keys:
                return 0

            keys_list = [DigitalAsset(variant=variant, content=key) for key in valid_keys]
            self._digital_asset_repo.bulk_create(objects=keys_list)

            added_count = len(valid_keys)
            update_fields = variant.add_available_stock(added_count=added_count)
            self._product_repo.save_variant(variant=variant, update_fields=update_fields)

            logger.info(f"Bulk created {added_count} digital assets for variant {variant.id}.")
            return added_count


class BulkDeleteDigitalAssetsCase:
    """
    Process and securely delete unused digital assets.

    **Business Rules:**
    - Delete only digital assets that are NOT used (is_used=False).
    - Delegate deletion to the DigitalAssetRepository.
    - Synchronize the variant's available_stock.
    - Execute strictly within an atomic database transaction.

    **Required:**
    - Variant object and asset IDs must be provided.
    """

    def __init__(self, digital_asset_repo: DigitalAssetRepository, product_repo: ProductRepository) -> None:
        self._digital_asset_repo = digital_asset_repo
        self._product_repo = product_repo

    def execute(self, variant: ProductVariant, asset_ids: Sequence[str]) -> int:
        with ts.atomic():
            if not asset_ids:
                return 0

            assets_to_delete = self._digital_asset_repo.filter_for_update_by(
                variant_id=variant.id, is_used=False, id__in=asset_ids
            )

            subtract_count, _ = self._digital_asset_repo.delete(objects=assets_to_delete)

            if subtract_count == 0:
                return 0

            update_fields = variant.subtract_available_stock(subtract_count=subtract_count)
            self._product_repo.save_variant(variant=variant, update_fields=update_fields)

            logger.info(f"Deleted {subtract_count} unused digital assets for variant {variant.id}.")
            return subtract_count


class SyncDigitalVariantsStockCase:
    """
    Synchronizes the available_stock of all digital product variants
    with the actual count of their unused digital assets.

    **Business Rules:**
    - Fetch all variants that belong to DIGITAL products.
    - Calculate the exact count of unused digital assets (is_used=False).
    - Hard-reset the available_stock of the variant to this exact count.
    - Execute strictly within an atomic database transaction.

    **Required:**
    - None.
    """

    def __init__(self, product_repo: ProductRepository, digital_asset_repo: DigitalAssetRepository) -> None:
        self._product_repo = product_repo
        self._digital_asset_repo = digital_asset_repo

    def execute(self) -> int:
        updated_count = 0
        variants_to_update: list[ProductVariant] = []

        with ts.atomic():
            digital_variants = self._product_repo.get_digital_variants_for_update()

            if not digital_variants:
                return 0

            for variant in digital_variants:
                actual_keys_count = self._digital_asset_repo.count_by(variant=variant, is_used=False)

                if variant.available_stock != actual_keys_count:
                    logger.info(
                        f"Variant {variant.id} stock mismatch. Old: {variant.available_stock}, New: {actual_keys_count}"
                    )
                    variant.set_available_stock(current_count=actual_keys_count)
                    variants_to_update.append(variant)

            if variants_to_update:
                self._product_repo.bulk_update_stock(variants=variants_to_update)
                updated_count = len(variants_to_update)

        return updated_count


class BulkCloneProductVariantCase:
    """
    Create new variations based on an original variant using field mutations.

    **Business Rules:**
    - Loop through the provided mutation dictionaries.
    - Save the clone via Repository, then apply ManyToMany relations (tags).
    - Execute strictly within an atomic database transaction.

    **Required:**
    - None (Gracefully returns 0 if no mutations are provided).
    """

    def __init__(self, product_repo: ProductRepository) -> None:
        self._product_repo = product_repo

    def execute(self, base_variant: ProductVariant, mutations: Sequence[Mapping[str, Any]]) -> int:
        if not mutations:
            return 0

        created_count = 0
        base_tags = list(base_variant.tags.all())

        with ts.atomic():
            for mutation in mutations:
                new_variant = base_variant.create_clone(mutation_data=mutation)
                new_variant = self._product_repo.save_variant(variant=new_variant)

                if base_tags:
                    new_variant.tags.set(base_tags)

                created_count += 1

        logger.info(f"Successfully cloned {created_count} variants from base {base_variant.id}.")
        return created_count
