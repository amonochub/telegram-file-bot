#!/usr/bin/env python3
"""
Тест OCR функциональности с созданием тестового PDF
"""

import asyncio
import tempfile
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import os
import sys

# Добавляем путь к проекту
sys.path.insert(0, '/Users/amonoc/Library/Mobile Documents/com~apple~CloudDocs/VS_Code/telegram-file-bot')

async def create_test_pdf_with_text():
    """Создает тестовый PDF с текстом для OCR"""
    
    # Создаем изображение с текстом
    img = Image.new('RGB', (800, 600), color='white')
    draw = ImageDraw.Draw(img)
    
    # Пытаемся использовать системный шрифт
    try:
        # На macOS попробуем системные шрифты
        font_paths = [
            '/System/Library/Fonts/Arial.ttf',
            '/System/Library/Fonts/Helvetica.ttc',
            '/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf',
        ]
        
        font = None
        for font_path in font_paths:
            if os.path.exists(font_path):
                font = ImageFont.truetype(font_path, 40)
                break
        
        if font is None:
            font = ImageFont.load_default()
            print("⚠️ Используется шрифт по умолчанию")
    except:
        font = ImageFont.load_default()
        print("⚠️ Используется шрифт по умолчанию")
    
    # Добавляем текст на русском и английском
    text_lines = [
        "Тестовый документ для OCR",
        "Test document for OCR",
        "",
        "Содержание:",
        "1. Валютные операции",
        "2. Курс USD: 80.05 ₽",
        "3. Курс EUR: 92.51 ₽",
        "",
        "Content:",
        "• Currency exchange rates",
        "• Document processing",
        "• Text recognition test"
    ]
    
    y_position = 50
    for line in text_lines:
        if line.strip():  # Пропускаем пустые строки
            draw.text((50, y_position), line, fill='black', font=font)
        y_position += 45
    
    # Сохраняем как временный PNG
    with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as tmp_img:
        img_path = Path(tmp_img.name)
        img.save(img_path, 'PNG')
    
    # Конвертируем PNG в PDF
    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_pdf:
        pdf_path = Path(tmp_pdf.name)
        img.save(pdf_path, 'PDF')
    
    # Удаляем временный PNG
    img_path.unlink()
    
    print(f"📄 Создан тестовый PDF: {pdf_path}")
    return pdf_path

async def test_ocr_pipeline():
    """Тестирует полный pipeline OCR"""
    print("🧾 Тестирование OCR функциональности\n")
    
    try:
        # Создаем тестовый PDF
        test_pdf = await create_test_pdf_with_text()
        
        # Импортируем OCR функции
        from app.services.ocr_service import perform_ocr
        
        print("🔄 Выполняется OCR обработка...")
        
        # Выполняем OCR
        searchable_pdf, extracted_text = await perform_ocr(str(test_pdf))
        
        print(f"✅ OCR завершен успешно!")
        print(f"📂 Searchable PDF: {searchable_pdf}")
        print(f"📄 Размер исходного PDF: {test_pdf.stat().st_size} байт")
        print(f"📄 Размер обработанного PDF: {searchable_pdf.stat().st_size} байт")
        
        print("\n📝 Извлеченный текст:")
        print("-" * 50)
        print(extracted_text)
        print("-" * 50)
        
        # Проверяем качество распознавания
        keywords = ["Тестовый", "Test", "USD", "EUR", "валютные", "Currency"]
        found_keywords = [kw for kw in keywords if kw.lower() in extracted_text.lower()]
        
        print(f"\n🎯 Качество распознавания:")
        print(f"   Найдено ключевых слов: {len(found_keywords)}/{len(keywords)}")
        print(f"   Найденные: {', '.join(found_keywords)}")
        
        if len(found_keywords) >= len(keywords) * 0.7:  # 70% успешности
            print("✅ OCR работает корректно!")
        else:
            print("⚠️ Качество OCR ниже ожидаемого")
        
        # Очистка
        test_pdf.unlink()
        if searchable_pdf.exists():
            searchable_pdf.unlink()
            
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при тестировании OCR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    asyncio.run(test_ocr_pipeline())
