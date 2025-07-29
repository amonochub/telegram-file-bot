"""
Конфигурация приложения с валидацией и окружением.
"""
import os
from typing import List, Optional

import structlog
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

log = structlog.get_logger(__name__)

# Константы для Яндекс.Диска
YANDEX_ROOT_PATH = os.getenv("YANDEX_ROOT_PATH", "disk:/1-Sh23SGxNjxYQ")
USER_FILES_DIR = YANDEX_ROOT_PATH


class Settings(BaseSettings):
    """Настройки приложения с валидацией"""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

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

    # Redis
    redis_url: str = Field("redis://localhost:6379", validation_alias="REDIS_URL")

    # Logging
    log_level: str = Field("INFO", validation_alias="LOG_LEVEL")

    # File upload
    max_file_size: int = Field(100_000_000, validation_alias="MAX_FILE_SIZE")  # 100MB
    upload_dir: str = Field("/bot_files", validation_alias="UPLOAD_DIR")
    temp_dir: str = Field("temp", validation_alias="TEMP_DIR")

    # Cache
    cache_ttl: int = Field(3600, validation_alias="CACHE_TTL")  # 1 hour
    max_buffer_size: int = Field(100, validation_alias="MAX_BUFFER_SIZE")

    # CBR API
    cbr_api_url: str = Field("https://www.cbr-xml-daily.ru/daily_json.js", validation_alias="CBR_API_URL")

    # Yandex.Disk root path
    yandex_root_path: str = Field("disk:/1-Sh23SGxNjxYQ", validation_alias="YANDEX_ROOT_PATH")

    @field_validator("bot_token")
    @classmethod
    def validate_bot_token(cls, v: str) -> str:
        """Validate bot token format."""
        if not v or len(v) < 45:
            raise ValueError("Bot token must be at least 45 characters")
        if ":" not in v:
            raise ValueError("Bot token must contain ':'")
        return v

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level."""
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if v.upper() not in valid_levels:
            raise ValueError(f"Log level must be one of: {valid_levels}")
        return v.upper()

    @field_validator("max_file_size")
    @classmethod
    def validate_file_size(cls, v: int) -> int:
        """Validate max file size."""
        if v <= 0:
            raise ValueError("Max file size must be positive")
        if v > 1_000_000_000:  # 1GB
            raise ValueError("Max file size cannot exceed 1GB")
        return v

    @property
    def is_development(self) -> bool:
        """Check if running in development mode."""
        return self.log_level == "DEBUG"

    def validate_configuration(self) -> None:
        """Validate the entire configuration and log warnings."""
        warnings = []

        # Check Yandex.Disk token
        if not self.yandex_disk_token:
            warnings.append("Yandex.Disk token not set - file operations will be disabled")

        # Check allowed users
        if not self.allowed_user_ids:
            warnings.append("No allowed users configured - bot is open to all users")

        # Log warnings
        for warning in warnings:
            log.warning("Configuration warning", message=warning)


def create_settings() -> Settings:
    """Create and validate settings."""
    try:
        settings = Settings()
        settings.validate_configuration()
        return settings
    except Exception as e:
        log.error("Failed to load configuration", error=str(e))
        raise


# Создаем глобальный экземпляр настроек
settings = create_settings()
