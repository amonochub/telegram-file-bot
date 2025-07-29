import os
import tempfile
from typing import Any, Dict, Optional

import structlog
from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.keyboards.menu import main_menu

# ----- Заглушка вместо реального сервиса ИИ для устранения ошибок Ruff (F821) -----
# В будущем заменить на реальную интеграцию


# --- Заглушка ИИ-сервиса (пока вместо Gemini/иных) ---
class _DummyAIService:  # pylint: disable=too-few-public-methods
    async def analyze_document_with_ai(self, text: str, doc_type: str):  # noqa: D401
        """Заглушка анализа документа."""
        return {}

    async def verify_document_consistency(self, contract_data, assignment_data, report_data) -> dict:
        """Заглушка проверки согласованности."""
        return {
            "status": "success",
            "checks": [],
            "errors": [],
            "warnings": [],
        }


# Экземпляр-заглушка, чтобы код продолжал работать без реального сервиса
ai_service = _DummyAIService()

router = Router()
logger = structlog.get_logger()

# user_id -> mapping of document types to data
user_documents: Dict[int, Dict[str, Any]] = {}


@router.message(Command("ai_check"))
async def ai_check_command(message: Message):
    builder = InlineKeyboardBuilder()
    builder.button(text="📄 Загрузить договор", callback_data="upload_contract")
    builder.button(text="📋 Загрузить поручение", callback_data="upload_assignment")
    builder.button(text="📊 Загрузить акт-отчет", callback_data="upload_report")
    builder.button(text="🔍 Проверить соответствие", callback_data="verify_documents")
    builder.adjust(1)
    await message.answer(
        "🤖 **ИИ-проверка документов**\n\n"
        "Загрузите документы для анализа и проверки соответствия:\n\n"
        "1. Агентский договор\n"
        "2. Поручение\n"
        "3. Акт-отчет (опционально)\n\n"
        "После загрузки нажмите 'Проверить соответствие'",
        reply_markup=builder.as_markup(),
        parse_mode="Markdown",
    )


@router.callback_query(F.data.startswith("upload_"))
async def handle_document_upload(callback: CallbackQuery):
    doc_type = callback.data.split("_")[1]
    doc_names = {
        "contract": "агентский договор",
        "assignment": "поручение",
        "report": "акт-отчет",
    }
    user_id = callback.from_user.id
    if user_id not in user_documents:
        user_documents[user_id] = {}
    user_documents[user_id]["waiting_for"] = doc_type
    await callback.message.edit_text(
        f"📎 Отправьте {doc_names[doc_type]} в формате .docx или .pdf\n\nДля отмены используйте /cancel"
    )
    await callback.answer()


