"""
Обработчики для распознавания PDF (OCR)
"""

import structlog
from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.constants.messages import OCR_MENU_TEXT, OCR_INSTRUCTIONS, LOG_OCR_MENU_TRIGGERED

router = Router()
log = structlog.get_logger()


@router.message(F.text == OCR_MENU_TEXT)
async def ocr_menu(message: Message, state: FSMContext) -> None:
    """
    Обработчик кнопки "🧾 Распознать PDF"

    Args:
        message: Сообщение от пользователя
        state: Контекст конечного автомата
    """
    log.info(LOG_OCR_MENU_TRIGGERED, text=message.text, user_id=message.from_user.id)
    await state.clear()

    # Устанавливаем режим OCR
    await state.update_data(ocr_mode=True)

    await message.answer(
        OCR_INSTRUCTIONS + "\n\n"
        "💡 <b>Что происходит при OCR:</b>\n"
        "• Извлекается текст из изображений в PDF\n"
        "• Создается новый PDF с возможностью поиска\n"
        "• Вы получаете предварительный просмотр текста\n\n"
        "📋 <b>Поддерживаемые языки:</b> Русский, Английский\n"
        "⏱️ <b>Время обработки:</b> 10-30 секунд\n\n"
        "Отправьте PDF документ для начала обработки! 📄",
        parse_mode="HTML",
    )


@router.message(F.document)
async def handle_ocr_document(message: Message, state: FSMContext):
    """
    Обработчик PDF документов для OCR

    Args:
        message: Сообщение с документом
        state: Контекст конечного автомата
    """
    log.info("ocr_document_handler_called", user_id=message.from_user.id, filename=message.document.file_name)

    data = await state.get_data()
    log.info("ocr_state_data", data=data)

    # Проверяем, что мы в режиме OCR
    if not data.get("ocr_mode"):
        log.info("ocr_mode_not_active")
        return  # Пропускаем, если не в режиме OCR

    log.info("ocr_mode_active, processing document")

    doc = message.document

    # Проверяем, что это PDF
    if not doc.file_name.lower().endswith(".pdf"):
        from app.keyboards.menu import main_menu

        await message.answer(
            "❌ <b>Неверный формат файла!</b>\n\n"
            "Для OCR поддерживается только <b>PDF формат</b>.\n\n"
            "📋 <b>Что можно сделать:</b>\n"
            "• Конвертируйте файл в PDF и попробуйте снова\n"
            "• Используйте другие форматы для загрузки файлов\n\n"
            "Отправьте PDF документ для распознавания! 📄",
            parse_mode="HTML",
            reply_markup=main_menu(),
        )
        await state.update_data(ocr_mode=False)
        return

    # Отправляем сообщение о начале обработки
    processing_msg = await message.answer("🔄 Обрабатываю PDF документ...")

    try:
        # Скачиваем файл во временную директорию
        file_info = await message.bot.get_file(doc.file_id)
        import tempfile
        import os
        from pathlib import Path

        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            temp_path = Path(tmp.name)

        await message.bot.download_file(file_info.file_path, str(temp_path))

        # Выполняем OCR
        try:
            from app.services.ocr_service import perform_ocr

            pdf_path, full_text = await perform_ocr(temp_path)

            # Отправляем searchable-PDF
            from aiogram.types import FSInputFile

            await message.answer_document(
                FSInputFile(pdf_path),
                caption=f"✅ OCR завершен!\n\n"
                f"📄 Исходный файл: {doc.file_name}\n"
                f"🔍 PDF теперь содержит распознанный текст",
            )

            # Показываем первые строки распознанного текста
            preview = "\n".join(full_text.splitlines()[:10]) or "– текст не распознан –"
            await message.answer(f"🔍 <b>Preview OCR-текста (10 строк)</b>\n<pre>{preview}</pre>", parse_mode="HTML")

            # Удаляем временные файлы
            if pdf_path.exists():
                os.unlink(pdf_path)

        except Exception as e:
            log.error("ocr_processing_failed", error=str(e))
            await processing_msg.edit_text(f"❌ Ошибка при обработке PDF: {str(e)}")
        finally:
            # Удаляем временный PDF файл
            if temp_path.exists():
                os.unlink(temp_path)

    except Exception as e:
        log.error("ocr_download_failed", error=str(e))
        await processing_msg.edit_text(f"❌ Ошибка при скачивании файла: {str(e)}")

    # Сбрасываем режим OCR
    await state.update_data(ocr_mode=False)
