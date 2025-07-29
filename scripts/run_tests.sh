#!/bin/bash

# Скрипт для запуска тестов с разными опциями

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Функция для вывода сообщений
print_message() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Проверяем, что мы в правильной директории
if [ ! -f "pytest.ini" ] && [ ! -f "pyproject.toml" ]; then
    print_error "Скрипт должен быть запущен из корневой директории проекта"
    exit 1
fi

# Проверяем, что виртуальное окружение активировано
if [ -z "$VIRTUAL_ENV" ]; then
    print_warning "Виртуальное окружение не активировано. Попытка активации..."
    
    # Пробуем найти виртуальное окружение
    VENV_FOUND=false
    for venv_dir in .venv venv env virtualenv env3; do
        if [ -d "$venv_dir" ] && [ -f "$venv_dir/bin/activate" ]; then
            print_message "Найдено виртуальное окружение: $venv_dir"
            source "$venv_dir/bin/activate"
            VENV_FOUND=true
            break
        fi
    done
    
    if [ "$VENV_FOUND" = false ]; then
        print_error "Виртуальное окружение не найдено. Ожидаемые директории: .venv, venv, env, virtualenv, env3"
    exit 1
fi
fi

# Устанавливаем PYTHONPATH для корректного импорта модулей
export PYTHONPATH="$(pwd)"

# Функция для показа справки
show_help() {
    echo "Использование: $0 [опции]"
    echo ""
    echo "Опции:"
    echo "  -h, --help              Показать эту справку"
    echo "  -u, --unit              Запустить только unit тесты"
    echo "  -i, --integration       Запустить только integration тесты"
    echo "  -f, --fast              Быстрый запуск (без coverage)"
    echo "  -c, --coverage          Запустить с coverage отчетом"
    echo "  -v, --verbose           Подробный вывод"
    echo "  -k, --keep-going        Продолжать при ошибках"
    echo "  --html                  Генерировать HTML отчет coverage"
    echo "  --xml                   Генерировать XML отчет coverage"
    echo "  --pattern PATTERN       Запустить тесты по паттерну (например: test_menu*)"
    echo "  --file FILE             Запустить конкретный файл тестов"
    echo ""
    echo "Примеры:"
    echo "  $0                      Запустить все тесты с coverage"
    echo "  $0 -u                   Запустить только unit тесты"
    echo "  $0 -f                   Быстрый запуск без coverage"
    echo "  $0 -c --html            Запустить с HTML отчетом"
    echo "  $0 --pattern test_menu  Запустить тесты с именем test_menu*"
    echo "  $0 --file tests/test_menu_advanced.py"
}

# Параметры по умолчанию
UNIT_ONLY=false
INTEGRATION_ONLY=false
FAST_MODE=false
COVERAGE_MODE=true
VERBOSE_MODE=false
KEEP_GOING=false
HTML_REPORT=false
XML_REPORT=false
TEST_PATTERN=""
TEST_FILE=""

# Парсим аргументы
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_help
            exit 0
            ;;
        -u|--unit)
            UNIT_ONLY=true
            shift
            ;;
        -i|--integration)
            INTEGRATION_ONLY=true
            shift
            ;;
        -f|--fast)
            FAST_MODE=true
            COVERAGE_MODE=false
            shift
            ;;
        -c|--coverage)
            COVERAGE_MODE=true
            shift
            ;;
        -v|--verbose)
            VERBOSE_MODE=true
            shift
            ;;
        -k|--keep-going)
            KEEP_GOING=true
            shift
            ;;
        --html)
            HTML_REPORT=true
            shift
            ;;
        --xml)
            XML_REPORT=true
            shift
            ;;
        --pattern)
            TEST_PATTERN="$2"
            shift 2
            ;;
        --file)
            TEST_FILE="$2"
            shift 2
            ;;
        *)
            print_error "Неизвестная опция: $1"
            show_help
            exit 1
            ;;
    esac
done

# Проверяем конфликты опций
if $UNIT_ONLY && $INTEGRATION_ONLY; then
    print_error "Нельзя использовать --unit и --integration одновременно"
    exit 1
fi

# Формируем массив аргументов pytest
PYTEST_ARGS=()

# Добавляем опции
[[ $VERBOSE_MODE == true ]] && PYTEST_ARGS+=(-v)

if [[ $KEEP_GOING == true ]]; then
    PYTEST_ARGS+=(--tb=short)
else
    PYTEST_ARGS+=(--tb=short -x)
fi

# Добавляем coverage опции
if [[ $COVERAGE_MODE == true ]]; then
    PYTEST_ARGS+=(--cov=app --cov-report=term-missing)
    
    [[ $HTML_REPORT == true ]] && PYTEST_ARGS+=(--cov-report=html:htmlcov)
    [[ $XML_REPORT == true ]] && PYTEST_ARGS+=(--cov-report=xml)
    
    PYTEST_ARGS+=(--cov-fail-under=80)
fi

# Добавляем фильтры по типам тестов
[[ $UNIT_ONLY == true ]] && PYTEST_ARGS+=(-m unit)
[[ $INTEGRATION_ONLY == true ]] && PYTEST_ARGS+=(-m integration)

# Определяем путь к тестам
if [[ -n "$TEST_FILE" ]]; then
    TEST_PATH="$TEST_FILE"
elif [[ -n "$TEST_PATTERN" ]]; then
    # Используем расширение wildcard для bash
    TEST_PATH="tests/${TEST_PATTERN}"
    # Проверяем, что файлы существуют
    if ! ls $TEST_PATH >/dev/null 2>&1; then
        print_error "Файлы по паттерну '$TEST_PATH' не найдены"
        exit 1
    fi
elif [[ $FAST_MODE == true ]]; then
    TEST_PATH="tests/test_menu_advanced.py"
else
    TEST_PATH="tests/"
fi

# Добавляем путь к тестам (используем eval для расширения wildcard)
if [[ -n "$TEST_PATTERN" ]]; then
    # Для паттернов используем eval для расширения wildcard
    eval "PYTEST_ARGS+=($TEST_PATH)"
else
    PYTEST_ARGS+=("$TEST_PATH")
fi

# Выводим информацию о запуске
print_message "Запуск тестов..."
print_message "Команда: pytest ${PYTEST_ARGS[*]}"

# Запускаем тесты
start_time=$(date +%s)

# Временно отключаем set -e для корректной обработки ошибок
set +e
pytest "${PYTEST_ARGS[@]}"
TEST_EXIT_CODE=$?
set -e

end_time=$(date +%s)
duration=$((end_time - start_time))

if [[ $TEST_EXIT_CODE -eq 0 ]]; then
    print_success "Тесты прошли успешно за ${duration} секунд"
    
    if [[ $COVERAGE_MODE == true ]] && [[ $HTML_REPORT == true ]]; then
        print_message "HTML отчет coverage доступен в htmlcov/index.html"
    fi
    
    exit 0
else
    print_error "Тесты завершились с ошибками за ${duration} секунд"
    exit 1
fi 