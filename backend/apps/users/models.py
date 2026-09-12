from typing import TYPE_CHECKING, Any

from django.contrib.auth.models import AbstractUser, BaseUserManager, PermissionsMixin
from django.core.files.base import ContentFile
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.models import DefaultModel
from apps.core.storage import hashed_storage
from apps.users.domain.dto import UserDeliveryDataDTO, UserSettingsDataDTO

if TYPE_CHECKING:
    from apps.orders.models import PromoCode


class CustomUserManager(BaseUserManager["User"]):
    """
    Custom manager for User model to handle Telegram ID authentication.

    NOTE: `save()` is used here ONLY to support Django's CLI (e.g., createsuperuser).
    In application logic (Use Cases), users must be created and saved via UserRepository.
    """

    def create_user(self, tg_id: int, password: str | None = None, **extra_fields: Any) -> "User":
        if not tg_id:
            raise ValueError("tg_id (Telegram ID) is required to create a user.")

        user = self.model(tg_id=tg_id, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, tg_id: int, password: str | None = None, **extra_fields: Any) -> "User":
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self.create_user(tg_id, password, **extra_fields)


class UserSettingsData(DefaultModel):
    class Theme(models.TextChoices):
        LIGHT = "light", _("Light theme")
        DARK = "dark", _("Dark theme")

    class ParticlesStyle(models.TextChoices):
        NONE = "none", _("None")
        LINES = "lines", _("Lines")
        SHAPES = "shapes", _("Shapes")
        BOTH = "both", _("Both")

    user = models.OneToOneField("users.User", on_delete=models.CASCADE, related_name="settings", verbose_name=_("User"))

    preferred_payment_currency = models.CharField(
        max_length=50, default="usdt", verbose_name=_("Preferred payment currency")
    )
    preferred_network = models.CharField(max_length=50, default="trc20", verbose_name=_("Preferred network"))
    particles_style = models.CharField(
        max_length=50, choices=ParticlesStyle.choices, default=ParticlesStyle.BOTH, verbose_name=_("Particles style")
    )

    default_theme = models.CharField(
        max_length=50, choices=Theme.choices, default=Theme.LIGHT, verbose_name=_("Default theme")
    )
    custom_theme = models.CharField(
        max_length=50, choices=Theme.choices, null=True, blank=True, verbose_name=_("Custom theme")
    )

    default_language_code = models.CharField(max_length=50, default="en", verbose_name=_("Default language code"))
    custom_language_code = models.CharField(
        max_length=50, null=True, blank=True, verbose_name=_("Custom language code")
    )

    class Meta(DefaultModel.Meta):
        verbose_name = _("User settings")
        verbose_name_plural = _("User settings")

    @property
    def current_theme(self) -> str:
        return self.custom_theme if self.custom_theme else self.default_theme

    @property
    def current_language_code(self) -> str:
        return self.custom_language_code if self.custom_language_code else self.default_language_code

    def update_settings(self, dto: UserSettingsDataDTO) -> list[str]:
        updated_fields: list[str] = []

        if dto.preferred_payment_currency is not None:
            self.preferred_payment_currency = dto.preferred_payment_currency
            updated_fields.append("preferred_payment_currency")

        if dto.preferred_network is not None:
            self.preferred_network = dto.preferred_network
            updated_fields.append("preferred_network")

        if dto.default_theme is not None:
            self.default_theme = dto.default_theme
            updated_fields.append("default_theme")

        if dto.custom_theme is not None:
            self.custom_theme = dto.custom_theme if dto.custom_theme != "" else None
            updated_fields.append("custom_theme")

        if dto.default_language_code is not None:
            self.default_language_code = dto.default_language_code
            updated_fields.append("default_language_code")

        if dto.custom_language_code is not None:
            self.custom_language_code = dto.custom_language_code if dto.custom_language_code != "" else None
            updated_fields.append("custom_language_code")

        if dto.particles_style is not None:
            self.particles_style = dto.particles_style
            updated_fields.append("particles_style")

        return updated_fields


