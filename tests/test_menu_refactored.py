"""
Тесты для рефакторенной модульной структуры меню
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from aiogram.types import Message
from aiogram.fsm.context import FSMContext

from app.handlers.menu.overview import browse_menu
from app.handlers.menu.upload import upload_menu
from app.handlers.menu.help import help_button
from app.constants.messages import OVERVIEW_MENU_TEXT, UPLOAD_MENU_TEXT, UPLOAD_INSTRUCTIONS, HELP_MENU_TEXT, HELP_TEXT


@pytest.fixture
def mock_message():
    """Фикстура для создания мок-сообщения"""
    message = AsyncMock(spec=Message)
    message.from_user.id = 123456
    message.answer = AsyncMock()
    return message


@pytest.fixture
def mock_state():
    """Фикстура для создания мок-состояния"""
    state = AsyncMock(spec=FSMContext)
    state.clear = AsyncMock()
    return state


class TestOverviewMenu:
    """Тесты для обработчика обзора папок"""

    @pytest.mark.asyncio
    async def test_browse_menu_clears_state(self, mock_message, mock_state):
        """Тест очистки состояния при нажатии кнопки обзора папок"""
        mock_message.text = OVERVIEW_MENU_TEXT

        await browse_menu(mock_message, mock_state)

        mock_state.clear.assert_called_once()

    @pytest.mark.asyncio
    async def test_browse_menu_calls_files_command(self, mock_message, mock_state):
        """Тест вызова files_command при нажатии кнопки обзора папок"""
        mock_message.text = OVERVIEW_MENU_TEXT

        # Мокаем импорт и функцию
        with pytest.MonkeyPatch().context() as m:
            mock_files_command = AsyncMock()
            m.setattr("app.handlers.menu.overview.files_command", mock_files_command)

            await browse_menu(mock_message, mock_state)

            mock_files_command.assert_called_once_with(mock_message)


class TestUploadMenu:
    """Тесты для обработчика загрузки файлов"""

    @pytest.mark.asyncio
    async def test_upload_menu_clears_state(self, mock_message, mock_state):
        """Тест очистки состояния при нажатии кнопки загрузки"""
        mock_message.text = UPLOAD_MENU_TEXT

        await upload_menu(mock_message, mock_state)

        mock_state.clear.assert_called_once()

    @pytest.mark.asyncio
    async def test_upload_menu_sends_instructions(self, mock_message, mock_state):
        """Тест отправки инструкций при нажатии кнопки загрузки"""
        mock_message.text = UPLOAD_MENU_TEXT

        await upload_menu(mock_message, mock_state)

        mock_message.answer.assert_called_once_with(UPLOAD_INSTRUCTIONS)


class TestHelpMenu:
    """Тесты для обработчика помощи"""

    @pytest.mark.asyncio
    async def test_help_button_clears_state(self, mock_message, mock_state):
        """Тест очистки состояния при нажатии кнопки помощи"""
        mock_message.text = HELP_MENU_TEXT

        await help_button(mock_message, mock_state)

        mock_state.clear.assert_called_once()

    @pytest.mark.asyncio
    async def test_help_button_sends_help_text(self, mock_message, mock_state):
        """Тест отправки текста помощи при нажатии кнопки помощи"""
        mock_message.text = HELP_MENU_TEXT

        await help_button(mock_message, mock_state)

        mock_message.answer.assert_called_once()
        call_args = mock_message.answer.call_args
        assert call_args[0][0] == HELP_TEXT
        assert call_args[1]["parse_mode"] == "Markdown"


class TestConstants:
    """Тесты для констант сообщений"""

    def test_overview_menu_text_constant(self):
        """Тест константы текста кнопки обзора папок"""
        assert OVERVIEW_MENU_TEXT == "📂 Обзор папок"

    def test_upload_menu_text_constant(self):
        """Тест константы текста кнопки загрузки"""
        assert UPLOAD_MENU_TEXT == "📤 Загрузка файлов"

    def test_help_menu_text_constant(self):
        """Тест константы текста кнопки помощи"""
        assert HELP_MENU_TEXT == "ℹ️ Помощь"

    def test_upload_instructions_constant(self):
        """Тест константы инструкций загрузки"""
        assert "Отправьте файл или архив" in UPLOAD_INSTRUCTIONS

    def test_help_text_constant(self):
        """Тест константы текста помощи"""
        assert "Помощь по боту" in HELP_TEXT
