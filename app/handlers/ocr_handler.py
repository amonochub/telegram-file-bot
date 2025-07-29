import os
import tempfile

import structlog
from aiogram import F, Router
from aiogram.types import Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import FSInputFile

from app.config import settings
from app.services.ocr_service import OCRService
from app.services.yandex_disk_service import YandexDiskService
from app.keyboards.menu import main_menu

router = Router()
logger = structlog.get_logger()

yandex_service = YandexDiskService(settings.yandex_disk_token)
ocr_service = OCRService(["rus", "eng"])


@router.message(F.document)
async def handle_pdf_document(message: Message):
    if not message.document.file_name.lower().endswith(".pdf"):
        await message.reply("⬆️ Для загрузки файлов используйте меню /upload")
        return
    logger.info(
        "pdf_document_received",
        user_id=message.from_user.id,
        file_name=message.document.file_name,
        file_size=message.document.file_size,
    )
    if message.document.file_size > settings.max_file_size:
        await message.reply("❌ PDF файл слишком большой. Максимальный размер: 100 МБ")
        return
    try:
        processing_msg = await message.reply(
            "📄 PDF получен! Выберите действие:",
            reply_markup=create_pdf_action_keyboard(),
        )
        file_info = {
            "file_id": message.document.file_id,
            "file_name": message.document.file_name,
            "file_size": message.document.file_size,
            "user_id": message.from_user.id,
            "message_id": processing_msg.message_id,
        }
        if not hasattr(handle_pdf_document, "temp_files"):  # type: ignore[attr-defined]
            handle_pdf_document.temp_files = {}  # type: ignore[attr-defined]
        handle_pdf_document.temp_files[  # type: ignore[attr-defined]
            f"{message.from_user.id}_{message.document.file_id}"
        ] = file_info
    except Exception as e:
        logger.error("Error handling PDF document", error=str(e))
        await message.reply(f"❌ Ошибка обработки PDF: {e}")


# --- объявляем атрибут для mypy после определения функции ---
from typing import Any, Dict

handle_pdf_document.temp_files: Dict[str, Dict[str, Any]] = {}  # type: ignore[attr-defined]


def create_pdf_action_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="🔍 Извлечь текст (OCR)", callback_data="pdf_ocr")
    builder.button(text="📤 Просто загрузить", callback_data="pdf_upload")
    builder.adjust(1)
    return builder.as_markup()


