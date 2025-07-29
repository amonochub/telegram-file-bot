"""
Performance monitoring and metrics utilities.

Provides decorators and utilities for monitoring bot performance,
tracking response times, and collecting metrics.
"""

import time
from functools import wraps
from typing import Any, Callable, Dict, Optional, TypeVar

import structlog

log = structlog.get_logger(__name__)

F = TypeVar('F', bound=Callable[..., Any])


class PerformanceMetrics:
    """Simple performance metrics collector."""
    
    def __init__(self):
        self._metrics: Dict[str, list] = {}
        self._counters: Dict[str, int] = {}
    
    def record_time(self, name: str, duration: float) -> None:
        """Record timing metric."""
        if name not in self._metrics:
            self._metrics[name] = []
        self._metrics[name].append(duration)
    
    def increment_counter(self, name: str, value: int = 1) -> None:
        """Increment counter metric."""
        self._counters[name] = self._counters.get(name, 0) + value
    
    def get_stats(self, name: str) -> Dict[str, Any]:
        """Get statistics for a metric."""
        if name not in self._metrics or not self._metrics[name]:
            return {}
        
        times = self._metrics[name]
        return {
            'count': len(times),
            'avg': sum(times) / len(times),
            'min': min(times),
            'max': max(times),
            'total': sum(times),
        }
    
    def get_counter(self, name: str) -> int:
        """Get counter value."""
        return self._counters.get(name, 0)
    
    def reset(self) -> None:
        """Reset all metrics."""
        self._metrics.clear()
        self._counters.clear()


# Global metrics instance
metrics = PerformanceMetrics()


def monitor_performance(
    metric_name: Optional[str] = None,
    log_slow_threshold: float = 1.0,
    increment_counter: bool = True,
) -> Callable[[F], F]:
    """
    Decorator to monitor function performance.
    
    Args:
        metric_name: Name for the metric (defaults to function name)
        log_slow_threshold: Log warning if execution exceeds this time (seconds)
        increment_counter: Whether to increment call counter
        
    Usage:
        @monitor_performance("api_call", log_slow_threshold=2.0)
        async def call_api():
            # function code
    """
    def decorator(func: F) -> F:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            name = metric_name or func.__name__
            start_time = time.time()
            
            try:
                result = await func(*args, **kwargs)
                return result
            finally:
                duration = time.time() - start_time
                
                # Record metrics
                metrics.record_time(name, duration)
                if increment_counter:
                    metrics.increment_counter(f"{name}_calls")
                
                # Log slow operations
                if duration > log_slow_threshold:
                    log.warning(
                        "Slow operation detected",
                        function=name,
                        duration=f"{duration:.2f}s",
                        threshold=f"{log_slow_threshold}s",
                    )
                else:
                    log.debug(
                        "Function executed",
                        function=name,
                        duration=f"{duration:.3f}s",
                    )
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            name = metric_name or func.__name__
            start_time = time.time()
            
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                duration = time.time() - start_time
                
                # Record metrics
                metrics.record_time(name, duration)
                if increment_counter:
                    metrics.increment_counter(f"{name}_calls")
                
                # Log slow operations
                if duration > log_slow_threshold:
                    log.warning(
                        "Slow operation detected",
                        function=name,
                        duration=f"{duration:.2f}s",
                        threshold=f"{log_slow_threshold}s",
                    )
                else:
                    log.debug(
                        "Function executed",
                        function=name,
                        duration=f"{duration:.3f}s",
                    )
        
        # Return appropriate wrapper based on function type
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


def log_memory_usage(name: str) -> None:
    """Log current memory usage."""
    try:
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        memory_info = process.memory_info()
        
        log.info(
            "Memory usage",
            operation=name,
            rss_mb=f"{memory_info.rss / 1024 / 1024:.1f}",
            vms_mb=f"{memory_info.vms / 1024 / 1024:.1f}",
        )
    except ImportError:
        log.debug("psutil not available for memory monitoring")
    except Exception as e:
        log.warning("Failed to get memory usage", error=str(e))


def get_performance_summary() -> Dict[str, Any]:
    """Get performance summary for all metrics."""
    summary = {
        'timing_stats': {},
        'counters': dict(metrics._counters),
    }
    
    for name in metrics._metrics:
        summary['timing_stats'][name] = metrics.get_stats(name)
    
    return summary


def reset_metrics() -> None:
    """Reset all performance metrics."""
    metrics.reset()


# Context manager for measuring code blocks
class measure_time:
    """Context manager for measuring execution time."""
    
    def __init__(self, name: str, log_result: bool = True):
        self.name = name
        self.log_result = log_result
        self.start_time = 0
        self.duration = 0
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.duration = time.time() - self.start_time
        metrics.record_time(self.name, self.duration)
        
        if self.log_result:
            log.debug(
                "Code block executed",
                block=self.name,
                duration=f"{self.duration:.3f}s",
            )