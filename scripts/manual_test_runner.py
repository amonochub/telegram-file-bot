#!/usr/bin/env python3
"""
Скрипт для автоматизации ручного тестирования Telegram File Bot
"""

import asyncio
import logging
import sys
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
import json

# Добавляем корневую директорию в путь
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import settings
from app.services.yandex_disk_service import YandexDiskService
from app.services.cbr_rate_service import CBRRateService
from app.services.ocr_service import OCRService
from app.utils.file_validation import FileValidator


class ManualTestRunner:
    """Класс для выполнения ручных тестов"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.results: Dict[str, bool] = {}
        self.errors: List[str] = []
        self.start_time = datetime.now()
        
    async def run_all_tests(self) -> bool:
        """Запускает все ручные тесты"""
        self.logger.info("🚀 Начинаем ручное тестирование Telegram File Bot")
        
        tests = [
            ("test_config_loading", self.test_config_loading),
            ("test_yandex_disk_connection", self.test_yandex_disk_connection),
            ("test_cbr_api_connection", self.test_cbr_api_connection),
            ("test_ocr_service", self.test_ocr_service),
            ("test_file_validation", self.test_file_validation),
            ("test_directory_structure", self.test_directory_structure),
            ("test_environment_variables", self.test_environment_variables),
        ]
        
        for test_name, test_func in tests:
            try:
                self.logger.info(f"🧪 Выполняем тест: {test_name}")
                result = await test_func()
                self.results[test_name] = result
                status = "✅ ПРОЙДЕН" if result else "❌ ПРОВАЛЕН"
                self.logger.info(f"{status}: {test_name}")
            except Exception as e:
                self.logger.error(f"❌ ОШИБКА в тесте {test_name}: {e}")
                self.results[test_name] = False
                self.errors.append(f"{test_name}: {str(e)}")
        
        return await self.generate_report()
    
    async def test_config_loading(self) -> bool:
        """Тест загрузки конфигурации"""
        try:
            # Проверяем основные настройки
            assert settings.bot_token, "BOT_TOKEN не установлен"
            assert settings.log_level in ["DEBUG", "INFO", "WARNING", "ERROR"], "Неверный уровень логирования"
            assert settings.max_file_size > 0, "MAX_FILE_SIZE должен быть положительным"
            assert settings.cache_ttl > 0, "CACHE_TTL должен быть положительным"
            
            self.logger.info("✅ Конфигурация загружена корректно")
            return True
        except Exception as e:
            self.logger.error(f"❌ Ошибка загрузки конфигурации: {e}")
            return False
    
    async def test_yandex_disk_connection(self) -> bool:
        """Тест подключения к Яндекс.Диску"""
        if not settings.yandex_disk_token:
            self.logger.warning("⚠️ YANDEX_DISK_TOKEN не установлен - пропускаем тест")
            return True
        
        try:
            yandex_service = YandexDiskService(settings.yandex_disk_token)
            connected = await yandex_service.check_connection()
            
            if connected:
                self.logger.info("✅ Подключение к Яндекс.Диску успешно")
                return True
            else:
                self.logger.error("❌ Не удалось подключиться к Яндекс.Диску")
                return False
        except Exception as e:
            self.logger.error(f"❌ Ошибка подключения к Яндекс.Диску: {e}")
            return False
    
    async def test_cbr_api_connection(self) -> bool:
        """Тест подключения к API ЦБР"""
        try:
            cbr_service = CBRRateService()
            rates = await cbr_service.get_current_rates()
            
            if rates and len(rates) > 0:
                self.logger.info(f"✅ Получены курсы валют: {len(rates)} валют")
                return True
            else:
                self.logger.error("❌ Не удалось получить курсы валют")
                return False
        except Exception as e:
            self.logger.error(f"❌ Ошибка подключения к API ЦБР: {e}")
            return False
    
    async def test_ocr_service(self) -> bool:
        """Тест OCR сервиса"""
        try:
            ocr_service = OCRService()
            
            # Проверяем, что сервис инициализирован
            assert ocr_service is not None, "OCR сервис не инициализирован"
            
            self.logger.info("✅ OCR сервис инициализирован")
            return True
        except Exception as e:
            self.logger.error(f"❌ Ошибка инициализации OCR сервиса: {e}")
            return False
    
    async def test_file_validation(self) -> bool:
        """Тест валидации файлов"""
        try:
            validator = FileValidator()
            
            # Тестируем валидацию размера файла
            assert validator.validate_file_size(1024 * 1024) == True, "Файл 1MB должен быть валидным"
            assert validator.validate_file_size(settings.max_file_size + 1) == False, "Файл больше лимита должен быть невалидным"
            
            self.logger.info("✅ Валидация файлов работает корректно")
            return True
        except Exception as e:
            self.logger.error(f"❌ Ошибка валидации файлов: {e}")
            return False
    
    async def test_directory_structure(self) -> bool:
        """Тест структуры директорий"""
        try:
            required_dirs = ["temp", "logs"]
            required_files = ["app/main.py", "app/config.py", "requirements.txt"]
            
            # Проверяем директории
            for dir_name in required_dirs:
                dir_path = Path(dir_name)
                if not dir_path.exists():
                    dir_path.mkdir(exist_ok=True)
                    self.logger.info(f"📁 Создана директория: {dir_name}")
            
            # Проверяем файлы
            for file_path in required_files:
                if not Path(file_path).exists():
                    self.logger.error(f"❌ Отсутствует файл: {file_path}")
                    return False
            
            self.logger.info("✅ Структура директорий корректна")
            return True
        except Exception as e:
            self.logger.error(f"❌ Ошибка проверки структуры директорий: {e}")
            return False
    
    async def test_environment_variables(self) -> bool:
        """Тест переменных окружения"""
        try:
            required_vars = ["BOT_TOKEN"]
            optional_vars = ["YANDEX_DISK_TOKEN", "GEMINI_API_KEY", "ALLOWED_USER_ID"]
            
            # Проверяем обязательные переменные
            for var in required_vars:
                if not getattr(settings, var.lower(), None):
                    self.logger.error(f"❌ Отсутствует обязательная переменная: {var}")
                    return False
            
            # Проверяем опциональные переменные
            for var in optional_vars:
                value = getattr(settings, var.lower(), None)
                if value:
                    self.logger.info(f"✅ Найдена переменная: {var}")
                else:
                    self.logger.warning(f"⚠️ Отсутствует опциональная переменная: {var}")
            
            self.logger.info("✅ Переменные окружения проверены")
            return True
        except Exception as e:
            self.logger.error(f"❌ Ошибка проверки переменных окружения: {e}")
            return False
    
    async def generate_report(self) -> bool:
        """Генерирует отчет о тестировании"""
        end_time = datetime.now()
        duration = end_time - self.start_time
        
        passed_tests = sum(1 for result in self.results.values() if result)
        total_tests = len(self.results)
        
        self.logger.info("\n" + "="*50)
        self.logger.info("📊 ОТЧЕТ О РУЧНОМ ТЕСТИРОВАНИИ")
        self.logger.info("="*50)
        
        for test_name, result in self.results.items():
            status = "✅ ПРОЙДЕН" if result else "❌ ПРОВАЛЕН"
            self.logger.info(f"{status}: {test_name}")
        
        self.logger.info(f"\n📈 Статистика:")
        self.logger.info(f"   Всего тестов: {total_tests}")
        self.logger.info(f"   Пройдено: {passed_tests}")
        self.logger.info(f"   Провалено: {total_tests - passed_tests}")
        self.logger.info(f"   Время выполнения: {duration}")
        
        if self.errors:
            self.logger.info(f"\n❌ Ошибки:")
            for error in self.errors:
                self.logger.info(f"   - {error}")
        
        # Сохраняем отчет в файл
        report_data = {
            "timestamp": end_time.isoformat(),
            "duration_seconds": duration.total_seconds(),
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "failed_tests": total_tests - passed_tests,
            "results": self.results,
            "errors": self.errors
        }
        
        report_file = Path("logs/manual_test_report.json")
        report_file.parent.mkdir(exist_ok=True)
        
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, ensure_ascii=False, indent=2)
        
        self.logger.info(f"\n📄 Отчет сохранен в: {report_file}")
        
        success_rate = (passed_tests / total_tests) * 100 if total_tests > 0 else 0
        self.logger.info(f"\n🎯 Процент успешности: {success_rate:.1f}%")
        
        if success_rate >= 80:
            self.logger.info("🎉 ТЕСТИРОВАНИЕ ПРОЙДЕНО УСПЕШНО!")
            return True
        else:
            self.logger.error("💥 ТЕСТИРОВАНИЕ ПРОВАЛЕНО!")
            return False


async def main():
    """Главная функция"""
    # Настройка логирования
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('logs/manual_test.log', encoding='utf-8')
        ]
    )
    
    runner = ManualTestRunner()
    success = await runner.run_all_tests()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main()) 