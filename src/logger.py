"""Настройка централизованного JSON-логирования."""

from __future__ import annotations

import json
import logging
import os
from datetime import UTC, datetime
from typing import Any

SENSITIVE_SUBSTRINGS = ("token", "secret", "key", "hash", "session", "password")


class JsonFormatter(logging.Formatter):
    """Форматтер для вывода логов в JSON с маскированием секретов."""

    def format(self, record: logging.LogRecord) -> str:
        ts = datetime.now(tz=UTC).isoformat().replace("+00:00", "Z")
        context = getattr(record, "_context", {})
        payload: dict[str, Any] = {
            "ts": ts,
            "level": record.levelname.lower(),
            "msg": record.getMessage(),
            "context": sanitize_context(context),
        }
        return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def sanitize_context(context: dict[str, Any]) -> dict[str, Any]:
    """Маскирует секретные значения в контексте."""

    safe_context: dict[str, Any] = {}
    for key, value in context.items():
        lowered_key = key.lower()
        if any(fragment in lowered_key for fragment in SENSITIVE_SUBSTRINGS):
            safe_context[key] = "***"
        else:
            safe_context[key] = value
    return safe_context


class ContextLogger(logging.LoggerAdapter):
    """Адаптер для логгера, добавляющий контекст."""

    def process(self, msg: str, kwargs: dict[str, Any]) -> Any:
        context = kwargs.pop("context", {})
        kwargs.setdefault("extra", {})
        kwargs["extra"]["_context"] = context
        return msg, kwargs


def configure_logging() -> None:
    """Инициализирует корневой логгер при первом вызове."""

    root = logging.getLogger()
    if root.handlers:
        return

    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    level = os.getenv("LOG_LEVEL", "INFO").upper()
    root.setLevel(level)
    root.addHandler(handler)


def get_logger(name: str) -> ContextLogger:
    """Возвращает адаптированный логгер с контекстом."""

    configure_logging()
    logger = logging.getLogger(name)
    return ContextLogger(logger, {})
