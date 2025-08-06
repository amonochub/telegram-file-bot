#!/usr/bin/env python3
"""
Простой тест ЦБ API без Redis
"""

import asyncio
import aiohttp
from datetime import date
import xml.etree.ElementTree as ET

CBR_URL = "https://www.cbr.ru/scripts/XML_daily.asp?date_req={for_date}"

ISO2CBR = {
    "USD": "R01235",
    "EUR": "R01239", 
    "CNY": "R01375",
    "AED": "R01230",
    "TRY": "R01700J",
}

async def get_cbr_rate(currency="USD"):
    """Получить курс валюты из ЦБ"""
    try:
        today = date.today()
        date_req = today.strftime("%d/%m/%Y")
        url = CBR_URL.format(for_date=date_req)
        
        print(f"🔗 Запрос к ЦБ: {url}")
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status != 200:
                    print(f"❌ HTTP ошибка: {resp.status}")
                    return None
                    
                xml_text = await resp.text()
                
        # Парсим XML
        tree = ET.fromstring(xml_text)
        
        # Извлекаем дату
        date_str = tree.get("Date", "")
        print(f"📅 Дата курса: {date_str}")
        
        # Ищем валюту
        cbr_id = ISO2CBR.get(currency)
        if not cbr_id:
            print(f"❌ Валюта {currency} не поддерживается")
            return None
            
        valute = tree.find(f".//Valute[@ID='{cbr_id}']")
        if valute is None:
            print(f"❌ Валюта {currency} не найдена в ответе ЦБ")
            return None
            
        value_elem = valute.find("Value")
        nominal_elem = valute.find("Nominal")
        
        if value_elem is None or nominal_elem is None:
            print(f"❌ Отсутствуют данные для {currency}")
            return None
            
        value = float(value_elem.text.replace(",", "."))
        nominal = int(nominal_elem.text)
        rate = value / nominal
        
        print(f"✅ Курс {currency}: {rate:.4f} ₽")
        return rate
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return None

async def main():
    """Основная функция тестирования"""
    print("🏦 Тест курсов ЦБ РФ\n")
    
    currencies = ["USD", "EUR", "CNY", "AED", "TRY"]
    
    for currency in currencies:
        rate = await get_cbr_rate(currency)
        if rate:
            print(f"💱 {currency}: {rate:.4f} ₽")
        else:
            print(f"❌ {currency}: Не удалось получить курс")
        print()

if __name__ == "__main__":
    asyncio.run(main())
