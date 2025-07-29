# 🚀 Быстрый деплой на сервер

## 📋 Подготовка (локально)

1. **Проверка кода:**
   ```bash
   # Запуск тестов
   ./scripts/run_tests.sh -f
   
   # Проверка импорта
   python -c "import app.main; print('✅ Основной модуль работает')"
   ```

2. **Коммит и пуш:**
   ```bash
   git add .
   git commit -m "Описание изменений"
   git push origin main
   ```

## 🖥️ Деплой на сервер

### Автоматический деплой (рекомендуется)

```bash
# Подключение к серверу
ssh user@your-server.com

# Переход в директорию проекта
cd ~/telegram-file-bot

# Запуск автоматического деплоя
./deploy.sh
```

### Ручной деплой

```bash
# 1. Остановка контейнеров
docker-compose down

# 2. Обновление кода
git pull origin main

# 3. Пересборка и запуск
docker-compose build --no-cache
docker-compose up -d

# 4. Проверка статуса
docker-compose ps
docker-compose logs -f bot
```

## 🔍 Проверка работы

```bash
# Проверка статуса сервисов
docker-compose ps

# Просмотр логов
docker-compose logs -f bot

# Проверка подключения к Redis
docker-compose exec redis redis-cli ping

# Проверка работы бота
docker-compose exec bot python -c "import app.main; print('✅ Бот работает')"
```

## 🛠️ Устранение проблем

### Если бот не запускается:

```bash
# Подробные логи
docker-compose logs bot

# Полная пересборка
docker-compose down
docker system prune -f
docker-compose build --no-cache
docker-compose up -d
```

### Если нужно откатиться:

```bash
# Откат к предыдущей версии
git reset --hard HEAD~1
git pull origin main
docker-compose build --no-cache
docker-compose up -d
```

## ✅ Чек-лист

- [ ] Код протестирован локально
- [ ] Изменения закоммичены и запушены
- [ ] Подключение к серверу установлено
- [ ] Старые контейнеры остановлены
- [ ] Код обновлен с Git
- [ ] Docker образы пересобраны
- [ ] Сервисы запущены
- [ ] Логи показывают успешный запуск
- [ ] Бот отвечает на сообщения

---

**🎉 Деплой завершен! Бот готов к работе.** 