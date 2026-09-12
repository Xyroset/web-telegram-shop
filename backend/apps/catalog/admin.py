import itertools
import json
from collections import defaultdict
from collections.abc import Mapping, Sequence
from typing import Any

from django import forms
from django.contrib import admin, messages
from django.core.exceptions import ValidationError
from django.db.models import QuerySet
from django.http import HttpRequest, HttpResponseRedirect
from django.urls import reverse
from django.utils.functional import cached_property
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from unfold.admin import ModelAdmin, StackedInline, TabularInline
from unfold.decorators import action

from apps.catalog.models import (
    Category,
    DigitalAsset,
    Photo,
    Product,
    ProductVariant,
    Review,
    ReviewPhoto,
    Tag,
)
from apps.catalog.repo import DigitalAssetRepository, ProductRepository
from apps.catalog.usecases import (
    BulkCloneProductVariantCase,
    BulkCreateDigitalAssetsCase,
    BulkDeleteDigitalAssetsCase,
    SyncDigitalVariantsStockCase,
)


class PhotoInline(TabularInline):
    model = Photo
    fields = ["image", "ordering"]
    extra = 1
    ordering = ["ordering"]


class ReviewPhotoInline(TabularInline):
    model = ReviewPhoto
    extra = 1
    can_delete = False
    readonly_fields = ["image", "is_active"]

    def has_add_permission(self, request: HttpRequest, obj: ReviewPhoto | None = None) -> bool:
        return False


class ProductVariantAdminForm(forms.ModelForm):
    bulk_keys = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 5, "placeholder": _("Paste keys here, one per line...")}),
        required=False,
        help_text=_("Paste new keys here. They will be processed and saved as Digital Assets upon saving the form."),
        label=_("Bulk keys"),
    )

    matrix_combinations = forms.CharField(
        widget=forms.Textarea(
            attrs={
                "rows": 6,
                "placeholder": _("Size: S, M, L\nColor: Black, Gray\nStyle: Oversize, Fit"),
            }
        ),
        required=False,
        help_text=_(
            "Generate variations automatically. Use format 'Attribute: val1, val2'. Each line creates a new dimension."
        ),
        label=_("Matrix combination"),
    )

    class Meta:
        model = ProductVariant
        fields = "__all__"

    def clean_matrix_combinations(self) -> list[dict[str, Any]] | None:
        data = self.cleaned_data.get("matrix_combinations")
        if not data:
            return None

        axes = []
        for line in str(data).strip().split("\n"):
            if not line.strip():
                continue
            if ":" not in line:
                raise ValidationError(_("Invalid format. Line '%(line)s' is missing a colon (:).") % {"line": line})

            key, raw_values = line.split(":", 1)
            key = key.strip().upper()
            values = [v.strip().upper() for v in raw_values.split(",") if v.strip().upper()]

            if not values:
                raise ValidationError(_("No values provided for attribute '%(key)s'.") % {"key": key})

            axes.append((key, values))

        if not axes:
            return None

        base_title = self.cleaned_data.get("title", "")
        base_title = str(base_title).split(" / ")[0].strip()

        base_metadata = self.cleaned_data.get("metadata") or {}

        keys = [axis[0] for axis in axes]
        value_lists = [axis[1] for axis in axes]

        mutations: list[dict[str, Any]] = []
        for combo in itertools.product(*value_lists):
            new_metadata = dict(base_metadata)
            new_metadata.update(dict(zip(keys, combo)))

            suffix = " / ".join(combo)
            new_title = f"{base_title} / {suffix}"

            mutations.append({"title": new_title, "metadata": new_metadata})

        return mutations


def parse_attribute_lines(raw: str) -> list[dict[str, str]]:
    lines = [line.strip() for line in raw.splitlines() if line.strip()]
    result: list[dict[str, str]] = []

    for line in lines:
        if ":" in line:
            label, value = line.split(":", 1)
            result.append({"label": label.strip(), "value": value.strip()})
            continue
        if " - " in line:
            label, value = line.split(" - ", 1)
            result.append({"label": label.strip(), "value": value.strip()})
            continue

        result.append({"label": "", "value": line})

    return result


def format_attributes_for_admin(value: Any) -> str:
    if value is None:
        return ""

    if isinstance(value, dict):
        return "\n".join(f"{key}: {val}" for key, val in value.items())

    if isinstance(value, list):
        lines = []
        for entry in value:
            if isinstance(entry, dict):
                label = str(entry.get("label") or entry.get("name") or "").strip()
                val = str(entry.get("value") or "").strip()
                if label:
                    lines.append(f"{label}: {val}")
                elif val:
                    lines.append(val)
                continue
            lines.append(str(entry))
        return "\n".join(lines)

    return str(value)


