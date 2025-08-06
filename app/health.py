"""
Health check endpoint для мониторинга состояния бота
"""

import asyncio
import json
from datetime import datetime
from typing import Dict, Any, Optional
import aiohttp
import structlog

from app.config import settings

log = structlog.get_logger()


class HealthChecker:
    """Класс для проверки состояния различных компонентов системы"""
    
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        
    async def start(self):
        """Инициализация HTTP сессии"""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=10)
        )
        
    async def stop(self):
        """Закрытие HTTP сессии"""
        if self.session:
            await self.session.close()
    
    async def check_redis(self) -> Dict[str, Any]:
        """Проверка состояния Redis"""
        try:
            import redis.asyncio as redis
            
            # Создаем подключение к Redis
            redis_client = redis.from_url(settings.redis_url)
            
            # Проверяем ping
            start_time = datetime.utcnow()
            pong = await redis_client.ping()
            response_time = (datetime.utcnow() - start_time).total_seconds()
            
            # Получаем информацию о Redis
            info = await redis_client.info()
            
            await redis_client.close()
            
            return {
                "status": "healthy" if pong else "unhealthy",
                "response_time": response_time,
                "version": info.get("redis_version", "unknown"),
                "memory_used": info.get("used_memory_human", "unknown"),
                "connected_clients": info.get("connected_clients", 0),
                "uptime": info.get("uptime_in_seconds", 0)
            }
            
        except Exception as e:
            log.error("redis_health_check_failed", error=str(e))
            return {
                "status": "unhealthy",
                "error": str(e)
            }
    
    async def check_cbr_api(self) -> Dict[str, Any]:
        """Проверка доступности API ЦБ РФ"""
        try:
            if not self.session:
                raise Exception("HTTP session not initialized")
                
            # Формируем URL для проверки
            test_url = "https://www.cbr-xml-daily.ru/daily_json.js"
            
            start_time = datetime.utcnow()
            async with self.session.get(test_url) as response:
                response_time = (datetime.utcnow() - start_time).total_seconds()
                
                if response.status == 200:
                    data = await response.json()
                    return {
                        "status": "healthy",
                        "response_time": response_time,
                        "status_code": response.status,
                        "date": data.get("Date", "unknown"),
                        "timestamp": data.get("Timestamp", "unknown")
                    }
                else:
                    return {
                        "status": "unhealthy",
                        "response_time": response_time,
                        "status_code": response.status,
                        "error": f"HTTP {response.status}"
                    }
                    
        except Exception as e:
            log.error("cbr_api_health_check_failed", error=str(e))
            return {
                "status": "unhealthy",
                "error": str(e)
            }
    
    async def check_yandex_disk(self) -> Dict[str, Any]:
        """Проверка доступности Yandex.Disk API"""
        try:
            if not settings.yandex_disk_token:
                return {
                    "status": "skipped",
                    "reason": "No Yandex.Disk token configured"
                }
                
            if not self.session:
                raise Exception("HTTP session not initialized")
                
            headers = {
                "Authorization": f"OAuth {settings.yandex_disk_token}"
            }
            
            start_time = datetime.utcnow()
            async with self.session.get(
                "https://cloud-api.yandex.net/v1/disk/",
                headers=headers
            ) as response:
                response_time = (datetime.utcnow() - start_time).total_seconds()
                
                if response.status == 200:
                    data = await response.json()
                    return {
                        "status": "healthy",
                        "response_time": response_time,
                        "status_code": response.status,
                        "total_space": data.get("total_space", 0),
                        "used_space": data.get("used_space", 0),
                        "free_space": data.get("total_space", 0) - data.get("used_space", 0)
                    }
                else:
                    return {
                        "status": "unhealthy",
                        "response_time": response_time,
                        "status_code": response.status,
                        "error": f"HTTP {response.status}"
                    }
                    
        except Exception as e:
            log.error("yandex_disk_health_check_failed", error=str(e))
            return {
                "status": "unhealthy",
                "error": str(e)
            }
    
    async def check_system_resources(self) -> Dict[str, Any]:
        """Проверка системных ресурсов"""
        try:
            import psutil
            
            # CPU
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # Memory
            memory = psutil.virtual_memory()
            
            # Disk
            disk = psutil.disk_usage('/')
            
            return {
                "status": "healthy",
                "cpu_percent": cpu_percent,
                "memory": {
                    "total": memory.total,
                    "available": memory.available,
                    "percent": memory.percent,
                    "used": memory.used
                },
                "disk": {
                    "total": disk.total,
                    "used": disk.used,
                    "free": disk.free,
                    "percent": (disk.used / disk.total) * 100
                }
            }
            
        except ImportError:
            return {
                "status": "skipped",
                "reason": "psutil not available"
            }
        except Exception as e:
            log.error("system_resources_check_failed", error=str(e))
            return {
                "status": "unhealthy",
                "error": str(e)
            }
    
    async def comprehensive_health_check(self) -> Dict[str, Any]:
        """Комплексная проверка всех компонентов"""
        start_time = datetime.utcnow()
        
        # Запускаем все проверки параллельно
        checks = await asyncio.gather(
            self.check_redis(),
            self.check_cbr_api(),
            self.check_yandex_disk(),
            self.check_system_resources(),
            return_exceptions=True
        )
        
        redis_check, cbr_check, yandex_check, system_check = checks
        
        # Обрабатываем исключения
        for i, check in enumerate([redis_check, cbr_check, yandex_check, system_check]):
            if isinstance(check, Exception):
                checks[i] = {
                    "status": "error",
                    "error": str(check)
                }
        
        redis_check, cbr_check, yandex_check, system_check = checks
        
        # Определяем общий статус
        all_statuses = [
            redis_check.get("status"),
            cbr_check.get("status"),
            yandex_check.get("status"),
            system_check.get("status")
        ]
        
        # Считаем общий статус
        if any(status == "unhealthy" or status == "error" for status in all_statuses):
            overall_status = "unhealthy"
        elif all(status in ["healthy", "skipped"] for status in all_statuses):
            overall_status = "healthy"
        else:
            overall_status = "degraded"
        
        total_time = (datetime.utcnow() - start_time).total_seconds()
        
        result = {
            "status": overall_status,
            "timestamp": datetime.utcnow().isoformat(),
            "check_duration": total_time,
            "version": "1.0",
            "environment": getattr(settings, 'environment', 'development'),
            "services": {
                "redis": redis_check,
                "cbr_api": cbr_check,
                "yandex_disk": yandex_check,
                "system": system_check
            }
        }
        
        log.info("health_check_completed", 
                status=overall_status, 
                duration=total_time,
                services_count=len(result["services"]))
        
        return result


# Глобальный экземпляр health checker
health_checker = HealthChecker()


async def get_health_status() -> Dict[str, Any]:
    """Получить текущий статус здоровья системы"""
    return await health_checker.comprehensive_health_check()


async def simple_health_check() -> bool:
    """Простая проверка для Docker health check"""
    try:
        result = await health_checker.check_redis()
        return result.get("status") == "healthy"
    except Exception as e:
        log.error("simple_health_check_failed", error=str(e))
        return False
