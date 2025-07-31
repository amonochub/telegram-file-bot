"""Утилиты для очистки временных файлов."""

import os
import time
from pathlib import Path
from typing import List

import structlog

from app.config import settings

log = structlog.get_logger(__name__)


def cleanup_temp_files() -> dict:
    """
    Очищает временные файлы старше 1 часа.

    Returns:
        Словарь с информацией об очистке
    """
    temp_dir = settings.temp_dir_path

    if not temp_dir.exists():
        return {"deleted_count": 0, "size_before": 0, "size_after": 0, "error": "Temp directory does not exist"}

    current_time = time.time()
    deleted_count = 0
    size_before = 0
    size_after = 0

    try:
        # Подсчитываем размер до очистки
        for root, dirs, files in os.walk(temp_dir):
            for file in files:
                file_path = Path(root) / file
                if file_path.exists():
                    size_before += file_path.stat().st_size

                    # Проверяем возраст файла
                    file_age = current_time - file_path.stat().st_atime
                    if file_age > 3600:  # 1 час
                        try:
                            file_path.unlink()
                            deleted_count += 1
                        except Exception as e:
                            log.warning(f"Failed to delete {file_path}: {e}")

        # Подсчитываем размер после очистки
        for root, dirs, files in os.walk(temp_dir):
            for file in files:
                file_path = Path(root) / file
                if file_path.exists():
                    size_after += file_path.stat().st_size

        # Удаляем пустые директории
        for root, dirs, files in os.walk(temp_dir, topdown=False):
            for dir_name in dirs:
                dir_path = Path(root) / dir_name
                try:
                    if dir_path.exists() and not any(dir_path.iterdir()):
                        dir_path.rmdir()
                except Exception as e:
                    log.warning(f"Failed to remove empty directory {dir_path}: {e}")

        return {"deleted_count": deleted_count, "size_before": size_before, "size_after": size_after, "error": None}

    except Exception as e:
        log.error(f"Error during cleanup: {e}")
        return {"deleted_count": deleted_count, "size_before": size_before, "size_after": size_after, "error": str(e)}


def cleanup_specific_file(file_path: str) -> bool:
    """
    Удаляет конкретный файл.

    Args:
        file_path: Путь к файлу для удаления

    Returns:
        True если файл удален, False если ошибка
    """
    try:
        path = Path(file_path)
        if path.exists():
            path.unlink()
            return True
        return False
    except Exception as e:
        log.error(f"Error deleting file {file_path}: {e}")
        return False


def get_temp_dir_size() -> int:
    """
    Возвращает размер временной директории в байтах.

    Returns:
        Размер в байтах
    """
    temp_dir = settings.temp_dir_path

    if not temp_dir.exists():
        return 0

    total_size = 0

    try:
        for root, dirs, files in os.walk(temp_dir):
            for file in files:
                file_path = Path(root) / file
                if file_path.exists():
                    total_size += file_path.stat().st_size
        return total_size
    except Exception as e:
        log.error(f"Error calculating temp dir size: {e}")
        return 0
