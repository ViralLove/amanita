"""
Dependency providers для обработчиков каталога.
Использует общие providers из bot/dependencies.py.
"""

from bot.dependencies import (
    get_catalog_service,
    get_product_service,
    get_image_service
)

# Re-export для удобства использования в handlers
__all__ = [
    'get_catalog_service',
    'get_product_service', 
    'get_image_service'
]
