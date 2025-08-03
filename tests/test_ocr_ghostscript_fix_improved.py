"""
Улучшенные тесты для проверки исправления проблемы с Ghostscript 10.0.0-10.02.0
Основаны на рекомендациях Context7 и лучших практиках pytest
"""

import pytest
from pathlib import Path
from typing import Tuple

from app.services.ocr_service import run_ocr, perform_ocr


class TestGhostscriptFixImproved:
    """Улучшенные тесты исправления проблемы с Ghostscript"""

    def test_ocr_with_output_type_pdf(self, mocker, temp_pdf_file: Path) -> None:
        """Тест что используется output_type='pdf' для обхода Ghostscript"""
        mock_ocr = mocker.patch("app.services.ocr_service.ocrmypdf.ocr", create=True)
        mocker.patch("pathlib.Path.exists", return_value=True)
        mocker.patch("pathlib.Path.read_text", return_value="test text")
        
        # Вызываем функцию
        run_ocr(temp_pdf_file)
        
        # Проверяем, что ocrmypdf.ocr был вызван с правильными параметрами
        mock_ocr.assert_called()
        call_args = mock_ocr.call_args
        
        # Проверяем, что используется output_type='pdf'
        assert call_args[1]['output_type'] == 'pdf'

    def test_ocr_fallback_mechanism_works(self, mocker, temp_pdf_file: Path) -> None:
        """Тест что fallback механизм работает при ошибке первой попытки"""
        mock_ocr = mocker.patch("app.services.ocr_service.ocrmypdf.ocr", create=True)
        mocker.patch("pathlib.Path.exists", return_value=True)
        mocker.patch("pathlib.Path.read_text", return_value="test text")
        
        # Первый вызов вызывает исключение
        mock_ocr.side_effect = [
            Exception("Ghostscript error"),  # Первый вызов
            None  # Второй вызов (fallback)
        ]
        
        # Вызываем функцию
        run_ocr(temp_pdf_file)
        
        # Проверяем, что ocrmypdf.ocr был вызван дважды
        assert mock_ocr.call_count == 2
        
        # Проверяем параметры первого вызова
        first_call = mock_ocr.call_args_list[0]
        assert first_call[1]['skip_text'] is True
        assert first_call[1]['output_type'] == 'pdf'
        
        # Проверяем параметры второго вызова (fallback)
        second_call = mock_ocr.call_args_list[1]
        assert second_call[1]['force_ocr'] is True
        assert second_call[1]['output_type'] == 'pdf'

    def test_ocr_both_attempts_fail(self, mocker, temp_pdf_file: Path) -> None:
        """Тест что исключение пробрасывается если оба попытки не удались"""
        mock_ocr = mocker.patch("app.services.ocr_service.ocrmypdf.ocr", create=True)
        mock_ocr.side_effect = Exception("OCR failed")
        
        # Проверяем, что исключение пробрасывается
        with pytest.raises(Exception, match="OCR failed"):
            run_ocr(temp_pdf_file)
        
        # Проверяем, что ocrmypdf.ocr был вызван дважды
        assert mock_ocr.call_count == 2

    @pytest.mark.parametrize("expected_params", [
        {
            'language': 'rus+eng',
            'skip_text': True,
            'deskew': False,
            'rotate_pages': False,
            'remove_background': False,
            'progress_bar': False,
            'output_type': 'pdf'
        }
    ])
    def test_ocr_parameters_validation(self, mocker, temp_pdf_file: Path, expected_params: dict) -> None:
        """Параметризованный тест валидации параметров OCR"""
        mock_ocr = mocker.patch("app.services.ocr_service.ocrmypdf.ocr", create=True)
        mocker.patch("pathlib.Path.exists", return_value=True)
        mocker.patch("pathlib.Path.read_text", return_value="test text")
        
        # Вызываем функцию
        run_ocr(temp_pdf_file)
        
        # Проверяем параметры
        call_args = mock_ocr.call_args[1]
        for param, value in expected_params.items():
            assert call_args[param] == value

    def test_ocr_sidecar_file_cleanup(self, mocker, temp_pdf_file: Path) -> None:
        """Тест что sidecar файл удаляется в finally блоке"""
        mocker.patch("app.services.ocr_service.ocrmypdf.ocr", create=True)
        mocker.patch("pathlib.Path.exists", return_value=True)
        mocker.patch("pathlib.Path.read_text", return_value="test text")
        mock_unlink = mocker.patch("pathlib.Path.unlink")
        
        # Вызываем функцию
        run_ocr(temp_pdf_file)
        
        # Проверяем, что unlink был вызван для sidecar файла
        mock_unlink.assert_called_with(missing_ok=True)

    @pytest.mark.asyncio
    async def test_perform_ocr_async(self, mocker) -> None:
        """Тест асинхронной функции perform_ocr"""
        mock_run_ocr = mocker.patch("app.services.ocr_service.run_ocr")
        mock_run_ocr.return_value = (Path("/tmp/test.pdf"), "test text")
        
        # Вызываем асинхронную функцию
        result = await perform_ocr("/tmp/input.pdf")
        
        # Проверяем результат
        assert result == (Path("/tmp/test.pdf"), "test text")

    def test_ocr_language_setting(self, mocker, temp_pdf_file: Path) -> None:
        """Тест что язык OCR настраивается правильно"""
        mock_ocr = mocker.patch("app.services.ocr_service.ocrmypdf.ocr", create=True)
        mocker.patch("pathlib.Path.exists", return_value=True)
        mocker.patch("pathlib.Path.read_text", return_value="test text")
        
        # Вызываем функцию
        run_ocr(temp_pdf_file)
        
        # Проверяем, что язык установлен правильно
        call_args = mock_ocr.call_args[1]
        assert call_args['language'] == 'rus+eng'

    def test_ocr_error_logging(self, mocker, temp_pdf_file: Path, mock_logging) -> None:
        """Тест что ошибки логируются правильно"""
        mock_ocr = mocker.patch("app.services.ocr_service.ocrmypdf.ocr", create=True)
        mock_ocr.side_effect = Exception("OCR processing failed")
        
        # Проверяем, что исключение пробрасывается
        with pytest.raises(Exception, match="OCR processing failed"):
            run_ocr(temp_pdf_file)
        
        # Проверяем, что ошибка была залогирована
        mock_logging.error.assert_called()
        error_call = mock_logging.error.call_args
        assert "ocr_failed" in error_call[0][0]
        assert str(temp_pdf_file) in error_call[1]['path']

    def test_ocr_with_empty_pdf(self, mocker, temp_pdf_file: Path) -> None:
        """Тест обработки пустого PDF файла"""
        mock_ocr = mocker.patch("app.services.ocr_service.ocrmypdf.ocr", create=True)
        mocker.patch("pathlib.Path.exists", return_value=True)
        mocker.patch("pathlib.Path.read_text", return_value="")
        
        # Вызываем функцию
        result = run_ocr(temp_pdf_file)
        
        # Проверяем, что функция работает с пустым текстом
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_ocr_with_large_pdf(self, mocker, temp_pdf_file: Path) -> None:
        """Тест обработки большого PDF файла"""
        mock_ocr = mocker.patch("app.services.ocr_service.ocrmypdf.ocr", create=True)
        mocker.patch("pathlib.Path.exists", return_value=True)
        mocker.patch("pathlib.Path.read_text", return_value="x" * 10000)  # Большой текст
        
        # Вызываем функцию
        result = run_ocr(temp_pdf_file)
        
        # Проверяем, что функция работает с большим текстом
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_ocr_with_corrupted_pdf(self, mocker, temp_pdf_file: Path) -> None:
        """Тест обработки поврежденного PDF файла"""
        mock_ocr = mocker.patch("app.services.ocr_service.ocrmypdf.ocr", create=True)
        mock_ocr.side_effect = Exception("Corrupted PDF")
        
        # Проверяем, что исключение пробрасывается
        with pytest.raises(Exception, match="Corrupted PDF"):
            run_ocr(temp_pdf_file)

    @pytest.mark.integration
    def test_ocr_integration_workflow(self, mocker, temp_pdf_file: Path) -> None:
        """Интеграционный тест полного workflow OCR"""
        mock_ocr = mocker.patch("app.services.ocr_service.ocrmypdf.ocr", create=True)
        mocker.patch("pathlib.Path.exists", return_value=True)
        mocker.patch("pathlib.Path.read_text", return_value="integration test text")
        
        # Вызываем функцию
        result = run_ocr(temp_pdf_file)
        
        # Проверяем полный результат
        assert isinstance(result, tuple)
        assert len(result) == 2
        assert isinstance(result[0], Path)
        assert isinstance(result[1], str)
        assert result[1] == "integration test text"

    def test_ocr_performance_benchmark(self, mocker, temp_pdf_file: Path) -> None:
        """Тест производительности OCR"""
        import time
        
        mock_ocr = mocker.patch("app.services.ocr_service.ocrmypdf.ocr", create=True)
        mocker.patch("pathlib.Path.exists", return_value=True)
        mocker.patch("pathlib.Path.read_text", return_value="performance test text")
        
        # Измеряем время выполнения
        start_time = time.time()
        result = run_ocr(temp_pdf_file)
        end_time = time.time()
        
        # Проверяем, что выполнение заняло разумное время (< 1 секунды для мока)
        execution_time = end_time - start_time
        assert execution_time < 1.0
        
        # Проверяем результат
        assert isinstance(result, tuple)
        assert len(result) == 2 