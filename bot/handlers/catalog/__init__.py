"""
Модуль обработчиков каталога продуктов.
Реализует принцип единственной ответственности (SRP) через разделение на специализированные модули.
"""

from aiogram import Router
from .catalog_handlers import router as catalog_router
from .product_handlers import router as product_router
from .navigation_handlers import router as navigation_router

# Инициализируем DI контейнер для каталога
from di_container import container
container.configure_for_environment("development")

# Создаем основной router для каталога
router = Router()

# Включаем все под-router'ы
router.include_router(catalog_router)
router.include_router(product_router)
router.include_router(navigation_router)

__all__ = ['router']
