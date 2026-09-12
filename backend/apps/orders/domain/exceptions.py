# * Order
class OrderBaseException(Exception):
    pass


class OrderBasketEmptyError(OrderBaseException):
    pass


class OrderStatusInvalidError(OrderBaseException):
    pass


class OrderNotFoundError(OrderBaseException):
    pass


class OrderPendingLimitExceededError(OrderBaseException):
    pass


class OrderListEmptyError(OrderBaseException):
    pass


class OrderConflictDataError(OrderBaseException):
    pass


# * PromoCode
class PromoCodeBaseException(Exception):
    pass


class PromoCodeInactiveError(PromoCodeBaseException):
    pass


class PromoCodeLimitReachedError(PromoCodeBaseException):
    pass


class PromoCodeNotYetValidError(PromoCodeBaseException):
    pass


class PromoCodeExpiredError(PromoCodeBaseException):
    pass


class PromoCodeAlreadyUsedError(PromoCodeBaseException):
    pass


class PromoCodeMinAmountError(PromoCodeBaseException):
    pass
