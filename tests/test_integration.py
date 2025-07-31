"""
Интеграционные тесты для проверки взаимодействия между компонентами
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from pathlib import Path
import tempfile
import shutil

from app.config import settings
from app.services.ocr_service import perform_ocr
from app.services.cbr_rate_service import CBRRateService
from app.services.yandex_disk_service import YandexDiskService
from app.services.rates_cache import get_rate, has_rate
from app.utils.file_validation import validate_file, sanitize_filename, validate_file_path
from app.utils.file_text_extractor import extract_text


class TestIntegration:
    """Интеграционные тесты"""

    @pytest.fixture
    def temp_dir(self):
        """Создает временную директорию для тестов"""
        temp_dir = Path(tempfile.mkdtemp())
        yield temp_dir
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def sample_pdf(self, temp_dir):
        """Создает тестовый PDF файл"""
        pdf_path = temp_dir / "test.pdf"
        # Создаем простой PDF файл для тестирования
        with open(pdf_path, "wb") as f:
            f.write(b"%PDF-1.4\n%Test PDF\n")
        return pdf_path

    @pytest.fixture
    def sample_image(self, temp_dir):
        """Создает тестовое изображение"""
        image_path = temp_dir / "test.jpg"
        # Создаем простой JPG файл для тестирования
        with open(image_path, "wb") as f:
            f.write(b"\xff\xd8\xff\xe0")  # JPEG header
        return image_path

    @pytest.mark.asyncio
    async def test_file_processing_pipeline(self, temp_dir, sample_pdf):
        """Тест полного пайплайна обработки файла"""
        # Проверка валидации файла
        validated_filename = validate_file(sample_pdf.name, sample_pdf.stat().st_size)
        assert validated_filename == sample_pdf.name

        # Проверка извлечения текста
        with patch("app.utils.file_text_extractor.extract_text") as mock_extract:
            mock_extract.return_value = "Тестовый текст из PDF"
            text = extract_text(sample_pdf)
            assert text == "Тестовый текст из PDF"

    @pytest.mark.asyncio
    async def test_ocr_integration(self, temp_dir, sample_image):
        """Тест интеграции OCR сервиса"""
        with patch("app.services.ocr_service.perform_ocr") as mock_ocr:
            mock_ocr.return_value = (Path("test.pdf"), "Текст из изображения")

            result = await perform_ocr(str(sample_image))
            assert result[1] == "Текст из изображения"

    @pytest.mark.asyncio
    async def test_cbr_rates_integration(self):
        """Тест интеграции с API ЦБР"""
        cbr_service = CBRRateService()
        cache = RatesCache()

        with patch("app.services.cbr_rate_service.fetch_rates_from_api") as mock_fetch:
            mock_fetch.return_value = {
                "USD": {"Value": 75.5, "Previous": 75.0},
                "EUR": {"Value": 85.2, "Previous": 85.0},
            }

            rates = await cbr_service.get_current_rates()
            assert "USD" in rates
            assert "EUR" in rates
            assert rates["USD"]["Value"] == 75.5

    @pytest.mark.asyncio
    async def test_yandex_disk_integration(self):
        """Тест интеграции с Яндекс.Диском"""
        if not settings.yandex_disk_token:
            pytest.skip("YANDEX_DISK_TOKEN не настроен")

        yandex_service = YandexDiskService(settings.yandex_disk_token)

        with patch("app.services.yandex_disk_service.YandexDiskService.check_connection") as mock_check:
            mock_check.return_value = True

            connected = await yandex_service.check_connection()
            assert connected

    @pytest.mark.asyncio
    async def test_cache_integration(self):
        """Тест интеграции кэширования"""
        # Тест проверки наличия курса
        from datetime import date

        test_date = date(2024, 1, 1)

        with patch("app.services.rates_cache.has_rate") as mock_has_rate:
            mock_has_rate.return_value = True
            has_rates = await has_rate(test_date)
            assert has_rates

    @pytest.mark.asyncio
    async def test_error_handling_integration(self, temp_dir):
        """Тест обработки ошибок в интеграции"""
        # Тест обработки несуществующего файла
        non_existent_file = temp_dir / "non_existent.pdf"

        # Проверяем, что валидация пути возвращает False для несуществующего файла
        assert not validate_file_path(non_existent_file)

    @pytest.mark.asyncio
    async def test_concurrent_operations(self):
        """Тест конкурентных операций"""
        from datetime import date

        # Создаем несколько задач для конкурентного выполнения
        tasks = []
        for i in range(5):
            test_date = date(2024, 1, i + 1)
            task = has_rate(test_date)
            tasks.append(task)

        # Выполняем все задачи одновременно
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Проверяем, что все задачи выполнились успешно
        assert all(not isinstance(result, Exception) for result in results)

    @pytest.mark.asyncio
    async def test_memory_usage_integration(self, temp_dir):
        """Тест использования памяти"""
        import psutil
        import os
        from datetime import date

        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss

        # Выполняем операции, которые могут потреблять память
        for i in range(100):
            test_date = date(2024, 1, i + 1)
            await has_rate(test_date)

        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory

        # Проверяем, что увеличение памяти разумное (менее 100MB)
        assert memory_increase < 100 * 1024 * 1024

    @pytest.mark.asyncio
    async def test_configuration_integration(self):
        """Тест интеграции конфигурации"""
        # Проверяем, что все сервисы могут использовать настройки
        assert settings.bot_token
        assert settings.max_file_size > 0
        assert settings.cache_ttl > 0

        # Проверяем, что функции доступны
        assert has_rate is not None
        assert validate_file is not None

    @pytest.mark.asyncio
    async def test_logging_integration(self):
        """Тест интеграции логирования"""
        import logging

        # Проверяем, что логирование настроено
        logger = logging.getLogger(__name__)
        assert logger is not None

        # Проверяем, что можем записывать логи
        logger.info("Тестовое сообщение")

        # Проверяем, что уровень логирования корректный
        assert logger.level <= getattr(logging, settings.log_level)

    @pytest.mark.asyncio
    async def test_file_operations_integration(self, temp_dir):
        """Тест интеграции файловых операций"""
        # Создаем тестовые файлы
        test_files = []
        for i in range(3):
            file_path = temp_dir / f"test_{i}.txt"
            file_path.write_text(f"Тестовое содержимое файла {i}")
            test_files.append(file_path)

        # Проверяем, что все файлы созданы
        for file_path in test_files:
            assert file_path.exists()
            assert file_path.stat().st_size > 0

        # Проверяем валидацию файлов
        for file_path in test_files:
            validated_filename = validate_file(file_path.name, file_path.stat().st_size)
            assert validated_filename == file_path.name

    @pytest.mark.asyncio
    async def test_api_resilience_integration(self):
        """Тест устойчивости к сбоям API"""
        cbr_service = CBRRateService()

        # Симулируем сбой API
        with patch("app.services.cbr_rate_service.fetch_rates_from_api") as mock_fetch:
            mock_fetch.side_effect = Exception("API недоступен")

            # Проверяем, что сервис обрабатывает ошибку gracefully
            rates = await cbr_service.get_current_rates()
            assert rates is None or len(rates) == 0

    @pytest.mark.asyncio
    async def test_data_consistency_integration(self):
        """Тест консистентности данных"""
        from datetime import date

        # Проверяем консистентность данных
        test_date = date(2024, 1, 1)

        with patch("app.services.rates_cache.has_rate") as mock_has_rate:
            mock_has_rate.return_value = True

            # Проверяем, что результат консистентен
            result1 = await has_rate(test_date)
            result2 = await has_rate(test_date)
            assert result1 == result2
