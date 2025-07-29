#!/usr/bin/env python3
"""
Демо-режим для тестирования Telegram File Bot
Запускает бота в режиме эмуляции без реального подключения к Telegram
"""

import asyncio
import logging
import os
from unittest.mock import Mock, AsyncMock

from app.config import settings
from app.logging_setup import setup_logging
from app.routers import main_router

# === регистрация роутеров ===
import app.handlers.menu.main
import app.handlers.menu.upload
import app.handlers.menu.overview
import app.handlers.menu.ai_verification
import app.handlers.menu.ocr
import app.handlers.menu.client_calc
import app.handlers.menu.cbr_rates


async def demo_main():
    """Демо-режим для тестирования"""
    setup_logging(settings.log_level)
    logger = logging.getLogger(__name__)
    logger.info("🚀 Запуск Telegram File Bot в ДЕМО-режиме...")
    
    # Создаем временную директорию
    os.makedirs("temp", exist_ok=True)
    
    # Проверяем конфигурацию ИИ
    settings.validate_ai_config()
    
    # Проверяем подключение к Яндекс.Диску
    if settings.yandex_disk_token:
        try:
            from app.services.yandex_disk_service import YandexDiskService
            yandex_service = YandexDiskService(settings.yandex_disk_token)
            connected = await yandex_service.check_connection()
            if connected:
                logger.info("✅ Подключение к Яндекс.Диску успешно")
            else:
                logger.warning("⚠️ Не удалось подключиться к Яндекс.Диску - функции Яндекс.Диска отключены")
        except Exception as e:
            logger.warning(f"⚠️ Яндекс.Диск недоступен: {e} - функции Яндекс.Диска отключены")
    else:
        logger.warning("⚠️ YANDEX_DISK_TOKEN не установлен - функции Яндекс.Диска отключены")
    
    # Создаем мок-объекты для демо-режима
    mock_bot = Mock()
    mock_bot.token = "demo_token"
    mock_bot.session = AsyncMock()
    mock_bot.session.close = AsyncMock()
    
    mock_dispatcher = Mock()
    mock_dispatcher.include_router = Mock()
    mock_dispatcher.start_polling = AsyncMock()
    
    logger.info("✅ Бот запущен в ДЕМО-режиме")
    logger.info("📝 Для реального запуска установите BOT_TOKEN и ALLOWED_USER_ID")
    logger.info("💡 Пример: export BOT_TOKEN='your_real_token' && export ALLOWED_USER_ID='your_id'")
    
    try:
        # Имитируем работу бота
        await asyncio.sleep(5)
        logger.info("🛑 Демо-режим завершен")
    finally:
        await mock_bot.session.close()
        logger.info("🛑 Бот остановлен")


if __name__ == "__main__":
    # Устанавливаем демо-переменные окружения
    os.environ.setdefault("BOT_TOKEN", "demo_token")
    os.environ.setdefault("ALLOWED_USER_ID", "123456789")
    os.environ.setdefault("LOG_LEVEL", "INFO")
    os.environ.setdefault("REDIS_URL", "redis://localhost:6379")
    
    asyncio.run(demo_main()) 