"""
Обработчики для загрузки файлов
"""

import structlog
from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
import os
import tempfile

from app.constants.messages import (
    UPLOAD_MENU_TEXT,
    UPLOAD_INSTRUCTIONS,
    LOG_UPLOAD_MENU_TRIGGERED,
)
from app.keyboards.menu import main_menu
from app.utils.file_router import determine_path
from app.config import settings, USER_FILES_DIR

router = Router()
log = structlog.get_logger()


@router.message(F.text == "📤 Загрузка файлов")
async def upload_menu(message: Message, state: FSMContext) -> None:
    """
    Обработчик кнопки "📤 Загрузка файлов"

    Args:
        message: Сообщение от пользователя
        state: Контекст конечного автомата
    """
    log.info(LOG_UPLOAD_MENU_TRIGGERED, text=message.text, user_id=message.from_user.id)
    # await state.clear()  # Удаляем сброс состояния, чтобы не терять выбранную папку
    # Устанавливаем режим загрузки
    await state.update_data(upload_mode=True)
    await message.answer(
        UPLOAD_INSTRUCTIONS
        + "\n\n<b>📝 Формат имени файла:</b>\n"
        + "<code>Принципал_Агент_вид документа_номер_дата</code>\n\n"
        + "<b>✅ Правильные примеры:</b>\n"
        + "• <code>Альфатрекс_Агрико_агентский договор_2_300525.docx</code>\n"
        + "• <code>Сбербанк_ИП Иванов_поручение_15_280725.pdf</code>\n"
        + "• <code>ВТБ_ООО Рога_акт-отчет_7_150124.docx</code>\n\n"
        + "<b>❌ Неправильные примеры:</b>\n"
        + "• <code>Договор.pdf</code> (неполное имя)\n"
        + "• <code>Альфатрекс@Агрико_договор_2_300525.docx</code> (спецсимволы)\n"
        + "• <code>Альфатрекс_Агрико_договор_2_30.05.25.docx</code> (точки в дате)\n\n"
        + "<b>💡 Советы:</b>\n"
        + "• Используйте только буквы, цифры, пробелы и подчёркивания\n"
        + "• Дата в формате ДДММГГ (например, 300525 = 30.05.2025)\n"
        + "• Номер документа - только цифры\n"
        + "• Не используйте спецсимволы и эмодзи!",
        parse_mode="HTML",
        reply_markup=main_menu(),
    )


