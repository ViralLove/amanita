"""
Dependency providers для handlers.
Централизованное управление зависимостями.
"""

from .common.formatting import ProductFormatterService, ProductFormatterConfig


def get_product_formatter_service() -> ProductFormatterService:
    """
    Dependency provider для ProductFormatterService.
    
    Returns:
        ProductFormatterService: Экземпляр сервиса форматирования с конфигурацией по умолчанию
    """
    return ProductFormatterService()


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
