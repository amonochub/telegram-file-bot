#!/bin/bash

# Безопасный скрипт для деплоя Telegram бота на сервер

set -e

echo "🚀 Начинаем безопасный деплой Telegram бота..."

# Проверяем наличие .env файла
if [ ! -f .env ]; then
    echo "❌ Файл .env не найден! Создайте его с необходимыми переменными окружения."
    exit 1
fi

# Проверяем права на директории
echo "🔒 Проверяем права доступа..."
if [ ! -w ./logs ]; then
    echo "📁 Создаем директорию logs..."
    mkdir -p logs
    chmod 755 logs
fi

if [ ! -w ./temp ]; then
    echo "📁 Создаем директорию temp..."
    mkdir -p temp
    chmod 755 temp
fi

# Останавливаем существующие контейнеры
echo "📦 Останавливаем существующие контейнеры..."
docker-compose down || true

# Удаляем старые образы
echo "🧹 Очищаем старые образы..."
docker system prune -f

# Собираем новый образ
echo "🔨 Собираем Docker образ..."
docker-compose build --no-cache

# Запускаем сервисы
echo "🚀 Запускаем сервисы..."
docker-compose up -d

# Проверяем статус
echo "📊 Проверяем статус сервисов..."
docker-compose ps

# Проверяем права доступа в контейнере
echo "🔍 Проверяем права доступа в контейнере..."
docker-compose exec bot whoami || echo "⚠️ Не удалось проверить пользователя в контейнере"

# Показываем логи
echo "📋 Логи бота:"
docker-compose logs -f bot 