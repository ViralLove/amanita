"""
Система мониторинга ошибок для ImageService.
Обеспечивает интеграцию с системами мониторинга и алертинга.
"""

import time
import logging
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass
from abc import ABC, abstractmethod

from .exceptions import ErrorCategory, ErrorSeverity
from .error_metrics import ErrorMetrics, get_error_metrics
from .error_codes import ErrorCodeRegistry, get_error_code_registry


@dataclass
class AlertRule:
    """Правило алерта."""
    name: str
    condition: Callable[[ErrorMetrics], bool]
    severity: str = "warning"
    description: str = ""
    cooldown_seconds: int = 300  # 5 минут


@dataclass
class HealthCheck:
    """Health check результат."""
    name: str
    status: str  # "healthy", "degraded", "unhealthy"
    message: str
    timestamp: float
    details: Dict[str, Any] = None


class MonitoringBackend(ABC):
    """Абстрактный backend для мониторинга."""
    
    @abstractmethod
    async def send_metric(self, name: str, value: float, tags: Dict[str, str] = None) -> None:
        """Отправляет метрику."""
        pass
    
    @abstractmethod
    async def send_alert(self, alert: AlertRule, metrics: ErrorMetrics) -> None:
        """Отправляет алерт."""
        pass
    
    @abstractmethod
    async def send_health_check(self, health_check: HealthCheck) -> None:
        """Отправляет health check."""
        pass


class PrometheusBackend(MonitoringBackend):
    """Backend для Prometheus."""
    
    def __init__(self, pushgateway_url: Optional[str] = None):
        """
        Инициализация Prometheus backend.
        
        Args:
            pushgateway_url: URL Pushgateway для отправки метрик
        """
        self.pushgateway_url = pushgateway_url
        self.logger = logging.getLogger(__name__)
    
    async def send_metric(self, name: str, value: float, tags: Dict[str, str] = None) -> None:
        """Отправляет метрику в Prometheus."""
        # В реальной реализации здесь будет отправка в Prometheus
        self.logger.debug(f"Prometheus metric: {name}={value}, tags={tags}")
    
    async def send_alert(self, alert: AlertRule, metrics: ErrorMetrics) -> None:
        """Отправляет алерт в Prometheus."""
        # В реальной реализации здесь будет отправка алерта
        self.logger.warning(f"Prometheus alert: {alert.name} - {alert.description}")
    
    async def send_health_check(self, health_check: HealthCheck) -> None:
        """Отправляет health check в Prometheus."""
        # В реальной реализации здесь будет отправка health check
        self.logger.info(f"Prometheus health check: {health_check.name} - {health_check.status}")


