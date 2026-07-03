"""Отправляет ОДИН опрос в беседу и завершает работу.

Этот скрипт не нужно держать запущенным: его раз в день запускает GitHub
по расписанию (см. .github/workflows/volleyball-poll.yml). Использует только
стандартную библиотеку Python — ничего устанавливать не нужно.

Читает два значения из переменных окружения:
  BOT_TOKEN — токен бота от @BotFather
  CHAT_ID   — ID беседы, куда слать опрос
"""

import json
import os
import urllib.parse
import urllib.request

QUESTION = "Играем сегодня в волейбол? 🏐"
OPTIONS = ["Да ✅", "Нет ❌", "50 на 50 🤔"]


def main() -> None:
    token = os.environ.get("BOT_TOKEN")
    chat_id = os.environ.get("CHAT_ID")
    if not token or not chat_id:
        raise SystemExit("Нужны переменные окружения BOT_TOKEN и CHAT_ID.")

    url = f"https://api.telegram.org/bot{token}/sendPoll"
    payload = {
        "chat_id": chat_id,
        "question": QUESTION,
        # Текущий формат Bot API: список объектов {"text": ...}
        "options": json.dumps([{"text": o} for o in OPTIONS], ensure_ascii=False),
        "is_anonymous": "false",          # видно, кто голосовал
        "allows_multiple_answers": "false",
    }
    data = urllib.parse.urlencode(payload).encode("utf-8")

    with urllib.request.urlopen(urllib.request.Request(url, data=data)) as resp:
        body = json.load(resp)

    if not body.get("ok"):
        raise SystemExit(f"Ошибка Telegram API: {body}")
    print("Опрос отправлен.")


if __name__ == "__main__":
    main()
