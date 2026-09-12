import uuid
from typing import cast
from unittest.mock import MagicMock, patch

import pytest
from pytest_mock import MockerFixture

from apps.catalog.domain.dto import CreateReviewDTO
from apps.catalog.domain.exceptions import (
    CatalogFavoriteItemExistError,
    CatalogProductNotPurchasedError,
    CatalogReviewAlreadyExistsError,
)
from apps.catalog.models import ProductVariant
from apps.catalog.repo import (
    DigitalAssetRepository,
    FavoriteItemRepository,
    ProductRepository,
    ReviewRepository,
)
from apps.catalog.usecases import (
    BulkCloneProductVariantCase,
    BulkCreateDigitalAssetsCase,
    BulkDeleteDigitalAssetsCase,
    CreateFavoriteItemCase,
    CreateReviewCase,
    DeleteFavoriteItemCase,
    DeleteReviewCase,
    GetReviewsCase,
    SyncDigitalVariantsStockCase,
    UpdateReviewCase,
)
from apps.core.domain.exceptions import CoreObjectNotFoundError
from apps.orders.repo import OrderRepository


@patch("django.db.transaction.atomic", MagicMock())
class TestCreateFavoriteItemCase:
    def test_create_favorite_item_success(self) -> None:
        """Happy path: Successfully adds a product to the user's wishlist."""
        mock_fav_repo: MagicMock | FavoriteItemRepository = MagicMock()
        mock_product_repo: MagicMock | ProductRepository = MagicMock()
        usecase = CreateFavoriteItemCase(favorite_item_repo=mock_fav_repo, product_repo=mock_product_repo)
        fake_user = MagicMock()
        fake_product = MagicMock()
        mock_product_repo.get_by.return_value = fake_product  # type: ignore[union-attr]
        mock_fav_repo.get_or_create.return_value = (MagicMock(), True)  # type: ignore[union-attr]

        usecase.execute(user=fake_user, product_id=1)

        mock_product_repo.get_by.assert_called_once_with(id=1)  # type: ignore[union-attr]
        mock_fav_repo.get_or_create.assert_called_once_with(user=fake_user, product=fake_product)  # type: ignore[union-attr]

    def test_create_favorite_item_already_exists(self) -> None:
        """Failure path: Raises error if product is already in the wishlist."""
        mock_fav_repo: MagicMock | FavoriteItemRepository = MagicMock()
        mock_product_repo: MagicMock | ProductRepository = MagicMock()
        usecase = CreateFavoriteItemCase(favorite_item_repo=mock_fav_repo, product_repo=mock_product_repo)
        mock_product_repo.get_by.return_value = MagicMock()  # type: ignore[union-attr]
        mock_fav_repo.get_or_create.return_value = (MagicMock(), False)  # type: ignore[union-attr]

        with pytest.raises(CatalogFavoriteItemExistError):
            usecase.execute(user=MagicMock(), product_id=1)


@patch("django.db.transaction.atomic", MagicMock())
class TestDeleteFavoriteItemCase:
    def test_delete_favorite_item_success(self) -> None:
        """Happy path: Deletes the favorite item successfully."""
        mock_fav_repo: MagicMock | FavoriteItemRepository = MagicMock()
        usecase = DeleteFavoriteItemCase(favorite_item_repo=mock_fav_repo)
        fake_user = MagicMock()
        fake_items = MagicMock()
        mock_fav_repo.filter_by.return_value = fake_items  # type: ignore[union-attr]
        mock_fav_repo.delete.return_value = (1, {})  # type: ignore[union-attr]

        usecase.execute(user=fake_user, product_id=1)

        mock_fav_repo.filter_by.assert_called_once_with(user=fake_user, product_id=1)  # type: ignore[union-attr]
        mock_fav_repo.delete.assert_called_once_with(objects=fake_items)  # type: ignore[union-attr]

    def test_delete_favorite_item_not_found(self) -> None:
        """Failure path: Raises error if the favorite item does not exist."""
        mock_fav_repo: MagicMock | FavoriteItemRepository = MagicMock()
        usecase = DeleteFavoriteItemCase(favorite_item_repo=mock_fav_repo)
        mock_fav_repo.delete.return_value = (0, {})  # type: ignore[union-attr]

        with pytest.raises(CoreObjectNotFoundError):
            usecase.execute(user=MagicMock(), product_id=1)


