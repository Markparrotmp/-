"""Телеграм-бот, который каждый день в заданное время присылает в беседу
опрос «Играем в волейбол?» с вариантами Да / Нет / 50 на 50.

Запускается как один постоянный процесс: пока скрипт работает, встроенный
планировщик сам отправляет опрос в нужное время.
"""

import logging
import os
from datetime import time
from zoneinfo import ZoneInfo

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# --- Настройки опроса ---------------------------------------------------------

QUESTION = "Играем сегодня в волейбол? 🏐"
OPTIONS = ["Да ✅", "Нет ❌", "50 на 50 🤔"]

# Дополнительные опросы, которые создаются командами: /ab -> «аб», /pest -> «пест».
# Чтобы добавить новый опрос, просто допиши строку: "команда": "название опроса".
EXTRA_POLLS = {
    "ab": "аб",
    "pest": "пест",
}

# Часовой пояс и время ежедневной отправки (12:00 по Москве).
TIMEZONE = ZoneInfo("Europe/Moscow")
POLL_TIME = time(hour=12, minute=0, tzinfo=TIMEZONE)

# --- Логирование --------------------------------------------------------------

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


# --- Отправка опроса ----------------------------------------------------------

async def send_volleyball_poll(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Отправляет опрос в беседу. Вызывается планировщиком и командой /poll."""
    chat_id = context.job.chat_id
    await context.bot.send_poll(
        chat_id=chat_id,
        question=QUESTION,
        options=OPTIONS,
        is_anonymous=False,  # видно, кто как проголосовал
        allows_multiple_answers=False,
    )
    logger.info("Опрос отправлен в чат %s", chat_id)


# --- Команды ------------------------------------------------------------------

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Приветствие и краткая справка."""
    extra = "\n".join(f"/{cmd} — опрос «{title}»" for cmd, title in EXTRA_POLLS.items())
    await update.effective_message.reply_text(
        "Привет! Я бот для волейбольной беседы. 🏐\n\n"
        "Каждый день в 12:00 по Москве я присылаю опрос: играем сегодня или нет.\n\n"
        "Команды:\n"
        "/poll — отправить ежедневный опрос прямо сейчас\n"
        f"{extra}\n"
        "/chatid — узнать ID этого чата (нужно для настройки)"
    )


async def cmd_chatid(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показывает ID текущего чата — его нужно записать в переменную CHAT_ID."""
    chat = update.effective_chat
    await update.effective_message.reply_text(
        f"ID этого чата: `{chat.id}`\n"
        "Впиши его в переменную окружения CHAT_ID и перезапусти бота.",
        parse_mode="Markdown",
    )


def make_poll_command(question: str):
    """Возвращает обработчик команды, отправляющий опрос с заданным вопросом."""

    async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        await context.bot.send_poll(
            chat_id=update.effective_chat.id,
            question=question,
            options=OPTIONS,
            is_anonymous=False,
            allows_multiple_answers=False,
        )

    return handler


# --- Запуск -------------------------------------------------------------------

def main() -> None:
    token = os.environ.get("BOT_TOKEN")
    if not token:
        raise SystemExit(
            "Не задан BOT_TOKEN. Получи токен у @BotFather и установи переменную окружения.\n"
            "Пример: export BOT_TOKEN='123456:ABC...'"
        )

    application = Application.builder().token(token).build()

    application.add_handler(CommandHandler("start", cmd_start))
    application.add_handler(CommandHandler("chatid", cmd_chatid))
    application.add_handler(CommandHandler("poll", make_poll_command(QUESTION)))
    for cmd, title in EXTRA_POLLS.items():
        application.add_handler(CommandHandler(cmd, make_poll_command(title)))

    # Планируем ежедневную отправку, если известен ID чата.
    chat_id = os.environ.get("CHAT_ID")
    if chat_id:
        application.job_queue.run_daily(
            send_volleyball_poll,
            time=POLL_TIME,
            chat_id=int(chat_id),
            name="daily_volleyball_poll",
        )
        logger.info(
            "Ежедневный опрос запланирован на %s (%s) в чат %s",
            POLL_TIME.strftime("%H:%M"),
            TIMEZONE.key,
            chat_id,
        )
    else:
        logger.warning(
            "CHAT_ID не задан — ежедневный опрос не запланирован. "
            "Добавь бота в беседу, вызови /chatid, впиши ID в CHAT_ID и перезапусти."
        )

    logger.info("Бот запущен. Нажми Ctrl+C для остановки.")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
