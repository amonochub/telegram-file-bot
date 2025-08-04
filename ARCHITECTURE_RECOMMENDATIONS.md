# Дополнительные рекомендации по улучшению архитектуры

## Анализ архитектурных проблем

### 1. Проблемы разделения ответственности

**Текущие проблемы:**
- Handlers содержат бизнес-логику
- Services смешивают разные уровни абстракции  
- Отсутствуют четкие границы между слоями

**Рекомендуемая архитектура:**
```
app/
├── handlers/          # Только UI логика
├── services/          # Бизнес-логика
├── repositories/      # Доступ к данным
├── models/           # Доменные модели
└── interfaces/       # Абстракции
```

### 2. Dependency Injection

**Текущая проблема:**
```python
# Прямая зависимость
from app.config import settings
yandex_service = YandexDiskService(settings.yandex_disk_token)
```

**Рекомендуемое решение:**
```python
# Через DI контейнер
@inject
class FileHandler:
    def __init__(self, yandex_service: YandexDiskService):
        self.yandex_service = yandex_service
```

### 3. Обработка ошибок

**Создать иерархию исключений:**
```python
class ApplicationError(Exception):
    """Базовое исключение приложения"""
    pass

class BusinessLogicError(ApplicationError):
    """Ошибки бизнес-логики"""
    pass

class ExternalServiceError(ApplicationError):
    """Ошибки внешних сервисов"""
    pass
```

### 4. Асинхронность

**Проблемы:**
- Смешение sync/async кода
- Блокирующие операции в async функциях

**Решения:**
- Использовать `asyncio.to_thread()` для CPU-интенсивных задач
- Все I/O операции должны быть асинхронными

### 5. Типизация

**Добавить строгую типизацию:**
```python
from typing import Protocol

class FileStorage(Protocol):
    async def upload(self, file_path: Path) -> str: ...
    async def download(self, file_id: str) -> bytes: ...
```

### 6. Конфигурация

**Улучшить систему настроек:**
```python
class DatabaseSettings(BaseSettings):
    host: str
    port: int
    
class TelegramSettings(BaseSettings):
    bot_token: str
    
class AppSettings(BaseSettings):
    database: DatabaseSettings
    telegram: TelegramSettings
```

### 7. Валидация

**Добавить валидацию на входе:**
```python
from pydantic import BaseModel, validator

class FileUploadRequest(BaseModel):
    file_size: int
    file_type: str
    
    @validator('file_size')
    def validate_size(cls, v):
        if v > 100_000_000:  # 100MB
            raise ValueError('File too large')
        return v
```

### 8. Мониторинг и метрики

**Добавить observability:**
```python
import structlog
from prometheus_client import Counter, Histogram

file_uploads = Counter('file_uploads_total', 'Total file uploads')
processing_time = Histogram('processing_seconds', 'Processing time')

@processing_time.time()
async def process_file(file_path: Path):
    file_uploads.inc()
    # обработка
```

### 9. Тестирование

**Улучшить тестируемость:**
```python
# Моки для внешних сервисов
@pytest.fixture
def mock_yandex_service():
    return Mock(spec=YandexDiskService)

# Интеграционные тесты
@pytest.mark.integration
async def test_file_upload_flow():
    # тест полного флоу
    pass
```

### 10. Документация API

**Добавить OpenAPI спецификацию:**
```python
from pydantic import BaseModel

class FileAnalysisResponse(BaseModel):
    """Результат анализа файла"""
    document_type: str
    confidence: float
    parameters: Dict[str, List[str]]
    
    class Config:
        schema_extra = {
            "example": {
                "document_type": "invoice",
                "confidence": 0.95,
                "parameters": {"iban": ["DE89370400440532013000"]}
            }
        }
```

## Приоритеты реализации

### Фаза 1 (Критично - 1 неделя)
1. ✅ Исправить инициализацию Settings
2. ✅ Исправить проблемы безопасности  
3. ✅ Исправить форматирование кода
4. Исправить ошибки типизации

### Фаза 2 (Высокий приоритет - 2 недели)  
1. Внедрить dependency injection
2. Разделить ответственность handlers/services
3. Улучшить обработку ошибок
4. Добавить строгую типизацию

### Фаза 3 (Средний приоритет - 1 неделя)
1. Добавить мониторинг
2. Улучшить тестирование
3. Оптимизировать производительность

### Фаза 4 (Улучшения - 1 неделя)
1. Документация API
2. Рефакторинг конфигурации
3. UX улучшения

## Инструменты для автоматизации

### Pre-commit hooks
```yaml
repos:
  - repo: https://github.com/psf/black
    rev: 23.3.0
    hooks:
      - id: black
  - repo: https://github.com/pycqa/isort
    rev: 5.12.0
    hooks:
      - id: isort
  - repo: https://github.com/pycqa/flake8
    rev: 6.0.0
    hooks:
      - id: flake8
  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.3.0
    hooks:
      - id: mypy
```

### CI/CD Pipeline
```yaml
name: Code Quality
on: [push, pull_request]
jobs:
  quality:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: pip install -r requirements.dev.txt
      - name: Run linting
        run: |
          flake8 app/
          mypy app/
          black --check app/
          isort --check app/
      - name: Run tests
        run: pytest --cov=app tests/
      - name: Security scan
        run: bandit -r app/
```

Эти рекомендации помогут превратить проект из текущего состояния в хорошо структурированное, поддерживаемое и масштабируемое приложение.