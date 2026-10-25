"""Клиенты внешних API: CoinGecko и ExchangeRate-API."""

from abc import ABC, abstractmethod

import requests

from valutatrade_hub.core.exceptions import ApiRequestError
from valutatrade_hub.parser_service.config import ParserConfig


class BaseApiClient(ABC):
    """Базовый класс API-клиента."""

    def __init__(self, config: ParserConfig | None = None) -> None:
        self.config = config or ParserConfig()

    @abstractmethod
    def fetch_rates(self) -> dict[str, float]:
        """Возвращает словарь {«CODE_USD»: rate}."""


class CoinGeckoClient(BaseApiClient):
    """Клиент CoinGecko (криптовалюты)."""

    def fetch_rates(self) -> dict[str, float]:
        ids = ",".join(
            self.config.CRYPTO_ID_MAP[code]
            for code in self.config.CRYPTO_CURRENCIES
            if code in self.config.CRYPTO_ID_MAP
        )
        params = {"ids": ids, "vs_currencies": self.config.BASE_CURRENCY.lower()}
        try:
            response = requests.get(
                self.config.COINGECKO_URL,
                params=params,
                timeout=self.config.REQUEST_TIMEOUT,
            )
        except requests.exceptions.RequestException as exc:
            raise ApiRequestError(f"CoinGecko: {exc}") from exc

        if response.status_code != 200:
            raise ApiRequestError(
                f"CoinGecko вернул статус {response.status_code}"
            )

        try:
            data = response.json()
        except ValueError as exc:
            raise ApiRequestError("CoinGecko: некорректный JSON") from exc

        base = self.config.BASE_CURRENCY.upper()
        result: dict[str, float] = {}
        for code, coin_id in self.config.CRYPTO_ID_MAP.items():
            entry = data.get(coin_id)
            if not entry:
                continue
            rate = entry.get(self.config.BASE_CURRENCY.lower())
            if isinstance(rate, (int, float)):
                result[f"{code}_{base}"] = float(rate)
        return result


class ExchangeRateApiClient(BaseApiClient):
    """Клиент ExchangeRate-API (фиатные валюты)."""

    def fetch_rates(self) -> dict[str, float]:
        key = self.config.EXCHANGERATE_API_KEY
        if not key:
            raise ApiRequestError(
                "ExchangeRate-API: ключ не задан (EXCHANGERATE_API_KEY)"
            )

        url = (
            f"{self.config.EXCHANGERATE_API_URL}/{key}/latest/"
            f"{self.config.BASE_CURRENCY}"
        )
        try:
            response = requests.get(url, timeout=self.config.REQUEST_TIMEOUT)
        except requests.exceptions.RequestException as exc:
            raise ApiRequestError(f"ExchangeRate-API: {exc}") from exc

        if response.status_code != 200:
            raise ApiRequestError(
                f"ExchangeRate-API вернул статус {response.status_code}"
            )

        try:
            data = response.json()
        except ValueError as exc:
            raise ApiRequestError(
                "ExchangeRate-API: некорректный JSON"
            ) from exc

        if data.get("result") != "success":
            reason = data.get("error-type", "unknown error")
            raise ApiRequestError(f"ExchangeRate-API: {reason}")

        rates = data.get("rates", {})
        base = self.config.BASE_CURRENCY.upper()
        result: dict[str, float] = {}
        for code in self.config.FIAT_CURRENCIES:
            rate = rates.get(code)
            if isinstance(rate, (int, float)):
                # API возвращает 1 BASE = N CODE, нам нужен 1 CODE = ? BASE
                result[f"{code}_{base}"] = 1.0 / float(rate) if rate else 0.0
        return result