#!/usr/bin/env python3
"""
Продвинутый тест OCR с различными сценариями
"""

import asyncio
import tempfile
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import os
import sys

# Добавляем путь к проекту
sys.path.insert(0, '/Users/amonoc/Library/Mobile Documents/com~apple~CloudDocs/VS_Code/telegram-file-bot')

async def create_financial_document():
    """Создает тестовый финансовый документ"""
    
    img = Image.new('RGB', (800, 1000), color='white')
    draw = ImageDraw.Draw(img)
    
    # Получаем шрифт
    try:
        font_title = ImageFont.load_default()
        font_text = ImageFont.load_default()
    except:
        font_title = ImageFont.load_default()
        font_text = ImageFont.load_default()
    
    # Заголовок документа
    draw.text((50, 50), "ВАЛЮТНЫЕ ОПЕРАЦИИ", fill='black', font=font_title)
    draw.text((50, 80), "CURRENCY OPERATIONS", fill='black', font=font_title)
    
    # Линия разделитель
    draw.line([(50, 120), (750, 120)], fill='black', width=2)
    
    # Содержание документа
    content = [
        "",
        "Дата: 06.08.2025",
        "Date: 06.08.2025",
        "",
        "КУРСЫ ВАЛЮТ / EXCHANGE RATES:",
        "",
        "USD (Доллар США / US Dollar):",
        "  • Курс покупки: 79.85 ₽",
        "  • Курс продажи: 80.25 ₽",
        "  • Официальный курс ЦБ: 80.05 ₽",
        "",
        "EUR (Евро / Euro):",
        "  • Курс покупки: 92.10 ₽", 
        "  • Курс продажи: 92.90 ₽",
        "  • Официальный курс ЦБ: 92.51 ₽",
        "",
        "ОПЕРАЦИИ / OPERATIONS:",
        "",
        "1. Обмен валюты",
        "   Сумма: 1,000.00 USD",
        "   К получению: 79,850.00 ₽",
        "",
        "2. Currency exchange",
        "   Amount: 500.00 EUR",
        "   To receive: 46,050.00 ₽",
        "",
        "ИТОГО / TOTAL:",
        "Операций: 2",
        "Общая сумма: 125,900.00 ₽",
        "",
        "Комиссия: 2.5%",
        "Commission: 2.5%",
        "",
        "Документ подготовлен автоматически",
        "Document generated automatically"
    ]
    
    y_pos = 150
    for line in content:
        if line.strip():
            if line.startswith("КУРСЫ ВАЛЮТ") or line.startswith("ОПЕРАЦИИ") or line.startswith("ИТОГО"):
                # Заголовки разделов
                draw.text((50, y_pos), line, fill='black', font=font_title)
            elif line.startswith("  •") or line.startswith("   "):
                # Отступы для подпунктов
                draw.text((70, y_pos), line.strip(), fill='black', font=font_text)
            else:
                draw.text((50, y_pos), line, fill='black', font=font_text)
        y_pos += 25
    
    # Сохраняем как PDF
    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_pdf:
        pdf_path = Path(tmp_pdf.name)
        img.save(pdf_path, 'PDF')
    
    print(f"📄 Создан финансовый документ: {pdf_path}")
    return pdf_path

async def test_financial_ocr():
    """Тест OCR на финансовом документе"""
    print("💰 Тестирование OCR на финансовом документе\n")
    
    try:
        # Создаем тестовый документ
        doc_path = await create_financial_document()
        
        from app.services.ocr_service import perform_ocr
        
        print("🔄 Выполняется OCR финансового документа...")
        
        # Выполняем OCR
        searchable_pdf, extracted_text = await perform_ocr(str(doc_path))
        
        print("✅ OCR завершен!")
        
        # Анализируем результаты
        print("\n📊 Анализ распознанного текста:")
        print("-" * 60)
        print(extracted_text)
        print("-" * 60)
        
        # Проверяем ключевые элементы
        financial_keywords = [
            "валютные", "currency", "операции", "operations",
            "курс", "exchange", "доллар", "dollar", "евро", "euro",
            "покупки", "продажи", "официальный", "итого", "total",
            "комиссия", "commission", "сумма", "amount"
        ]
        
        numbers_patterns = ["79.85", "80.25", "80.05", "92.10", "92.90", "92.51", "1,000", "500", "2.5"]
        
        found_keywords = [kw for kw in financial_keywords if kw.lower() in extracted_text.lower()]
        found_numbers = [num for num in numbers_patterns if num in extracted_text]
        
        print(f"\n📈 Результаты анализа:")
        print(f"   Финансовые термины: {len(found_keywords)}/{len(financial_keywords)}")
        print(f"   Числовые данные: {len(found_numbers)}/{len(numbers_patterns)}")
        print(f"   Найденные термины: {', '.join(found_keywords[:10])}")
        print(f"   Найденные числа: {', '.join(found_numbers[:10])}")
        
        # Оценка качества
        keyword_score = len(found_keywords) / len(financial_keywords)
        number_score = len(found_numbers) / len(numbers_patterns)
        total_score = (keyword_score + number_score) / 2
        
        print(f"\n🎯 Оценка качества OCR: {total_score:.1%}")
        
        if total_score >= 0.7:
            print("✅ Отличное качество распознавания!")
        elif total_score >= 0.5:
            print("⚠️ Удовлетворительное качество распознавания")
        else:
            print("❌ Низкое качество распознавания")
        
        # Очистка
        doc_path.unlink()
        if searchable_pdf.exists():
            searchable_pdf.unlink()
            
        return total_score
        
    except Exception as e:
        print(f"❌ Ошибка при тестировании OCR: {e}")
        import traceback
        traceback.print_exc()
        return 0.0

async def test_ocr_error_handling():
    """Тест обработки ошибок в OCR"""
    print("\n🛡️ Тестирование обработки ошибок OCR")
    
    from app.services.ocr_service import perform_ocr
    
    # Тест с несуществующим файлом
    try:
        await perform_ocr("/несуществующий/файл.pdf")
        print("❌ Ошибка: должно было быть исключение для несуществующего файла")
    except Exception as e:
        print(f"✅ Корректно обработана ошибка несуществующего файла: {type(e).__name__}")
    
    # Тест с пустым файлом
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
            empty_path = tmp.name
        
        await perform_ocr(empty_path)
        print("⚠️ OCR обработал пустой файл без ошибки")
        os.unlink(empty_path)
    except Exception as e:
        print(f"✅ Корректно обработана ошибка пустого файла: {type(e).__name__}")
        os.unlink(empty_path)

async def main():
    """Основная функция тестирования"""
    print("🧾 Комплексное тестирование OCR системы")
    print("=" * 50)
    
    # Базовый тест
    score = await test_financial_ocr()
    
    # Тест обработки ошибок
    await test_ocr_error_handling()
    
    print("\n" + "=" * 50)
    if score >= 0.7:
        print("🎉 OCR система работает отлично!")
    elif score >= 0.5:
        print("✅ OCR система работает удовлетворительно")
    else:
        print("⚠️ OCR система требует улучшений")

if __name__ == "__main__":
    asyncio.run(main())
