"""
Конфигурация приложения
"""

import os
from typing import Optional, List, Union
from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings
import logging

from app.utils.types import UserId, FileSize

# Константы для Яндекс.Диска
YANDEX_ROOT_PATH = os.getenv("YANDEX_ROOT_PATH", "disk:/1-Sh23SGxNjxYQ")
USER_FILES_DIR = YANDEX_ROOT_PATH


class Settings(BaseSettings):
    """Настройки приложения"""

    # Настройка для загрузки .env файла
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    # Bot
    bot_token: str = Field(default="", validation_alias="BOT_TOKEN")
    allowed_user_id: Optional[str] = Field(None, validation_alias="ALLOWED_USER_ID")

    @property
    def allowed_user_ids(self) -> List[UserId]:
        """Возвращает список разрешенных ID пользователей"""
        if not self.allowed_user_id or self.allowed_user_id.strip() == "":
            return []

        try:
            # Разделяем по запятой и убираем пробелы
            user_ids = [UserId(int(uid.strip())) for uid in self.allowed_user_id.split(",") if uid.strip()]
            return user_ids
        except (ValueError, TypeError):
            return []

    @property
    def allowed_user_id_int(self) -> Optional[UserId]:
        """Возвращает первый allowed_user_id как целое число или None (для обратной совместимости)"""
        user_ids = self.allowed_user_ids
        return user_ids[0] if user_ids else None

    def is_user_allowed(self, user_id: int) -> bool:
        """Проверяет, разрешен ли доступ пользователю"""
        if not self.allowed_user_ids:  # Если список пустой - доступ запрещен всем
            logging.warning(
                "SECURITY WARNING: No allowed users specified in ALLOWED_USER_ID. "
                "Access denied by default. Set ALLOWED_USER_ID for production use."
            )
            return False  # По умолчанию запрещаем доступ для безопасности
        return UserId(user_id) in self.allowed_user_ids

    # Yandex.Disk
    yandex_disk_token: Optional[str] = Field(None, validation_alias="YANDEX_DISK_TOKEN")

    # Redis
    redis_url: str = Field("redis://localhost:6379", validation_alias="REDIS_URL")

    # Logging
    log_level: str = Field("INFO", validation_alias="LOG_LEVEL")

    # File upload
    max_file_size: int = Field(100_000_000, validation_alias="MAX_FILE_SIZE")  # 100MB
    upload_dir: str = Field("/bot_files", validation_alias="UPLOAD_DIR")
    temp_dir: str = Field("temp", validation_alias="TEMP_DIR")

    @property
    def upload_dir_path(self) -> Path:
        """Возвращает upload_dir как Path объект"""
        return Path(self.upload_dir)

    @property
    def temp_dir_path(self) -> Path:
        """Возвращает temp_dir как Path объект"""
        return Path(self.temp_dir)

    # Cache
    cache_ttl: int = Field(3600, validation_alias="CACHE_TTL")  # 1 hour
    max_buffer_size: int = Field(100, validation_alias="MAX_BUFFER_SIZE")

    # CBR API
    cbr_api_url: str = Field("https://www.cbr-xml-daily.ru/daily_json.js", validation_alias="CBR_API_URL")

    # Yandex.Disk root path
    yandex_root_path: str = Field("disk:/1-Sh23SGxNjxYQ", validation_alias="YANDEX_ROOT_PATH")

    # Gemini API
    gemini_api_key: Optional[str] = Field(None, validation_alias="GEMINI_API_KEY")


# Создаем глобальный экземпляр настроек через функцию для lazy initialization
# Это предотвращает ValidationError при импорте модуля без переменных окружения
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """
    Получает экземпляр настроек с lazy initialization.
    Создает настройки только при первом обращении.
    """
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


# Для обратной совместимости создаем свойство settings
class SettingsProxy:
    def __getattr__(self, name):
        return getattr(get_settings(), name)


# Создаем экземпляр прокси для обратной совместимости
settings = SettingsProxy()