class TestGetReviewsCase:
    def test_get_reviews_success(self) -> None:
        """Happy path: Successfully retrieves product reviews."""
        mock_review_repo: MagicMock | ReviewRepository = MagicMock()
        mock_product_repo: MagicMock | ProductRepository = MagicMock()
        usecase = GetReviewsCase(review_repo=mock_review_repo, product_repo=mock_product_repo)
        fake_user = MagicMock()
        mock_product_repo.exist_object.return_value = True  # type: ignore[union-attr]

        usecase.execute(user=fake_user, product_id=1)

        mock_review_repo.get_product_reviews.assert_called_once_with(user=fake_user, product_id=1)  # type: ignore[union-attr]

    def test_get_reviews_product_not_found(self) -> None:
        """Failure path: Raises error if the product does not exist."""
        mock_review_repo: MagicMock | ReviewRepository = MagicMock()
        mock_product_repo: MagicMock | ProductRepository = MagicMock()
        usecase = GetReviewsCase(review_repo=mock_review_repo, product_repo=mock_product_repo)
        mock_product_repo.exist_object.return_value = False  # type: ignore[union-attr]

        with pytest.raises(CoreObjectNotFoundError):
            usecase.execute(user=MagicMock(), product_id=1)


@patch("django.db.transaction.atomic", MagicMock())
class TestCreateReviewCase:
    def test_create_review_success(self) -> None:
        """Happy path: Successfully creates a review."""
        mock_review_repo: MagicMock | ReviewRepository = MagicMock()
        mock_product_repo: MagicMock | ProductRepository = MagicMock()
        mock_order_repo: MagicMock | OrderRepository = MagicMock()
        usecase = CreateReviewCase(
            review_repo=mock_review_repo,
            product_repo=mock_product_repo,
            order_repo=mock_order_repo,
        )
        fake_user = MagicMock()
        fake_product = MagicMock(id=1)
        fake_review = MagicMock()
        dto = CreateReviewDTO(product_id=1, rating=5, text="Great!", is_anonymous=False, photos=[])

        mock_order_repo.check_user_purchased_product.return_value = True  # type: ignore[union-attr]
        mock_product_repo.get_by.return_value = fake_product  # type: ignore[union-attr]
        mock_review_repo.exists_by.return_value = False  # type: ignore[union-attr]
        mock_review_repo.create.return_value = fake_review  # type: ignore[union-attr]
        fake_review.prepare_photos.return_value = []

        usecase.execute(user=fake_user, dto=dto)

        mock_review_repo.create.assert_called_once_with(  # type: ignore[union-attr]
            user=fake_user, product=fake_product, rating=5, text="Great!", is_anonymous=False
        )
        mock_review_repo.save_photos.assert_called_once_with(photos=[])  # type: ignore[union-attr]

    def test_create_review_not_purchased(self) -> None:
        """Failure path: User hasn't purchased the product."""
        mock_order_repo: MagicMock | OrderRepository = MagicMock()
        usecase = CreateReviewCase(review_repo=MagicMock(), product_repo=MagicMock(), order_repo=mock_order_repo)
        mock_order_repo.check_user_purchased_product.return_value = False  # type: ignore[union-attr]

        with pytest.raises(CatalogProductNotPurchasedError):
            usecase.execute(user=MagicMock(), dto=MagicMock())

    def test_create_review_already_exists(self) -> None:
        """Failure path: Review already exists."""
        mock_order_repo: MagicMock | OrderRepository = MagicMock()
        mock_review_repo: MagicMock | ReviewRepository = MagicMock()
        usecase = CreateReviewCase(review_repo=mock_review_repo, product_repo=MagicMock(), order_repo=mock_order_repo)
        mock_order_repo.check_user_purchased_product.return_value = True  # type: ignore[union-attr]
        mock_review_repo.exists_by.return_value = True  # type: ignore[union-attr]

        with pytest.raises(CatalogReviewAlreadyExistsError):
            usecase.execute(user=MagicMock(), dto=MagicMock())


