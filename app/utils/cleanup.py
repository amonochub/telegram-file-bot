"""Утилиты для очистки временных файлов."""

import os
import shutil
import tempfile
from pathlib import Path
from typing import List
import structlog

logger = structlog.get_logger(__name__)


def cleanup_temp_files(temp_dir: str = "temp", max_age_hours: int = 24) -> int:
    """
    Очищает временные файлы старше указанного возраста.
    
    Args:
        temp_dir: Директория с временными файлами
        max_age_hours: Максимальный возраст файлов в часах
        
    Returns:
        Количество удаленных файлов
    """
    import time
    
    if not os.path.exists(temp_dir):
        logger.info("temp_dir_not_exists", temp_dir=temp_dir)
        return 0
    
    current_time = time.time()
    max_age_seconds = max_age_hours * 3600
    deleted_count = 0
    
    try:
        for root, dirs, files in os.walk(temp_dir):
            for file in files:
                file_path = os.path.join(root, file)
                try:
                    # Проверяем время последнего доступа
                    file_age = current_time - os.path.getatime(file_path)
                    
                    if file_age > max_age_seconds:
                        os.remove(file_path)
                        deleted_count += 1
                        logger.debug("temp_file_deleted", file_path=file_path, age_hours=file_age/3600)
                        
                except (OSError, PermissionError) as e:
                    logger.warning("failed_to_delete_temp_file", file_path=file_path, error=str(e))
                    
        # Удаляем пустые директории
        for root, dirs, files in os.walk(temp_dir, topdown=False):
            for dir_name in dirs:
                dir_path = os.path.join(root, dir_name)
                try:
                    if not os.listdir(dir_path):  # Если директория пустая
                        os.rmdir(dir_path)
                        logger.debug("empty_temp_dir_deleted", dir_path=dir_path)
                except (OSError, PermissionError) as e:
                    logger.warning("failed_to_delete_temp_dir", dir_path=dir_path, error=str(e))
                    
    except Exception as e:
        logger.error("cleanup_error", temp_dir=temp_dir, error=str(e))
        
    logger.info("cleanup_completed", temp_dir=temp_dir, deleted_count=deleted_count)
    return deleted_count


def cleanup_specific_file(file_path: str) -> bool:
    """
    Удаляет конкретный файл с обработкой ошибок.
    
    Args:
        file_path: Путь к файлу для удаления
        
    Returns:
        True если файл успешно удален, False в противном случае
    """
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            logger.debug("file_deleted", file_path=file_path)
            return True
        else:
            logger.debug("file_not_exists", file_path=file_path)
            return True  # Файл уже не существует
    except (OSError, PermissionError) as e:
        logger.warning("failed_to_delete_file", file_path=file_path, error=str(e))
        return False


def cleanup_temp_file_safe(file_path: str) -> None:
    """
    Безопасное удаление временного файла с логированием.
    Используется в блоках finally для гарантированной очистки.
    
    Args:
        file_path: Путь к файлу для удаления
    """
    if file_path and os.path.exists(file_path):
        try:
            os.remove(file_path)
            logger.debug("temp_file_cleaned", file_path=file_path)
        except (OSError, PermissionError) as e:
            logger.warning("failed_to_cleanup_temp_file", file_path=file_path, error=str(e))


def get_temp_dir_size(temp_dir: str = "temp") -> int:
    """
    Возвращает общий размер временной директории в байтах.
    
    Args:
        temp_dir: Путь к временной директории
        
    Returns:
        Размер директории в байтах
    """
    total_size = 0
    
    if not os.path.exists(temp_dir):
        return 0
        
    try:
        for root, dirs, files in os.walk(temp_dir):
            for file in files:
                file_path = os.path.join(root, file)
                try:
                    total_size += os.path.getsize(file_path)
                except (OSError, PermissionError):
                    pass
    except Exception as e:
        logger.error("failed_to_calculate_temp_size", temp_dir=temp_dir, error=str(e))
        
    return total_size


def format_size(size_bytes: int) -> str:
    """Форматирует размер в байтах в читаемый вид."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} TB" 