@router.message(F.document)
async def handle_manual_upload(msg: Message, state: FSMContext):
    """
    Обработчик загрузки документов

    Args:
        msg: Сообщение с документом
        state: Контекст конечного автомата
    """
    log.info("handle_manual_upload invoked", user_id=msg.from_user.id)
    log.info("Document received", filename=msg.document.file_name if msg.document else "No document")
    data = await state.get_data()
    log.info("FSM data", data=data)

    # Проверяем, не находимся ли мы в режиме OCR
    # ocr_mode и upload_mode - взаимоисключающие режимы обработки документов
    # В каждый момент времени может быть активен только один режим
    if data.get("ocr_mode"):
        log.info("OCR mode active, skipping upload handler")
        return  # Пропускаем обработку, чтобы документ попал в OCR обработчик

    # Проверяем, не находимся ли мы в режиме загрузки файлов
    if not data.get("upload_mode"):
        log.info("Upload mode not active")
        await msg.answer(
            "❌ Вы ещё не активировали режим загрузки. Нажмите «📤 Загрузка файлов» и следуйте инструкциям 🙂",
            reply_markup=main_menu(),
        )
        return

    doc = msg.document
    if not doc or not hasattr(doc, "file_name") or doc.file_name is None:
        await msg.answer(
            "❌ Файл не содержит имени. Попробуйте переименовать файл и отправить снова.", reply_markup=main_menu()
        )
        return

    # Валидация файла перед загрузкой
    try:
        from app.utils.file_validation import validate_file, FileValidationError

        validate_file(doc.file_name, doc.file_size)
    except FileValidationError as e:
        await msg.answer(
            f"❌ <b>Файл не прошел проверку:</b>\n\n{str(e)}\n\n" f"Пожалуйста, проверьте файл и попробуйте снова.",
            parse_mode="HTML",
            reply_markup=main_menu(),
        )
        return
    except Exception as e:
        log.error("file_validation_error", filename=doc.file_name, error=str(e))
        await msg.answer(
            "❌ Произошла ошибка при проверке файла. Попробуйте снова.",
            reply_markup=main_menu(),
        )
        return

    file_path = None
    try:
        # Получаем информацию о файле
        file_info = await msg.bot.get_file(doc.file_id)

        with tempfile.NamedTemporaryFile(delete=False, suffix=f"_{doc.file_name if doc.file_name else ''}") as tmp:
            file_path = tmp.name
            # Загружаем файл используя правильный метод для aiogram 3.x
            await msg.bot.download_file(file_info.file_path, file_path)

        # Загрузка в Яндекс.Диск
        try:
            from app.services.yandex_disk_service import YandexDiskService

            yandex_service = YandexDiskService(settings.yandex_disk_token)

            # Показываем прогресс загрузки
            progress_msg = await msg.answer("⏳ Загружаю файл на Яндекс.Диск...")

            # Загружаем файл в выбранную папку
            # Правильно формируем путь
            if USER_FILES_DIR.startswith("disk:"):
                base_path = USER_FILES_DIR[5:]  # Убираем только первый disk:
            else:
                base_path = USER_FILES_DIR

            # Формируем полный путь для загрузки
            file_path_components = determine_path(doc.file_name)
            remote_path = f"{base_path}/{file_path_components}/{doc.file_name}"

            # Проверяем, соответствует ли имя файла шаблону
            from app.utils.file_router import parse_filename

            filename_info = parse_filename(doc.file_name)
            is_unsorted = file_path_components.startswith("unsorted")

            log.info(
                "upload_path_components",
                user_files_dir=USER_FILES_DIR,
                base_path=base_path,
                file_path_components=file_path_components,
                filename=doc.file_name,
                remote_path=remote_path,
                is_unsorted=is_unsorted,
            )

            # Проверяем, существует ли файл с таким именем
            file_exists = await yandex_service.file_exists(remote_path)
            if file_exists:
                await msg.answer(
                    f"⚠️ <b>Файл уже существует!</b>\n\n"
                    f"Файл <code>{doc.file_name}</code> уже загружен на Яндекс.Диск.\n\n"
                    f"📁 Путь: <code>{remote_path}</code>\n\n"
                    f"Чтобы загрузить файл с другим именем, переименуйте его и попробуйте снова.",
                    parse_mode="HTML",
                    reply_markup=main_menu(),
                )
                return

            success = await yandex_service.upload_file(file_path, remote_path)

            if success:
                log.info("manual upload succeeded", filename=doc.file_name, path=file_path)

                # Удаляем сообщение о прогрессе
                await progress_msg.delete()

                # Формируем сообщение об успешной загрузке
                success_message = f"✅ Файл <b>{doc.file_name}</b> надёжно сохранён на Яндекс.Диске!\n"

                # Добавляем предупреждение, если файл помещен в unsorted
                if is_unsorted:
                    success_message += (
                        f"⚠️ <b>Внимание:</b> Файл помещен в папку 'unsorted', так как имя не соответствует шаблону.\n\n"
                    )
                    success_message += (
                        "<b>Правильный формат:</b> <code>Принципал_Агент_вид документа_номер_дата</code>\n"
                    )
                    success_message += (
                        "<b>Пример:</b> <code>Альфатрекс_Агрико_агентский договор_2_300525.docx</code>\n\n"
                    )

                success_message += f'<a href="{success}">🔗 Скачать файл</a>\n'
                success_message += "Хотите загрузить ещё? 📎"

                await msg.answer(
                    success_message,
                    parse_mode="HTML",
                    reply_markup=main_menu(),
                )
            else:
                log.error("manual upload failed on service", filename=doc.file_name)
                await progress_msg.edit_text(
                    f"❌ Не получилось сохранить <b>{doc.file_name}</b> на Яндекс.Диск. "
                    "Попробуйте ещё раз чуть позже или обратитесь в поддержку 🙏",
                    parse_mode="HTML",
                    reply_markup=main_menu(),
                )
        except Exception as e:
            log.error("manual upload exception", filename=doc.file_name, error=str(e))
            await progress_msg.edit_text(
                "⚠️ Возникла непредвиденная ошибка при загрузке. "
                "Пожалуйста, попробуйте ещё раз или сообщите администратору.",
                parse_mode="HTML",
                reply_markup=main_menu(),
            )
    finally:
        # Безопасная очистка временного файла
        from app.utils.cleanup import cleanup_temp_file_safe

        cleanup_temp_file_safe(file_path)
    # выходим из режима загрузки, но не отправляем 'Главное меню'
    await state.update_data(upload_mode=False)
