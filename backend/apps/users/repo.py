from apps.core.domain.exceptions import CoreObjectNotFoundError
from apps.core.repo import BaseRepository
from apps.orders.models import PromoCode
from apps.users.models import User, UserDeliveryData, UserPromocode, UserSettingsData


class UserRepository(BaseRepository[User]):
    def __init__(self):
        super().__init__(model_class=User)

    def get_user_promocode(self, user: User, promocode: PromoCode) -> UserPromocode:
        try:
            return UserPromocode.objects.get(user=user, promocode=promocode)
        except UserPromocode.DoesNotExist:
            raise CoreObjectNotFoundError("User Promocode not found.")

    def save_user_promocode(self, user_promocode: UserPromocode) -> None:
        user_promocode.save()

    def delete_user_promocode(self, user_promocode: UserPromocode) -> None:
        user_promocode.delete()


class UserSettingsDataRepository(BaseRepository[UserSettingsData]):
    def __init__(self):
        super().__init__(model_class=UserSettingsData)


class UserDeliveryDataRepository(BaseRepository[UserDeliveryData]):
    def __init__(self):
        super().__init__(model_class=UserDeliveryData)
