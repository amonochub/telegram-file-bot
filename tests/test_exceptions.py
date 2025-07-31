"""Тесты для кастомных исключений."""

import pytest
from app.utils.exceptions import (
    FileValidationError, CBRServiceError, YandexDiskError, OCRProcessingError,
    ConfigurationError, UserNotAllowedError, RateNotFoundError, CalculationError,
    ValidationError
)


class TestFileValidationError:
    """Тесты для FileValidationError."""

    def test_file_validation_error_creation(self):
        """Тест создания FileValidationError."""
        error = FileValidationError("Invalid file type")
        assert str(error) == "Invalid file type"
        assert isinstance(error, Exception)

    def test_file_validation_error_with_details(self):
        """Тест создания FileValidationError с деталями."""
        error = FileValidationError("Invalid file type", file_path="/path/to/file.txt")
        assert "Invalid file type" in str(error)
        assert hasattr(error, 'file_path')
        assert error.file_path == "/path/to/file.txt"

    def test_file_validation_error_inheritance(self):
        """Тест наследования FileValidationError."""
        error = FileValidationError("Test error")
        assert isinstance(error, Exception)
        assert isinstance(error, FileValidationError)


class TestCBRServiceError:
    """Тесты для CBRServiceError."""

    def test_cbr_service_error_creation(self):
        """Тест создания CBRServiceError."""
        error = CBRServiceError("CBR service failed")
        assert str(error) == "CBR service failed"
        assert isinstance(error, Exception)

    def test_cbr_service_error_inheritance(self):
        """Тест наследования CBRServiceError."""
        error = CBRServiceError("Test error")
        assert isinstance(error, Exception)
        assert isinstance(error, CBRServiceError)


class TestOCRProcessingError:
    """Тесты для OCRProcessingError."""

    def test_ocr_processing_error_creation(self):
        """Тест создания OCRProcessingError."""
        error = OCRProcessingError("OCR failed")
        assert str(error) == "OCR failed"
        assert isinstance(error, Exception)

    def test_ocr_processing_error_with_details(self):
        """Тест создания OCRProcessingError с деталями."""
        error = OCRProcessingError("OCR failed", file_path="/path/to/file.pdf", language="en")
        assert "OCR failed" in str(error)
        assert hasattr(error, 'file_path')
        assert hasattr(error, 'language')
        assert error.file_path == "/path/to/file.pdf"
        assert error.language == "en"

    def test_ocr_processing_error_inheritance(self):
        """Тест наследования OCRProcessingError."""
        error = OCRProcessingError("Test error")
        assert isinstance(error, Exception)
        assert isinstance(error, OCRProcessingError)


class TestConfigurationError:
    """Тесты для ConfigurationError."""

    def test_configuration_error_creation(self):
        """Тест создания ConfigurationError."""
        error = ConfigurationError("Configuration failed")
        assert str(error) == "Configuration failed"
        assert isinstance(error, Exception)

    def test_configuration_error_inheritance(self):
        """Тест наследования ConfigurationError."""
        error = ConfigurationError("Test error")
        assert isinstance(error, Exception)
        assert isinstance(error, ConfigurationError)


class TestUserNotAllowedError:
    """Тесты для UserNotAllowedError."""

    def test_user_not_allowed_error_creation(self):
        """Тест создания UserNotAllowedError."""
        error = UserNotAllowedError("User not allowed")
        assert str(error) == "User not allowed"
        assert isinstance(error, Exception)

    def test_user_not_allowed_error_inheritance(self):
        """Тест наследования UserNotAllowedError."""
        error = UserNotAllowedError("Test error")
        assert isinstance(error, Exception)
        assert isinstance(error, UserNotAllowedError)


class TestRateNotFoundError:
    """Тесты для RateNotFoundError."""

    def test_rate_not_found_error_creation(self):
        """Тест создания RateNotFoundError."""
        error = RateNotFoundError("Rate not found")
        assert str(error) == "Rate not found"
        assert isinstance(error, Exception)

    def test_rate_not_found_error_inheritance(self):
        """Тест наследования RateNotFoundError."""
        error = RateNotFoundError("Test error")
        assert isinstance(error, Exception)
        assert isinstance(error, RateNotFoundError)


class TestCalculationError:
    """Тесты для CalculationError."""

    def test_calculation_error_creation(self):
        """Тест создания CalculationError."""
        error = CalculationError("Calculation failed")
        assert str(error) == "Calculation failed"
        assert isinstance(error, Exception)

    def test_calculation_error_inheritance(self):
        """Тест наследования CalculationError."""
        error = CalculationError("Test error")
        assert isinstance(error, Exception)
        assert isinstance(error, CalculationError)


class TestYandexDiskError:
    """Тесты для YandexDiskError."""

    def test_yandex_disk_error_creation(self):
        """Тест создания YandexDiskError."""
        error = YandexDiskError("Upload failed")
        assert str(error) == "Upload failed"
        assert isinstance(error, Exception)

    def test_yandex_disk_error_with_details(self):
        """Тест создания YandexDiskError с деталями."""
        error = YandexDiskError("Upload failed", operation="upload", remote_path="/disk/file.txt")
        assert "Upload failed" in str(error)
        assert hasattr(error, 'operation')
        assert hasattr(error, 'remote_path')
        assert error.operation == "upload"
        assert error.remote_path == "/disk/file.txt"

    def test_yandex_disk_error_inheritance(self):
        """Тест наследования YandexDiskError."""
        error = YandexDiskError("Test error")
        assert isinstance(error, Exception)
        assert isinstance(error, YandexDiskError)


class TestValidationError:
    """Тесты для ValidationError."""

    def test_validation_error_creation(self):
        """Тест создания ValidationError."""
        error = ValidationError("Invalid input")
        assert str(error) == "Invalid input"
        assert isinstance(error, Exception)

    def test_validation_error_with_details(self):
        """Тест создания ValidationError с деталями."""
        error = ValidationError("Invalid input", field="username", value="test")
        assert "Invalid input" in str(error)
        assert hasattr(error, 'field')
        assert hasattr(error, 'value')
        assert error.field == "username"
        assert error.value == "test"

    def test_validation_error_inheritance(self):
        """Тест наследования ValidationError."""
        error = ValidationError("Test error")
        assert isinstance(error, Exception)
        assert isinstance(error, ValidationError)


class TestExceptionHierarchy:
    """Тесты иерархии исключений."""

    def test_exception_hierarchy(self):
        """Тест иерархии исключений."""
        # Все исключения должны наследоваться от Exception
        exceptions = [
            FileValidationError("test"),
            CBRServiceError("test"),
            OCRProcessingError("test"),
            YandexDiskError("test"),
            ConfigurationError("test"),
            UserNotAllowedError("test"),
            RateNotFoundError("test"),
            CalculationError("test")
        ]
        
        for exc in exceptions:
            assert isinstance(exc, Exception)

    def test_exception_messages(self):
        """Тест сообщений исключений."""
        test_message = "Test error message"
        
        exceptions = [
            FileValidationError(test_message),
            CBRServiceError(test_message),
            OCRProcessingError(test_message),
            YandexDiskError(test_message),
            ConfigurationError(test_message),
            UserNotAllowedError(test_message),
            RateNotFoundError(test_message),
            CalculationError(test_message)
        ]
        
        for exc in exceptions:
            assert test_message in str(exc) 