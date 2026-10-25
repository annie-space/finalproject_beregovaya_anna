"""CLI-интерфейс ValutaTrade Hub."""

import argparse
import sys

from valutatrade_hub.core import usecases
from valutatrade_hub.core.exceptions import (
    ApiRequestError,
    CurrencyNotFoundError,
    InsufficientFundsError,
    ValutaTradeError,
)
from valutatrade_hub.parser_service.storage import RatesStorage
from valutatrade_hub.parser_service.updater import RatesUpdater


def _print_error(message: str) -> None:
    print(f"Ошибка: {message}")


# ---------- Core-команды ----------

def cmd_register(args: argparse.Namespace) -> int:
    try:
        user = usecases.register(
            username=args.username, password=args.password
        )
    except ValueError as exc:
        _print_error(str(exc))
        return 1
    print(
        f"Пользователь '{user.username}' зарегистрирован "
        f"(id={user.user_id}). Войдите: login --username {user.username}"
    )
    return 0


def cmd_login(args: argparse.Namespace) -> int:
    try:
        user = usecases.login(username=args.username, password=args.password)
    except ValueError as exc:
        _print_error(str(exc))
        return 1
    usecases.set_current_user(user)
    print(f"Вы вошли как '{user.username}'")
    return 0


def cmd_show_portfolio(args: argparse.Namespace) -> int:
    try:
        user = usecases.require_login()
    except ValueError as exc:
        _print_error(str(exc))
        return 1

    try:
        data = usecases.show_portfolio(user.user_id, base=args.base)
    except CurrencyNotFoundError as exc:
        _print_error(str(exc))
        return 1
    except ValueError as exc:
        _print_error(str(exc))
        return 1

    wallets = data["wallets"]
    if not wallets:
        print("Портфель пуст. Купите валюту: buy --currency BTC --amount 0.05")
        return 0

    print(
        f"Портфель пользователя '{user.username}' "
        f"(база: {data['base']}):"
    )
    for code, wallet in wallets.items():
        value = wallet.balance * _rate_to(wallet.currency_code, data["base"])
        print(f"- {code}: {wallet.balance:.4f}  → {value:.2f} {data['base']}")
    print("-" * 33)
    print(f"ИТОГО: {data['total']:.2f} {data['base']}")
    return 0


def _rate_to(code: str, base: str) -> float:
    """Курс code → base через заглушку из Portfolio."""
    from valutatrade_hub.core.models import Portfolio

    rates = Portfolio.EXCHANGE_RATES_TO_USD
    c = code.upper()
    b = base.upper()
    if c not in rates or b not in rates:
        return 1.0
    return rates[c] / rates[b]


def cmd_buy(args: argparse.Namespace) -> int:
    try:
        user = usecases.require_login()
    except ValueError as exc:
        _print_error(str(exc))
        return 1

    try:
        res = usecases.buy(
            user_id=user.user_id, currency=args.currency, amount=args.amount
        )
    except (CurrencyNotFoundError, ApiRequestError) as exc:
        _print_error(str(exc))
        return 1
    except (ValueError, InsufficientFundsError) as exc:
        _print_error(str(exc))
        return 1

    print(
        f"Покупка выполнена: {res['amount']:.4f} {res['currency']} "
        f"по курсу {res['rate']:.2f} USD/{res['currency']}"
    )
    print("Изменения в портфеле:")
    print(
        f"- {res['currency']}: было {res['before']:.4f} "
        f"→ стало {res['after']:.4f}"
    )
    print(f"Оценочная стоимость покупки: {res['value_usd']:.2f} USD")
    return 0


def cmd_sell(args: argparse.Namespace) -> int:
    try:
        user = usecases.require_login()
    except ValueError as exc:
        _print_error(str(exc))
        return 1

    try:
        res = usecases.sell(
            user_id=user.user_id, currency=args.currency, amount=args.amount
        )
    except InsufficientFundsError as exc:
        _print_error(str(exc))
        return 1
    except (ValueError, CurrencyNotFoundError) as exc:
        _print_error(str(exc))
        return 1

    print(
        f"Продажа выполнена: {res['amount']:.4f} {res['currency']} "
        f"по курсу {res['rate']:.2f} USD/{res['currency']}"
    )
    print("Изменения в портфеле:")
    print(
        f"- {res['currency']}: было {res['before']:.4f} "
        f"→ стало {res['after']:.4f}"
    )
    print(f"Оценочная выручка: {res['value_usd']:.2f} USD")
    return 0


def cmd_get_rate(args: argparse.Namespace) -> int:
    try:
        res = usecases.get_rate(args.from_code, args.to_code)
    except (CurrencyNotFoundError, ApiRequestError) as exc:
        _print_error(str(exc))
        return 1

    print(
        f"Курс {res['from']}→{res['to']}: {res['rate']:.8f} "
        f"(обновлено: {res['updated_at']})"
    )
    if res["reverse"]:
        print(f"Обратный курс {res['to']}→{res['from']}: {res['reverse']:.8f}")
    return 0


# ---------- Parser-команды ----------

