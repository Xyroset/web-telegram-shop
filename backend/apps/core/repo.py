from collections.abc import Sequence
from typing import Any, Generic, TypeVar

from django.db import models

from apps.core.domain.exceptions import CoreMultipleObjectsFoundError, CoreObjectNotFoundError, CoreRequiredFiltersError

T = TypeVar("T", bound=models.Model)


class BaseRepository(Generic[T]):
    """
    Base repository providing standard data access methods for Django models.
    Abstracts the ORM from the Use Cases layer.
    """

    def __init__(self, model_class: type[T]) -> None:
        """
        Initialize the repository with a specific Django model class.

        Args:
            model_class (type[T]): The specific Django model class this repository manages.
        """
        self.model_class = model_class

    def get_or_create(self, defaults: dict[str, Any] | None = None, **filters: Any) -> tuple[T, bool]:
        """
        Get an existing object by multiple filter fields, or create it if it does not exist.
        """
        if not filters:
            creation_data = defaults or {}
            instance = self.model_class.objects.create(**creation_data)  # type: ignore[attr-defined]
            return instance, True

        try:
            return self.model_class.objects.get_or_create(**filters, defaults=defaults)  # type: ignore[attr-defined, no-any-return]

        except self.model_class.MultipleObjectsReturned:  # type: ignore[attr-defined]
            filters_str = ", ".join(f"{key}={value}" for key, value in filters.items())
            raise CoreMultipleObjectsFoundError(
                f"Expected 1 object for lookup, but found multiple! Filters: {filters_str}"
            )

    def create(self, **fields: Any) -> T:
        """
        Directly create and return a new domain model instance.
        """
        return self.model_class.objects.create(**fields)  # type: ignore[attr-defined, no-any-return]

    def get_by(self, **filters: Any) -> T:
        """
        Fetch a single object matching the provided multiple filters.
        """
        if not filters:
            raise CoreRequiredFiltersError("At least one filter parameter must be provided to get_by().")

        try:
            return self.model_class.objects.get(**filters)  # type: ignore[attr-defined, no-any-return]

        except self.model_class.DoesNotExist:  # type: ignore[attr-defined]
            filters_str = ", ".join(f"{key}={value}" for key, value in filters.items())
            raise CoreObjectNotFoundError(f"Object not found! Filters: {filters_str}")

        except self.model_class.MultipleObjectsReturned:  # type: ignore[attr-defined]
            filters_str = ", ".join(f"{key}={value}" for key, value in filters.items())
            raise CoreMultipleObjectsFoundError(
                f"Expected 1 object, but found multiple! Use filter_by() for multiple! Filters: {filters_str}"
            )

    def get_for_update_by(self, **filters: Any) -> T:
        """
        Fetch a single object matching the provided multiple filters and lock it for update.
        Utilizes `select_for_update()` to prevent race conditions during concurrent modifications.
        """
        if not filters:
            raise CoreRequiredFiltersError("At least one filter parameter must be provided to get_for_update_by().")

        try:
            return self.model_class.objects.select_for_update(of=("self",)).get(**filters)  # type: ignore[attr-defined, no-any-return]

        except self.model_class.DoesNotExist:  # type: ignore[attr-defined]
            filters_str = ", ".join(f"{key}={value}" for key, value in filters.items())
            raise CoreObjectNotFoundError(f"Object not found! Filters: {filters_str}")

        except self.model_class.MultipleObjectsReturned:  # type: ignore[attr-defined]
            filters_str = ", ".join(f"{key}={value}" for key, value in filters.items())
            raise CoreMultipleObjectsFoundError(
                f"Expected 1 object, but found multiple! Use filter_for_update_by() for multiple!"
                f" Filters: {filters_str}"
            )

    def filter_by(self, **filters: Any) -> models.QuerySet[T]:
        """
        Fetch a QuerySet of objects matching the provided filters.
        """
        if not filters:
            raise CoreRequiredFiltersError("At least one filter parameter must be provided to filter_by().")

        return self.model_class.objects.filter(**filters)  # type: ignore[attr-defined, no-any-return]

    def filter_for_update_by(self, **filters: Any) -> models.QuerySet[T]:
        """
        Fetch a QuerySet of objects matching the provided filters and lock them for update.
        """
        if not filters:
            raise CoreRequiredFiltersError("At least one filter parameter must be provided to filter_for_update_by().")

        return self.model_class.objects.select_for_update(of=("self",)).filter(**filters)  # type: ignore[attr-defined, no-any-return]

    def save(self, instance: T, update_fields: Sequence[str] | None = None) -> None:
        """
        Save the domain model instance to the database.
        """
        instance.save(update_fields=update_fields)

    def delete(self, objects: T | models.QuerySet[T]) -> tuple[int, dict[str, int]]:
        """
        Permanently delete a single object from the database.
        """
        return objects.delete()

    def bulk_create(self, objects: Sequence[T]) -> None:
        """
        Insert multiple objects into the database in an efficient manner.
        """
        if not objects:
            raise CoreObjectNotFoundError("Object(s) not found for update")

        self.model_class.objects.bulk_create(objects)  # type: ignore[attr-defined]

    def bulk_update(self, objects: Sequence[T], update_fields: Sequence[str]) -> None:
        """
        Update multiple objects in the database efficiently.
        Django requires `update_fields` to be explicitly provided.
        """
        if not objects:
            raise CoreObjectNotFoundError("Object(s) not found for update")

        if not update_fields:
            raise ValueError("update_fields must be provided for bulk_update.")

        self.model_class.objects.bulk_update(objects, fields=update_fields)  # type: ignore[attr-defined]

    def count_by(self, **filters: Any) -> int:
        """
        Counts records matching the provided filters efficiently.
        """
        if not filters:
            raise CoreRequiredFiltersError("At least one filter parameter must be provided.")

        return self.model_class.objects.filter(**filters).count()  # type: ignore[attr-defined, no-any-return]

    def exist_object(self, **filters: Any) -> bool:
        """
        Efficiently checks if any record matches the provided filters using EXISTS query.
        """
        if not filters:
            raise CoreRequiredFiltersError("At least one filter parameter must be provided.")

        return self.model_class.objects.filter(**filters).exists()  # type: ignore[attr-defined, no-any-return]
