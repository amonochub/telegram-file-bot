
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

# Установка Python зависимостей от root (это нормально для сборки образа)
RUN pip install --no-cache-dir -r requirements.txt

# Копирование исходного кода
COPY . .

# Создание директорий и установка прав
RUN mkdir -p logs temp && \
    chown -R botuser:botuser /app

# Переключение на непривилегированного пользователя
USER botuser

# Переменные окружения
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Команда запуска
CMD ["python", "-m", "app.main"]