def cmd_update_rates(args: argparse.Namespace) -> int:
    """Обновляет курсы из внешних API."""
    try:
        updater = RatesUpdater()
        result = updater.run_update(source=args.source)
    except Exception as exc:
        _print_error(f"{type(exc).__name__}: {exc}")
        return 1

    if result["updated"] == 0:
        print("Не удалось обновить курсы.")
        for err in result["errors"]:
            print(f"  - {err}")
        return 1

    print(f"Обновлено курсов: {result['updated']}")
    print(f"Последнее обновление: {result['last_refresh']}")
    if result["errors"]:
        print("Предупреждения:")
        for err in result["errors"]:
            print(f"  - {err}")
    return 0


def cmd_show_rates(args: argparse.Namespace) -> int:
    """Показывает кэш курсов из rates.json."""
    storage = RatesStorage()
    data = storage.load_rates()
    pairs = data.get("pairs", {})
    last_refresh = data.get("last_refresh", "—")

    if not pairs:
        print("Локальный кеш курсов пуст. Выполните 'update-rates'.")
        return 0

    if args.currency:
        code = args.currency.upper()
        filtered = {
            pair: info
            for pair, info in pairs.items()
            if pair.startswith(f"{code}_") or pair.endswith(f"_{code}")
        }
        if not filtered:
            _print_error(f"Курс для '{code}' не найден в кеше")
            return 1
        pairs = filtered

    if args.base:
        base = args.base.upper()
        filtered = {
            pair: info
            for pair, info in pairs.items()
            if pair.endswith(f"_{base}")
        }
        if not filtered:
            _print_error(f"Курсы с базой '{base}' не найдены")
            return 1
        pairs = filtered

    items = list(pairs.items())
    if args.top:
        items.sort(key=lambda kv: kv[1]["rate"], reverse=True)
        items = items[: args.top]
    else:
        items.sort(key=lambda kv: kv[0])

    print(f"Курсы из кеша (обновлено: {last_refresh}):")
    for pair, info in items:
        print(f"- {pair}: {info['rate']}")
    return 0


# ---------- Парсер ----------

def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="valutatrade", description="ValutaTrade Hub"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("register", help="Регистрация")
    p.add_argument("--username", required=True)
    p.add_argument("--password", required=True)
    p.set_defaults(func=cmd_register)

    p = sub.add_parser("login", help="Вход")
    p.add_argument("--username", required=True)
    p.add_argument("--password", required=True)
    p.set_defaults(func=cmd_login)

    p = sub.add_parser("show-portfolio", help="Показать портфель")
    p.add_argument("--base", default="USD")
    p.set_defaults(func=cmd_show_portfolio)

    p = sub.add_parser("buy", help="Купить валюту")
    p.add_argument("--currency", required=True)
    p.add_argument("--amount", required=True, type=float)
    p.set_defaults(func=cmd_buy)

    p = sub.add_parser("sell", help="Продать валюту")
    p.add_argument("--currency", required=True)
    p.add_argument("--amount", required=True, type=float)
    p.set_defaults(func=cmd_sell)

    p = sub.add_parser("get-rate", help="Курс валюты")
    p.add_argument("--from", dest="from_code", required=True)
    p.add_argument("--to", dest="to_code", required=True)
    p.set_defaults(func=cmd_get_rate)

    p = sub.add_parser("update-rates", help="Обновить курсы из API")
    p.add_argument(
        "--source",
        choices=["coingecko", "exchangerate"],
        default=None,
        help="Обновить только указанный источник",
    )
    p.set_defaults(func=cmd_update_rates)

    p = sub.add_parser("show-rates", help="Показать кеш курсов")
    p.add_argument("--currency", default=None)
    p.add_argument("--top", type=int, default=None)
    p.add_argument("--base", default=None)
    p.set_defaults(func=cmd_show_rates)

    return parser


# ---------- Точки входа ----------

def main(argv: list[str] | None = None) -> int:
    """Точка входа CLI.

    Без аргументов — интерактивный REPL (сессия сохраняется).
    С аргументами — одна команда и выход.
    """
    if argv is None and len(sys.argv) > 1:
        argv = sys.argv[1:]

    if argv:
        parser = _build_parser()
        args = parser.parse_args(argv)
        try:
            return args.func(args)
        except ValutaTradeError as exc:
            _print_error(str(exc))
            return 1

    return _repl()


def _repl() -> int:
    """Интерактивный режим: команды вводятся по одной, сессия живёт."""
    parser = _build_parser()
    print("ValutaTrade Hub. Введите 'help' или 'exit'.")
    while True:
        try:
            line = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not line:
            continue
        if line in ("exit", "quit"):
            break
        if line == "help":
            parser.print_help()
            continue
        try:
            args = parser.parse_args(line.split())
        except SystemExit:
            continue
        try:
            args.func(args)
        except ValutaTradeError as exc:
            _print_error(str(exc))
        except Exception as exc:
            _print_error(f"{type(exc).__name__}: {exc}")
    return 0


if __name__ == "__main__":
    sys.exit(main())