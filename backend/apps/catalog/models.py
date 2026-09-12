import uuid
from collections.abc import Mapping, Sequence
from datetime import timedelta
from decimal import Decimal
from typing import Any

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import UploadedFile
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.catalog.domain.dto import ReviewDTO
from apps.catalog.domain.exceptions import (
    CatalogDigitalAssetAlreadyUsedError,
    CatalogDigitalAssetConflictError,
    CatalogInvalidStockOperationError,
    CatalogOutOfStockError,
    CatalogStockInconsistencyError,
)
from apps.core.models import DefaultModel
from apps.core.storage import hashed_storage


class Category(DefaultModel):
    name = models.CharField(verbose_name=_("Name"))
    slug = models.SlugField(unique=True, verbose_name=_("Slug"))

    class Meta(DefaultModel.Meta):
        verbose_name = _("Category")
        verbose_name_plural = _("Categories")

    def __str__(self) -> str:
        return self.name


class Tag(DefaultModel):
    name = models.CharField(verbose_name=_("Name"))
    slug = models.SlugField(unique=True, verbose_name=_("Slug"))

    class Meta(DefaultModel.Meta):
        verbose_name = _("Tag")
        verbose_name_plural = _("Tags")

    def __str__(self) -> str:
        return self.name


class Product(DefaultModel):
    class Type(models.TextChoices):
        PHYSICAL = "PHYSICAL", _("Physical")
        DIGITAL = "DIGITAL", _("Digital")

    name = models.CharField(max_length=150, verbose_name=_("Name"))
    category = models.ForeignKey(
        "catalog.Category",
        on_delete=models.PROTECT,
        related_name="products",
        null=True,
        verbose_name=_("Category"),
    )
    product_type = models.CharField(
        max_length=20,
        choices=Type.choices,
        default=Type.PHYSICAL,
        verbose_name=_("Product Type"),
    )
    main_image = models.ImageField(
        upload_to="products/main/",
        null=True,
        blank=True,
        storage=hashed_storage,
        verbose_name=_("Main Image"),
    )
    video_file = models.FileField(
        upload_to="products/videos/",
        storage=hashed_storage,
        null=True,
        blank=True,
        verbose_name=_("Video File"),
    )
    video_url = models.URLField(max_length=255, null=True, blank=True, verbose_name=_("Video URL"))
    attributes = models.JSONField(default=dict, blank=True, verbose_name=_("Attributes"))
    base_description = models.TextField(null=True, blank=True, verbose_name=_("Base Description"))

    class Meta(DefaultModel.Meta):
        verbose_name = _("Product")
        verbose_name_plural = _("Products")

    def clean(self) -> None:
        super().clean()
        if self.video_file and self.video_url:
            raise ValidationError(_("You can either upload a video file OR paste a video URL, but not both."))

    @property
    def video_source(self) -> str | None:
        if self.video_file:
            return str(self.video_file.url)
        return str(self.video_url) if self.video_url else None

    @property
    def requires_shipping(self) -> bool:
        return self.product_type == self.Type.PHYSICAL

    @property
    def is_instant_delivery(self) -> bool:
        return self.product_type == self.Type.DIGITAL

    @property
    def average_rating(self) -> float:
        return getattr(self, "annotated_avg_rating", 0.0)

    @property
    def purchases_count(self) -> int:
        return getattr(self, "annotated_purchases_count", 0)

    def __str__(self) -> str:
        return f"Product - {self.name}"


