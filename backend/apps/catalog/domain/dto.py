from dataclasses import dataclass

from django.core.files.uploadedfile import UploadedFile


@dataclass
class ReviewDTO:
    rating: int | None = None
    text: str | None = None


@dataclass(frozen=True)
class CreateReviewDTO:
    product_id: int
    rating: int
    text: str | None
    is_anonymous: bool
    photos: list[UploadedFile]
