"""
Система метрик ошибок для ImageService.
Обеспечивает сбор статистики и мониторинг ошибок.
"""

import time
import logging
from typing import Dict, List, Optional, Any, Counter
from dataclasses import dataclass, field
from collections import defaultdict, deque
from threading import Lock

from .exceptions import ErrorCategory, ErrorSeverity
from .error_codes import ErrorCodeInfo, get_error_code_registry


@dataclass
class ErrorMetric:
    """Метрика ошибки."""
    error_code: str
    category: ErrorCategory
    severity: ErrorSeverity
    timestamp: float
    context: Dict[str, Any] = field(default_factory=dict)
    retry_count: int = 0
    fallback_used: bool = False


@dataclass
class ErrorStats:
    """Статистика ошибок."""
    total_errors: int = 0
    errors_by_category: Dict[str, int] = field(default_factory=dict)
    errors_by_severity: Dict[str, int] = field(default_factory=dict)
    errors_by_code: Dict[str, int] = field(default_factory=dict)
    retry_attempts: int = 0
    fallback_uses: int = 0
    last_error_time: Optional[float] = None
    error_rate_per_minute: float = 0.0


class ErrorMetrics:
    """
    Система метрик ошибок.
    
    Обеспечивает:
    - Сбор статистики ошибок
    - Агрегацию по категориям и уровням
    - Расчет error rate
    - Мониторинг retry и fallback операций
    """
    
    def __init__(self, max_history_size: int = 1000):
        """
        Инициализация системы метрик.
        
        Args:
            max_history_size: Максимальный размер истории ошибок
        """
        self.max_history_size = max_history_size
        self.logger = logging.getLogger(__name__)
        
        # История ошибок
        self._error_history: deque = deque(maxlen=max_history_size)
        
        # Счетчики
        self._error_counters: Dict[str, int] = defaultdict(int)
        self._category_counters: Dict[ErrorCategory, int] = defaultdict(int)
        self._severity_counters: Dict[ErrorSeverity, int] = defaultdict(int)
        
        # Метрики retry и fallback
        self._retry_counters: Dict[str, int] = defaultdict(int)
        self._fallback_counters: Dict[str, int] = defaultdict(int)
        
        # Блокировка для thread safety
        self._lock = Lock()
        
        # Время начала сбора метрик
        self._start_time = time.time()
        
        self.logger.info(f"[ErrorMetrics] Инициализирован с max_history_size={max_history_size}")
    
    def record_error(
        self,
        error_code: str,
        category: ErrorCategory,
        severity: ErrorSeverity,
        context: Optional[Dict[str, Any]] = None,
        retry_count: int = 0,
        fallback_used: bool = False
    ) -> None:
        """
        Записывает ошибку в метрики.
        
        Args:
            error_code: Код ошибки
            category: Категория ошибки
            severity: Уровень серьезности
            context: Контекст ошибки
            retry_count: Количество retry попыток
            fallback_used: Использовался ли fallback
        """
        with self._lock:
            timestamp = time.time()
            
            # Создаем метрику
            metric = ErrorMetric(
                error_code=error_code,
                category=category,
                severity=severity,
                timestamp=timestamp,
                context=context or {},
                retry_count=retry_count,
                fallback_used=fallback_used
            )
            
            # Добавляем в историю
            self._error_history.append(metric)
            
            # Обновляем счетчики
            self._error_counters[error_code] += 1
            self._category_counters[category] += 1
            self._severity_counters[severity] += 1
            
            # Обновляем retry и fallback счетчики
            if retry_count > 0:
                self._retry_counters[error_code] += retry_count
            
            if fallback_used:
                self._fallback_counters[error_code] += 1
            
            self.logger.debug(f"Recorded error: {error_code} (category: {category.value}, severity: {severity.value})")
    
    def get_error_stats(self) -> ErrorStats:
        """
        Получает статистику ошибок.
        
        Returns:
            ErrorStats: Статистика ошибок
        """
        with self._lock:
            total_errors = len(self._error_history)
            
            # Агрегация по категориям
            errors_by_category = {
                category.value: count 
                for category, count in self._category_counters.items()
            }
            
            # Агрегация по уровням серьезности
            errors_by_severity = {
                severity.value: count 
                for severity, count in self._severity_counters.items()
            }
            
            # Агрегация по кодам
            errors_by_code = dict(self._error_counters)
            
            # Общие retry и fallback метрики
            total_retry_attempts = sum(self._retry_counters.values())
            total_fallback_uses = sum(self._fallback_counters.values())
            
            # Время последней ошибки
            last_error_time = None
            if self._error_history:
                last_error_time = self._error_history[-1].timestamp
            
            # Расчет error rate
            current_time = time.time()
            time_elapsed = current_time - self._start_time
            error_rate_per_minute = (total_errors / time_elapsed) * 60 if time_elapsed > 0 else 0.0
            
            return ErrorStats(
                total_errors=total_errors,
                errors_by_category=errors_by_category,
                errors_by_severity=errors_by_severity,
                errors_by_code=errors_by_code,
                retry_attempts=total_retry_attempts,
                fallback_uses=total_fallback_uses,
                last_error_time=last_error_time,
                error_rate_per_minute=error_rate_per_minute
            )
    
    def get_errors_by_category(self, category: ErrorCategory) -> List[ErrorMetric]:
        """
        Получает ошибки по категории.
        
        Args:
            category: Категория ошибки
            
        Returns:
            List[ErrorMetric]: Список ошибок
        """
        with self._lock:
            return [
                metric for metric in self._error_history 
                if metric.category == category
            ]
    
    def get_errors_by_severity(self, severity: ErrorSeverity) -> List[ErrorMetric]:
        """
        Получает ошибки по уровню серьезности.
        
        Args:
            severity: Уровень серьезности
            
        Returns:
            List[ErrorMetric]: Список ошибок
        """
        with self._lock:
            return [
                metric for metric in self._error_history 
                if metric.severity == severity
            ]
    
    def get_errors_by_code(self, error_code: str) -> List[ErrorMetric]:
        """
        Получает ошибки по коду.
        
        Args:
            error_code: Код ошибки
            
        Returns:
            List[ErrorMetric]: Список ошибок
        """
        with self._lock:
            return [
                metric for metric in self._error_history 
                if metric.error_code == error_code
            ]
    
    def get_recent_errors(self, minutes: int = 5) -> List[ErrorMetric]:
        """
        Получает недавние ошибки.
        
        Args:
            minutes: Количество минут назад
            
        Returns:
            List[ErrorMetric]: Список недавних ошибок
        """
        with self._lock:
            cutoff_time = time.time() - (minutes * 60)
            return [
                metric for metric in self._error_history 
                if metric.timestamp >= cutoff_time
            ]
    
    def get_retry_stats(self) -> Dict[str, int]:
        """
        Получает статистику retry операций.
        
        Returns:
            Dict[str, int]: Статистика retry по кодам ошибок
        """
        with self._lock:
            return dict(self._retry_counters)
    
    def get_fallback_stats(self) -> Dict[str, int]:
        """
        Получает статистику fallback операций.
        
        Returns:
            Dict[str, int]: Статистика fallback по кодам ошибок
        """
        with self._lock:
            return dict(self._fallback_counters)
    
    def get_error_rate(self, window_minutes: int = 5) -> float:
        """
        Получает error rate за указанный период.
        
        Args:
            window_minutes: Окно времени в минутах
            
        Returns:
            float: Error rate (ошибок в минуту)
        """
        recent_errors = self.get_recent_errors(window_minutes)
        return len(recent_errors) / window_minutes
    
    def get_top_errors(self, limit: int = 10) -> List[tuple]:
        """
        Получает топ ошибок по частоте.
        
        Args:
            limit: Максимальное количество
            
        Returns:
            List[tuple]: Список (error_code, count) отсортированный по убыванию
        """
        with self._lock:
            return sorted(
                self._error_counters.items(),
                key=lambda x: x[1],
                reverse=True
            )[:limit]
    
    def get_health_score(self) -> float:
        """
        Получает health score системы (0.0 - 1.0).
        
        Returns:
            float: Health score (1.0 = отлично, 0.0 = критично)
        """
        stats = self.get_error_stats()
        
        if stats.total_errors == 0:
            return 1.0
        
        # Штрафы за разные типы ошибок
        critical_penalty = stats.errors_by_severity.get(ErrorSeverity.CRITICAL.value, 0) * 0.3
        error_penalty = stats.errors_by_severity.get(ErrorSeverity.ERROR.value, 0) * 0.1
        warning_penalty = stats.errors_by_severity.get(ErrorSeverity.WARNING.value, 0) * 0.05
        
        # Штраф за высокий error rate
        rate_penalty = min(stats.error_rate_per_minute * 0.1, 0.5)
        
        # Базовый score
        base_score = 1.0
        
        # Применяем штрафы
        total_penalty = critical_penalty + error_penalty + warning_penalty + rate_penalty
        health_score = max(0.0, base_score - total_penalty)
        
        return health_score
    
    def reset_metrics(self) -> None:
        """Сбрасывает все метрики."""
        with self._lock:
            self._error_history.clear()
            self._error_counters.clear()
            self._category_counters.clear()
            self._severity_counters.clear()
            self._retry_counters.clear()
            self._fallback_counters.clear()
            self._start_time = time.time()
            
            self.logger.info("[ErrorMetrics] Metrics reset")
    
    def export_metrics(self) -> Dict[str, Any]:
        """
        Экспортирует метрики в формате для мониторинга.
        
        Returns:
            Dict[str, Any]: Метрики в структурированном формате
        """
        stats = self.get_error_stats()
        
        return {
            "timestamp": time.time(),
            "uptime_seconds": time.time() - self._start_time,
            "health_score": self.get_health_score(),
            "error_rate_per_minute": stats.error_rate_per_minute,
            "total_errors": stats.total_errors,
            "errors_by_category": stats.errors_by_category,
            "errors_by_severity": stats.errors_by_severity,
            "errors_by_code": stats.errors_by_code,
            "retry_attempts": stats.retry_attempts,
            "fallback_uses": stats.fallback_uses,
            "top_errors": self.get_top_errors(10),
            "recent_errors_count": len(self.get_recent_errors(5))
        }
    
    def cleanup(self):
        """Очищает ресурсы метрик."""
        with self._lock:
            self._error_history.clear()
            self._error_counters.clear()
            self._category_counters.clear()
            self._severity_counters.clear()
            self._retry_counters.clear()
            self._fallback_counters.clear()
            
            self.logger.info("[ErrorMetrics] Cleanup completed")


# Глобальный экземпляр метрик
_error_metrics = ErrorMetrics()


def get_error_metrics() -> ErrorMetrics:
    """
    Получает глобальный экземпляр метрик ошибок.
    
    Returns:
        ErrorMetrics: Глобальные метрики
    """
    return _error_metrics


def record_error(
    error_code: str,
    category: ErrorCategory,
    severity: ErrorSeverity,
    context: Optional[Dict[str, Any]] = None,
    retry_count: int = 0,
    fallback_used: bool = False
) -> None:
    """
    Записывает ошибку в глобальные метрики.
    
    Args:
        error_code: Код ошибки
        category: Категория ошибки
        severity: Уровень серьезности
        context: Контекст ошибки
        retry_count: Количество retry попыток
        fallback_used: Использовался ли fallback
    """
    _error_metrics.record_error(
        error_code, category, severity, context, retry_count, fallback_used
    )


def get_error_stats() -> ErrorStats:
    """
    Получает статистику ошибок из глобальных метрик.
    
    Returns:
        ErrorStats: Статистика ошибок
    """
    return _error_metrics.get_error_stats()
