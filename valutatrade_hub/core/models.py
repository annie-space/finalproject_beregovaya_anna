"""Модели данных ValutaTrade Hub: User, Wallet, Portfolio."""

import hashlib
import secrets
from datetime import datetime

from valutatrade_hub.core.exceptions import (
    CurrencyNotFoundError,
    InsufficientFundsError,
)


class Wallet:
    """Кошелёк пользователя для одной валюты."""

    def __init__(self, currency_code: str, balance: float = 0.0):
        self.currency_code = currency_code
        self._balance = 0.0
        self.balance = balance

    @property
    def balance(self) -> float:
        """Текущий баланс кошелька."""
        return self._balance

    @balance.setter
    def balance(self, value: float) -> None:
        """Устанавливает баланс с проверкой типа и неотрицательности."""
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise TypeError("Баланс должен быть числом")
        if value < 0:
            raise ValueError("Баланс не может быть отрицательным")
        self._balance = float(value)

    def deposit(self, amount: float) -> None:
        """Пополнение баланса."""
        if not isinstance(amount, (int, float)) or isinstance(amount, bool):
            raise TypeError("Сумма должна быть числом")
        if amount <= 0:
            raise ValueError("Сумма пополнения должна быть положительной")
        self.balance = self._balance + amount

    def withdraw(self, amount: float) -> None:
        """Снятие средств, если баланс позволяет."""
        if not isinstance(amount, (int, float)) or isinstance(amount, bool):
            raise TypeError("Сумма должна быть числом")
        if amount <= 0:
            raise ValueError("Сумма снятия должна быть положительной")
        if amount > self._balance:
            raise InsufficientFundsError(
                available=self._balance,
                required=amount,
                code=self.currency_code,
            )
        self.balance = self._balance - amount

    def get_balance_info(self) -> str:
        """Строка с информацией о балансе."""
        return f"{self.currency_code}: {self._balance:.4f}"


class User:
    """Пользователь системы."""

    def __init__(
        self,
        user_id: int,
        username: str,
        hashed_password: str,
        salt: str,
        registration_date: datetime,
    ):
        self._user_id = user_id
        self._username = ""
        self._hashed_password = hashed_password
        self._salt = salt
        self._registration_date = registration_date
        self.username = username

    @property
    def user_id(self) -> int:
        """Уникальный идентификатор пользователя."""
        return self._user_id

    @property
    def username(self) -> str:
        """Имя пользователя."""
        return self._username

    @username.setter
    def username(self, value: str) -> None:
        """Устанавливает имя пользователя с проверкой."""
        if not isinstance(value, str) or not value.strip():
            raise ValueError("Имя пользователя не может быть пустым")
        self._username = value.strip()

    @property
    def hashed_password(self) -> str:
        """Хеш пароля (только чтение)."""
        return self._hashed_password

    @property
    def salt(self) -> str:
        """Соль пользователя (только чтение)."""
        return self._salt

    @property
    def registration_date(self) -> datetime:
        """Дата регистрации (только чтение)."""
        return self._registration_date

    def _hash_password(self, password: str) -> str:
        """Односторонний хеш: sha256(password + salt)."""
        return hashlib.sha256((password + self._salt).encode()).hexdigest()

    def verify_password(self, password: str) -> bool:
        """Проверяет, совпадает ли пароль с сохранённым хешем."""
        return self._hash_password(password) == self._hashed_password

    def change_password(self, new_password: str) -> None:
        """Меняет пароль пользователя (с валидацией длины)."""
        if not isinstance(new_password, str) or len(new_password) < 4:
            raise ValueError("Пароль должен быть не короче 4 символов")
        self._hashed_password = self._hash_password(new_password)

    def get_user_info(self) -> str:
        """Информация о пользователе без пароля."""
        return (
            f"User(id={self._user_id}, username='{self._username}', "
            f"registered={self._registration_date.isoformat()})"
        )

    @classmethod
    def create(cls, user_id: int, username: str, password: str) -> "User":
        """Фабричный метод: создаёт пользователя с новой солью и хешем."""
        if not isinstance(password, str) or len(password) < 4:
            raise ValueError("Пароль должен быть не короче 4 символов")
        salt = secrets.token_hex(8)
        hashed = hashlib.sha256((password + salt).encode()).hexdigest()
        return cls(
            user_id=user_id,
            username=username,
            hashed_password=hashed,
            salt=salt,
            registration_date=datetime.now(),
        )

    def to_dict(self) -> dict:
        """Сериализация для users.json."""
        return {
            "user_id": self._user_id,
            "username": self._username,
            "hashed_password": self._hashed_password,
            "salt": self._salt,
            "registration_date": self._registration_date.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "User":
        """Десериализация из users.json."""
        return cls(
            user_id=data["user_id"],
            username=data["username"],
            hashed_password=data["hashed_password"],
            salt=data["salt"],
            registration_date=datetime.fromisoformat(data["registration_date"]),
        )


class Portfolio:
    """Портфель пользователя: набор кошельков по валютам."""

    # Заглушка курсов к USD (пока Parser Service не подключён).
    EXCHANGE_RATES_TO_USD: dict[str, float] = {
        "USD": 1.0,
        "EUR": 1.08,
        "GBP": 1.27,
        "RUB": 0.0102,
        "BTC": 59337.21,
        "ETH": 3720.00,
        "SOL": 145.12,
    }

    def __init__(self, user_id: int, wallets: dict[str, Wallet] | None = None):
        self._user_id = user_id
        self._wallets: dict[str, Wallet] = wallets or {}

    @property
    def user_id(self) -> int:
        """ID пользователя, которому принадлежит портфель."""
        return self._user_id

    @property
    def wallets(self) -> dict[str, Wallet]:
        """Копия словаря кошельков (защита от внешней мутации)."""
        return dict(self._wallets)

    def get_wallet(self, currency_code: str) -> Wallet | None:
        """Возвращает кошелёк по коду или None, если его нет."""
        return self._wallets.get(currency_code.upper())

    def add_currency(self, currency_code: str) -> Wallet:
        """Добавляет новый кошелёк, если его ещё нет."""
        code = currency_code.upper()
        if code in self._wallets:
            raise ValueError(f"Кошелёк '{code}' уже существует")
        wallet = Wallet(code)
        self._wallets[code] = wallet
        return wallet

    def get_total_value(self, base_currency: str = "USD") -> float:
        """Общая стоимость всех кошельков в базовой валюте."""
        base = base_currency.upper()
        if base not in self.EXCHANGE_RATES_TO_USD:
            raise CurrencyNotFoundError(base)

        base_rate = self.EXCHANGE_RATES_TO_USD[base]
        total = 0.0
        for code, wallet in self._wallets.items():
            rate_to_usd = self.EXCHANGE_RATES_TO_USD.get(code)
            if rate_to_usd is None:
                continue
            value_in_usd = wallet.balance * rate_to_usd
            total += value_in_usd / base_rate
        return total

    def to_dict(self) -> dict:
        """Сериализация для portfolios.json."""
        return {
            "user_id": self._user_id,
            "wallets": {
                code: {"currency_code": code, "balance": wallet.balance}
                for code, wallet in self._wallets.items()
            },
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Portfolio":
        """Десериализация из portfolios.json."""
        wallets = {
            code: Wallet(code, w["balance"])
            for code, w in data.get("wallets", {}).items()
        }
        return cls(user_id=data["user_id"], wallets=wallets)