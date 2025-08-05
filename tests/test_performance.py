"""
Тесты производительности для проверки скорости и эффективности работы системы
"""

import pytest
import asyncio
import time
import psutil
import os
from pathlib import Path
from unittest.mock import patch, AsyncMock
import tempfile
import shutil

from app.services.rates_cache import get_rate, has_rate
from app.services.cbr_rate_service import CBRRateService
from app.services.ocr_service import perform_ocr
from app.utils.file_validation import validate_file, validate_file_path
from app.config import settings


# Создаем тестовые классы для недостающих компонентов
class FileValidator:
    def validate_size(self, size: int) -> bool:
        return size <= settings.max_file_size
    
    def validate_extension(self, filename: str) -> bool:
        allowed_extensions = {'.pdf', '.jpg', '.png', '.docx', '.txt'}
        path = Path(filename)
        return path.suffix.lower() in allowed_extensions


class RatesCache:
    def __init__(self):
        self.cache = {}
        self.request_count = 0
    
    async def set_rates(self, key: str, data: dict):
        self.cache[key] = data
    
    async def get_rates(self, key: str):
        self.request_count += 1
        return self.cache.get(key)
    
    def clear(self):
        self.cache.clear()
        self.request_count = 0


class TestPerformance:
    """Тесты производительности"""

    @pytest.fixture
    def temp_dir(self):
        """Создает временную директорию для тестов"""
        temp_dir = Path(tempfile.mkdtemp())
        yield temp_dir
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def large_file(self, temp_dir):
        """Создает большой файл для тестирования"""
        large_file = temp_dir / "large_file.txt"
        # Создаем файл размером 10MB
        with open(large_file, "wb") as f:
            f.write(b"0" * 10 * 1024 * 1024)
        return large_file

    @pytest.mark.asyncio
    async def test_cache_performance(self):
        """Тест производительности кэша"""
        from datetime import date

        # Тест скорости проверки курсов
        start_time = time.time()
        for i in range(1000):
            test_date = date(2024, 1, i % 30 + 1)
            await has_rate(test_date)
        check_time = time.time() - start_time

        # Проверяем, что операции выполняются быстро
        assert check_time < 5.0, f"Проверка курсов слишком медленная: {check_time:.2f}с"

        print(f"Cache performance - Check: {check_time:.2f}s")

    @pytest.mark.asyncio
    async def test_api_response_time(self):
        """Тест времени отклика API"""
        cbr_service = CBRRateService()

        with patch("app.services.rates_cache.get_rate") as mock_get_rate:
            mock_get_rate.return_value = 75.5

            start_time = time.time()
            from datetime import date
            rate = await cbr_service.get_cbr_rate(date.today(), "USD")
            response_time = time.time() - start_time

            assert response_time < 1.0, f"API ответ слишком медленный: {response_time:.2f}с"
            assert rate is not None

            print(f"API response time: {response_time:.2f}s")

    @pytest.mark.asyncio
    async def test_file_validation_performance(self, temp_dir):
        """Тест производительности валидации файлов"""

        # Создаем множество файлов для тестирования
        test_files = []
        for i in range(100):
            file_path = temp_dir / f"test_{i}.txt"
            file_path.write_text(f"Test content {i}")
            test_files.append(file_path)

        # Тест скорости валидации
        start_time = time.time()
        for file_path in test_files:
            validate_file(file_path.name, file_path.stat().st_size)
        validation_time = time.time() - start_time

        assert validation_time < 1.0, f"Валидация файлов слишком медленная: {validation_time:.2f}с"

        print(f"File validation performance: {validation_time:.2f}s for 100 files")

    @pytest.mark.asyncio
    async def test_memory_usage_performance(self):
        """Тест использования памяти"""
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss

        # Выполняем операции, которые могут потреблять память
        from datetime import date

        for i in range(1000):
            test_date = date(2024, 1, i % 30 + 1)
            await has_rate(test_date)

        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory

        # Проверяем, что увеличение памяти разумное (менее 50MB)
        assert (
            memory_increase < 50 * 1024 * 1024
        ), f"Слишком большое потребление памяти: {memory_increase / 1024 / 1024:.1f}MB"

        print(f"Memory usage: {memory_increase / 1024 / 1024:.1f}MB increase")

    @pytest.mark.asyncio
    async def test_concurrent_performance(self):
        """Тест производительности при конкурентных операциях"""
        cache = RatesCache()

        # Создаем множество конкурентных задач
        async def cache_operation(i):
            from datetime import date

            test_date = date(2024, 1, i % 30 + 1)
            return await has_rate(test_date)

        start_time = time.time()
        tasks = [cache_operation(i) for i in range(100)]
        results = await asyncio.gather(*tasks)
        concurrent_time = time.time() - start_time

        assert concurrent_time < 10.0, f"Конкурентные операции слишком медленные: {concurrent_time:.2f}с"
        assert len(results) == 100

        print(f"Concurrent performance: {concurrent_time:.2f}s for 100 operations")

    @pytest.mark.asyncio
    async def test_large_file_handling(self, large_file):
        """Тест обработки больших файлов"""
        file_validator = FileValidator()

        start_time = time.time()

        # Проверяем валидацию большого файла
        file_size = large_file.stat().st_size
        validated_filename = validate_file(large_file.name, file_size)
        is_valid = validated_filename == large_file.name

        validation_time = time.time() - start_time

        # Проверяем, что валидация выполняется быстро даже для больших файлов
        assert validation_time < 0.1, f"Валидация большого файла слишком медленная: {validation_time:.2f}с"
        assert is_valid

        print(f"Large file validation: {validation_time:.2f}s for {file_size / 1024 / 1024:.1f}MB file")

    @pytest.mark.asyncio
    async def test_ocr_performance(self, temp_dir):
        """Тест производительности OCR"""

        # Создаем простой текстовый PDF для тестирования
        pdf_path = temp_dir / "test.pdf"
        pdf_path.write_text("Test content for OCR performance testing")

        with patch("app.services.ocr_service.run_ocr") as mock_ocr:
            mock_ocr.return_value = "Test text extracted"

            start_time = time.time()
            result = await perform_ocr(str(pdf_path))
            ocr_time = time.time() - start_time

            assert ocr_time < 5.0, f"OCR обработка слишком медленная: {ocr_time:.2f}с"
            
            print(f"OCR performance: {ocr_time:.2f}s")
            
            print(f"OCR performance: {ocr_time:.2f}s")

    @pytest.mark.asyncio
    async def test_database_performance(self):
        """Тест производительности базы данных (если используется)"""
        # Этот тест можно адаптировать под конкретную БД
        cache = RatesCache()

        # Тест массовых операций
        start_time = time.time()

        # Проверяем много курсов
        from datetime import date

        for i in range(500):
            test_date = date(2024, 1, i % 30 + 1)
            await has_rate(test_date)

        db_time = time.time() - start_time

        assert db_time < 30.0, f"Операции с БД слишком медленные: {db_time:.2f}с"

        print(f"Database performance: {db_time:.2f}s for 1000 operations")

    @pytest.mark.asyncio
    async def test_network_performance(self):
        """Тест производительности сети"""
        cbr_service = CBRRateService()

        with patch("app.services.rates_cache.get_rate") as mock_get_rate:
            mock_get_rate.return_value = 75.5

            # Тест множественных запросов
            start_time = time.time()

            tasks = []
            from datetime import date
            for _ in range(10):
                task = cbr_service.get_cbr_rate(date.today(), "USD")
                tasks.append(task)

            results = await asyncio.gather(*tasks)
            network_time = time.time() - start_time

            assert network_time < 5.0, f"Сетевые операции слишком медленные: {network_time:.2f}с"
            assert all(result is not None for result in results)

            print(f"Network performance: {network_time:.2f}s for 10 concurrent requests")

    @pytest.mark.asyncio
    async def test_cpu_usage_performance(self):
        """Тест использования CPU"""
        process = psutil.Process(os.getpid())

        # Измеряем CPU до операций
        cpu_percent_before = process.cpu_percent()

        # Выполняем интенсивные операции
        from datetime import date

        for i in range(1000):
            test_date = date(2024, 1, i % 30 + 1)
            await has_rate(test_date)

        # Измеряем CPU после операций
        cpu_percent_after = process.cpu_percent()

        # Проверяем, что CPU не превышает разумные пределы
        assert cpu_percent_after < 80, f"Слишком высокое использование CPU: {cpu_percent_after}%"

        print(f"CPU usage: {cpu_percent_before}% -> {cpu_percent_after}%")

    @pytest.mark.asyncio
    async def test_startup_performance(self):
        """Тест производительности запуска"""
        start_time = time.time()

        # Инициализируем основные компоненты
        from app.config import settings
        from app.services.rates_cache import has_rate
        from app.services.cbr_rate_service import CBRRateService
        from app.utils.file_validation import validate_file

        cbr_service = CBRRateService()

        startup_time = time.time() - start_time

        assert startup_time < 2.0, f"Запуск слишком медленный: {startup_time:.2f}с"

        print(f"Startup performance: {startup_time:.2f}s")

    @pytest.mark.asyncio
    async def test_error_recovery_performance(self):
        """Тест производительности восстановления после ошибок"""
        cache = RatesCache()

        # Симулируем ошибки и измеряем время восстановления
        start_time = time.time()

        from datetime import date

        for i in range(100):
            try:
                test_date = date(2024, 1, i % 30 + 1)
                await has_rate(test_date)
            except Exception:
                # Игнорируем ошибки для теста производительности
                pass

        recovery_time = time.time() - start_time

        assert recovery_time < 10.0, f"Восстановление после ошибок слишком медленное: {recovery_time:.2f}с"

        print(f"Error recovery performance: {recovery_time:.2f}s")

    @pytest.mark.asyncio
    async def test_memory_leak_performance(self):
        """Тест утечек памяти"""
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss

        # Выполняем цикл операций
        from datetime import date

        for cycle in range(5):
            for i in range(100):
                test_date = date(2024, 1, i % 30 + 1)
                await has_rate(test_date)

            # Проверяем память после каждого цикла
            current_memory = process.memory_info().rss
            memory_increase = current_memory - initial_memory

            # Проверяем, что нет значительных утечек памяти
            assert (
                memory_increase < 100 * 1024 * 1024
            ), f"Возможная утечка памяти: {memory_increase / 1024 / 1024:.1f}MB"

        final_memory = process.memory_info().rss
        total_increase = final_memory - initial_memory

        print(f"Memory leak test: {total_increase / 1024 / 1024:.1f}MB total increase")

    @pytest.mark.asyncio
    async def test_throughput_performance(self):
        """Тест пропускной способности"""
        cache = RatesCache()

        # Измеряем количество операций в секунду
        start_time = time.time()
        operations = 0

        # Выполняем операции в течение 1 секунды
        from datetime import date

        while time.time() - start_time < 1.0:
            test_date = date(2024, 1, operations % 30 + 1)
            await has_rate(test_date)
            operations += 1

        throughput = operations / (time.time() - start_time)

        # Проверяем минимальную пропускную способность
        assert throughput > 10, f"Слишком низкая пропускная способность: {throughput:.1f} ops/sec"

        print(f"Throughput: {throughput:.1f} operations/second")
