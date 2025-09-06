"""
Базовый класс для обработчиков каталога.
Содержит общую функциональность для всех обработчиков каталога.
"""

import logging
from abc import ABC, abstractmethod
from typing import Optional, Any
from aiogram.types import CallbackQuery
from services.common.localization import Localization
from model.user_settings import UserSettings
from dependencies import get_user_settings

logger = logging.getLogger(__name__)


class BaseCatalogHandler(ABC):
    """Базовый класс для всех обработчиков каталога"""
    
    def __init__(self):
        """Инициализация базового обработчика"""
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.info(f"[{self.__class__.__name__}] Инициализирован")
    
    def get_user_id(self, callback: CallbackQuery) -> int:
        """
        Извлекает ID пользователя из callback
        
        Args:
            callback: Callback запрос от пользователя
            
        Returns:
            int: ID пользователя
        """
        try:
            user_id = callback.from_user.id
            self.logger.debug(f"[{self.__class__.__name__}] Получен user_id: {user_id}")
            return user_id
        except Exception as e:
            self.logger.error(f"[{self.__class__.__name__}] Ошибка получения user_id: {e}")
            raise
    
    def get_user_localization(self, callback: CallbackQuery) -> Localization:
        """
        Получает объект локализации для пользователя
        
        Args:
            callback: Callback запрос от пользователя
            
        Returns:
            Localization: Объект локализации
        """
        try:
            user_id = self.get_user_id(callback)
            user_settings = get_user_settings()
            lang = user_settings.get_language(user_id)
            
            loc = Localization(lang)
            self.logger.debug(f"[{self.__class__.__name__}] Получена локализация для user_id {user_id}: {lang}")
            return loc
        except Exception as e:
            self.logger.error(f"[{self.__class__.__name__}] Ошибка получения локализации: {e}")
            # Fallback на русский язык
            return Localization("ru")
    
    def get_user_settings(self) -> UserSettings:
        """
        Получает настройки пользователя
        
        Returns:
            UserSettings: Настройки пользователя
        """
        try:
            user_settings = get_user_settings()
            self.logger.debug(f"[{self.__class__.__name__}] Получены настройки пользователя")
            return user_settings
        except Exception as e:
            self.logger.error(f"[{self.__class__.__name__}] Ошибка получения настроек пользователя: {e}")
            raise
    
    def log_handler_call(self, callback: CallbackQuery, handler_name: str) -> None:
        """
        Логирует вызов обработчика
        
        Args:
            callback: Callback запрос от пользователя
            handler_name: Название обработчика
        """
        try:
            user_id = self.get_user_id(callback)
            self.logger.info(f"[{self.__class__.__name__}] {handler_name} вызван! callback.data={callback.data}, from_user={user_id}")
        except Exception as e:
            self.logger.error(f"[{self.__class__.__name__}] Ошибка логирования вызова обработчика: {e}")
    
    def extract_callback_data(self, callback: CallbackQuery) -> str:
        """
        Извлекает данные callback
        
        Args:
            callback: Callback запрос от пользователя
            
        Returns:
            str: Данные callback
        """
        try:
            data = callback.data
            self.logger.debug(f"[{self.__class__.__name__}] Извлечены данные callback: {data}")
            return data
        except Exception as e:
            self.logger.error(f"[{self.__class__.__name__}] Ошибка извлечения данных callback: {e}")
            return ""
    
    def extract_product_id_from_callback(self, callback: CallbackQuery, prefix: str = "product:details:") -> Optional[str]:
        """
        Извлекает ID продукта из callback данных
        
        Args:
            callback: Callback запрос от пользователя
            prefix: Префикс для поиска ID продукта
            
        Returns:
            Optional[str]: ID продукта или None
        """
        try:
            data = self.extract_callback_data(callback)
            if data and data.startswith(prefix):
                product_id = data[len(prefix):]
                self.logger.debug(f"[{self.__class__.__name__}] Извлечен product_id: {product_id}")
                return product_id
            else:
                self.logger.warning(f"[{self.__class__.__name__}] Не удалось извлечь product_id из данных: {data}")
                return None
        except Exception as e:
            self.logger.error(f"[{self.__class__.__name__}] Ошибка извлечения product_id: {e}")
            return None
    
    async def handle_callback_error(self, callback: CallbackQuery, error: Exception, context: str = "") -> None:
        """
        Обрабатывает ошибки callback
        
        Args:
            callback: Callback запрос от пользователя
            error: Исключение
            context: Контекст ошибки
        """
        try:
            user_id = self.get_user_id(callback)
            self.logger.error(f"[{self.__class__.__name__}] Ошибка в {context} для user_id {user_id}: {error}")
            
            # Отправляем сообщение об ошибке пользователю
            loc = self.get_user_localization(callback)
            error_message = loc.t('error.general', '❌ Произошла ошибка. Попробуйте позже.')
            
            await callback.message.answer(error_message)
            await callback.answer()
            
        except Exception as e:
            self.logger.error(f"[{self.__class__.__name__}] Ошибка при обработке ошибки callback: {e}")
            try:
                await callback.answer()
            except:
                pass
    
    @abstractmethod
    async def handle_callback(self, callback: CallbackQuery) -> None:
        """
        Абстрактный метод для обработки callback
        
        Args:
            callback: Callback запрос от пользователя
        """
        pass
    
    async def process_callback(self, callback: CallbackQuery) -> None:
        """
        Основной метод обработки callback с общей логикой
        
        Args:
            callback: Callback запрос от пользователя
        """
        try:
            # Логируем вызов
            self.log_handler_call(callback, "process_callback")
            
            # Вызываем конкретную реализацию
            await self.handle_callback(callback)
            
        except Exception as e:
            await self.handle_callback_error(callback, e, "process_callback")
        finally:
            # Всегда отвечаем на callback
            try:
                await callback.answer()
            except Exception as e:
                self.logger.error(f"[{self.__class__.__name__}] Ошибка ответа на callback: {e}")
