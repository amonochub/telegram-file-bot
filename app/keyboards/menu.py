from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

MAIN_KB = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📂 Обзор папок")],
        [KeyboardButton(text="📤 Загрузка файлов")],
        [KeyboardButton(text="🧾 Распознать PDF")],
        [KeyboardButton(text="💰 Расчёт для клиента")],
        [KeyboardButton(text="📈 Курсы ЦБ")],
        [KeyboardButton(text="ℹ️ Помощь")],
    ],
    resize_keyboard=True,
    persistent=True,
)


def main_menu() -> ReplyKeyboardMarkup:
    return MAIN_KB


def with_back(*rows: list[str]) -> ReplyKeyboardMarkup:
    """
    Вернуть новую клавиатуру = переданные строки + «🏠 Главное меню».
    """
    buttons = [[KeyboardButton(text=txt) for txt in row] for row in rows]
    buttons.append([KeyboardButton(text="🏠 Главное меню")])
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)
