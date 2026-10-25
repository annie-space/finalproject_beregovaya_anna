"""Singleton SettingsLoader: конфигурация проекта."""

import os
from pathlib import Path
from typing import Any


class SettingsLoader:
    """Единая точка конфигурации проекта.

    Реализован как Singleton через __new__: просто и читабельно.
    Значения по умолчанию можно переопределить переменными окружения.
    """

    _instance: "SettingsLoader | None" = None

    # Значения по умолчанию
    DEFAULTS: dict[str, Any] = {
        "DATA_DIR": "data",
        "RATES_TTL_SECONDS": 300,  # 5 минут
        "BASE_CURRENCY": "USD",
        "LOG_FILE": "logs/actions.log",
        "LOG_LEVEL": "INFO",
        "LOG_MAX_BYTES": 1_000_000,
        "LOG_BACKUP_COUNT": 3,
    }

    def __new__(cls) -> "SettingsLoader":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self._config: dict[str, Any] = dict(self.DEFAULTS)
        self._load_from_env()
        self._initialized = True

    def _load_from_env(self) -> None:
        """Переопределяет настройки из переменных окружения."""
        for key in self.DEFAULTS:
            env_value = os.getenv(f"VALUTATRADE_{key}")
            if env_value is not None:
                self._config[key] = self._coerce(key, env_value)

    def _coerce(self, key: str, value: str) -> Any:
        """Приводит строку из env к типу значения по умолчанию."""
        default = self.DEFAULTS[key]
        if isinstance(default, int):
            return int(value)
        return value

    def get(self, key: str, default: Any = None) -> Any:
        """Возвращает значение настройки."""
        return self._config.get(key, default)

    def reload(self) -> None:
        """Перезагружает конфигурацию (сбрасывает к дефолтам + env)."""
        self._config = dict(self.DEFAULTS)
        self._load_from_env()

    @property
    def data_dir(self) -> Path:
        """Путь к папке data/."""
        return Path(self.get("DATA_DIR"))

    @property
    def rates_ttl_seconds(self) -> int:
        """TTL кэша курсов в секундах."""
        return int(self.get("RATES_TTL_SECONDS"))

    @property
    def base_currency(self) -> str:
        """Базовая валюта по умолчанию."""
        return str(self.get("BASE_CURRENCY"))