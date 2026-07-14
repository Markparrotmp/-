# 💌 Daily Compliment Bot

Телеграм-бот, который каждое утро присылает любимой девушке развёрнутый, тёплый
комплимент и добрую открытку.

## Как это работает

- **Текст** сочиняет Claude (модель `claude-opus-4-8`): каждый день — новый
  развёрнутый комплимент из 4–6 предложений с пожеланием на день. Если ключ
  Claude API не задан или запрос не удался, берётся комплимент из запасного
  списка на 30 дней (`compliments.py`) — бот не пропустит ни одного утра.
- **Открытка** рисуется программно (`postcard.py`): мягкий градиент, боке,
  сердечки и короткая тёплая надпись. Палитра и надпись меняются по дате —
  7 цветовых тем и 10 фраз, так что открытки не повторяются подряд.
- **Расписание** — GitHub Actions запускает отправку каждый день в 09:00 по
  Москве (`.github/workflows/daily-compliment.yml`).

## Настройка

### 1. Создайте бота

1. Напишите [@BotFather](https://t.me/BotFather) в Telegram → `/newbot`.
2. Придумайте имя и username, получите **токен** вида `123456:ABC-DEF...`.

### 2. Узнайте chat_id

1. Девушка должна написать боту любое сообщение (например, `/start`) —
   иначе бот не сможет писать ей первым.
2. Откройте в браузере:
   `https://api.telegram.org/bot<ТОКЕН>/getUpdates`
3. В ответе найдите `"chat":{"id": 123456789, ...}` — это и есть **chat_id**.

### 3. Добавьте секреты в репозиторий

GitHub → Settings → Secrets and variables → Actions:

| Тип | Имя | Значение |
|---|---|---|
| Secret | `COMPLIMENT_BOT_TOKEN` | токен от BotFather |
| Secret | `COMPLIMENT_CHAT_ID` | chat_id получательницы |
| Secret | `ANTHROPIC_API_KEY` | ключ с [platform.claude.com](https://platform.claude.com) (необязательно, но с ним тексты каждый день уникальные) |
| Variable | `HER_NAME` | имя, как вы её называете (необязательно, по умолчанию «солнышко») |

### 4. Проверьте вручную

GitHub → Actions → **Daily compliment** → **Run workflow**. Через минуту
сообщение с открыткой придёт в Telegram.

## Изменить время отправки

В `.github/workflows/daily-compliment.yml` поправьте cron (время в UTC):

```yaml
- cron: "0 6 * * *"   # 06:00 UTC = 09:00 МСК
```

Например, `"30 4 * * *"` — это 07:30 по Москве.

## Запуск локально

```bash
pip install -r requirements.txt
export TELEGRAM_BOT_TOKEN=...
export TELEGRAM_CHAT_ID=...
export ANTHROPIC_API_KEY=...   # необязательно
export HER_NAME=Катя           # необязательно
python send_compliment.py
```

Только открытка, без отправки: `python postcard.py` → `postcard.png`.

## Перенос в отдельный репозиторий

Проект полностью автономен. Чтобы вынести его в свой репозиторий:

```bash
# создайте пустой репозиторий на GitHub, например daily-compliment-bot, затем:
git clone https://github.com/<вы>/<текущий-репозиторий>.git tmp
cd tmp
mkdir -p new/.github/workflows
cp -r compliment-bot/* new/
cp .github/workflows/daily-compliment.yml new/.github/workflows/
cd new
# в workflow уберите префикс compliment-bot/ из путей
git init && git add -A && git commit -m "Daily compliment bot"
git remote add origin https://github.com/<вы>/daily-compliment-bot.git
git push -u origin main
```

После переноса заново добавьте секреты в настройках нового репозитория.
