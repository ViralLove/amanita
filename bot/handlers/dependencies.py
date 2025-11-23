"""
Dependency providers для handlers.
Централизованное управление зависимостями.
"""

from .common.formatting import ProductFormatterService, ProductFormatterConfig


def get_product_formatter_service(localization_service=None) -> ProductFormatterService:
    """
    Dependency provider для ProductFormatterService с LocalizationService.
    
    Args:
        localization_service: Сервис локализации (если не указан, создаётся через get_localization_service())
    
    Returns:
        ProductFormatterService: Экземпляр сервиса форматирования с локализацией
    """
    if localization_service is None:
        from dependencies import get_localization_service
        localization_service = get_localization_service()  # Default lang='ru'
    return ProductFormatterService(localization_service=localization_service)


def get_product_formatter_service_with_config(config: ProductFormatterConfig) -> ProductFormatterService:
    """
    Dependency provider для ProductFormatterService с кастомной конфигурацией.
    
    Args:
        config: Конфигурация для сервиса
        
    Returns:
        ProductFormatterService: Экземпляр сервиса с указанной конфигурацией
    """
    return ProductFormatterService(config)


def get_default_product_formatter_config() -> ProductFormatterConfig:
    """
    Dependency provider для конфигурации по умолчанию.
    
    Returns:
        ProductFormatterConfig: Конфигурация по умолчанию
    """
    return ProductFormatterConfig()
