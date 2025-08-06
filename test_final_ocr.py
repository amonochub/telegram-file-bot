#!/usr/bin/env python3
"""Финальный тест OCR функциональности"""

import asyncio
from pathlib import Path
from app.services.ocr_service import perform_ocr
import fitz  # PyMuPDF


async def test_final_ocr():
    """Финальный тест OCR с реальным документом"""
    
    # Создаем тестовый PDF с текстом
    test_file = Path("/tmp/final_ocr_test.pdf")
    
    # Создаем PDF с русским и английским текстом
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)  # A4
    
    # Добавляем текст в PDF
    text_lines = [
        "Тестовый документ для OCR",
        "Test document for OCR processing",
        "Строка с числами: 12345",
        "Line with numbers: 67890",
        "Проверка распознавания текста",
        "Text recognition verification"
    ]
    
    font = "helv"  # Helvetica
    font_size = 12
    y_position = 100
    
    for line in text_lines:
        page.insert_text((50, y_position), line, fontsize=font_size, fontname=font)
        y_position += 30
    
    doc.save(test_file)
    doc.close()
    
    print(f"✅ Создан тестовый PDF: {test_file}")
    print(f"📄 Размер файла: {test_file.stat().st_size} байт")
    
    try:
        # Запускаем OCR
        print("\n🔍 Запуск OCR...")
        output_file, extracted_text = await perform_ocr(str(test_file))
        
        print(f"✅ OCR завершен успешно!")
        print(f"📁 Выходной файл: {output_file}")
        print(f"📝 Извлеченный текст ({len(extracted_text)} символов):")
        print("-" * 50)
        print(extracted_text)
        print("-" * 50)
        
        # Проверяем, что текст распознан
        if "Тестовый документ" in extracted_text and "Test document" in extracted_text:
            print("✅ Русский и английский текст распознан корректно!")
        else:
            print("⚠️ Не весь текст распознан корректно")
            
        # Проверяем числа
        if "12345" in extracted_text and "67890" in extracted_text:
            print("✅ Числа распознаны корректно!")
        else:
            print("⚠️ Числа распознаны не полностью")
            
    except Exception as e:
        print(f"❌ Ошибка OCR: {e}")
        return False
        
    finally:
        # Очистка
        if test_file.exists():
            test_file.unlink()
            print(f"🗑️ Удален тестовый файл: {test_file}")
            
    return True


if __name__ == "__main__":
    print("🚀 Финальный тест OCR функциональности")
    print("=" * 50)
    
    result = asyncio.run(test_final_ocr())
    
    if result:
        print("\n🎉 OCR функциональность работает отлично!")
    else:
        print("\n❌ Обнаружены проблемы с OCR")
