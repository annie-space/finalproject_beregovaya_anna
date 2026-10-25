"""Настройка логирования ValutaTrade Hub."""

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from valutatrade_hub.infra.settings import SettingsLoader

_configured: bool = False


def setup_logging() -> logging.Logger:
    """Настраивает корневой логгер (идемпотентно)."""
    global _configured

    logger = logging.getLogger("valutatrade")
    if _configured:
        return logger

    settings = SettingsLoader()
    log_file = Path(settings.get("LOG_FILE", "logs/actions.log"))
    log_file.parent.mkdir(parents=True, exist_ok=True)

    level = getattr(logging, str(settings.get("LOG_LEVEL", "INFO")).upper())
    logger.setLevel(level)

    formatter = logging.Formatter(
        fmt="%(asctime)s %(levelname)s %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )

    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=int(settings.get("LOG_MAX_BYTES", 1_000_000)),
        backupCount=int(settings.get("LOG_BACKUP_COUNT", 3)),
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    if not any(isinstance(h, logging.StreamHandler) for h in logger.handlers):
        stream = logging.StreamHandler()
        stream.setFormatter(formatter)
        logger.addHandler(stream)

    logger.propagate = False
    _configured = True
    return logger


def get_logger() -> logging.Logger:
    """Возвращает настроенный логгер проекта."""
    return setup_logging()