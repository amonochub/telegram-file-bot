import pytest
from app.config import Settings


def test_settings_from_env(monkeypatch):
    """Тест загрузки настроек из переменных окружения"""
    # Устанавливаем переменные окружения
    monkeypatch.setenv("BOT_TOKEN", "test_bot_token")
    monkeypatch.setenv("YANDEX_DISK_TOKEN", "test_yandex_token")
    monkeypatch.setenv("UPLOAD_DIR", "/test_upload")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    
    # Создаем новый экземпляр настроек с обязательным bot_token
    settings = Settings(_env_file=None, bot_token="test_bot_token")
    
    assert settings.bot_token == "test_bot_token"
    assert settings.yandex_disk_token == "test_yandex_token"
    assert settings.upload_dir == "/test_upload"
    assert settings.log_level == "DEBUG"


def test_settings_override_from_env(monkeypatch):
    """Тест переопределения настроек переменными окружения"""
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    
    settings = Settings(_env_file=None, bot_token="test_token")
    assert settings.log_level == "DEBUG"


def test_allowed_user_id_int():
    """Тест проверки allowed_user_id_int"""
    # Тест с пустым значением
    settings = Settings(_env_file=None, bot_token="test", allowed_user_id="")
    assert settings.allowed_user_id_int is None
    
    # Тест с числовым значением
    settings = Settings(_env_file=None, bot_token="test", allowed_user_id="123")
    assert settings.allowed_user_id_int == 123
    
    # Тест с None
    settings = Settings(_env_file=None, bot_token="test", allowed_user_id=None)
    assert settings.allowed_user_id_int is None 