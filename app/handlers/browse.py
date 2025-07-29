import os
import tempfile

import structlog
from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, FSInputFile, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton

from app.config import settings
from app.services.yandex_disk_service import YandexDiskService
from app.config import USER_FILES_DIR

router = Router()
logger = structlog.get_logger()

yandex_service = YandexDiskService(settings.yandex_disk_token)

# Кэш для путей (path -> id)
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
            print("[DEBUG] Yandex.Disk connection successful")
        else:
            print("[DEBUG] Yandex.Disk connection failed")
        return connected
    except Exception as e:
        print(f"[DEBUG] Yandex.Disk connection error: {e}")
        return False


PAGE_SIZE = 20


class BrowseStates(StatesGroup):
    waiting_new_folder_name = State()


@router.message(Command("files"))
async def files_command(message: Message):
    logger.info("files_command", user_id=message.from_user.id)
    print("[DEBUG] files_command triggered")
    user_path = USER_FILES_DIR
    await show_directory(message, user_path)


async def show_directory(message: Message, path: str, page: int = 0, edit: bool = False):
    try:
        logger.info("show_directory_called", path=path, user_id=message.from_user.id)
        print(f"[DEBUG] show_directory called for path: {path}")

        # Проверяем доступность Яндекс.Диска
        try:
            # Получаем список файлов без создания папки
            files_list = await yandex_service.get_files_list(path)
            logger.info("yadisk_files_list", files_list=files_list)
            print(f"[DEBUG] files_list: {files_list}")

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
                builder.button(
                    text=f"📄 {file['name']} ({file_size})",
                    callback_data=f"download_file:{get_path_id(file['path'])}",
                )

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
        print(f"[DEBUG] Exception in show_directory: {e}")

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
