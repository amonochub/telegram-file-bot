# 🔧 Обновление на сервере

## ✅ Проблема решена

**Ошибка:** `ALLOWED_USER_ID` не мог обработать пустые значения

**Решение:** 
- Изменен тип поля с `int` на `str`
- Добавлена обработка пустых значений
- Обновлен `env.example`

## 🚀 Команды для обновления на сервере

### 1. Обновление кода

```bash
# Переход в директорию проекта
cd ~/telegram-file-bot

# Остановка контейнеров
docker-compose down

# Обновление кода
git pull origin main

# Проверка изменений
git log --oneline -3
```

### 2. Обновление .env файла

```bash
# Проверка текущего .env
cat .env

# Если ALLOWED_USER_ID пустой, оставьте его пустым
# Если есть значение, убедитесь что это число
# Пример правильного .env:
```

**Пример правильного .env:**
```bash
# Telegram Bot
BOT_TOKEN=ваш_токен_бота

# Yandex.Disk
YANDEX_DISK_TOKEN=ваш_токен_яндекс_диска

# Redis
REDIS_URL=redis://localhost:6379

# Логирование
LOG_LEVEL=INFO

# Опционально: ограничение доступа (оставьте пустым для публичного доступа)
ALLOWED_USER_ID=

# Дополнительные настройки
MAX_FILE_SIZE=100000000
UPLOAD_DIR=/bot_files
TEMP_DIR=temp
CACHE_TTL=3600
MAX_BUFFER_SIZE=100
CBR_API_URL=https://www.cbr-xml-daily.ru/daily_json.js
```

### 3. Перезапуск сервисов

```bash
# Пересборка и запуск
docker-compose build --no-cache
docker-compose up -d

# Проверка статуса
docker-compose ps

# Проверка логов
docker-compose logs -f bot
```

### 4. Проверка работы

```bash
# Проверка подключения к Redis
docker-compose exec redis redis-cli ping

# Проверка работы бота
docker-compose exec bot python -c "from app.config import settings; print('✅ Конфигурация загружена:', settings.allowed_user_id_int)"
```

## 🔍 Диагностика проблем

### Если бот все еще не запускается:

```bash
# Подробные логи
docker-compose logs bot

# Проверка переменных окружения
docker-compose exec bot env | grep -E "(BOT_TOKEN|ALLOWED_USER_ID)"

# Проверка конфигурации
docker-compose exec bot python -c "from app.config import settings; print('BOT_TOKEN:', bool(settings.bot_token)); print('ALLOWED_USER_ID:', settings.allowed_user_id)"
```

### Если нужно полностью пересоздать контейнеры:

```bash
# Остановка и удаление контейнеров
docker-compose down

# Удаление образов
docker system prune -f

# Пересборка с нуля
docker-compose build --no-cache
docker-compose up -d
```

## ✅ Ожидаемый результат

После обновления:

1. **Бот должен запуститься без ошибок**
2. **В логах не должно быть ошибок валидации**
3. **Бот должен отвечать на сообщения**
4. **Все функции должны работать**

## 📋 Проверочный список

- [ ] Код обновлен (`git pull origin main`)
- [ ] .env файл настроен правильно
- [ ] Контейнеры пересобраны
- [ ] Бот запущен без ошибок
- [ ] Логи показывают успешный запуск
- [ ] Бот отвечает на сообщения

---

**✅ Обновление завершено! Бот должен работать корректно.** 