import pytest
from app.config import Settings


def test_settings_from_env(monkeypatch):
    """Тест загрузки настроек из переменных окружения"""
    monkeypatch.setenv("BOT_TOKEN", "test_bot_token")
    monkeypatch.setenv("YANDEX_DISK_TOKEN", "test_yandex_token")
    monkeypatch.setenv("GEMINI_API_KEY", "test_gemini_key")
    monkeypatch.setenv("UPLOAD_DIR", "/test_upload")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    
    settings = Settings()
    
    assert settings.bot_token == "test_bot_token"
    assert settings.yandex_disk_token == "test_yandex_token"
    assert settings.gemini_api_key == "test_gemini_key"
    assert settings.upload_dir == "/test_upload"
    assert settings.log_level == "DEBUG"


def test_settings_override_from_env(monkeypatch):
    """Тест переопределения настроек переменными окружения"""
    monkeypatch.setenv("GEMINI_API_KEY", "env_gemini_key")
    
    settings = Settings()
    assert settings.gemini_api_key == "env_gemini_key"


def test_has_ai_support():
    """Тест проверки поддержки ИИ"""
    settings = Settings()
    assert settings.has_ai_support == (settings.gemini_api_key is not None) 