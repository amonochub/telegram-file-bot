# Рефакторинг меню бота

## Обзор изменений

Файл `app/handlers/menu.py` был рефакторен для улучшения масштабируемости, читаемости и тестируемости. Вместо одного большого файла теперь используется модульная структура с дополнительными улучшениями.

## Новая структура

```
app/handlers/menu/
├── __init__.py          # Главный роутер меню
├── overview.py          # Обзор папок
├── upload.py            # Загрузка файлов
├── ai_verification.py   # Проверка ИИ
├── ocr.py              # Распознавание PDF
├── client_calc.py      # Расчёт для клиента
├── cbr_rates.py        # Курсы ЦБ
├── help.py             # Помощь
└── main.py             # Главное меню и неизвестные команды

app/constants/
└── messages.py         # Текстовые константы

app/middleware/
└── error_handler.py    # Глобальная обработка ошибок

app/utils/
├── logging_context.py  # Контекстное логирование
└── navigation.py       # Система навигации с историей

tests/
├── test_menu_refactored.py  # Базовые тесты
└── test_menu_advanced.py    # Расширенные тесты
```

## Ключевые улучшения

### 1. Модульная структура
- Каждый тип меню теперь в отдельном файле
- Легко добавлять новые функции меню
- Простое тестирование отдельных модулей

### 2. Структурированное логирование
- Заменены `print()` на `structlog`
- Единообразное логирование во всех модулях
- Логи попадают в систему логирования
- **НОВОЕ**: Контекстное логирование с информацией о пользователе

### 3. Типизация
- Добавлены return types для всех функций
- Улучшено автодополнение в IDE
- Лучшая документация кода

### 4. Константы сообщений
- Все тексты вынесены в `app/constants/messages.py`
- Легко локализовать и изменять тексты
- Нет дублирования строк
- **НОВОЕ**: Константы для сообщений об ошибках

### 5. Документирование
- Добавлены docstrings для всех функций
- Описание параметров и назначения
- Примеры использования

### 6. Глобальная обработка ошибок
- **НОВОЕ**: Middleware для обработки ошибок
- Автоматическое логирование ошибок
- Пользовательские сообщения об ошибках
- Разделение ошибок Telegram API и внутренних ошибок

### 7. Система навигации с историей
- **НОВОЕ**: Класс `NavigationHistory` для управления историей
- Функции `navigate_to_menu()` и `go_back()`
- Ограничение истории (максимум 10 элементов)
- "Хлебные крошки" для отслеживания пути

### 8. Контекстное логирование
- **НОВОЕ**: Утилиты для извлечения контекста пользователя
- Автоматическое логирование с информацией о пользователе
- Структурированные логи для анализа

## Примеры использования

### Добавление нового пункта меню

1. Создайте новый модуль в `app/handlers/menu/`:
```python
# app/handlers/menu/new_feature.py
import structlog
from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.constants.messages import NEW_FEATURE_TEXT, ERROR_NEW_FEATURE
from app.keyboards.menu import main_menu
from app.utils.logging_context import log_handler_call, log_handler_error
from app.utils.navigation import navigate_to_menu

router = Router()
log = structlog.get_logger()

@router.message(F.text == NEW_FEATURE_TEXT)
async def new_feature_menu(message: Message, state: FSMContext) -> None:
    """Обработчик нового пункта меню"""
    try:
        log_handler_call("new_feature_menu", message, menu_text=message.text)
        await navigate_to_menu(state, "new_feature", action="feature_action")
        await state.clear()
        # Ваша логика здесь
    except Exception as e:
        log_handler_error("new_feature_menu", message, e)
        await message.answer(ERROR_NEW_FEATURE, reply_markup=main_menu())
```

2. Добавьте константы в `app/constants/messages.py`:
```python
NEW_FEATURE_TEXT = "🆕 Новая функция"
ERROR_NEW_FEATURE = "❌ Произошла ошибка в новой функции. Попробуйте позже."
```

3. Подключите роутер в `app/handlers/menu/__init__.py`:
```python
from .new_feature import router as new_feature_router
# ...
menu_router.include_router(new_feature_router)
```

### Использование системы навигации

```python
from app.utils.navigation import navigate_to_menu, go_back, NavigationHistory

# Переход к меню с сохранением истории
await navigate_to_menu(state, "overview", action="browse_folders")

# Возврат к предыдущему меню
previous_menu = await go_back(state)
if previous_menu:
    print(f"Вернулись к: {previous_menu['menu']}")

# Получение хлебных крошек
nav = NavigationHistory(state)
breadcrumbs = await nav.get_breadcrumbs()
print(f"Путь: {' > '.join(breadcrumbs)}")
```

### Контекстное логирование

```python
from app.utils.logging_context import log_handler_call, log_handler_error

# Логирование вызова обработчика
log_handler_call("my_handler", message, extra_data="custom_info")

# Логирование ошибки
try:
    # Ваш код
    pass
except Exception as e:
    log_handler_error("my_handler", message, e, context="additional_info")
```

## Тестирование

### Базовые тесты
```python
@pytest.mark.asyncio
async def test_new_feature_menu(mock_message, mock_state):
    """Тест нового пункта меню"""
    mock_message.text = NEW_FEATURE_TEXT
    
    await new_feature_menu(mock_message, mock_state)
    
    mock_state.clear.assert_called_once()
    # Другие проверки
```

### Тесты навигации
```python
@pytest.mark.asyncio
async def test_navigation_flow(mock_state):
    """Тест потока навигации"""
    await navigate_to_menu(mock_state, "menu1")
    await navigate_to_menu(mock_state, "menu2")
    
    nav = NavigationHistory(mock_state)
    breadcrumbs = await nav.get_breadcrumbs()
    assert breadcrumbs == ["menu1", "menu2"]
```

### Тесты обработки ошибок
```python
@pytest.mark.asyncio
async def test_error_handling(mock_message, mock_state):
    """Тест обработки ошибок"""
    with patch('my_function', side_effect=Exception("Test error")):
        await my_handler(mock_message, mock_state)
        
        mock_message.answer.assert_called_once()
        call_args = mock_message.answer.call_args
        assert "❌" in call_args[0][0]
```

## Миграция

### Из старой структуры
Старый файл `app/handlers/menu.py` сохранен как `app/handlers/menu.py.backup`

### В новую структуру
1. Обновите импорты в `app/routers/__init__.py`
2. Используйте новые константы из `app/constants/messages.py`
3. Подключите middleware для обработки ошибок
4. Запустите тесты для проверки работоспособности

## Преимущества новой структуры

1. **Масштабируемость**: Легко добавлять новые функции меню
2. **Читаемость**: Каждый файл отвечает за одну функцию
3. **Тестируемость**: Можно тестировать каждый модуль отдельно
4. **Поддерживаемость**: Проще находить и исправлять ошибки
5. **Локализация**: Тексты вынесены в отдельные файлы
6. **Типизация**: Лучшая поддержка IDE и статического анализа
7. **Отказоустойчивость**: Глобальная обработка ошибок
8. **Навигация**: История переходов и хлебные крошки
9. **Мониторинг**: Структурированное логирование с контекстом

## Совместимость

Новая структура полностью совместима с существующим кодом. Все обработчики работают так же, как и раньше, но теперь код лучше организован и легче поддерживается.

## Следующие шаги

1. Добавить больше тестов для покрытия всех сценариев
2. Реализовать метрики и мониторинг
3. Добавить кэширование для часто используемых данных
4. Рассмотреть инъекцию зависимостей для сложных модулей
5. Добавить систему уведомлений об ошибках (Sentry, etc.) 