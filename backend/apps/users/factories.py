import factory

from apps.users.models import User, UserDeliveryData, UserSettingsData


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User

    tg_id = factory.Sequence(lambda n: 100000000 + n)
    tg_username = factory.Sequence(lambda n: f"user_{n}")
    first_name = factory.Sequence(lambda n: f"Name_{n}")
    last_name = factory.Sequence(lambda n: f"Surname_{n}")
    is_staff = False
    is_superuser = False


class UserSettingsFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = UserSettingsData

    user = factory.SubFactory(UserFactory)
    preferred_payment_currency = "usdt"
    preferred_network = "trc20"
    particles_style = UserSettingsData.ParticlesStyle.BOTH
    default_theme = UserSettingsData.Theme.LIGHT
    custom_theme = None
    default_language_code = "en"
    custom_language_code = None


class UserDeliveryDataFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = UserDeliveryData

    user = factory.SubFactory(UserFactory)
    is_current = True
    full_name = factory.Faker("name")
    email = factory.Faker("email")
    phone = "+1234567890"
    zip_code = "10001"
    address_line = factory.Faker("street_address")
    destination_code = "US"
    region_code = "NY"
