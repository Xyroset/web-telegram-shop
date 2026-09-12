from dataclasses import dataclass


@dataclass
class TelegramAuthDTO:
    tg_id: int
    tg_username: str
    first_name: str
    last_name: str
    default_language_code: str
    default_theme: str


@dataclass
class UserSettingsDataDTO:
    preferred_payment_currency: str | None = None
    preferred_network: str | None = None
    particles_style: str | None = None
    default_theme: str | None = None
    default_language_code: str | None = None
    custom_theme: str | None = None
    custom_language_code: str | None = None


@dataclass
class UserDeliveryDataDTO:
    full_name: str | None = None
    email: str | None = None
    phone: str | None = None
    address_line: str | None = None
    zip_code: str | None = None
    destination_code: str | None = None
    region_code: str | None = None
