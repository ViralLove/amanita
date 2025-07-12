"""
Конфигурация для AMANITA API
"""
import os
from typing import Optional

class APIConfig:
    """Конфигурация API приложения"""
    
    # Основные настройки
    API_TITLE = "AMANITA API"
    API_DESCRIPTION = "API для интеграции e-commerce платформ с блокчейн экосистемой AMANITA"
    API_VERSION = "1.0.0"
    
    # Настройки сервера
    HOST = os.environ.get("AMANITA_API_HOST", "0.0.0.0")
    PORT = int(os.environ.get("AMANITA_API_PORT", "8000"))
    
    # Настройки логирования
    LOG_LEVEL = os.environ.get("AMANITA_API_LOG_LEVEL", "INFO")
    LOG_FILE = os.environ.get("AMANITA_API_LOG_FILE", "logs/amanita_api.log")
    LOG_MAX_SIZE = int(os.environ.get("AMANITA_API_LOG_MAX_SIZE", "10485760"))  # 10MB
    LOG_BACKUP_COUNT = int(os.environ.get("AMANITA_API_LOG_BACKUP_COUNT", "5"))
    
    # Настройки CORS
    CORS_ORIGINS = os.environ.get("AMANITA_API_CORS_ORIGINS", "*").split(",")
    CORS_ALLOW_CREDENTIALS = os.environ.get("AMANITA_API_CORS_ALLOW_CREDENTIALS", "true").lower() == "true"
    
    # Настройки безопасности
    TRUSTED_HOSTS = os.environ.get("AMANITA_API_TRUSTED_HOSTS", "*").split(",")
    
    # Настройки документации
    DOCS_URL = os.environ.get("AMANITA_API_DOCS_URL", "/docs")
    REDOC_URL = os.environ.get("AMANITA_API_REDOC_URL", "/redoc")
    OPENAPI_URL = os.environ.get("AMANITA_API_OPENAPI_URL", "/openapi.json")
    
    @classmethod
    def get_logging_config(cls) -> dict:
        """Получить конфигурацию логирования"""
        return {
            "log_level": cls.LOG_LEVEL,
            "log_file": cls.LOG_FILE,
            "max_size": cls.LOG_MAX_SIZE,
            "backup_count": cls.LOG_BACKUP_COUNT
        }
    
    @classmethod
    def get_cors_config(cls) -> dict:
        """Получить конфигурацию CORS"""
        return {
            "allow_origins": cls.CORS_ORIGINS,
            "allow_credentials": cls.CORS_ALLOW_CREDENTIALS,
            "allow_methods": ["*"],
            "allow_headers": ["*"]
        }
    
    @classmethod
    def get_fastapi_config(cls) -> dict:
        """Получить конфигурацию FastAPI"""
        return {
            "title": cls.API_TITLE,
            "description": cls.API_DESCRIPTION,
            "version": cls.API_VERSION,
            "docs_url": cls.DOCS_URL,
            "redoc_url": cls.REDOC_URL,
            "openapi_url": cls.OPENAPI_URL
        } 