# Настройка и запуск Telegram File Bot

## 🚀 Быстрый запуск

### 1. Получите токен бота
1. Откройте Telegram и найдите @BotFather
2. Отправьте команду `/newbot`
3. Следуйте инструкциям для создания бота
4. Скопируйте полученный токен

### 2. Узнайте ваш Telegram ID
1. Отправьте сообщение боту @userinfobot
2. Скопируйте ваш User ID

### 3. Установите переменные окружения
```bash
export BOT_TOKEN="ваш_токен_бота_здесь"
export ALLOWED_USER_ID="ваш_telegram_id_здесь"
```

### 4. Запустите бота
```bash
./start_bot.sh
```

## 🔧 Дополнительная настройка

### Яндекс.Диск (опционально)
Для работы с Яндекс.Диском:
1. Получите OAuth токен на https://yandex.ru/dev/disk/
2. Установите переменную:
```bash
export YANDEX_DISK_TOKEN="ваш_oauth_токен_здесь"
```

### AI функции (опционально)
Для работы с AI (Gemini):
1. Получите API ключ на https://makersuite.google.com/app/apikey
2. Установите переменную:
```bash
export GEMINI_API_KEY="ваш_api_ключ_здесь"
```

## 📋 Все переменные окружения

```bash
# Обязательные
export BOT_TOKEN="токен_бота"
export ALLOWED_USER_ID="ваш_telegram_id"

# Опциональные
export YANDEX_DISK_TOKEN="oauth_токен_яндекс_диска"
export GEMINI_API_KEY="api_ключ_gemini"
export LOG_LEVEL="INFO"
export REDIS_URL="redis://localhost:6379"
```

## 🐛 Устранение проблем

### Redis не запущен
```bash
brew services start redis
```

### Зависимости не установлены
```bash
source .venv/bin/activate
pip install -r requirements.txt
```

### Системные зависимости (macOS)
```bash
brew install redis tesseract poppler libmagic
```

## 📝 Проверка работы

После запуска бота:
1. Найдите вашего бота в Telegram
2. Отправьте команду `/start`
3. Проверьте, что бот отвечает

## 🛑 Остановка бота

Нажмите `Ctrl+C` в терминале для остановки бота. 