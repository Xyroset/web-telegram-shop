import logging

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler

import apps.basket.domain.exceptions as basket_e
import apps.catalog.domain.exceptions as catalog_e
import apps.delivery.domain.exceptions as delivery_e
import apps.notifications.domain.exceptions as notify_e
import apps.orders.domain.exceptions as order_e
import apps.payments.domain.exceptions as payment_e
import apps.support.domain.exceptions as support_e
import apps.telegram.domain.exceptions as telegram_e
import apps.users.domain.exceptions as user_e

logger = logging.getLogger(__name__)


class BaseException(Exception):
    pass


class CoreObjectNotFoundError(BaseException):
    pass


class CoreMultipleObjectsFoundError(BaseException):
    pass


class CoreRequiredFiltersError(BaseException):
    pass


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if response is not None:
        return response

    exception_map = {
        CoreObjectNotFoundError: (status.HTTP_404_NOT_FOUND, "Object not found!"),
        CoreMultipleObjectsFoundError: (status.HTTP_409_CONFLICT, "Expected 1 object, but found multiple!"),
        CoreRequiredFiltersError: (status.HTTP_400_BAD_REQUEST, "At least one filter parameter must be provided"),
        catalog_e.CatalogProductListEmptyError: (status.HTTP_404_NOT_FOUND, "Catalog is empty!"),
        catalog_e.CatalogFavoriteItemExistError: (status.HTTP_400_BAD_REQUEST, "Favorite item is exist!"),
        catalog_e.CatalogInvalidStockOperationError: (
            status.HTTP_400_BAD_REQUEST,
            "Quantity must be greater than zero.",
        ),
        catalog_e.CatalogOutOfStockError: (status.HTTP_409_CONFLICT, "Not enough stock available!"),
        catalog_e.CatalogStockInconsistencyError: (status.HTTP_409_CONFLICT, "Stock data is inconsistent!"),
        catalog_e.CatalogDigitalAssetAlreadyUsedError: (
            status.HTTP_409_CONFLICT,
            "This digital asset is already allocated.",
        ),
        catalog_e.CatalogDigitalAssetConflictError: (
            status.HTTP_409_CONFLICT,
            "Cannot release an asset that is not used.",
        ),
        catalog_e.CatalogDigitalAssetOutOfStockError: (status.HTTP_409_CONFLICT, "Not enough stock available"),
        catalog_e.CatalogProductNotPurchasedError: (
            status.HTTP_409_CONFLICT,
            "You can only review products you have purchased!",
        ),
        catalog_e.CatalogReviewAlreadyExistsError: (
            status.HTTP_409_CONFLICT,
            "You have already reviewed this product!",
        ),
        basket_e.BasketItemLimitError: (status.HTTP_400_BAD_REQUEST, "Limit on the basket item!"),
        delivery_e.DeliveryConflictDataError: (status.HTTP_409_CONFLICT, "Delivery state conflict!"),
        delivery_e.DeliveryInvalidDataError: (status.HTTP_400_BAD_REQUEST, "Delivery data is invalid!"),
        delivery_e.DeliveryUnsupportedDestinationError: (
            status.HTTP_400_BAD_REQUEST,
            "Unsupported destination or region code",
        ),
        notify_e.NotificationProvidersNotFound: (
            status.HTTP_404_NOT_FOUND,
            "No active notification providers configured. Skipping alerts.",
        ),
        notify_e.NotificationProviderRunTimeError: (
            status.HTTP_400_BAD_REQUEST,
            "Notification dispatch failed for all providers!",
        ),
        notify_e.NotificationEmailError: (status.HTTP_502_BAD_GATEWAY, "Failed to send Email message!"),
        notify_e.NotificationTelegramError: (status.HTTP_502_BAD_GATEWAY, "Failed to send Telegram message!"),
        notify_e.NotificationWebhookError: (status.HTTP_502_BAD_GATEWAY, "Failed to send Webhook message!"),
        order_e.OrderBasketEmptyError: (status.HTTP_404_NOT_FOUND, "Basket is empty!"),
        order_e.OrderPendingLimitExceededError: (status.HTTP_429_TOO_MANY_REQUESTS, "Too many pending orders!"),
        order_e.OrderNotFoundError: (status.HTTP_404_NOT_FOUND, "Order not found!"),
        order_e.OrderStatusInvalidError: (status.HTTP_400_BAD_REQUEST, "Order is not pending status!"),
        order_e.OrderListEmptyError: (status.HTTP_404_NOT_FOUND, "No orders found!"),
        order_e.OrderConflictDataError: (status.HTTP_409_CONFLICT, "Conflict order data!"),
        order_e.PromoCodeAlreadyUsedError: (status.HTTP_400_BAD_REQUEST, "Promo code already used by this user!"),
        order_e.PromoCodeExpiredError: (status.HTTP_400_BAD_REQUEST, "Promo code expired!"),
        order_e.PromoCodeInactiveError: (status.HTTP_400_BAD_REQUEST, "Promo code is inactive!"),
        order_e.PromoCodeLimitReachedError: (status.HTTP_400_BAD_REQUEST, "Promo code usage limit reached!"),
        order_e.PromoCodeNotYetValidError: (status.HTTP_400_BAD_REQUEST, "Promo code is not yet valid!"),
        order_e.PromoCodeMinAmountError: (status.HTTP_400_BAD_REQUEST, "Promo code min order amount not met!"),
        payment_e.PaymentGatewayNotFoundError: (status.HTTP_404_NOT_FOUND, "API for payments gateway not found!"),
        payment_e.PaymentGatewayUnavailableError: (status.HTTP_504_GATEWAY_TIMEOUT, "API gateway is temporarily down!"),
        payment_e.PaymentGatewayBadRequestError: (status.HTTP_400_BAD_REQUEST, "Bad request for API payment!"),
        payment_e.PaymentConflictDataError: (status.HTTP_409_CONFLICT, "Conflict transaction data!"),
        payment_e.PaymentUnsupportedCurrencyNetworkError: (
            status.HTTP_400_BAD_REQUEST,
            "Unsupported currency or network!",
        ),
        support_e.SupportInvalidTicketStateError: (status.HTTP_409_CONFLICT, "Invalid ticket state!"),
        support_e.SupportTicketLimitExceededError: (status.HTTP_400_BAD_REQUEST, "Support ticket limit exceeded!"),
        telegram_e.TelegramAPIError: (status.HTTP_502_BAD_GATEWAY, "Telegram API Error!"),
        user_e.UserNotFoundError: (status.HTTP_404_NOT_FOUND, "User not found!"),
    }

    for exc_class, (status_code, default_message) in exception_map.items():
        if isinstance(exc, exc_class):
            custom_message = str(exc)

            final_message = custom_message if custom_message else default_message
            logger.error(final_message)
            return Response({"message": final_message}, status=status_code)

    return None
