#!/bin/bash

# Улучшенный скрипт деплоя с rollback и health checks

set -e

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Конфигурация
BACKUP_DIR="backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
MAX_RETRIES=3
HEALTH_CHECK_TIMEOUT=120
COMPOSE_FILE="docker-compose.production.yml"

# Функции логирования
log_info() {
    echo -e "${GREEN}ℹ️  $1${NC}"
}

log_warn() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Проверка зависимостей
check_dependencies() {
    log_info "Проверка зависимостей..."
    
    if ! command -v docker &> /dev/null; then
        log_error "Docker не установлен"
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose не установлен"
        exit 1
    fi
    
    if [ ! -f "$COMPOSE_FILE" ]; then
        log_error "Файл $COMPOSE_FILE не найден"
        exit 1
    fi
    
    if [ ! -f ".env" ]; then
        log_error "Файл .env не найден"
        exit 1
    fi
}

# Создание резервной копии
create_backup() {
    log_info "Создание резервной копии..."
    
    mkdir -p "$BACKUP_DIR"
    
    # Backup конфигурации контейнеров
    docker-compose -f "$COMPOSE_FILE" ps > "$BACKUP_DIR/containers_$TIMESTAMP.txt" 2>/dev/null || true
    docker images > "$BACKUP_DIR/images_$TIMESTAMP.txt"
    
    # Backup Redis данных
    if docker-compose -f "$COMPOSE_FILE" ps | grep -q "redis.*Up"; then
        log_info "Создание резервной копии Redis данных..."
        docker-compose -f "$COMPOSE_FILE" exec -T redis redis-cli --rdb "/data/backup_$TIMESTAMP.rdb" || log_warn "Не удалось создать backup Redis"
    fi
    
    # Backup логов
    if [ -d "logs" ]; then
        tar -czf "$BACKUP_DIR/logs_$TIMESTAMP.tar.gz" logs/ 2>/dev/null || log_warn "Не удалось создать backup логов"
    fi
    
    log_info "Резервная копия создана в $BACKUP_DIR"
}

# Проверка health check
check_health() {
    local service=$1
    local max_attempts=$2
    local attempt=1
    
    log_info "Проверка здоровья сервиса $service..."
    
    while [ $attempt -le $max_attempts ]; do
        if docker-compose -f "$COMPOSE_FILE" exec -T "$service" python -c "import app.main; print('OK')" &>/dev/null; then
            log_info "Сервис $service здоров"
            return 0
        fi
        
        log_warn "Попытка $attempt/$max_attempts: сервис $service не отвечает"
        sleep 10
        ((attempt++))
    done
    
    log_error "Сервис $service не прошел health check"
    return 1
}

# Откат к предыдущей версии
rollback() {
    log_error "Выполняется откат к предыдущей версии..."
    
    # Останавливаем новые контейнеры
    docker-compose -f "$COMPOSE_FILE" down || true
    
    # Восстанавливаем из backup (если есть)
    if [ -f "$BACKUP_DIR/docker-compose.yml.backup" ]; then
        cp "$BACKUP_DIR/docker-compose.yml.backup" docker-compose.yml
        log_info "Восстановлен предыдущий docker-compose.yml"
    fi
    
    # Запускаем предыдущую версию
    docker-compose -f "$COMPOSE_FILE" up -d || log_error "Не удалось запустить предыдущую версию"
    
    log_error "Откат завершен. Проверьте логи для диагностики проблемы."
    exit 1
}

# Ожидание готовности сервисов
wait_for_services() {
    log_info "Ожидание готовности сервисов..."
    
    local start_time=$(date +%s)
    local timeout=$HEALTH_CHECK_TIMEOUT
    
    while true; do
        local current_time=$(date +%s)
        local elapsed=$((current_time - start_time))
        
        if [ $elapsed -gt $timeout ]; then
            log_error "Таймаут ожидания готовности сервисов ($timeout сек)"
            return 1
        fi
        
        # Проверяем Redis
        if docker-compose -f "$COMPOSE_FILE" exec -T redis redis-cli ping &>/dev/null; then
            log_info "Redis готов"
            break
        fi
        
        log_info "Ожидание Redis... ($elapsed/$timeout сек)"
        sleep 5
    done
    
    # Ждем еще немного для инициализации бота
    log_info "Ожидание инициализации бота..."
    sleep 15
}

