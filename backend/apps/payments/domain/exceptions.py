class PaymentBaseError(Exception):
    pass


class PaymentGatewayUnavailableError(PaymentBaseError):
    pass


class PaymentGatewayBadRequestError(PaymentBaseError):
    pass


class PaymentGatewayNotFoundError(PaymentBaseError):
    pass


class PaymentConflictDataError(PaymentBaseError):
    pass


class PaymentUnsupportedCurrencyNetworkError(PaymentBaseError):
    pass
