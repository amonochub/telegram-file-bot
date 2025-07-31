"""
Тесты для валидации файлов
"""

import pytest
from pathlib import Path

from app.utils.file_validation import validate_file, sanitize_filename, validate_file_path
from app.utils.exceptions import FileValidationError


class TestFileValidation:
    """Тесты для валидации файлов"""

    def test_validate_file_success(self):
        """Тест успешной валидации файла"""
        result = validate_file("test.pdf", 1024)
        assert result == "test.pdf"

    def test_validate_file_empty_name(self):
        """Тест валидации пустого имени файла"""
        with pytest.raises(FileValidationError, match="Пустое имя файла"):
            validate_file("", 1024)

    def test_validate_file_too_long_name(self):
        """Тест валидации слишком длинного имени файла"""
        long_name = "a" * 300
        with pytest.raises(FileValidationError, match="Слишком длинное имя файла"):
            validate_file(long_name, 1024)

    def test_validate_file_no_extension(self):
        """Тест валидации файла без расширения"""
        with pytest.raises(FileValidationError, match="Файл должен иметь расширение"):
            validate_file("test", 1024)

    def test_validate_file_invalid_extension(self):
        """Тест валидации файла с недопустимым расширением"""
        with pytest.raises(FileValidationError, match="Недопустимое расширение"):
            validate_file("test.exe", 1024)

    def test_validate_file_empty_size(self):
        """Тест валидации пустого файла"""
        with pytest.raises(FileValidationError, match="Пустой файл"):
            validate_file("test.pdf", 0)

    def test_validate_file_too_large(self):
        """Тест валидации слишком большого файла"""
        with pytest.raises(FileValidationError, match="Файл слишком большой"):
            validate_file("test.pdf", 200_000_000)  # 200MB

    def test_validate_file_dangerous_chars(self):
        """Тест валидации файла с опасными символами"""
        with pytest.raises(FileValidationError, match="недопустимые символы"):
            validate_file("test<>.pdf", 1024)

    def test_validate_file_hidden_file(self):
        """Тест валидации скрытого файла"""
        with pytest.raises(FileValidationError, match="Системные и скрытые файлы запрещены"):
            validate_file(".test.pdf", 1024)


class TestSanitizeFilename:
    """Тесты для очистки имен файлов"""

    def test_sanitize_filename_success(self):
        """Тест успешной очистки имени файла"""
        result = sanitize_filename("test.pdf")
        assert result == "test.pdf"

    def test_sanitize_filename_dangerous_chars(self):
        """Тест очистки опасных символов"""
        result = sanitize_filename('test<>:"/\\|?*.pdf')
        assert result == "test_.pdf"

    def test_sanitize_filename_multiple_underscores(self):
        """Тест очистки множественных подчеркиваний"""
        result = sanitize_filename("test___file.pdf")
        assert result == "test_file.pdf"

    def test_sanitize_filename_trim_underscores(self):
        """Тест обрезки подчеркиваний в начале и конце"""
        result = sanitize_filename("_test_file_.pdf")
        assert result == "test_file_.pdf"

    def test_sanitize_filename_too_long(self):
        """Тест обрезки слишком длинного имени"""
        long_name = "a" * 300 + ".pdf"
        result = sanitize_filename(long_name)
        assert len(result) <= 255


class TestValidateFilePath:
    """Тесты для валидации путей к файлам"""

    def test_validate_file_path_success(self, tmp_path):
        """Тест успешной валидации пути к файлу"""
        file_path = tmp_path / "test.pdf"
        file_path.write_bytes(b"%PDF-1.4\n%EOF")

        # Создаем временный файл с правильным содержимым
        assert validate_file_path(file_path) is True

    def test_validate_file_path_not_exists(self, tmp_path):
        """Тест валидации несуществующего файла"""
        file_path = tmp_path / "nonexistent.pdf"

        assert validate_file_path(file_path) is False

    def test_validate_file_path_directory(self, tmp_path):
        """Тест валидации директории"""
        dir_path = tmp_path / "test_dir"
        dir_path.mkdir()

        assert validate_file_path(dir_path) is False

    def test_validate_file_path_empty_file(self, tmp_path):
        """Тест валидации пустого файла"""
        file_path = tmp_path / "empty.pdf"
        file_path.touch()

        assert validate_file_path(file_path) is False

    def test_validate_file_path_invalid_extension(self, tmp_path):
        """Тест валидации файла с недопустимым расширением"""
        file_path = tmp_path / "test.exe"
        file_path.write_bytes(b"test content")

        assert validate_file_path(file_path) is False
