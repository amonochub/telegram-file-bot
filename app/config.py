"""
Конфигурация приложения
"""
import os
from typing import Optional, List
from pydantic import Field
from pydantic_settings import BaseSettings
import logging

# Константы для Яндекс.Диска
YANDEX_ROOT_PATH = os.getenv("YANDEX_ROOT_PATH", "disk:/1-Sh23SGxNjxYQ")
USER_FILES_DIR = YANDEX_ROOT_PATH

class Settings(BaseSettings):
    """Настройки приложения"""
    
    # Bot
    bot_token: str = Field(..., validation_alias="BOT_TOKEN")
    allowed_user_id: Optional[str] = Field(None, validation_alias="ALLOWED_USER_ID")
    
    @property
    def allowed_user_ids(self) -> List[int]:
        """Возвращает список разрешенных ID пользователей"""
        if not self.allowed_user_id or self.allowed_user_id.strip() == "":
            return []
        
        try:
            # Разделяем по запятой и убираем пробелы
            user_ids = [int(uid.strip()) for uid in self.allowed_user_id.split(",") if uid.strip()]
            return user_ids
        except (ValueError, TypeError):
            return []
    
    @property
    def allowed_user_id_int(self) -> Optional[int]:
        """Возвращает первый allowed_user_id как целое число или None (для обратной совместимости)"""
        user_ids = self.allowed_user_ids
        return user_ids[0] if user_ids else None
    
    def is_user_allowed(self, user_id: int) -> bool:
        """Проверяет, разрешен ли доступ пользователю"""
        if not self.allowed_user_ids:  # Если список пустой - доступ разрешен всем
            return True
        return user_id in self.allowed_user_ids
    
    # Yandex.Disk
    yandex_disk_token: Optional[str] = Field(None, validation_alias="YANDEX_DISK_TOKEN")
    yandex_root_path: str = Field("disk:/disk:", validation_alias="YANDEX_ROOT_PATH")
    
    # Upload directory
    upload_dir: str = Field("/bot_files", validation_alias="UPLOAD_DIR")
    temp_dir: str = Field("temp", validation_alias="TEMP_DIR")
    max_file_size: int = Field(100_000_000, validation_alias="MAX_FILE_SIZE")
    
    # Redis
    redis_url: str = Field("redis://localhost:6379", validation_alias="REDIS_URL")
    cache_ttl: int = Field(3600, validation_alias="CACHE_TTL")
    max_buffer_size: int = Field(100, validation_alias="MAX_BUFFER_SIZE")
    
    # CBR API
    cbr_api_url: str = Field("https://www.cbr-xml-daily.ru/daily_json.js", validation_alias="CBR_API_URL")
    
    # Logging
    log_level: str = Field("INFO", validation_alias="LOG_LEVEL")
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"  # Игнорируем лишние переменные

# Создаем экземпляр настроек
settings = Settings(_env_file=".env")
