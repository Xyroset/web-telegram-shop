from typing import Any

from django.db import models
from django.utils.translation import gettext_lazy as _


class DefaultModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created at"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Updated at"))
    is_active = models.BooleanField(default=True, verbose_name=_("Is active"))

    class Meta:
        abstract = True

        indexes = [
            models.Index(fields=["is_active", "-created_at"]),
        ]

    def save(self, *args: Any, **kwargs: Any) -> None:
        if "update_fields" in kwargs and kwargs["update_fields"] is not None:
            update_fields = set(kwargs["update_fields"])
            update_fields.add("updated_at")
            kwargs["update_fields"] = list(update_fields)

        super().save(*args, **kwargs)
