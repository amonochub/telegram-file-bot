import pytest
from app.config import Settings


def test_allowed_user_ids_empty():
    """Тест проверки allowed_user_ids с пустым значением"""
    settings = Settings(_env_file=None, bot_token="test", allowed_user_id="")
    assert settings.allowed_user_ids == []
    assert settings.allowed_user_id_int is None


def test_is_user_allowed_empty_list():
    """Тест проверки is_user_allowed с пустым списком (доступ всем)"""
    settings = Settings(_env_file=None, bot_token="test", allowed_user_id="")
    assert settings.is_user_allowed(123) == True
    assert settings.is_user_allowed(456) == True 