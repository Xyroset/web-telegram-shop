from apps.core.repo import BaseRepository
from apps.delivery.models import Delivery


class DeliveryRepository(BaseRepository[Delivery]):
    def __init__(self):
        super().__init__(model_class=Delivery)
