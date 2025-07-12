from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
import logging
import sys
import os
import json
from datetime import datetime
from typing import Optional
from logging.handlers import RotatingFileHandler
from api.config import APIConfig

# Настройка логирования для API
def setup_logging(log_level: str = "INFO", log_file: Optional[str] = None):
    """
    Настройка логирования для API слоя
    
    Args:
        log_level: Уровень логирования (DEBUG, INFO, WARNING, ERROR)
        log_file: Путь к файлу для записи логов (если None - только консоль)
    """
    logger = logging.getLogger("amanita_api")
    logger.setLevel(getattr(logging, log_level.upper()))
    
    # Очищаем существующие обработчики
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Создаем обработчик для вывода в консоль
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, log_level.upper()))
    
    # Форматтер для консоли (человекочитаемый)
    console_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    # Если указан файл, добавляем файловый обработчик
    if log_file:
        # Создаем директорию для логов если не существует
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)
        
        # Получаем конфигурацию логирования
        log_config = APIConfig.get_logging_config()
        
        # Ротация логов: настраиваемый размер и количество файлов
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=log_config["max_size"],
            backupCount=log_config["backup_count"],
            encoding='utf-8'
        )
        file_handler.setLevel(getattr(logging, log_level.upper()))
        
        # JSON форматтер для файлов (structured logging)
        class JSONFormatter(logging.Formatter):
            def format(self, record):
                log_entry = {
                    "timestamp": datetime.fromtimestamp(record.created).isoformat(),
                    "level": record.levelname,
                    "logger": record.name,
                    "message": record.getMessage(),
                    "module": record.module,
                    "function": record.funcName,
                    "line": record.lineno
                }
                
                # Добавляем exception info если есть
                if record.exc_info:
                    log_entry["exception"] = self.formatException(record.exc_info)
                
                # Добавляем extra поля если есть
                for key, value in record.__dict__.items():
                    if key not in ['name', 'msg', 'args', 'levelname', 'levelno', 'pathname', 
                                 'filename', 'module', 'lineno', 'funcName', 'created', 
                                 'msecs', 'relativeCreated', 'thread', 'threadName', 
                                 'processName', 'process', 'getMessage', 'exc_info', 
                                 'exc_text', 'stack_info']:
                        log_entry[key] = value
                
                return json.dumps(log_entry, ensure_ascii=False)
        
        file_handler.setFormatter(JSONFormatter())
        logger.addHandler(file_handler)
    
    # Настраиваем логирование для внешних библиотек
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("fastapi").setLevel(logging.WARNING)
    
    return logger

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
    # Настройка логирования
    logger = setup_logging(log_level, log_file)
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
    
    # Сохранение service_factory в состоянии приложения
    if service_factory:
        app.state.service_factory = service_factory
        logger.info("ServiceFactory интегрирован в приложение")
    
    # Базовые эндпоинты
    @app.get("/")
    async def root():
        """Корневой эндпоинт"""
        logger.info("Запрос к корневому эндпоинту", extra={"endpoint": "/"})
        return {
            "message": "AMANITA API",
            "version": "1.0.0",
            "status": "running"
        }
    
    @app.get("/health")
    async def health_check():
        """Health check эндпоинт"""
        logger.debug("Health check запрос", extra={"endpoint": "/health"})
        return {
            "status": "healthy",
            "service": "amanita_api"
        }
    
    @app.get("/health/detailed")
    async def detailed_health_check():
        """Детальный health check"""
        logger.info("Детальный health check запрос", extra={"endpoint": "/health/detailed"})
        
        health_status = {
            "status": "healthy",
            "service": "amanita_api",
            "components": {
                "api": "ok",
                "service_factory": "ok" if service_factory else "not_initialized"
            }
        }
        
        # Проверка ServiceFactory если доступен
        if service_factory:
            try:
                # Базовая проверка blockchain service
                blockchain_service = service_factory.blockchain
                health_status["components"]["blockchain"] = "ok"
                logger.debug("Blockchain service проверен успешно")
            except Exception as e:
                health_status["components"]["blockchain"] = f"error: {str(e)}"
                health_status["status"] = "degraded"
                logger.error("Ошибка при проверке blockchain service", extra={"error": str(e)})
        
        return health_status
    
    @app.get("/hello")
    async def hello_world():
        """Простой hello world endpoint для тестирования"""
        logger.info("Hello world запрос", extra={"endpoint": "/hello"})
        return {
            "message": "Hello World!",
            "service": "amanita_api",
            "status": "running",
            "timestamp": datetime.now().isoformat()
        }
    
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