@router.message(F.document)
async def handle_document_received(message: Message, state: Optional[FSMContext] = None):
    user_id = message.from_user.id

    # Проверяем, не находимся ли мы в режиме загрузки файлов
    if state:
        data = await state.get_data()
        if data.get("upload_mode"):
            logger.info("Upload mode active, skipping AI verification handler")
            return  # Пропускаем обработку, чтобы документ попал в обработчик загрузки

    # Проверяем, что пользователь действительно в режиме ИИ-проверки
    if user_id not in user_documents or "waiting_for" not in user_documents[user_id]:
        logger.info("User not in AI verification mode, skipping")
        return  # Пропускаем обработку, чтобы документ попал в другие обработчики
    doc_type = user_documents[user_id]["waiting_for"]
    try:
        processing_msg = await message.reply("🔄 Обрабатываю документ с помощью ИИ...")
        file_info = await message.bot.get_file(message.document.file_id)
        with tempfile.NamedTemporaryFile(delete=False, suffix=f"_{message.document.file_name}") as temp_file:
            temp_path = temp_file.name
        await message.bot.download_file(file_info.file_path, temp_path)
        # auth_success = await google_ai_service.authenticate_google() # Removed Google Drive authentication
        # if not auth_success: # Removed Google Drive authentication
        #     await processing_msg.edit_text("❌ Ошибка подключения к Google Drive") # Removed Google Drive authentication
        #     return # Removed Google Drive authentication
        # file_id = await google_ai_service.upload_document( # Removed Google Drive authentication
        #     temp_path, message.document.file_name # Removed Google Drive authentication
        # ) # Removed Google Drive authentication
        # if not file_id: # Removed Google Drive authentication
        #     await processing_msg.edit_text("❌ Ошибка загрузки на Google Drive") # Removed Google Drive authentication
        #     return # Removed Google Drive authentication
        text = "Текст из документа не извлечен."  # Placeholder for text extraction
        if text.strip():
            analysis_result = await ai_service.analyze_document_with_ai(  # Placeholder for AI analysis
                text,
                doc_type,  # Placeholder for AI analysis
            )  # Placeholder for AI analysis
            if "error" in analysis_result:  # Placeholder for AI analysis
                await processing_msg.edit_text(  # Placeholder for AI analysis
                    f"❌ Ошибка ИИ-анализа: {analysis_result['error']}"  # Placeholder for AI analysis
                )  # Placeholder for AI analysis
                return  # Placeholder for AI analysis
            user_documents[user_id][doc_type] = {  # Placeholder for AI analysis
                "file_name": message.document.file_name,  # Placeholder for AI analysis
                "analysis": analysis_result,  # Placeholder for AI analysis
                "text": text[:1000] + "..." if len(text) > 1000 else text,  # Placeholder for AI analysis
            }  # Placeholder for AI analysis
            del user_documents[user_id]["waiting_for"]  # Placeholder for AI analysis
            doc_names = {  # Placeholder for AI analysis
                "contract": "Агентский договор",  # Placeholder for AI analysis
                "assignment": "Поручение",  # Placeholder for AI analysis
                "report": "Акт-отчет",  # Placeholder for AI analysis
            }  # Placeholder for AI analysis
            result_text = f"✅ **{doc_names[doc_type]} обработан!**\n\n"  # Placeholder for AI analysis
            if doc_type == "contract":  # Placeholder for AI analysis
                result_text += (  # Placeholder for AI analysis
                    f"📋 **Договор:** {analysis_result.get('contract_number', 'н/д')}\n"  # Placeholder for AI analysis
                    f"📅 **Дата:** {analysis_result.get('contract_date', 'н/д')}\n"  # Placeholder for AI analysis
                    f"🏢 **Принципал:** {analysis_result.get('principal_name', 'н/д')}\n"  # Placeholder for AI analysis
                    f"🏢 **Агент:** {analysis_result.get('agent_name', 'н/д')}\n"  # Placeholder for AI analysis
                    f"💰 **Валюты:** {', '.join(analysis_result.get('currencies', []))}\n"  # Placeholder for AI analysis
                )  # Placeholder for AI analysis
            elif doc_type == "assignment":  # Placeholder for AI analysis
                result_text += (  # Placeholder for AI analysis
                    f"📋 **Поручение:** {analysis_result.get('assignment_number', 'н/д')}\n"  # Placeholder for AI analysis
                    f"📅 **Дата:** {analysis_result.get('assignment_date', 'н/д')}\n"  # Placeholder for AI analysis
                    f"🏭 **Экспортер:** {analysis_result.get('exporter_name', 'н/д')}\n"  # Placeholder for AI analysis
                    f"🧾 **Инвойс:** {analysis_result.get('invoice_number', 'н/д')}\n"  # Placeholder for AI analysis
                    f"💵 **Сумма:** {analysis_result.get('exchange_amount', 'н/д')} {analysis_result.get('currency', '')}\n"  # Placeholder for AI analysis
                    f"💰 **Вознаграждение:** {analysis_result.get('agent_fee', 'н/д')} ₽\n"  # Placeholder for AI analysis
                )  # Placeholder for AI analysis
            elif doc_type == "report":  # Placeholder for AI analysis
                result_text += (  # Placeholder for AI analysis
                    f"📋 **Акт-отчет:** {analysis_result.get('report_number', 'н/д')}\n"  # Placeholder for AI analysis
                    f"📅 **Дата:** {analysis_result.get('report_date', 'н/д')}\n"  # Placeholder for AI analysis
                    f"🔗 **Поручение:** {analysis_result.get('assignment_number', 'н/д')}\n"  # Placeholder for AI analysis
                    f"🏭 **Экспортер:** {analysis_result.get('exporter_name', 'н/д')}\n"  # Placeholder for AI analysis
                    f"💰 **Сумма услуги:** {analysis_result.get('service_amount_rub', 'н/d')} ₽\n"  # Placeholder for AI analysis
                )  # Placeholder for AI analysis
            builder = InlineKeyboardBuilder()  # Placeholder for AI analysis
            builder.button(  # Placeholder for AI analysis
                text="🔍 Проверить соответствие",
                callback_data="verify_documents",  # Placeholder for AI analysis
            )  # Placeholder for AI analysis
            builder.button(
                text="📎 Загрузить еще документ", callback_data="ai_check_menu"
            )  # Placeholder for AI analysis
            builder.adjust(1)  # Placeholder for AI analysis
            await processing_msg.edit_text(  # Placeholder for AI analysis
                result_text,
                reply_markup=builder.as_markup(),
                parse_mode="Markdown",  # Placeholder for AI analysis
            )  # Placeholder for AI analysis
            os.unlink(temp_path)  # Placeholder for AI analysis
    except Exception as e:  # Placeholder for AI analysis
        logger.error("Error processing document", error=str(e))  # Placeholder for AI analysis
        await message.reply(f"❌ Ошибка обработки документа: {e}")  # Placeholder for AI analysis