@patch("django.db.transaction.atomic", MagicMock())
class TestUpdateReviewCase:
    def test_update_review_success(self) -> None:
        """Happy path: Updates review fields successfully."""
        mock_review_repo: MagicMock | ReviewRepository = MagicMock()
        usecase = UpdateReviewCase(review_repo=mock_review_repo)
        fake_user = MagicMock()
        fake_review = MagicMock()
        review_id = uuid.uuid4()

        mock_review_repo.get_for_update_by.return_value = fake_review  # type: ignore[union-attr]
        fake_review.update_review.return_value = ["rating", "text"]

        usecase.execute(user=fake_user, review_id=review_id, rating=4, text="Updated")

        fake_review.update_review.assert_called_once()
        mock_review_repo.save.assert_called_once_with(  # type: ignore[union-attr]
            instance=fake_review, update_fields=["rating", "text"]
        )


@patch("django.db.transaction.atomic", MagicMock())
class TestDeleteReviewCase:
    def test_delete_review_success(self) -> None:
        """Happy path: Deletes a review."""
        mock_review_repo: MagicMock | ReviewRepository = MagicMock()
        usecase = DeleteReviewCase(review_repo=mock_review_repo)
        fake_user = MagicMock()
        fake_review = MagicMock()
        review_id = uuid.uuid4()

        mock_review_repo.get_by.return_value = fake_review  # type: ignore[union-attr]

        usecase.execute(user=fake_user, review_id=review_id)

        mock_review_repo.delete.assert_called_once_with(objects=fake_review)  # type: ignore[union-attr]


@patch("django.db.transaction.atomic", MagicMock())
class TestBulkCreateDigitalAssetsCase:
    def test_bulk_create_success(self, mocker: MockerFixture) -> None:
        """Happy path: Successfully creates valid digital assets and updates stock."""
        mock_digital_repo: MagicMock | DigitalAssetRepository = MagicMock()
        mock_product_repo: MagicMock | ProductRepository = MagicMock()
        usecase = BulkCreateDigitalAssetsCase(digital_asset_repo=mock_digital_repo, product_repo=mock_product_repo)

        fake_variant = ProductVariant(id=1)
        mocker.patch.object(fake_variant, "add_available_stock", return_value=["available_stock"])

        raw_keys = ["  key_1  ", "", "key_2", "   "]

        result = usecase.execute(variant=fake_variant, raw_keys=raw_keys)

        assert result == 2
        mock_digital_repo.bulk_create.assert_called_once()  # type: ignore[union-attr]
        cast(MagicMock, fake_variant.add_available_stock).assert_called_once_with(added_count=2)
        mock_product_repo.save_variant.assert_called_once_with(  # type: ignore[union-attr]
            variant=fake_variant, update_fields=["available_stock"]
        )

    def test_bulk_create_empty_keys(self) -> None:
        """Failure path: Returns 0 when no valid keys are provided."""
        mock_digital_repo: MagicMock | DigitalAssetRepository = MagicMock()
        usecase = BulkCreateDigitalAssetsCase(digital_asset_repo=mock_digital_repo, product_repo=MagicMock())

        result = usecase.execute(variant=ProductVariant(id=1), raw_keys=["", "   "])

        assert result == 0
        mock_digital_repo.bulk_create.assert_not_called()  # type: ignore[union-attr]


