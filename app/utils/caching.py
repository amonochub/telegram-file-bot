"""
Enhanced caching utilities for the bot.

Provides in-memory caching with TTL, size limits, and statistics.
Supplements Redis caching for frequently accessed data.
"""

import time
from functools import wraps
from typing import Any, Callable, Dict, Optional, TypeVar

import structlog

log = structlog.get_logger(__name__)

F = TypeVar('F', bound=Callable[..., Any])


class CacheEntry:
    """Cache entry with expiration."""
    
    def __init__(self, value: Any, ttl: Optional[float] = None):
        self.value = value
        self.created_at = time.time()
        self.ttl = ttl
    
    def is_expired(self) -> bool:
        """Check if entry is expired."""
        if self.ttl is None:
            return False
        return time.time() - self.created_at > self.ttl
    
    @property
    def age(self) -> float:
        """Get entry age in seconds."""
        return time.time() - self.created_at


class LRUCache:
    """LRU cache with TTL and size limits."""
    
    def __init__(self, max_size: int = 1000, default_ttl: Optional[float] = None):
        self.max_size = max_size
        self.default_ttl = default_ttl
        self._cache: Dict[str, CacheEntry] = {}
        self._access_order: list = []
        self._stats = {
            'hits': 0,
            'misses': 0,
            'evictions': 0,
            'expired': 0,
        }
    
    def get(self, key: str) -> Any:
        """Get value from cache."""
        if key not in self._cache:
            self._stats['misses'] += 1
            return None
        
        entry = self._cache[key]
        
        # Check expiration
        if entry.is_expired():
            self._stats['expired'] += 1
            del self._cache[key]
            if key in self._access_order:
                self._access_order.remove(key)
            return None
        
        # Update access order
        if key in self._access_order:
            self._access_order.remove(key)
        self._access_order.append(key)
        
        self._stats['hits'] += 1
        return entry.value
    
    def set(self, key: str, value: Any, ttl: Optional[float] = None) -> None:
        """Set value in cache."""
        ttl = ttl or self.default_ttl
        
        # Remove existing entry
        if key in self._cache:
            if key in self._access_order:
                self._access_order.remove(key)
        
        # Add new entry
        self._cache[key] = CacheEntry(value, ttl)
        self._access_order.append(key)
        
        # Evict if necessary
        self._evict_if_necessary()
    
    def delete(self, key: str) -> bool:
        """Delete key from cache."""
        if key in self._cache:
            del self._cache[key]
            if key in self._access_order:
                self._access_order.remove(key)
            return True
        return False
    
    def clear(self) -> None:
        """Clear all cache entries."""
        self._cache.clear()
        self._access_order.clear()
    
    def _evict_if_necessary(self) -> None:
        """Evict oldest entries if cache is full."""
        while len(self._cache) > self.max_size:
            if not self._access_order:
                break
            
            oldest_key = self._access_order.pop(0)
            if oldest_key in self._cache:
                del self._cache[oldest_key]
                self._stats['evictions'] += 1
    
    def cleanup_expired(self) -> int:
        """Remove expired entries and return count."""
        expired_keys = []
        for key, entry in self._cache.items():
            if entry.is_expired():
                expired_keys.append(key)
        
        for key in expired_keys:
            self.delete(key)
            self._stats['expired'] += 1
        
        return len(expired_keys)
    
    def stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total_requests = self._stats['hits'] + self._stats['misses']
        hit_rate = self._stats['hits'] / total_requests if total_requests > 0 else 0
        
        return {
            'size': len(self._cache),
            'max_size': self.max_size,
            'hits': self._stats['hits'],
            'misses': self._stats['misses'],
            'hit_rate': f"{hit_rate:.2%}",
            'evictions': self._stats['evictions'],
            'expired': self._stats['expired'],
        }
    
    def keys(self) -> list:
        """Get all cache keys."""
        return list(self._cache.keys())


# Global cache instances
_file_cache = LRUCache(max_size=500, default_ttl=3600)  # 1 hour TTL
_api_cache = LRUCache(max_size=200, default_ttl=300)    # 5 minutes TTL
_user_cache = LRUCache(max_size=1000, default_ttl=1800) # 30 minutes TTL


def cached(
    cache_key: Optional[str] = None,
    ttl: Optional[float] = None,
    cache_type: str = "default",
) -> Callable[[F], F]:
    """
    Decorator for caching function results.
    
    Args:
        cache_key: Custom cache key (defaults to function name + args hash)
        ttl: TTL in seconds (defaults to cache's default)
        cache_type: Cache type ("file", "api", "user", "default")
        
    Usage:
        @cached(ttl=300, cache_type="api")
        async def fetch_data(param1, param2):
            # expensive operation
            return result
    """
    def decorator(func: F) -> F:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            # Get cache instance
            cache = _get_cache_instance(cache_type)
            
            # Generate cache key
            key = cache_key or _generate_cache_key(func.__name__, args, kwargs)
            
            # Try to get from cache
            cached_value = cache.get(key)
            if cached_value is not None:
                log.debug("Cache hit", function=func.__name__, key=key)
                return cached_value
            
            # Execute function
            log.debug("Cache miss", function=func.__name__, key=key)
            result = await func(*args, **kwargs)
            
            # Cache result
            cache.set(key, result, ttl)
            
            return result
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            # Get cache instance
            cache = _get_cache_instance(cache_type)
            
            # Generate cache key
            key = cache_key or _generate_cache_key(func.__name__, args, kwargs)
            
            # Try to get from cache
            cached_value = cache.get(key)
            if cached_value is not None:
                log.debug("Cache hit", function=func.__name__, key=key)
                return cached_value
            
            # Execute function
            log.debug("Cache miss", function=func.__name__, key=key)
            result = func(*args, **kwargs)
            
            # Cache result
            cache.set(key, result, ttl)
            
            return result
        
        # Return appropriate wrapper based on function type
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


def cache_clear(cache_type: str = "all") -> None:
    """Clear cache(s)."""
    if cache_type == "all":
        _file_cache.clear()
        _api_cache.clear()
        _user_cache.clear()
        log.info("All caches cleared")
    else:
        cache = _get_cache_instance(cache_type)
        cache.clear()
        log.info("Cache cleared", cache_type=cache_type)


def cache_stats(cache_type: str = "all") -> Dict[str, Any]:
    """Get cache statistics."""
    if cache_type == "all":
        return {
            "file": _file_cache.stats(),
            "api": _api_cache.stats(),
            "user": _user_cache.stats(),
        }
    else:
        cache = _get_cache_instance(cache_type)
        return cache.stats()


def cleanup_expired_entries() -> Dict[str, int]:
    """Clean up expired entries from all caches."""
    return {
        "file": _file_cache.cleanup_expired(),
        "api": _api_cache.cleanup_expired(),
        "user": _user_cache.cleanup_expired(),
    }


def _get_cache_instance(cache_type: str) -> LRUCache:
    """Get cache instance by type."""
    cache_map = {
        "file": _file_cache,
        "api": _api_cache,
        "user": _user_cache,
        "default": _api_cache,
    }
    return cache_map.get(cache_type, _api_cache)


def _generate_cache_key(func_name: str, args: tuple, kwargs: dict) -> str:
    """Generate cache key from function name and arguments."""
    import hashlib
    
    # Create string representation of arguments
    args_str = str(args) + str(sorted(kwargs.items()))
    
    # Hash the arguments to create a short key
    args_hash = hashlib.md5(args_str.encode()).hexdigest()[:8]
    
    return f"{func_name}:{args_hash}"