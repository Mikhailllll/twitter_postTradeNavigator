"""Клиент для взаимодействия с DeepSeek API."""

from __future__ import annotations

import os

import httpx
from tenacity import (
    AsyncRetrying,
    RetryError,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from .logger import get_logger
from .text_rules import contains_cyrillic

DEFAULT_MODEL = "deepseek-chat"


class DeepSeekClient:
    """Асинхронный клиент DeepSeek для перевода и перефразирования."""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str = DEFAULT_MODEL,
        request_timeout: float = 20.0,
    ) -> None:
        self.api_key = api_key or _get_env("DEEPSEEK_API_KEY")
        self.base_url = base_url or os.getenv(
            "DEEPSEEK_BASE_URL", "https://api.deepseek.com"
        )
        self.model = model
        self.timeout = httpx.Timeout(10.0, read=request_timeout)
        self.logger = get_logger(__name__)

    async def ensure_localization(self, *, text: str) -> str:
        """Переводит или перефразирует текст, если отсутствует кириллица."""

        if contains_cyrillic(text):
            return text

        request_payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": "Ты — аналитик Binance. Переведи или кратко перефразируй текст на русский язык, сохранив ключевые факты и числа.",
                },
                {"role": "user", "content": text},
            ],
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        try:
            async for attempt in AsyncRetrying(
                wait=wait_exponential(multiplier=1, min=1, max=30),
                stop=stop_after_attempt(4),
                retry=retry_if_exception_type(
                    (
                        httpx.TransportError,
                        httpx.HTTPStatusError,
                        httpx.TimeoutException,
                    )
                ),
                reraise=True,
            ):
                with attempt:
                    async with httpx.AsyncClient(
                        base_url=self.base_url, timeout=self.timeout
                    ) as client:
                        response = await client.post(
                            "/v1/chat/completions",
                            json=request_payload,
                            headers=headers,
                        )
                        response.raise_for_status()
                        data = response.json()
                        completion = data["choices"][0]["message"]["content"].strip()
                        self.logger.info(
                            "Получен ответ DeepSeek",
                            context={
                                "model": self.model,
                                "status_code": response.status_code,
                            },
                        )
                        return completion
        except RetryError as exc:
            error = exc.last_attempt.exception()
            self.logger.error(
                "Ошибка обращения к DeepSeek",
                context={"error": str(error), "model": self.model},
            )
            raise

        return text


def _get_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Не задана переменная окружения {name}")
    return value
