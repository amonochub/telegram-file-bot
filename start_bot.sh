#!/bin/bash

# Скрипт для запуска Telegram File Bot

echo "🚀 Запуск Telegram File Bot..."

# Проверяем, активировано ли виртуальное окружение
if [[ "$VIRTUAL_ENV" == "" ]]; then
    echo "📦 Активация виртуального окружения..."
    source .venv/bin/activate
fi

# Проверяем, запущен ли Redis
echo "🔍 Проверка Redis..."
if ! redis-cli ping > /dev/null 2>&1; then
    echo "⚠️ Redis не запущен. Запускаем Redis..."
    brew services start redis
    sleep 2
fi

# Проверяем переменные окружения
if [[ -z "$BOT_TOKEN" ]]; then
    echo "❌ Ошибка: BOT_TOKEN не установлен!"
    echo "📝 Установите переменную окружения BOT_TOKEN с вашим токеном бота"
    echo "💡 Пример: export BOT_TOKEN='your_bot_token_here'"
    exit 1
fi

if [[ -z "$ALLOWED_USER_ID" ]]; then
    echo "❌ Ошибка: ALLOWED_USER_ID не установлен!"
    echo "📝 Установите переменную окружения ALLOWED_USER_ID с вашим Telegram ID"
    echo "💡 Пример: export ALLOWED_USER_ID='123456789'"
    exit 1
fi

# Устанавливаем остальные переменные по умолчанию
export LOG_LEVEL=${LOG_LEVEL:-"INFO"}
export REDIS_URL=${REDIS_URL:-"redis://localhost:6379"}
export YANDEX_DISK_TOKEN=${YANDEX_DISK_TOKEN:-""}
export GEMINI_API_KEY=${GEMINI_API_KEY:-""}

echo "✅ Все проверки пройдены. Запуск бота..."
python3 -m app.main 