"""
Enhanced Analyzer Service
Расширенный сервис анализа для извлечения и анализа данных из документов
"""

import re
import json
from collections import defaultdict, Counter
from typing import Dict, List, Optional, Tuple, Any, TypedDict
from dataclasses import dataclass
from datetime import datetime, date
import structlog

from app.utils.types import CurrencyCode, Amount
from app.services.analyzer import extract_parameters as basic_extract

log = structlog.get_logger(__name__)


class FinancialSummary(TypedDict):
    """Структура для финансового анализа"""
    currencies_found: List[str]
    amounts_found: List[Dict[str, Any]]
    total_amounts_by_currency: Dict[str, float]
    accounts_count: int
    ibans_count: int


class DateAnalysis(TypedDict):
    """Структура для анализа дат"""
    dates_count: int
    unique_dates: List[str]
    date_range: Optional[Dict[str, Any]]
    parsed_dates: List[Dict[str, Any]]


@dataclass
class AnalysisResult:
    """Результат анализа документа"""
    
    # Базовые параметры
    extracted_data: Dict[str, List[str]]
    
    # Расширенный анализ
    document_type: Optional[str] = None
    confidence_score: float = 0.0
    currency_operations: List[Dict[str, Any]] = None
    date_analysis: Optional[DateAnalysis] = None
    financial_summary: Optional[FinancialSummary] = None
    
    # Метаданные
    processing_time: float = 0.0
    word_count: int = 0
    analysis_timestamp: datetime = None
    
    def __post_init__(self):
        if self.currency_operations is None:
            self.currency_operations = []
        if self.analysis_timestamp is None:
            self.analysis_timestamp = datetime.now()


