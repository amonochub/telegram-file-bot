import os

import structlog

import asyncio

from app.services.celery_app import celery_app
from app.services.reporter import build_report, validate_doc
from app.utils.telegram_utils import escape_markdown

log = structlog.get_logger(__name__)


@celery_app.task
def validate_task(file_path: str, user_id: int, chat_id: int, bot_token: str):
    """Celery-задача: валидирует документ и отправляет отчёт пользователю."""

    async def _run() -> None:
        from aiogram import Bot

        bot = Bot(bot_token, parse_mode="HTML")
        try:
            misses, patched = validate_doc(file_path)

            if not misses:
                txt = "✅ Проверка завершена, расхождений нет!"
                await bot.send_message(chat_id, txt)
            else:
                report = build_report(misses)
                await bot.send_message(chat_id, escape_markdown(report), parse_mode="Markdown")

            from aiogram.types import FSInputFile

            await bot.send_document(chat_id, FSInputFile(patched), caption="Файл с подсветкой ⬆️")
            os.remove(file_path)
            os.remove(patched)
            log.info("validate_task_success", file_path=file_path, user_id=user_id)
        except Exception as e:  # noqa: BLE001
            log.error("validate_task_error", file_path=file_path, user_id=user_id, error=str(e))

    # Выполняем асинхронную часть в отдельном event loop
    asyncio.run(_run())
