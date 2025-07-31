import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import aiohttp
import yadisk
import structlog

from app.config import settings

log = structlog.get_logger(__name__)


class YandexDiskService:
    """Сервис для работы с Яндекс.Диском"""

    def __init__(self, token: str):
        self.token = token
        self.client = yadisk.YaDisk(token=token)
        self.logger = log

    def _clean_path(self, path: str) -> str:
        """
        Очищает путь для Яндекс.Диска.

        Args:
            path: Исходный путь

        Returns:
            Очищенный путь
        """
        # Убираем префикс disk: если есть
        if path.startswith("disk:"):
            path = path[5:]

        # Убираем лишние слеши
        path = path.strip("/")

        return path

    async def check_connection(self) -> bool:
        """Проверяет подключение к Яндекс.Диску"""
        try:
            self.client.get_disk_info()
            return True
        except Exception as e:
            self.logger.error(f"Ошибка подключения к Яндекс.Диску: {e}")
            return False

    async def upload_file(self, local_path: str, remote_path: str) -> Optional[str]:
        """
        Загружает файл на Яндекс.Диск.

        Args:
            local_path: Локальный путь к файлу
            remote_path: Путь на Яндекс.Диске

        Returns:
            URL для скачивания или None при ошибке
        """
        try:
            # Проверяем существование файла
            if not Path(local_path).exists():
                self.logger.error(f"Файл не найден: {local_path}")
                return None

            # Очищаем путь для Яндекс.Диска
            clean_remote_path = self._clean_path(remote_path)
            self.logger.info(f"upload_file: original_path='{remote_path}', clean_path='{clean_remote_path}'")

            # Создаем директорию если нужно
            remote_dir = Path(clean_remote_path).parent
            await self.ensure_path(str(remote_dir))

            # Загружаем файл
            self._upload(local_path, clean_remote_path)
            self.logger.info(f"Файл загружен на Яндекс.Диск: {clean_remote_path}")

            # Возвращаем ссылку для скачивания
            url = await self.get_download_url(clean_remote_path)
            return url or remote_path

        except Exception as e:
            self.logger.error(f"Ошибка при загрузке {local_path}: {e}")
            return None

    async def download_file(self, remote_path: str, local_path: str) -> bool:
        """
        Скачивает файл с Яндекс.Диска.

        Args:
            remote_path: Путь на Яндекс.Диске
            local_path: Локальный путь для сохранения

        Returns:
            True если успешно, False при ошибке
        """
        try:
            # Создаем локальную директорию
            local_dir = Path(local_path).parent
            local_dir.mkdir(parents=True, exist_ok=True)

            # Скачиваем файл
            self._download(remote_path, local_path)
            self.logger.info(f"Файл скачан с Яндекс.Диска: {local_path}")
            return True

        except Exception as e:
            self.logger.error(f"Неожиданная ошибка при скачивании: {e}")
            return False

    def _upload(self, local_path: str, remote_path: str) -> None:
        """Синхронная загрузка файла"""
        self.client.upload(local_path, remote_path)

    def _download(self, remote_path: str, local_path: str) -> None:
        """Синхронное скачивание файла"""
        self.client.download(remote_path, local_path)

    async def ensure_path(self, path: str) -> bool:
        """Создает путь если не существует"""
        try:
            self.client.mkdir(path)
            return True
        except Exception:
            return False

    async def get_download_url(self, path: str) -> Optional[str]:
        """Получает ссылку для скачивания"""
        try:
            return self.client.get_download_link(path)
        except Exception:
            return None

    async def get_files_list(self, path: str) -> List[Dict[str, Any]]:
        """Получает список файлов"""
        try:
            files = self.client.listdir(path)
            return [
                {
                    "name": item.name,
                    "path": item.path,
                    "type": "dir" if item.type == "dir" else "file",
                    "size": getattr(item, "size", 0),
                }
                for item in files
            ]
        except Exception as e:
            self.logger.error(f"Ошибка получения списка файлов: {e}")
            return []

    async def create_folder(self, path: str) -> bool:
        """Создает папку"""
        try:
            self.client.mkdir(path)
            return True
        except Exception as e:
            self.logger.error(f"Ошибка создания папки {path}: {e}")
            return False

    async def delete_file(self, path: str) -> bool:
        """Удаляет файл"""
        try:
            self.client.remove(path)
            return True
        except Exception as e:
            self.logger.error(f"Ошибка удаления файла {path}: {e}")
            return False

    async def get_disk_info(self) -> Optional[Dict[str, Any]]:
        """Получает информацию о диске"""
        try:
            info = self.client.get_disk_info()
            return {"total_space": info.total_space, "used_space": info.used_space, "free_space": info.free_space}
        except Exception as e:
            self.logger.error(f"Ошибка получения информации о диске: {e}")
            return None

    async def file_exists(self, path: str) -> bool:
        """Проверяет существование файла"""
        try:
            self.client.get_meta(path)
            return True
        except Exception:
            return False

    def format_file_size(self, size_bytes: int) -> str:
        """Форматирует размер файла"""
        size_float = float(size_bytes)
        for unit in ["B", "KB", "MB", "GB"]:
            if size_float < 1024.0:
                return f"{size_float:.1f} {unit}"
            size_float /= 1024.0
        return f"{size_float:.1f} TB"
