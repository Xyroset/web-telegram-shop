import logging
import uuid
from decimal import Decimal
from typing import Any

from celery import current_app
from django.db import transaction as ts

from apps.catalog.repo import DigitalAssetRepository, ProductRepository
from apps.core.domain.exceptions import CoreObjectNotFoundError
from apps.delivery.repo import DeliveryRepository
from apps.orders.domain.services import DigitalAssetManagementService, StockManagementService
from apps.orders.models import Order
from apps.orders.repo import OrderRepository, PromoCodeRepository
from apps.payments.repo import PaymentTransactionRepository
from apps.users.models import User
from apps.users.repo import UserRepository

logger = logging.getLogger(__name__)


class CancelOrderCase:
    """
    Cancels an order initiated by the user.

    **Business Rules:**
    - Fails any active payment transactions and revokes their expiration tasks.
    - Checks for stuck captured funds. If funds exist, marks order as FAILED.
    - Releases physical and digital stock via Domain Services.
    - Rolls back promocode usage limits.
    - Cancels delivery tracking.

    **Required:**
    - Order must exist. Otherwise error — **CoreObjectNotFoundError**.
    - Order status must be **PENDING** to execute cancellation.
    """

    def __init__(
        self,
        order_repo: OrderRepository,
        user_repo: UserRepository,
        delivery_repo: DeliveryRepository,
        payment_repo: PaymentTransactionRepository,
        promocode_repo: PromoCodeRepository,
        product_repo: ProductRepository,
        digital_asset_repo: DigitalAssetRepository,
    ) -> None:
        self._order_repo = order_repo
        self._user_repo = user_repo
        self._delivery_repo = delivery_repo
        self._payment_repo = payment_repo
        self._promocode_repo = promocode_repo
        self._stock_service = StockManagementService(product_repo=product_repo)
        self._digital_asset_service = DigitalAssetManagementService(
            digital_asset_repo=digital_asset_repo,
            product_repo=product_repo,
        )

    def execute(self, order_id: uuid.UUID | str, user: User | None = None) -> None:
        with ts.atomic():
            filters: dict[str, Any] = {"id": order_id}
            if user:
                filters["user"] = user
            order = self._order_repo.get_for_update_by(**filters)

            if order.state != Order.Status.PENDING:
                logger.info(f"Order {order_id} cancellation skipped. State: {order.state}")
                return

            self._process_reversion(order=order, fallback_state=Order.Status.CANCELLED)

        if order.task_id:
            current_app.control.revoke(str(order.task_id), terminate=True)

    def _process_reversion(self, order: Order, fallback_state: str) -> None:
        active_tx = order.get_active_transaction()
        if active_tx:
            active_tx = self._payment_repo.get_for_update_by(id=active_tx.id)
            tx_updates = active_tx.mark_as_failed()
            self._payment_repo.save(instance=active_tx, update_fields=tx_updates)

            if active_tx.task_id:
                current_app.control.revoke(str(active_tx.task_id), terminate=True)

        paid_fiat = order.target_fiat_money.subtract(order.get_remaining_usd_balance())

        if paid_fiat.amount > Decimal("0.00"):
            order_updates = order.mark_as_failed()
            logger.error(f"Order {order.id} reverted but contains {paid_fiat.amount} USD of captured funds!")

            if active_tx:

                def dispatch_admin() -> None:
                    current_app.send_task(
                        "notifications.dispatch_admin_stuck_funds_transaction_notifications",
                        args=[str(active_tx.id)],
                    )

                ts.on_commit(dispatch_admin)
        else:
            if fallback_state == Order.Status.CANCELLED:
                order_updates = order.mark_as_cancelled()
            else:
                order_updates = order.mark_as_expired()

        self._order_repo.save(instance=order, update_fields=order_updates)

        try:
            delivery = self._delivery_repo.get_for_update_by(order=order)
            delivery_updates = delivery.mark_as_canceled()
            self._delivery_repo.save(instance=delivery, update_fields=delivery_updates)
        except CoreObjectNotFoundError:
            logger.warning(f"Delivery record not found for order {order.id} during reversion.")

        order_items = self._order_repo.get_order_items(order=order)
        physical_items = [item for item in order_items if not item.is_digital]
        digital_items = [item for item in order_items if item.is_digital]

        if digital_items:
            self._digital_asset_service.release_assets_and_stock(order_items=digital_items)
        if physical_items:
            self._stock_service.release_physical(order_items=physical_items)

        if order.promocode and order.user:
            promo = self._promocode_repo.get_for_update_by(id=order.promocode.id)
            promo_updates = promo.rollback_promocode_usage()
            self._promocode_repo.save(instance=promo, update_fields=promo_updates)

            try:
                user_promocode = self._user_repo.get_user_promocode(user=order.user, promocode=order.promocode)
                if user_promocode.used - 1 > 0:
                    user_promocode.update_used(new_used=user_promocode.used - 1)
                    self._user_repo.save_user_promocode(user_promocode=user_promocode)
                else:
                    self._user_repo.delete_user_promocode(user_promocode=user_promocode)
            except CoreObjectNotFoundError:
                return None


