from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException
import logging
import sys
import os
import json
from datetime import datetime
from typing import Optional
from logging.handlers import RotatingFileHandler
from bot.api.config import APIConfig
from bot.api.middleware.auth import HMACMiddleware
from fastapi.exceptions import RequestValidationError, HTTPException
from pydantic import ValidationError
from bot.api import error_handlers
from bot.api.models.health import HealthCheckResponse, HealthStatus, ServiceInfo, DetailedHealthCheckResponse, SystemUptime, ComponentInfo, ComponentStatus
from bot.api.models.common import get_current_timestamp, generate_request_id, Timestamp, RequestId
from bot.api.utils.health_utils import calculate_uptime, get_system_metrics, check_component_latency
from bot.api.utils.health_utils import (
    check_api_component, check_service_factory_component, check_blockchain_component,
    check_database_component, check_external_apis_component
)
from bot.services.service_factory import ServiceFactory
from bot.utils.sentry_init import init_sentry
from bot.utils.logging_setup import setup_logging

init_sentry()
logger = setup_logging(
    log_level=APIConfig.LOG_LEVEL,
    log_file=APIConfig.LOG_FILE,
    max_size=APIConfig.LOG_MAX_SIZE,
    backup_count=APIConfig.LOG_BACKUP_COUNT
)

# Глобальное время запуска приложения
APP_START_TIME = datetime.now()

