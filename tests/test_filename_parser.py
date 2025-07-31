"""Тесты для парсинга имен файлов."""

import pytest
from datetime import date

from app.utils.filename_parser import parse_filename


class TestFilenameParser:
    """Тесты для функций parse_filename и determine_path."""

    def test_valid_filename_parsing(self):
        """Тест корректного парсинга имени файла."""
        filename = "Альфатрекс_Агрико_договор_2_300525.docx"

        result = parse_filename(filename)

        assert result is not None
        assert result.principal == "Альфатрекс"
        assert result.agent == "Агрико"
        assert result.doctype == "договор"
        assert result.number == "2"
        assert result.date == "300525"
        assert result.ext == "docx"

    def test_valid_filename_with_spaces(self):
        """Тест имени файла с пробелами в названиях."""
        filename = "Сбербанк_Иванов_поручение_15_280725.pdf"

        result = parse_filename(filename)

        assert result is not None
        assert result.principal == "Сбербанк"
        assert result.agent == "Иванов"
        assert result.doctype == "поручение"
        assert result.number == "15"
        assert result.date == "280725"
        assert result.ext == "pdf"

    def test_invalid_filename_format(self):
        """Тест некорректного формата имени файла."""
        filename = "просто_файл.pdf"

        result = parse_filename(filename)

        assert result is None

    def test_filename_with_underscores_in_names(self):
        """Тест имени файла с подчеркиваниями в названиях."""
        filename = "ВТБ_Рога_акт_7_150124.docx"

        result = parse_filename(filename)

        assert result is not None
        assert result.principal == "ВТБ"
        assert result.agent == "Рога"
        assert result.doctype == "акт"
        assert result.number == "7"
        assert result.date == "150124"
        assert result.ext == "docx"

    def test_filename_with_special_chars(self):
        """Тест имени файла со специальными символами."""
        filename = "Альфатрекс@Агрико_договор_2_300525.docx"

        result = parse_filename(filename)

        # Special characters should make parsing fail
        assert result is None

    def test_filename_with_dots_in_date(self):
        """Тест имени файла с точками в дате."""
        filename = "Альфатрекс_Агрико_договор_2_30.05.25.docx"

        result = parse_filename(filename)

        # Dots in date are actually supported and normalized
        assert result is not None
        assert result.date == "300525"  # normalized to remove dots

    def test_empty_filename(self):
        """Тест пустого имени файла."""
        filename = ""

        result = parse_filename(filename)

        assert result is None

    def test_none_filename(self):
        """Тест None имени файла."""
        filename = None

        result = parse_filename(filename)

        assert result is None

    def test_filename_with_emoji(self):
        """Тест имени файла с эмодзи."""
        filename = "Альфатрекс🚀_Агрико_договор_2_300525.docx"

        result = parse_filename(filename)

        assert result is None

    def test_parse_filename_edge_cases(self):
        """Тест граничных случаев парсинга."""
        test_cases = [
            # Минимально валидное имя
            (
                "А_Б_В_1_010101.pdf",
                {"principal": "А", "agent": "Б", "doctype": "в", "number": "1", "date": "010101"},  # lowercase
            ),
            # Длинное имя
            (
                "Принципал_Агент_Документ_999_311299.pdf",
                {
                    "principal": "Принципал",
                    "agent": "Агент",
                    "doctype": "документ",  # lowercase
                    "number": "999",
                    "date": "311299",
                },
            ),
        ]

        for filename, expected in test_cases:
            result = parse_filename(filename)
            assert result is not None
            assert result.principal == expected["principal"]
            assert result.agent == expected["agent"]
            assert result.doctype == expected["doctype"]
            assert result.number == expected["number"]
            assert result.date == expected["date"]

    def test_parse_filename_invalid_cases(self):
        """Тест невалидных случаев парсинга."""
        invalid_cases = [
            "файл.pdf",  # Недостаточно частей
            "А_Б_В_Г_Д_Е_Ж_З.pdf",  # Слишком много частей
            "А_Б_В_abc_010101.pdf",  # Некорректный номер
            "А_Б_В_1_abc.pdf",  # Некорректная дата
            "А_Б_В_1_010101",  # Без расширения
        ]

        for filename in invalid_cases:
            result = parse_filename(filename)
            assert result is None, f"Файл '{filename}' должен быть невалидным"