class ProductAdminForm(forms.ModelForm):
    attributes = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 6, "placeholder": _("Material: Cotton\nColor: Black\nWeight: 500g")}),
        required=False,
        help_text=_("One per line 'Label: Value'. JSON object/array is also accepted."),
        label=_("Attributes"),
    )

    class Meta:
        model = Product
        fields = "__all__"

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.attributes:
            self.initial["attributes"] = format_attributes_for_admin(self.instance.attributes)

    def clean_attributes(self) -> Mapping[str, Any] | Sequence[Mapping[str, str]]:
        raw = self.cleaned_data.get("attributes")
        if raw is None:
            return {}
        text = str(raw).strip()
        if not text:
            return {}

        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            return parse_attribute_lines(text)

        if isinstance(parsed, (dict, list)):
            return parsed

        return parse_attribute_lines(str(parsed))


@admin.register(ProductVariant)
class ProductVariantAdmin(ModelAdmin):
    form = ProductVariantAdminForm
    list_display = ["id", "title", "product", "price", "is_active", "available_stock", "reserved_stock"]
    list_editable = ["is_active"]
    search_fields = ["title", "product__name"]
    list_filter = ["tags", "is_active"]

    readonly_fields = ["id", "reserved_stock", "task_id", "created_at", "updated_at"]

    actions_list = ["sync_all_digital_stock_action"]

    @cached_property
    def _digitalassets_usecase(self) -> BulkCreateDigitalAssetsCase:
        return BulkCreateDigitalAssetsCase(
            digital_asset_repo=DigitalAssetRepository(), product_repo=ProductRepository()
        )

    @cached_property
    def _clone_usecase(self) -> BulkCloneProductVariantCase:
        return BulkCloneProductVariantCase(product_repo=ProductRepository())

    def save_model(self, request: HttpRequest, obj: ProductVariant, form: forms.ModelForm, change: bool) -> None:
        mutations = form.cleaned_data.get("matrix_combinations")

        if mutations:
            first_mutation = mutations.pop(0)
            obj.title = first_mutation["title"]
            obj.metadata = first_mutation["metadata"]

        super().save_model(request, obj, form, change)

        raw_keys_text = form.cleaned_data.get("bulk_keys")
        if raw_keys_text:
            keys_list = str(raw_keys_text).split("\n")
            added_count = self._digitalassets_usecase.execute(variant=obj, raw_keys=keys_list)
            if added_count > 0:
                self.message_user(request, _("Successfully added %(count)d digital assets.") % {"count": added_count})

        if mutations and change:
            cloned_count = self._clone_usecase.execute(base_variant=obj, mutations=mutations)
            if cloned_count > 0:
                self.message_user(
                    request,
                    _("Matrix generated! Adapted base variant and cloned %(count)d new variants.")
                    % {"count": cloned_count},
                )

    def get_readonly_fields(self, request: HttpRequest, obj: ProductVariant | None = None) -> list[str]:
        readonly_fields = list(super().get_readonly_fields(request, obj))
        if obj and obj.is_digital:
            if "available_stock" not in readonly_fields:
                readonly_fields.append("available_stock")
        return readonly_fields

    @action(description=_("Sync All Digital Stock"))
    def sync_all_digital_stock_action(self, request: HttpRequest) -> HttpResponseRedirect:
        """
        Global admin action to synchronize available_stock for all digital variants.
        Acts purely as a controller: assembles dependencies and calls the Use Case.
        """
        product_repo = ProductRepository()
        digital_asset_repo = DigitalAssetRepository()

        usecase = SyncDigitalVariantsStockCase(product_repo=product_repo, digital_asset_repo=digital_asset_repo)

        try:
            updated_count = usecase.execute()
            self.message_user(
                request,
                _("Successfully synchronized stock for %(count)d digital variants.") % {"count": updated_count},
                level=messages.SUCCESS,
            )
        except Exception as exc:
            self.message_user(
                request,
                _("Failed to synchronize digital stock. System error: %(error)s") % {"error": exc},
                level=messages.ERROR,
            )

        referer = request.META.get("HTTP_REFERER")
        fallback_url = reverse("admin:catalog_productvariant_changelist")
        return HttpResponseRedirect(referer or fallback_url)