class ProductVariant(DefaultModel):
    class StockStatus(models.TextChoices):
        IN_STOCK = "IN_STOCK", _("In Stock")
        LOW_STOCK = "LOW_STOCK", _("Low Stock")
        OUT_OF_STOCK = "OUT_OF_STOCK", _("Out of Stock")

    product = models.ForeignKey(
        "catalog.Product", related_name="variants", on_delete=models.CASCADE, verbose_name=_("Product")
    )
    title = models.CharField(max_length=150, verbose_name=_("Title"))
    badge = models.CharField(max_length=50, null=True, blank=True, verbose_name=_("Badge"))
    image = models.ImageField(
        upload_to="products/variants/",
        storage=hashed_storage,
        null=True,
        blank=True,
        verbose_name=_("Image"),
    )
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name=_("Price"))
    old_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name=_("Old Price"))
    discount_expires_at = models.DateTimeField(null=True, blank=True, verbose_name=_("Discount Expires At"))

    available_stock = models.IntegerField(default=0, verbose_name=_("Available Stock"))
    reserved_stock = models.IntegerField(default=0, verbose_name=_("Reserved Stock"))

    tags = models.ManyToManyField("catalog.Tag", related_name="variants", blank=True, verbose_name=_("Tags"))
    specific_description = models.CharField(
        max_length=255, blank=True, null=True, verbose_name=_("Specific Description")
    )

    weight_kg = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name=_("Weight (kg)"))
    length_cm = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name=_("Length (cm)"))
    width_cm = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name=_("Width (cm)"))
    height_cm = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name=_("Height (cm)"))

    task_id = models.CharField(max_length=255, null=True, blank=True, verbose_name=_("Task ID"))
    metadata = models.JSONField(
        default=dict, blank=True, null=True, help_text=_("Universal field"), verbose_name=_("Metadata")
    )

    class Meta(DefaultModel.Meta):
        verbose_name = _("Product Variant")
        verbose_name_plural = _("Product Variants")
        constraints = [
            models.CheckConstraint(condition=models.Q(available_stock__gte=0), name="available_stock_not_negative"),
            models.CheckConstraint(condition=models.Q(reserved_stock__gte=0), name="reserved_stock_not_negative"),
        ]

    @property
    def is_promotion(self) -> bool:
        return bool(self.old_price and self.old_price > self.price)

    @property
    def promotion_discount(self) -> int:
        if self.old_price and self.old_price > self.price:
            return int((1 - (self.price / self.old_price)) * 100)
        return 0

    @property
    def is_new(self) -> bool:
        return timezone.now() - self.created_at < timedelta(days=7)

    @property
    def volumetric_weight_kg(self) -> Decimal:
        if self.length_cm and self.width_cm and self.height_cm:
            return (self.length_cm * self.width_cm * self.height_cm) / Decimal("5000.0")
        return Decimal("0.00")

    @property
    def stock_status(self) -> str:
        if self.available_stock <= 0:
            return self.StockStatus.OUT_OF_STOCK
        if self.available_stock <= 5:
            return self.StockStatus.LOW_STOCK
        return self.StockStatus.IN_STOCK

    @property
    def is_digital(self) -> bool:
        return self.product.product_type == Product.Type.DIGITAL

    def reserve_stock(self, quantity: int) -> list[str]:
        """
        Reserves stock when a user places an order.
        Moves items from available to reserved pool.
        """
        if quantity <= 0:
            raise CatalogInvalidStockOperationError("Quantity to reserve must be greater than zero.")
        if self.available_stock < quantity:
            raise CatalogOutOfStockError(f"Not enough stock for {self.title}. Available: {self.available_stock}")
        self.available_stock -= quantity
        self.reserved_stock += quantity
        return ["available_stock", "reserved_stock"]

    def release_stock(self, quantity: int) -> list[str]:
        """
        Releases stock when an order is cancelled or expires.
        Moves items back from reserved to available pool.
        """
        if quantity <= 0:
            raise CatalogInvalidStockOperationError("Quantity to release must be greater than zero.")
        if self.reserved_stock < quantity:
            raise CatalogStockInconsistencyError(f"Cannot release {quantity}. Only {self.reserved_stock} reserved.")
        self.reserved_stock -= quantity
        self.available_stock += quantity
        return ["available_stock", "reserved_stock"]

    def commit_stock(self, quantity: int) -> list[str]:
        """
        Commits stock when an order is successfully paid or shipped.
        Permanently removes the items from the reserved pool.
        """
        if quantity <= 0:
            raise CatalogInvalidStockOperationError("Quantity to commit must be greater than zero.")
        if self.reserved_stock < quantity:
            raise CatalogStockInconsistencyError(f"Cannot commit {quantity}. Only {self.reserved_stock} reserved.")
        self.reserved_stock -= quantity
        return ["reserved_stock"]

    def create_clone(self, mutation_data: Mapping[str, Any]) -> "ProductVariant":
        clone_data = {}
        exclude_fields = {"id", "created_at", "updated_at", "task_id"}
        for field in self._meta.get_fields():
            if getattr(field, "concrete", False) and not getattr(field, "many_to_many", False):
                if field.name not in exclude_fields:
                    clone_data[field.name] = getattr(self, field.name)
        clone_data.update({k: v for k, v in mutation_data.items() if k not in exclude_fields})
        return ProductVariant(**clone_data)

    def add_available_stock(self, added_count: int) -> list[str]:
        self.available_stock += added_count
        return ["available_stock"]

    def subtract_available_stock(self, subtract_count: int) -> list[str]:
        self.available_stock -= subtract_count
        return ["available_stock"]

    def set_available_stock(self, current_count: int) -> list[str]:
        self.available_stock = current_count
        return ["available_stock"]

    def __str__(self) -> str:
        return f"Variant - {self.title} ({self.product.name})"


