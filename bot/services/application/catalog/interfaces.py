"""
Интерфейсы (Protocol) для сервисов каталога.
Определяет контракты для всех сервисов каталога.
"""

from typing import Protocol, List, Any, Optional
from aiogram.types import CallbackQuery
from services.common.localization import Localization


class CatalogServiceProtocol(Protocol):
    """Протокол для CatalogService"""
    
    async def get_catalog_with_progress(self) -> List[Any]:
        """Получает каталог продуктов с отображением прогресса"""
        ...
    
    async def send_catalog_to_user(self, callback: CallbackQuery, products: List[Any], loc: Localization) -> None:
        """Отправляет каталог продуктов пользователю"""
        ...


class ProductServiceProtocol(Protocol):
    """Протокол для ProductService"""
    
    async def get_product_by_id(self, product_id: str) -> Optional[Any]:
        """Получает продукт по ID"""
        ...
    
    async def send_product_details(self, callback: CallbackQuery, product: Any, loc: Localization) -> None:
        """Отправляет детальную информацию о продукте пользователю"""
        ...


class ImageServiceProtocol(Protocol):
    """Протокол для ImageService"""
    
    async def download_image(self, image_url: str) -> Optional[str]:
        """Загружает изображение по URL и сохраняет во временный файл"""
        ...
    
    async def send_image_with_caption(self, callback: CallbackQuery, image_path: str, caption: str, 
                                    keyboard: Any = None) -> None:
        """Отправляет изображение с подписью пользователю"""
        ...
    
    async def cleanup_temp_files(self, *file_paths: str) -> None:
        """Удаляет временные файлы"""
        ...


class NavigationServiceProtocol(Protocol):
    """Протокол для NavigationService"""
    
    def create_scroll_message(self, loc: Localization) -> str:
        """Создает сообщение для навигации по каталогу"""
        ...
    
    def handle_catalog_navigation(self, callback_data: str, loc: Localization) -> Optional[dict]:
        """Обрабатывает навигационные команды каталога"""
        ...


class ProgressServiceProtocol(Protocol):
    """Протокол для ProgressService"""
    
    async def create_progress_message(self, message: Any, operation: str, loc: Localization) -> Optional[Any]:
        """Создает сообщение о прогрессе операции"""
        ...
    
    async def update_progress(self, operation: str, progress: int, total: int, loc: Localization, 
                            additional_info: str = "") -> bool:
        """Обновляет сообщение о прогрессе"""
        ...
    
    async def complete_progress(self, operation: str, loc: Localization, success: bool = True, 
                              final_message: str = "") -> bool:
        """Завершает отображение прогресса"""
        ...


class ErrorHandlingServiceProtocol(Protocol):
    """Протокол для ErrorHandlingService"""
    
    async def handle_catalog_error(self, error: Exception, callback: CallbackQuery, 
                                 loc: Localization, context: str = "") -> bool:
        """Обрабатывает ошибки каталога"""
        ...
    
    async def handle_product_error(self, error: Exception, callback: CallbackQuery, 
                                 loc: Localization, product_id: str = "") -> bool:
        """Обрабатывает ошибки продуктов"""
        ...
    
    async def handle_image_error(self, error: Exception, callback: CallbackQuery, 
                               loc: Localization, image_url: str = "") -> bool:
        """Обрабатывает ошибки изображений"""
        ...


class CacheServiceProtocol(Protocol):
    """Протокол для CacheService"""
    
    async def get_catalog_cache(self, cache_key: str = "catalog") -> Optional[List[Any]]:
        """Получает кэшированный каталог"""
        ...
    
    async def set_catalog_cache(self, catalog_data: List[Any], cache_key: str = "catalog") -> bool:
        """Сохраняет каталог в кэш"""
        ...
    
    async def get_product_cache(self, product_id: str) -> Optional[Any]:
        """Получает кэшированный продукт"""
        ...
    
    async def set_product_cache(self, product_id: str, product_data: Any) -> bool:
        """Сохраняет продукт в кэш"""
        ...
    
    def invalidate_cache(self, cache_key: str) -> bool:
        """Инвалидирует запись кэша"""
        ...
