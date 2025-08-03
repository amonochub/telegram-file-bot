#!/usr/bin/env python3
"""
Demo script for Enhanced Analyzer
Демонстрация возможностей расширенного анализатора
"""

import asyncio
import json
from app.services.enhanced_analyzer import analyze_document, get_analyzer_stats


async def demo_enhanced_analyzer():
    """Демонстрация расширенного анализатора"""
    print("🔍 Demo Enhanced Analyzer - Демонстрация расширенного анализатора")
    print("=" * 80)
    
    # Статистика анализатора
    stats = get_analyzer_stats()
    print("\n📊 Статистика анализатора:")
    for key, value in stats.items():
        print(f"   {key}: {value}")
    
    # Тестовые документы
    test_documents = [
        {
            "name": "Счет на оплату",
            "content": """
            СЧЕТ НА ОПЛАТУ №INV-2024-001
            
            От: ООО "Рога и Копыта"
            ИНН: 1234567890
            КПП: 123456789
            Расчетный счет: 40702810123456789012
            БИК: 044525225
            
            К оплате: 250,500.75 EUR
            Дата выставления: 15.03.2024
            Дата оплаты: до 01.04.2024
            
            IBAN: DE89370400440532013000
            SWIFT: DEUTDEFF
            
            Контакты:
            Email: accounting@example.com
            Телефон: +7 (495) 123-45-67
            """
        },
        {
            "name": "Договор поставки",
            "content": """
            ДОГОВОР ПОСТАВКИ №CON-2024-789
            
            Заказчик: ПАО "Газпром"
            ОГРН: 1027700070518
            ИНН: 7736050003
            
            Поставщик: ООО "Сервис+"
            ОГРН: 1234567890123
            
            Предмет договора: Поставка оборудования
            Сумма договора: 1,500,000.00 RUB
            Процент предоплаты: 50%
            Штраф за просрочку: 0.1% за каждый день
            
            Дата подписания: 01.02.2024
            Срок действия: до 31.12.2024
            Дата поставки: не позднее 15.06.2024
            """
        },
        {
            "name": "Банковская выписка",
            "content": """
            ВЫПИСКА ПО СЧЕТУ
            
            Банк: Сбербанк России
            БИК: 044525225
            Счет: 40702810400000123456
            
            Период: с 01.03.2024 по 31.03.2024
            
            Операции:
            05.03.2024 - Поступление 100,000.00 USD от ООО "Партнер"
            10.03.2024 - Списание 25,750.50 EUR на оплату инвойса №INV-001
            15.03.2024 - Поступление 500,000.00 ₽ от продажи
            20.03.2024 - Комиссия банка: 2.5%
            
            Остаток на конец периода: 1,234,567.89 RUB
            """
        }
    ]
    
    # Анализируем каждый документ
    for i, doc in enumerate(test_documents, 1):
        print(f"\n{i}. 📄 Анализ документа: {doc['name']}")
        print("-" * 60)
        
        result = await analyze_document(doc['content'], f"{doc['name']}.pdf")
        
        print(f"🎯 Тип документа: {result.document_type or 'Не определен'}")
        print(f"📊 Уверенность: {result.confidence_score:.1%}")
        print(f"⏱️ Время обработки: {result.processing_time:.3f}s")
        print(f"📝 Количество слов: {result.word_count}")
        
        # Извлеченные параметры
        if result.extracted_data:
            print("\n🔍 Извлеченные параметры:")
            for param_type, values in result.extracted_data.items():
                if values:
                    print(f"   {param_type}: {values}")
        
        # Финансовая информация
        if result.financial_summary and result.financial_summary.get("currencies_found"):
            print("\n💰 Финансовая информация:")
            print(f"   Валюты: {', '.join(result.financial_summary['currencies_found'])}")
            print(f"   Счетов: {result.financial_summary['accounts_count']}")
            print(f"   IBAN: {result.financial_summary['ibans_count']}")
            
            if result.financial_summary.get("total_amounts_by_currency"):
                print("   Суммы по валютам:")
                for curr, amount in result.financial_summary["total_amounts_by_currency"].items():
                    print(f"     {curr}: {amount:,.2f}")
        
        # Анализ дат
        if result.date_analysis and result.date_analysis.get("dates_count", 0) > 0:
            print("\n📅 Анализ дат:")
            print(f"   Найдено дат: {result.date_analysis['dates_count']}")
            if result.date_analysis.get("date_range"):
                print(f"   Период: {result.date_analysis['date_range']['earliest']} - {result.date_analysis['date_range']['latest']}")
                print(f"   Диапазон: {result.date_analysis['date_range']['span_days']} дней")
        
        # Валютные операции
        if result.currency_operations:
            print(f"\n💱 Валютные операции: {len(result.currency_operations)}")
            for op in result.currency_operations[:3]:  # Показываем первые 3
                print(f"   {op['type']}: {op.get('amount', 'N/A')}")
    
    print("\n" + "=" * 80)
    print("✅ Демонстрация завершена!")
    print("\n🎓 Возможности Enhanced Analyzer:")
    print("   • Извлечение 16+ типов параметров (IBAN, SWIFT, ИНН, телефоны, email)")
    print("   • Определение типа документа (счет, договор, выписка)")
    print("   • Финансовый анализ с группировкой по валютам")
    print("   • Анализ дат с вычислением периодов")
    print("   • Оценка уверенности в результатах")
    print("   • Структурированный результат в JSON-формате")


if __name__ == "__main__":
    asyncio.run(demo_enhanced_analyzer())