class DigitalAsset(DefaultModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    variant = models.ForeignKey(
        ProductVariant, on_delete=models.CASCADE, related_name="digital_assets", verbose_name=_("Variant")
    )
    content = models.CharField(max_length=255, verbose_name=_("Content"))
    is_used = models.BooleanField(default=False, verbose_name=_("Is Used"))
    order_item = models.OneToOneField(
        "orders.OrderItem",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="issued_asset",
        verbose_name=_("Order Item"),
    )

    class Meta(DefaultModel.Meta):
        verbose_name = _("Digital Asset")
        verbose_name_plural = _("Digital Assets")
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(is_used=True, order_item__isnull=False) | models.Q(is_used=False, order_item__isnull=True)
                ),
                name="used_asset_must_have_order_item",
            )
        ]

    def allocate_to_order(self, order_item_id: str) -> list[str]:
        """
        Allocates a digital asset to a specific order item.
        """
        if self.is_used or self.order_item_id is not None:
            raise CatalogDigitalAssetAlreadyUsedError("This digital asset is already allocated.")
        self.is_used = True
        self.order_item_id = uuid.UUID(order_item_id)
        return ["is_used", "order_item_id"]

    def release_asset(self) -> list[str]:
        """
        Releases the digital asset back to the available pool if the order is cancelled.
        """
        if not self.is_used:
            raise CatalogDigitalAssetConflictError("Cannot release an asset that is not used.")
        self.is_used = False
        self.order_item_id = None
        return ["is_used", "order_item_id"]


class Photo(DefaultModel):
    product = models.ForeignKey(
        "catalog.Product", on_delete=models.CASCADE, related_name="gallery_photos", verbose_name=_("Product")
    )
    image = models.ImageField(
        upload_to="products/gallery/",
        storage=hashed_storage,
        verbose_name=_("Image"),
    )
    ordering = models.PositiveIntegerField(default=0, verbose_name=_("Ordering"))

    class Meta(DefaultModel.Meta):
        verbose_name = _("Photo")
        verbose_name_plural = _("Photos")
        ordering = ["ordering", "-created_at"]

    def __str__(self) -> str:
        return f"Gallery Photo for {self.product.name}"


class Review(DefaultModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reviews", verbose_name=_("User")
    )
    product = models.ForeignKey(
        "catalog.Product", related_name="reviews", on_delete=models.CASCADE, verbose_name=_("Product")
    )

    is_anonymous = models.BooleanField(default=False, verbose_name=_("Is Anonymous"))
    rating = models.IntegerField(
        default=1, validators=[MinValueValidator(1), MaxValueValidator(5)], verbose_name=_("Rating")
    )
    text = models.TextField(verbose_name=_("Text"), blank=True, null=True)

    admin_reply_text = models.TextField(null=True, blank=True, verbose_name=_("Admin Reply Text"))
    admin_reply_created_at = models.DateTimeField(null=True, blank=True, verbose_name=_("Admin Reply Created At"))

    class Meta(DefaultModel.Meta):
        verbose_name = _("Review")
        verbose_name_plural = _("Reviews")
        constraints = [models.UniqueConstraint(fields=["user", "product"], name="unique_review_per_user_product")]

    def add_admin_reply(self, text: str) -> list[str]:
        self.admin_reply_text = text
        self.admin_reply_created_at = timezone.now()
        return ["admin_reply_text", "admin_reply_created_at"]

    def update_review(self, dto: ReviewDTO) -> list[str]:
        updated_fields: list[str] = []
        if dto.rating is not None:
            self.rating = dto.rating
            updated_fields.append("rating")
        if dto.text is not None:
            self.text = dto.text
            updated_fields.append("text")
        return updated_fields

    def prepare_photos(self, photos: list[UploadedFile]) -> Sequence["ReviewPhoto"]:
        return [ReviewPhoto(review=self, image=photo_file) for photo_file in photos]

    def __str__(self) -> str:
        return f"Review by {self.user} for {self.product_id} (Rating: {self.rating})"


class FavoriteItem(DefaultModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="favorites", verbose_name=_("User")
    )
    product = models.ForeignKey("catalog.Product", on_delete=models.CASCADE, verbose_name=_("Product"))

    class Meta(DefaultModel.Meta):
        verbose_name = _("Favorite Item")
        verbose_name_plural = _("Favorite Items")
        constraints = [models.UniqueConstraint(fields=["user", "product"], name="unique_favorite_item")]

    def __str__(self) -> str:
        return f"Favorite item - {self.product.name}"


class ReviewPhoto(DefaultModel):
    review = models.ForeignKey(Review, on_delete=models.CASCADE, related_name="photos", verbose_name=_("Review"))
    image = models.ImageField(upload_to="reviews/", storage=hashed_storage, verbose_name=_("Image"))

    class Meta(DefaultModel.Meta):
        verbose_name = _("Review Photo")
        verbose_name_plural = _("Review Photos")

    def __str__(self) -> str:
        return f"Photo for review #{self.review.id}"
