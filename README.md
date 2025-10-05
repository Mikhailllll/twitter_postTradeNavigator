# Twitter Post Trade Navigator

Сервис автоматически преобразует объявления из Telegram-канала [@binance_announcements](https://t.me/binance_announcements) и публикует их в Twitter с учётом лимита символов и правил оформления.

## Возможности

- Получение новых сообщений из Telegram через Telethon с учётом ретраев и таймаутов.
- Условный перевод или перефразирование англоязычных сообщений с помощью DeepSeek.
- Правила форматирования текста: эмодзи, хэштеги, ссылка на оригинал и блок полезных ссылок Binance.
- Публикация твит-ниток через Twitter API v2 (OAuth2 PKCE) с автоматическим обновлением токена.
- Хранение состояния обработанных сообщений в `state.json`.
- Централизованное JSON-логирование и модульные тесты (pytest).

## Подготовка окружения

1. Установите зависимости:
   ```bash
   python3.11 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
2. Заполните переменные окружения (пример в `.env.example`):
   - `API_ID`, `API_HASH`, `STRING_SESSION`, `TELEGRAMCANALISTOCHNIK`
   - `DEEPSEEK_API_KEY`
   - `TWITTER_CLIENT_ID`, `TWITTER_REFRESH_TOKEN`, `TWITTER_REDIRECT_URI`
   - при необходимости настройте `LOG_LEVEL`

Создайте файл `.env` или используйте секреты CI/CD.

## Запуск

```bash
python -m src.main --dry-run  # прогон без публикации и сохранения состояния
python -m src.main            # полноценный запуск
```

## Тестирование и качество

```bash
pytest
ruff check src tests
black --check src tests
```

## Структура проекта

```
src/
  deepseek_client.py    # обёртка DeepSeek API
  logger.py             # JSON-логирование
  main.py               # точка входа
  state_store.py        # работа с state.json
  telegram_source.py    # интеграция с Telegram
  text_rules.py         # правила форматирования
  twitter_client.py     # публикация в Twitter
state.json              # текущее состояние
```

## Переменные окружения

Критичные переменные проверяются на старте модулей, при отсутствии будет выброшено исключение с подсказкой.
