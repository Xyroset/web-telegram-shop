class BaseSupportError(Exception):
    pass


class SupportInvalidTicketStateError(BaseSupportError):
    pass


class SupportTicketLimitExceededError(BaseSupportError):
    pass
