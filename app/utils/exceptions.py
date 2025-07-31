"""
Кастомные исключения для приложения
"""


class FileValidationError(Exception):
    """Ошибка валидации файла"""

    def __init__(self, message: str, file_path: str = None, **kwargs):
        super().__init__(message)
        self.file_path = file_path
        self.details = kwargs


class CBRServiceError(Exception):
    """Ошибка сервиса курсов ЦБ"""

    def __init__(self, message: str, **kwargs):
        super().__init__(message)
        self.details = kwargs


class YandexDiskError(Exception):
    """Ошибка работы с Яндекс.Диском"""

    def __init__(self, message: str, operation: str = None, remote_path: str = None, **kwargs):
        super().__init__(message)
        self.operation = operation
        self.remote_path = remote_path
        self.details = kwargs


class OCRProcessingError(Exception):
    """Ошибка обработки OCR"""

    def __init__(self, message: str, file_path: str = None, language: str = None, **kwargs):
        super().__init__(message)
        self.file_path = file_path
        self.language = language
        self.details = kwargs


class ConfigurationError(Exception):
    """Ошибка конфигурации"""

    def __init__(self, message: str, **kwargs):
        super().__init__(message)
        self.details = kwargs


class UserNotAllowedError(Exception):
    """Пользователь не имеет доступа"""

    def __init__(self, message: str, user_id: int = None, **kwargs):
        super().__init__(message)
        self.user_id = user_id
        self.details = kwargs


class RateNotFoundError(Exception):
    """Курс валюты не найден"""

    def __init__(self, message: str, currency: str = None, date: str = None, **kwargs):
        super().__init__(message)
        self.currency = currency
        self.date = date
        self.details = kwargs


class CalculationError(Exception):
    """Ошибка в расчетах"""

    def __init__(self, message: str, **kwargs):
        super().__init__(message)
        self.details = kwargs


class ValidationError(Exception):
    """Ошибка валидации данных"""

    def __init__(self, message: str, field: str = None, value: str = None, **kwargs):
        super().__init__(message)
        self.field = field
        self.value = value
        self.details = kwargs
