#!/bin/bash

# Скрипт для обновления на сервере
# Запускать на сервере в директории ../root/telegram-file-bot

set -e

echo "🔄 Обновляем код на сервере..."

# Проверяем, что мы в правильной директории
if [ ! -f "app/main.py" ]; then
    echo "❌ Ошибка: Не найдена директория app/main.py"
    exit 1
fi

# Сохраняем текущую ветку
CURRENT_BRANCH=$(git branch --show-current)

# Получаем последние изменения
echo "📥 Получаем изменения с GitHub..."
git fetch origin

# Проверяем, есть ли изменения
LOCAL_COMMIT=$(git rev-parse HEAD)
REMOTE_COMMIT=$(git rev-parse origin/main)

if [ "$LOCAL_COMMIT" = "$REMOTE_COMMIT" ]; then
    echo "✅ Код уже актуален"
else
    echo "🔄 Обновляем код..."
    git pull origin main
    
    # Проверяем, что обновление прошло успешно
    if [ $? -eq 0 ]; then
        echo "✅ Код успешно обновлен"
        
        # Перезапускаем бота
        echo "🔄 Перезапускаем бота..."
        sudo systemctl restart telegram-bot
        
        # Проверяем статус
        if sudo systemctl is-active --quiet telegram-bot; then
            echo "✅ Бот успешно перезапущен"
        else
            echo "❌ Ошибка при перезапуске бота"
            echo "Проверьте логи: sudo journalctl -u telegram-bot -n 50"
            exit 1
        fi
    else
        echo "❌ Ошибка при обновлении кода"
        exit 1
    fi
fi

echo "✅ Обновление завершено успешно"
