"""Бизнес-логика ValutaTrade Hub."""

from datetime import datetime, timezone

from valutatrade_hub.core.exceptions import (
    ApiRequestError,
    CurrencyNotFoundError,
)
from valutatrade_hub.core.models import Portfolio, User
from valutatrade_hub.decorators import log_action
from valutatrade_hub.infra.database import DatabaseManager

USERS_FILE = "users.json"
PORTFOLIOS_FILE = "portfolios.json"
RATES_FILE = "rates.json"


# ---------- Вспомогательные ----------

def _load_users(db: DatabaseManager) -> list[dict]:
    return db.read_json(USERS_FILE, default=[])


def _save_users(db: DatabaseManager, users: list[dict]) -> None:
    db.write_json(USERS_FILE, users)


def _load_portfolios(db: DatabaseManager) -> list[dict]:
    return db.read_json(PORTFOLIOS_FILE, default=[])


def _save_portfolios(db: DatabaseManager, portfolios: list[dict]) -> None:
    db.write_json(PORTFOLIOS_FILE, portfolios)


def _find_user(users: list[dict], username: str) -> User | None:
    for u in users:
        if u["username"] == username:
            return User.from_dict(u)
    return None


def _find_portfolio(portfolios: list[dict], user_id: int) -> Portfolio | None:
    for p in portfolios:
        if p["user_id"] == user_id:
            return Portfolio.from_dict(p)
    return None


def _load_rates(db: DatabaseManager) -> dict:
    return db.read_json(RATES_FILE, default={})


# ---------- Регистрация и логин ----------

@log_action("REGISTER")
def register(username: str, password: str, **_) -> User:
    """Регистрирует нового пользователя. Возвращает объект User."""
    if not username or not username.strip():
        raise ValueError("Имя пользователя не может быть пустым")
    if not password or len(password) < 4:
        raise ValueError("Пароль должен быть не короче 4 символов")

    db = DatabaseManager()
    users = _load_users(db)

    if any(u["username"] == username for u in users):
        raise ValueError(f"Имя пользователя '{username}' уже занято")

    new_id = max((u["user_id"] for u in users), default=0) + 1
    user = User.create(user_id=new_id, username=username, password=password)

    users.append(user.to_dict())
    _save_users(db, users)

    portfolios = _load_portfolios(db)
    portfolios.append({"user_id": new_id, "wallets": {}})
    _save_portfolios(db, portfolios)

    return user


@log_action("LOGIN")
def login(username: str, password: str, **_) -> User:
    """Проверяет учётные данные. Возвращает User при успехе."""
    db = DatabaseManager()
    users = _load_users(db)
    user = _find_user(users, username)
    if user is None:
        raise ValueError(f"Пользователь '{username}' не найден")
    if not user.verify_password(password):
        raise ValueError("Неверный пароль")
    return user


# ---------- Портфель ----------

def show_portfolio(user_id: int, base: str = "USD") -> dict:
    """Возвращает данные портфеля для отображения."""
    db = DatabaseManager()
    portfolios = _load_portfolios(db)
    portfolio = _find_portfolio(portfolios, user_id)
    if portfolio is None:
        raise ValueError(f"Портфель для user_id={user_id} не найден")

    total = portfolio.get_total_value(base_currency=base)
    return {
        "user_id": user_id,
        "base": base.upper(),
        "wallets": portfolio.wallets,
        "total": total,
    }


# ---------- Покупка/продажа ----------

@log_action("BUY")
def buy(user_id: int, currency: str, amount: float, **_) -> dict:
    """Покупает валюту: зачисляет amount на кошелёк currency."""
    if amount <= 0:
        raise ValueError("'amount' должен быть положительным числом")

    code = currency.upper()
    rates = _load_rates(DatabaseManager())
    rate = rates.get("pairs", {}).get(f"{code}_USD", {}).get("rate")
    if rate is None:
        raise CurrencyNotFoundError(code)

    db = DatabaseManager()
    portfolios = _load_portfolios(db)
    portfolio = _find_portfolio(portfolios, user_id)
    if portfolio is None:
        raise ValueError(f"Портфель для user_id={user_id} не найден")

    wallet = portfolio.get_wallet(code)
    if wallet is None:
        wallet = portfolio.add_currency(code)
    before = wallet.balance
    wallet.deposit(amount)

    # Обновляем сохранённый портфель
    for p in portfolios:
        if p["user_id"] == user_id:
            p["wallets"] = portfolio.to_dict()["wallets"]
            break
    _save_portfolios(db, portfolios)

    return {
        "currency": code,
        "amount": amount,
        "rate": rate,
        "before": before,
        "after": wallet.balance,
        "value_usd": amount * rate,
    }


@log_action("SELL")
def sell(user_id: int, currency: str, amount: float, **_) -> dict:
    """Продаёт валюту: списывает amount с кошелька currency."""
    if amount <= 0:
        raise ValueError("'amount' должен быть положительным числом")

    code = currency.upper()
    db = DatabaseManager()
    portfolios = _load_portfolios(db)
    portfolio = _find_portfolio(portfolios, user_id)
    if portfolio is None:
        raise ValueError(f"Портфель для user_id={user_id} не найден")

    wallet = portfolio.get_wallet(code)
    if wallet is None:
        raise ValueError(
            f"У вас нет кошелька '{code}'. "
            "Он создаётся автоматически при первой покупке."
        )

    before = wallet.balance
    wallet.withdraw(amount)

    rates = _load_rates(db)
    rate = rates.get("pairs", {}).get(f"{code}_USD", {}).get("rate", 0.0)

    for p in portfolios:
        if p["user_id"] == user_id:
            p["wallets"] = portfolio.to_dict()["wallets"]
            break
    _save_portfolios(db, portfolios)

    return {
        "currency": code,
        "amount": amount,
        "rate": rate,
        "before": before,
        "after": wallet.balance,
        "value_usd": amount * rate,
    }


# ---------- Курсы ----------

def get_rate(from_code: str, to_code: str) -> dict:
    """Возвращает курс from_code → to_code из кэша rates.json."""
    frm = from_code.upper()
    to = to_code.upper()

    db = DatabaseManager()
    rates = _load_rates(db)
    pairs = rates.get("pairs", {})

    def _rate(code_a: str, code_b: str) -> float | None:
        direct = pairs.get(f"{code_a}_{code_b}")
        if direct:
            return direct["rate"]
        inverse = pairs.get(f"{code_b}_{code_a}")
        if inverse and inverse["rate"]:
            return 1.0 / inverse["rate"]
        return None

    rate = _rate(frm, to)
    if rate is None:
        raise ApiRequestError(
            f"Курс {frm}→{to} недоступен. Обновите кэш (update-rates)."
        )

    reverse = _rate(to, frm)
    updated_at = (
        pairs.get(f"{frm}_{to}", {}).get("updated_at")
        or pairs.get(f"{to}_{frm}", {}).get("updated_at")
        or datetime.now(timezone.utc).isoformat()
    )

    return {
        "from": frm,
        "to": to,
        "rate": rate,
        "reverse": reverse,
        "updated_at": updated_at,
    }


# ---------- Сессия ----------

_current_user: User | None = None


def set_current_user(user: User | None) -> None:
    """Устанавливает текущего залогиненного пользователя."""
    global _current_user
    _current_user = user


def get_current_user() -> User | None:
    """Возвращает текущего залогиненного пользователя."""
    return _current_user


def require_login() -> User:
    """Возвращает текущего пользователя или бросает ValueError."""
    if _current_user is None:
        raise ValueError("Сначала выполните login")
    return _current_user