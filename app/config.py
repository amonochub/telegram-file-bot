"""
Конфигурация приложения
"""
import os
from typing import Optional
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
    allowed_user_id: Optional[int] = Field(None, validation_alias="ALLOWED_USER_ID")
    
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
