class NotificationBaseError(Exception):
    pass


class NotificationEmailError(NotificationBaseError):
    pass


class NotificationTelegramError(NotificationBaseError):
    pass

class NotificationWebhookError(NotificationBaseError):
    pass


class NotificationProvidersNotFound(NotificationBaseError):
    pass


class NotificationProviderRunTimeError(NotificationBaseError):
    pass
