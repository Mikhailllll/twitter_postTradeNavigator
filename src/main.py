"""Точка входа для публикации обновлений Binance в Twitter."""

from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

from .deepseek_client import DeepSeekClient
from .logger import get_logger
from .state_store import StateStore
from .telegram_source import TelegramSource
from .text_rules import build_thread, generate_hashtags
from .twitter_client import TwitterClient

logger = get_logger(__name__)


async def run(*, dry_run: bool) -> None:
    """Основной сценарий обработки сообщений."""

    state_store = StateStore(Path("state.json"))
    state = state_store.read()
    telegram_source = TelegramSource()
    deepseek_client = DeepSeekClient()
    twitter_client = TwitterClient(dry_run=dry_run)

    messages = await telegram_source.fetch_new_messages(last_seen_id=state.last_seen_id)
    if not messages:
        logger.info("Новых сообщений нет", context={"last_seen_id": state.last_seen_id})
        return

    for message in messages:
        localized_text = await deepseek_client.ensure_localization(text=message.text)
        hashtags = generate_hashtags(localized_text)
        thread = build_thread(
            message_id=message.message_id, text=localized_text, hashtags=hashtags
        )
        tweet_ids = await twitter_client.post_thread(thread)
        if tweet_ids:
            state_store.update_last_seen(message_id=message.message_id, dry_run=dry_run)
            logger.info(
                "Сообщение опубликовано",
                context={"message_id": message.message_id, "tweets": tweet_ids},
            )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Публикация новостей Binance в Twitter"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Не отправлять твиты и не сохранять состояние",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    asyncio.run(run(dry_run=args.dry_run))


if __name__ == "__main__":
    main()
