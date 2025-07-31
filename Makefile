# Makefile для запуска тестов проекта

.PHONY: help test test-all test-manual test-unit test-integration test-performance test-security test-lint test-types clean install

# Цвета для вывода
GREEN = \033[0;32m
RED = \033[0;31m
YELLOW = \033[1;33m
BLUE = \033[0;34m
NC = \033[0m # No Color

help: ## Показать справку по командам
	@echo "$(BLUE)Доступные команды:$(NC)"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(GREEN)%-20s$(NC) %s\n", $$1, $$2}'

install: ## Установить зависимости
	@echo "$(BLUE)Установка зависимостей...$(NC)"
	pip install -r requirements.txt
	pip install -r requirements.dev.txt

test: ## Запустить все автоматические тесты
	@echo "$(BLUE)Запуск всех автоматических тестов...$(NC)"
	python scripts/run_all_tests.py --tests unit integration performance security linting type_checking

test-all: ## Запустить все тесты (включая ручные)
	@echo "$(BLUE)Запуск всех тестов...$(NC)"
	python scripts/run_all_tests.py --all

test-manual: ## Запустить только ручные тесты
	@echo "$(BLUE)Запуск ручных тестов...$(NC)"
	python scripts/run_all_tests.py --tests manual

test-unit: ## Запустить только модульные тесты
	@echo "$(BLUE)Запуск модульных тестов...$(NC)"
	python scripts/run_all_tests.py --tests unit

test-integration: ## Запустить только интеграционные тесты
	@echo "$(BLUE)Запуск интеграционных тестов...$(NC)"
	python scripts/run_all_tests.py --tests integration

test-performance: ## Запустить только тесты производительности
	@echo "$(BLUE)Запуск тестов производительности...$(NC)"
	python scripts/run_all_tests.py --tests performance

test-security: ## Запустить только тесты безопасности
	@echo "$(BLUE)Запуск тестов безопасности...$(NC)"
	python scripts/run_all_tests.py --tests security

test-lint: ## Запустить только линтер
	@echo "$(BLUE)Запуск линтера...$(NC)"
	python scripts/run_all_tests.py --tests linting

test-types: ## Запустить только проверку типов
	@echo "$(BLUE)Запуск проверки типов...$(NC)"
	python scripts/run_all_tests.py --tests type_checking

test-quick: ## Быстрые тесты (без медленных)
	@echo "$(BLUE)Запуск быстрых тестов...$(NC)"
	PYTHONPATH=. pytest tests/ -v -m "not slow" --tb=short

test-coverage: ## Запустить тесты с покрытием
	@echo "$(BLUE)Запуск тестов с покрытием...$(NC)"
	PYTHONPATH=. pytest tests/ -v --cov=app --cov-report=term-missing --cov-report=html:htmlcov --cov-fail-under=80

test-watch: ## Запустить тесты в режиме наблюдения
	@echo "$(BLUE)Запуск тестов в режиме наблюдения...$(NC)"
	PYTHONPATH=. pytest tests/ -v -f --tb=short

manual-test: ## Запустить ручные тесты через скрипт
	@echo "$(BLUE)Запуск ручных тестов...$(NC)"
	python scripts/manual_test_runner.py

clean: ## Очистить временные файлы и кэш
	@echo "$(BLUE)Очистка временных файлов...$(NC)"
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type f -name "*.pyo" -delete 2>/dev/null || true
	find . -type f -name "*.pyd" -delete 2>/dev/null || true
	rm -rf .pytest_cache/ 2>/dev/null || true
	rm -rf htmlcov/ 2>/dev/null || true
	rm -rf .coverage 2>/dev/null || true
	rm -rf temp/ 2>/dev/null || true
	rm -rf logs/*.log 2>/dev/null || true

setup: ## Настройка окружения для тестирования
	@echo "$(BLUE)Настройка окружения для тестирования...$(NC)"
	mkdir -p logs
	mkdir -p temp
	mkdir -p htmlcov
	@echo "$(GREEN)Окружение настроено!$(NC)"

check-env: ## Проверить переменные окружения
	@echo "$(BLUE)Проверка переменных окружения...$(NC)"
	@if [ -f .env ]; then \
		echo "$(GREEN)Файл .env найден$(NC)"; \
	else \
		echo "$(YELLOW)Файл .env не найден. Создайте его на основе env.example$(NC)"; \
	fi
	@echo "BOT_TOKEN: $$(if [ -n "$$BOT_TOKEN" ]; then echo "$(GREEN)установлен$(NC)"; else echo "$(RED)не установлен$(NC)"; fi)"
	@echo "YANDEX_DISK_TOKEN: $$(if [ -n "$$YANDEX_DISK_TOKEN" ]; then echo "$(GREEN)установлен$(NC)"; else echo "$(YELLOW)не установлен (опционально)$(NC)"; fi)"

lint: ## Запустить линтер
	@echo "$(BLUE)Запуск линтера...$(NC)"
	flake8 app/ tests/ --max-line-length=120 --ignore=E501,W503

types: ## Запустить проверку типов
	@echo "$(BLUE)Запуск проверки типов...$(NC)"
	mypy app/ --ignore-missing-imports

format: ## Форматировать код
	@echo "$(BLUE)Форматирование кода...$(NC)"
	black app/ tests/ --line-length=120
	isort app/ tests/

security-check: ## Проверка безопасности
	@echo "$(BLUE)Проверка безопасности...$(NC)"
	bandit -r app/ -f json -o security_report.json || true
	@echo "$(GREEN)Отчет о безопасности сохранен в security_report.json$(NC)"

test-report: ## Генерировать отчет о тестировании
	@echo "$(BLUE)Генерация отчета о тестировании...$(NC)"
	python scripts/run_all_tests.py --all
	@echo "$(GREEN)Отчет сохранен в logs/comprehensive_test_report.json$(NC)"

ci: ## Запуск для CI/CD
	@echo "$(BLUE)Запуск тестов для CI/CD...$(NC)"
	make setup
	make check-env
	make test-unit
	make test-integration
	make test-security
	make lint
	make types

dev: ## Запуск для разработки
	@echo "$(BLUE)Запуск тестов для разработки...$(NC)"
	make test-quick
	make lint
	make types

# Алиасы для удобства
t: test
ta: test-all
tm: test-manual
tu: test-unit
ti: test-integration
tp: test-performance
ts: test-security
tl: test-lint
tt: test-types
tq: test-quick
tc: test-coverage
tw: test-watch
mt: manual-test
c: clean
s: setup
ce: check-env
l: lint
ty: types
f: format
sc: security-check
tr: test-report 