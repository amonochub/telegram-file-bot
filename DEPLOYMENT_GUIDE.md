# 🚀 Руководство по развертыванию

## Обзор

Этот документ описывает процесс обновления кода на сервере для Telegram бота.

### Информация о проекте
- **Репозиторий**: `amonochub/telegram-file-bot`
- **Путь на сервере**: `../root/telegram-file-bot`
- **Сервис**: `telegram-bot`

## 📋 Порядок действий для обновления

### 1. Подготовка локально

```bash
# Проверить статус Git
git status

# Убедиться, что все изменения закоммичены
git add .
git commit -m "feat: описание изменений"

# Отправить изменения в GitHub
git push origin main
```

### 2. Автоматическое развертывание

Используйте созданный скрипт:

```bash
# Запустить скрипт развертывания
./scripts/deploy_to_server.sh
```

### 3. Ручное обновление на сервере

#### Подключение к серверу
```bash
ssh user@your-server.com
```

#### Переход в директорию проекта
```bash
cd ../root/telegram-file-bot
```

#### Обновление кода
```bash
# Получить последние изменения
git fetch origin

# Проверить, есть ли изменения
git log --oneline HEAD..origin/main

# Обновить код
git pull origin main
```

#### Перезапуск бота
```bash
# Перезапустить сервис
sudo systemctl restart telegram-bot

# Проверить статус
sudo systemctl status telegram-bot

# Проверить логи
sudo journalctl -u telegram-bot -f
```

## 🔧 Автоматическое обновление на сервере

### Копирование скрипта обновления
```bash
# Скопировать скрипт на сервер
scp scripts/update_server.sh user@your-server.com:~/

# Подключиться к серверу
ssh user@your-server.com

# Перейти в директорию проекта
cd ../root/telegram-file-bot

# Запустить автоматическое обновление
~/update_server.sh
```

## 📊 Мониторинг

### Проверка статуса сервиса
```bash
sudo systemctl status telegram-bot
```

### Просмотр логов
```bash
# Последние логи
sudo journalctl -u telegram-bot -n 50

# Следить за логами в реальном времени
sudo journalctl -u telegram-bot -f
```

### Проверка процесса
```bash
# Найти процесс бота
ps aux | grep python

# Проверить использование ресурсов
top -p $(pgrep -f "python.*main.py")
```

## 🚨 Устранение неполадок

### Проблемы с Git
```bash
# Сбросить локальные изменения (осторожно!)
git reset --hard origin/main

# Очистить неотслеживаемые файлы
git clean -fd
```

### Проблемы с сервисом
```bash
# Остановить сервис
sudo systemctl stop telegram-bot

# Проверить конфигурацию
sudo systemctl cat telegram-bot

# Перезапустить с отладкой
sudo systemctl restart telegram-bot
sudo journalctl -u telegram-bot -f
```

### Проблемы с зависимостями
```bash
# Активировать виртуальное окружение
source venv/bin/activate

# Обновить зависимости
pip install -r requirements.txt

# Проверить установленные пакеты
pip list
```

## 📝 Чек-лист развертывания

- [ ] Код закоммичен и отправлен в GitHub
- [ ] Подключение к серверу установлено
- [ ] Код обновлен на сервере (`git pull origin main`)
- [ ] Зависимости обновлены (если нужно)
- [ ] Сервис перезапущен (`sudo systemctl restart telegram-bot`)
- [ ] Статус сервиса проверен (`sudo systemctl status telegram-bot`)
- [ ] Логи проверены на наличие ошибок
- [ ] Функциональность бота протестирована

## 🔒 Безопасность

### Проверка конфигурации
```bash
# Проверить права доступа к файлам
ls -la app/config.py

# Проверить переменные окружения
cat .env | grep -v "^#" | grep -v "^$"
```

### Резервное копирование
```bash
# Создать резервную копию перед обновлением
cp -r ../root/telegram-file-bot ../root/telegram-file-bot.backup.$(date +%Y%m%d_%H%M%S)
```

## 📞 Контакты для поддержки

При возникновении проблем:
1. Проверьте логи сервиса
2. Убедитесь в корректности конфигурации
3. Проверьте подключение к внешним сервисам
4. Обратитесь к документации проекта

---

**Последнее обновление**: $(date)
**Версия**: 1.0 