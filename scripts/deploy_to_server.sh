#!/bin/bash

# Скрипт для развертывания кода на сервер
# Путь: ../root/telegram-file-bot

set -e  # Остановка при ошибке

echo "🚀 Начинаем развертывание на сервер..."

# Проверяем, что мы в правильной директории
if [ ! -f "app/main.py" ]; then
    echo "❌ Ошибка: Не найдена директория app/main.py"
    echo "Убедитесь, что вы находитесь в корневой директории проекта"
    exit 1
fi

# Проверяем статус Git
echo "📋 Проверяем статус Git..."
git_status=$(git status --porcelain)
if [ -n "$git_status" ]; then
    echo "⚠️  Внимание: Есть незакоммиченные изменения:"
    echo "$git_status"
    read -p "Продолжить развертывание? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "❌ Развертывание отменено"
        exit 1
    fi
fi

# Отправляем изменения в GitHub
echo "📤 Отправляем изменения в GitHub..."
git push origin main

# Проверяем, что изменения отправлены
if [ $? -ne 0 ]; then
    echo "❌ Ошибка при отправке в GitHub"
    exit 1
fi

echo "✅ Код успешно отправлен в GitHub"
echo ""
echo "📋 Следующие шаги для обновления на сервере:"
echo ""
echo "1. Подключитесь к серверу:"
echo "   ssh user@your-server.com"
echo ""
echo "2. Перейдите в директорию проекта:"
echo "   cd ../root/telegram-file-bot"
echo ""
echo "3. Обновите код с GitHub:"
echo "   git pull origin main"
echo ""
echo "4. Перезапустите бота:"
echo "   sudo systemctl restart telegram-bot"
echo ""
echo "5. Проверьте статус:"
echo "   sudo systemctl status telegram-bot"
echo ""
echo "6. Проверьте логи:"
echo "   sudo journalctl -u telegram-bot -f"
echo ""

# Создаем скрипт для автоматического обновления на сервере
cat > scripts/update_server.sh << 'EOF'
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
EOF

chmod +x scripts/update_server.sh

echo "📝 Создан скрипт scripts/update_server.sh для автоматического обновления на сервере"
echo ""
echo "💡 Для автоматического обновления на сервере выполните:"
echo "   scp scripts/update_server.sh user@your-server.com:~/"
echo "   ssh user@your-server.com"
echo "   cd ../root/telegram-file-bot"
echo "   ~/update_server.sh" 