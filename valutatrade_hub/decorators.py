"""Декораторы ValutaTrade Hub."""

import functools
import time
from typing import Callable

from valutatrade_hub.logging_config import get_logger


def log_action(action: str, verbose: bool = False) -> Callable:
    """Логирует вызов функции на уровне INFO.

    Args:
        action: имя операции (BUY, SELL, REGISTER, LOGIN).
        verbose: если True — логирует ещё и время выполнения.
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            log = get_logger()
            start = time.perf_counter()

            ctx_keys = (
                "username",
                "user_id",
                "currency",
                "currency_code",
                "amount",
                "from_code",
                "to_code",
            )
            ctx_parts = [
                f"{key}={kwargs[key]!r}" for key in ctx_keys if key in kwargs
            ]
            context = " ".join(ctx_parts)

            try:
                result = func(*args, **kwargs)
            except Exception as exc:
                elapsed_ms = (time.perf_counter() - start) * 1000
                log.info(
                    "%s %s result=ERROR error_type=%s error=%r elapsed_ms=%.1f",
                    action,
                    context,
                    type(exc).__name__,
                    str(exc),
                    elapsed_ms,
                )
                raise

            elapsed_ms = (time.perf_counter() - start) * 1000
            if verbose:
                log.info(
                    "%s %s result=OK elapsed_ms=%.1f",
                    action,
                    context,
                    elapsed_ms,
                )
            else:
                log.info("%s %s result=OK", action, context)
            return result

        return wrapper

    return decorator