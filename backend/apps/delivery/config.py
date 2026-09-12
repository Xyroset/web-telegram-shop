from decimal import Decimal

from apps.core.config_manager import shop_config
from apps.delivery.domain.interfaces import ShippingPricingStrategy
from apps.delivery.domain.services import DynamicZoneWeightCalculator


def get_active_pricing_strategy() -> ShippingPricingStrategy:
    """
    Factory function to instantiate and return the active pricing strategy.
    """

    base_rate = shop_config.get("delivery", "delivery_settings.base_rate", 0.00)
    rate_per_kg = shop_config.get("delivery", "delivery_settings.rate_per_kg", 0.00)
    free_threshold = shop_config.get("delivery", "delivery_settings.free_shipping_threshold", 0.00)
    max_multiplier = shop_config.get("delivery", "delivery_settings.max_multiplier_free_shipping_threshold", 0.00)
    default_multiplier = shop_config.get("delivery", "delivery_settings.default_multiplier", 1.0)

    zone_multipliers = shop_config.get("delivery", "zone_multipliers", {})

    return DynamicZoneWeightCalculator(
        base_rate=Decimal(str(base_rate)),
        rate_per_kg=Decimal(str(rate_per_kg)),
        free_threshold=Decimal(str(free_threshold)),
        max_multiplier_free_shipping_threshold=Decimal(str(max_multiplier)),
        zone_multipliers=zone_multipliers,
        default_multiplier=Decimal(str(default_multiplier)),
    )
