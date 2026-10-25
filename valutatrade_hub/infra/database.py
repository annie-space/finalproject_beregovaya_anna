"""Singleton DatabaseManager: работа с JSON-хранилищем."""

import json
from pathlib import Path


class DatabaseManager:
    """Единая точка доступа к JSON-файлам data/.

    Реализован как Singleton через __new__: просто и читабельно.
    """

    _instance: "DatabaseManager | None" = None

    def __new__(cls, data_dir: str | Path = "data") -> "DatabaseManager":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, data_dir: str | Path = "data") -> None:
        if self._initialized:
            return
        self._data_dir = Path(data_dir)
        self._data_dir.mkdir(parents=True, exist_ok=True)
        self._initialized = True

    @property
    def data_dir(self) -> Path:
        """Путь к папке data/."""
        return self._data_dir

    def _path(self, filename: str) -> Path:
        """Полный путь к файлу внутри data/."""
        return self._data_dir / filename

    def read_json(self, filename: str, default):
        """Читает JSON-файл. Если файла нет — возвращает default."""
        path = self._path(filename)
        if not path.exists():
            return default
        try:
            with path.open("r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return default

    def write_json(self, filename: str, data) -> None:
        """Атомарно пишет JSON-файл (tmp → rename)."""
        path = self._path(filename)
        tmp_path = path.with_suffix(path.suffix + ".tmp")
        with tmp_path.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        tmp_path.replace(path)