import uuid

from apps.core.domain.exceptions import CoreObjectNotFoundError
from apps.core.repo import BaseRepository
from apps.payments.models import PaymentTransaction


class PaymentTransactionRepository(BaseRepository[PaymentTransaction]):
    """
    Repository abstraction for isolating PaymentTransaction database operations.
    """

    def __init__(self) -> None:
        super().__init__(model_class=PaymentTransaction)

    def get_by_id_with_full_details(self, transaction_id: str | uuid.UUID) -> PaymentTransaction:
        """
        Fetch a payment transaction by ID with preloaded order, user, and delivery relations.
        """
        try:
            return self.model_class.objects.select_related(
                "order",
                "order__user",
                "order__delivery",
            ).get(id=transaction_id)
        except self.model_class.DoesNotExist:
            raise CoreObjectNotFoundError(f"Transaction not found! Transaction id: {transaction_id}")
