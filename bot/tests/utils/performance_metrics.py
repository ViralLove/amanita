import time
import psutil
import functools
import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)

@dataclass
class PerformanceMetrics:
    """Класс для сбора метрик производительности"""
    test_name: str
    start_time: float = field(default_factory=time.perf_counter)
    end_time: Optional[float] = None
    memory_before: Optional[int] = None
    memory_after: Optional[int] = None
    memory_peak: Optional[int] = None
    cpu_percent: Optional[float] = None
    
    def __post_init__(self):
        self.memory_before = psutil.Process().memory_info().rss
    
    def finish(self):
        """Завершает измерение метрик"""
        self.end_time = time.perf_counter()
        self.memory_after = psutil.Process().memory_info().rss
        self.memory_peak = psutil.Process().memory_info().rss  # Упрощенная версия
        self.cpu_percent = psutil.Process().cpu_percent()
    
    @property
    def execution_time(self) -> float:
        """Время выполнения в секундах"""
        if self.end_time is None:
            return time.perf_counter() - self.start_time
        return self.end_time - self.start_time
    
    @property
    def memory_usage(self) -> int:
        """Использование памяти в байтах"""
        if self.memory_after is None:
            return psutil.Process().memory_info().rss - self.memory_before
        return self.memory_after - self.memory_before
    
    @property
    def memory_usage_mb(self) -> float:
        """Использование памяти в мегабайтах"""
        return self.memory_usage / 1024 / 1024
    
    def to_dict(self) -> Dict[str, Any]:
        """Преобразует метрики в словарь"""
        return {
            "test_name": self.test_name,
            "execution_time_seconds": round(self.execution_time, 3),
            "memory_usage_mb": round(self.memory_usage_mb, 2),
            "memory_peak_mb": round(self.memory_peak / 1024 / 1024, 2) if self.memory_peak else None,
            "cpu_percent": round(self.cpu_percent, 1) if self.cpu_percent else None,
            "timestamp": datetime.now().isoformat()
        }
    
    def log_metrics(self):
        """Логирует метрики в структурированном виде"""
        metrics_dict = self.to_dict()
        logger.info(f"📊 МЕТРИКИ ПРОИЗВОДИТЕЛЬНОСТИ: {self.test_name}")
        logger.info(f"   ⏱️  Время выполнения: {metrics_dict['execution_time_seconds']} сек")
        logger.info(f"   💾 Использование памяти: {metrics_dict['memory_usage_mb']} МБ")
        if metrics_dict['memory_peak_mb']:
            logger.info(f"   📈 Пиковое использование памяти: {metrics_dict['memory_peak_mb']} МБ")
        if metrics_dict['cpu_percent']:
            logger.info(f"   🖥️  Использование CPU: {metrics_dict['cpu_percent']}%")

def measure_performance(test_name: Optional[str] = None):
    """
    Декоратор для автоматического измерения производительности тестов
    
    Args:
        test_name: Имя теста для логирования (если не указано, берется из функции)
    """
    def decorator(func):
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            name = test_name or func.__name__
            metrics = PerformanceMetrics(name)
            
            try:
                logger.info(f"🚀 Начинаем измерение производительности: {name}")
                result = await func(*args, **kwargs)
                return result
            finally:
                metrics.finish()
                metrics.log_metrics()
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            name = test_name or func.__name__
            metrics = PerformanceMetrics(name)
            
            try:
                logger.info(f"🚀 Начинаем измерение производительности: {name}")
                result = func(*args, **kwargs)
                return result
            finally:
                metrics.finish()
                metrics.log_metrics()
        
        # Возвращаем соответствующую обертку в зависимости от типа функции
        if hasattr(func, '__code__') and func.__code__.co_flags & 0x80:  # CO_COROUTINE
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator

def measure_fixture_performance(fixture_name: Optional[str] = None):
    """
    Декоратор для измерения производительности фикстур
    
    Args:
        fixture_name: Имя фикстуры для логирования
    """
    def decorator(func):
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            name = fixture_name or func.__name__
            metrics = PerformanceMetrics(f"fixture_{name}")
            
            try:
                logger.info(f"🔧 Начинаем измерение производительности фикстуры: {name}")
                result = await func(*args, **kwargs)
                return result
            finally:
                metrics.finish()
                metrics.log_metrics()
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            name = fixture_name or func.__name__
            metrics = PerformanceMetrics(f"fixture_{name}")
            
            try:
                logger.info(f"🔧 Начинаем измерение производительности фикстуры: {name}")
                result = func(*args, **kwargs)
                return result
            finally:
                metrics.finish()
                metrics.log_metrics()
        
        # Возвращаем соответствующую обертку
        if hasattr(func, '__code__') and func.__code__.co_flags & 0x80:  # CO_COROUTINE
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator

class PerformanceCollector:
    """Класс для сбора и анализа метрик производительности"""
    
    def __init__(self):
        self.metrics: list[PerformanceMetrics] = []
    
    def add_metrics(self, metrics: PerformanceMetrics):
        """Добавляет метрики в коллектор"""
        self.metrics.append(metrics)
    
    def get_summary(self) -> Dict[str, Any]:
        """Возвращает сводку по всем метрикам"""
        if not self.metrics:
            return {}
        
        execution_times = [m.execution_time for m in self.metrics]
        memory_usages = [m.memory_usage_mb for m in self.metrics]
        
        return {
            "total_tests": len(self.metrics),
            "avg_execution_time": round(sum(execution_times) / len(execution_times), 3),
            "min_execution_time": round(min(execution_times), 3),
            "max_execution_time": round(max(execution_times), 3),
            "avg_memory_usage": round(sum(memory_usages) / len(memory_usages), 2),
            "min_memory_usage": round(min(memory_usages), 2),
            "max_memory_usage": round(max(memory_usages), 2),
            "timestamp": datetime.now().isoformat()
        }
    
    def log_summary(self):
        """Логирует сводку метрик"""
        summary = self.get_summary()
        if not summary:
            return
        
        logger.info("📊 СВОДКА МЕТРИК ПРОИЗВОДИТЕЛЬНОСТИ:")
        logger.info(f"   📈 Всего тестов: {summary['total_tests']}")
        logger.info(f"   ⏱️  Среднее время выполнения: {summary['avg_execution_time']} сек")
        logger.info(f"   ⏱️  Минимальное время: {summary['min_execution_time']} сек")
        logger.info(f"   ⏱️  Максимальное время: {summary['max_execution_time']} сек")
        logger.info(f"   💾 Среднее использование памяти: {summary['avg_memory_usage']} МБ")
        logger.info(f"   💾 Минимальное использование памяти: {summary['min_memory_usage']} МБ")
        logger.info(f"   💾 Максимальное использование памяти: {summary['max_memory_usage']} МБ")

# Глобальный экземпляр коллектора
performance_collector = PerformanceCollector() 