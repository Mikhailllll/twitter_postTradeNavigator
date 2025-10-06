"""Тесты для правил обработки текста."""

from __future__ import annotations

from src import text_rules


def test_contains_cyrillic_detection():
    assert text_rules.contains_cyrillic("Тестовое сообщение")
    assert not text_rules.contains_cyrillic("Binance listing soon")


def test_generate_hashtags_limits():
    result = text_rules.generate_hashtags("Binance launches new listing on Launchpool")
    assert len(result) <= 2
    assert all(tag.startswith("#") for tag in result)


def test_build_thread_includes_links():
    hashtags = ["#binance", "#listing"]
    tweets = text_rules.build_thread(
        message_id=123, text="Binance listing update", hashtags=hashtags
    )
    assert any("https://t.me/binance_announcements/123" in tweet for tweet in tweets)
    assert any("Полезные ссылки Binance" in tweet for tweet in tweets)
    assert all(len(tweet) <= text_rules.MAX_TWEET_LENGTH for tweet in tweets)


def test_build_thread_trims_hashtags_and_long_lines():
    long_word = "A" * 600
    hashtags = ["#" + "b" * 200, "#" + "c" * 200]
    tweets = text_rules.build_thread(
        message_id=42,
        text=f"{long_word} end",
        hashtags=hashtags,
    )
    assert tweets, "Ожидаем хотя бы один твит"
    assert all(len(tweet) <= text_rules.MAX_TWEET_LENGTH for tweet in tweets)
    assert all(len(part) <= text_rules.MAX_TWEET_LENGTH for part in tweets)
