import json
import logging
from collections.abc import Mapping
from pathlib import Path
from typing import Any, cast

import yaml
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)


class ConfigManager:
    def __init__(self) -> None:
        self._cache_key = "shop_runtime_configuration"

    @property
    def config_dir(self) -> Path:
        path = getattr(settings, "SHOP_CONFIG_DIR", "/app/shop_config")
        return Path(path)

    def reload(self) -> Mapping[str, Any]:
        if not self.config_dir.exists() or not self.config_dir.is_dir():
            logger.warning(f"Config directory not found at: {self.config_dir}")
            return {}

        new_config: dict[str, Any] = {"locales": {}}

        for file_path in self.config_dir.rglob("*"):
            if not file_path.is_file() or file_path.name.endswith(".example.yaml"):
                continue

            filename_without_ext = file_path.stem

            try:
                if file_path.suffix == ".yaml":
                    with file_path.open("r", encoding="utf-8") as f:
                        new_config[filename_without_ext] = yaml.safe_load(f) or {}

                elif file_path.suffix == ".json":
                    with file_path.open("r", encoding="utf-8") as f:
                        new_config["locales"][filename_without_ext] = json.load(f) or {}

            except (OSError, json.JSONDecodeError, yaml.YAMLError) as e:
                logger.error(f"Failed to parse config file {file_path}: {e}")

        cache.set(self._cache_key, new_config, timeout=None)
        return new_config

    def _get_all_config(self) -> Mapping[str, Any]:
        config = cache.get(self._cache_key)
        if config is None:
            config = self.reload()
        return cast(Mapping[str, Any], config)

    def get(self, namespace: str, key_path: str, default: Any = None) -> Any:
        config = self._get_all_config()
        namespace_data = config.get(namespace)

        if namespace_data is None:
            return default

        if not key_path:
            return namespace_data

        keys = key_path.split(".")
        current_value = namespace_data

        for key in keys:
            if isinstance(current_value, dict) and key in current_value:
                current_value = current_value[key]
            else:
                return default

        return current_value


shop_config = ConfigManager()
