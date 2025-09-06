"""
Утилиты для health check и мониторинга
"""
import time
import psutil
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from api.models.health import SystemUptime, ComponentInfo, ComponentStatus


def format_uptime(seconds: float) -> str:
    """
    Форматирует время работы в человекочитаемый вид
    
    Args:
        seconds: Время в секундах
        
    Returns:
        str: Форматированное время (например: "2d 3h 45m 30s")
    """
    if seconds < 60:
        return f"{int(seconds)}s"
    
    minutes = int(seconds // 60)
    if minutes < 60:
        return f"{minutes}m {int(seconds % 60)}s"
    
    hours = int(minutes // 60)
    if hours < 24:
        return f"{hours}h {minutes % 60}m {int(seconds % 60)}s"
    
    days = int(hours // 24)
    return f"{days}d {hours % 24}h {minutes % 60}m {int(seconds % 60)}s"


def calculate_uptime(start_time: datetime) -> SystemUptime:
    """
    Вычисляет время работы системы
    
    Args:
        start_time: Время запуска системы
        
    Returns:
        SystemUptime: Информация о времени работы
    """
    now = datetime.now()
    uptime_seconds = (now - start_time).total_seconds()
    
    return SystemUptime(
        start_time=start_time,
        uptime_seconds=uptime_seconds,
        uptime_formatted=format_uptime(uptime_seconds)
    )


def get_system_metrics() -> Dict[str, Any]:
    """
    Получает системные метрики
    
    Returns:
        Dict[str, Any]: Системные метрики
    """
    try:
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        return {
            "cpu_percent": cpu_percent,
            "memory": {
                "total_gb": round(memory.total / (1024**3), 2),
                "available_gb": round(memory.available / (1024**3), 2),
                "used_percent": memory.percent
            },
            "disk": {
                "total_gb": round(disk.total / (1024**3), 2),
                "free_gb": round(disk.free / (1024**3), 2),
                "used_percent": round((disk.used / disk.total) * 100, 2)
            }
        }
    except Exception as e:
        return {"error": f"Не удалось получить системные метрики: {str(e)}"}


async def check_component_latency(check_func, component_name: str, timeout: float = 5.0) -> ComponentInfo:
    """
    Проверяет компонент с измерением времени отклика
    
    Args:
        check_func: Функция проверки компонента
        component_name: Название компонента
        timeout: Таймаут проверки в секундах
        
    Returns:
        ComponentInfo: Информация о компоненте
    """
    start_time = time.time()
    last_check = datetime.now()
    
    try:
        # Выполняем проверку с таймаутом
        result = await asyncio.wait_for(check_func(), timeout=timeout)
        latency_ms = (time.time() - start_time) * 1000
        
        return ComponentInfo(
            name=component_name,
            status=ComponentStatus.OK,
            latency_ms=round(latency_ms, 2),
            last_check=last_check,
            error_count=0,
            details=result if isinstance(result, dict) else {"status": "ok"}
        )
        
    except asyncio.TimeoutError:
        return ComponentInfo(
            name=component_name,
            status=ComponentStatus.ERROR,
            latency_ms=None,
            last_check=last_check,
            error_count=1,
            last_error="Timeout",
            details={"timeout_seconds": timeout}
        )
        
    except Exception as e:
        return ComponentInfo(
            name=component_name,
            status=ComponentStatus.ERROR,
            latency_ms=None,
            last_check=last_check,
            error_count=1,
            last_error=str(e),
            details={"error_type": type(e).__name__}
        )


async def check_api_component() -> Dict[str, Any]:
    """Проверка API компонента"""
    # Простая проверка - API работает если мы дошли до этой функции
    return {"status": "operational", "endpoints_available": True}


async def check_service_factory_component(service_factory) -> Dict[str, Any]:
    """Проверка ServiceFactory компонента"""
    if not service_factory:
        raise Exception("ServiceFactory не инициализирован")
    
    # Проверяем доступность основных сервисов
    available_services = []
    
    if hasattr(service_factory, 'blockchain'):
        available_services.append("blockchain")
    
    if hasattr(service_factory, 'account'):
        available_services.append("account")
    
    if hasattr(service_factory, 'circle'):
        available_services.append("circle")
    
    return {
        "status": "operational",
        "available_services": available_services,
        "total_services": len(available_services)
    }


async def check_blockchain_component(service_factory) -> Dict[str, Any]:
    """Проверка блокчейн компонента"""
    if not service_factory or not hasattr(service_factory, 'blockchain'):
        raise Exception("Blockchain service недоступен")
    
    # Здесь можно добавить реальную проверку блокчейн сервиса
    # Например, проверка подключения к сети, получение последнего блока и т.д.
    
    return {
        "status": "operational",
        "network": "ethereum",
        "connection": "active"
    }


async def check_database_component() -> Dict[str, Any]:
    """Проверка базы данных"""
    # Здесь можно добавить проверку подключения к БД
    # Пока возвращаем заглушку
    return {
        "status": "operational",
        "type": "sqlite",  # или другая БД
        "connection": "active"
    }


async def check_external_apis_component() -> Dict[str, Any]:
    """Проверка внешних API"""
    # Здесь можно добавить проверку внешних сервисов
    # Например, Telegram API, платежные системы и т.д.
    
    external_apis = {
        "telegram_api": "operational",
        "payment_gateway": "operational"
    }
    
    return {
        "status": "operational",
        "apis": external_apis,
        "total_apis": len(external_apis)
    } 