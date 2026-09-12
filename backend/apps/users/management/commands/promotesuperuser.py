import getpass
from typing import Any

from django.core.management.base import BaseCommand
from django.db import transaction as ts
from django.utils.functional import cached_property

from apps.users.repo import UserRepository


class Command(BaseCommand):
    """
    Management command to grant superuser and staff permissions to an existing user by TG_ID.
    """

    help = "Grants superuser and staff permissions to an existing user by TG_ID"

    @cached_property
    def _user_repo(self) -> UserRepository:
        return UserRepository()

    def handle(self, *args: Any, **options: Any) -> None:
        raw_tg_id = input("TG_ID: ").strip()
        tg_id = int(raw_tg_id)
        password = getpass.getpass("PASSWORD: ")

        with ts.atomic():
            user = self._user_repo.get_for_update_by(tg_id=tg_id)
            updated_fields = user.promote_superuser(password=password)

            self._user_repo.save(instance=user, update_fields=updated_fields)

            self.stdout.write(
                self.style.SUCCESS(f"Success! User with TG_ID {tg_id} has been granted superuser status.")
            )