@router.callback_query(F.data == "pdf_ocr")
async def process_pdf_ocr(callback_query):
    user_id = callback_query.from_user.id
    file_key = None
    for key in handle_pdf_document.temp_files.keys():
        if key.startswith(f"{user_id}_"):
            file_key = key
            break
    if not file_key:
        await callback_query.message.edit_text("❌ Файл не найден. Попробуйте загрузить заново.")
        return
    file_info = handle_pdf_document.temp_files[file_key]
    try:
        await callback_query.message.edit_text("⏳ Обрабатываю PDF с помощью OCR...")
        file_telegram_info = await callback_query.bot.get_file(file_info["file_id"])
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_input:
            temp_input_path = temp_input.name
        with tempfile.NamedTemporaryFile(delete=False, suffix="_ocr.pdf") as temp_output:
            temp_output_path = temp_output.name
        await callback_query.bot.download_file(file_telegram_info.file_path, temp_input_path)
        ocr_result = await ocr_service.process_pdf_with_ocr(temp_input_path, temp_output_path)
        if ocr_result["success"]:
            ocr_filename = file_info["file_name"].replace(".pdf", "_ocr.pdf")
            remote_dir = f"{settings.upload_dir}/{user_id}/ocr_documents"

            # формируем полный текст
            full_text = "\n".join(ocr_result["text"])

            # оптимизируем PDF
            with tempfile.NamedTemporaryFile(delete=False, suffix="_opt.pdf") as tmp_opt:
                opt_path = tmp_opt.name
            ocr_service.optimize_pdf(temp_output_path, opt_path)

            # сохраняем TXT и DOCX

            # PDF (optimized)
            pdf_remote = f"{remote_dir}/{ocr_filename}"
            uploaded_path = await yandex_service.upload_file(opt_path, pdf_remote)

            # TXT
            with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as tmp_txt:
                txt_path = tmp_txt.name
            ocr_service.save_txt(full_text, txt_path)
            txt_remote = pdf_remote.replace(".pdf", ".txt")
            txt_url = await yandex_service.upload_file(txt_path, txt_remote)

            # DOCX
            with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as tmp_docx:
                tmp_docx_path = tmp_docx.name
            ocr_service.text_to_docx(full_text, tmp_docx_path)
            await callback_query.message.answer_document(
                FSInputFile(tmp_docx_path, filename=ocr_filename.replace(".pdf", ".docx"))
            )

            # --- формируем краткое резюме ---
            text_preview = full_text[:1000] + ("..." if len(full_text) > 1000 else "")

            from app.services.ocr import detect_language  # перевод при англ.

            lang = detect_language(full_text)
            translated = ""
            if lang == "en" and settings.gemini_api_key:
                try:
                    import asyncio
                    import functools
                    import google.generativeai as genai

                    genai.configure(api_key=settings.gemini_api_key)

                    async def _translate() -> str:
                        model = genai.GenerativeModel("gemini-pro")
                        prompt = (
                            "Переведи следующий текст на русский язык, сохраняя структуру. "
                            "Верни только перевод без пояснений.\n\n" + full_text[:4000]
                        )
                        response = model.generate_content(prompt)
                        return response.text.strip()

                    translated = await asyncio.get_event_loop().run_in_executor(None, _translate)
                except Exception as e:  # pragma: no cover
                    logger.warning("translate_failed", err=str(e))

            result_text = (
                f"✅ OCR обработка завершена!\n\n"
                f"📁 Файл сохранён: {uploaded_path}\n"
                f"📄 Страниц обработано: {ocr_result['pages_count']}\n"
                f"🌐 Языки: {', '.join(ocr_result['languages'])}\n\n"
                f"📝 Превью текста:\n{text_preview}\n\n"
                + (f"🌍 Перевод фрагмента:\n{translated}" if translated else "")
            )

            builder = InlineKeyboardBuilder()
            if uploaded_path:
                builder.button(text="📥 OCR-PDF", callback_data=f"download_ocr:{uploaded_path}")
            if txt_url:
                builder.button(text="📄 TXT", callback_data=f"download_txt:{txt_url}")
            builder.button(text="📋 Весь текст", callback_data=f"show_full_text:{file_key}")
            builder.adjust(1)

            await callback_query.message.edit_text(result_text, reply_markup=builder.as_markup(), parse_mode="Markdown")
            await callback_query.message.answer("✅ Текст успешно извлечён!", reply_markup=main_menu())
        else:
            await callback_query.message.edit_text("❌ Ошибка загрузки обработанного файла")
            await callback_query.message.answer(f"❌ Ошибка OCR: {ocr_result['error']}", reply_markup=main_menu())
        for temp_path in [temp_input_path, temp_output_path]:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
        handle_pdf_document.temp_files[file_key]["ocr_result"] = ocr_result
    except Exception as e:
        logger.error("Error processing PDF OCR", error=str(e))
        await callback_query.message.edit_text(f"❌ Ошибка OCR обработки: {e}")
        await callback_query.message.answer(f"❌ Ошибка OCR: {e}", reply_markup=main_menu())
    await callback_query.answer()


@router.callback_query(F.data == "pdf_upload")
async def process_pdf_upload(callback_query):
    user_id = callback_query.from_user.id
    file_key = None
    for key in handle_pdf_document.temp_files.keys():
        if key.startswith(f"{user_id}_"):
            file_key = key
            break
    if not file_key:
        await callback_query.message.edit_text("❌ Файл не найден")
        return
    file_info = handle_pdf_document.temp_files[file_key]
    try:
        await callback_query.message.edit_text("⏳ Загружаю PDF на Яндекс.Диск...")
        file_telegram_info = await callback_query.bot.get_file(file_info["file_id"])
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
            temp_path = temp_file.name
        await callback_query.bot.download_file(file_telegram_info.file_path, temp_path)
        remote_path = f"{settings.upload_dir}/{user_id}/documents/{file_info['file_name']}"
        uploaded_path = await yandex_service.upload_file(temp_path, remote_path)
        if uploaded_path:
            await callback_query.message.edit_text(
                f"✅ PDF загружен на Яндекс.Диск!\n"
                f"📁 Путь: {uploaded_path}\n"
                f"📄 Размер: {yandex_service.format_file_size(file_info['file_size'])}"
            )
        else:
            await callback_query.message.edit_text("❌ Ошибка загрузки файла")
        os.unlink(temp_path)
    except Exception as e:
        await callback_query.message.edit_text(f"❌ Ошибка: {e}")
    await callback_query.answer()
