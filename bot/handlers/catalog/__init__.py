"""
Модуль обработчиков каталога продуктов.
Реализует принцип единственной ответственности (SRP) через разделение на специализированные модули.
"""

from aiogram import Router
from .catalog_handlers import router as catalog_router
from .product_handlers import router as product_router
from .navigation_handlers import router as navigation_router

# Импортируем DI контейнер
from di_container import container

# Инициализируем DI контейнер с автоматическим определением окружения
container.configure_for_environment()

def get_service(service_name: str):
    """
    Получение сервиса через DI контейнер.
    
    Args:
        service_name: Имя сервиса для получения
        
    Returns:
        Экземпляр сервиса
    """
    return container.get_service(service_name)

# Создаем основной router для каталога
router = Router()

# Включаем все под-router'ы
router.include_router(catalog_router)
router.include_router(product_router)
router.include_router(navigation_router)

__all__ = ['router', 'get_service', 'container']
