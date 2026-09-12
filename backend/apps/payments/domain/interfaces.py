from collections.abc import Mapping
from decimal import Decimal
from typing import Any, Protocol

from apps.payments.domain.dto import InvoiceDTO


class PaymentGatewayProtocol(Protocol):
    """
    Protocol defining the strict contract for all payment gateways.
    """

    def create_invoice(self, amount: Decimal, currency: str, network: str, order_id: str) -> InvoiceDTO: ...

    def verify_webhook(self, payload: Mapping[str, Any], signature: str) -> bool: ...

    def normalize_webhook_data(self, payload: Mapping[str, Any]) -> dict[str, Any]: ...
