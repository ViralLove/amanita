"""
Универсальный сервис локализации для Amanita
Расширяет существующий Localization для поддержки переводов продуктов и компонентов
"""

import logging
from typing import Optional, Dict, Any, Union
from .localization import Localization
from .product_localization import ProductLocalizationService
from .component_localization import ComponentLocalizationService

logger = logging.getLogger(__name__)


class LocalizationService(Localization):
    """
    Универсальный сервис локализации
    
    Наследует от существующего Localization для сохранения обратной совместимости
    и добавляет поддержку переводов продуктов и компонентов.
    """
    
    def __init__(self, lang: str = 'ru'):
        """
        Инициализация сервиса локализации
        
        Args:
            lang: Язык локализации (по умолчанию 'ru')
        """
        logger.info(f"[LocalizationService] Инициализация с языком: {lang}")
        
        # Инициализируем базовый Localization
        super().__init__(lang)
        
        # Инициализируем сервисы для продуктов и компонентов
        self.product_localization = ProductLocalizationService(lang)
        self.component_localization = ComponentLocalizationService(lang)
        
        logger.info("[LocalizationService] Сервисы локализации инициализированы")
    
    def t(self, key: str, default: Optional[str] = None, **kwargs) -> str:
        """
        Универсальный метод локализации
        
        Поддерживает три типа переводов:
        - interface.* - интерфейсные переводы (существующая функциональность)
        - product.* - переводы продуктов (новая функциональность)
        - component.* - переводы компонентов (новая функциональность)
        
        Args:
            key: Ключ перевода (например, 'interface.onboarding.welcome' или 'product.amanita_powder.title')
            default: Значение по умолчанию при отсутствии перевода
            **kwargs: Параметры для подстановки в перевод
            
        Returns:
            str: Переведенный текст или fallback значение
        """
        logger.debug(f"[LocalizationService] Запрос перевода: key='{key}', lang='{self.lang}'")
        
        try:
            # Определяем тип перевода по префиксу ключа
            if key.startswith('product.'):
                logger.debug("[LocalizationService] Обработка как перевод продукта")
                return self.product_localization.get_translation(key, default, **kwargs)
            
            elif key.startswith('component.'):
                logger.debug("[LocalizationService] Обработка как перевод компонента")
                return self.component_localization.get_translation(key, default, **kwargs)
            
            else:
                # Интерфейсные переводы - используем базовый функционал
                logger.debug("[LocalizationService] Обработка как интерфейсный перевод")
                # ✅ ИСПРАВЛЕНИЕ: Localization.t() принимает только key, без default
                result = super().t(key)
                # Если результат равен ключу (fallback), используем default
                if result == key and default is not None:
                    return default
                return result
                
        except Exception as e:
            logger.error(f"[LocalizationService] Ошибка при получении перевода '{key}': {e}")
            return default or key
    
    def get_product_translation(self, business_id: str, field: str, default: Optional[str] = None, **kwargs) -> str:
        """
        Получает перевод поля продукта
        
        Args:
            business_id: ID продукта (например, 'amanita_powder_001')
            field: Поле для перевода (например, 'title', 'description')
            default: Значение по умолчанию
            **kwargs: Параметры для подстановки
            
        Returns:
            str: Переведенный текст
        """
        key = f"product.{business_id}.{field}"
        return self.t(key, default, **kwargs)
    
    def get_component_translation(self, biounit_id: str, field: str, default: Optional[str] = None, **kwargs) -> str:
        """
        Получает перевод поля компонента
        
        Args:
            biounit_id: ID биологической единицы (например, 'amanita_muscaria')
            field: Поле для перевода (например, 'common_name', 'generic_description')
            default: Значение по умолчанию
            **kwargs: Параметры для подстановки
            
        Returns:
            str: Переведенный текст
        """
        key = f"component.{biounit_id}.{field}"
        return self.t(key, default, **kwargs)
    
    def set_product_data(self, business_id: str, language: str, data: Dict[str, Any]) -> None:
        """
        Устанавливает данные перевода продукта
        
        Args:
            business_id: ID продукта
            language: Язык перевода
            data: Словарь с переводами полей
        """
        logger.info(f"[LocalizationService] Установка данных продукта: {business_id}, язык: {language}")
        self.product_localization.set_data(business_id, language, data)
    
    def set_component_data(self, biounit_id: str, language: str, data: Dict[str, Any]) -> None:
        """
        Устанавливает данные перевода компонента
        
        Args:
            biounit_id: ID биологической единицы
            language: Язык перевода
            data: Словарь с переводами полей
        """
        logger.info(f"[LocalizationService] Установка данных компонента: {biounit_id}, язык: {language}")
        self.component_localization.set_data(biounit_id, language, data)
    
    def get_supported_languages(self) -> list:
        """
        Получает список поддерживаемых языков
        
        Returns:
            list: Список кодов языков
        """
        return ['ru', 'en', 'es', 'de', 'fr', 'it', 'pt', 'pl', 'uk', 'tr', 'ar', 'zh', 'ja', 'ko', 'hi']
    
    def is_language_supported(self, language: str) -> bool:
        """
        Проверяет, поддерживается ли язык
        
        Args:
            language: Код языка для проверки
            
        Returns:
            bool: True если язык поддерживается
        """
        return language in self.get_supported_languages()
