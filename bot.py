"""Телеграм-бот, который каждый день в заданное время присылает в беседу
опрос «Играем в волейбол?» с вариантами Да / Нет / 50 на 50.

Запускается как один постоянный процесс: пока скрипт работает, встроенный
планировщик сам отправляет опрос в нужное время.
"""

import asyncio
import json
import logging
import os
import urllib.parse
import urllib.request
from datetime import datetime, time
from pathlib import Path
from zoneinfo import ZoneInfo

from telegram import BotCommand, Update
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

# Файл, где бот запоминает, что сегодня опрос уже вызывали вручную
# (переживает перезапуски бота).
STATE_FILE = Path(__file__).with_name("state.json")

# --- Погода (Open-Meteo, бесплатно и без ключа) --------------------------------
# Координаты: Железнодорожный (Балашиха), Московская область.
WEATHER_LAT = 55.744
WEATHER_LON = 38.017
# Игра около 17:30 — усредняем прогноз на 17:00 и 18:00.
WEATHER_HOURS = (17, 18)
WEATHER_LABEL = "к 17:30"

# Коды погоды WMO -> (описание, эмодзи)
WEATHER_DESCRIPTIONS = {
    0: ("ясно", "☀️"),
    1: ("почти ясно", "🌤"),
    2: ("переменная облачность", "⛅"),
    3: ("пасмурно", "☁️"),
    45: ("туман", "🌫"),
    48: ("туман", "🌫"),
    51: ("морось", "🌦"),
    53: ("морось", "🌦"),
    55: ("морось", "🌦"),
    61: ("небольшой дождь", "🌧"),
    63: ("дождь", "🌧"),
    65: ("сильный дождь", "🌧"),
    66: ("ледяной дождь", "🌧"),
    67: ("ледяной дождь", "🌧"),
    71: ("небольшой снег", "🌨"),
    73: ("снег", "🌨"),
    75: ("сильный снег", "🌨"),
    77: ("снег", "🌨"),
    80: ("ливень", "🌧"),
    81: ("ливень", "🌧"),
    82: ("сильный ливень", "🌧"),
    85: ("снегопад", "🌨"),
    86: ("снегопад", "🌨"),
    95: ("гроза", "⛈"),
    96: ("гроза с градом", "⛈"),
    99: ("гроза с градом", "⛈"),
}

# --- Логирование --------------------------------------------------------------

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


# --- Получение прогноза погоды --------------------------------------------------

def _fetch_weather_sync() -> str:
    """Запрашивает прогноз у Open-Meteo и возвращает строку для опроса."""
    params = urllib.parse.urlencode({
        "latitude": WEATHER_LAT,
        "longitude": WEATHER_LON,
        "hourly": "temperature_2m,precipitation_probability,weather_code",
        "forecast_days": 1,
        "timezone": "Europe/Moscow",
    })
    url = f"https://api.open-meteo.com/v1/forecast?{params}"
    with urllib.request.urlopen(url, timeout=6) as resp:
        hourly = json.load(resp)["hourly"]

    temps = [hourly["temperature_2m"][h] for h in WEATHER_HOURS]
    rain_probs = [hourly["precipitation_probability"][h] or 0 for h in WEATHER_HOURS]
    code = hourly["weather_code"][WEATHER_HOURS[0]]

    temp = round(sum(temps) / len(temps))
    rain = max(rain_probs)
    desc, emoji = WEATHER_DESCRIPTIONS.get(code, ("", "🌡"))

    line = f"Погода {WEATHER_LABEL}: {temp:+d}° {emoji} {desc}".rstrip()
    if rain >= 20:
        line += f", вероятность осадков {rain}%"
    return line


async def with_weather(question: str) -> str:
    """Добавляет к вопросу опроса строку с прогнозом. Если погода недоступна,
    опрос уходит без неё — сам опрос важнее."""
    try:
        weather = await asyncio.to_thread(_fetch_weather_sync)
    except Exception as exc:
        logger.warning("Не удалось получить погоду: %s", exc)
        return question
    return f"{question}\n\n{weather}"


# --- Учёт ручных опросов (чтобы не спамить) -----------------------------------

def _today() -> str:
    return datetime.now(TIMEZONE).date().isoformat()


def mark_manual_poll() -> None:
    """Запоминает, что сегодня в основной беседе опрос уже вызывали вручную."""
    STATE_FILE.write_text(json.dumps({"last_manual_poll": _today()}))


def manual_poll_sent_today() -> bool:
    try:
        data = json.loads(STATE_FILE.read_text())
    except (FileNotFoundError, ValueError):
        return False
    return data.get("last_manual_poll") == _today()


# --- Отправка опроса ----------------------------------------------------------

async def send_volleyball_poll(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Ежедневный опрос по расписанию. Пропускается, если сегодня опрос
    уже вызывали вручную командой (/poll, /ab или /pest)."""
    chat_id = context.job.chat_id
    if manual_poll_sent_today():
        logger.info(
            "Ежедневный опрос пропущен: сегодня опрос уже вызывали вручную."
        )
        return
    await context.bot.send_poll(
        chat_id=chat_id,
        question=await with_weather(QUESTION),
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
        chat_id = update.effective_chat.id
        await context.bot.send_poll(
            chat_id=chat_id,
            question=await with_weather(question),
            options=OPTIONS,
            is_anonymous=False,
            allows_multiple_answers=False,
        )
        # Если опрос вызвали в основной беседе — сегодня автоматический
        # опрос в 12:00 уже не нужен.
        if str(chat_id) == os.environ.get("CHAT_ID", ""):
            mark_manual_poll()
            logger.info("Ручной опрос в основной беседе — дневной опрос сегодня отменён.")

    return handler


# --- Запуск -------------------------------------------------------------------

async def register_commands(application: Application) -> None:
    """Регистрирует список команд у Телеграма, чтобы при вводе «/» в чате
    выпадало меню с подсказками."""
    commands = [
        BotCommand("poll", "опрос «Играем сегодня в волейбол?»"),
        *[BotCommand(cmd, f"опрос «{title}»") for cmd, title in EXTRA_POLLS.items()],
        BotCommand("chatid", "показать ID этого чата"),
        BotCommand("help", "справка"),
    ]
    await application.bot.set_my_commands(commands)
    logger.info("Меню команд зарегистрировано: %s", [c.command for c in commands])


def main() -> None:
    token = os.environ.get("BOT_TOKEN")
    if not token:
        raise SystemExit(
            "Не задан BOT_TOKEN. Получи токен у @BotFather и установи переменную окружения.\n"
            "Пример: export BOT_TOKEN='123456:ABC...'"
        )

    application = Application.builder().token(token).post_init(register_commands).build()

    application.add_handler(CommandHandler(["start", "help"], cmd_start))
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
