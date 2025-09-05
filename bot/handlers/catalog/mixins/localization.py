"""
Миксин для работы с локализацией в обработчиках каталога.
Содержит логику получения и кэширования локализации.
"""

import logging
from typing import Optional, Dict, Any
from aiogram.types import CallbackQuery
from bot.services.common.localization import Localization
from bot.model.user_settings import UserSettings
from bot.dependencies import get_user_settings

logger = logging.getLogger(__name__)


class LocalizationMixin:
    """Миксин для работы с локализацией в обработчиках каталога"""
    
    def __init__(self):
        """Инициализация миксина локализации"""
        self.logger = logging.getLogger(self.__class__.__name__)
        self._localization_cache: Dict[int, Localization] = {}
        self.logger.info(f"[{self.__class__.__name__}] LocalizationMixin инициализирован")
    
    def get_localization(self, callback: CallbackQuery, use_cache: bool = True) -> Localization:
        """
        Получает объект локализации для пользователя
        
        Args:
            callback: Callback запрос от пользователя
            use_cache: Использовать кэш локализации
            
        Returns:
            Localization: Объект локализации
        """
        try:
            user_id = callback.from_user.id
            
            # Проверяем кэш
            if use_cache and user_id in self._localization_cache:
                cached_loc = self._localization_cache[user_id]
                self.logger.debug(f"[{self.__class__.__name__}] Локализация получена из кэша для user_id {user_id}")
                return cached_loc
            
            # Получаем язык пользователя
            user_settings = get_user_settings()
            lang = user_settings.get_language(user_id)
            
            # Создаем объект локализации
            loc = Localization(lang)
            
            # Сохраняем в кэш
            if use_cache:
                self._localization_cache[user_id] = loc
            
            self.logger.debug(f"[{self.__class__.__name__}] Получена локализация для user_id {user_id}: {lang}")
            return loc
            
        except Exception as e:
            self.logger.error(f"[{self.__class__.__name__}] Ошибка получения локализации: {e}")
            # Fallback на русский язык
            fallback_loc = Localization("ru")
            if use_cache:
                self._localization_cache[callback.from_user.id] = fallback_loc
            return fallback_loc
    
    def translate(self, key: str, callback: CallbackQuery, default: str = "", 
                  use_cache: bool = True, **kwargs) -> str:
        """
        Переводит текст с использованием локализации пользователя
        
        Args:
            key: Ключ для перевода
            callback: Callback запрос от пользователя
            default: Значение по умолчанию
            use_cache: Использовать кэш локализации
            **kwargs: Дополнительные параметры для перевода
            
        Returns:
            str: Переведенный текст
        """
        try:
            loc = self.get_localization(callback, use_cache)
            translated_text = loc.t(key, default, **kwargs)
            
            self.logger.debug(f"[{self.__class__.__name__}] Переведен текст: {key} -> {translated_text}")
            return translated_text
            
        except Exception as e:
            self.logger.error(f"[{self.__class__.__name__}] Ошибка перевода текста: {e}")
            return default or key
    
    def get_user_language(self, callback: CallbackQuery) -> str:
        """
        Получает язык пользователя
        
        Args:
            callback: Callback запрос от пользователя
            
        Returns:
            str: Код языка пользователя
        """
        try:
            user_id = callback.from_user.id
            user_settings = get_user_settings()
            lang = user_settings.get_language(user_id)
            
            self.logger.debug(f"[{self.__class__.__name__}] Получен язык пользователя {user_id}: {lang}")
            return lang
            
        except Exception as e:
            self.logger.error(f"[{self.__class__.__name__}] Ошибка получения языка пользователя: {e}")
            return "ru"  # Fallback на русский язык
    
    def set_user_language(self, callback: CallbackQuery, language: str) -> bool:
        """
        Устанавливает язык пользователя
        
        Args:
            callback: Callback запрос от пользователя
            language: Код языка для установки
            
        Returns:
            bool: True если язык установлен успешно
        """
        try:
            user_id = callback.from_user.id
            user_settings = get_user_settings()
            
            # Устанавливаем язык
            user_settings.set_language(user_id, language)
            
            # Обновляем кэш локализации
            if user_id in self._localization_cache:
                self._localization_cache[user_id] = Localization(language)
            
            self.logger.info(f"[{self.__class__.__name__}] Установлен язык для user_id {user_id}: {language}")
            return True
            
        except Exception as e:
            self.logger.error(f"[{self.__class__.__name__}] Ошибка установки языка пользователя: {e}")
            return False
    
    def clear_localization_cache(self, user_id: Optional[int] = None) -> None:
        """
        Очищает кэш локализации
        
        Args:
            user_id: ID пользователя для очистки (если None - очищает весь кэш)
        """
        try:
            if user_id is not None:
                if user_id in self._localization_cache:
                    del self._localization_cache[user_id]
                    self.logger.debug(f"[{self.__class__.__name__}] Очищен кэш локализации для user_id {user_id}")
            else:
                self._localization_cache.clear()
                self.logger.info(f"[{self.__class__.__name__}] Очищен весь кэш локализации")
                
        except Exception as e:
            self.logger.error(f"[{self.__class__.__name__}] Ошибка очистки кэша локализации: {e}")
    
    def get_localization_cache_size(self) -> int:
        """
        Возвращает размер кэша локализации
        
        Returns:
            int: Количество записей в кэше
        """
        return len(self._localization_cache)
    
    def get_localization_cache_info(self) -> Dict[str, Any]:
        """
        Возвращает информацию о кэше локализации
        
        Returns:
            Dict[str, Any]: Информация о кэше
        """
        try:
            return {
                'cache_size': len(self._localization_cache),
                'cached_users': list(self._localization_cache.keys()),
                'languages': [loc.language for loc in self._localization_cache.values()]
            }
        except Exception as e:
            self.logger.error(f"[{self.__class__.__name__}] Ошибка получения информации о кэше: {e}")
            return {}
    
    def is_language_supported(self, language: str) -> bool:
        """
        Проверяет, поддерживается ли язык
        
        Args:
            language: Код языка для проверки
            
        Returns:
            bool: True если язык поддерживается
        """
        try:
            # Список поддерживаемых языков
            supported_languages = ["ru", "en", "es", "fr", "de", "it", "pt", "zh", "ja", "ko"]
            return language in supported_languages
            
        except Exception as e:
            self.logger.error(f"[{self.__class__.__name__}] Ошибка проверки поддержки языка: {e}")
            return False
    
    def get_supported_languages(self) -> list:
        """
        Возвращает список поддерживаемых языков
        
        Returns:
            list: Список кодов поддерживаемых языков
        """
        return ["ru", "en", "es", "fr", "de", "it", "pt", "zh", "ja", "ko"]
