#!/usr/bin/env bash
# Автоустановка волейбольного бота на чистый сервер Ubuntu/Debian.
# Запуск от root одной командой:
#   bash <(curl -fsSL https://raw.githubusercontent.com/Markparrotmp/-/main/setup.sh)
# Скрипт можно запускать повторно — он просто обновит бота и перезапустит его.

set -euo pipefail

REPO_URL="https://github.com/Markparrotmp/-.git"
APP_DIR="/opt/volleybot"
DEFAULT_CHAT_ID="-1002678776842"

if [ "$(id -u)" -ne 0 ]; then
    echo "Запусти скрипт от root (на VPS ты и так root)." >&2
    exit 1
fi

echo "=== 1/5 Установка Python и git ==="
apt-get update -y
apt-get install -y python3-venv git

echo "=== 2/5 Загрузка кода бота ==="
if [ -d "$APP_DIR/.git" ]; then
    git -C "$APP_DIR" pull
else
    git clone "$REPO_URL" "$APP_DIR"
fi
cd "$APP_DIR"

echo "=== 3/5 Установка зависимостей ==="
[ -d .venv ] || python3 -m venv .venv
.venv/bin/pip install -q -r requirements.txt

echo "=== 4/5 Настройка токена ==="
if [ -f .env ]; then
    echo "Файл .env уже есть — оставляю как есть."
else
    read -rp "Вставь токен бота от @BotFather: " BOT_TOKEN
    read -rp "ID чата [Enter = ${DEFAULT_CHAT_ID}]: " CHAT_ID
    CHAT_ID="${CHAT_ID:-$DEFAULT_CHAT_ID}"
    printf 'BOT_TOKEN=%s\nCHAT_ID=%s\n' "$BOT_TOKEN" "$CHAT_ID" > .env
    chmod 600 .env
fi

echo "=== 5/5 Запуск службы ==="
cp volleybot.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable volleybot >/dev/null 2>&1
systemctl restart volleybot
sleep 3

if systemctl is-active --quiet volleybot; then
    echo ""
    echo "✅ Готово! Бот запущен и будет стартовать сам после перезагрузок."
    echo "Проверь: отправь /ab в волейбольную беседу."
    echo "Логи бота: journalctl -u volleybot -n 30"
else
    echo ""
    echo "❌ Бот не запустился. Посмотри логи:"
    journalctl -u volleybot -n 20 --no-pager || true
    exit 1
fi
