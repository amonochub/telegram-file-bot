#!/bin/bash

# Скрипт для деплоя Telegram бота на сервер

set -e

echo "🚀 Начинаем деплой Telegram бота..."

# Проверяем наличие .env файла
if [ ! -f .env ]; then
    echo "❌ Файл .env не найден! Создайте его с необходимыми переменными окружения."
    exit 1
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

# Показываем логи
echo "📋 Логи бота:"
docker-compose logs -f bot 