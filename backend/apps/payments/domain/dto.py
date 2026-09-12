import uuid
from dataclasses import dataclass
from typing import Any


@dataclass
class InputInvoiceDTO:
    order_id: uuid.UUID
    network: str | None = None
    currency: str | None = None


@dataclass
class InvoiceDTO:
    invoice_id: str
    pay_url: str
    currency: str
    pay_address: str | None = None


@dataclass
class PaymentTransactionDTO:
    invoice_id: str | None = None
    receiver_address: str | None = None
    sender_address: str | None = None
    tx_hash: str | None = None
    raw_response: dict[str, Any] | None = None
