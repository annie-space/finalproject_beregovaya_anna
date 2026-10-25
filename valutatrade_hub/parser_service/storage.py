"""Хранилище Parser Service: rates.json и exchange_rates.json."""

import json
from datetime import datetime, timezone
from pathlib import Path

from valutatrade_hub.parser_service.config import ParserConfig


class RatesStorage:
    """Чтение/запись кэша курсов и истории измерений."""

    def __init__(self, config: ParserConfig | None = None) -> None:
        self.config = config or ParserConfig()
        self.rates_path = Path(self.config.RATES_FILE_PATH)
        self.history_path = Path(self.config.HISTORY_FILE_PATH)

    # ---------- Служебное ----------

    @staticmethod
    def _atomic_write(path: Path, data) -> None:
        """Атомарная запись JSON (tmp → rename)."""
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        with tmp.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        tmp.replace(path)

    @staticmethod
    def _read_json(path: Path, default):
        if not path.exists():
            return default
        try:
            with path.open("r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return default

    # ---------- rates.json ----------

    def load_rates(self) -> dict:
        """Читает кэш rates.json."""
        return self._read_json(self.rates_path, default={"pairs": {}})

    def save_rates(self, new_rates: dict[str, dict]) -> None:
        """Сохраняет снимок курсов.

        new_rates: {"BTC_USD": {"rate": 59337.21, "source": "CoinGecko"}, ...}
        """
        now = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
        existing = self.load_rates()
        pairs = existing.get("pairs", {})

        for pair, info in new_rates.items():
            updated_at = info.get("updated_at") or now
            current = pairs.get(pair)
            # апдейт «побеждает», если updated_at свежее
            if current and current.get("updated_at", "") > updated_at:
                continue
            pairs[pair] = {
                "rate": info["rate"],
                "updated_at": updated_at,
                "source": info.get("source", "unknown"),
            }

        data = {"pairs": pairs, "last_refresh": now}
        self._atomic_write(self.rates_path, data)

    # ---------- exchange_rates.json (история) ----------

    def load_history(self) -> list[dict]:
        """Читает историю измерений."""
        data = self._read_json(self.history_path, default=[])
        return data if isinstance(data, list) else []

    def append_history(self, new_rates: dict[str, dict]) -> None:
        """Добавляет измерения в историю (без дублей по id)."""
        history = self.load_history()
        seen = {item["id"] for item in history}
        for pair, info in new_rates.items():
            updated_at = info.get("updated_at")
            if not updated_at:
                continue
            record_id = f"{pair}_{updated_at}"
            if record_id in seen:
                continue
            frm, to = pair.split("_", 1)
            history.append(
                {
                    "id": record_id,
                    "from_currency": frm,
                    "to_currency": to,
                    "rate": info["rate"],
                    "timestamp": updated_at,
                    "source": info.get("source", "unknown"),
                    "meta": info.get("meta", {}),
                }
            )
        self._atomic_write(self.history_path, history)