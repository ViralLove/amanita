"""
Сервис для работы с каталогом продуктов.
Содержит бизнес-логику получения и отправки каталога пользователям.
"""

import logging
from typing import List, Any
from aiogram.types import CallbackQuery
from services.common.localization import Localization
from services.product.registry_singleton import product_registry_service
from .image_service import ImageService
# Импорт будет добавлен в ItemY 5.2 при внедрении DI
# from handlers.dependencies import get_product_formatter_service

logger = logging.getLogger(__name__)


class CatalogService:
    """Сервис для работы с каталогом продуктов"""
    
    def __init__(self, image_service: ImageService = None):
        """
        Инициализация сервиса каталога
        
        Args:
            image_service: Сервис для работы с изображениями
        """
        self.image_service = image_service or ImageService()
        # Formatter service будет внедрен через DI в ItemY 5.2
        self.formatter_service = None
        self.logger = logging.getLogger(__name__)
    
    async def get_catalog_with_progress(self) -> List[Any]:
        """
        Получает каталог продуктов с отображением прогресса
        
        Returns:
            List[Any]: Список продуктов из каталога
        """
        try:
            self.logger.info("[CatalogService] Запрос каталога товаров")
            
            # Получаем каталог через сервис (с кэшированием)
            products = await product_registry_service.get_all_products()
            
            if not products:
                self.logger.info("[CatalogService] Каталог пуст")
                return []
            
            self.logger.info(f"[CatalogService] Найдено {len(products)} продуктов")
            return products
            
        except Exception as e:
            self.logger.error(f"[CatalogService] Ошибка при получении каталога: {e}")
            return []
    
    def _validate_product(self, product: Any) -> bool:
        """
        Валидирует продукт на наличие обязательных полей
        
        Args:
            product: Продукт для валидации
            
        Returns:
            bool: True если продукт валиден
        """
        try:
            # Проверяем наличие обязательных полей
            required_fields = ['id', 'name', 'description']
            for field in required_fields:
                if not hasattr(product, field) or not getattr(product, field):
                    return False
            return True
        except Exception as e:
            self.logger.error(f"[CatalogService] Ошибка валидации продукта: {e}")
            return False
    
    async def send_catalog_to_user(self, callback: CallbackQuery, products: List[Any], loc: Localization) -> None:
        """
        Отправляет каталог продуктов пользователю
        
        Args:
            callback: Callback запрос от пользователя
            products: Список продуктов для отправки
            loc: Объект локализации
        """
        try:
            if not products:
                await callback.message.answer(loc.t("catalog.empty"))
                return
            
            # Отправляем сообщение о прогрессе с хэштегами для навигации
            progress_message = await callback.message.answer(
                f"📦 Загружаем каталог: 0/{len(products)} продуктов...\n\n"
                f"🔍 <b>Навигация:</b> #catalog"
            )
            
            # Отправляем каждый продукт отдельным сообщением
            for i, product in enumerate(products):
                try:
                    await self._send_single_product(callback, product, loc)
                    
                    # Обновляем прогресс
                    await progress_message.edit_text(f"📦 Загружаем каталог: {i+1}/{len(products)} продуктов...")
                    
                    # Добавляем разделитель между продуктами (кроме последнего)
                    if i < len(products) - 1:
                        await callback.message.answer("☀️" * 8)
                        
                except Exception as e:
                    self.logger.error(f"[CatalogService] Ошибка при отправке продукта {getattr(product, 'id', 'unknown')}: {e}")
                    continue
            
            # Удаляем сообщение о прогрессе и отправляем финальное сообщение
            await progress_message.delete()
            await callback.message.answer(f"✅ Каталог загружен! Всего продуктов: {len(products)}")
            
            self.logger.info(f"[CatalogService] Каталог успешно отправлен: {len(products)} продуктов")
            
        except Exception as e:
            self.logger.error(f"[CatalogService] Ошибка при отправке каталога: {e}")
            await callback.message.answer(loc.t("catalog.error"))
            raise
    
    async def _send_single_product(self, callback: CallbackQuery, product: Any, loc: Localization) -> None:
        """
        Отправляет один продукт пользователю
        
        Args:
            callback: Callback запрос от пользователя
            product: Продукт для отправки
            loc: Объект локализации
        """
        try:
            # Форматируем продукт через сервис форматирования
            try:
                formatted_sections = self.formatter_service.format_product_for_telegram(product, loc)
                
                # Объединяем все секции в единый текст
                product_text = (
                    formatted_sections['main_info'] +
                    formatted_sections['composition'] +
                    formatted_sections['pricing'] +
                    formatted_sections['details']
                )
            except Exception as e:
                self.logger.error(f"[CatalogService] Ошибка сервиса форматирования для продукта {getattr(product, 'id', 'unknown')}: {e}")
                # Fallback форматирование
                product_text = f"🏷️ <b>{getattr(product, 'title', 'Продукт')}</b>\n❌ Ошибка при форматировании"
            
            # Обрезаем текст если он слишком длинный для Telegram
            original_length = len(product_text)
            product_text = self.formatter_service._truncate_text(product_text)
            final_length = len(product_text)
            
            if original_length != final_length:
                self.logger.info(f"[CatalogService] Текст продукта {getattr(product, 'id', 'unknown')} обрезан: {original_length} -> {final_length} символов")
            
            # Отправляем продукт через ImageService
            await self.image_service.send_product_with_image(
                callback=callback,
                product=product,
                product_text=product_text,
                loc=loc
            )
            
        except Exception as e:
            self.logger.error(f"[CatalogService] Ошибка при отправке продукта: {e}")
            raise
