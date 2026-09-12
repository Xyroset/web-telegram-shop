import uuid
from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.models import DefaultModel
from apps.payments.domain.dto import PaymentTransactionDTO
from apps.payments.domain.exceptions import PaymentConflictDataError
from apps.payments.domain.value_objects import CryptoMoney


class PaymentTransaction(DefaultModel):
    class Status(models.TextChoices):
        PENDING = "pending", _("Waiting for payment")
        PAID = "paid", _("Successfully paid")
        WRONG_AMOUNT = "wrong_amount", _("Paid wrong amount")
        PARTIALLY_PAID = "partially_paid", _("Partially paid")
        EXPIRED = "expired", _("Invoice expired")
        CANCELLED = "cancelled", _("Cancelled")
        FAILED = "failed", _("Failed")
        REFUNDED = "refunded", _("Refunded")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    order = models.ForeignKey(
        "orders.Order",
        on_delete=models.PROTECT,
        related_name="transactions",
        verbose_name=_("Order"),
    )
    invoice_id = models.CharField(max_length=255, null=True, blank=True, verbose_name=_("Invoice ID"))

    payment_currency = models.CharField(max_length=10, verbose_name=_("Payment currency"))
    network = models.CharField(max_length=50, verbose_name=_("Network"))

    target_amount_usd = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
        verbose_name=_("Target amount USD"),
    )

    amount_crypto = models.DecimalField(
        max_digits=20,
        decimal_places=8,
        default=Decimal("0.00000000"),
        validators=[MinValueValidator(Decimal("0.00000000"))],
        verbose_name=_("Target crypto amount"),
    )
    current_amount_crypto = models.DecimalField(
        max_digits=20,
        decimal_places=8,
        default=Decimal("0.00000000"),
        validators=[MinValueValidator(Decimal("0.00000000"))],
        verbose_name=_("Current crypto amount"),
    )

    receiver_address = models.CharField(max_length=300, null=True, blank=True, verbose_name=_("Receiver address"))
    sender_address = models.CharField(max_length=300, null=True, blank=True, verbose_name=_("Sender address"))
    tx_hash = models.CharField(max_length=255, null=True, blank=True, verbose_name=_("Transaction hash"))

    state = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        verbose_name=_("State"),
    )
    raw_response = models.JSONField(null=True, blank=True, verbose_name=_("Raw gateway response"))
    task_id = models.UUIDField(null=True, blank=True, verbose_name=_("Task ID"))

    class Meta(DefaultModel.Meta):
        verbose_name = _("Payment transaction")
        verbose_name_plural = _("Payment transactions")
        indexes = DefaultModel.Meta.indexes + [
            models.Index(
                fields=["state"],
                condition=~models.Q(state__in=["paid", "expired", "cancelled"]),
                name="idx_active_transactions",
            ),
        ]

    @property
    def captured_amount_usd(self) -> Decimal:
        """
        Calculates the fiat (USD) value actually captured by this transaction.
        Uses the exchange rate implicitly locked at the time of transaction creation.
        """
        if self.current_amount_crypto == Decimal("0.00"):
            return Decimal("0.00")

        if self.state == self.Status.PAID:
            return self.target_amount_usd

        if self.amount_crypto == Decimal("0.00"):
            return Decimal("0.00")

        proportion = self.current_amount_crypto / self.amount_crypto
        captured = self.target_amount_usd * proportion

        captured = min(captured, self.target_amount_usd)

        return captured.quantize(Decimal("0.01"))

    @property
    def target_crypto_money(self) -> CryptoMoney:
        return CryptoMoney(
            amount=self.amount_crypto,
            currency=self.payment_currency,
            network=self.network,
        )

    @property
    def current_crypto_money(self) -> CryptoMoney:
        return CryptoMoney(
            amount=self.current_amount_crypto,
            currency=self.payment_currency,
            network=self.network,
        )

    def update_payment(self, dto: PaymentTransactionDTO) -> list[str]:
        updated_fields: list[str] = []

        if dto.invoice_id is not None:
            self.invoice_id = dto.invoice_id
            updated_fields.append("invoice_id")

        if dto.receiver_address is not None:
            self.receiver_address = dto.receiver_address
            updated_fields.append("receiver_address")

        if dto.sender_address is not None:
            self.sender_address = dto.sender_address
            updated_fields.append("sender_address")

        if dto.tx_hash is not None:
            self.tx_hash = dto.tx_hash
            updated_fields.append("tx_hash")

        if dto.raw_response is not None:
            self.raw_response = dto.raw_response
            updated_fields.append("raw_response")

        return updated_fields

    def register_funds(self, received_amount: Decimal) -> list[str]:
        """
        Business logic to process incoming funds.
        Handles standard payments AND late payments after expiration.
        """
        if self.state in [self.Status.PAID, self.Status.FAILED]:
            raise PaymentConflictDataError(
                f"Cannot register funds for a closed transaction. Current status: {self.state}"
            )

        self.current_amount_crypto += received_amount

        if self.state in [self.Status.EXPIRED, self.Status.CANCELLED]:
            self.state = self.Status.WRONG_AMOUNT
            return ["current_amount_crypto", "state"]

        if self.current_amount_crypto == self.amount_crypto:
            self.state = self.Status.PAID
        elif self.current_amount_crypto < self.amount_crypto:
            self.state = self.Status.PARTIALLY_PAID
        else:
            self.state = self.Status.WRONG_AMOUNT

        return ["current_amount_crypto", "state"]

    def mark_as_expired(self) -> list[str]:
        if self.state == self.Status.PENDING and self.current_amount_crypto == Decimal("0.00"):
            self.state = self.Status.EXPIRED
            return ["state"]

        if self.state == self.Status.PARTIALLY_PAID or self.current_amount_crypto > Decimal("0.00"):
            self.state = self.Status.WRONG_AMOUNT
            return ["state"]

        raise PaymentConflictDataError(f"Cannot expire transaction in current status: {self.state}")

    def mark_as_cancelled(self) -> list[str]:
        if self.state == self.Status.PENDING and self.current_amount_crypto == Decimal("0.00"):
            self.state = self.Status.CANCELLED
            return ["state"]

        if self.state == self.Status.PARTIALLY_PAID or self.current_amount_crypto > Decimal("0.00"):
            self.state = self.Status.WRONG_AMOUNT
            return ["state"]

        raise PaymentConflictDataError(f"Cannot cancel transaction in current status: {self.state}")

    def mark_as_failed(self) -> list[str]:
        if self.state in [self.Status.PENDING, self.Status.EXPIRED]:
            self.state = self.Status.FAILED
            return ["state"]
        raise PaymentConflictDataError(f"Only PENDING, EXPIRED transaction can be failed. Current status: {self.state}")

    def mark_as_wrong_amount(self) -> list[str]:
        if self.state == self.Status.PARTIALLY_PAID or self.current_amount_crypto > Decimal("0.00"):
            self.state = self.Status.WRONG_AMOUNT
            return ["state"]
        raise PaymentConflictDataError(
            f"Only PARTIALLY_PAID transaction can be wrong_amount. Current status: {self.state}"
        )

    def mark_as_refunded(self) -> list[str]:
        if self.state in [self.Status.PAID, self.Status.PARTIALLY_PAID, self.Status.WRONG_AMOUNT]:
            self.state = self.Status.REFUNDED
            return ["state"]

        raise PaymentConflictDataError(
            f"Only PAID, PARTIALLY_PAID or WRONG_AMOUNT transaction can be refunded. Current status: {self.state}"
        )

    def mark_as_paid(self) -> list[str]:
        self.state = self.Status.PAID
        return ["state"]

    def resolve_overpayment(self) -> list[str]:
        """
        Resolves a WRONG_AMOUNT state by transitioning to PAID.

        **Business Rules:**
        - Used exclusively when a customer overpays, the state gets stuck in WRONG_AMOUNT,
          and an admin manually refunds the excess crypto (change).
        - The remaining balance covers the target, meaning the transaction is effectively PAID.
        """
        if self.state == self.Status.WRONG_AMOUNT and self.current_amount_crypto >= self.amount_crypto:
            self.state = self.Status.PAID
            return ["state"]

        raise PaymentConflictDataError(
            f"Cannot resolve overpayment. State must be WRONG_AMOUNT and fully funded. Current: {self.state}"
        )

    def __str__(self) -> str:
        return f"Status - {self.state}; Target - {self.amount_crypto}; Paid - {self.current_amount_crypto}"
