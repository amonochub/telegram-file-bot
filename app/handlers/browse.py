import os
import tempfile

import structlog
from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, FSInputFile, Message, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.config import settings
from app.services.yandex_disk_service import YandexDiskService
from app.config import USER_FILES_DIR

router = Router()
logger = structlog.get_logger()

yandex_service = YandexDiskService(settings.yandex_disk_token)

# Кэш для маппинга путей в короткие ID
# Используется из-за ограничения Telegram callback_data (64 байта)
# Вместо полного пути используется короткий числовой ID
path_cache = {}
id_counter = 1


def get_path_id(path: str) -> str:
    """Получить короткий ID для пути"""
    global id_counter
    if path not in path_cache:
        path_cache[path] = str(id_counter)
        id_counter += 1
    return path_cache[path]


def get_path_by_id(path_id: str) -> str:
    """Получить путь по ID"""
    for path, pid in path_cache.items():
        if pid == path_id:
            return path
    return ""


# Проверяем подключение к Яндекс.Диску при запуске
async def check_yandex_connection():
    try:
        connected = await yandex_service.check_connection()
        if connected:
            logger.info("Yandex.Disk connection successful")
        else:
            logger.warning("Yandex.Disk connection failed")
        return connected
    except Exception as e:
        logger.error("Yandex.Disk connection error", error=str(e))
        return False


PAGE_SIZE = 20


class BrowseStates(StatesGroup):
    waiting_new_folder_name = State()


@router.message(Command("files"))
async def files_command(message: Message):
    logger.info("files_command", user_id=message.from_user.id)
    user_path = USER_FILES_DIR
    await show_directory(message, user_path)


@router.message(Command("disk_info"))
async def disk_info_command(message: Message):
    """Показать информацию о диске"""
    logger.info("disk_info_command", user_id=message.from_user.id)

    try:
        # Получаем информацию о диске
        disk_info = await yandex_service.get_disk_info()

        if disk_info:
            used_space = yandex_service.format_file_size(disk_info.get("used_space", 0))
            total_space = yandex_service.format_file_size(disk_info.get("total_space", 0))
            free_space = yandex_service.format_file_size(disk_info.get("free_space", 0))

            # Вычисляем процент использования
            used_percent = 0
            if disk_info.get("total_space", 0) > 0:
                used_percent = (disk_info.get("used_space", 0) / disk_info.get("total_space", 0)) * 100

            # Создаем визуальный индикатор
            progress_bar_length = 20
            filled_length = int((used_percent / 100) * progress_bar_length)
            progress_bar = "█" * filled_length + "░" * (progress_bar_length - filled_length)

            info_text = (
                f"💾 <b>Информация о Яндекс.Диске</b>\n\n"
                f"📊 <b>Использовано:</b> {used_space} из {total_space}\n"
                f"📈 <b>Свободно:</b> {free_space}\n"
                f"📊 <b>Заполнено:</b> {used_percent:.1f}%\n\n"
                f"<code>{progress_bar}</code> {used_percent:.1f}%\n\n"
                f"🔄 Последнее обновление: {disk_info.get('updated', 'Неизвестно')}"
            )

            await message.answer(info_text, parse_mode="HTML")
        else:
            await message.answer("❌ Не удалось получить информацию о диске")

    except Exception as e:
        logger.error("Error getting disk info", error=str(e))
        await message.answer("❌ Ошибка при получении информации о диске")


@router.message(Command("cleanup"))
async def cleanup_command(message: Message):
    """Очистить временные файлы"""
    logger.info("cleanup_command", user_id=message.from_user.id)

    try:
        from app.utils.cleanup import cleanup_temp_files, get_temp_dir_size, format_size
        
        # Получаем размер до очистки
        size_before = get_temp_dir_size()
        
        # Очищаем файлы старше 1 часа
        deleted_count = cleanup_temp_files(max_age_hours=1)
        
        # Получаем размер после очистки
        size_after = get_temp_dir_size()
        
        info_text = (
            f"🧹 <b>Очистка временных файлов завершена</b>\n\n"
            f"🗑️ <b>Удалено файлов:</b> {deleted_count}\n"
            f"📊 <b>Освобождено места:</b> {format_size(size_before - size_after)}\n"
            f"💾 <b>Текущий размер temp:</b> {format_size(size_after)}\n\n"
            f"⏰ <b>Удалены файлы старше 1 часа</b>"
        )
        
        await message.answer(info_text, parse_mode="HTML")
        
    except Exception as e:
        logger.error("Error during cleanup", error=str(e))
        await message.answer("❌ Ошибка при очистке временных файлов")