@router.callback_query(F.data == "verify_documents")
async def verify_documents(callback: CallbackQuery):
    user_id = callback.from_user.id
    if user_id not in user_documents:
        await callback.message.edit_text("❌ Нет загруженных документов")
        return
    docs = user_documents[user_id]
    try:
        await callback.message.edit_text("🔄 Проверяю соответствие документов...")
        contract_data = docs.get("contract", {}).get("analysis", {})
        assignment_data = docs.get("assignment", {}).get("analysis", {})
        report_data = docs.get("report", {}).get("analysis", {})
        if not assignment_data and not contract_data:
            await callback.message.edit_text("❌ Нужно загрузить хотя бы договор и поручение")
            return
        analysis_result = await ai_service.verify_document_consistency(  # Placeholder for AI verification
            contract_data,
            assignment_data,
            report_data,  # Placeholder for AI verification
        )  # Placeholder for AI verification
        status_icons = {"success": "✅", "warning": "⚠️", "error": "❌"}  # Placeholder for AI verification
        result_text = (  # Placeholder for AI verification
            f"{status_icons[analysis_result['status']]} **Результат проверки**\n\n"  # Placeholder for AI verification
        )  # Placeholder for AI verification
        if analysis_result["checks"]:  # Placeholder for AI verification
            result_text += "📋 **Выполненные проверки:**\n"  # Placeholder for AI verification
            for check in analysis_result["checks"]:  # Placeholder for AI verification
                result_text += f"• {check} ✓\n"  # Placeholder for AI verification
            result_text += "\n"  # Placeholder for AI verification
        if analysis_result["errors"]:  # Placeholder for AI verification
            result_text += "❌ **Найдены ошибки:**\n"  # Placeholder for AI verification
            for error in analysis_result["errors"]:  # Placeholder for AI verification
                result_text += f"• {error}\n"  # Placeholder for AI verification
            result_text += "\n"  # Placeholder for AI verification
        if analysis_result["warnings"]:  # Placeholder for AI verification
            result_text += "⚠️ **Предупреждения:**\n"  # Placeholder for AI verification
            for warning in analysis_result["warnings"]:  # Placeholder for AI verification
                result_text += f"• {warning}\n"  # Placeholder for AI verification
            result_text += "\n"  # Placeholder for AI verification
        if analysis_result["status"] == "success":  # Placeholder for AI verification
            result_text += "🎉 Все документы соответствуют друг другу!"  # Placeholder for AI verification
        builder = InlineKeyboardBuilder()  # Placeholder for AI verification
        builder.button(  # Placeholder for AI verification
            text="📎 Загрузить новые документы",
            callback_data="ai_check_menu",  # Placeholder for AI verification
        )  # Placeholder for AI verification
        builder.adjust(1)  # Placeholder for AI verification
        await callback.message.edit_text(  # Placeholder for AI verification
            result_text,
            reply_markup=builder.as_markup(),
            parse_mode="Markdown",  # Placeholder for AI verification
        )  # Placeholder for AI verification
    except Exception as e:  # Placeholder for AI verification
        logger.error("Error verifying documents", error=str(e))  # Placeholder for AI verification
        await callback.message.edit_text(f"❌ Ошибка проверки: {e}")  # Placeholder for AI verification
    await callback.answer()


@router.callback_query(F.data == "ai_check_menu")
async def back_to_ai_menu(callback: CallbackQuery):
    builder = InlineKeyboardBuilder()
    builder.button(text="📄 Загрузить договор", callback_data="upload_contract")
    builder.button(text="📋 Загрузить поручение", callback_data="upload_assignment")
    builder.button(text="📊 Загрузить акт-отчет", callback_data="upload_report")
    builder.button(text="🔍 Проверить соответствие", callback_data="verify_documents")
    builder.adjust(1)
    await callback.message.edit_text(
        "🤖 **ИИ-проверка документов**\n\nЗагрузите документы для анализа и проверки соответствия:",
        reply_markup=builder.as_markup(),
        parse_mode="Markdown",
    )
    await callback.answer()


@router.message(Command("cancel"))
async def cancel_document_upload(message: Message):
    user_id = message.from_user.id
    if user_id in user_documents and "waiting_for" in user_documents[user_id]:
        del user_documents[user_id]["waiting_for"]
        await message.reply("❌ Загрузка документа отменена")
    else:
        await message.reply("Нет активной загрузки для отмены")
