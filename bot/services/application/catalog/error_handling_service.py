"""
Сервис для обработки ошибок в каталоге.
Содержит централизованную логику обработки ошибок и fallback стратегии.
"""

import logging
from typing import Dict, Any, Optional, Callable
from aiogram.types import CallbackQuery, Message
from bot.services.common.localization import Localization

logger = logging.getLogger(__name__)


class ErrorHandlingService:
    """Сервис для обработки ошибок в каталоге"""
    
    def __init__(self):
        """Инициализация сервиса обработки ошибок"""
        self.logger = logging.getLogger(__name__)
        self.error_counts: Dict[str, int] = {}
        self.fallback_strategies: Dict[str, Callable] = {}
        self.logger.info("[ErrorHandlingService] Инициализирован")
    
    async def handle_catalog_error(self, error: Exception, callback: CallbackQuery, 
                                 loc: Localization, context: str = "") -> bool:
        """
        Обрабатывает ошибки каталога
        
        Args:
            error: Исключение для обработки
            callback: Callback запрос
            loc: Объект локализации
            context: Контекст ошибки
            
        Returns:
            bool: True если ошибка обработана успешно
        """
        try:
            error_key = f"catalog_{context}"
            self._increment_error_count(error_key)
            
            self.logger.error(f"[ErrorHandlingService] Ошибка каталога ({context}): {error}")
            
            # Определяем тип ошибки и выбираем стратегию
            error_message = self._get_catalog_error_message(error, loc)
            
            await callback.message.answer(error_message)
            await callback.answer()
            
            # Применяем fallback стратегию если доступна
            if error_key in self.fallback_strategies:
                await self.fallback_strategies[error_key](callback, loc)
            
            return True
            
        except Exception as e:
            self.logger.error(f"[ErrorHandlingService] Ошибка при обработке ошибки каталога: {e}")
            return False
    
    async def handle_product_error(self, error: Exception, callback: CallbackQuery, 
                                 loc: Localization, product_id: str = "") -> bool:
        """
        Обрабатывает ошибки продуктов
        
        Args:
            error: Исключение для обработки
            callback: Callback запрос
            loc: Объект локализации
            product_id: ID продукта
            
        Returns:
            bool: True если ошибка обработана успешно
        """
        try:
            error_key = f"product_{product_id}"
            self._increment_error_count(error_key)
            
            self.logger.error(f"[ErrorHandlingService] Ошибка продукта ({product_id}): {error}")
            
            # Определяем тип ошибки и выбираем стратегию
            error_message = self._get_product_error_message(error, loc, product_id)
            
            await callback.message.answer(error_message)
            await callback.answer()
            
            # Применяем fallback стратегию если доступна
            if error_key in self.fallback_strategies:
                await self.fallback_strategies[error_key](callback, loc)
            
            return True
            
        except Exception as e:
            self.logger.error(f"[ErrorHandlingService] Ошибка при обработке ошибки продукта: {e}")
            return False
    
    async def handle_image_error(self, error: Exception, callback: CallbackQuery, 
                               loc: Localization, image_url: str = "") -> bool:
        """
        Обрабатывает ошибки изображений
        
        Args:
            error: Исключение для обработки
            callback: Callback запрос
            loc: Объект локализации
            image_url: URL изображения
            
        Returns:
            bool: True если ошибка обработана успешно
        """
        try:
            error_key = f"image_{hash(image_url) if image_url else 'unknown'}"
            self._increment_error_count(error_key)
            
            self.logger.error(f"[ErrorHandlingService] Ошибка изображения ({image_url}): {error}")
            
            # Определяем тип ошибки и выбираем стратегию
            error_message = self._get_image_error_message(error, loc)
            
            await callback.message.answer(error_message)
            await callback.answer()
            
            # Применяем fallback стратегию если доступна
            if error_key in self.fallback_strategies:
                await self.fallback_strategies[error_key](callback, loc)
            
            return True
            
        except Exception as e:
            self.logger.error(f"[ErrorHandlingService] Ошибка при обработке ошибки изображения: {e}")
            return False
    
    def _get_catalog_error_message(self, error: Exception, loc: Localization) -> str:
        """
        Получает сообщение об ошибке каталога
        
        Args:
            error: Исключение
            loc: Объект локализации
            
        Returns:
            str: Сообщение об ошибке
        """
        try:
            error_type = type(error).__name__
            
            if "timeout" in str(error).lower():
                return loc.t('catalog.error.timeout', '⏰ Время ожидания истекло. Попробуйте позже.')
            elif "connection" in str(error).lower():
                return loc.t('catalog.error.connection', '🔌 Ошибка подключения. Проверьте интернет.')
            elif "not found" in str(error).lower():
                return loc.t('catalog.error.not_found', '📭 Каталог не найден.')
            else:
                return loc.t('catalog.error.general', '❌ Ошибка загрузки каталога. Попробуйте позже.')
                
        except Exception as e:
            self.logger.error(f"[ErrorHandlingService] Ошибка получения сообщения об ошибке каталога: {e}")
            return "❌ Ошибка каталога"
    
    def _get_product_error_message(self, error: Exception, loc: Localization, product_id: str) -> str:
        """
        Получает сообщение об ошибке продукта
        
        Args:
            error: Исключение
            loc: Объект локализации
            product_id: ID продукта
            
        Returns:
            str: Сообщение об ошибке
        """
        try:
            error_type = type(error).__name__
            
            if "not found" in str(error).lower():
                return loc.t('product.error.not_found', f'📭 Продукт {product_id} не найден.')
            elif "timeout" in str(error).lower():
                return loc.t('product.error.timeout', '⏰ Время ожидания истекло. Попробуйте позже.')
            elif "connection" in str(error).lower():
                return loc.t('product.error.connection', '🔌 Ошибка подключения. Проверьте интернет.')
            else:
                return loc.t('product.error.general', f'❌ Ошибка загрузки продукта {product_id}.')
                
        except Exception as e:
            self.logger.error(f"[ErrorHandlingService] Ошибка получения сообщения об ошибке продукта: {e}")
            return f"❌ Ошибка продукта {product_id}"
    
    def _get_image_error_message(self, error: Exception, loc: Localization) -> str:
        """
        Получает сообщение об ошибке изображения
        
        Args:
            error: Исключение
            loc: Объект локализации
            
        Returns:
            str: Сообщение об ошибке
        """
        try:
            error_type = type(error).__name__
            
            if "timeout" in str(error).lower():
                return loc.t('image.error.timeout', '⏰ Время загрузки изображения истекло.')
            elif "connection" in str(error).lower():
                return loc.t('image.error.connection', '🔌 Ошибка подключения при загрузке изображения.')
            elif "not found" in str(error).lower():
                return loc.t('image.error.not_found', '📭 Изображение не найдено.')
            else:
                return loc.t('image.error.general', '❌ Ошибка загрузки изображения.')
                
        except Exception as e:
            self.logger.error(f"[ErrorHandlingService] Ошибка получения сообщения об ошибке изображения: {e}")
            return "❌ Ошибка изображения"
    
    def _increment_error_count(self, error_key: str) -> None:
        """
        Увеличивает счетчик ошибок
        
        Args:
            error_key: Ключ ошибки
        """
        try:
            self.error_counts[error_key] = self.error_counts.get(error_key, 0) + 1
            
            # Логируем частые ошибки
            if self.error_counts[error_key] > 5:
                self.logger.warning(f"[ErrorHandlingService] Частая ошибка: {error_key} ({self.error_counts[error_key]} раз)")
                
        except Exception as e:
            self.logger.error(f"[ErrorHandlingService] Ошибка увеличения счетчика ошибок: {e}")
    
    def register_fallback_strategy(self, error_key: str, strategy: Callable) -> None:
        """
        Регистрирует fallback стратегию для ошибки
        
        Args:
            error_key: Ключ ошибки
            strategy: Функция fallback стратегии
        """
        try:
            self.fallback_strategies[error_key] = strategy
            self.logger.info(f"[ErrorHandlingService] Зарегистрирована fallback стратегия для: {error_key}")
            
        except Exception as e:
            self.logger.error(f"[ErrorHandlingService] Ошибка регистрации fallback стратегии: {e}")
    
    def get_error_statistics(self) -> Dict[str, int]:
        """
        Возвращает статистику ошибок
        
        Returns:
            Dict[str, int]: Словарь с количеством ошибок по типам
        """
        return self.error_counts.copy()
    
    def clear_error_statistics(self) -> None:
        """Очищает статистику ошибок"""
        self.error_counts.clear()
        self.logger.info("[ErrorHandlingService] Статистика ошибок очищена")
