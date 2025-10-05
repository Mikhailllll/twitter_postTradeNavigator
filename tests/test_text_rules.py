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