async def show_directory(message: Message, path: str, page: int = 0, edit: bool = False):
    try:
        logger.info("show_directory_called", path=path, user_id=message.from_user.id)

        # Проверяем доступность Яндекс.Диска
        try:
            # Получаем список файлов без создания папки
            files_list = await yandex_service.get_files_list(path)
            logger.debug("files_list_retrieved", count=len(files_list), path=path)

            if not files_list:
                text = f"📁 Папка пуста: {path}"
                if edit:
                    await message.edit_text(text, parse_mode="HTML")
                else:
                    await message.answer(text, parse_mode="HTML")
                return
        except Exception as e:
            # Если Яндекс.Диск недоступен, показываем информативное сообщение
            text = (
                "⚠️ <b>Яндекс.Диск временно недоступен</b>\n\n"
                "Для работы с файлами нужно обновить токен Яндекс.Диска:\n"
                "1. Перейдите на https://yandex.ru/dev/disk/poligon/\n"
                "2. Получите новый OAuth-токен\n"
                "3. Обновите YANDEX_DISK_TOKEN в файле .env\n"
                "4. Перезапустите бота\n\n"
                "📋 <i>Подробная инструкция в файле GET_YANDEX_TOKEN.md</i>"
            )
            if edit:
                await message.edit_text(text, parse_mode="HTML")
            else:
                await message.answer(text, parse_mode="HTML")
            return

        builder = InlineKeyboardBuilder()
        user_root = USER_FILES_DIR
        if path != user_root and path.startswith(user_root):
            parent_path = os.path.dirname(path.rstrip("/"))
            builder.button(text="⬅️ Назад", callback_data=f"browse:{get_path_id(parent_path)}")

        # Разделяем папки и файлы
        folders = [f for f in files_list if f["type"] == "dir"]
        files = [f for f in files_list if f["type"] == "file"]

        # Объединяем папки и файлы в один список для правильной пагинации
        all_items = []
        for folder in folders:
            all_items.append({"type": "folder", "data": folder})
        for file in files:
            all_items.append({"type": "file", "data": file})

        # Применяем пагинацию
        start = page * PAGE_SIZE
        end = start + PAGE_SIZE
        page_items = all_items[start:end]

        # Создаем кнопки для элементов на текущей странице
        for item in page_items:
            if item["type"] == "folder":
                folder = item["data"]
                builder.button(text=f"📁 {folder['name']}", callback_data=f"browse:{get_path_id(folder['path'])}")
            elif item["type"] == "file":
                file = item["data"]
                file_size = yandex_service.format_file_size(file["size"])
                
                # Создаем строку с кнопками для файла
                file_row = []
                file_row.append(
                    InlineKeyboardButton(
                        text=f"📄 {file['name']} ({file_size})",
                        callback_data=f"download_file:{get_path_id(file['path'])}"
                    )
                )
                file_row.append(
                    InlineKeyboardButton(
                        text="🗑️",
                        callback_data=f"delete_file:{get_path_id(file['path'])}"
                    )
                )
                builder.row(*file_row)

        # pagination buttons
        total_items = len(folders) + len(files)
        total_pages = (total_items - 1) // PAGE_SIZE + 1 if total_items > 0 else 1
        if total_pages > 1:
            pag_row = []
            if page > 0:
                pag_row.append(
                    InlineKeyboardButton(text="⬅️", callback_data=f"browse_page:{get_path_id(path)}:{page - 1}")
                )
            pag_row.append(InlineKeyboardButton(text=f"{page + 1}/{total_pages}", callback_data="noop"))
            if page < total_pages - 1:
                pag_row.append(
                    InlineKeyboardButton(text="➡️", callback_data=f"browse_page:{get_path_id(path)}:{page + 1}")
                )
            builder.row(*pag_row)

        # button to create folder
        builder.button(text="➕ Новая папка", callback_data=f"browse_mkdir:{get_path_id(path)}")
        builder.adjust(1)
        text = f"📁 <b>{path}</b>\n\n📊 Папок: {len(folders)}  Файлов: {len(files)}  (стр. {page + 1}/{total_pages})"
        if edit:
            await message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="HTML")
        else:
            await message.answer(text, reply_markup=builder.as_markup(), parse_mode="HTML")
    except Exception as e:
        logger.error("Error showing directory", error=str(e), path=path)

        # Более информативное сообщение об ошибке
        if "Forbidden" in str(e) or "403" in str(e):
            error_text = "❌ Ошибка доступа к Яндекс.Диску. Проверьте токен и права доступа."
        elif "Not Found" in str(e) or "404" in str(e):
            error_text = "❌ Папка не найдена на Яндекс.Диске."
        else:
            error_text = f"❌ Ошибка загрузки папки: {e}"

        if edit:
            await message.edit_text(error_text, parse_mode="HTML")
        else:
            await message.answer(error_text, parse_mode="HTML")


