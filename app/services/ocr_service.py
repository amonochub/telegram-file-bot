import asyncio
import logging
import os
from typing import Any, Dict, List

import fitz  # PyMuPDF
import ocrmypdf
import pytesseract
from PIL import Image

logger = logging.getLogger(__name__)

# Удален неиспользуемый класс OCRService
# Используются только функции run_ocr и perform_ocr

from pathlib import Path
import tempfile
import structlog

log = structlog.get_logger(__name__)


def run_ocr(src: Path) -> tuple[Path, str]:
    """
    Запускает OCR, *сохраняя* оригинальный вид PDF.
    Возвращает путь к searchable-PDF и весь распознанный текст.
    """
    dst_pdf = Path(tempfile.mktemp(suffix="_ocr.pdf"))
    sidecar = Path(tempfile.mktemp(suffix=".txt"))

    try:
        ocrmypdf.ocr(
            src,
            dst_pdf,
            language="rus+eng",
            skip_text=True,  # если текст уже есть – не трогаем
            deskew=False,  # не крутим и не «чистим» страницы
            rotate_pages=False,
            remove_background=False,
            sidecar=str(sidecar),  # <— сюда кладётся plain-text
            progress_bar=False,
        )
        text = sidecar.read_text(encoding="utf-8", errors="ignore")
        return dst_pdf, text

    except Exception as e:
        log.error("ocr_failed", path=str(src), error=str(e))
        raise

    finally:
        if sidecar.exists():
            sidecar.unlink(missing_ok=True)


# Глобальные функции для использования в обработчиках
async def perform_ocr(pdf_path: str) -> tuple[Path, str]:
    """Выполняет OCR PDF документа и возвращает (путь к PDF, текст)"""
    try:
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, run_ocr, Path(pdf_path))
        return result
    except Exception as e:
        log.error("OCR processing error", error=str(e), pdf_path=pdf_path)
        raise
