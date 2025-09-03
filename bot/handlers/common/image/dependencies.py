"""
Dependency providers для ImageService.
Централизованное управление зависимостями для работы с изображениями.
"""

from .image_service import ImageService
from .image_service_config import ImageServiceConfig


def get_image_service() -> ImageService:
    """
    Dependency provider для ImageService с конфигурацией по умолчанию.
    
    Returns:
        ImageService: Экземпляр сервиса изображений
    """
    return ImageService()


def get_image_service_with_config(config: ImageServiceConfig) -> ImageService:
    """
    Dependency provider для ImageService с кастомной конфигурацией.
    
    Args:
        config: Конфигурация для сервиса
        
    Returns:
        ImageService: Экземпляр сервиса с указанной конфигурацией
    """
    return ImageService(config)


def get_default_image_service_config() -> ImageServiceConfig:
    """
    Dependency provider для конфигурации изображений по умолчанию.
    
    Returns:
        ImageServiceConfig: Конфигурация по умолчанию
    """
    return ImageServiceConfig()


def get_optimized_image_service_config() -> ImageServiceConfig:
    """
    Dependency provider для оптимизированной конфигурации изображений.
    
    Returns:
        ImageServiceConfig: Оптимизированная конфигурация
    """
    return ImageServiceConfig(
        download_timeout=15,
        max_file_size=5 * 1024 * 1024,  # 5MB
        retry_attempts=2,
        resize_large_images=True,
        max_image_dimension=1280,
        compression_quality=80,
        enable_cache=True,
        cache_duration=7200  # 2 часа
    )


def get_fast_image_service_config() -> ImageServiceConfig:
    """
    Dependency provider для быстрой конфигурации изображений.
    
    Returns:
        ImageServiceConfig: Быстрая конфигурация
    """
    return ImageServiceConfig(
        download_timeout=10,
        max_file_size=2 * 1024 * 1024,  # 2MB
        retry_attempts=1,
        resize_large_images=True,
        max_image_dimension=800,
        compression_quality=70,
        enable_cache=True,
        cache_duration=3600,  # 1 час
        max_media_group_size=5
    )
