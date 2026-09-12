import logging
import os

from apps.core.config_manager import shop_config
from apps.payments.domain.exceptions import (
    PaymentGatewayNotFoundError,
    PaymentGatewayUnavailableError,
)
from apps.payments.domain.interfaces import PaymentGatewayProtocol
from apps.payments.gateways.providers import CryptoBotGateway, NOWPaymentsGateway

logger = logging.getLogger(__name__)


def get_payment_gateway(provider_name: str | None = None) -> PaymentGatewayProtocol:
    """
    Factory function to instantiate the requested payment gateway.

    Reads configuration from shop_config and injects the corresponding
    environment credentials into the concrete gateway provider.
    """
    provider = provider_name or shop_config.get("payments", "payments_settings.default_payment_gateway", "nowpayments")
    provider = str(provider).lower()

    if provider == "nowpayments":
        if not shop_config.get("payments", "payments_settings.providers.nowpayments.is_active", False):
            raise PaymentGatewayUnavailableError("Provider nowpayments is NOT active!")

        is_testnet = shop_config.get("payments", "payments_settings.providers.nowpayments.is_testnet", True)

        if is_testnet:
            api_key = os.getenv("SANDBOX_NOWPAYMENTS_API_KEY", "")
            ipn_secret = os.getenv("SANDBOX_NOWPAYMENTS_IPN_SECRET", "")
            base_url = os.getenv("SANDBOX_NOWPAYMENTS_API_URL", "https://api-sandbox.nowpayments.io/v1")
        else:
            api_key = os.getenv("NOWPAYMENTS_API_KEY", "")
            ipn_secret = os.getenv("NOWPAYMENTS_IPN_SECRET", "")
            base_url = os.getenv("NOWPAYMENTS_API_URL", "https://api.nowpayments.io/v1")

        return NOWPaymentsGateway(api_key=api_key, ipn_secret=ipn_secret, base_url=base_url)

    if provider == "cryptobot":
        if not shop_config.get("payments", "payments_settings.providers.cryptobot.is_active", False):
            raise PaymentGatewayUnavailableError("Provider cryptobot is NOT active!")

        is_testnet = shop_config.get("payments", "payments_settings.providers.cryptobot.is_testnet", True)

        if is_testnet:
            api_token = os.getenv("SANDBOX_CRYPTOBOT_API_KEY", "")
            base_url = os.getenv("SANDBOX_CRYPTOBOT_API_URL", "https://testnet-pay.crypt.bot/api")
        else:
            api_token = os.getenv("CRYPTOBOT_API_KEY", "")
            base_url = os.getenv("CRYPTOBOT_API_URL", "https://pay.crypt.bot/api")

        return CryptoBotGateway(api_token=api_token, base_url=base_url)

    logger.error(f"Attempted to initialize unsupported payment gateway: {provider}")
    raise PaymentGatewayNotFoundError(f"Unsupported payment gateway: '{provider}'.")
