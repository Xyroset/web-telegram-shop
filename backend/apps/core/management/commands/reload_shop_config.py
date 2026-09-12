from typing import Any

from django.core.management.base import BaseCommand

from apps.core.config_manager import shop_config


class Command(BaseCommand):
    """
    Management command to reload shop configuration into the cache.
    """

    help = "Flushes and reloads all business YAML configuration files into Redis cache"

    def handle(self, *args: Any, **options: Any) -> None:
        self.stdout.write("Reading YAML configuration files from disk...")

        try:
            new_config = shop_config.reload()

            if new_config:
                self.stdout.write(self.style.SUCCESS("Successfully reloaded all configuration files into Redis cache."))
            else:
                self.stdout.write(self.style.WARNING("Config directory is empty or missing active YAML files."))
        except Exception as exc:
            self.stderr.write(self.style.ERROR(f"Critical error during configuration reload: {exc}"))