class EnhancedAnalyzer:
    """Расширенный анализатор документов"""
    
    # Расширенные паттерны для анализа
    ENHANCED_PATTERNS = {
        "iban": r"[A-Z]{2}\d{2}[A-Z0-9]{11,30}",
        "swift": r"[A-Z]{6}[A-Z0-9]{2}(?:[A-Z0-9]{3})?",
        "account": r"\b\d{10,20}\b",
        "number": r"№\s?\d+",
        "date": r"(?:0?[1-9]|[12][0-9]|3[01])[./-](?:0?[1-9]|1[0-2])[./-](?:\d{4})",
        "currency_amount": r"\d{1,3}(?:[ \u00A0]\d{3})*(?:[.,]\d{2})?\s?(?:EUR|USD|RUB|₽|€|\$)",
        "email": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
        "phone": r"(\+7|8)?[\s\-]?\(?[489][0-9]{2}\)?[\s\-]?[0-9]{3}[\s\-]?[0-9]{2}[\s\-]?[0-9]{2}",
        "inn": r"\b\d{10,12}\b",
        "kpp": r"\b\d{9}\b",
        "bik": r"\b04\d{7}\b",
        "ogrn": r"\b\d{13,15}\b",
        "passport": r"\b\d{4}\s?\d{6}\b",
        "card_number": r"\b\d{4}[\s\-]?\d{4}[\s\-]?\d{4}[\s\-]?\d{4}\b",
        "percentage": r"\d+(?:[.,]\d+)?%",
        "contract_number": r"(?:договор|contract|№)\s*[№#]?\s*([A-Za-z0-9\/\-]+)",
    }
    
    # Типы документов на основе ключевых слов
    DOCUMENT_TYPES = {
        "invoice": ["счет", "invoice", "инвойс", "к оплате", "итого"],
        "contract": ["договор", "contract", "соглашение", "agreement"],
        "bank_statement": ["выписка", "statement", "баланс", "остаток"],
        "payment_order": ["платежное поручение", "payment order", "перевод"],
        "receipt": ["чек", "receipt", "квитанция", "получение"],
        "report": ["отчет", "report", "анализ", "summary"],
    }
    
    def __init__(self):
        self.analysis_count = 0
        
    async def analyze_text(self, text: str, document_name: str = "") -> AnalysisResult:
        """
        Проводит комплексный анализ текста
        
        Args:
            text: Текст для анализа
            document_name: Имя документа (опционально)
            
        Returns:
            AnalysisResult: Результат анализа
        """
        start_time = datetime.now()
        self.analysis_count += 1
        
        try:
            log.info("enhanced_analysis_started", 
                    document=document_name, 
                    text_length=len(text),
                    analysis_number=self.analysis_count)
            
            # Базовое извлечение параметров
            extracted_data = self._extract_all_parameters(text)
            
            # Анализ типа документа
            document_type = self._detect_document_type(text)
            
            # Финансовый анализ
            financial_summary = self._analyze_financial_data(extracted_data, text)
            
            # Анализ валютных операций
            currency_operations = self._analyze_currency_operations(extracted_data, text)
            
            # Анализ дат
            date_analysis = self._analyze_dates(extracted_data)
            
            # Расчет уверенности
            confidence_score = self._calculate_confidence(extracted_data, text)
            
            # Подсчет времени обработки
            processing_time = (datetime.now() - start_time).total_seconds()
            
            result = AnalysisResult(
                extracted_data=extracted_data,
                document_type=document_type,
                confidence_score=confidence_score,
                currency_operations=currency_operations,
                date_analysis=date_analysis,
                financial_summary=financial_summary,
                processing_time=processing_time,
                word_count=len(text.split()),
                analysis_timestamp=start_time
            )
            
            log.info("enhanced_analysis_completed",
                    document_type=document_type,
                    confidence=confidence_score,
                    processing_time=processing_time,
                    parameters_found=sum(len(v) for v in extracted_data.values()))
            
            return result
            
        except Exception as e:
            log.error("enhanced_analysis_failed", 
                     error=str(e), 
                     document=document_name)
            # Возвращаем базовый результат в случае ошибки
            return AnalysisResult(
                extracted_data=self._extract_basic_parameters(text),
                confidence_score=0.1,
                processing_time=(datetime.now() - start_time).total_seconds()
            )
    
    def _extract_all_parameters(self, text: str) -> Dict[str, List[str]]:
        """Извлекает все параметры с использованием расширенных паттернов"""
        result = defaultdict(list)
        
        for key, pattern in self.ENHANCED_PATTERNS.items():
            try:
                matches = re.findall(pattern, text, flags=re.IGNORECASE | re.MULTILINE)
                if matches:
                    # Обработка кортежей из regex групп
                    if isinstance(matches[0], tuple):
                        matches = [match[0] if match[0] else match[1] for match in matches]
                    result[key].extend([str(match).strip() for match in matches if match])
            except Exception as e:
                log.warning("pattern_extraction_failed", pattern=key, error=str(e))
                
        return dict(result)
    
    def _extract_basic_parameters(self, text: str) -> Dict[str, List[str]]:
        """Fallback к базовому извлечению параметров"""
        try:
            return basic_extract(text)
        except:
            return {}
    
    def _detect_document_type(self, text: str) -> Optional[str]:
        """Определяет тип документа на основе ключевых слов"""
        text_lower = text.lower()
        
        # Подсчитываем совпадения для каждого типа документа
        type_scores = {}
        for doc_type, keywords in self.DOCUMENT_TYPES.items():
            score = sum(1 for keyword in keywords if keyword in text_lower)
            if score > 0:
                type_scores[doc_type] = score
        
        if type_scores:
            # Возвращаем тип с наибольшим количеством совпадений
            return max(type_scores.items(), key=lambda x: x[1])[0]
        
        return None
    
    def _analyze_financial_data(self, data: Dict[str, List[str]], text: str) -> FinancialSummary:
        """Анализирует финансовые данные"""
        summary: FinancialSummary = {
            "currencies_found": [],
            "amounts_found": [],
            "total_amounts_by_currency": {},
            "accounts_count": len(data.get("account", [])),
            "ibans_count": len(data.get("iban", [])),
        }
        
        # Анализируем валютные суммы
        currency_amounts = data.get("currency_amount", [])
        for amount_str in currency_amounts:
            try:
                # Простое извлечение валюты и суммы
                currency_match = re.search(r'(EUR|USD|RUB|₽|€|\$)', amount_str)
                amount_match = re.search(r'[\d\s.,]+', amount_str.replace(currency_match.group() if currency_match else '', ''))
                
                if currency_match and amount_match:
                    currency = currency_match.group()
                    amount_clean = re.sub(r'[^\d.,]', '', amount_match.group())
                    if amount_clean:
                        try:
                            amount_value = float(amount_clean.replace(',', '.'))
                        except ValueError:
                            amount_value = 0.0
                    else:
                        amount_value = 0.0
                    
                    currencies_found = summary["currencies_found"]
                    if currency not in currencies_found:
                        currencies_found.append(currency)
                    
                    amounts_found = summary["amounts_found"]
                    amounts_found.append({
                        "amount": amount_value,
                        "currency": currency,
                        "original": amount_str
                    })
                    
                    total_amounts = summary["total_amounts_by_currency"]
                    if currency not in total_amounts:
                        total_amounts[currency] = 0
                    total_amounts[currency] += amount_value
                    
            except Exception as e:
                log.warning("financial_analysis_item_failed", item=amount_str, error=str(e))
        
        return summary
    
    def _analyze_currency_operations(self, data: Dict[str, List[str]], text: str) -> List[Dict[str, Any]]:
        """Анализирует валютные операции"""
        operations = []
        
        # Ищем упоминания операций в тексте
        operation_patterns = {
            "transfer": ["перевод", "transfer", "отправка", "sending"],
            "payment": ["платеж", "payment", "оплата", "pay"],
            "exchange": ["обмен", "exchange", "конверт", "convert"],
            "receipt": ["получение", "receive", "поступление", "incoming"],
        }
        
        text_lower = text.lower()
        for op_type, keywords in operation_patterns.items():
            for keyword in keywords:
                if keyword in text_lower:
                    # Ищем ближайшие валютные суммы
                    nearby_amounts: list[str] = []
                    for amount in data.get("currency_amount", []):
                        operations.append({
                            "type": op_type,
                            "keyword": keyword,
                            "amount": amount,
                            "confidence": 0.7
                        })
        
        return operations
    
    def _analyze_dates(self, data: Dict[str, List[str]]) -> DateAnalysis:
        """Анализирует даты в документе"""
        dates = data.get("date", [])
        
        analysis: DateAnalysis = {
            "dates_count": len(dates),
            "unique_dates": list(set(dates)),
            "date_range": None,
            "parsed_dates": []
        }
        
        parsed_dates = []
        for date_str in dates:
            try:
                # Попытка парсинга различных форматов дат
                for fmt in ["%d.%m.%Y", "%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d"]:
                    try:
                        parsed_date = datetime.strptime(date_str, fmt).date()
                        parsed_dates.append(parsed_date)
                        analysis["parsed_dates"].append({
                            "original": date_str,
                            "parsed": parsed_date.isoformat(),
                            "format": fmt
                        })
                        break
                    except ValueError:
                        continue
            except Exception as e:
                log.warning("date_parsing_failed", date=date_str, error=str(e))
        
        if parsed_dates:
            analysis["date_range"] = {
                "earliest": min(parsed_dates).isoformat(),
                "latest": max(parsed_dates).isoformat(),
                "span_days": (max(parsed_dates) - min(parsed_dates)).days
            }
        
        return analysis
    
    def _calculate_confidence(self, data: Dict[str, List[str]], text: str) -> float:
        """Рассчитывает уверенность в анализе"""
        total_params = sum(len(v) for v in data.values())
        text_length = len(text.split())
        
        # Базовая уверенность на основе количества найденных параметров
        base_confidence = min(total_params / 10.0, 1.0)
        
        # Бонус за ключевые финансовые параметры
        key_params = ["iban", "swift", "account", "currency_amount"]
        key_found = sum(1 for key in key_params if data.get(key))
        key_bonus = key_found * 0.1
        
        # Штраф за слишком короткий или слишком длинный текст
        length_penalty = 0.0
        if text_length < 10:
            length_penalty = 0.3
        elif text_length > 10000:
            length_penalty = 0.1

        final_confidence = max(0.0, min(1.0, base_confidence + key_bonus - length_penalty))
        
        return round(final_confidence, 2)
    
    def get_analysis_statistics(self) -> Dict[str, Any]:
        """Возвращает статистику анализа"""
        return {
            "total_analyses": self.analysis_count,
            "patterns_available": len(self.ENHANCED_PATTERNS),
            "document_types_supported": len(self.DOCUMENT_TYPES),
            "analyzer_version": "1.0.0"
        }


# Глобальный экземпляр анализатора
enhanced_analyzer = EnhancedAnalyzer()


async def analyze_document(text: str, document_name: str = "") -> AnalysisResult:
    """
    Функция для анализа документа (высокоуровневый API)
    
    Args:
        text: Текст документа для анализа
        document_name: Имя документа (опционально)
        
    Returns:
        AnalysisResult: Результат анализа
    """
    return await enhanced_analyzer.analyze_text(text, document_name)


def get_analyzer_stats() -> Dict[str, Any]:
    """Получить статистику анализатора"""
    return enhanced_analyzer.get_analysis_statistics()