class LoggingBackend(MonitoringBackend):
    """Backend для логирования."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    async def send_metric(self, name: str, value: float, tags: Dict[str, str] = None) -> None:
        """Логирует метрику."""
        self.logger.info(f"Metric: {name}={value}, tags={tags}")
    
    async def send_alert(self, alert: AlertRule, metrics: ErrorMetrics) -> None:
        """Логирует алерт."""
        self.logger.warning(f"Alert: {alert.name} - {alert.description}")
    
    async def send_health_check(self, health_check: HealthCheck) -> None:
        """Логирует health check."""
        self.logger.info(f"Health check: {health_check.name} - {health_check.status}")


class ErrorMonitoring:
    """
    Система мониторинга ошибок.
    
    Обеспечивает:
    - Отправку метрик в системы мониторинга
    - Алерты при превышении порогов
    - Health checks для проверки состояния
    - Интеграцию с различными backend'ами
    """
    
    def __init__(self, backends: Optional[List[MonitoringBackend]] = None):
        """
        Инициализация системы мониторинга.
        
        Args:
            backends: Список backend'ов для мониторинга
        """
        self.backends = backends or [LoggingBackend()]
        self.logger = logging.getLogger(__name__)
        
        # Метрики и реестр кодов
        self.metrics = get_error_metrics()
        self.code_registry = get_error_code_registry()
        
        # Правила алертов
        self.alert_rules = self._initialize_alert_rules()
        
        # Время последнего алерта для каждого правила
        self._last_alert_times: Dict[str, float] = {}
        
        self.logger.info(f"[ErrorMonitoring] Инициализирован с {len(self.backends)} backends")
    
    def _initialize_alert_rules(self) -> List[AlertRule]:
        """Инициализирует правила алертов."""
        rules = []
        
        # Алерт на высокий error rate
        rules.append(AlertRule(
            name="high_error_rate",
            condition=lambda m: m.get_error_rate(5) > 10.0,  # > 10 ошибок в минуту
            severity="warning",
            description="Высокий error rate (> 10 ошибок в минуту)",
            cooldown_seconds=300
        ))
        
        # Алерт на критические ошибки
        rules.append(AlertRule(
            name="critical_errors",
            condition=lambda m: m.get_error_stats().errors_by_severity.get(ErrorSeverity.CRITICAL.value, 0) > 0,
            severity="critical",
            description="Обнаружены критические ошибки",
            cooldown_seconds=60
        ))
        
        # Алерт на низкий health score
        rules.append(AlertRule(
            name="low_health_score",
            condition=lambda m: m.get_health_score() < 0.7,
            severity="warning",
            description="Низкий health score (< 0.7)",
            cooldown_seconds=600
        ))
        
        # Алерт на частые retry операции
        rules.append(AlertRule(
            name="frequent_retries",
            condition=lambda m: m.get_error_stats().retry_attempts > 100,
            severity="warning",
            description="Частые retry операции (> 100)",
            cooldown_seconds=300
        ))
        
        return rules
    
    async def send_metrics(self) -> None:
        """Отправляет метрики во все backend'ы."""
        stats = self.metrics.get_error_stats()
        
        # Основные метрики
        metrics_to_send = [
            ("image_service_errors_total", stats.total_errors),
            ("image_service_error_rate_per_minute", stats.error_rate_per_minute),
            ("image_service_retry_attempts_total", stats.retry_attempts),
            ("image_service_fallback_uses_total", stats.fallback_uses),
            ("image_service_health_score", self.metrics.get_health_score())
        ]
        
        # Метрики по категориям
        for category, count in stats.errors_by_category.items():
            metrics_to_send.append(
                (f"image_service_errors_by_category_total", count, {"category": category})
            )
        
        # Метрики по уровням серьезности
        for severity, count in stats.errors_by_severity.items():
            metrics_to_send.append(
                (f"image_service_errors_by_severity_total", count, {"severity": severity})
            )
        
        # Отправляем метрики
        for backend in self.backends:
            try:
                for metric_data in metrics_to_send:
                    if len(metric_data) == 2:
                        name, value = metric_data
                        await backend.send_metric(name, value)
                    else:
                        name, value, tags = metric_data
                        await backend.send_metric(name, value, tags)
            except Exception as e:
                self.logger.error(f"Failed to send metrics to backend {type(backend).__name__}: {e}")
    
    async def check_alerts(self) -> None:
        """Проверяет правила алертов и отправляет уведомления."""
        current_time = time.time()
        
        for rule in self.alert_rules:
            try:
                # Проверяем cooldown
                last_alert_time = self._last_alert_times.get(rule.name, 0)
                if current_time - last_alert_time < rule.cooldown_seconds:
                    continue
                
                # Проверяем условие алерта
                if rule.condition(self.metrics):
                    # Отправляем алерт
                    for backend in self.backends:
                        try:
                            await backend.send_alert(rule, self.metrics)
                        except Exception as e:
                            self.logger.error(f"Failed to send alert to backend {type(backend).__name__}: {e}")
                    
                    # Обновляем время последнего алерта
                    self._last_alert_times[rule.name] = current_time
                    
                    self.logger.warning(f"Alert triggered: {rule.name} - {rule.description}")
                    
            except Exception as e:
                self.logger.error(f"Error checking alert rule {rule.name}: {e}")
    
    async def perform_health_check(self) -> HealthCheck:
        """
        Выполняет health check системы.
        
        Returns:
            HealthCheck: Результат health check
        """
        try:
            stats = self.metrics.get_error_stats()
            health_score = self.metrics.get_health_score()
            
            # Определяем статус
            if health_score >= 0.9:
                status = "healthy"
                message = "Система работает нормально"
            elif health_score >= 0.7:
                status = "degraded"
                message = "Система работает с деградацией"
            else:
                status = "unhealthy"
                message = "Система работает нестабильно"
            
            # Детали health check
            details = {
                "health_score": health_score,
                "total_errors": stats.total_errors,
                "error_rate_per_minute": stats.error_rate_per_minute,
                "critical_errors": stats.errors_by_severity.get(ErrorSeverity.CRITICAL.value, 0),
                "retry_attempts": stats.retry_attempts,
                "fallback_uses": stats.fallback_uses
            }
            
            health_check = HealthCheck(
                name="image_service",
                status=status,
                message=message,
                timestamp=time.time(),
                details=details
            )
            
            # Отправляем health check
            for backend in self.backends:
                try:
                    await backend.send_health_check(health_check)
                except Exception as e:
                    self.logger.error(f"Failed to send health check to backend {type(backend).__name__}: {e}")
            
            return health_check
            
        except Exception as e:
            self.logger.error(f"Error performing health check: {e}")
            
            # Возвращаем unhealthy health check
            return HealthCheck(
                name="image_service",
                status="unhealthy",
                message=f"Ошибка при выполнении health check: {e}",
                timestamp=time.time(),
                details={"error": str(e)}
            )
    
    def add_alert_rule(self, rule: AlertRule) -> None:
        """
        Добавляет новое правило алерта.
        
        Args:
            rule: Правило алерта
        """
        self.alert_rules.append(rule)
        self.logger.info(f"Added alert rule: {rule.name}")
    
    def remove_alert_rule(self, rule_name: str) -> bool:
        """
        Удаляет правило алерта.
        
        Args:
            rule_name: Имя правила
            
        Returns:
            bool: True если правило было удалено
        """
        for i, rule in enumerate(self.alert_rules):
            if rule.name == rule_name:
                del self.alert_rules[i]
                self.logger.info(f"Removed alert rule: {rule_name}")
                return True
        return False
    
    def add_backend(self, backend: MonitoringBackend) -> None:
        """
        Добавляет новый backend для мониторинга.
        
        Args:
            backend: Backend для мониторинга
        """
        self.backends.append(backend)
        self.logger.info(f"Added monitoring backend: {type(backend).__name__}")
    
    def remove_backend(self, backend: MonitoringBackend) -> bool:
        """
        Удаляет backend для мониторинга.
        
        Args:
            backend: Backend для удаления
            
        Returns:
            bool: True если backend был удален
        """
        try:
            self.backends.remove(backend)
            self.logger.info(f"Removed monitoring backend: {type(backend).__name__}")
            return True
        except ValueError:
            return False
    
    async def start_monitoring(self, interval_seconds: int = 60) -> None:
        """
        Запускает мониторинг в фоновом режиме.
        
        Args:
            interval_seconds: Интервал между проверками в секундах
        """
        self.logger.info(f"Starting monitoring with interval {interval_seconds}s")
        
        while True:
            try:
                # Отправляем метрики
                await self.send_metrics()
                
                # Проверяем алерты
                await self.check_alerts()
                
                # Выполняем health check
                await self.perform_health_check()
                
                # Ждем до следующей итерации
                await asyncio.sleep(interval_seconds)
                
            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(interval_seconds)
    
    def get_monitoring_status(self) -> Dict[str, Any]:
        """
        Получает статус системы мониторинга.
        
        Returns:
            Dict[str, Any]: Статус мониторинга
        """
        return {
            "backends_count": len(self.backends),
            "alert_rules_count": len(self.alert_rules),
            "last_alert_times": self._last_alert_times.copy(),
            "metrics_status": "active" if self.metrics else "inactive",
            "code_registry_status": "active" if self.code_registry else "inactive"
        }
    
    async def cleanup(self):
        """Очищает ресурсы мониторинга."""
        self.backends.clear()
        self.alert_rules.clear()
        self._last_alert_times.clear()
        
        self.logger.info("[ErrorMonitoring] Cleanup completed")


# Глобальный экземпляр мониторинга
_error_monitoring = ErrorMonitoring()


def get_error_monitoring() -> ErrorMonitoring:
    """
    Получает глобальный экземпляр мониторинга ошибок.
    
    Returns:
        ErrorMonitoring: Глобальный мониторинг
    """
    return _error_monitoring


def setup_prometheus_monitoring(pushgateway_url: Optional[str] = None) -> None:
    """
    Настраивает мониторинг с Prometheus backend.
    
    Args:
        pushgateway_url: URL Pushgateway для отправки метрик
    """
    monitoring = get_error_monitoring()
    prometheus_backend = PrometheusBackend(pushgateway_url)
    monitoring.add_backend(prometheus_backend)


async def start_monitoring(interval_seconds: int = 60) -> None:
    """
    Запускает глобальный мониторинг.
    
    Args:
        interval_seconds: Интервал между проверками в секундах
    """
    monitoring = get_error_monitoring()
    await monitoring.start_monitoring(interval_seconds)
