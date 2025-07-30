"""Тесты для валидации файлов."""

import pytest
from pathlib import Path

from app.utils.file_validation import validate_file, FileValidationError


class TestFileValidation:
    """Тесты для функции validate_file."""

    def test_valid_pdf_file(self):
        """Тест валидного PDF файла."""
        filename = "test_document.pdf"
        file_size = 1024 * 1024  # 1MB
        
        result = validate_file(filename, file_size)
        assert result is True

    def test_valid_docx_file(self):
        """Тест валидного DOCX файла."""
        filename = "test_document.docx"
        file_size = 2048 * 1024  # 2MB
        
        result = validate_file(filename, file_size)
        assert result is True

    def test_valid_image_file(self):
        """Тест валидного изображения."""
        filename = "test_image.jpg"
        file_size = 512 * 1024  # 512KB
        
        result = validate_file(filename, file_size)
        assert result is True

    def test_empty_filename(self):
        """Тест пустого имени файла."""
        filename = ""
        file_size = 1024
        
        with pytest.raises(FileValidationError) as exc_info:
            validate_file(filename, file_size)
        
        assert "Имя файла не может быть пустым" in str(exc_info.value)

    def test_none_filename(self):
        """Тест None имени файла."""
        filename = None
        file_size = 1024
        
        with pytest.raises(FileValidationError) as exc_info:
            validate_file(filename, file_size)
        
        assert "Имя файла не может быть пустым" in str(exc_info.value)

    def test_unsupported_extension(self):
        """Тест неподдерживаемого расширения."""
        filename = "test_file.exe"
        file_size = 1024
        
        with pytest.raises(FileValidationError) as exc_info:
            validate_file(filename, file_size)
        
        assert "Неподдерживаемый тип файла" in str(exc_info.value)

    def test_no_extension(self):
        """Тест файла без расширения."""
        filename = "test_file"
        file_size = 1024
        
        with pytest.raises(FileValidationError) as exc_info:
            validate_file(filename, file_size)
        
        assert "Неподдерживаемый тип файла" in str(exc_info.value)

    def test_file_too_large(self):
        """Тест файла слишком большого размера."""
        filename = "test_document.pdf"
        file_size = 101 * 1024 * 1024  # 101MB
        
        with pytest.raises(FileValidationError) as exc_info:
            validate_file(filename, file_size)
        
        assert "Размер файла превышает максимально допустимый" in str(exc_info.value)

    def test_filename_too_long(self):
        """Тест слишком длинного имени файла."""
        filename = "a" * 256 + ".pdf"  # 260 символов
        file_size = 1024
        
        with pytest.raises(FileValidationError) as exc_info:
            validate_file(filename, file_size)
        
        assert "Имя файла слишком длинное" in str(exc_info.value)

    def test_filename_with_special_chars(self):
        """Тест имени файла со специальными символами."""
        filename = "test<file>.pdf"
        file_size = 1024
        
        with pytest.raises(FileValidationError) as exc_info:
            validate_file(filename, file_size)
        
        assert "Имя файла содержит недопустимые символы" in str(exc_info.value)

    def test_filename_with_emoji(self):
        """Тест имени файла с эмодзи."""
        filename = "test🚀file.pdf"
        file_size = 1024
        
        with pytest.raises(FileValidationError) as exc_info:
            validate_file(filename, file_size)
        
        assert "Имя файла содержит недопустимые символы" in str(exc_info.value)

    def test_case_insensitive_extensions(self):
        """Тест регистронезависимых расширений."""
        test_cases = [
            ("test.PDF", 1024),
            ("test.DOCX", 1024),
            ("test.JPG", 1024),
            ("test.PNG", 1024),
        ]
        
        for filename, file_size in test_cases:
            result = validate_file(filename, file_size)
            assert result is True

    def test_zero_file_size(self):
        """Тест файла нулевого размера."""
        filename = "test_document.pdf"
        file_size = 0
        
        with pytest.raises(FileValidationError) as exc_info:
            validate_file(filename, file_size)
        
        assert "Размер файла должен быть больше нуля" in str(exc_info.value)

    def test_negative_file_size(self):
        """Тест отрицательного размера файла."""
        filename = "test_document.pdf"
        file_size = -1024
        
        with pytest.raises(FileValidationError) as exc_info:
            validate_file(filename, file_size)
        
        assert "Размер файла должен быть больше нуля" in str(exc_info.value) 