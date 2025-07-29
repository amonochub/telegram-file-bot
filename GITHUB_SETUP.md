# 🚀 Настройка GitHub репозитория

## 📋 Пошаговая инструкция

### 1. Создание репозитория на GitHub

1. **Перейдите на GitHub.com**
2. **Нажмите "+" → "New repository"**
3. **Заполните форму:**
   - **Repository name:** `telegram-file-bot`
   - **Description:** `Интеллектуальный Telegram бот для управления документами с интеграцией Yandex.Disk, OCR и расчётом валютных курсов`
   - **Visibility:** `Public` или `Private`
   - **НЕ ставьте галочки:**
     - ❌ "Add a README file"
     - ❌ "Add .gitignore"
     - ❌ "Choose a license"

4. **Нажмите "Create repository"**

### 2. Подключение локального репозитория

```bash
# Добавление remote origin
git remote add origin https://github.com/YOUR_USERNAME/telegram-file-bot.git

# Проверка remote
git remote -v

# Пуш в GitHub
git branch -M main
git push -u origin main
```

### 3. Настройка GitHub Pages (опционально)

```bash
# Создание ветки для документации
git checkout -b gh-pages

# Добавление документации
mkdir docs
cp README.md docs/index.md
cp DEPLOYMENT.md docs/deployment.md

# Коммит и пуш
git add .
git commit -m "📚 Добавлена документация для GitHub Pages"
git push origin gh-pages
```

### 4. Настройка GitHub Actions (опционально)

Файл `.github/workflows/ci.yml` уже создан и настроен для:
- ✅ Автоматического тестирования
- ✅ Проверки типов с mypy
- ✅ Линтинга с flake8
- ✅ Сборки Docker образа

### 5. Настройка секретов (для продакшена)

В настройках репозитория (`Settings` → `Secrets and variables` → `Actions`):

```bash
# Добавьте секреты:
BOT_TOKEN=ваш_токен_бота
YANDEX_DISK_TOKEN=ваш_токен_яндекс_диска
REDIS_URL=redis://localhost:6379
```

### 6. Настройка веток

```bash
# Создание ветки разработки
git checkout -b develop

# Пуш ветки разработки
git push -u origin develop

# Возврат на main
git checkout main
```

### 7. Настройка защиты веток

В настройках репозитория (`Settings` → `Branches`):

1. **Добавьте правило для `main`:**
   - ✅ "Require a pull request before merging"
   - ✅ "Require status checks to pass before merging"
   - ✅ "Require branches to be up to date before merging"

2. **Добавьте правило для `develop`:**
   - ✅ "Require a pull request before merging"

### 8. Настройка Issues и Projects

1. **Создайте шаблоны Issues:**
   - `Bug report`
   - `Feature request`
   - `Documentation`

2. **Создайте Project для управления задачами**

### 9. Настройка Wiki (опционально)

```bash
# Клонирование wiki
git clone https://github.com/YOUR_USERNAME/telegram-file-bot.wiki.git

# Добавление документации
cp README.md Home.md
cp DEPLOYMENT.md Deployment-Guide.md

# Коммит и пуш
git add .
git commit -m "📚 Добавлена документация в Wiki"
git push origin main
```

## 🔧 Полезные команды

### Проверка статуса
```bash
git status
git remote -v
git branch -a
```

### Обновление репозитория
```bash
git pull origin main
git push origin main
```

### Создание релиза
```bash
# Создание тега
git tag -a v1.0.0 -m "🎉 Первый релиз"

# Пуш тега
git push origin v1.0.0
```

### Настройка автоматического деплоя
```bash
# Добавление GitHub Actions для деплоя
# Создайте файл .github/workflows/deploy.yml
```

## 📊 Статистика проекта

После пушей вы увидите:
- 📈 **Contributions graph**
- 📊 **Repository insights**
- 🏷️ **Releases**
- 📋 **Issues и Pull Requests**

## 🎯 Следующие шаги

1. **Настройте CI/CD для автоматического деплоя**
2. **Добавьте мониторинг и алерты**
3. **Настройте автоматические обновления зависимостей**
4. **Добавьте интеграцию с внешними сервисами**

---

**✅ Репозиторий готов к использованию!** 