# Основная функция деплоя
deploy() {
    log_info "🚀 Начинаем деплой Telegram бота..."
    
    # Проверка зависимостей
    check_dependencies
    
    # Создание backup
    create_backup
    
    # Backup текущего docker-compose файла
    if [ -f "docker-compose.yml" ]; then
        cp docker-compose.yml "$BACKUP_DIR/docker-compose.yml.backup"
    fi
    
    # Получение последних изменений (если в git)
    if [ -d ".git" ]; then
        log_info "Обновление кода из Git..."
        git pull origin main || log_warn "Не удалось обновить код из Git"
    fi
    
    # Проверка конфигурации
    log_info "Проверка конфигурации Docker Compose..."
    docker-compose -f "$COMPOSE_FILE" config -q || {
        log_error "Ошибка в конфигурации Docker Compose"
        exit 1
    }
    
    # Создание необходимых директорий
    mkdir -p logs temp
    chmod 755 logs temp
    
    # Остановка старых контейнеров
    log_info "Остановка существующих контейнеров..."
    docker-compose -f "$COMPOSE_FILE" down || true
    
    # Очистка старых образов
    log_info "Очистка старых образов..."
    docker system prune -f || log_warn "Не удалось очистить старые образы"
    
    # Сборка новых образов
    log_info "Сборка Docker образов..."
    if ! docker-compose -f "$COMPOSE_FILE" build --no-cache; then
        log_error "Ошибка при сборке образов"
        rollback
    fi
    
    # Запуск сервисов
    log_info "Запуск сервисов..."
    if ! docker-compose -f "$COMPOSE_FILE" up -d; then
        log_error "Ошибка при запуске сервисов"
        rollback
    fi
    
    # Ожидание готовности
    if ! wait_for_services; then
        log_error "Сервисы не готовы"
        rollback
    fi
    
    # Health checks
    if ! check_health "bot" $MAX_RETRIES; then
        log_error "Бот не прошел health check"
        rollback
    fi
    
    # Проверка статуса сервисов
    log_info "Проверка статуса сервисов..."
    docker-compose -f "$COMPOSE_FILE" ps
    
    # Финальные проверки
    log_info "Выполнение финальных проверок..."
    
    # Проверка логов на ошибки
    if docker-compose -f "$COMPOSE_FILE" logs --tail=50 bot | grep -i "error\|exception\|traceback" &>/dev/null; then
        log_warn "Обнаружены ошибки в логах бота"
        docker-compose -f "$COMPOSE_FILE" logs --tail=20 bot
    fi
    
    log_info "✅ Деплой успешно завершен!"
    log_info "📊 Статус сервисов:"
    docker-compose -f "$COMPOSE_FILE" ps
    
    log_info "📋 Для просмотра логов используйте:"
    log_info "   docker-compose -f $COMPOSE_FILE logs -f bot"
    
    # Очистка старых backup'ов (оставляем последние 5)
    if [ -d "$BACKUP_DIR" ]; then
        ls -t "$BACKUP_DIR" | tail -n +6 | xargs -r rm -rf
        log_info "Очищены старые backup'ы"
    fi
}

# Функция для отображения справки
show_help() {
    echo "Использование: $0 [ОПЦИИ]"
    echo ""
    echo "Опции:"
    echo "  -h, --help           Показать эту справку"
    echo "  -f, --file FILE      Использовать указанный compose файл (по умолчанию: $COMPOSE_FILE)"
    echo "  -t, --timeout SEC    Таймаут health check в секундах (по умолчанию: $HEALTH_CHECK_TIMEOUT)"
    echo "  --no-backup          Пропустить создание резервной копии"
    echo "  --rollback TIMESTAMP Откатиться к указанной резервной копии"
    echo ""
    echo "Примеры:"
    echo "  $0                   Обычный деплой"
    echo "  $0 -f docker-compose.yml  Деплой с другим compose файлом"
    echo "  $0 --rollback 20231201_143000  Откат к резервной копии"
}

# Функция отката к конкретной резервной копии
rollback_to_backup() {
    local backup_timestamp=$1
    
    if [ ! -d "$BACKUP_DIR" ]; then
        log_error "Директория backup'ов не найдена"
        exit 1
    fi
    
    if [ ! -f "$BACKUP_DIR/docker-compose.yml.backup" ]; then
        log_error "Файл резервной копии не найден"
        exit 1
    fi
    
    log_info "Откат к резервной копии $backup_timestamp..."
    
    # Останавливаем текущие контейнеры
    docker-compose -f "$COMPOSE_FILE" down || true
    
    # Восстанавливаем конфигурацию
    cp "$BACKUP_DIR/docker-compose.yml.backup" docker-compose.yml
    
    # Восстанавливаем Redis данные
    if [ -f "$BACKUP_DIR/backup_$backup_timestamp.rdb" ]; then
        log_info "Восстановление данных Redis..."
        # Здесь должна быть логика восстановления Redis
    fi
    
    # Запускаем
    docker-compose -f "$COMPOSE_FILE" up -d
    
    log_info "Откат завершен"
}

# Обработка аргументов командной строки
NO_BACKUP=false
ROLLBACK_TIMESTAMP=""

while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_help
            exit 0
            ;;
        -f|--file)
            COMPOSE_FILE="$2"
            shift 2
            ;;
        -t|--timeout)
            HEALTH_CHECK_TIMEOUT="$2"
            shift 2
            ;;
        --no-backup)
            NO_BACKUP=true
            shift
            ;;
        --rollback)
            ROLLBACK_TIMESTAMP="$2"
            shift 2
            ;;
        *)
            log_error "Неизвестная опция: $1"
            show_help
            exit 1
            ;;
    esac
done

# Обработка сигналов для graceful shutdown
trap 'log_error "Деплой прерван пользователем"; exit 1' INT TERM

# Основная логика
if [ -n "$ROLLBACK_TIMESTAMP" ]; then
    rollback_to_backup "$ROLLBACK_TIMESTAMP"
else
    deploy
fi
