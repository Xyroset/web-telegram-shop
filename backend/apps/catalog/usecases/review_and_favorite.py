import logging
import uuid

from django.db import transaction as ts
from django.db.models import QuerySet

from apps.catalog.domain.dto import CreateReviewDTO, ReviewDTO
from apps.catalog.domain.exceptions import (
    CatalogFavoriteItemExistError,
    CatalogProductNotPurchasedError,
    CatalogReviewAlreadyExistsError,
)
from apps.catalog.models import Review
from apps.catalog.repo import FavoriteItemRepository, ProductRepository, ReviewRepository
from apps.core.domain.exceptions import CoreObjectNotFoundError
from apps.orders.repo import OrderRepository
from apps.users.models import User

logger = logging.getLogger(__name__)


class CreateFavoriteItemCase:
    """
    Add a product to the user's wishlist (favorites).

    **Business Rules:**
    - Ensures the product is only added once.
    - Throws a conflict error if it's already in the wishlist.

    **Required:**
    - The product must exist.
    """

    def __init__(self, favorite_item_repo: FavoriteItemRepository, product_repo: ProductRepository) -> None:
        self._favorite_item_repo = favorite_item_repo
        self._product_repo = product_repo

    def execute(self, user: User, product_id: int) -> None:
        product = self._product_repo.get_by(id=product_id)
        _, created = self._favorite_item_repo.get_or_create(user=user, product=product)

        if not created:
            raise CatalogFavoriteItemExistError("Product is already in favorites.")


class DeleteFavoriteItemCase:
    """
    Remove a product from the user's wishlist.

    **Business Rules:**
    - Strictly delegates deletion to the repository.

    **Required:**
    - The favorite item must exist for the given user and product.
    """

    def __init__(self, favorite_item_repo: FavoriteItemRepository) -> None:
        self._favorite_item_repo = favorite_item_repo

    def execute(self, user: User, product_id: int) -> None:
        with ts.atomic():
            favorite_items = self._favorite_item_repo.filter_by(user=user, product_id=product_id)
            deleted_count, _ = self._favorite_item_repo.delete(objects=favorite_items)

            if deleted_count == 0:
                raise CoreObjectNotFoundError(f"Favorite item for product {product_id} not found!")


class GetReviewsCase:
    """
    Retrieves all reviews for a specific product.

    **Business Rules:**
    - Fetches reviews using the repository to apply formatting annotations.

    **Required:**
    - The target product must exist in the database.
    """

    def __init__(self, review_repo: ReviewRepository, product_repo: ProductRepository) -> None:
        self._review_repo = review_repo
        self._product_repo = product_repo

    def execute(self, user: User, product_id: int) -> QuerySet[Review]:
        if not self._product_repo.exist_object(id=product_id):
            raise CoreObjectNotFoundError(f"Product {product_id} not found.")

        return self._review_repo.get_product_reviews(user=user, product_id=product_id)


class CreateReviewCase:
    """
    Creates a product review from a user.

    **Business Rules:**
    - A user can only write a review if they have successfully purchased the product.
    - A user can only write one review per product to prevent spam.

    **Required:**
    - User must have a PAID or DELIVERED order containing this product. Otherwise, `CatalogProductNotPurchasedError`.
    - User must not have an existing review for this product. Otherwise, `CatalogReviewAlreadyExistsError`.
    """

    def __init__(
        self, review_repo: ReviewRepository, product_repo: ProductRepository, order_repo: OrderRepository
    ) -> None:
        self._review_repo = review_repo
        self._product_repo = product_repo
        self._order_repo = order_repo

    def execute(self, user: User, dto: CreateReviewDTO) -> None:
        has_purchased = self._order_repo.check_user_purchased_product(user=user, product_id=dto.product_id)
        if not has_purchased:
            raise CatalogProductNotPurchasedError("You can only review products you have purchased.")

        product = self._product_repo.get_by(id=dto.product_id)

        if self._review_repo.exists_by(user=user, product=product):
            raise CatalogReviewAlreadyExistsError("You have already reviewed this product.")

        with ts.atomic():
            review = self._review_repo.create(
                user=user, product=product, rating=dto.rating, text=dto.text, is_anonymous=dto.is_anonymous
            )
            photos = review.prepare_photos(photos=dto.photos)
            self._review_repo.save_photos(photos=photos)

        logger.info(f"Review created by user {user.tg_id} for product {product.id}.")


class UpdateReviewCase:
    """
    Updates an existing review's rating and text.

    **Business Rules:**
    - Validates review ownership by passing `user` to the repository lookup.
    - Executes row locking to prevent race conditions during updates.

    **Required:**
    - The review must exist and belong to the requesting user.
    """

    def __init__(self, review_repo: ReviewRepository) -> None:
        self._review_repo = review_repo

    def execute(self, user: User, review_id: uuid.UUID, rating: int, text: str) -> None:
        with ts.atomic():
            review = self._review_repo.get_for_update_by(id=review_id, user=user)

            dto = ReviewDTO(rating=rating, text=text)
            update_fields = review.update_review(dto=dto)

            self._review_repo.save(instance=review, update_fields=update_fields)


class DeleteReviewCase:
    """
    Soft deletes an existing review.

    **Business Rules:**
    - Validates review ownership by passing `user` to the repository lookup.

    **Required:**
    - The review must exist and belong to the requesting user.
    """

    def __init__(self, review_repo: ReviewRepository) -> None:
        self._review_repo = review_repo

    def execute(self, user: User, review_id: uuid.UUID) -> None:
        with ts.atomic():
            review = self._review_repo.get_by(id=review_id, user=user)
            self._review_repo.delete(objects=review)
