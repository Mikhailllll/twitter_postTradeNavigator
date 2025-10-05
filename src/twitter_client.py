"""Публикация твитов через Twitter API v2."""

from __future__ import annotations

import os
import time
from collections.abc import Iterable

import httpx
from tenacity import (
    AsyncRetrying,
    RetryError,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from .logger import get_logger

TOKEN_URL = "https://api.twitter.com/2/oauth2/token"
TWEET_URL = "https://api.twitter.com/2/tweets"


class TwitterClient:
    """Публикует твиты и управляет OAuth2-токенами."""

    def __init__(self, *, dry_run: bool = False, timeout: float = 10.0) -> None:
        self.dry_run = dry_run
        if self.dry_run:
            self.client_id = _get_optional_env(
                "TWITTER_CLIENT_ID", aliases=("TWITTER_API_KEY",)
            )
            self.refresh_token = _get_optional_env(
                "TWITTER_REFRESH_TOKEN", aliases=("TWITTER_ACCESS_TOKEN",)
            )
        else:
            self.client_id = _get_env(
                "TWITTER_CLIENT_ID", aliases=("TWITTER_API_KEY",)
            )
            self.refresh_token = _get_env(
                "TWITTER_REFRESH_TOKEN", aliases=("TWITTER_ACCESS_TOKEN",)
            )
        self.redirect_uri = os.getenv("TWITTER_REDIRECT_URI", "https://localhost")
        self.timeout = httpx.Timeout(10.0, read=timeout)
        self.logger = get_logger(__name__)
        self._access_token: str | None = None
        self._expires_at: float = 0.0

    async def post_thread(self, tweets: Iterable[str]) -> list[str]:
        """Публикует последовательность твитов с учетом ответов."""

        tweet_ids: list[str] = []
        previous_id: str | None = None
        for text in tweets:
            payload = {"text": text}
            if previous_id:
                payload["reply"] = {"in_reply_to_tweet_id": previous_id}
            tweet_id = await self._create_tweet(payload=payload)
            if tweet_id:
                previous_id = tweet_id
                tweet_ids.append(tweet_id)
        return tweet_ids

    async def _create_tweet(self, *, payload: dict) -> str | None:
        if self.dry_run:
            self.logger.info(
                "DRY_RUN: твит не отправлен",
                context={"text": payload.get("text", "")[:50]},
            )
            return "dry-run"

        access_token = await self._get_access_token()
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

        try:
            async for attempt in AsyncRetrying(
                wait=wait_exponential(multiplier=1, min=1, max=30),
                stop=stop_after_attempt(5),
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
                    async with httpx.AsyncClient(timeout=self.timeout) as client:
                        response = await client.post(
                            TWEET_URL, json=payload, headers=headers
                        )
                        response.raise_for_status()
                        data = response.json()
                        tweet_id = data.get("data", {}).get("id")
                        self.logger.info(
                            "Твит опубликован",
                            context={"tweet_id": tweet_id},
                        )
                        return tweet_id
        except RetryError as exc:
            error = exc.last_attempt.exception()
            self.logger.error(
                "Ошибка отправки твита",
                context={"error": str(error)},
            )
            raise
        return None

    async def _get_access_token(self) -> str:
        if not self._access_token or time.time() >= self._expires_at - 60:
            await self._refresh_access_token()
        assert self._access_token is not None
        return self._access_token

    async def _refresh_access_token(self) -> None:
        data = {
            "grant_type": "refresh_token",
            "refresh_token": self.refresh_token,
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
        }

        try:
            async for attempt in AsyncRetrying(
                wait=wait_exponential(multiplier=1, min=1, max=60),
                stop=stop_after_attempt(5),
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
                    async with httpx.AsyncClient(timeout=self.timeout) as client:
                        response = await client.post(TOKEN_URL, data=data)
                        response.raise_for_status()
                        payload = response.json()
                        self._access_token = payload.get("access_token")
                        expires_in = int(payload.get("expires_in", 3600))
                        self._expires_at = time.time() + expires_in
                        if "refresh_token" in payload:
                            self.refresh_token = payload["refresh_token"]
                        self.logger.info(
                            "Токен обновлён",
                            context={"expires_in": expires_in},
                        )
                        return
        except RetryError as exc:
            error = exc.last_attempt.exception()
            self.logger.error(
                "Не удалось обновить токен",
                context={"error": str(error)},
            )
            raise


def _get_env(name: str, *, aliases: tuple[str, ...] = ()) -> str:
    """Возвращает значение переменной окружения с поддержкой синонимов."""

    for candidate in (name, *aliases):
        value = os.getenv(candidate)
        if value:
            return value

    names = " | ".join((name, *aliases))
    raise RuntimeError(f"Не задана переменная окружения из списка: {names}")


def _get_optional_env(name: str, *, aliases: tuple[str, ...] = ()) -> str | None:
    """Возвращает необязательную переменную окружения, если она задана."""

    for candidate in (name, *aliases):
        value = os.getenv(candidate)
        if value:
            return value
    return None
