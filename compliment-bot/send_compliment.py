# -*- coding: utf-8 -*-
"""Ежедневный комплимент с открыткой в Telegram.

Переменные окружения:
  TELEGRAM_BOT_TOKEN  — токен бота от @BotFather (обязательно)
  TELEGRAM_CHAT_ID    — chat_id получательницы (обязательно)
  ANTHROPIC_API_KEY   — ключ Claude API; если не задан или запрос не удался,
                        берётся комплимент из compliments.py
  HER_NAME            — имя (по умолчанию «солнышко»)
"""

import os
import sys
import time
from datetime import date

import requests

from compliments import FALLBACK_COMPLIMENTS
from postcard import make_postcard

TELEGRAM_CAPTION_LIMIT = 1024

WEEKDAYS = [
    "понедельник", "вторник", "среда", "четверг",
    "пятница", "суббота", "воскресенье",
]

MONTHS = [
    "января", "февраля", "марта", "апреля", "мая", "июня",
    "июля", "августа", "сентября", "октября", "ноября", "декабря",
]


def generate_with_claude(name: str, today: date) -> str | None:
    """Просит Claude сочинить развёрнутый комплимент. None — если не вышло."""
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return None
    try:
        import anthropic

        client = anthropic.Anthropic()
        date_str = f"{today.day} {MONTHS[today.month - 1]}, {WEEKDAYS[today.weekday()]}"
        response = client.messages.create(
            model="claude-opus-4-8",
            max_tokens=1024,
            system=(
                "Ты пишешь от лица любящего молодого человека утреннее сообщение "
                "его девушке. Пиши по-русски, тепло, искренне и без пошлости. "
                "Это должен быть развёрнутый, хорошо сложенный комплимент из "
                "4–6 предложений: с добрым утренним приветствием, конкретной "
                "похвалой её качествам (доброта, ум, красота, забота, сила — "
                "выбирай что-то одно и раскрывай) и тёплым пожеланием на день. "
                "Без хэштегов, без подписи, без кавычек вокруг текста. "
                "Можно 1–2 уместных эмодзи. Каждый день текст должен быть новым "
                "по теме и настроению."
            ),
            messages=[{
                "role": "user",
                "content": (
                    f"Сегодня {date_str}. Её зовут {name}. "
                    "Напиши сегодняшний комплимент."
                ),
            }],
        )
        if response.stop_reason == "refusal":
            return None
        text = "".join(b.text for b in response.content if b.type == "text").strip()
        return text or None
    except Exception as exc:  # noqa: BLE001 — при любой ошибке уходим на запасной список
        print(f"Claude API недоступен ({exc}); беру комплимент из запасного списка")
        return None


def fallback_compliment(name: str, today: date) -> str:
    idx = today.toordinal() % len(FALLBACK_COMPLIMENTS)
    return FALLBACK_COMPLIMENTS[idx].format(name=name)


def telegram_request(token: str, method: str, *, data=None, files=None) -> dict:
    url = f"https://api.telegram.org/bot{token}/{method}"
    last_error = None
    for attempt in range(4):
        try:
            resp = requests.post(url, data=data, files=files, timeout=30)
            payload = resp.json()
            if payload.get("ok"):
                return payload
            last_error = payload.get("description", resp.text)
        except requests.RequestException as exc:
            last_error = str(exc)
        time.sleep(2 ** attempt)
    raise RuntimeError(f"Telegram API: {method} не удался: {last_error}")


def send(token: str, chat_id: str, photo_path: str, text: str) -> None:
    if len(text) <= TELEGRAM_CAPTION_LIMIT:
        with open(photo_path, "rb") as photo:
            telegram_request(
                token, "sendPhoto",
                data={"chat_id": chat_id, "caption": text},
                files={"photo": photo},
            )
    else:
        with open(photo_path, "rb") as photo:
            telegram_request(
                token, "sendPhoto",
                data={"chat_id": chat_id},
                files={"photo": photo},
            )
        telegram_request(
            token, "sendMessage",
            data={"chat_id": chat_id, "text": text},
        )


def main() -> int:
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        print("Нужны переменные окружения TELEGRAM_BOT_TOKEN и TELEGRAM_CHAT_ID")
        return 1

    name = os.environ.get("HER_NAME", "солнышко")
    today = date.today()

    text = generate_with_claude(name, today) or fallback_compliment(name, today)
    photo_path = make_postcard("postcard.png", today)

    send(token, chat_id, photo_path, text)
    print("Комплимент и открытка отправлены ✨")
    return 0


if __name__ == "__main__":
    sys.exit(main())
