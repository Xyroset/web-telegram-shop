from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from apps.users.models import User

if TYPE_CHECKING:
    from apps.orders.models import PromoCode


@dataclass
class CreateOrderDTO:
    user: User
    total_price: Decimal
    expire_task_id: uuid.UUID
    promocode: PromoCode | None = None
    delivery_data: dict | None = None


@dataclass(frozen=True)
class OrderDTO:
    payload_url: str | None = None
    promocode: PromoCode | None = None
    paid_at: datetime | None = None
    task_id: str | None = None
    metadata: dict[str, Any] | None = None


@dataclass(frozen=True)
class OrderItemDTO:
    variant_id: int
    quantity: int
    fixed_price: Decimal
    is_digital: bool
