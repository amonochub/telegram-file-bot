
# 🤖 Telegram File Bot

Интеллектуальный Telegram бот для управления документами с интеграцией Yandex.Disk, OCR и расчётом валютных курсов.

## ✨ Возможности

### 📁 **Управление файлами**
- Загрузка файлов в Yandex.Disk с автоматической организацией
- Просмотр и навигация по папкам Yandex.Disk
- Скачивание файлов прямо в Telegram
- Поддержка PDF, DOCX, изображений

### 🔍 **OCR (Оптическое распознавание текста)**
- Распознавание текста из PDF документов
- Создание поискаемых PDF файлов
- Поддержка русского и английского языков
- Сохранение оригинального форматирования

### 💰 **Расчёт для клиента**
- Расчёт валютных операций с курсами ЦБ РФ
- Поддержка USD, EUR, CNY, AED, TRY
- Автоматическое получение актуальных курсов
- Расчёт комиссии агента

### 🗂️ **Умная организация файлов**
- Автоматический парсинг имён файлов
- Структурированное хранение по типам документов
- Интеллектуальная навигация по папкам

## 🚀 Быстрый старт

### Локальная разработка

```bash
# Клонирование репозитория
git clone <repository-url>
cd drive_bot_final

# Создание виртуального окружения
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# или
.venv\Scripts\activate  # Windows

# Установка зависимостей
pip install -r requirements.txt

# Создание .env файла
cp env.example .env
# Отредактируйте .env с вашими токенами

# Запуск бота
python -m app.main
```

### Деплой на сервер

```bash
# Клонирование и настройка
git clone <repository-url>
cd drive_bot_final

# Создание .env файла
cp env.example .env
# Настройте переменные окружения

# Запуск с Docker
./deploy.sh
```

## ⚙️ Конфигурация

### Переменные окружения (.env)

```bash
# Telegram Bot
BOT_TOKEN=your_telegram_bot_token

# Yandex.Disk
YANDEX_DISK_TOKEN=your_yandex_disk_token

# Redis (для кэширования курсов валют)
REDIS_URL=redis://localhost:6379

# Логирование
LOG_LEVEL=INFO
```

## 📋 Структура проекта

```
drive_bot_final/
├── app/
│   ├── handlers/          # Обработчики сообщений
│   │   ├── menu/         # Меню и навигация
│   │   └── browse.py     # Просмотр файлов
│   ├── services/         # Бизнес-логика
│   │   ├── yandex_disk_service.py
│   │   ├── ocr_service.py
│   │   └── rates_cache.py
│   ├── utils/            # Утилиты
│   └── main.py           # Точка входа
├── tests/                # Тесты
├── docker-compose.yml    # Docker конфигурация
├── Dockerfile           # Docker образ
└── requirements.txt     # Зависимости
```

## 🔧 Технологии

- **Python 3.11+** - основной язык
- **Aiogram 3.x** - Telegram Bot API
- **Yandex.Disk API** - облачное хранилище
- **Redis** - кэширование курсов валют
- **OCRmyPDF** - OCR для PDF
- **PyMuPDF** - работа с PDF
- **python-docx** - работа с DOCX
- **Docker** - контейнеризация

## 📊 Мониторинг

### Логи

```bash
# Просмотр логов в реальном времени
docker-compose logs -f bot

# Логи с фильтрацией
docker-compose logs bot | grep "error"
```

### Статус сервисов

```bash
# Проверка статуса
docker-compose ps

# Проверка здоровья Redis
docker-compose exec redis redis-cli ping
```

## 🧪 Тестирование

```bash
# Запуск всех тестов
python -m pytest tests/ -v

# Запуск конкретного теста
python -m pytest tests/test_rates_cache.py -v

# Проверка покрытия
python -m pytest --cov=app tests/
```

## 🔄 Обновление

### Обновление кода

```bash
# Остановка сервисов
docker-compose down

# Обновление кода
git pull origin main

# Пересборка и запуск
docker-compose build --no-cache
docker-compose up -d
```

### Обновление зависимостей

```bash
# Обновление requirements.txt
pip install --upgrade -r requirements.txt

# Пересборка образа
docker-compose build --no-cache
docker-compose up -d
```

## 🛠️ Устранение неполадок

### Проблемы с подключением

1. **Telegram Bot не отвечает**
   - Проверьте токен в .env
   - Убедитесь, что бот не заблокирован

2. **Ошибки Yandex.Disk**
   - Проверьте токен доступа
   - Убедитесь в наличии места на диске

3. **Проблемы с OCR**
   - Проверьте установку Tesseract
   - Убедитесь в наличии языковых пакетов

### Логи и отладка

```bash
# Подробные логи
LOG_LEVEL=DEBUG python -m app.main

# Логи Docker
docker-compose logs -f bot
```

## 📈 Производительность

- **Кэширование курсов валют** - Redis
- **Асинхронная обработка** - asyncio
- **Оптимизированная загрузка файлов** - потоковая передача
- **Умное управление памятью** - буферизация

## 🔒 Безопасность

- Валидация файлов перед загрузкой
- Проверка расширений файлов
- Ограничение размера файлов
- Безопасное хранение токенов

## 📞 Поддержка

При возникновении проблем:

1. Проверьте логи: `docker-compose logs -f bot`
2. Убедитесь в правильности конфигурации
3. Проверьте подключение к интернету
4. Создайте issue в репозитории

## 📄 Лицензия

MIT License - см. файл LICENSE для подробностей.

---

**Разработано с ❤️ для эффективного управления документами**
