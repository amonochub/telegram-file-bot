"""
Кастомные типы для улучшения типизации
"""

from typing import NewType
from decimal import Decimal
from datetime import date

# Семантически различные типы для предотвращения ошибок
UserId = NewType("UserId", int)
ChatId = NewType("ChatId", int)
FileSize = NewType("FileSize", int)
RateValue = NewType("RateValue", Decimal)
CurrencyCode = NewType("CurrencyCode", str)
FilePath = NewType("FilePath", str)
RemotePath = NewType("RemotePath", str)

# Типы для API
ApiResponse = NewType("ApiResponse", dict)
CacheKey = NewType("CacheKey", str)
SubscriptionKey = NewType("SubscriptionKey", str)

# Типы для валидации
ValidatedFilename = NewType("ValidatedFilename", str)
SanitizedFilename = NewType("SanitizedFilename", str)

# Типы для OCR
OcrText = NewType("OcrText", str)
OcrConfidence = NewType("OcrConfidence", float)

# Типы для расчетов
Amount = NewType("Amount", Decimal)
Commission = NewType("Commission", Decimal)
CalculationResult = NewType("CalculationResult", Decimal)

# Типы для дат
BusinessDate = NewType("BusinessDate", date)
FutureDate = NewType("FutureDate", date)
PastDate = NewType("PastDate", date)
