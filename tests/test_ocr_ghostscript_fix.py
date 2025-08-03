"""
Тесты для проверки исправления проблемы с Ghostscript 10.0.0-10.02.0
"""

import pytest
from unittest.mock import patch, MagicMock, mock_open
from pathlib import Path
import tempfile

from app.services.ocr_service import run_ocr, perform_ocr


class TestGhostscriptFix:
    """Тесты исправления проблемы с Ghostscript"""

    def test_ocr_with_output_type_pdf(self):
        """Тест что используется output_type='pdf' для обхода Ghostscript"""
        with patch("app.services.ocr_service.ocrmypdf.ocr", create=True) as mock_ocr, \
             patch("pathlib.Path.exists", return_value=True), \
             patch("pathlib.Path.read_text", return_value="test text"):
            
            # Создаём временный файл
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                test_pdf = Path(tmp.name)
            
            try:
                # Вызываем функцию
                run_ocr(test_pdf)
                
                # Проверяем, что ocrmypdf.ocr был вызван с правильными параметрами
                mock_ocr.assert_called()
                call_args = mock_ocr.call_args
                
                # Проверяем, что используется output_type='pdf'
                assert call_args[1]['output_type'] == 'pdf'
                
            finally:
                # Очищаем
                if test_pdf.exists():
                    test_pdf.unlink()

    def test_ocr_fallback_to_force_ocr(self):
        """Тест fallback на force_ocr при ошибке"""
        with patch("app.services.ocr_service.ocrmypdf.ocr", create=True) as mock_ocr, \
             patch("pathlib.Path.exists", return_value=True), \
             patch("pathlib.Path.read_text", return_value="test text"):
            
            # Первый вызов вызывает исключение
            mock_ocr.side_effect = [
                Exception("Ghostscript error"),  # Первый вызов
                None  # Второй вызов (fallback)
            ]
            
            # Создаём временный файл
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                test_pdf = Path(tmp.name)
            
            try:
                # Вызываем функцию
                run_ocr(test_pdf)
                
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
                
            finally:
                # Очищаем
                if test_pdf.exists():
                    test_pdf.unlink()

    def test_ocr_both_attempts_fail(self):
        """Тест что исключение пробрасывается если оба попытки не удались"""
        with patch("app.services.ocr_service.ocrmypdf.ocr", create=True) as mock_ocr:
            # Оба вызова вызывают исключение
            mock_ocr.side_effect = Exception("OCR failed")
            
            # Создаём временный файл
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                test_pdf = Path(tmp.name)
            
            try:
                # Проверяем, что исключение пробрасывается
                with pytest.raises(Exception):
                    run_ocr(test_pdf)
                
                # Проверяем, что ocrmypdf.ocr был вызван дважды
                assert mock_ocr.call_count == 2
                
            finally:
                # Очищаем
                if test_pdf.exists():
                    test_pdf.unlink()

    def test_ocr_parameters_correct(self):
        """Тест что все параметры OCR корректны"""
        with patch("app.services.ocr_service.ocrmypdf.ocr", create=True) as mock_ocr, \
             patch("pathlib.Path.exists", return_value=True), \
             patch("pathlib.Path.read_text", return_value="test text"):
            
            # Создаём временный файл
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                test_pdf = Path(tmp.name)
            
            try:
                # Вызываем функцию
                run_ocr(test_pdf)
                
                # Проверяем параметры
                call_args = mock_ocr.call_args
                expected_params = {
                    'language': 'rus+eng',
                    'skip_text': True,
                    'deskew': False,
                    'rotate_pages': False,
                    'remove_background': False,
                    'progress_bar': False,
                    'output_type': 'pdf'
                }
                
                for param, value in expected_params.items():
                    assert call_args[1][param] == value
                
            finally:
                # Очищаем
                if test_pdf.exists():
                    test_pdf.unlink()

    def test_ocr_sidecar_file_cleanup(self):
        """Тест что sidecar файл удаляется в finally блоке"""
        with patch("app.services.ocr_service.ocrmypdf.ocr", create=True) as mock_ocr, \
             patch("pathlib.Path.exists", return_value=True), \
             patch("pathlib.Path.read_text", return_value="test text"), \
             patch("pathlib.Path.unlink") as mock_unlink:
            
            # Создаём временный файл
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                test_pdf = Path(tmp.name)
            
            try:
                # Вызываем функцию
                run_ocr(test_pdf)
                
                # Проверяем, что unlink был вызван для sidecar файла
                mock_unlink.assert_called_with(missing_ok=True)
                
            finally:
                # Очищаем
                if test_pdf.exists():
                    test_pdf.unlink()

    @pytest.mark.asyncio
    async def test_perform_ocr_async(self):
        """Тест асинхронной функции perform_ocr"""
        with patch("app.services.ocr_service.run_ocr") as mock_run_ocr, \
             patch("asyncio.get_event_loop") as mock_get_loop:
            
            # Настраиваем моки
            mock_loop = MagicMock()
            mock_get_loop.return_value = mock_loop
            
            # Создаем корутину для run_in_executor
            async def mock_run_in_executor(*args, **kwargs):
                return (Path("/tmp/test.pdf"), "test text")
            
            mock_loop.run_in_executor = mock_run_in_executor
            
            # Вызываем асинхронную функцию
            result = await perform_ocr("/tmp/input.pdf")
            
            # Проверяем результат
            assert result == (Path("/tmp/test.pdf"), "test text")

    def test_ocr_with_different_language(self):
        """Тест что язык OCR настраивается правильно"""
        with patch("app.services.ocr_service.ocrmypdf.ocr", create=True) as mock_ocr, \
             patch("pathlib.Path.exists", return_value=True), \
             patch("pathlib.Path.read_text", return_value="test text"):
            
            # Создаём временный файл
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                test_pdf = Path(tmp.name)
            
            try:
                # Вызываем функцию
                run_ocr(test_pdf)
                
                # Проверяем, что язык установлен правильно
                call_args = mock_ocr.call_args
                assert call_args[1]['language'] == 'rus+eng'
                
            finally:
                # Очищаем
                if test_pdf.exists():
                    test_pdf.unlink()

    def test_ocr_error_logging(self):
        """Тест что ошибки логируются правильно"""
        with patch("app.services.ocr_service.ocrmypdf.ocr", create=True) as mock_ocr, \
             patch("app.services.ocr_service.log") as mock_log:
            
            # Настраиваем мок для вызова исключения
            mock_ocr.side_effect = Exception("OCR processing failed")
            
            # Создаём временный файл
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                test_pdf = Path(tmp.name)
            
            try:
                # Проверяем, что исключение пробрасывается
                with pytest.raises(Exception):
                    run_ocr(test_pdf)
                
                # Проверяем, что ошибка была залогирована
                mock_log.error.assert_called()
                error_call = mock_log.error.call_args
                assert "ocr_failed" in error_call[0][0]
                assert str(test_pdf) in error_call[1]['path']
                
            finally:
                # Очищаем
                if test_pdf.exists():
                    test_pdf.unlink() 