@router.callback_query(F.data.startswith("browse:"))
async def browse_callback(callback: CallbackQuery):
    path = get_path_by_id(callback.data.replace("browse:", ""))
    await show_directory(callback.message, path, page=0, edit=True)
    await callback.answer()


@router.callback_query(F.data.startswith("browse_page:"))
async def browse_page_callback(callback: CallbackQuery):
    data = callback.data.replace("browse_page:", "").split(":")
    path = get_path_by_id(data[0])
    page = int(data[1])
    await show_directory(callback.message, path, page=page, edit=True)
    await callback.answer()


@router.callback_query(F.data.startswith("browse_mkdir:"))
async def browse_mkdir_prompt(callback: CallbackQuery, state: FSMContext):
    path = get_path_by_id(callback.data.replace("browse_mkdir:", ""))
    await callback.message.answer("Введите имя новой папки:")
    await state.update_data(mkdir_path=path)
    await state.set_state(BrowseStates.waiting_new_folder_name)
    await callback.answer()


@router.message(BrowseStates.waiting_new_folder_name)
async def browse_mkdir_create(msg: Message, state: FSMContext):
    data = await state.get_data()
    base_path = data.get("mkdir_path", "/")
    new_path = os.path.join(base_path, msg.text.strip())
    success = await yandex_service.create_folder(new_path)
    if success:
        await msg.answer("✅ Папка создана")
    else:
        await msg.answer("❌ Не удалось создать папку")
    await show_directory(msg, base_path)
    await state.clear()


@router.callback_query(F.data.startswith("download_file:"))
async def download_callback(callback: CallbackQuery):
    file_path = get_path_by_id(callback.data.replace("download_file:", ""))
    file_name = os.path.basename(file_path)

    try:
        # Показываем сообщение о загрузке
        loading_msg = await callback.message.answer("⏳ Скачиваю файл...")

        # Скачиваем файл с Яндекс.Диска во временную папку
        with tempfile.NamedTemporaryFile(delete=False, suffix=f"_{file_name}") as temp_file:
            temp_path = temp_file.name

        # Скачиваем файл
        success = await yandex_service.download_file(file_path, temp_path)

        if success and os.path.exists(temp_path):
            # Отправляем файл в Telegram
            from aiogram.types import FSInputFile

            await callback.message.answer_document(
                FSInputFile(temp_path, filename=file_name), caption=f"📥 Файл: {file_name}"
            )

            # Удаляем временный файл
            os.unlink(temp_path)

            # Удаляем сообщение о загрузке
            await loading_msg.delete()
        else:
            await loading_msg.edit_text(f"❌ Не удалось скачать файл {file_name}")

    except Exception as e:
        logger.error(f"Ошибка скачивания файла {file_path}: {e}")
        await callback.message.answer(f"❌ Ошибка при скачивании файла {file_name}: {str(e)}")
    await callback.answer()


@router.callback_query(F.data.startswith("delete_file:"))
async def delete_file_callback(callback: CallbackQuery):
    file_path = get_path_by_id(callback.data.replace("delete_file:", ""))
    file_name = os.path.basename(file_path)
    
    # Создаем клавиатуру для подтверждения удаления
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Да, удалить", callback_data=f"confirm_delete:{callback.data.replace('delete_file:', '')}")
    builder.button(text="❌ Отмена", callback_data=f"cancel_delete:{callback.data.replace('delete_file:', '')}")
    builder.adjust(2)
    
    await callback.message.answer(
        f"🗑️ Вы уверены, что хотите удалить файл <b>{file_name}</b>?\n\n"
        f"📁 Путь: <code>{file_path}</code>\n\n"
        "⚠️ Это действие нельзя отменить!",
        parse_mode="HTML",
        reply_markup=builder.as_markup()
    )
    await callback.answer()


@router.callback_query(F.data.startswith("confirm_delete:"))
async def confirm_delete_callback(callback: CallbackQuery):
    file_path = get_path_by_id(callback.data.replace("confirm_delete:", ""))
    file_name = os.path.basename(file_path)
    
    try:
        # Показываем сообщение о удалении
        loading_msg = await callback.message.answer("🗑️ Удаляю файл...")
        
        # Удаляем файл с Яндекс.Диска
        success = await yandex_service.remove_file(file_path)
        
        if success:
            await loading_msg.edit_text(f"✅ Файл <b>{file_name}</b> успешно удален!")
        else:
            await loading_msg.edit_text(f"❌ Не удалось удалить файл {file_name}")
            
    except Exception as e:
        logger.error(f"Ошибка удаления файла {file_path}: {e}")
        await callback.message.answer(f"❌ Ошибка при удалении файла {file_name}: {str(e)}")
    await callback.answer()


@router.callback_query(F.data.startswith("cancel_delete:"))
async def cancel_delete_callback(callback: CallbackQuery):
    await callback.message.edit_text("❌ Удаление отменено")
    await callback.answer()
