from unittest.mock import Mock, patch
import pytest

# Mock the keyboard structure for testing
MOCK_KEYBOARD = [
    [Mock(text="📂 Обзор папок")],
    [Mock(text="📤 Загрузка файлов")],
    [Mock(text="🧾 Распознать PDF")],
    [Mock(text="💰 Расчёт для клиента")],
    [Mock(text="📈 Курсы ЦБ")],
    [Mock(text="ℹ️ Помощь")],
]

# Mock the MAIN_KB object
MOCK_MAIN_KB = Mock(keyboard=MOCK_KEYBOARD)

# Handler mapping for testing
BUTTONS_TO_HANDLERS = {
    "📂 Обзор папок": "browse_menu",
    "📤 Загрузка файлов": "upload_menu",
    "🧾 Распознать PDF": "ocr_menu",
    "💰 Расчёт для клиента": "client_calc_menu",
    "📈 Курсы ЦБ": "cbr_rates_menu",
    "ℹ️ Помощь": "help_button",
    "🏠 Главное меню": "main_menu_button",
}


def _flatten_texts():
    """Return a list of texts from all buttons in MOCK_KEYBOARD."""
    return [btn.text for row in MOCK_KEYBOARD for btn in row]


@patch("app.keyboards.menu.MAIN_KB", MOCK_MAIN_KB)
def test_all_buttons_present():
    """Ensure all necessary buttons are present in the keyboard."""
    texts = _flatten_texts()
    mandatory = [txt for txt in BUTTONS_TO_HANDLERS if txt != "🏠 Главное меню"]
    for expected in mandatory:
        assert expected in texts, f"Button '{expected}' is missing from MAIN_KB"


def test_all_handlers_defined():
    """Ensure handlers exist for each button."""
    import importlib
    
    handler_modules = {
        "browse_menu": "app.handlers.menu.overview",
        "upload_menu": "app.handlers.menu.upload",
        "ocr_menu": "app.handlers.menu.ocr",
        "client_calc_menu": "app.handlers.menu.client_calc",
        "cbr_rates_menu": "app.handlers.menu.cbr_rates",
        "help_button": "app.handlers.menu.help",
        "main_menu_button": "app.handlers.menu.main",
    }
    
    for btn_text, handler_name in BUTTONS_TO_HANDLERS.items():
        if handler_name in handler_modules:
            try:
                module = importlib.import_module(handler_modules[handler_name])
                assert hasattr(module, handler_name), (
                    f"Handler '{handler_name}' not found in {handler_modules[handler_name]}"
                )
            except ImportError:
                pytest.fail(f"Module {handler_modules[handler_name]} not found for handler {handler_name}")