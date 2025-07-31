"""Расширенные тесты для парсера имен файлов."""

import pytest
from pathlib import Path
from app.utils.filename_parser import parse_filename, FilenameInfo


class TestFilenameParser:
    """Тесты для парсера имен файлов."""

    def test_parse_filename_basic(self):
        """Тест базового парсинга имени файла."""
        result = parse_filename("document.pdf")
        assert result is None  # Не соответствует формату

    def test_parse_filename_with_path(self):
        """Тест парсинга имени файла с путем."""
        result = parse_filename("/path/to/document.pdf")
        assert result is None  # Не соответствует формату

    def test_parse_filename_no_extension(self):
        """Тест парсинга имени файла без расширения."""
        result = parse_filename("document")
        assert result is None  # Не соответствует формату

    def test_parse_filename_multiple_dots(self):
        """Тест парсинга имени файла с несколькими точками."""
        result = parse_filename("document.backup.pdf")
        assert result is None  # Не соответствует формату

    def test_parse_filename_hidden_file(self):
        """Тест парсинга скрытого файла."""
        result = parse_filename(".hidden_file")
        assert result is None  # Не соответствует формату

    def test_parse_filename_unicode(self):
        """Тест парсинга имени файла с Unicode символами."""
        result = parse_filename("документ.pdf")
        assert result is None  # Не соответствует формату

    def test_parse_filename_special_characters(self):
        """Тест парсинга имени файла со специальными символами."""
        result = parse_filename("file-name_with_underscores.pdf")
        assert result is None  # Не соответствует формату

    def test_parse_filename_numbers(self):
        """Тест парсинга имени файла с числами."""
        result = parse_filename("document_2024_v1.2.pdf")
        assert result is None  # Не соответствует формату

    def test_parse_filename_empty_string(self):
        """Тест парсинга пустой строки."""
        result = parse_filename("")
        assert result is None

    def test_parse_filename_only_extension(self):
        """Тест парсинга только расширения."""
        result = parse_filename(".pdf")
        assert result is None

    def test_parse_filename_path_object(self):
        """Тест парсинга Path объекта."""
        path = Path("document.pdf")
        result = parse_filename(str(path))
        assert result is None  # Не соответствует формату

    def test_parse_filename_case_sensitivity(self):
        """Тест чувствительности к регистру."""
        result = parse_filename("Document.PDF")
        assert result is None  # Не соответствует формату

    def test_parse_filename_complex_path(self):
        """Тест парсинга сложного пути."""
        result = parse_filename("/complex/path/to/document.backup.pdf")
        assert result is None  # Не соответствует формату

    def test_parse_filename_with_spaces(self):
        """Тест парсинга имени файла с пробелами."""
        result = parse_filename("my document.pdf")
        assert result is None  # Не соответствует формату

    def test_parse_filename_with_tabs(self):
        """Тест парсинга имени файла с табуляцией."""
        result = parse_filename("my\tdocument.pdf")
        assert result is None  # Не соответствует формату

    def test_parse_filename_with_newlines(self):
        """Тест парсинга имени файла с переносами строк."""
        result = parse_filename("my\ndocument.pdf")
        assert result is None  # Не соответствует формату

    def test_parse_filename_edge_cases(self):
        """Тест граничных случаев."""
        result = parse_filename("document.pdf")
        assert result is None  # Не соответствует формату

    def test_parse_filename_valid_format(self):
        """Тест валидного формата имени файла."""
        result = parse_filename("Principal_Agent_Contract_123_230525.pdf")
        assert result is not None
        assert isinstance(result, FilenameInfo)
        assert result.principal == "Principal"
        assert result.agent == "Agent"
        assert result.doctype == "contract"
        assert result.number == "123"
        assert result.date == "230525"
        assert result.ext == "pdf"

    def test_parse_filename_return_type(self):
        """Тест типа возвращаемого значения."""
        result = parse_filename("Principal_Agent_Contract_123_230525.pdf")
        assert isinstance(result, FilenameInfo)

    def test_parse_filename_consistency(self):
        """Тест консистентности парсинга."""
        result1 = parse_filename("Principal_Agent_Contract_123_230525.pdf")
        result2 = parse_filename("Principal_Agent_Contract_123_230525.pdf")
        assert result1 == result2

    def test_parse_filename_preserves_original(self):
        """Тест сохранения оригинального имени."""
        result = parse_filename("Principal_Agent_Contract_123_230525.pdf")
        assert result is not None
        # Проверяем, что данные корректно извлечены
        assert result.principal == "Principal"
        assert result.ext == "pdf" 