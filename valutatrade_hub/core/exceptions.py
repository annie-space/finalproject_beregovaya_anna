"""Пользовательские исключения ValutaTrade Hub."""


class ValutaTradeError(Exception):
    """Исключение для всех ошибок проекта."""


class InsufficientFundsError(ValutaTradeError):
    """Недостаточно средств для выполнения операции."""

    def __init__(self, available: float, required: float, code: str):
        self.available = available
        self.required = required
        self.code = code
        message = (
            f"Недостаточно средств: доступно {available} {code}, "
            f"требуется {required} {code}"
        )
        super().__init__(message)


class CurrencyNotFoundError(ValutaTradeError):
    """Неизвестная валюта."""

    def __init__(self, code: str):
        self.code = code
        super().__init__(f"Неизвестная валюта '{code}'")


class ApiRequestError(ValutaTradeError):
    """Сбой при обращении к внешнему API."""

    def __init__(self, reason: str):
        self.reason = reason
        super().__init__(f"Ошибка при обращении к внешнему API: {reason}")