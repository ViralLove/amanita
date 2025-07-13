"""
Модели для health check и мониторинга API
"""
from datetime import datetime
from typing import Optional, Dict, Any, List
from enum import Enum
from pydantic import BaseModel, Field, ConfigDict
from .common import RequestId, Timestamp


class ComponentStatus(str, Enum):
    """Статусы компонентов системы"""
    OK = "ok"
    DEGRADED = "degraded"
    ERROR = "error"
    NOT_INITIALIZED = "not_initialized"
    UNAVAILABLE = "unavailable"


class ComponentInfo(BaseModel):
    """Информация о компоненте системы"""
    name: str = Field(..., description="Название компонента")
    status: ComponentStatus = Field(..., description="Статус компонента")
    latency_ms: Optional[float] = Field(None, description="Время отклика в миллисекундах")
    last_check: Optional[datetime] = Field(None, description="Время последней проверки")
    error_count: int = Field(0, description="Количество ошибок")
    last_error: Optional[str] = Field(None, description="Последняя ошибка")
    version: Optional[str] = Field(None, description="Версия компонента")
    details: Optional[Dict[str, Any]] = Field(None, description="Дополнительные детали")
    
    model_config = ConfigDict(arbitrary_types_allowed=True)


class SystemUptime(BaseModel):
    """Информация о времени работы системы"""
    start_time: datetime = Field(..., description="Время запуска системы")
    uptime_seconds: float = Field(..., description="Время работы в секундах")
    uptime_formatted: str = Field(..., description="Форматированное время работы")
    
    model_config = ConfigDict(arbitrary_types_allowed=True)


class HealthStatus(BaseModel):
    """Статус здоровья сервиса"""
    status: str = Field(..., description="Статус сервиса (healthy, degraded, unhealthy)")
    message: Optional[str] = Field(None, description="Дополнительное сообщение о статусе")
    
    model_config = ConfigDict(arbitrary_types_allowed=True)


class ServiceInfo(BaseModel):
    """Информация о сервисе"""
    name: str = Field(..., description="Название сервиса")
    version: str = Field(..., description="Версия сервиса")
    environment: str = Field(..., description="Окружение (development, staging, production)")
    
    model_config = ConfigDict(arbitrary_types_allowed=True)


class HealthCheckResponse(BaseModel):
    """Ответ на health check запрос"""
    success: bool = Field(True, description="Статус операции")
    status: HealthStatus = Field(..., description="Статус здоровья")
    service: ServiceInfo = Field(..., description="Информация о сервисе")
    timestamp: Timestamp = Field(..., description="Временная метка проверки")
    request_id: Optional[RequestId] = Field(None, description="ID запроса")
    uptime: Optional[SystemUptime] = Field(None, description="Информация о времени работы")
    details: Optional[Dict[str, Any]] = Field(None, description="Дополнительные детали о состоянии сервиса")
    
    model_config = ConfigDict(arbitrary_types_allowed=True)


class DetailedHealthCheckResponse(HealthCheckResponse):
    """Детальный ответ на health check запрос"""
    components: List[ComponentInfo] = Field(default_factory=list, description="Список компонентов системы")
    system_metrics: Optional[Dict[str, Any]] = Field(None, description="Системные метрики")
    
    model_config = ConfigDict(arbitrary_types_allowed=True) 