from django.contrib import admin
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect
from django.utils.translation import gettext_lazy as _
from unfold.admin import ModelAdmin
from unfold.decorators import action

from apps.orders.repo import OrderRepository
from apps.payments.models import PaymentTransaction
from apps.payments.repo import PaymentTransactionRepository
from apps.payments.usecases import (
    CancelTransactionCase,
    RefundTransactionCase,
    ResolveOverpaymentCase,
)


@admin.register(PaymentTransaction)
class PaymentTransactionAdmin(ModelAdmin):
    list_display = ["id", "state", "amount_crypto", "current_amount_crypto", "created_at"]
    list_display_links = ["id", "state"]
    list_filter = ["state", "payment_currency", "network"]
    search_fields = ["id", "invoice_id", "tx_hash", "receiver_address", "sender_address"]

    readonly_fields = [
        "id",
        "order",
        "state",
        "invoice_id",
        "payment_currency",
        "network",
        "target_amount_usd",
        "amount_crypto",
        "current_amount_crypto",
        "receiver_address",
        "sender_address",
        "tx_hash",
        "raw_response",
        "created_at",
        "updated_at",
    ]

    fieldsets = (
        (_("Basic information"), {"fields": ("id", "order", "state", "target_amount_usd")}),
        (
            _("Crypto information"),
            {
                "fields": (
                    "invoice_id",
                    "payment_currency",
                    "network",
                    "amount_crypto",
                    "current_amount_crypto",
                    "receiver_address",
                    "sender_address",
                    "tx_hash",
                    "raw_response",
                )
            },
        ),
        (
            _("Timestamps"),
            {
                "fields": ("created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )

    actions_detail = ["cancel_transaction_action", "resolve_overpayment_action", "refund_transaction_action"]

    @action(description=_("Cancel Transaction"), url_path="cancel-transaction")
    def cancel_transaction_action(self, request: HttpRequest, object_id: str) -> HttpResponse:
        """
        Delegates the cancellation of a transaction to the CancelTransactionCase.
        Executes without user context to bypass ownership checks for admins.
        """
        usecase = CancelTransactionCase(payment_repo=PaymentTransactionRepository())

        try:
            usecase.execute(transaction_id=object_id)
            self.message_user(request, _("Transaction successfully cancelled."), level="SUCCESS")
        except Exception as exc:
            self.message_user(request, _("Error: %(error)s") % {"error": exc}, level="ERROR")

        return redirect(request.META.get("HTTP_REFERER", "."))

    @action(description=_("Resolve Overpayment (Keep Target, Refund Rest)"), url_path="resolve-overpayment")
    def resolve_overpayment_action(self, request: HttpRequest, object_id: str) -> HttpResponse:
        """
        Action to resolve a stuck WRONG_AMOUNT transaction after admin has manually
        returned the excess crypto to the customer. Delegates to ResolveOverpaymentCase.
        """
        usecase = ResolveOverpaymentCase(
            payment_repo=PaymentTransactionRepository(),
            order_repo=OrderRepository(),
        )

        try:
            usecase.execute(transaction_id=object_id)
            self.message_user(
                request, _("Overpayment successfully resolved. Transaction marked as PAID."), level="SUCCESS"
            )
        except Exception as exc:
            self.message_user(request, _("Error: ") + str(exc), level="ERROR")

        return redirect(request.META.get("HTTP_REFERER", "."))

    @action(description=_("Mark as Fully Refunded"), url_path="mark-refunded")
    def refund_transaction_action(self, request: HttpRequest, object_id: str) -> HttpResponse:
        """
        Action to mark the transaction as completely refunded.
        Delegates to RefundTransactionCase.
        """
        use_case = RefundTransactionCase(
            payment_repo=PaymentTransactionRepository(),
            order_repo=OrderRepository(),
        )

        try:
            use_case.execute(transaction_id=object_id)
            self.message_user(request, _("Transaction successfully marked as REFUNDED."), level="SUCCESS")
        except Exception as exc:
            self.message_user(request, _("Error: %(error)s") % {"error": exc}, level="ERROR")

        return redirect(request.META.get("HTTP_REFERER", "."))
