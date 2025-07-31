#!/usr/bin/env python3
"""
Скрипт для запуска всех тестов проекта
"""

import asyncio
import subprocess
import sys
import logging
from pathlib import Path
from datetime import datetime
import json
import argparse

# Добавляем корневую директорию в путь
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestRunner:
    """Класс для запуска всех тестов"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.results = {}
        self.start_time = datetime.now()
        
    def setup_logging(self):
        """Настройка логирования"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler('logs/test_runner.log', encoding='utf-8')
            ]
        )
    
    async def run_manual_tests(self) -> bool:
        """Запуск ручных тестов"""
        self.logger.info("🧪 Запуск ручных тестов...")
        
        try:
            # Импортируем и запускаем ручные тесты
            from scripts.manual_test_runner import ManualTestRunner
            
            runner = ManualTestRunner()
            success = await runner.run_all_tests()
            
            self.results['manual_tests'] = {
                'success': success,
                'timestamp': datetime.now().isoformat()
            }
            
            return success
        except Exception as e:
            self.logger.error(f"❌ Ошибка при запуске ручных тестов: {e}")
            self.results['manual_tests'] = {
                'success': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
            return False
    
    def run_unit_tests(self) -> bool:
        """Запуск модульных тестов"""
        self.logger.info("🧪 Запуск модульных тестов...")
        
        try:
            # Запускаем pytest с покрытием
            cmd = [
                sys.executable, "-m", "pytest",
                "tests/",
                "-v",
                "--tb=short",
                "--cov=app",
                "--cov-report=term-missing",
                "--cov-report=html:htmlcov",
                "--cov-report=xml",
                "--cov-fail-under=80",
                "-m", "not slow and not integration"
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            success = result.returncode == 0
            
            self.results['unit_tests'] = {
                'success': success,
                'return_code': result.returncode,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'timestamp': datetime.now().isoformat()
            }
            
            if success:
                self.logger.info("✅ Модульные тесты пройдены успешно")
            else:
                self.logger.error("❌ Модульные тесты провалены")
                self.logger.error(f"STDOUT: {result.stdout}")
                self.logger.error(f"STDERR: {result.stderr}")
            
            return success
        except Exception as e:
            self.logger.error(f"❌ Ошибка при запуске модульных тестов: {e}")
            self.results['unit_tests'] = {
                'success': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
            return False
    
    def run_integration_tests(self) -> bool:
        """Запуск интеграционных тестов"""
        self.logger.info("🧪 Запуск интеграционных тестов...")
        
        try:
            cmd = [
                sys.executable, "-m", "pytest",
                "tests/test_integration.py",
                "-v",
                "--tb=short",
                "-m", "integration"
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            success = result.returncode == 0
            
            self.results['integration_tests'] = {
                'success': success,
                'return_code': result.returncode,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'timestamp': datetime.now().isoformat()
            }
            
            if success:
                self.logger.info("✅ Интеграционные тесты пройдены успешно")
            else:
                self.logger.error("❌ Интеграционные тесты провалены")
                self.logger.error(f"STDOUT: {result.stdout}")
                self.logger.error(f"STDERR: {result.stderr}")
            
            return success
        except Exception as e:
            self.logger.error(f"❌ Ошибка при запуске интеграционных тестов: {e}")
            self.results['integration_tests'] = {
                'success': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
            return False
    
    def run_performance_tests(self) -> bool:
        """Запуск тестов производительности"""
        self.logger.info("🧪 Запуск тестов производительности...")
        
        try:
            cmd = [
                sys.executable, "-m", "pytest",
                "tests/test_performance.py",
                "-v",
                "--tb=short",
                "-m", "not slow"
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            success = result.returncode == 0
            
            self.results['performance_tests'] = {
                'success': success,
                'return_code': result.returncode,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'timestamp': datetime.now().isoformat()
            }
            
            if success:
                self.logger.info("✅ Тесты производительности пройдены успешно")
            else:
                self.logger.error("❌ Тесты производительности провалены")
                self.logger.error(f"STDOUT: {result.stdout}")
                self.logger.error(f"STDERR: {result.stderr}")
            
            return success
        except Exception as e:
            self.logger.error(f"❌ Ошибка при запуске тестов производительности: {e}")
            self.results['performance_tests'] = {
                'success': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
            return False
    
    def run_security_tests(self) -> bool:
        """Запуск тестов безопасности"""
        self.logger.info("🧪 Запуск тестов безопасности...")
        
        try:
            cmd = [
                sys.executable, "-m", "pytest",
                "tests/test_security.py",
                "-v",
                "--tb=short"
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            success = result.returncode == 0
            
            self.results['security_tests'] = {
                'success': success,
                'return_code': result.returncode,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'timestamp': datetime.now().isoformat()
            }
            
            if success:
                self.logger.info("✅ Тесты безопасности пройдены успешно")
            else:
                self.logger.error("❌ Тесты безопасности провалены")
                self.logger.error(f"STDOUT: {result.stdout}")
                self.logger.error(f"STDERR: {result.stderr}")
            
            return success
        except Exception as e:
            self.logger.error(f"❌ Ошибка при запуске тестов безопасности: {e}")
            self.results['security_tests'] = {
                'success': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
            return False
    
    def run_linting(self) -> bool:
        """Запуск линтера"""
        self.logger.info("🧪 Запуск линтера...")
        
        try:
            # Проверяем наличие flake8
            cmd = [sys.executable, "-m", "flake8", "app/", "tests/"]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            success = result.returncode == 0
            
            self.results['linting'] = {
                'success': success,
                'return_code': result.returncode,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'timestamp': datetime.now().isoformat()
            }
            
            if success:
                self.logger.info("✅ Линтинг пройден успешно")
            else:
                self.logger.warning("⚠️ Линтинг обнаружил проблемы")
                self.logger.warning(f"STDOUT: {result.stdout}")
            
            return success
        except Exception as e:
            self.logger.error(f"❌ Ошибка при запуске линтера: {e}")
            self.results['linting'] = {
                'success': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
            return False
    
    def run_type_checking(self) -> bool:
        """Запуск проверки типов"""
        self.logger.info("🧪 Запуск проверки типов...")
        
        try:
            cmd = [sys.executable, "-m", "mypy", "app/"]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            success = result.returncode == 0
            
            self.results['type_checking'] = {
                'success': success,
                'return_code': result.returncode,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'timestamp': datetime.now().isoformat()
            }
            
            if success:
                self.logger.info("✅ Проверка типов пройдена успешно")
            else:
                self.logger.warning("⚠️ Проверка типов обнаружила проблемы")
                self.logger.warning(f"STDOUT: {result.stdout}")
            
            return success
        except Exception as e:
            self.logger.error(f"❌ Ошибка при запуске проверки типов: {e}")
            self.results['type_checking'] = {
                'success': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
            return False
    
    def generate_report(self) -> bool:
        """Генерирует итоговый отчет"""
        end_time = datetime.now()
        duration = end_time - self.start_time
        
        # Подсчитываем результаты
        total_tests = len(self.results)
        passed_tests = sum(1 for result in self.results.values() if result.get('success', False))
        
        self.logger.info("\n" + "="*60)
        self.logger.info("📊 ИТОГОВЫЙ ОТЧЕТ О ТЕСТИРОВАНИИ")
        self.logger.info("="*60)
        
        for test_type, result in self.results.items():
            status = "✅ ПРОЙДЕН" if result.get('success', False) else "❌ ПРОВАЛЕН"
            self.logger.info(f"{status}: {test_type}")
        
        self.logger.info(f"\n📈 Статистика:")
        self.logger.info(f"   Всего тестовых категорий: {total_tests}")
        self.logger.info(f"   Пройдено: {passed_tests}")
        self.logger.info(f"   Провалено: {total_tests - passed_tests}")
        self.logger.info(f"   Время выполнения: {duration}")
        
        # Сохраняем отчет в файл
        report_data = {
            "timestamp": end_time.isoformat(),
            "duration_seconds": duration.total_seconds(),
            "total_test_categories": total_tests,
            "passed_categories": passed_tests,
            "failed_categories": total_tests - passed_tests,
            "results": self.results
        }
        
        report_file = Path("logs/comprehensive_test_report.json")
        report_file.parent.mkdir(exist_ok=True)
        
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, ensure_ascii=False, indent=2)
        
        self.logger.info(f"\n📄 Подробный отчет сохранен в: {report_file}")
        
        success_rate = (passed_tests / total_tests) * 100 if total_tests > 0 else 0
        self.logger.info(f"\n🎯 Общий процент успешности: {success_rate:.1f}%")
        
        if success_rate >= 80:
            self.logger.info("🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО!")
            return True
        else:
            self.logger.error("💥 НЕКОТОРЫЕ ТЕСТЫ ПРОВАЛЕНЫ!")
            return False
    
    async def run_all_tests(self, test_types: list = None) -> bool:
        """Запускает все тесты"""
        self.logger.info("🚀 Начинаем комплексное тестирование проекта")
        
        if test_types is None:
            test_types = ['manual', 'unit', 'integration', 'performance', 'security', 'linting', 'type_checking']
        
        test_functions = {
            'manual': self.run_manual_tests,
            'unit': self.run_unit_tests,
            'integration': self.run_integration_tests,
            'performance': self.run_performance_tests,
            'security': self.run_security_tests,
            'linting': self.run_linting,
            'type_checking': self.run_type_checking
        }
        
        for test_type in test_types:
            if test_type in test_functions:
                if asyncio.iscoroutinefunction(test_functions[test_type]):
                    await test_functions[test_type]()
                else:
                    test_functions[test_type]()
        
        return self.generate_report()


async def main():
    """Главная функция"""
    parser = argparse.ArgumentParser(description='Запуск всех тестов проекта')
    parser.add_argument('--tests', nargs='+', 
                       choices=['manual', 'unit', 'integration', 'performance', 'security', 'linting', 'type_checking'],
                       help='Типы тестов для запуска')
    parser.add_argument('--all', action='store_true', help='Запустить все тесты')
    
    args = parser.parse_args()
    
    runner = TestRunner()
    runner.setup_logging()
    
    if args.all or not args.tests:
        test_types = None  # Запустить все тесты
    else:
        test_types = args.tests
    
    success = await runner.run_all_tests(test_types)
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main()) 