"""
Универсальный сервис локализации для Amanita
Расширяет существующий Localization для поддержки переводов продуктов и компонентов
"""

import logging
from typing import Optional, Dict, Any
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
    
    def __init__(
        self,
        lang: str = 'ru',
        cache_service: Any = None,
        fallback_service: Any = None,
        ipfs_service: Any = None
    ):
        """
        Инициализация сервиса локализации
        
        Args:
            lang: Язык локализации (по умолчанию 'ru')
            cache_service: Сервис кэширования (TranslationCacheService) - используется в ProductLocalizationService
            fallback_service: Сервис fallback стратегий (FallbackLocalizationService) - используется в ProductLocalizationService
            ipfs_service: Сервис работы с IPFS (MultilingualIPFSService) - содержит все зависимости включая blockchain_gateway
        """
        logger.info(f"[LocalizationService] Инициализация с языком: {lang}")
        
        # Инициализируем базовый Localization
        super().__init__(lang)
        
        # Храним зависимости для переиспользования при смене языка
        self._deps: Dict[str, Any] = {
            "cache_service": cache_service,
            "fallback_service": fallback_service,
            "ipfs_service": ipfs_service
        }
        # Инициализируем сервисы для продуктов и компонентов
        self._build_children(self.lang)
        
        logger.info("[LocalizationService] Сервисы локализации инициализированы")

    def _build_children(self, lang: str) -> None:
        """
        Создаёт/пересоздаёт дочерние сервисы с заданным языком и сохранёнными зависимостями.
        """
        logger.debug(f"[LocalizationService] Построение дочерних сервисов для языка: {lang}")
        self.product_localization = ProductLocalizationService(
            lang,
            cache_service=self._deps.get("cache_service"),
            fallback_service=self._deps.get("fallback_service"),
            ipfs_service=self._deps.get("ipfs_service"),
        )
        self.component_localization = ComponentLocalizationService(
            lang,
            cache_service=self._deps.get("cache_service"),
            fallback_service=self._deps.get("fallback_service"),
            ipfs_service=self._deps.get("ipfs_service"),
        )

    def switch_language(self, lang: str) -> None:
        """
        Переключает язык рантайм: обновляет текущий язык и пересобирает дочерние сервисы.
        Инвалидирует кэши и перезагружает fallback-данные.
        """
        try:
            if not self.is_language_supported(lang):
                logger.warning(f"[LocalizationService] Неподдерживаемый язык: {lang}")
                return
            logger.debug(f"[LocalizationService] Переключение языка: {self.lang} → {lang}")
            self.lang = lang
            # Пересоздаём дочерние сервисы с новым языком
            self._build_children(lang)
            # Инвалидируем кэши на всякий случай
            if hasattr(self.product_localization, "clear_cache"):
                self.product_localization.clear_cache()
            if hasattr(self.component_localization, "clear_cache"):
                self.component_localization.clear_cache()
            logger.info(f"[LocalizationService] Язык переключён на: {lang}")
        except Exception as e:
            logger.error(f"[LocalizationService] Ошибка при переключении языка на '{lang}': {e}")
            raise
    
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
                # Интерфейсные переводы — быстрый путь без лишнего логирования базового класса
                value = self._fast_lookup_interface(key)
                if isinstance(value, str):
                    return value
                # fallback на базовую реализацию, если структура изменена
                result = super().t(key)
                if result == key and default is not None:
                    return default
                return result
                
        except Exception as e:
            logger.error(f"[LocalizationService] Ошибка при получении перевода '{key}': {e}")
            return default or key
    
    def _fast_lookup_interface(self, key: str) -> Optional[str]:
        """
        Быстрый поиск интерфейсного ключа по self.labels, избегая лишних логов базового класса.
        """
        try:
            parts = key.split('.')
            if not parts or not isinstance(self.labels, dict):
                return None
            node: Any = self.labels
            for part in parts:
                if isinstance(node, dict) and part in node:
                    node = node[part]
                else:
                    return None
            return node if isinstance(node, str) else None
        except Exception:
            return None
    
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
    
    def get_component_translation(self, component_id: str, field: str, default: Optional[str] = None, **kwargs) -> str:
        """
        Получает перевод поля компонента
        
        Args:
            component_id: ID биологической единицы (например, 'amanita_muscaria')
            field: Поле для перевода (например, 'common_name', 'generic_description')
            default: Значение по умолчанию
            **kwargs: Параметры для подстановки
            
        Returns:
            str: Переведенный текст
        """
        key = f"component.{component_id}.{field}"
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
    
    def set_component_data(self, component_id: str, language: str, data: Dict[str, Any]) -> None:
        """
        Устанавливает данные перевода компонента
        
        Args:
            component_id: ID биологической единицы
            language: Язык перевода
            data: Словарь с переводами полей
        """
        logger.info(f"[LocalizationService] Установка данных компонента: {component_id}, язык: {language}")
        self.component_localization.set_data(component_id, language, data)
    
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
