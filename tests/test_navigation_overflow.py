"""
Тесты для проверки логирования переполнения истории навигации
"""

import pytest
from unittest.mock import AsyncMock, patch
from aiogram.fsm.context import FSMContext

from app.utils.navigation import NavigationHistory, MAX_HISTORY


@pytest.fixture
def mock_state():
    """Фикстура для создания мок-состояния FSMContext"""
    state = AsyncMock(spec=FSMContext)
    state.clear = AsyncMock()
    state.get_data = AsyncMock(return_value={})
    state.update_data = AsyncMock()

    # Возвращаем состояние для использования в тестах
    yield state

    # Очищаем состояние между тестами для предотвращения "протекания"
    NavigationHistory._histories.pop(state, None)


@pytest.mark.asyncio
async def test_navigation_history_overflow_logging(mock_state):
    """Тест логирования при переполнении истории"""
    nav = NavigationHistory(mock_state)

    # Создаем историю, превышающую лимит
    long_history = [{"menu": f"menu_{i}", "context": {}} for i in range(MAX_HISTORY + 5)]
    NavigationHistory._histories[mock_state] = long_history

    with patch("app.utils.navigation.logger.info") as mock_log:
        await nav.push("new_menu")

        # Проверяем, что было залогировано переполнение
        mock_log.assert_called_once()
        log_message = mock_log.call_args[0][0]
        assert "История переполнена" in log_message
        assert "удалено 6 старых пунктов" in log_message  # 15 + 1 - 10 = 6


@pytest.mark.asyncio
async def test_navigation_history_no_overflow_logging(mock_state):
    """Тест отсутствия логирования при нормальном размере истории"""
    nav = NavigationHistory(mock_state)

    # Создаем историю в пределах лимита
    normal_history = [{"menu": f"menu_{i}", "context": {}} for i in range(MAX_HISTORY - 1)]
    NavigationHistory._histories[mock_state] = normal_history

    with patch("app.utils.navigation.logger.info") as mock_log:
        await nav.push("new_menu")

        # Проверяем, что логирования переполнения не было
        mock_log.assert_not_called()


@pytest.mark.asyncio
async def test_navigation_history_exact_limit_logging(mock_state):
    """Тест логирования при достижении точного лимита"""
    nav = NavigationHistory(mock_state)

    # Создаем историю точно на лимите
    exact_history = [{"menu": f"menu_{i}", "context": {}} for i in range(MAX_HISTORY)]
    NavigationHistory._histories[mock_state] = exact_history

    with patch("app.utils.navigation.logger.info") as mock_log:
        await nav.push("new_menu")

        # Проверяем, что было залогировано переполнение
        mock_log.assert_called_once()
        log_message = mock_log.call_args[0][0]
        assert "История переполнена" in log_message
        assert "удалено 1 старых пунктов" in log_message  # 10 + 1 - 10 = 1


@pytest.mark.asyncio
async def test_navigation_history_overflow_keeps_latest(mock_state):
    """Тест, что при переполнении сохраняются последние элементы"""
    nav = NavigationHistory(mock_state)

    # Создаем историю, превышающую лимит
    long_history = [{"menu": f"menu_{i}", "context": {}} for i in range(MAX_HISTORY + 3)]
    NavigationHistory._histories[mock_state] = long_history

    await nav.push("new_menu")

    # Проверяем, что остались только последние MAX_HISTORY элементов
    final_history = NavigationHistory._histories[mock_state]
    assert len(final_history) == MAX_HISTORY

    # Проверяем, что последний элемент - это новый
    assert final_history[-1]["menu"] == "new_menu"

    # Проверяем, что сохранились последние элементы из исходной истории
    # После добавления нового элемента и обрезки до MAX_HISTORY
    expected_menus = [f"menu_{i}" for i in range(4, MAX_HISTORY + 3)] + ["new_menu"]
    actual_menus = [item["menu"] for item in final_history]
    assert actual_menus == expected_menus


@pytest.mark.asyncio
async def test_max_history_constant():
    """Тест, что константа MAX_HISTORY доступна и имеет правильное значение"""
    assert MAX_HISTORY == 10
    assert isinstance(MAX_HISTORY, int)
    assert MAX_HISTORY > 0


@pytest.mark.asyncio
async def test_logger_implementation_correctness(mock_state):
    """Тест соответствия реализации - проверяем правильное использование logger"""
    nav = NavigationHistory(mock_state)

    # Создаем историю точно на лимите
    exact_history = [{"menu": f"menu_{i}", "context": {}} for i in range(MAX_HISTORY)]
    NavigationHistory._histories[mock_state] = exact_history

    # Проверяем, что используется правильный logger (не logging.info напрямую)
    with patch("app.utils.navigation.logger.info") as mock_log:
        await nav.push("new_menu")

        # Проверяем, что logger.info был вызван
        mock_log.assert_called_once()

        # Проверяем точное соответствие сообщения
        log_message = mock_log.call_args[0][0]
        assert log_message == "[push] История переполнена, удалено 1 старых пунктов"


@pytest.mark.asyncio
async def test_cleanup_between_tests(mock_state):
    """Тест, что состояние очищается между тестами"""
    # Проверяем, что состояние изначально чистое
    assert mock_state not in NavigationHistory._histories

    # Добавляем что-то в историю
    NavigationHistory._histories[mock_state] = [{"menu": "test", "context": {}}]
    assert mock_state in NavigationHistory._histories

    # После завершения теста фикстура должна очистить состояние
    # Это проверяется в следующем тесте
