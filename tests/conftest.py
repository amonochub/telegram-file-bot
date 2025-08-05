"""
Фикстуры для тестов OCR сервиса
"""

import pytest
import tempfile
import os
from pathlib import Path
from typing import Tuple


@pytest.fixture(autouse=True)
def setup_test_env():
    """Устанавливаем переменные окружения для тестов"""
    os.environ["BOT_TOKEN"] = "test_token_12345"
    os.environ["YANDEX_DISK_TOKEN"] = "test_yandex_token"
    os.environ["REDIS_URL"] = "redis://localhost:6379"
    os.environ["LOG_LEVEL"] = "INFO"
    # Не устанавливаем ALLOWED_USER_ID для тестов по умолчанию
    if "ALLOWED_USER_ID" in os.environ:
        del os.environ["ALLOWED_USER_ID"]
    yield


@pytest.fixture
def temp_pdf_file() -> Path:
    """Создает временный PDF файл для тестов"""
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        test_pdf = Path(tmp.name)
    yield test_pdf
    if test_pdf.exists():
        test_pdf.unlink()


@pytest.fixture
def mock_ocr_service(mocker):
    """Мокирует OCR сервис и файловые операции"""
    mock_ocr = mocker.patch("app.services.ocr_service.ocrmypdf.ocr", create=True)
    mocker.patch("pathlib.Path.exists", return_value=True)
    mocker.patch("pathlib.Path.read_text", return_value="test text")
    return mock_ocr


@pytest.fixture
def mock_file_operations(mocker):
    """Автоматически мокирует файловые операции для всех тестов"""
    mocker.patch("pathlib.Path.exists", return_value=True)
    mocker.patch("pathlib.Path.read_text", return_value="test text")


@pytest.fixture(scope="session")
def ocr_test_data() -> dict:
    """Создает тестовые данные для всех OCR тестов"""
    return {
        "sample_text": "test text",
        "expected_params": {
            'language': 'rus+eng',
            'skip_text': True,
            'deskew': False,
            'rotate_pages': False,
            'remove_background': False,
            'progress_bar': False,
            'output_type': 'pdf'
        },
        "fallback_params": {
            'language': 'rus+eng',
            'force_ocr': True,
            'deskew': False,
            'rotate_pages': False,
            'remove_background': False,
            'progress_bar': False,
            'output_type': 'pdf'
        }
    }


@pytest.fixture
def mock_logging(mocker):
    """Мокирует логирование для тестов"""
    return mocker.patch("app.services.ocr_service.log")


@pytest.fixture
def mock_asyncio_loop(mocker):
    """Мокирует asyncio event loop для асинхронных тестов"""
    mock_loop = mocker.MagicMock()
    mocker.patch("asyncio.get_event_loop", return_value=mock_loop)
    return mock_loop
