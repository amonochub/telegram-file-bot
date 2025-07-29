
# Используем официальный образ Python 3.11
FROM python:3.11-slim

# Установка системных зависимостей
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-rus \
    tesseract-ocr-eng \
    poppler-utils \
    ghostscript \
    && rm -rf /var/lib/apt/lists/*

# Создание непривилегированного пользователя
RUN groupadd -r botuser && useradd -r -g botuser botuser

# Установка рабочей директории
WORKDIR /app

# Копирование файлов зависимостей
COPY requirements.txt .

# Переключение на непривилегированного пользователя перед установкой pip
USER botuser

# Установка Python зависимостей от имени botuser
RUN pip install --no-cache-dir -r requirements.txt

# Копирование исходного кода
COPY --chown=botuser:botuser . .

# Создание директорий
RUN mkdir -p logs temp

# Переменные окружения
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Команда запуска
CMD ["python", "-m", "app.main"]
