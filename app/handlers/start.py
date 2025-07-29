from aiogram import F, Router
from aiogram.types import Message
from aiogram.fsm.context import FSMContext

from app.constants.messages import MAIN_MENU_WELCOME
from app.keyboards.menu import main_menu

router = Router()

@router.message(F.text == "/start")
async def cmd_start(msg: Message, state: FSMContext) -> None:
    """
    Обработчик команды /start
    Приветствует пользователя и показывает главное меню
    
    Args:
        msg: Сообщение от пользователя
        state: Контекст конечного автомата
    """
    await state.clear()
    await msg.answer(MAIN_MENU_WELCOME, reply_markup=main_menu(), parse_mode="HTML")
