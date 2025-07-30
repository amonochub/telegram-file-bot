"""Тесты для парсинга имен файлов."""

import pytest
from datetime import date

from app.utils.filename_parser import parse_filename, determine_path


class TestFilenameParser:
    """Тесты для функций parse_filename и determine_path."""

    def test_valid_filename_parsing(self):
        """Тест корректного парсинга имени файла."""
        filename = "Альфатрекс_Агрико_агентский договор_2_300525.docx"
        
        result = parse_filename(filename)
        
        assert result is not None
        assert result["principal"] == "Альфатрекс"
        assert result["agent"] == "Агрико"
        assert result["document_type"] == "агентский договор"
        assert result["number"] == "2"
        assert result["date"] == "300525"

    def test_valid_filename_with_spaces(self):
        """Тест имени файла с пробелами в названиях."""
        filename = "Сбербанк_ИП Иванов_поручение_15_280725.pdf"
        
        result = parse_filename(filename)
        
        assert result is not None
        assert result["principal"] == "Сбербанк"
        assert result["agent"] == "ИП Иванов"
        assert result["document_type"] == "поручение"
        assert result["number"] == "15"
        assert result["date"] == "280725"

    def test_invalid_filename_format(self):
        """Тест некорректного формата имени файла."""
        filename = "просто_файл.pdf"
        
        result = parse_filename(filename)
        
        assert result is None

    def test_filename_with_underscores_in_names(self):
        """Тест имени файла с подчеркиваниями в названиях."""
        filename = "ВТБ_ООО_Рога_и_Копыта_акт-отчет_7_150124.docx"
        
        result = parse_filename(filename)
        
        assert result is not None
        assert result["principal"] == "ВТБ"
        assert result["agent"] == "ООО_Рога_и_Копыта"
        assert result["document_type"] == "акт-отчет"
        assert result["number"] == "7"
        assert result["date"] == "150124"

    def test_filename_with_special_chars(self):
        """Тест имени файла со специальными символами."""
        filename = "Альфатрекс@Агрико_договор_2_300525.docx"
        
        result = parse_filename(filename)
        
        assert result is None

    def test_filename_with_dots_in_date(self):
        """Тест имени файла с точками в дате."""
        filename = "Альфатрекс_Агрико_договор_2_30.05.25.docx"
        
        result = parse_filename(filename)
        
        assert result is None

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

    def test_determine_path_valid_filename(self):
        """Тест определения пути для валидного имени файла."""
        filename = "Альфатрекс_Агрико_агентский договор_2_300525.docx"
        
        result = determine_path(filename)
        
        assert result == "disk:/disk:/Альфатрекс/Агрико/агентский договор/Альфатрекс_Агрико_агентский договор_2_300525.docx"

    def test_determine_path_invalid_filename(self):
        """Тест определения пути для невалидного имени файла."""
        filename = "просто_файл.pdf"
        
        result = determine_path(filename)
        
        assert result == "disk:/disk:/unsorted/просто_файл.pdf"

    def test_determine_path_with_spaces(self):
        """Тест определения пути для имени с пробелами."""
        filename = "Сбербанк_ИП Иванов_поручение_15_280725.pdf"
        
        result = determine_path(filename)
        
        assert result == "disk:/disk:/Сбербанк/ИП Иванов/поручение/Сбербанк_ИП Иванов_поручение_15_280725.pdf"

    def test_determine_path_with_special_chars(self):
        """Тест определения пути для имени со спецсимволами."""
        filename = "Альфатрекс@Агрико_договор_2_300525.docx"
        
        result = determine_path(filename)
        
        assert result == "disk:/disk:/unsorted/Альфатрекс@Агрико_договор_2_300525.docx"

    def test_parse_filename_edge_cases(self):
        """Тест граничных случаев парсинга."""
        test_cases = [
            # Минимально валидное имя
            ("А_Б_В_1_010101.pdf", {
                "principal": "А",
                "agent": "Б", 
                "document_type": "В",
                "number": "1",
                "date": "010101"
            }),
            # Максимально длинное имя
            ("Очень_длинное_название_принципала_Очень_длинное_название_агента_Очень_длинный_тип_документа_999_311299.pdf", {
                "principal": "Очень_длинное_название_принципала",
                "agent": "Очень_длинное_название_агента",
                "document_type": "Очень_длинный_тип_документа",
                "number": "999",
                "date": "311299"
            }),
        ]
        
        for filename, expected in test_cases:
            result = parse_filename(filename)
            assert result is not None
            for key, value in expected.items():
                assert result[key] == value

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