"""Система локализации для Telegram File Bot."""

import tomllib
import importlib.resources
from typing import Dict, Any
import structlog

logger = structlog.get_logger(__name__)

# Кэш для загруженных языков
_cache: Dict[str, Dict[str, Any]] = {}


def load_lang(lang: str) -> Dict[str, Any]:
    """Загружает языковой файл из TOML."""
    if lang in _cache:
        return _cache[lang]

    try:
        # Загружаем файл из пакета
        data = importlib.resources.files(__package__).joinpath(f"{lang}.toml").read_bytes()
        _cache[lang] = tomllib.loads(data.decode())
        logger.debug("language_loaded", lang=lang)
        return _cache[lang]
    except Exception as e:
        logger.error("failed_to_load_language", lang=lang, error=str(e))
        # Fallback к русскому языку
        if lang != "ru":
            return load_lang("ru")
        return {}


def t(key: str, lang: str = "ru") -> str:
    """
    Получает локализованную строку по ключу.

    Args:
        key: Ключ в формате "section.key" (например, "common.start_welcome")
        lang: Код языка (ru, en)

    Returns:
        Локализованная строка или ключ, если строка не найдена
    """
    parts = key.split(".")
    node = load_lang(lang)

    for part in parts:
        if isinstance(node, dict):
            node = node.get(part, {})
        else:
            break

    if isinstance(node, str):
        return node

    # Если строка не найдена, возвращаем ключ
    logger.warning("translation_not_found", key=key, lang=lang)
    return key


def clear_cache() -> None:
    """Очищает кэш локализации."""
    _cache.clear()
    logger.info("translation_cache_cleared")


def get_available_languages() -> list[str]:
    """Возвращает список доступных языков."""
    return ["ru", "en"]
