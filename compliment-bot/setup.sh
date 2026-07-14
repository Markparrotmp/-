#!/usr/bin/env bash
# Автоустановка бота-комплиментщика на сервер Ubuntu/Debian.
# Запуск от root одной командой:
#   bash <(curl -fsSL https://raw.githubusercontent.com/Markparrotmp/-/main/compliment-bot/setup.sh)
# Скрипт можно запускать повторно — он обновит бота и перечитает настройки.

set -euo pipefail

REPO_URL="https://github.com/Markparrotmp/-.git"
APP_DIR="/opt/complimentbot"
BOT_DIR="$APP_DIR/compliment-bot"

if [ "$(id -u)" -ne 0 ]; then
    echo "Запусти скрипт от root (на VPS ты и так root)." >&2
    exit 1
fi

echo "=== 1/5 Установка Python, git и шрифтов ==="
apt-get update -y
apt-get install -y python3-venv git fonts-dejavu-core

echo "=== 2/5 Загрузка кода бота ==="
if [ -d "$APP_DIR/.git" ]; then
    git -C "$APP_DIR" pull
else
    git clone "$REPO_URL" "$APP_DIR"
fi

echo "=== 3/5 Установка зависимостей ==="
[ -d "$APP_DIR/.venv" ] || python3 -m venv "$APP_DIR/.venv"
"$APP_DIR/.venv/bin/pip" install -q -r "$BOT_DIR/requirements.txt"

echo "=== 4/5 Настройка ==="
if [ -f "$BOT_DIR/.env" ]; then
    echo "Файл .env уже есть — оставляю как есть."
    echo "(Чтобы поменять настройки: nano $BOT_DIR/.env, затем ничего перезапускать не надо.)"
else
    read -rp "Вставь токен бота от @BotFather: " BOT_TOKEN
    read -rp "chat_id девушки: " CHAT_ID
    read -rp "Ключ Claude API [Enter = пропустить, будут готовые тексты]: " API_KEY
    read -rp "Её имя, как ты её называешь [Enter = «солнышко»]: " HER_NAME
    {
        printf 'TELEGRAM_BOT_TOKEN=%s\n' "$BOT_TOKEN"
        printf 'TELEGRAM_CHAT_ID=%s\n' "$CHAT_ID"
        printf 'ANTHROPIC_API_KEY=%s\n' "$API_KEY"
        printf 'HER_NAME=%s\n' "$HER_NAME"
    } > "$BOT_DIR/.env"
    chmod 600 "$BOT_DIR/.env"
fi

echo "=== 5/5 Включение расписания ==="
cp "$BOT_DIR/complimentbot.service" "$BOT_DIR/complimentbot.timer" /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now complimentbot.timer >/dev/null 2>&1

echo ""
read -rp "Отправить тестовый комплимент прямо сейчас? [Y/n]: " ANSWER
if [ "${ANSWER:-Y}" != "n" ] && [ "${ANSWER:-Y}" != "N" ]; then
    if systemctl start complimentbot.service; then
        echo "✅ Тестовый комплимент отправлен — проверь Telegram!"
    else
        echo "❌ Отправка не удалась. Логи:"
        journalctl -u complimentbot -n 20 --no-pager || true
        exit 1
    fi
fi

echo ""
echo "✅ Готово! Комплимент будет уходить каждый день в 09:00 по Москве,"
echo "   даже после перезагрузок сервера."
echo ""
echo "Полезное:"
echo "  ближайший запуск:  systemctl list-timers complimentbot.timer"
echo "  логи:              journalctl -u complimentbot -n 30"
echo "  отправить сейчас:  systemctl start complimentbot.service"
echo "  сменить время:     nano /etc/systemd/system/complimentbot.timer"
echo "                     затем: systemctl daemon-reload"
