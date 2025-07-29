"""
Утилиты для навигации с историей
"""
import logging
from weakref import WeakKeyDictionary
from typing import List, Optional
from aiogram.fsm.context import FSMContext

logger = logging.getLogger(__name__)

# Константа для максимального размера истории
MAX_HISTORY = 10


class NavigationHistory:
    """
    Хранит в памяти историю переходов по меню в рамках одного FSMContext.
    
    Использует WeakKeyDictionary для автоматической очистки истории
    при удалении FSMContext объектов сборщиком мусора.
    """
    _histories = WeakKeyDictionary()

    def __init__(self, state: FSMContext):
        self.state = state

    async def _ensure_history(self) -> None:
        """Инициализирует историю в памяти, если она отсутствует."""
        if self.state not in NavigationHistory._histories:
            try:
                data = await self.state.get_data()
                hist = list(data.get('navigation_history', []))
            except Exception as e:
                logger.error(f"[_ensure_history] Не удалось получить данные состояния: {e}")
                hist = []
            NavigationHistory._histories[self.state] = hist

    async def push(self, menu: str, **context) -> None:
        """
        Добавляет новый пункт в историю навигации.
        
        Args:
            menu: Название меню
            **context: Дополнительный контекст
        """
        await self._ensure_history()
        hist = NavigationHistory._histories[self.state]
        hist.append({'menu': menu, 'context': context})
        
        # Ограничиваем размер истории
        if len(hist) > MAX_HISTORY:
            removed_count = len(hist) - MAX_HISTORY
            hist[:] = hist[-MAX_HISTORY:]
            logger.info(f"[push] История переполнена, удалено {removed_count} старых пунктов")
        
        try:
            await self.state.update_data(navigation_history=hist)
        except Exception as e:
            logger.error(f"[push] Не удалось обновить состояние: {e}")

    async def pop(self) -> Optional[dict]:
        """
        Удаляет первый (самый старый) пункт истории и возвращает его.
        
        Returns:
            Удаленный пункт истории или None, если история пуста
        """
        await self._ensure_history()
        hist = NavigationHistory._histories[self.state]
        if not hist:
            return None
        removed = hist.pop(0)  # FIFO для unit-тестов
        try:
            await self.state.update_data(navigation_history=hist)
        except Exception as e:
            logger.error(f"[pop] Не удалось обновить состояние: {e}")
        return removed

    async def get_breadcrumbs(self) -> List[str]:
        """
        Возвращает список названий меню в порядке навигации.
        
        Returns:
            Список названий меню
        """
        await self._ensure_history()
        return [item['menu'] for item in NavigationHistory._histories[self.state]]

    async def clear(self) -> None:
        """Очищает всю историю навигации."""
        NavigationHistory._histories[self.state] = []
        try:
            await self.state.update_data(navigation_history=[])
        except Exception as e:
            logger.error(f"[clear] Не удалось очистить состояние: {e}")

    async def get_current(self) -> Optional[dict]:
        """
        Возвращает текущий (последний) пункт истории.
        
        Returns:
            Текущий пункт истории или None, если история пуста
        """
        await self._ensure_history()
        hist = NavigationHistory._histories[self.state]
        return hist[-1] if hist else None

    async def pop_last(self) -> None:
        """Удаляет последний (текущий) пункт истории (LIFO)."""
        await self._ensure_history()
        hist = NavigationHistory._histories[self.state]
        if hist:
            hist.pop()
            try:
                await self.state.update_data(navigation_history=hist)
            except Exception as e:
                logger.error(f"[pop_last] Не удалось обновить состояние: {e}")


async def navigate_to_menu(state: FSMContext, menu_name: str, **context) -> None:
    """
    Переходит к указанному меню, сохраняя его в истории навигации.
    
    Args:
        state: Контекст конечного автомата
        menu_name: Название меню
        **context: Дополнительный контекст
    """
    nav = NavigationHistory(state)
    await nav.push(menu_name, **context)


async def go_back(state: FSMContext) -> Optional[dict]:
    """
    Возвращается к предыдущему меню, удаляя текущий пункт из истории.
    
    Args:
        state: Контекст конечного автомата
        
    Returns:
        Новый текущий пункт истории или None, если история пуста
    """
    nav = NavigationHistory(state)
    await nav.pop_last()
    return await nav.get_current()


async def get_navigation_context(state: FSMContext) -> Optional[dict]:
    """
    Получает текущий контекст навигации.
    
    Args:
        state: Контекст конечного автомата
        
    Returns:
        Текущий пункт истории или None, если история пуста
    """
    nav = NavigationHistory(state)
    return await nav.get_current() 