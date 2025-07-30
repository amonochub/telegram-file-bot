import asyncio
import os
from typing import Any, Dict, List, Optional

import structlog
import yadisk
from yadisk.exceptions import YaDiskError

logger = structlog.get_logger(__name__)


class YandexDiskService:
    """Сервис для работы с Яндекс.Диском"""

    def __init__(self, token: str):
        self.token = token
        self.client = yadisk.YaDisk(token=token)
        self.logger = logger

    # --- helpers для run_in_executor ---
    def _upload(self, local_path: str, remote_path: str) -> None:
        """Блокирующая загрузка файла на Диск (используется в executor)."""
        # Добавляем таймаут для операций загрузки
        import asyncio
        try:
            self.client.upload(local_path, remote_path)
        except Exception as e:
            self.logger.error("upload_timeout_or_error", local_path=local_path, remote_path=remote_path, error=str(e))
            raise

    def _download(self, remote_path: str, local_path: str) -> None:
        """Блокирующее скачивание файла с Диска (используется в executor)."""
        try:
            self.client.download(remote_path, local_path)
        except Exception as e:
            self.logger.error("download_timeout_or_error", remote_path=remote_path, local_path=local_path, error=str(e))
            raise

    def _remove(self, remote_path: str, permanently: bool) -> None:
        """Блокирующее удаление файла с Диска (используется в executor)."""
        try:
            self.client.remove(remote_path, permanently)
        except Exception as e:
            self.logger.error("remove_timeout_or_error", remote_path=remote_path, permanently=permanently, error=str(e))
            raise

    async def check_connection(self) -> bool:
        try:
            loop = asyncio.get_event_loop()
            disk_info = await loop.run_in_executor(None, self.client.get_disk_info)
            self.logger.info(
                f"Подключение к Яндекс.Диску успешно. Место: {disk_info.used_space}/{disk_info.total_space}"
            )
            return True
        except Exception as e:
            self.logger.error(f"Ошибка подключения к Яндекс.Диску: {e}")
            return False

    async def upload_file(self, local_path: str, remote_path: str) -> Optional[str]:
        try:
            if not os.path.exists(local_path):
                self.logger.error(f"Файл не найден: {local_path}")
                return None

            # Создаем базовую папку при первой загрузке
            try:
                from app.config import USER_FILES_DIR

                # Правильно обрабатываем путь disk:/disk:
                if USER_FILES_DIR.startswith("disk:"):
                    base_dir = USER_FILES_DIR[5:]  # Убираем только первый disk:
                else:
                    base_dir = USER_FILES_DIR
                await self.create_folder(base_dir)
                self.logger.info(f"Базовая папка создана: {base_dir}")
            except Exception as e:
                self.logger.warning(f"Не удалось создать базовую папку: {e}")

            # Правильно обрабатываем путь для загрузки
            if remote_path.startswith("disk:"):
                clean_remote_path = remote_path[5:]  # Убираем только первый disk:
            else:
                clean_remote_path = remote_path

            remote_dir = os.path.dirname(clean_remote_path)
            if remote_dir and remote_dir != "/":
                await self.ensure_path(remote_dir)

            self.logger.info(f"upload_file: original_path='{remote_path}', clean_path='{clean_remote_path}'")
            loop = asyncio.get_event_loop()
            # Добавляем таймаут 60 секунд для загрузки файлов
            await asyncio.wait_for(
                loop.run_in_executor(None, self._upload, local_path, clean_remote_path),  # type: ignore[arg-type]
                timeout=60.0
            )
            self.logger.info(f"Файл загружен на Яндекс.Диск: {clean_remote_path}")
            url = await self.get_download_url(clean_remote_path)
            return url or remote_path
        except YaDiskError as e:
            self.logger.error(f"Ошибка Яндекс.Диска при загрузке {local_path}: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Неожиданная ошибка при загрузке: {e}")
            return None

    async def download_file(self, remote_path: str, local_path: str) -> bool:
        try:
            local_dir = os.path.dirname(local_path)
            if local_dir:
                os.makedirs(local_dir, exist_ok=True)
            loop = asyncio.get_event_loop()
            # Добавляем таймаут 60 секунд для скачивания файлов
            await asyncio.wait_for(
                loop.run_in_executor(None, self._download, remote_path, local_path),  # type: ignore[arg-type]
                timeout=60.0
            )
            self.logger.info(f"Файл скачан с Яндекс.Диска: {local_path}")
            return True
        except YaDiskError as e:
            self.logger.error(f"Ошибка Яндекс.Диска при скачивании {remote_path}: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Неожиданная ошибка при скачивании: {e}")
            return False

    async def get_files_list(self, path: str = "/", limit: int = 100) -> List[Dict[str, Any]]:
        try:
            # Убираем только первый префикс disk: если он есть
            if path.startswith("disk:"):
                clean_path = path[5:]  # Убираем "disk:" (5 символов)
            else:
                clean_path = path

            self.logger.info(f"get_files_list: original_path='{path}', clean_path='{clean_path}'")

            loop = asyncio.get_event_loop()
            files_info = await loop.run_in_executor(None, lambda: list(self.client.listdir(clean_path, limit=limit)))

            self.logger.info(f"API response: {len(files_info)} items from {clean_path}")

            files_list = []
            for item in files_info:
                file_info = {
                    "name": item.name,
                    "path": item.path,
                    "type": item.type,
                    "size": getattr(item, "size", 0) if item.type == "file" else 0,
                    "created": str(getattr(item, "created", "")),
                    "modified": str(getattr(item, "modified", "")),
                }
                files_list.append(file_info)
                self.logger.debug(f"Added item: {file_info['name']} ({file_info['type']})")

            self.logger.info(f"Получен список из {len(files_list)} элементов из {path} (clean_path: {clean_path})")
            return files_list
        except YaDiskError as e:
            self.logger.error(f"Ошибка получения списка файлов {path}: {e}")
            return []
        except Exception as e:
            self.logger.error(f"Неожиданная ошибка при получении списка: {e}")
            return []

    async def delete_file(self, remote_path: str, permanently: bool = False) -> bool:
        try:
            loop = asyncio.get_event_loop()
            # Добавляем таймаут 30 секунд для удаления файлов
            await asyncio.wait_for(
                loop.run_in_executor(None, self._remove, remote_path, permanently),  # type: ignore[arg-type]
                timeout=30.0
            )
            self.logger.info(f"Файл удален: {remote_path}")
            return True
        except YaDiskError as e:
            self.logger.error(f"Ошибка удаления файла {remote_path}: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Неожиданная ошибка при удалении: {e}")
            return False

    async def remove_file(self, remote_path: str) -> bool:
        """Алиас для delete_file для совместимости с интерфейсом"""
        return await self.delete_file(remote_path, permanently=True)

    async def create_folder(self, path: str) -> bool:
        try:
            # Правильно обрабатываем путь disk:/disk:
            if path.startswith("disk:"):
                path_no_disk = path[5:]  # Убираем только первый disk:
            else:
                path_no_disk = path
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self.client.mkdir, path_no_disk)
            self.logger.info(f"Папка создана: {path_no_disk}")
            return True
        except YaDiskError as e:
            if "already exists" in str(e).lower() or "уже существует" in str(e).lower():
                self.logger.debug(f"Папка уже существует: {path}")
                return True
            self.logger.error(f"Ошибка создания папки {path}: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Неожиданная ошибка при создании папки: {e}")
            return False

    async def get_disk_info(self) -> Optional[Dict[str, Any]]:
        try:
            loop = asyncio.get_event_loop()
            disk_info = await loop.run_in_executor(None, self.client.get_disk_info)
            return {
                "total_space": disk_info.total_space,
                "used_space": disk_info.used_space,
                "free_space": disk_info.total_space - disk_info.used_space,
                "total_space_gb": round(disk_info.total_space / (1024**3), 2),
                "used_space_gb": round(disk_info.used_space / (1024**3), 2),
                "free_space_gb": round((disk_info.total_space - disk_info.used_space) / (1024**3), 2),
            }
        except YaDiskError as e:
            self.logger.error(f"Ошибка получения информации о диске: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Неожиданная ошибка: {e}")
            return None

    async def file_exists(self, remote_path: str) -> bool:
        try:
            loop = asyncio.get_event_loop()
            exists = await loop.run_in_executor(None, self.client.exists, remote_path)
            return exists
        except Exception as e:
            self.logger.error(f"Ошибка проверки существования файла {remote_path}: {e}")
            return False

    async def get_download_url(self, remote_path: str) -> Optional[str]:
        try:
            loop = asyncio.get_event_loop()
            download_info = await loop.run_in_executor(None, self.client.get_download_link, remote_path)
            return download_info
        except Exception as e:
            self.logger.error(f"Ошибка получения ссылки для скачивания {remote_path}: {e}")
            return None

    async def _ensure_directory_exists(self, remote_dir: str):
        """Создаёт каталог remote_dir и все промежуточные каталоги (рекурсивно)."""
        remote_dir_no_disk = remote_dir.replace("disk:", "")
        parts = remote_dir_no_disk.strip("/").split("/")
        current_path = ""
        for part in parts:
            current_path += f"/{part}"
            try:
                await self.create_folder(current_path)
            except Exception:
                pass

    async def ensure_path(self, remote_dir: str) -> None:
        """Обёртка над _ensure_directory_exists для публичного использования."""
        await self._ensure_directory_exists(remote_dir)

    def format_file_size(self, size_bytes: int) -> str:
        if size_bytes == 0:
            return "0 Б"
        size_names = ["Б", "КБ", "МБ", "ГБ", "ТБ"]
        i = 0
        size = float(size_bytes)
        while size >= 1024.0 and i < len(size_names) - 1:
            size /= 1024.0
            i += 1
        return f"{size:.1f} {size_names[i]}"
