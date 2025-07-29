import re

from app.config import settings
from app.utils.filename_parser import SUPPORTED_EXTS

DANGEROUS_CHARS = r'[<>:"/\\|?*]'
MAX_FILENAME_LENGTH = 255


class FileValidationError(Exception):
    pass


def validate_file(filename: str, file_size: int) -> None:
    if not filename or not filename.strip():
        raise FileValidationError("Пустое имя файла")
    if len(filename) > MAX_FILENAME_LENGTH:
        raise FileValidationError(
            f"Слишком длинное имя файла (макс. {MAX_FILENAME_LENGTH} символов)"
        )
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
        raise FileValidationError(
            f"Файл слишком большой: {size_mb:.1f}МБ (макс. {max_mb:.0f}МБ)"
        )
    if re.search(DANGEROUS_CHARS, filename):
        raise FileValidationError("Имя файла содержит недопустимые символы")
    if filename.startswith(".") or filename.startswith("~"):
        raise FileValidationError("Системные и скрытые файлы запрещены")


def sanitize_filename(filename: str) -> str:
    clean_name = re.sub(DANGEROUS_CHARS, "_", filename)
    clean_name = re.sub(r"_+", "_", clean_name)
    clean_name = clean_name.strip("_")
    return clean_name[:MAX_FILENAME_LENGTH]
