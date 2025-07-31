import re
from pathlib import Path
from typing import Optional

from app.config import settings
from app.utils.filename_parser import SUPPORTED_EXTS
from app.utils.types import ValidatedFilename, SanitizedFilename, FileSize
from app.utils.exceptions import FileValidationError

DANGEROUS_CHARS = r'[<>:"/\\|?*]'
MAX_FILENAME_LENGTH = 255


def validate_file(filename: str, file_size: int) -> ValidatedFilename:
    """
    Валидирует файл и возвращает валидированное имя.

    Args:
        filename: Имя файла для валидации
        file_size: Размер файла в байтах

    Returns:
        Валидированное имя файла

    Raises:
        FileValidationError: Если файл не прошел валидацию
    """
    if not filename or not filename.strip():
        raise FileValidationError("Пустое имя файла")
    if len(filename) > MAX_FILENAME_LENGTH:
        raise FileValidationError(f"Слишком длинное имя файла (макс. {MAX_FILENAME_LENGTH} символов)")
    if "." not in filename:
        raise FileValidationError("Файл должен иметь расширение")
    ext = filename.lower().rsplit(".", 1)[-1]
    if ext not in SUPPORTED_EXTS:
        raise FileValidationError(f"Недопустимое расширение: .{ext}")
    if file_size <= 0:
        raise FileValidationError("Пустой файл")
    if file_size > settings.max_file_size:
        size_mb = file_size / (1024 * 1024)
        max_mb = settings.max_file_size / (1024 * 1024)
        raise FileValidationError(f"Файл слишком большой: {size_mb:.1f}МБ (макс. {max_mb:.0f}МБ)")
    if re.search(DANGEROUS_CHARS, filename):
        raise FileValidationError("Имя файла содержит недопустимые символы")
    if filename.startswith(".") or filename.startswith("~"):
        raise FileValidationError("Системные и скрытые файлы запрещены")

    return ValidatedFilename(filename)


def sanitize_filename(filename: str) -> SanitizedFilename:
    """
    Очищает имя файла от опасных символов.

    Args:
        filename: Исходное имя файла

    Returns:
        Очищенное имя файла
    """
    clean_name = re.sub(DANGEROUS_CHARS, "_", filename)
    clean_name = re.sub(r"_+", "_", clean_name)
    clean_name = clean_name.strip("_")
    return SanitizedFilename(clean_name[:MAX_FILENAME_LENGTH])


def validate_file_path(file_path: Path) -> bool:
    """
    Валидирует путь к файлу.

    Args:
        file_path: Путь к файлу

    Returns:
        True если путь валиден, False если нет
    """
    try:
        # Проверяем, что файл существует
        if not file_path.exists():
            return False

        # Проверяем, что это файл, а не директория
        if not file_path.is_file():
            return False

        # Проверяем размер файла
        file_size = file_path.stat().st_size
        if file_size <= 0:
            return False
        if file_size > settings.max_file_size:
            return False

        # Проверяем расширение (убираем точку)
        ext = file_path.suffix.lower().lstrip(".")
        if ext not in SUPPORTED_EXTS:
            return False

        return True

    except (OSError, ValueError):
        return False
