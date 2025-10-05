"""Правила обработки текста для твитов."""

from __future__ import annotations

import re
import textwrap
from collections.abc import Iterable

MAX_TWEET_LENGTH = 280
BINANCE_LINKS_BLOCK = (
    "Полезные ссылки Binance:\n"
    "• Биржа: https://www.binance.com\n"
    "• Поддержка: https://www.binance.com/support\n"
    "• Академия: https://academy.binance.com"
)

EMOJI_KEYWORDS = {
    "листинг": "🆕",
    "listing": "🆕",
    "launchpool": "🚀",
    "maintenance": "🛠️",
    "upgrade": "🔧",
    "update": "🔄",
    "airdrop": "🎁",
    "bonus": "💰",
    "binance": "🟡",
}

CYRILLIC_PATTERN = re.compile("[А-Яа-яЁё]")
HASHTAG_WORD_PATTERN = re.compile(r"[A-Za-z0-9]{3,}")


def contains_cyrillic(text: str) -> bool:
    """Проверяет наличие кириллических символов."""

    return bool(CYRILLIC_PATTERN.search(text))


def insert_emojis(text: str) -> str:
    """Добавляет релевантные эмодзи в начало текста."""

    lowered = text.lower()
    emojis: list[str] = []
    for keyword, emoji in EMOJI_KEYWORDS.items():
        if keyword in lowered:
            emojis.append(emoji)
    if not emojis:
        emojis.append("📢")
    emojis_str = " ".join(dict.fromkeys(emojis))
    return f"{emojis_str} {text}".strip()


def generate_hashtags(text: str, *, limit: int = 2) -> list[str]:
    """Генерирует до двух хэштегов на основе текста."""

    candidates = []
    for match in HASHTAG_WORD_PATTERN.finditer(text):
        word = match.group(0)
        if word.isdigit():
            continue
        candidates.append(word.lower())
    unique: list[str] = []
    for candidate in candidates:
        if candidate not in unique:
            unique.append(candidate)
    hashtags = [
        candidate.replace("/", "").replace("-", "") for candidate in unique[:limit]
    ]
    return [f"#{tag}" for tag in hashtags]


def build_thread(*, message_id: int, text: str, hashtags: Iterable[str]) -> list[str]:
    """Формирует твит-нитку с ссылкой на оригинал и блоком ссылок Binance."""

    base_text = insert_emojis(text)
    source_link = f"Источник: https://t.me/binance_announcements/{message_id}"
    main_body = f"{base_text}\n\n{source_link}".strip()

    tweets = _chunk_text(main_body)
    if not tweets and main_body:
        tweets = [main_body]

    hashtags_line = " ".join(hashtags).strip()
    if hashtags_line and tweets:
        if len(tweets[-1]) + 2 + len(hashtags_line) <= MAX_TWEET_LENGTH:
            tweets[-1] = f"{tweets[-1]}\n\n{hashtags_line}"
        else:
            tweets.append(hashtags_line)

    for tail in _chunk_text(BINANCE_LINKS_BLOCK):
        tweets.append(tail)

    return tweets


def _chunk_text(text: str) -> list[str]:
    """Разбивает текст на части, подходящие для Twitter."""

    normalized = text.replace("\r\n", "\n").strip()
    if not normalized:
        return []

    chunks: list[str] = []
    paragraphs = normalized.split("\n\n")
    for paragraph in paragraphs:
        lines = textwrap.wrap(
            paragraph,
            width=MAX_TWEET_LENGTH,
            break_long_words=False,
            break_on_hyphens=False,
        )
        if not lines:
            continue
        for line in lines:
            if not chunks:
                chunks.append(line)
                continue
            candidate = f"{chunks[-1]}\n\n{line}"
            if len(candidate) <= MAX_TWEET_LENGTH:
                chunks[-1] = candidate
            else:
                chunks.append(line)
    return chunks
