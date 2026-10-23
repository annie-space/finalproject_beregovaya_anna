"""Модели данных ValutaTrade Hub: User, Wallet, Portfolio."""

from valutatrade_hub.core.exceptions import InsufficientFundsError


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