@patch("django.db.transaction.atomic", MagicMock())
class TestBulkDeleteDigitalAssetsCase:
    def test_bulk_delete_success(self) -> None:
        """Happy path: Deletes assets and subtracts stock."""
        mock_digital_repo: DigitalAssetRepository | MagicMock = MagicMock()
        mock_product_repo: ProductRepository | MagicMock = MagicMock()
        usecase = BulkDeleteDigitalAssetsCase(digital_asset_repo=mock_digital_repo, product_repo=mock_product_repo)
        fake_variant = MagicMock(id=1)
        fake_variant.subtract_available_stock.return_value = ["available_stock"]
        fake_assets = [MagicMock(), MagicMock()]
        mock_digital_repo.filter_for_update_by.return_value = fake_assets  # type: ignore[union-attr]
        mock_digital_repo.delete.return_value = (2, {"catalog.DigitalAsset": 2})  # type: ignore[union-attr]

        result = usecase.execute(variant=fake_variant, asset_ids=["uuid1", "uuid2"])

        assert result == 2
        mock_digital_repo.delete.assert_called_once_with(objects=fake_assets)  # type: ignore[union-attr]
        mock_product_repo.save_variant.assert_called_once_with(  # type: ignore[union-attr]
            variant=fake_variant, update_fields=["available_stock"]
        )

    def test_bulk_delete_no_ids(self) -> None:
        """Failure path: Returns 0 when no IDs provided."""
        mock_digital_repo: DigitalAssetRepository | MagicMock = MagicMock()
        usecase = BulkDeleteDigitalAssetsCase(digital_asset_repo=mock_digital_repo, product_repo=MagicMock())

        result = usecase.execute(variant=MagicMock(), asset_ids=[])

        assert result == 0
        mock_digital_repo.delete.assert_not_called()  # type: ignore[union-attr]


@patch("django.db.transaction.atomic", MagicMock())
class TestSyncDigitalVariantsStockCase:
    def test_sync_variants_stock_success(self) -> None:
        """Happy path: Updates stock when there is a mismatch."""
        mock_product_repo: MagicMock | ProductRepository = MagicMock()
        mock_digital_repo: MagicMock | DigitalAssetRepository = MagicMock()
        usecase = SyncDigitalVariantsStockCase(product_repo=mock_product_repo, digital_asset_repo=mock_digital_repo)
        fake_variant = MagicMock(available_stock=5)
        mock_product_repo.get_digital_variants_for_update.return_value = [fake_variant]  # type: ignore[union-attr]
        mock_digital_repo.count_by.return_value = 10  # type: ignore[union-attr]

        result = usecase.execute()

        assert result == 1
        fake_variant.set_available_stock.assert_called_once_with(current_count=10)
        mock_product_repo.bulk_update_stock.assert_called_once_with(variants=[fake_variant])  # type: ignore[union-attr]


@patch("django.db.transaction.atomic", MagicMock())
class TestBulkCloneProductVariantCase:
    def test_bulk_clone_success(self) -> None:
        """Happy path: Successfully clones variants and sets ManyToMany tags."""
        mock_product_repo: MagicMock | ProductRepository = MagicMock()
        usecase = BulkCloneProductVariantCase(product_repo=mock_product_repo)

        base_variant = MagicMock()
        fake_tags = [MagicMock(), MagicMock()]
        base_variant.tags.all.return_value = fake_tags

        new_variant_1 = MagicMock()
        new_variant_2 = MagicMock()
        base_variant.create_clone.side_effect = [new_variant_1, new_variant_2]
        mock_product_repo.save_variant.side_effect = [new_variant_1, new_variant_2]  # type: ignore[union-attr]

        mutations = [{"price": "10.00"}, {"price": "20.00"}]

        result = usecase.execute(base_variant=base_variant, mutations=mutations)

        assert result == 2
        assert base_variant.create_clone.call_count == 2
        assert mock_product_repo.save_variant.call_count == 2  # type: ignore[union-attr]
        new_variant_1.tags.set.assert_called_once_with(fake_tags)
        new_variant_2.tags.set.assert_called_once_with(fake_tags)

    def test_bulk_clone_empty_mutations(self) -> None:
        """Failure path: Returns 0 when no mutations provided."""
        mock_product_repo: MagicMock | ProductRepository = MagicMock()
        usecase = BulkCloneProductVariantCase(product_repo=mock_product_repo)

        result = usecase.execute(base_variant=MagicMock(), mutations=[])

        assert result == 0
        mock_product_repo.save_variant.assert_not_called()  # type: ignore[union-attr]