class ExpireOrderCase:
    """
    Expires an order automatically via Celery beat/countdown.

    **Business Rules:**
    - Identical logistics reversion to CancelOrderCase.
    - Transitions order to EXPIRED state instead of CANCELLED.

    **Required:**
    - Order must exist. Otherwise error — **CoreObjectNotFoundError**.
    - Order status must be **PENDING** to execute expiration.
    """

    def __init__(
        self,
        order_repo: OrderRepository,
        user_repo: UserRepository,
        delivery_repo: DeliveryRepository,
        payment_repo: PaymentTransactionRepository,
        promocode_repo: PromoCodeRepository,
        product_repo: ProductRepository,
        digital_asset_repo: DigitalAssetRepository,
    ) -> None:
        self._order_repo = order_repo
        self._user_repo = user_repo
        self._delivery_repo = delivery_repo
        self._payment_repo = payment_repo
        self._promocode_repo = promocode_repo
        self._stock_service = StockManagementService(product_repo=product_repo)
        self._digital_asset_service = DigitalAssetManagementService(
            digital_asset_repo=digital_asset_repo,
            product_repo=product_repo,
        )

    def execute(self, order_id: uuid.UUID | str) -> None:
        with ts.atomic():
            order = self._order_repo.get_for_update_by(id=order_id)

            if order.state != Order.Status.PENDING:
                logger.info(f"Order {order_id} expiration skipped. State: {order.state}")
                return

            self._process_reversion(order=order, fallback_state=Order.Status.EXPIRED)

        if order.task_id:
            current_app.control.revoke(str(order.task_id), terminate=True)

    def _process_reversion(self, order: Order, fallback_state: str) -> None:
        active_tx = order.get_active_transaction()
        if active_tx:
            active_tx = self._payment_repo.get_for_update_by(id=active_tx.id)
            tx_updates = active_tx.mark_as_failed()
            self._payment_repo.save(instance=active_tx, update_fields=tx_updates)

            if active_tx.task_id:
                current_app.control.revoke(str(active_tx.task_id), terminate=True)

        paid_fiat = order.target_fiat_money.subtract(order.get_remaining_usd_balance())

        if paid_fiat.amount > Decimal("0.00"):
            order_updates = order.mark_as_failed()
            logger.error(f"Order {order.id} reverted but contains {paid_fiat.amount} USD of captured funds!")

            if active_tx:

                def dispatch_admin() -> None:
                    current_app.send_task(
                        "notifications.dispatch_admin_stuck_funds_transaction_notifications",
                        args=[str(active_tx.id)],
                    )

                ts.on_commit(dispatch_admin)
        else:
            if fallback_state == Order.Status.CANCELLED:
                order_updates = order.mark_as_cancelled()
            else:
                order_updates = order.mark_as_expired()

        self._order_repo.save(instance=order, update_fields=order_updates)

        try:
            delivery = self._delivery_repo.get_for_update_by(order=order)
            delivery_updates = delivery.mark_as_canceled()
            self._delivery_repo.save(instance=delivery, update_fields=delivery_updates)
        except CoreObjectNotFoundError:
            logger.warning(f"Delivery record not found for order {order.id} during reversion.")

        order_items = self._order_repo.get_order_items(order=order)
        physical_items = [item for item in order_items if not item.is_digital]
        digital_items = [item for item in order_items if item.is_digital]

        if digital_items:
            self._digital_asset_service.release_assets_and_stock(order_items=digital_items)
        if physical_items:
            self._stock_service.release_physical(order_items=physical_items)

        if order.promocode and order.user:
            promo = self._promocode_repo.get_for_update_by(id=order.promocode.id)
            promo_updates = promo.rollback_promocode_usage()
            self._promocode_repo.save(instance=promo, update_fields=promo_updates)

            try:
                user_promocode = self._user_repo.get_user_promocode(user=order.user, promocode=order.promocode)
                if user_promocode.used - 1 > 0:
                    user_promocode.update_used(new_used=user_promocode.used - 1)
                    self._user_repo.save_user_promocode(user_promocode=user_promocode)
                else:
                    self._user_repo.delete_user_promocode(user_promocode=user_promocode)
            except CoreObjectNotFoundError:
                return None