def create_api_app(service_factory=None, log_level: str = "INFO", log_file: Optional[str] = None) -> FastAPI:
    """
    Создание FastAPI приложения с базовой конфигурацией
    
    Args:
        service_factory: Экземпляр ServiceFactory для интеграции с существующими сервисами
        log_level: Уровень логирования
        log_file: Путь к файлу для записи логов
    
    Returns:
        FastAPI: Настроенное приложение
    """
    # logger уже инициализирован глобально
    logger.info("Инициализация AMANITA API приложения", extra={
        "log_level": log_level,
        "log_file": log_file,
        "service_factory_available": service_factory is not None
    })
    
    # Получаем конфигурации
    fastapi_config = APIConfig.get_fastapi_config()
    cors_config = APIConfig.get_cors_config()
    
    # Создание FastAPI приложения
    app = FastAPI(**fastapi_config)
    
    # Настройка CORS для веб-клиентов
    app.add_middleware(
        CORSMiddleware,
        **cors_config
    )
    
    # Настройка Trusted Host для безопасности
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=APIConfig.TRUSTED_HOSTS
    )
    
    # Настройка HMAC аутентификации
    api_key_service = None
    if service_factory:
        try:
            api_key_service = service_factory.create_api_key_service()
            logger.info("ApiKeyService интегрирован в HMAC middleware")
        except Exception as e:
            logger.warning(f"Не удалось инициализировать ApiKeyService: {e}")
    
    app.add_middleware(HMACMiddleware, api_key_service=api_key_service)
    
    # Сохранение service_factory в состоянии приложения
    if service_factory:
        app.state.service_factory = service_factory
        logger.info("ServiceFactory интегрирован в приложение")
    
    # Глобальные обработчики ошибок
    app.add_exception_handler(RequestValidationError, error_handlers.validation_exception_handler)
    app.add_exception_handler(ValidationError, error_handlers.pydantic_validation_error_handler)
    app.add_exception_handler(HTTPException, error_handlers.http_exception_handler)
    app.add_exception_handler(StarletteHTTPException, error_handlers.not_found_exception_handler)
    app.add_exception_handler(Exception, error_handlers.unhandled_exception_handler)

    def create_public_response(message: str, additional_data: dict = None) -> dict:
        """Создает единообразный ответ для публичных эндпоинтов"""
        response = {
            "success": True,
            "service": "amanita_api",
            "version": "1.0.0",
            "environment": APIConfig.ENVIRONMENT,
            "timestamp": get_current_timestamp(),
            "request_id": generate_request_id(),
            "message": message
        }
        
        if additional_data:
            response.update(additional_data)
        
        return response

    # Базовые эндпоинты
    @app.get("/")
    async def root():
        """Корневой эндпоинт"""
        logger.info("Запрос к корневому эндпоинту", extra={"endpoint": "/"})
        return create_public_response(
            message="AMANITA API",
            additional_data={"status": "running"}
        )
    
    @app.get("/health")
    async def health_check():
        """Health check эндпоинт"""
        logger.debug("Health check запрос", extra={"endpoint": "/health"})
        
        # Вычисляем uptime
        uptime = calculate_uptime(APP_START_TIME)
        
        return HealthCheckResponse(
            success=True,
            status=HealthStatus(
                status="healthy",
                message="Service is running normally"
            ),
            service=ServiceInfo(
                name="amanita_api",
                version="1.0.0",
                environment=APIConfig.ENVIRONMENT
            ),
            timestamp=Timestamp(get_current_timestamp()),
            request_id=RequestId(generate_request_id()),
            uptime=uptime
        )
    
    @app.get("/health/detailed")
    async def detailed_health_check():
        """Детальный health check"""
        logger.info("Детальный health check запрос", extra={"endpoint": "/health/detailed"})
        
        # Вычисляем uptime
        uptime = calculate_uptime(APP_START_TIME)
        
        # Получаем системные метрики
        system_metrics = get_system_metrics()
        
        # Проверяем компоненты системы
        components = []
        
        # API компонент
        api_component = await check_component_latency(check_api_component, "api")
        components.append(api_component)
        
        # ServiceFactory компонент
        if service_factory:
            sf_component = await check_component_latency(
                lambda: check_service_factory_component(service_factory), 
                "service_factory"
            )
            components.append(sf_component)
        else:
            components.append(ComponentInfo(
                name="service_factory",
                status=ComponentStatus.NOT_INITIALIZED,
                last_check=datetime.now(),
                error_count=0,
                details={"message": "ServiceFactory не инициализирован"}
            ))
        
        # Blockchain компонент
        if service_factory and hasattr(service_factory, 'blockchain'):
            blockchain_component = await check_component_latency(
                lambda: check_blockchain_component(service_factory),
                "blockchain"
            )
            components.append(blockchain_component)
        else:
            components.append(ComponentInfo(
                name="blockchain",
                status=ComponentStatus.UNAVAILABLE,
                last_check=datetime.now(),
                error_count=0,
                details={"message": "Blockchain service недоступен"}
            ))
        
        # Database компонент
        db_component = await check_component_latency(check_database_component, "database")
        components.append(db_component)
        
        # External APIs компонент
        external_apis_component = await check_component_latency(check_external_apis_component, "external_apis")
        components.append(external_apis_component)
        
        # Определяем общий статус на основе компонентов
        error_components = [c for c in components if c.status == ComponentStatus.ERROR]
        degraded_components = [c for c in components if c.status == ComponentStatus.DEGRADED]
        
        if error_components:
            status = "unhealthy"
            message = f"Критические ошибки в компонентах: {', '.join([c.name for c in error_components])}"
        elif degraded_components:
            status = "degraded"
            message = f"Проблемы в компонентах: {', '.join([c.name for c in degraded_components])}"
        else:
            status = "healthy"
            message = "Все компоненты работают нормально"
        
        return DetailedHealthCheckResponse(
            success=True,
            status=HealthStatus(
                status=status,
                message=message
            ),
            service=ServiceInfo(
                name="amanita_api",
                version="1.0.0",
                environment=APIConfig.ENVIRONMENT
            ),
            timestamp=Timestamp(get_current_timestamp()),
            request_id=RequestId(generate_request_id()),
            uptime=uptime,
            components=components,
            system_metrics=system_metrics
        )
    
    @app.get("/hello")
    async def hello_world():
        """Простой hello world endpoint для тестирования"""
        logger.info("Hello world запрос", extra={"endpoint": "/hello"})
        return create_public_response(
            message="Hello World!",
            additional_data={"status": "running"}
        )
    
    @app.post("/auth-test")
    async def auth_test(request: Request):
        """Тестовый эндпоинт для проверки HMAC аутентификации"""
        logger.info("Auth test запрос", extra={
            "endpoint": "/auth-test",
            "client_address": getattr(request.state, 'client_address', 'unknown')
        })
        
        client_address = getattr(request.state, 'client_address', 'unknown')
        
        return {
            "success": True,
            "client_address": client_address,
            "authenticated_at": datetime.now().isoformat(),
            "message": "Authentication successful"
        }
    
    # Подключаем роутеры
    from bot.api.routes import api_keys, products, media, description
    app.include_router(api_keys.router)
    app.include_router(products.router)
    app.include_router(media.router)
    app.include_router(description.router)
    
    logger.info("FastAPI приложение создано с базовой конфигурацией", extra={
        "docs_url": "/docs",
        "health_endpoint": "/health"
    })
    return app

# Создание приложения по умолчанию (для разработки)
app = create_api_app()

if __name__ == "__main__":
    import uvicorn
    
    # Создаем приложение с настройками логирования из конфигурации
    app = create_api_app(
        log_level=APIConfig.LOG_LEVEL,
        log_file=APIConfig.LOG_FILE
    )
    
    uvicorn.run(
        "bot.api.main:app",
        host=APIConfig.HOST,
        port=APIConfig.PORT,
        reload=True,
        log_level="info"
    ) 