class ProductVariantInline(StackedInline):
    model = ProductVariant
    extra = 0
    fields = [
        "is_active",
        "title",
        "badge",
        "image",
        "price",
        "old_price",
        "discount_expires_at",
        "available_stock",
        "reserved_stock",
        "tags",
        "specific_description",
        "weight_kg",
        "length_cm",
        "width_cm",
        "height_cm",
        "metadata",
        "manage_variant_link",
    ]
    readonly_fields = ["reserved_stock", "manage_variant_link"]

    @admin.display(description=_("Detail settings"))
    def manage_variant_link(self, obj: ProductVariant) -> str:
        if obj.pk:
            url = reverse("admin:catalog_productvariant_change", args=[obj.pk])
            return format_html(
                f'<a href="{{}}" class="font-medium text-primary-600 hover:text-primary-500">{_("Manage detail")}</a>',
                url,
            )
        return str(_("Save product to add product variant"))

    def get_readonly_fields(self, request: HttpRequest, obj: Product | None = None) -> list[str]:
        readonly_fields = list(super().get_readonly_fields(request, obj))

        if obj and obj.is_instant_delivery:
            if "available_stock" not in readonly_fields:
                readonly_fields.append("available_stock")
        return readonly_fields


@admin.register(Product)
class ProductAdmin(ModelAdmin):
    form = ProductAdminForm
    list_display = ["id", "name", "category", "is_active"]
    list_editable = ["is_active"]
    list_display_links = ["id", "name"]
    search_fields = ["name", "base_description"]
    list_filter = ["category", "is_active"]
    inlines = [PhotoInline, ProductVariantInline]


@admin.register(Review)
class ReviewAdmin(ModelAdmin):
    list_display = ["id", "user", "product", "rating", "created_at"]
    list_display_links = ["id", "user"]
    list_filter = ["rating"]
    search_fields = ["user__tg_id", "user__tg_username", "product__name", "text"]
    inlines = [ReviewPhotoInline]

    readonly_fields = [
        "id",
        "user",
        "product",
        "rating",
        "text",
        "admin_reply_created_at",
        "is_anonymous",
        "created_at",
        "updated_at",
    ]

    fieldsets = (
        (_("User Review"), {"fields": ("id", "user", "product", "rating", "text", "is_anonymous")}),
        (_("Admin Response"), {"fields": ("admin_reply_text", "admin_reply_created_at")}),
        (_("Timestamps"), {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )

    def save_model(self, request: HttpRequest, obj: Review, form: forms.ModelForm, change: bool) -> None:
        if change and "admin_reply_text" in form.changed_data and obj.admin_reply_text:
            obj.add_admin_reply(text=obj.admin_reply_text)
        super().save_model(request, obj, form, change)


@admin.register(Category)
class CategoryAdmin(ModelAdmin):
    list_display = ["id", "name"]
    list_display_links = ["id", "name"]
    search_fields = ["name"]


@admin.register(Tag)
class TagAdmin(ModelAdmin):
    list_display = ["id", "name"]
    list_display_links = ["id", "name"]


@admin.register(DigitalAsset)
class DigitalAssetAdmin(ModelAdmin):
    list_display = ["id", "variant", "content", "is_used", "order_item"]
    list_display_links = ["id", "content"]
    list_filter = ["is_used", "variant"]
    search_fields = ["content"]

    readonly_fields = ["is_used", "order_item", "created_at", "updated_at"]

    @cached_property
    def _delete_usecase(self) -> BulkDeleteDigitalAssetsCase:
        return BulkDeleteDigitalAssetsCase(
            digital_asset_repo=DigitalAssetRepository(), product_repo=ProductRepository()
        )

    def delete_model(self, request: HttpRequest, obj: DigitalAsset) -> None:
        """
        Overrides single object deletion to route through our Use Case.
        """
        self._delete_usecase.execute(variant=obj.variant, asset_ids=[str(obj.id)])

    def delete_queryset(self, request: HttpRequest, queryset: QuerySet[DigitalAsset]) -> None:
        """
        Overrides bulk deletion via Action menu to route through our Use Case.
        Groups assets by variant to ensure atomic stock updates per variant.
        """
        queryset = queryset.select_related("variant")

        variant_assets: dict[ProductVariant, list[str]] = defaultdict(list)
        for asset in queryset:
            variant_assets[asset.variant].append(str(asset.id))

        for variant, asset_ids in variant_assets.items():
            self._delete_usecase.execute(variant=variant, asset_ids=asset_ids)
