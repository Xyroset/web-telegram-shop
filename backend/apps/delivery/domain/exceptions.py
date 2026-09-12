class DeliveryBaseError(Exception):
    pass


class DeliveryConflictDataError(DeliveryBaseError):
    pass


class DeliveryInvalidDataError(DeliveryBaseError):
    pass


class DeliveryUnsupportedDestinationError(DeliveryBaseError):
    pass