class UserDeliveryData(DefaultModel):
    user = models.ForeignKey(
        "users.User", on_delete=models.CASCADE, related_name="delivery_data", verbose_name=_("User")
    )
    is_current = models.BooleanField(default=True, verbose_name=_("Is current"))

    full_name = models.CharField(max_length=255, null=True, blank=True, verbose_name=_("Full name"))
    email = models.CharField(max_length=255, null=True, blank=True, verbose_name=_("Email"))
    phone = models.CharField(max_length=50, null=True, blank=True, verbose_name=_("Phone"))
    zip_code = models.CharField(max_length=20, null=True, blank=True, verbose_name=_("Zip code"))
    address_line = models.CharField(max_length=255, null=True, blank=True, verbose_name=_("Address line"))
    destination_code = models.CharField(max_length=50, null=True, blank=True, verbose_name=_("Destination code"))
    region_code = models.CharField(max_length=50, null=True, blank=True, verbose_name=_("Region code"))

    class Meta(DefaultModel.Meta):
        verbose_name = _("User delivery data")
        verbose_name_plural = _("User delivery data")
        constraints = [
            models.UniqueConstraint(
                fields=["user"], condition=models.Q(is_current=True), name="unique_current_child_per_parent"
            )
        ]
        indexes = DefaultModel.Meta.indexes + [
            models.Index(
                fields=["is_current"],
                name="idx_is_current",
            ),
        ]

    def update_delivery_data(self, dto: UserDeliveryDataDTO) -> list[str]:
        updated_fields: list[str] = []

        if dto.full_name is not None:
            self.full_name = dto.full_name
            updated_fields.append("full_name")

        if dto.email is not None:
            self.email = dto.email
            updated_fields.append("email")

        if dto.phone is not None:
            self.phone = dto.phone
            updated_fields.append("phone")

        if dto.address_line is not None:
            self.address_line = dto.address_line
            updated_fields.append("address_line")

        if dto.zip_code is not None:
            self.zip_code = dto.zip_code
            updated_fields.append("zip_code")

        if dto.destination_code is not None:
            self.destination_code = dto.destination_code
            updated_fields.append("destination_code")

        if dto.region_code is not None and dto.region_code.strip() == "":
            self.region_code = None
            updated_fields.append("region_code")
        elif dto.region_code is not None:
            self.region_code = dto.region_code
            updated_fields.append("region_code")

        return updated_fields

    def mark_as_current(self) -> list[str]:
        self.is_current = True
        return ["is_current"]

    def unset_current(self) -> list[str]:
        self.is_current = False
        return ["is_current"]


class UserPromocode(DefaultModel):
    user = models.ForeignKey("users.User", on_delete=models.CASCADE, verbose_name=_("User"))
    promocode = models.ForeignKey(
        "orders.Promocode", on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_("Promo code")
    )
    used = models.PositiveIntegerField(default=1, verbose_name=_("Used"))

    class Meta(DefaultModel.Meta):
        verbose_name = _("User promocode")
        verbose_name_plural = _("User promocodes")

    def update_used(self, new_used: int) -> None:
        self.used = new_used


class User(AbstractUser, PermissionsMixin, DefaultModel):
    tg_id = models.BigIntegerField(primary_key=True, unique=True, verbose_name=_("Telegram ID"))

    tg_username = models.CharField(max_length=150, null=True, blank=True, verbose_name=_("Telegram username"))
    first_name = models.CharField(max_length=150, null=True, blank=True, verbose_name=_("First name"))  # type: ignore[assignment]
    last_name = models.CharField(max_length=150, null=True, blank=True, verbose_name=_("Last name"))  # type: ignore[assignment]

    photo = models.ImageField(
        upload_to="avatars/", null=True, blank=True, storage=hashed_storage, verbose_name=_("Photo")
    )

    is_staff = models.BooleanField(default=False, verbose_name=_("Staff status"))
    is_superuser = models.BooleanField(default=False, verbose_name=_("Superuser status"))

    USERNAME_FIELD = "tg_id"
    username = None  # type: ignore[assignment]

    REQUIRED_FIELDS: list[str] = []  # type: ignore[misc]

    objects = CustomUserManager()  # type: ignore[assignment, misc]

    class Meta(DefaultModel.Meta):
        db_table = "auth_user"
        verbose_name = _("User")
        verbose_name_plural = _("Users")

    def update_base_parameters(self, tg_username: str, first_name: str, last_name: str) -> list[str]:
        self.tg_username = tg_username
        self.first_name = first_name
        self.last_name = last_name

        return ["tg_username", "first_name", "last_name"]

    def save_new_user_avatar(self, filename: str, avatar_file: ContentFile) -> None:
        if self.photo:
            self.photo.delete(save=False)
        self.photo.save(name=filename, content=avatar_file, save=False)

    def promote_superuser(self, password: str) -> list[str]:
        self.is_superuser = True
        self.is_staff = True
        self.set_password(password)
        return ["is_superuser", "is_staff", "password"]

    def init_settings(self) -> UserSettingsData:
        return UserSettingsData(user=self)

    def prepare_user_promocode(self, promocode: "PromoCode") -> UserPromocode:
        return UserPromocode(user=self, promocode=promocode)

    def make_delivery_address_current(self, address_id: int) -> list[str]:
        """
        This aggregate method unsets all other addresses and sets the target to current.

        WARNING: This iterates over `self.delivery_data.all()`. To prevent N+1 queries,
        the Use Case MUST prefetch `delivery_data` when retrieving the user aggregate.
        """
        target_address = next((addr for addr in self.delivery_data.all() if addr.id == address_id), None)
        if not target_address:
            raise ValueError(f"Delivery address with ID {address_id} not found in user aggregate.")

        for address in self.delivery_data.all():
            if address.is_current and address.id != address_id:
                address.unset_current()

        target_address.mark_as_current()

        return ["is_current"]

    def get_username(self) -> str:
        return str(getattr(self, self.USERNAME_FIELD))

    def __str__(self) -> str:
        username = getattr(self, "tg_username", None)
        if username:
            return f"@{username}"
        return str(getattr(self, self.USERNAME_FIELD))
