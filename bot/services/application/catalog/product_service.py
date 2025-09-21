"""
Сервис для работы с детальной информацией о продуктах.
Содержит бизнес-логику поиска и отправки деталей продуктов.
"""

import logging
from typing import Optional, Any
from aiogram.types import CallbackQuery
from services.common.localization import Localization
from services.product.registry_singleton import product_registry_service
from .image_service import ImageService
# Импорт будет добавлен в ItemY 5.2 при внедрении DI
# from handlers.dependencies import get_product_formatter_service

logger = logging.getLogger(__name__)


class ProductService:
    """Сервис для работы с детальной информацией о продуктах"""
    
    def __init__(self, image_service: ImageService = None, formatter_service = None):
        """
        Инициализация сервиса продуктов
        
        Args:
            image_service: Сервис для работы с изображениями
            formatter_service: Сервис для форматирования продуктов
        """
        self.image_service = image_service or ImageService()
        self.formatter_service = formatter_service
        self.logger = logging.getLogger(__name__)
    
    async def get_product_by_id(self, product_id: str) -> Optional[Any]:
        """
        Получает продукт по ID
        
        Args:
            product_id: ID продукта для поиска
            
        Returns:
            Optional[Any]: Найденный продукт или None
        """
        try:
            self.logger.info(f"[ProductService] Поиск продукта по ID: {product_id}")
            
            # Получаем все продукты и ищем по ID
            # TODO: Добавить метод get_product_by_id в ProductRegistryService
            products = await product_registry_service.get_all_products()
            
            for product in products:
                if (getattr(product, 'id', None) == product_id or 
                    getattr(product, 'business_id', None) == product_id):
                    self.logger.info(f"[ProductService] Продукт найден: {product.title}")
                    return product
            
            self.logger.error(f"[ProductService] Продукт с ID {product_id} не найден")
            return None
            
        except Exception as e:
            self.logger.error(f"[ProductService] Ошибка при поиске продукта {product_id}: {e}")
            return None
    
    def _validate_product_id(self, product_id: str) -> bool:
        """
        Валидирует ID продукта
        
        Args:
            product_id: ID продукта для валидации
            
        Returns:
            bool: True если ID валиден
        """
        try:
            if not product_id or not isinstance(product_id, str):
                return False
            if len(product_id.strip()) == 0:
                return False
            return True
        except Exception as e:
            self.logger.error(f"[ProductService] Ошибка валидации ID продукта: {e}")
            return False
    
    async def send_product_details(self, callback: CallbackQuery, product: Any, loc: Localization) -> None:
        """
        Отправляет детальную информацию о продукте пользователю
        
        Args:
            callback: Callback запрос от пользователя
            product: Продукт для отправки деталей
            loc: Объект локализации
        """
        try:
            self.logger.info(f"[ProductService] Отправка деталей продукта: {product.title}")
            
            # Форматируем основную информацию и детальное описание через сервис
            try:
                # Сообщение 1: Основная информация для caption (оптимизировано для 1024 символов)
                main_info_text = self.formatter_service.format_product_main_info_for_telegram(product, loc)
                
                # Сообщение 2: Детальное описание (без ограничений длины, без навигации)
                description_text = self.formatter_service.format_product_description_for_telegram(product, loc)
                
                self.logger.info(f"[ProductService] Основная информация: {len(main_info_text)} символов")
                self.logger.info(f"[ProductService] Детальное описание: {len(description_text)} символов")
                
            except Exception as e:
                self.logger.error(f"[ProductService] Ошибка сервиса форматирования для продукта {getattr(product, 'id', 'unknown')}: {e}")
                # Fallback форматирование
                main_info_text = f"🏷️ <b>{getattr(product, 'title', 'Продукт')}</b>\n❌ Ошибка при загрузке основной информации"
                description_text = f"❌ Ошибка при загрузке детальной информации"
            
            # Отправляем детальную информацию через ImageService
            await self.image_service.send_product_details_with_image(
                callback=callback,
                product=product,
                main_info_text=main_info_text,
                description_text=description_text,
                loc=loc
            )
            
            self.logger.info(f"[ProductService] Детальная информация успешно отправлена для продукта {getattr(product, 'id', 'unknown')}")
            
        except Exception as e:
            self.logger.error(f"[ProductService] Ошибка при отправке детальной информации: {e}")
            raise
