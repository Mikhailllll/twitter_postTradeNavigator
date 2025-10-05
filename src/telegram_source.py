"""Получение сообщений из Telegram-канала Binance."""

from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass

from telethon import TelegramClient
from telethon.errors import FloodWaitError, RPCError
from telethon.sessions import StringSession
from tenacity import (
    AsyncRetrying,
    RetryError,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from .logger import get_logger


@dataclass(slots=True)
class TelegramMessage:
    """Структура сообщения, полученного из Telegram."""

    message_id: int
    text: str
    date: str


class TelegramSource:
    """Источник сообщений из Telegram-канала Binance."""

    def __init__(self, *, timeout: float = 10.0, fetch_limit: int = 50) -> None:
        self.api_id = int(_get_env("API_ID", aliases=("TELETHON_API_ID",)))
        self.api_hash = _get_env("API_HASH", aliases=("TELETHON_API_HASH",))
        self.string_session = _get_env("STRING_SESSION", aliases=("TELETHON_SESSION",))
        self.channel = _get_env("TELEGRAMCANALISTOCHNIK")
        self.timeout = timeout
        self.fetch_limit = fetch_limit
        self.logger = get_logger(__name__)

    async def fetch_new_messages(
        self, *, last_seen_id: int | None
    ) -> list[TelegramMessage]:
        """Возвращает новые сообщения, опубликованные после указанного идентификатора."""

        messages: list[TelegramMessage] = []
        try:
            async for attempt in AsyncRetrying(
                wait=wait_exponential(multiplier=1, min=1, max=60),
                stop=stop_after_attempt(5),
                retry=retry_if_exception_type(
                    (FloodWaitError, RPCError, asyncio.TimeoutError)
                ),
                reraise=True,
            ):
                with attempt:
                    self.logger.info(
                        "Запрос новых сообщений",
                        context={"channel": self.channel, "last_seen_id": last_seen_id},
                    )
                    batch = await self._fetch_once(last_seen_id=last_seen_id)
                    messages.extend(batch)
                    break
        except RetryError as exc:
            self.logger.error(
                "Не удалось получить сообщения из Telegram",
                context={
                    "channel": self.channel,
                    "error": str(exc.last_attempt.exception()),
                },
            )
            raise

        return sorted(messages, key=lambda msg: msg.message_id)

    async def _fetch_once(self, *, last_seen_id: int | None) -> list[TelegramMessage]:
        client = TelegramClient(
            StringSession(self.string_session),
            self.api_id,
            self.api_hash,
            connection_retries=3,
            retry_delay=2,
            timeout=self.timeout,
        )

        await client.connect()
        try:
            entity = await client.get_entity(self.channel)
            collected: list[TelegramMessage] = []
            async for message in client.iter_messages(entity, limit=self.fetch_limit):
                if message.message is None:
                    continue
                if last_seen_id and message.id <= last_seen_id:
                    break
                collected.append(
                    TelegramMessage(
                        message_id=message.id,
                        text=message.message,
                        date=message.date.isoformat() if message.date else "",
                    )
                )
            self.logger.info(
                "Получено сообщений",
                context={"count": len(collected), "channel": self.channel},
            )
            return collected
        finally:
            await client.disconnect()


def _get_env(name: str, *, aliases: tuple[str, ...] = ()) -> str:
    """Возвращает обязательную переменную окружения с учётом синонимов."""

    for candidate in (name, *aliases):
        value = os.getenv(candidate)
        if value:
            return value

    names = " | ".join((name, *aliases))
    raise RuntimeError(f"Не задана переменная окружения из списка: {names}")
