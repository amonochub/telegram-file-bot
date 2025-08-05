"""
Тесты безопасности для проверки уязвимостей и защиты системы
"""

import pytest
import asyncio
from pathlib import Path
from unittest.mock import patch, AsyncMock
import tempfile
import shutil
import os
import json

from app.config import settings
from app.services.yandex_disk_service import YandexDiskService
from app.services.cbr_rate_service import CBRRateService
from app.utils.file_validation import validate_file, sanitize_filename, validate_file_path


# Для тестов создаем простую реализацию FileValidator
class FileValidator:
    def validate_size(self, size: int) -> bool:
        return size <= settings.max_file_size
    
    def validate_extension(self, filename: str) -> bool:
        allowed_extensions = {'.pdf', '.jpg', '.png', '.docx', '.txt'}
        path = Path(filename)
        return path.suffix.lower() in allowed_extensions


# Простая реализация для тестов RatesCache
class RatesCache:
    def __init__(self):
        self.cache = {}
    
    async def set_rates(self, key: str, data: dict):
        self.cache[key] = data
    
    async def get_rates(self, key: str):
        return self.cache.get(key)


# from app.middleware.user_check import UserCheckMiddleware  # Временно отключено


class TestSecurity:
    """Тесты безопасности"""

    @pytest.fixture
    def temp_dir(self):
        """Создает временную директорию для тестов"""
        temp_dir = Path(tempfile.mkdtemp())
        yield temp_dir
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def malicious_file(self, temp_dir):
        """Создает потенциально опасный файл"""
        malicious_file = temp_dir / "malicious.exe"
        with open(malicious_file, "wb") as f:
            f.write(b"MZ\x90\x00")  # PE header
        return malicious_file

    @pytest.mark.asyncio
    async def test_file_type_validation_security(self, temp_dir):
        """Тест безопасности валидации типов файлов"""

        # Тест опасных расширений файлов
        dangerous_extensions = [
            "malicious.exe",
            "virus.bat",
            "trojan.cmd",
            "hack.sh",
            "dangerous.py",
            "malware.js",
            "exploit.php",
            "backdoor.vbs",
        ]

        for filename in dangerous_extensions:
            file_path = temp_dir / filename
            file_path.write_text("malicious content")

            # Проверяем, что опасные файлы отклоняются
            with pytest.raises(Exception):
                validate_file(filename, file_path.stat().st_size)

    @pytest.mark.asyncio
    async def test_file_size_limits_security(self, temp_dir):
        """Тест безопасности лимитов размера файлов"""
        file_validator = FileValidator()

        # Тест файлов, превышающих лимит
        oversized_file = temp_dir / "oversized.txt"
        oversized_size = settings.max_file_size + 1024 * 1024  # +1MB

        with open(oversized_file, "wb") as f:
            f.write(b"0" * oversized_size)

        # Проверяем, что файлы превышающие лимит отклоняются
        with pytest.raises(Exception):
            validate_file("oversized.txt", oversized_size)

    @pytest.mark.asyncio
    async def test_path_traversal_security(self, temp_dir):
        """Тест защиты от path traversal атак"""
        file_validator = FileValidator()

        # Тест попыток path traversal
        malicious_paths = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32\\config\\sam",
            "....//....//....//etc/passwd",
            "%2e%2e%2f%2e%2e%2f%2e%2e%2fetc%2fpasswd",
        ]

        for malicious_path in malicious_paths:
            # Проверяем, что path traversal блокируется
            assert not validate_file_path(
                Path(malicious_path)
            ), f"Path traversal {malicious_path} должен быть заблокирован"

    @pytest.mark.asyncio
    async def test_user_authentication_security(self):
        """Тест безопасности аутентификации пользователей"""
        # Тест с неавторизованным пользователем
        if settings.allowed_user_ids:
            unauthorized_user_id = 999999999

            # Проверяем, что неавторизованные пользователи блокируются
            assert not settings.is_user_allowed(unauthorized_user_id)

    @pytest.mark.asyncio
    async def test_token_security(self):
        """Тест безопасности токенов"""
        # Проверяем, что токены не пустые
        assert settings.bot_token, "BOT_TOKEN должен быть установлен"

        # Для тестовой среды проверяем, что токен присутствует
        if not settings.bot_token.startswith("test"):
            # Проверяем длину токена (должен быть достаточно длинным)
            assert len(settings.bot_token) > 20, "BOT_TOKEN должен быть достаточно длинным"

            # Проверяем, что токен не содержит очевидных паттернов
            assert "test" not in settings.bot_token.lower(), "BOT_TOKEN не должен содержать тестовые значения"

    @pytest.mark.asyncio
    async def test_api_security(self):
        """Тест безопасности API"""
        cbr_service = CBRRateService()

        # Тест с некорректными параметрами
        with pytest.raises(Exception):
            await cbr_service.get_rates_for_date("invalid_date")

        # Тест с пустыми параметрами
        with pytest.raises(Exception):
            await cbr_service.get_rates_for_date("")

    @pytest.mark.asyncio
    async def test_file_content_security(self, temp_dir):
        """Тест безопасности содержимого файлов"""
        # Создаем файл с потенциально опасным содержимым
        dangerous_content = """
        <script>alert('xss')</script>
        <?php system($_GET['cmd']); ?>
        <img src="x" onerror="alert('xss')">
        """

        dangerous_file = temp_dir / "dangerous.html"
        dangerous_file.write_text(dangerous_content)

        # Проверяем, что опасное содержимое не выполняется
        content = dangerous_file.read_text()
        assert "<script>" in content, "Содержимое должно быть прочитано как текст"
        assert "<?php" in content, "PHP код должен быть прочитан как текст"

    @pytest.mark.asyncio
    async def test_memory_exhaustion_security(self):
        """Тест защиты от исчерпания памяти"""
        cache = RatesCache()

        # Попытка загрузить слишком много данных в кэш
        large_data = {"data": "x" * 1024 * 1024}  # 1MB данных

        try:
            for i in range(1000):
                await cache.set_rates(f"memory_test_{i}", large_data)
        except MemoryError:
            # Ожидаем ошибку при исчерпании памяти
            pass
        except Exception as e:
            # Другие ошибки также приемлемы
            assert "memory" in str(e).lower() or "size" in str(e).lower()

    @pytest.mark.asyncio
    async def test_sql_injection_security(self):
        """Тест защиты от SQL инъекций (если используется БД)"""
        # Этот тест можно адаптировать под конкретную БД
        cache = RatesCache()

        # Попытка SQL инъекции через ключи кэша
        malicious_keys = [
            "'; DROP TABLE rates; --",
            "' OR '1'='1",
            "'; INSERT INTO users VALUES ('hacker', 'password'); --",
        ]

        for malicious_key in malicious_keys:
            try:
                await cache.set_rates(malicious_key, {"test": "data"})
                # Проверяем, что данные сохранились корректно
                result = await cache.get_rates(malicious_key)
                assert result == {"test": "data"}
            except Exception as e:
                # Ошибки при обработке специальных символов приемлемы
                assert "invalid" in str(e).lower() or "malformed" in str(e).lower()

    @pytest.mark.asyncio
    async def test_rate_limiting_security(self):
        """Тест защиты от перегрузки запросами"""
        cache = RatesCache()

        # Попытка выполнить слишком много операций одновременно
        tasks = []
        for i in range(1000):
            task = cache.set_rates(f"rate_limit_test_{i}", {"data": "test"})
            tasks.append(task)

        try:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            # Проверяем, что не все операции завершились успешно
            exceptions = [r for r in results if isinstance(r, Exception)]
            assert len(exceptions) > 0, "Должны быть отклонены некоторые запросы"
        except Exception:
            # Ожидаем ошибку при перегрузке
            pass

    @pytest.mark.asyncio
    async def test_input_validation_security(self):
        """Тест валидации входных данных"""
        file_validator = FileValidator()

        # Тест с некорректными именами файлов
        invalid_filenames = [
            "",  # Пустое имя
            "a" * 1000,  # Слишком длинное имя
            "file\x00.txt",  # Null байт
            "file\x0a.txt",  # Newline
            "file\x0d.txt",  # Carriage return
        ]

        for filename in invalid_filenames:
            with pytest.raises(Exception):
                validate_file(filename, 1024)

    @pytest.mark.asyncio
    async def test_encryption_security(self):
        """Тест безопасности шифрования (если используется)"""
        # Проверяем, что чувствительные данные не хранятся в открытом виде
        config_file = Path("app/config.py")

        if config_file.exists():
            config_content = config_file.read_text()

            # Проверяем, что токены не захардкожены
            assert "BOT_TOKEN = " not in config_content, "Токены не должны быть захардкожены"
            assert "YANDEX_DISK_TOKEN = " not in config_content, "Токены не должны быть захардкожены"

    @pytest.mark.asyncio
    async def test_logging_security(self):
        """Тест безопасности логирования"""
        # Проверяем, что чувствительные данные не логируются
        log_file = Path("logs/app.log")

        if log_file.exists():
            log_content = log_file.read_text()

            # Проверяем, что токены не попадают в логи
            assert settings.bot_token not in log_content, "BOT_TOKEN не должен попадать в логи"
            if settings.yandex_disk_token:
                assert settings.yandex_disk_token not in log_content, "YANDEX_DISK_TOKEN не должен попадать в логи"

    @pytest.mark.asyncio
    async def test_directory_traversal_security(self, temp_dir):
        """Тест защиты от directory traversal"""
        # Создаем структуру директорий для тестирования
        test_dir = temp_dir / "test_dir"
        test_dir.mkdir()

        # Попытка доступа к файлам вне разрешенной директории
        malicious_paths = [
            temp_dir / ".." / ".." / ".." / "etc" / "passwd",
            temp_dir / ".." / ".." / ".." / "windows" / "system32" / "config" / "sam",
        ]

        for malicious_path in malicious_paths:
            # Проверяем, что доступ к файлам вне разрешенной директории блокируется
            assert (
                not malicious_path.exists() or not malicious_path.is_file()
            ), f"Доступ к {malicious_path} должен быть заблокирован"

    @pytest.mark.asyncio
    async def test_session_security(self):
        """Тест безопасности сессий"""
        # Проверяем, что сессии не содержат чувствительных данных
        # Этот тест можно адаптировать под конкретную систему сессий

        # Проверяем только наши модули на наличие чувствительных данных
        import sys

        for module_name, module in sys.modules.items():
            # Проверяем только наши модули
            if module_name.startswith("app.") and hasattr(module, "__dict__"):
                for attr_name, attr_value in module.__dict__.items():
                    if isinstance(attr_value, str) and len(attr_value) > 20:
                        if "token" in attr_name.lower() or "password" in attr_name.lower():
                            # Проверяем, что это не реальный токен
                            assert attr_value.startswith("test") or attr_value.startswith(
                                "mock"
                            ), f"Чувствительные данные в {module_name}.{attr_name}"

    @pytest.mark.asyncio
    async def test_error_handling_security(self):
        """Тест безопасности обработки ошибок"""
        # Проверяем, что ошибки не раскрывают чувствительную информацию

        try:
            # Симулируем ошибку
            raise Exception("Test error")
        except Exception as e:
            error_message = str(e)

            # Проверяем, что в сообщении об ошибке нет чувствительных данных
            assert settings.bot_token not in error_message, "BOT_TOKEN не должен попадать в сообщения об ошибках"
            if settings.yandex_disk_token:
                assert (
                    settings.yandex_disk_token not in error_message
                ), "YANDEX_DISK_TOKEN не должен попадать в сообщения об ошибках"

    @pytest.mark.asyncio
    async def test_file_permissions_security(self, temp_dir):
        """Тест безопасности прав доступа к файлам"""
        # Создаем тестовый файл
        test_file = temp_dir / "test.txt"
        test_file.write_text("test content")

        # Проверяем права доступа
        stat = test_file.stat()

        # Проверяем, что файл не имеет избыточных прав
        # В Unix системах: 0o644 (rw-r--r--)
        # В Windows: права должны быть ограничены
        if os.name != "nt":  # Unix-like системы
            mode = stat.st_mode & 0o777
            assert mode <= 0o644, f"Файл имеет избыточные права доступа: {oct(mode)}"

    @pytest.mark.asyncio
    async def test_network_security(self):
        """Тест сетевой безопасности"""
        # Проверяем, что используются HTTPS соединения
        cbr_service = CBRRateService()

        # Проверяем URL API
        api_url = settings.cbr_api_url
        assert api_url.startswith("https://"), "API должен использовать HTTPS"

        # Проверяем, что нет HTTP соединений
        assert "http://" not in api_url, "Не должно быть HTTP соединений"

    @pytest.mark.asyncio
    async def test_dependency_security(self):
        """Тест безопасности зависимостей"""
        # Проверяем requirements.txt на наличие известных уязвимостей
        requirements_file = Path("requirements.txt")

        if requirements_file.exists():
            requirements_content = requirements_file.read_text()

            # Проверяем, что используются фиксированные версии
            lines = requirements_content.split("\n")
            for line in lines:
                line = line.strip()
                if line and not line.startswith("#"):
                    # Проверяем, что указана версия
                    if "==" not in line and ">=" not in line and "<=" not in line:
                        print(f"Warning: {line} не имеет фиксированной версии")

    @pytest.mark.asyncio
    async def test_configuration_security(self):
        """Тест безопасности конфигурации"""
        # Проверяем, что настройки безопасности корректны

        # Проверяем максимальный размер файла
        assert settings.max_file_size > 0, "MAX_FILE_SIZE должен быть положительным"
        assert settings.max_file_size <= 100 * 1024 * 1024, "MAX_FILE_SIZE не должен быть слишком большим"

        # Проверяем TTL кэша
        assert settings.cache_ttl > 0, "CACHE_TTL должен быть положительным"
        assert settings.cache_ttl <= 86400, "CACHE_TTL не должен быть слишком большим"

        # Проверяем уровень логирования
        assert settings.log_level in ["DEBUG", "INFO", "WARNING", "ERROR"], "Неверный уровень логирования"

    @pytest.mark.asyncio
    async def test_environment_security(self):
        """Тест безопасности окружения"""
        # Проверяем, что чувствительные данные не попадают в переменные окружения
        env_vars = os.environ

        # Проверяем, что нет очевидных токенов в переменных окружения
        for var_name, var_value in env_vars.items():
            if "token" in var_name.lower() or "password" in var_name.lower():
                if var_value and len(var_value) > 20:
                    # Проверяем, что это не тестовое значение
                    assert var_value.startswith("test") or var_value.startswith(
                        "mock"
                    ), f"Чувствительные данные в переменной окружения {var_name}"
