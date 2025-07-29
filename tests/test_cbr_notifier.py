"""
Тесты для сервиса уведомлений о курсах ЦБ
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.cbr_notifier import CBRNotificationService


@pytest.mark.asyncio
async def test_subscribe_user():
    """Тест подписки пользователя на уведомления"""
    
    # Создаем мок для бота и Redis
    mock_bot = MagicMock()
    mock_redis = AsyncMock()
    
    with patch('app.services.cbr_notifier.aioredis.from_url', return_value=mock_redis):
        service = CBRNotificationService(mock_bot, "redis://localhost:6379")
        
        # Мокаем smembers для пустого списка подписчиков
        mock_redis.smembers.return_value = set()
        
        await service.connect()
        
        # Проверяем, что пользователь не подписан
        assert 123 not in service.subscribers
        
        # Подписываем пользователя
        await service.subscribe_user(123)
        
        # Проверяем, что пользователь добавлен в список
        assert 123 in service.subscribers
        
        # Проверяем, что команда добавления в Redis была вызвана
        mock_redis.sadd.assert_called_once_with("cbr_subscribers", 123)


@pytest.mark.asyncio
async def test_unsubscribe_user():
    """Тест отписки пользователя от уведомлений"""
    
    # Создаем мок для бота и Redis
    mock_bot = MagicMock()
    mock_redis = AsyncMock()
    
    with patch('app.services.cbr_notifier.aioredis.from_url', return_value=mock_redis):
        service = CBRNotificationService(mock_bot, "redis://localhost:6379")
        
        # Мокаем smembers для списка с одним подписчиком
        mock_redis.smembers.return_value = {"123"}
        
        await service.connect()
        
        # Проверяем, что пользователь подписан
        assert 123 in service.subscribers
        
        # Отписываем пользователя
        await service.unsubscribe_user(123)
        
        # Проверяем, что пользователь удален из списка
        assert 123 not in service.subscribers
        
        # Проверяем, что команда удаления из Redis была вызвана
        mock_redis.srem.assert_called_once_with("cbr_subscribers", 123) 