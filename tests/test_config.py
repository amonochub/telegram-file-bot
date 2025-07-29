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


def test_allowed_user_ids_empty():
    """Тест проверки allowed_user_ids с пустым значением"""
    settings = Settings(_env_file=None, bot_token="test", allowed_user_id="")
    assert settings.allowed_user_ids == []
    assert settings.allowed_user_id_int is None


def test_allowed_user_ids_single():
    """Тест проверки allowed_user_ids с одним пользователем"""
    settings = Settings(_env_file=None, bot_token="test", allowed_user_id="123")
    assert settings.allowed_user_ids == [123]
    assert settings.allowed_user_id_int == 123


def test_allowed_user_ids_multiple():
    """Тест проверки allowed_user_ids с несколькими пользователями"""
    settings = Settings(_env_file=None, bot_token="test", allowed_user_id="123,456,789")
    assert settings.allowed_user_ids == [123, 456, 789]
    assert settings.allowed_user_id_int == 123


def test_allowed_user_ids_with_spaces():
    """Тест проверки allowed_user_ids с пробелами"""
    settings = Settings(_env_file=None, bot_token="test", allowed_user_id=" 123 , 456 , 789 ")
    assert settings.allowed_user_ids == [123, 456, 789]


def test_is_user_allowed_empty_list():
    """Тест проверки is_user_allowed с пустым списком (доступ всем)"""
    settings = Settings(_env_file=None, bot_token="test", allowed_user_id="")
    assert settings.is_user_allowed(123) == True
    assert settings.is_user_allowed(456) == True


def test_is_user_allowed_single_user():
    """Тест проверки is_user_allowed с одним пользователем"""
    settings = Settings(_env_file=None, bot_token="test", allowed_user_id="123")
    assert settings.is_user_allowed(123) == True
    assert settings.is_user_allowed(456) == False


def test_is_user_allowed_multiple_users():
    """Тест проверки is_user_allowed с несколькими пользователями"""
    settings = Settings(_env_file=None, bot_token="test", allowed_user_id="123,456,789")
    assert settings.is_user_allowed(123) == True
    assert settings.is_user_allowed(456) == True
    assert settings.is_user_allowed(789) == True
    assert settings.is_user_allowed(999) == False 