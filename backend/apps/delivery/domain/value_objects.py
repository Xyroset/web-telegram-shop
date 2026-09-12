import re
from dataclasses import asdict, dataclass

from apps.delivery.domain.exceptions import DeliveryInvalidDataError


@dataclass(frozen=True)
class DeliveryDataVO:
    """
    Value Object representing snapshot delivery data.
    Ensures all fields are present and strings have valid formats.
    """

    full_name: str
    email: str
    phone: str
    zip_code: str
    address_line: str
    destination_code: str
    region_code: str | None = None

    def __post_init__(self) -> None:
        self._validate_empty(["full_name", "email", "phone", "zip_code", "address_line", "destination_code"])
        self._validate_email()
        self._validate_phone()

    def _validate_empty(self, fields: list[str]) -> None:
        for field in fields:
            val = getattr(self, field)
            if not val or not str(val).strip():
                raise DeliveryInvalidDataError(f"Field '{field}' cannot be empty.")

    def _validate_email(self) -> None:
        email_regex = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
        if not re.match(email_regex, self.email):
            raise DeliveryInvalidDataError(f"Invalid email format: {self.email}")

    def _validate_phone(self) -> None:
        phone_regex = r"^\+?[1-9]\d{7,14}$"
        if not re.match(phone_regex, self.phone):
            raise DeliveryInvalidDataError(f"Invalid phone format: {self.phone}")

    def to_dict(self) -> dict[str, str | None]:
        return asdict(self)
