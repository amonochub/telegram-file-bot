import asyncio
import logging
import os
from typing import Any, Dict, List

import fitz  # PyMuPDF
import ocrmypdf
import pytesseract
from PIL import Image

logger = logging.getLogger(__name__)


class OCRService:
    def __init__(self, languages: List[str] = None):
        self.languages = languages or ["rus", "eng"]
        self.tesseract_lang = "+".join(self.languages)
        self.logger = logger

    async def process_pdf_with_ocr(self, input_pdf_path: str, output_pdf_path: str = None) -> Dict[str, Any]:
        if not output_pdf_path:
            output_pdf_path = input_pdf_path.replace(".pdf", "_ocr.pdf")
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._run_ocrmypdf, input_pdf_path, output_pdf_path)
            extracted_text = await self.extract_text_from_pdf(output_pdf_path)
            result = {
                "success": True,
                "input_path": input_pdf_path,
                "output_path": output_pdf_path,
                "text": extracted_text,
                "pages_count": (len(extracted_text) if isinstance(extracted_text, list) else 1),
                "languages": self.languages,
            }
            self.logger.info(f"OCR обработка завершена: {input_pdf_path}")
            return result
        except Exception as e:
            self.logger.error(f"Ошибка OCR обработки {input_pdf_path}: {e}")
            return {"success": False, "error": str(e), "input_path": input_pdf_path}

    def _run_ocrmypdf(self, input_path: str, output_path: str):
        try:
            ocrmypdf.ocr(
                input_path,
                output_path,
                language=self.tesseract_lang,
                # Отключаем deskew для сохранения оригинального форматирования
                # deskew=True,
                # Отключаем clean для совместимости с macOS
                # clean=True,
                force_ocr=False,
                skip_text=False,
                redo_ocr=False,
                # Уменьшаем oversample для сохранения качества
                oversample=200,
                # Отключаем PDF/A конвертацию
                output_type="pdf",
            )
        except ocrmypdf.exceptions.ExitCode as e:
            if e.exit_code == ocrmypdf.ExitCode.already_done_ocr:
                import shutil

                shutil.copy2(input_path, output_path)
            else:
                raise RuntimeError(str(e)) from e  # type: ignore[misc]
        except Exception as e:
            # Логируем ошибку, но продолжаем обработку
            self.logger.warning(f"OCR processing warning: {e}")
            # Пробуем без дополнительных опций
            ocrmypdf.ocr(
                input_path,
                output_path,
                language=self.tesseract_lang,
                force_ocr=True,
                skip_text=False,
                redo_ocr=False,
                output_type="pdf",
            )

    async def extract_text_from_pdf(self, pdf_path: str) -> List[str]:
        try:
            loop = asyncio.get_event_loop()
            pages_text = await loop.run_in_executor(None, self._extract_pdf_text_sync, pdf_path)
            return pages_text
        except Exception as e:
            self.logger.error(f"Ошибка извлечения текста из {pdf_path}: {e}")
            return []

    def _extract_pdf_text_sync(self, pdf_path: str) -> List[str]:
        doc = fitz.open(pdf_path)
        pages_text = []
        for page_num in range(doc.page_count):
            page = doc[page_num]
            text = page.get_text()
            pages_text.append(text.strip())
        doc.close()
        return pages_text

    async def ocr_image_to_text(self, image_path: str) -> str:
        try:
            loop = asyncio.get_event_loop()
            text = await loop.run_in_executor(None, self._ocr_image_sync, image_path)
            return text.strip()
        except Exception as e:
            self.logger.error(f"Ошибка OCR изображения {image_path}: {e}")
            return ""

    def _ocr_image_sync(self, image_path: str) -> str:
        try:
            image = Image.open(image_path)
            text = pytesseract.image_to_string(image, lang=self.tesseract_lang, config="--psm 6")
            return text
        except Exception as e:
            self.logger.error(f"Ошибка pytesseract: {e}")
            return ""

    async def convert_pdf_to_images(self, pdf_path: str, output_dir: str) -> List[str]:
        try:
            os.makedirs(output_dir, exist_ok=True)
            loop = asyncio.get_event_loop()
            image_paths = await loop.run_in_executor(None, self._convert_pdf_to_images_sync, pdf_path, output_dir)
            return image_paths
        except Exception as e:
            self.logger.error(f"Ошибка конвертации PDF в изображения: {e}")
            return []

    def _convert_pdf_to_images_sync(self, pdf_path: str, output_dir: str) -> List[str]:
        doc = fitz.open(pdf_path)
        image_paths = []
        for page_num in range(doc.page_count):
            page = doc[page_num]
            mat = fitz.Matrix(2.0, 2.0)
            pix = page.get_pixmap(matrix=mat)
            image_path = os.path.join(output_dir, f"page_{page_num + 1}.png")
            pix.save(image_path)
            image_paths.append(image_path)
        doc.close()
        return image_paths

    def get_supported_languages(self) -> List[str]:
        try:
            languages = pytesseract.get_languages()
            return languages
        except Exception as e:
            self.logger.error(f"Ошибка получения списка языков: {e}")
            return ["eng"]

    # --- Дополнительно: экспорт текста в DOCX ---
    def text_to_docx(self, text: str, output_path: str) -> None:
        """Сохранить извлечённый текст в DOCX-файл."""
        try:
            from docx import Document

            doc = Document()
            for line in text.split("\n"):
                if line.strip():
                    doc.add_paragraph(line.strip())
            doc.save(output_path)
            self.logger.info("docx_saved", path=output_path)
        except Exception as e:  # pragma: no cover
            self.logger.error(f"Ошибка сохранения DOCX: {e}")

    # --- сжатие PDF ---
    def optimize_pdf(self, input_pdf: str, output_pdf: str) -> bool:
        """Оптимизировать PDF (сжать) с помощью ocrmypdf --optimize 3."""
        try:
            ocrmypdf.ocr(
                input_pdf,
                output_pdf,
                optimize=3,
                skip_text=True,
                force_ocr=False,
                redo_ocr=False,
            )
            return True
        except Exception as e:  # pragma: no cover
            self.logger.error(f"optimize_pdf_failed: {e}")
            return False

    def save_txt(self, text: str, output_path: str) -> None:
        try:
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(text)
            self.logger.info("txt_saved", path=output_path)
        except Exception as e:
            self.logger.error(f"Ошибка сохранения TXT: {e}")


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
        result = run_ocr(Path(pdf_path))
        return result
    except Exception as e:
        log.error(f"OCR processing error: {e}")
        raise
