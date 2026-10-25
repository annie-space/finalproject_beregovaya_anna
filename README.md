# ValutaTrade Hub

Консольное приложение — симулятор валютного кошелька с поддержкой фиатных
и криптовалют. Позволяет регистрироваться, управлять портфелем, покупать
и продавать валюты, смотреть актуальные курсы.

Проект состоит из двух сервисов:

- **Core Service** — CLI, пользователи, кошельки, транзакции.
- **Parser Service** — обновление курсов из внешних API (CoinGecko,
  ExchangeRate-API) с кэшированием и историей.

## Технологии

- Python 3.12
- [uv](https://docs.astral.sh/uv/) — управление зависимостями
- [ruff](https://docs.astral.sh/ruff/) — линтер (PEP8)
- `requests` — HTTP-запросы к API
- `prettytable` — форматированный вывод (опционально)
- `json` — хранилище данных

## Структура проекта

```
finalproject_beregovaya_anna/
├── data/
│   ├── users.json              # пользователи
│   ├── portfolios.json         # портфели и кошельки
│   ├── rates.json              # кэш последних курсов
│   └── exchange_rates.json     # история измерений
├── valutatrade_hub/
│   ├── __init__.py
│   ├── logging_config.py       # логирование с ротацией
│   ├── decorators.py           # @log_action
│   ├── core/
│   │   ├── currencies.py       # (опционально) иерархия валют
│   │   ├── exceptions.py       # доменные исключения
│   │   ├── models.py           # User, Wallet, Portfolio
│   │   └── usecases.py         # бизнес-логика
│   ├── infra/
│   │   ├── settings.py         # Singleton SettingsLoader
│   │   └── database.py         # Singleton DatabaseManager
│   ├── parser_service/
│   │   ├── config.py           # ParserConfig
│   │   ├── api_clients.py      # CoinGecko, ExchangeRate-API
│   │   ├── storage.py          # rates.json + история
│   │   └── updater.py          # RatesUpdater
│   └── cli/
│       └── interface.py        # CLI + REPL
├── main.py
├── pyproject.toml
├── uv.lock
├── README.md
└── .gitignore
```

## Установка

```bash
# 1. Клонировать репозиторий
git clone https://github.com/annie-space/finalproject_beregovaya_anna.git
cd finalproject_beregovaya_anna

# 2. Установить зависимости через uv
uv sync

# 3. (опционально) Установить API-ключ ExchangeRate-API
#    Регистрация: https://www.exchangerate-api.com/
export EXCHANGERATE_API_KEY=ваш_ключ        # Linux/macOS
set EXCHANGERATE_API_KEY=ваш_ключ           # Windows (cmd)
$env:EXCHANGERATE_API_KEY="ваш_ключ"        # Windows (PowerShell)
```

> **Важно:** ключ ExchangeRate-API хранится **только в переменной
> окружения**, не коммитится в Git. CoinGecko работает без ключа.

## Запуск

```bash
uv run main.py
```

Приложение запускается в **интерактивном режиме (REPL)** —
сессия сохраняется между командами.

Также можно выполнить одну команду и выйти:

```bash
uv run main.py register --username alice --password 1234
```

## Команды CLI

### Регистрация и вход

```text
> register --username alice --password 1234
Пользователь 'alice' зарегистрирован (id=1). Войдите: login --username alice

> login --username alice --password 1234
Вы вошли как 'alice'
```

### Просмотр портфеля

```text
> show-portfolio
Портфель пользователя 'alice' (база: USD):
- USD: 150.0000  → 150.00 USD
- BTC: 0.0500  → 2966.86 USD
- EUR: 200.0000  → 216.00 USD
---------------------------------
ИТОГО: 3332.86 USD

> show-portfolio --base EUR
```

### Покупка и продажа

```text
> buy --currency BTC --amount 0.05
Покупка выполнена: 0.0500 BTC по курсу 59337.21 USD/BTC
Изменения в портфеле:
- BTC: было 0.0000 → стало 0.0500
Оценочная стоимость покупки: 2966.86 USD

> sell --currency BTC --amount 0.01
Продажа выполнена: 0.0100 BTC по курсу 59337.21 USD/BTC
Изменения в портфеле:
- BTC: было 0.0500 → стало 0.0400
Оценочная выручка: 593.37 USD
```

### Курсы валют

```text
> get-rate --from BTC --to USD
Курс BTC→USD: 59337.21000000 (обновлено: 2026-10-25T00:00:00Z)
Обратный курс USD→BTC: 0.00001685
```

### Parser Service

```text
> update-rates
Обновлено курсов: 3
Последнее обновление: 2026-10-25T17:29:53+00:00

> update-rates --source coingecko
> update-rates --source exchangerate

> show-rates
Курсы из кеша (обновлено: 2026-10-25T17:29:54+00:00):
- BTC_USD: 80669.0
- ETH_USD: 2355.05
- SOL_USD: 101.5

> show-rates --top 2
> show-rates --currency BTC
> show-rates --base USD
```

## Обработка ошибок

| Ситуация | Сообщение |
|---|---|
| Не залогинен | `Сначала выполните login` |
| Пользователь занят | `Имя пользователя 'alice' уже занято` |
| Неверный пароль | `Неверный пароль` |
| Недостаточно средств | `Недостаточно средств: доступно 0.04 BTC, требуется 0.05 BTC` |
| Неизвестная валюта | `Неизвестная валюта 'ABC'` |
| Нет курса | `Курс BTC→USD недоступен. Обновите кэш (update-rates).` |

## Кэш курсов и TTL

- `data/rates.json` — **снимок** последних курсов (по одному на пару).
- `data/exchange_rates.json` — **история** измерений с уникальными id.

TTL кэша задаётся в `SettingsLoader` (`RATES_TTL_SECONDS`, по умолчанию
**300 секунд**). Если кэш устарел — Core Service сообщает, что нужно
обновить (`update-rates`).

Обновление TTL через переменную окружения:

```bash
set VALUTATRADE_RATES_TTL_SECONDS=600
```

## Логирование

Логи пишутся в `logs/actions.log` с ротацией (1 МБ × 3 бэкапа).

Пример записи:

```
2026-10-25T17:29:53 INFO BUY user_id=1 currency='BTC' amount=0.05 result=OK
```

Декоратор `@log_action` применяется к `register`, `login`, `buy`, `sell`.

## Singleton

Два синглтона реализованы через `__new__`:

- **SettingsLoader** — конфигурация (пути, TTL, формат логов).
- **DatabaseManager** — доступ к JSON-файлам (атомарная запись tmp → rename).

Гарантируют единственный экземпляр в приложении.

## Разработка

```bash
# Проверка стиля
uv run ruff check .

# Запуск
uv run main.py
```

## Лицензия

Учебный проект. MIT.