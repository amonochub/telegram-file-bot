"""Тесты для конфигурации приложения."""

import pytest
from unittest.mock import patch
from app.config import Settings


class TestSettings:
    """Тесты для класса Settings."""

    def test_allowed_user_ids_empty(self):
        """Тест пустого списка разрешенных пользователей."""
        with patch.dict('os.environ', {'BOT_TOKEN': 'test_token'}):
            settings = Settings()
            assert settings.allowed_user_ids == []

    def test_is_user_allowed_empty_list(self):
        """Тест проверки доступа при пустом списке (доступ всем)."""
        with patch.dict('os.environ', {'BOT_TOKEN': 'test_token'}):
            settings = Settings()
            assert settings.is_user_allowed(123) is True
            assert settings.is_user_allowed(456) is True

    def test_default_values(self):
        """Тест значений по умолчанию."""
        with patch.dict('os.environ', {'BOT_TOKEN': 'test_token'}):
            settings = Settings()
            assert settings.redis_url == "redis://localhost:6379"
            assert settings.log_level == "INFO"
            assert settings.max_file_size == 100_000_000
            assert settings.cache_ttl == 3600
            assert settings.max_buffer_size == 100
            assert settings.cbr_api_url == "https://www.cbr-xml-daily.ru/daily_json.js"
            assert settings.yandex_root_path == "disk:/1-Sh23SGxNjxYQ"

    def test_upload_dir_path(self):
        """Тест получения upload_dir как Path."""
        with patch.dict('os.environ', {'BOT_TOKEN': 'test_token'}):
            settings = Settings()
            assert str(settings.upload_dir_path) == '/bot_files'

    def test_temp_dir_path(self):
        """Тест получения temp_dir как Path."""
        with patch.dict('os.environ', {'BOT_TOKEN': 'test_token'}):
            settings = Settings()
            assert str(settings.temp_dir_path) == 'temp'
