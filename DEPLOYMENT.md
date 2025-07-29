# 🚀 Деплой Telegram бота

## 📋 Требования

- Docker и Docker Compose
- Доступ к серверу с Linux
- Telegram Bot Token
- Yandex.Disk Token

## 🔧 Подготовка к деплою

### 1. Создание .env файла

Создайте файл `.env` в корне проекта:

```bash
# Telegram Bot
BOT_TOKEN=your_telegram_bot_token_here

# Yandex.Disk
YANDEX_DISK_TOKEN=your_yandex_disk_token_here

# Redis (опционально)
REDIS_URL=redis://localhost:6379

# Логирование
LOG_LEVEL=INFO
```

### 2. Проверка конфигурации

Убедитесь, что все переменные окружения настроены правильно:

```bash
# Проверка импорта модулей
python -c "import app.main; print('✅ Основной модуль импортируется успешно')"
```

## 🐳 Деплой с Docker

### Автоматический деплой

```bash
# Запуск скрипта деплоя
./deploy.sh
```

### Ручной деплой

```bash
# 1. Остановка существующих контейнеров
docker-compose down

# 2. Сборка образа
docker-compose build --no-cache

# 3. Запуск сервисов
docker-compose up -d

# 4. Проверка статуса
docker-compose ps

# 5. Просмотр логов
docker-compose logs -f bot
```

## 📊 Мониторинг

### Проверка статуса сервисов

```bash
docker-compose ps
```

### Просмотр логов

```bash
# Логи бота
docker-compose logs -f bot

# Логи Redis
docker-compose logs -f redis
```

### Проверка здоровья приложения

```bash
# Проверка подключения к Redis
docker-compose exec redis redis-cli ping

# Проверка работы бота
docker-compose exec bot python -c "import app.main; print('✅ Бот работает')"
```

## 🔄 Обновление

### Обновление кода

```bash
# 1. Остановка сервисов
docker-compose down

# 2. Обновление кода (git pull)

# 3. Пересборка и запуск
docker-compose build --no-cache
docker-compose up -d
```

### Обновление переменных окружения

```bash
# 1. Редактирование .env файла

# 2. Перезапуск сервисов
docker-compose restart bot
```

## 🛠️ Устранение неполадок

### Проблемы с подключением к Telegram

```bash
# Проверка токена бота
docker-compose logs bot | grep "bot"
```

### Проблемы с Yandex.Disk

```bash
# Проверка подключения к Yandex.Disk
docker-compose logs bot | grep "yandex"
```

### Проблемы с Redis

```bash
# Проверка Redis
docker-compose exec redis redis-cli ping
```

## 📁 Структура проекта

```
drive_bot_final/
├── app/                    # Основной код приложения
├── tests/                  # Тесты
├── logs/                   # Логи (создается автоматически)
├── temp/                   # Временные файлы
├── docker-compose.yml      # Конфигурация Docker Compose
├── Dockerfile             # Docker образ
├── requirements.txt        # Python зависимости
├── deploy.sh              # Скрипт деплоя
└── .env                   # Переменные окружения
```

## 🔒 Безопасность

- Не коммитьте `.env` файл в Git
- Используйте сильные токены для Telegram и Yandex.Disk
- Регулярно обновляйте зависимости
- Мониторьте логи на предмет подозрительной активности

## 📞 Поддержка

При возникновении проблем:

1. Проверьте логи: `docker-compose logs -f bot`
2. Убедитесь, что все переменные окружения настроены
3. Проверьте подключение к интернету
4. Убедитесь, что порты не заняты другими сервисами 