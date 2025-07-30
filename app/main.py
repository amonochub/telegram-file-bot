import asyncio
import logging
import os

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from app.config import settings
from app.logging_setup import setup_logging
from app.routers import main_router

# === регистрация роутеров ===
# Роутеры автоматически регистрируются через app.routers.main_router


async def main():
    setup_logging(settings.log_level)
    logger = logging.getLogger(__name__)
    logger.info("🚀 Запуск Telegram File Bot...")

    if not settings.bot_token:
        logger.error("❌ BOT_TOKEN не установлен")
        return

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

    bot = Bot(
        token=settings.bot_token,
        # Убираем parse_mode чтобы избежать ошибок парсинга Markdown
    )
    dp = Dispatcher()
    dp.include_router(main_router)

    # Создаем временную директорию
    os.makedirs("temp", exist_ok=True)

    logger.info("✅ Бот запущен и готов к работе")
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()
        logger.info("🛑 Бот остановлен")


if __name__ == "__main__":
    asyncio.run(main())
