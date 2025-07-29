"""
Расширенные тесты для рефакторенной структуры меню
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from app.handlers.menu.overview import browse_menu
from app.handlers.menu.upload import upload_menu
from app.handlers.menu.help import help_button
from app.constants.messages import (
    OVERVIEW_MENU_TEXT,
    UPLOAD_MENU_TEXT,
    UPLOAD_INSTRUCTIONS,
    HELP_MENU_TEXT,
    HELP_TEXT,
    ERROR_OVERVIEW_FOLDERS
)
from app.utils.navigation import NavigationHistory, navigate_to_menu, go_back
from app.middleware.error_handler import ErrorHandlerMiddleware

# Создаем собственный класс для TelegramAPIError, если он недоступен
class TelegramAPIError(Exception):
    """Исключение для ошибок Telegram API"""
    pass


@pytest.fixture
def mock_message():
    """Фикстура для создания мок-сообщения"""
    message = AsyncMock(spec=Message)
    
    # Создаем вложенные объекты
    message.from_user = AsyncMock()
    message.from_user.id = 123456
    message.from_user.username = "test_user"
    message.from_user.first_name = "Test"
    
    message.chat = AsyncMock()
    message.chat.id = 789012
    message.chat.type = "private"
    
    message.message_id = 1
    message.text = OVERVIEW_MENU_TEXT
    message.answer = AsyncMock()
    return message


@pytest.fixture
def mock_callback_query():
    """Фикстура для создания мок-callback query"""
    callback = AsyncMock(spec=CallbackQuery)
    
    # Создаем вложенные объекты
    callback.from_user = AsyncMock()
    callback.from_user.id = 123456
    callback.from_user.username = "test_user"
    callback.from_user.first_name = "Test"
    
    callback.chat = AsyncMock()
    callback.chat.id = 789012
    callback.chat.type = "private"
    
    callback.data = "test_callback"
    callback.message = AsyncMock()
    callback.message.answer = AsyncMock()
    callback.message.message_id = 1
    callback.message.chat = AsyncMock()
    callback.message.chat.id = 789012
    callback.message.chat.type = "private"
    return callback


@pytest.fixture
def mock_state():
    """Фикстура для создания мок-состояния"""
    state = AsyncMock(spec=FSMContext)
    state.clear = AsyncMock()
    state.get_data = AsyncMock(return_value={})
    state.update_data = AsyncMock()
    return state


@pytest.fixture
def mock_state_with_history():
    """Фикстура для создания мок-состояния с историей навигации"""
    state = AsyncMock(spec=FSMContext)
    state.clear = AsyncMock()
    state.get_data = AsyncMock(return_value={
        'navigation_history': [
            {'menu': 'menu1', 'context': {}},
            {'menu': 'menu2', 'context': {}}
        ]
    })
    state.update_data = AsyncMock()
    return state


@pytest.fixture
def mock_state_with_long_history():
    """Фикстура для создания мок-состояния с длинной историей"""
    long_history = [{'menu': f'menu{i}', 'context': {}} for i in range(15)]
    state = AsyncMock(spec=FSMContext)
    state.clear = AsyncMock()
    state.get_data = AsyncMock(return_value={'navigation_history': long_history})
    state.update_data = AsyncMock()
    return state


class TestNavigationHistory:
    """Тесты для системы навигации"""
    
    @pytest.mark.asyncio
    async def test_navigation_history_push(self, mock_state):
        """Тест добавления в историю навигации"""
        nav = NavigationHistory(mock_state)
        await nav.push("test_menu", action="test_action")
        
        mock_state.update_data.assert_called_once()
        call_args = mock_state.update_data.call_args[1]
        assert 'navigation_history' in call_args
        history = call_args['navigation_history']
        assert len(history) == 1
        assert history[0]['menu'] == "test_menu"
        assert history[0]['context']['action'] == "test_action"
    
    @pytest.mark.asyncio
    async def test_navigation_history_pop(self, mock_state_with_history):
        """Тест возврата из истории навигации"""
        nav = NavigationHistory(mock_state_with_history)
        result = await nav.pop()
        
        assert result['menu'] == 'menu1'
        mock_state_with_history.update_data.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_navigation_history_pop_empty(self, mock_state):
        """Тест возврата из пустой истории навигации"""
        nav = NavigationHistory(mock_state)
        result = await nav.pop()
        
        assert result is None
        mock_state.update_data.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_navigation_history_breadcrumbs(self, mock_state_with_history):
        """Тест получения хлебных крошек"""
        nav = NavigationHistory(mock_state_with_history)
        breadcrumbs = await nav.get_breadcrumbs()
        
        assert breadcrumbs == ['menu1', 'menu2']
    
    @pytest.mark.asyncio
    async def test_navigation_history_limit(self, mock_state_with_long_history):
        """Тест ограничения размера истории"""
        nav = NavigationHistory(mock_state_with_long_history)
        await nav.push("new_menu")
        
        # Проверяем, что история ограничена 10 элементами
        call_args = mock_state_with_long_history.update_data.call_args[1]
        history = call_args['navigation_history']
        assert len(history) == 10
        assert history[-1]['menu'] == "new_menu"
    
    @pytest.mark.asyncio
    async def test_navigation_history_clear(self, mock_state_with_history):
        """Тест очистки истории навигации"""
        nav = NavigationHistory(mock_state_with_history)
        await nav.clear()
        
        mock_state_with_history.update_data.assert_called_once_with(navigation_history=[])
    
    @pytest.mark.asyncio
    async def test_navigation_history_get_current(self, mock_state_with_history):
        """Тест получения текущего меню"""
        nav = NavigationHistory(mock_state_with_history)
        current = await nav.get_current()
        
        assert current['menu'] == 'menu2'
    
    @pytest.mark.asyncio
    async def test_navigation_history_get_current_empty(self, mock_state):
        """Тест получения текущего меню из пустой истории"""
        nav = NavigationHistory(mock_state)
        current = await nav.get_current()
        
        assert current is None


class TestErrorHandling:
    """Тесты для обработки ошибок"""
    
    @pytest.mark.asyncio
    async def test_browse_menu_handles_exception(self, mock_message, mock_state):
        """Тест обработки исключений в browse_menu"""
        # Симулируем исключение при вызове files_command
        with patch('app.handlers.browse.files_command', side_effect=Exception("Test error")):
            await browse_menu(mock_message, mock_state)
            
            # Проверяем, что пользователю отправлено сообщение об ошибке
            mock_message.answer.assert_called_once()
            call_args = mock_message.answer.call_args
            assert ERROR_OVERVIEW_FOLDERS in call_args[0][0]
    
    @pytest.mark.asyncio
    async def test_browse_menu_handles_answer_exception(self, mock_message, mock_state):
        """Тест обработки исключения при отправке сообщения об ошибке"""
        # Симулируем исключение при вызове files_command
        with patch('app.handlers.browse.files_command', side_effect=Exception("Test error")):
            # Симулируем исключение при отправке сообщения
            mock_message.answer.side_effect = TelegramAPIError("Message send failed")
            
            # Обработчик должен не падать, а логировать ошибку
            with patch('app.handlers.menu.overview.log_handler_error') as mock_log:
                await browse_menu(mock_message, mock_state)
                
                # Проверяем, что ошибка залогирована
                assert mock_log.call_count == 2  # Одна для основной ошибки, одна для ошибки отправки
    
    @pytest.mark.asyncio
    async def test_error_handler_middleware_telegram_api_error(self, mock_message):
        """Тест middleware для ошибок Telegram API"""
        middleware = ErrorHandlerMiddleware()
        
        # Создаем обработчик, который вызывает TelegramAPIError
        async def handler_with_error(event, data):
            raise TelegramAPIError("Test API error")
        
        # Вызываем middleware
        with patch('app.middleware.error_handler.log') as mock_log:
            result = await middleware(handler_with_error, mock_message, {})
            
            # Проверяем, что ошибка залогирована
            mock_log.error.assert_called_once()
            log_call = mock_log.error.call_args
            assert "Unexpected error in handler" in log_call[0][0]
            
            # Проверяем, что ошибка не пробрасывается наружу
            assert result is None
    
    @pytest.mark.asyncio
    async def test_error_handler_middleware_general_error(self, mock_message):
        """Тест middleware для общих ошибок"""
        middleware = ErrorHandlerMiddleware()
        
        # Создаем обработчик, который вызывает общее исключение
        async def handler_with_error(event, data):
            raise ValueError("Test general error")
        
        # Вызываем middleware
        with patch('app.middleware.error_handler.log') as mock_log:
            result = await middleware(handler_with_error, mock_message, {})
            
            # Проверяем, что ошибка залогирована
            mock_log.error.assert_called_once()
            log_call = mock_log.error.call_args
            assert "Unexpected error in handler" in log_call[0][0]
            
            # Проверяем, что ошибка не пробрасывается наружу
            assert result is None
    
    @pytest.mark.asyncio
    async def test_error_handler_middleware_successful_handler(self, mock_message):
        """Тест middleware для успешного обработчика"""
        middleware = ErrorHandlerMiddleware()
        
        # Создаем успешный обработчик
        async def successful_handler(event, data):
            return "success"
        
        # Вызываем middleware
        result = await middleware(successful_handler, mock_message, {})
        
        # Проверяем, что результат пробрасывается
        assert result == "success"
    
    @pytest.mark.asyncio
    async def test_error_handler_middleware_callback_query(self, mock_callback_query):
        """Тест middleware для callback query"""
        middleware = ErrorHandlerMiddleware()
        
        # Создаем обработчик, который вызывает исключение
        async def handler_with_error(event, data):
            raise Exception("Test error")
        
        # Вызываем middleware
        with patch('app.middleware.error_handler.log') as mock_log:
            result = await middleware(handler_with_error, mock_callback_query, {})
            
            # Проверяем, что ошибка залогирована
            mock_log.error.assert_called_once()
            
            # Проверяем, что ошибка не пробрасывается наружу
            assert result is None


class TestLoggingContext:
    """Тесты для контекстного логирования"""
    
    @pytest.mark.asyncio
    async def test_log_handler_call_with_context(self, mock_message):
        """Тест логирования вызова обработчика с контекстом"""
        from app.utils.logging_context import log_handler_call
        
        with patch('app.utils.logging_context.structlog.get_logger') as mock_logger:
            mock_log = AsyncMock()
            mock_logger.return_value = mock_log
            
            log_handler_call("test_handler", mock_message, extra_data="test")
            
            # Проверяем, что лог вызван с правильными параметрами
            mock_log.info.assert_called_once()
            call_args = mock_log.info.call_args[1]
            assert call_args['user_id'] == 123456
            assert call_args['username'] == "test_user"
            assert call_args['extra_data'] == "test"
    
    @pytest.mark.asyncio
    async def test_log_handler_error_with_context(self, mock_message):
        """Тест логирования ошибки с контекстом"""
        from app.utils.logging_context import log_handler_error
        
        with patch('app.utils.logging_context.structlog.get_logger') as mock_logger:
            mock_log = AsyncMock()
            mock_logger.return_value = mock_log
            
            test_error = ValueError("Test error")
            log_handler_error("test_handler", mock_message, test_error, extra_data="test")
            
            # Проверяем, что лог вызван с правильными параметрами
            mock_log.error.assert_called_once()
            call_args = mock_log.error.call_args[1]
            assert call_args['user_id'] == 123456
            assert call_args['error'] == "Test error"
            assert call_args['error_type'] == "ValueError"
            assert call_args['extra_data'] == "test"
    
    @pytest.mark.asyncio
    async def test_get_user_context_message(self, mock_message):
        """Тест извлечения контекста из сообщения"""
        from app.utils.logging_context import get_user_context
        
        context = get_user_context(mock_message)
        
        assert context['user_id'] == 123456
        assert context['username'] == "test_user"
        assert context['first_name'] == "Test"
        assert context['chat_id'] == 789012
        assert context['chat_type'] == "private"
        assert context['message_id'] == 1
        assert context['text'] == OVERVIEW_MENU_TEXT
        assert context['message_type'] == "message"
    
    @pytest.mark.asyncio
    async def test_get_user_context_callback(self, mock_callback_query):
        """Тест извлечения контекста из callback query"""
        from app.utils.logging_context import get_user_context
        
        context = get_user_context(mock_callback_query)
        
        assert context['user_id'] == 123456
        assert context['username'] == "test_user"
        assert context['first_name'] == "Test"
        assert context['chat_id'] == 789012
        assert context['chat_type'] == "private"
        assert context['callback_data'] == "test_callback"
        assert context['message_type'] == "callback"


class TestMenuIntegration:
    """Интеграционные тесты для меню"""
    
    @pytest.mark.asyncio
    async def test_menu_navigation_flow(self, mock_message, mock_state):
        """Тест полного потока навигации по меню"""
        # Начинаем с главного меню
        await navigate_to_menu(mock_state, "main_menu")
        
        # Переходим к обзору папок
        await navigate_to_menu(mock_state, "overview")
        
        # Проверяем историю
        nav = NavigationHistory(mock_state)
        breadcrumbs = await nav.get_breadcrumbs()
        assert breadcrumbs == ["main_menu", "overview"]
        
        # Возвращаемся назад
        previous = await go_back(mock_state)
        assert previous['menu'] == "main_menu"
        
        # Проверяем обновленную историю
        breadcrumbs = await nav.get_breadcrumbs()
        assert breadcrumbs == ["main_menu"]
    
    @pytest.mark.asyncio
    async def test_menu_error_recovery(self, mock_message, mock_state):
        """Тест восстановления после ошибки в меню"""
        # Симулируем ошибку в обработчике
        with patch('app.handlers.browse.files_command', side_effect=Exception("Test error")):
            await browse_menu(mock_message, mock_state)
            
            # Проверяем, что состояние очищено
            mock_state.clear.assert_called_once()
            
            # Проверяем, что пользователь получил сообщение об ошибке
            mock_message.answer.assert_called_once()
            call_args = mock_message.answer.call_args
            assert "❌" in call_args[0][0]  # Проверяем наличие эмодзи ошибки
    
    @pytest.mark.asyncio
    async def test_menu_successful_flow(self, mock_message, mock_state):
        """Тест успешного потока меню"""
        # Симулируем успешный вызов files_command
        with patch('app.handlers.browse.files_command') as mock_files:
            await browse_menu(mock_message, mock_state)
            
            # Проверяем, что состояние очищено
            mock_state.clear.assert_called_once()
            
            # Проверяем, что files_command вызван
            mock_files.assert_called_once_with(mock_message)
            
            # Проверяем, что сообщение об ошибке НЕ отправлено
            mock_message.answer.assert_not_called()


class TestEdgeCases:
    """Тесты граничных случаев"""
    
    @pytest.mark.asyncio
    async def test_navigation_with_empty_context(self, mock_state):
        """Тест навигации с пустым контекстом"""
        await navigate_to_menu(mock_state, "test_menu")
        
        nav = NavigationHistory(mock_state)
        current = await nav.get_current()
        
        assert current['menu'] == "test_menu"
        assert current['context'] == {}
    
    @pytest.mark.asyncio
    async def test_navigation_with_complex_context(self, mock_state):
        """Тест навигации со сложным контекстом"""
        complex_context = {
            'action': 'test_action',
            'params': {'key': 'value'},
            'timestamp': 1234567890
        }
        
        await navigate_to_menu(mock_state, "test_menu", **complex_context)
        
        nav = NavigationHistory(mock_state)
        current = await nav.get_current()
        
        assert current['menu'] == "test_menu"
        assert current['context'] == complex_context
    
    @pytest.mark.asyncio
    async def test_state_update_failure(self, mock_state):
        """Тест обработки ошибки обновления состояния"""
        # Симулируем ошибку при обновлении состояния
        mock_state.update_data.side_effect = Exception("State update failed")
        
        nav = NavigationHistory(mock_state)
        
        # Обработчик должен не падать
        with patch('app.utils.navigation.logger.error') as mock_log:
            await nav.push("test_menu")
            
            # Проверяем, что ошибка залогирована
            mock_log.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_state_get_data_failure(self, mock_state):
        """Тест обработки ошибки получения данных состояния"""
        # Симулируем ошибку при получении данных
        mock_state.get_data.side_effect = Exception("Get data failed")
        
        nav = NavigationHistory(mock_state)
        
        # Обработчик должен не падать и вернуть пустой результат
        with patch('app.utils.navigation.logger.error') as mock_log:
            result = await nav.get_current()
            
            assert result is None
            # Проверяем, что ошибка залогирована
            mock_log.assert_called_once()


class TestParameterizedTests:
    """Параметризованные тесты для покрытия разных сценариев"""
    
    @pytest.mark.parametrize("menu_name,expected_breadcrumb", [
        ("main_menu", "main_menu"),
        ("overview", "overview"),
        ("upload", "upload"),
        ("help", "help"),
        ("", ""),  # Пустое имя
        ("very_long_menu_name_that_might_cause_issues", "very_long_menu_name_that_might_cause_issues"),
    ])
    @pytest.mark.asyncio
    async def test_navigation_with_different_menu_names(self, mock_state, menu_name, expected_breadcrumb):
        """Тест навигации с разными именами меню"""
        await navigate_to_menu(mock_state, menu_name)
        
        nav = NavigationHistory(mock_state)
        breadcrumbs = await nav.get_breadcrumbs()
        
        assert breadcrumbs == [expected_breadcrumb]
    
    @pytest.mark.parametrize("error_type,expected_message", [
        (ValueError, "ValueError"),
        (TypeError, "TypeError"),
        (RuntimeError, "RuntimeError"),
        (Exception, "Exception"),
    ])
    @pytest.mark.asyncio
    async def test_error_logging_with_different_exceptions(self, mock_message, error_type, expected_message):
        """Тест логирования разных типов исключений"""
        from app.utils.logging_context import log_handler_error
        
        with patch('app.utils.logging_context.structlog.get_logger') as mock_logger:
            mock_log = AsyncMock()
            mock_logger.return_value = mock_log
            
            test_error = error_type("Test error")
            log_handler_error("test_handler", mock_message, test_error)
            
            call_args = mock_log.error.call_args[1]
            assert call_args['error_type'] == expected_message 