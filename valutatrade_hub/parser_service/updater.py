"""Координатор обновления курсов Parser Service."""

from datetime import datetime, timezone

from valutatrade_hub.core.exceptions import ApiRequestError
from valutatrade_hub.logging_config import get_logger
from valutatrade_hub.parser_service.api_clients import (
    BaseApiClient,
    CoinGeckoClient,
    ExchangeRateApiClient,
)
from valutatrade_hub.parser_service.config import ParserConfig
from valutatrade_hub.parser_service.storage import RatesStorage


class RatesUpdater:
    """Опрашивает API-клиенты, объединяет и сохраняет курсы."""

    def __init__(
        self,
        clients: list[BaseApiClient] | None = None,
        storage: RatesStorage | None = None,
        config: ParserConfig | None = None,
    ) -> None:
        self.config = config or ParserConfig()
        self.storage = storage or RatesStorage(self.config)
        if clients is None:
            clients = [CoinGeckoClient(self.config),
                       ExchangeRateApiClient(self.config)]
        self.clients = clients
        self.log = get_logger()

    def run_update(self, source: str | None = None) -> dict:
        """Обновляет курсы. Возвращает сводку.

        source: "coingecko" | "exchangerate" | None (все).
        """
        self.log.info("Starting rates update...")
        now = (
            datetime.now(timezone.utc)
            .replace(microsecond=0)
            .isoformat()
        )

        collected: dict[str, dict] = {}
        errors: list[str] = []

        for client in self.clients:
            name = type(client).__name__
            if source:
                src = source.lower()
                if src == "coingecko" and "CoinGecko" not in name:
                    continue
                if src == "exchangerate" and "ExchangeRate" not in name:
                    continue
            try:
                self.log.info("Fetching from %s...", name)
                rates = client.fetch_rates()
                count = len(rates)
                self.log.info("Fetching from %s... OK (%d rates)", name, count)
                for pair, value in rates.items():
                    collected[pair] = {
                        "rate": value,
                        "updated_at": now,
                        "source": "CoinGecko"
                        if "CoinGecko" in name
                        else "ExchangeRate-API",
                    }
            except ApiRequestError as exc:
                self.log.error("Failed to fetch from %s: %s", name, exc)
                errors.append(f"{name}: {exc}")

        if not collected:
            self.log.error("No rates collected, aborting update")
            return {
                "updated": 0,
                "errors": errors,
                "last_refresh": None,
            }

        self.log.info(
            "Writing %d rates to %s...",
            len(collected),
            self.config.RATES_FILE_PATH,
        )
        self.storage.save_rates(collected)
        self.storage.append_history(collected)

        if errors:
            self.log.warning(
                "Update completed with errors (%d)", len(errors)
            )
        else:
            self.log.info("Update successful. Total rates updated: %d",
                          len(collected))

        return {
            "updated": len(collected),
            "errors": errors,
            "last_refresh": now,
        }