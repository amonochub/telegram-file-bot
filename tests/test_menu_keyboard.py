from app.keyboards.menu import MAIN_KB
import importlib

menu_module = importlib.import_module("app.handlers.menu")

BUTTONS_TO_HANDLERS = {
    "📂 Обзор папок": "browse_menu",
    "📤 Загрузка файлов": "upload_menu",
    "🤖 Проверка ИИ": "ai_verification_menu",
    "🧾 Распознать PDF": "ocr_menu",
    "💰 Расчёт для клиента": "client_calc_menu",
    "📈 Курсы ЦБ": "cbr_rates_menu",
    # Кнопка «🏠 Главное меню» появляется динамически через util.with_back(), проверяем только наличие хендлера
    "🏠 Главное меню": "main_menu_button",
}


def _flatten_texts():
    """Вернуть список текстов всех кнопок из MAIN_KB."""
    return [btn.text for row in MAIN_KB.keyboard for btn in row]


def test_all_buttons_present():
    """Убеждаемся, что все необходимые кнопки присутствуют в клавиатуре."""
    texts = _flatten_texts()
    mandatory = [txt for txt in BUTTONS_TO_HANDLERS if txt != "🏠 Главное меню"]
    for expected in mandatory:
        assert expected in texts, f"Кнопка '{expected}' отсутствует в MAIN_KB"


def test_all_handlers_defined():
    """Проверяем, что для каждой кнопки объявлен соответствующий хендлер в app.handlers.menu."""
    for text, handler_name in BUTTONS_TO_HANDLERS.items():
        assert hasattr(menu_module, handler_name), f"Для кнопки '{text}' нет хендлера '{handler_name}'"
        handler = getattr(menu_module, handler_name)
        # Проверяем, что это корутина (async def)
        assert callable(handler) and hasattr(handler, "__code__"), (
            f"'{handler_name}' не является вызываемой функцией"
        ) 