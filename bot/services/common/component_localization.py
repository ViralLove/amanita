"""
Component localization service (shared components / biounits).

This module resolves keys like `component.<component_id>.<field>` into localized strings.

Important terminology (SSOT for this repo):
- The per-component description payload is stored off-chain and referenced from the on-chain
  AmanitaInternational mapping via `getComplexFieldCID(className, language)` where
  `className="ComponentDescription.<component_id>"`.
- The actual stored JSON for ComponentDescription is typically a *plain dict* with keys like
  `generic_description/effects/shamanic/warnings` (see `data/components/.../complex_fields/*.json`).
- `MultilingualIPFSService` is responsible for fetching this payload and normalizing it when needed.
"""

import logging
from typing import Optional, Dict, Any, List, Union
import json
import os
from pathlib import Path
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class ComponentLocalizationService:
    """
    Localizes component fields.

    Key format: `component.<component_id>.<field>`

    Data sources:
    - cached translations (in-memory + optional external cache service)
    - IPFS/Arweave payloads via `MultilingualIPFSService`
    - fallback service and local template JSONs
    """
    
    def __init__(self, language: str = 'ru', cache_service=None, fallback_service=None, ipfs_service=None):
        """
        Инициализация сервиса локализации компонентов
        
        Args:
            language: Язык по умолчанию
            cache_service: Сервис кэширования (TranslationCacheService)
            fallback_service: Сервис fallback стратегий (FallbackLocalizationService)
            ipfs_service: Сервис работы с IPFS (MultilingualIPFSService)
        """
        self.language = language
        self.cache_service = cache_service
        self.fallback_service = fallback_service
        self.ipfs_service = ipfs_service
        
        # Локальный кэш для быстрого доступа
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.fallback_data: Dict[str, Dict[str, Any]] = {}
        
        # Поддерживаемые языки
        self.supported_languages = ['ru', 'en', 'es', 'fr', 'de', 'it', 'pt', 'zh', 'ja', 'ko', 'ar', 'hi', 'tr', 'pl', 'uk']
        
        # "Complex fields" here means global templates (NOT per-component payloads).
        # Per-component ComponentDescription is fetched via `MultilingualIPFSService.get_component_translations()`
        # using the AmanitaInternational complex-field CID mapping.
        #
        # This set is intentionally empty in current production flows (reserved for future global templates).
        self.COMPLEX_COMPONENT_FIELDS = set()
        
        # Загружаем fallback данные из JSON файлов
        self._load_fallback_data()
        
        logger.info(f"[ComponentLocalizationService] Инициализирован для языка: {language}")
    
    def _load_fallback_data(self) -> None:
        """Загружает fallback данные из JSON файлов"""
        try:
            from config import APP_ROOT_DIR
            project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
            fallback_path = os.path.join(project_root, APP_ROOT_DIR, "templates", "components", f"{self.language}.json")
            
            if os.path.exists(fallback_path):
                with open(fallback_path, 'r', encoding='utf-8') as f:
                    self.fallback_data = json.load(f)
                logger.info(f"[ComponentLocalizationService] Загружены fallback данные из {fallback_path}")
            else:
                logger.warning(f"[ComponentLocalizationService] Fallback файл не найден: {fallback_path}")
                self.fallback_data = {}
                
        except Exception as e:
            logger.error(f"[ComponentLocalizationService] Ошибка загрузки fallback данных: {e}")
            self.fallback_data = {}
    
    def _is_complex_field(self, field: str) -> bool:
        """
        Returns True only for global template fields (reserved).

        Per-component fields like `generic_description/effects/...` are retrieved via
        `MultilingualIPFSService.get_component_translations(component_id, language)` and are NOT
        routed through this template mechanism.

        Args:
            field: Field name (e.g., "generic_description", "title")
            
        Returns:
            bool: True if the field is a global template field
        """
        return field in self.COMPLEX_COMPONENT_FIELDS
    
    def _extract_field_from_complex_data(self, complex_data: Dict[str, Any], field: str) -> Optional[str]:
        """
        Extracts a specific field from a ComponentDescription payload.
        
        Args:
            complex_data: ComponentDescription fields dict
                         Format: {"generic_description": "...", "effects": "...", ...}
            field: Field name (generic_description/effects/shamanic/warnings/...)
            
        Returns:
            str or None: Field value, if present
        """
        try:
            if not isinstance(complex_data, dict):
                logger.warning(f"[ComponentLocalizationService] complex_data не является словарем: {type(complex_data)}")
                return None
            
            if not complex_data:
                logger.debug(f"[ComponentLocalizationService] complex_data пуст для поля {field}")
                return None
            
            # complex_data - это уже fields из get_component_description()
            # Формат: {"generic_description": "...", "effects": "...", ...}
            value = complex_data.get(field)
            
            if value is None:
                logger.debug(f"[ComponentLocalizationService] Поле {field} отсутствует в complex_data")
                return None
            
            # Преобразуем значение в строку, если это не строка
            if isinstance(value, str):
                return value
            elif isinstance(value, (int, float, bool)):
                return str(value)
            elif isinstance(value, dict) or isinstance(value, list):
                # Если это сложная структура, преобразуем в JSON строку
                import json
                return json.dumps(value, ensure_ascii=False)
            else:
                return str(value)
                
        except Exception as e:
            logger.error(f"[ComponentLocalizationService] Ошибка извлечения поля {field} из complex_data: {e}")
            return None
    
    def get_translation(self, key: str, default: Optional[str] = None, **kwargs) -> str:
        """
        Получает перевод компонента с поддержкой IPFS и fallback стратегий
        
        Args:
            key: Ключ в формате 'component.{component_id}.{field}'
            default: Значение по умолчанию
            **kwargs: Параметры для подстановки
            
        Returns:
            str: Переведенный текст
        """
        logger.debug(f"[ComponentLocalizationService] Запрос перевода: {key}")
        
        try:
            # Парсим ключ: component.{component_id}.{field}
            parts = key.split('.')
            if len(parts) < 3 or parts[0] != 'component':
                logger.error(f"[ComponentLocalizationService] Неверный формат ключа: {key}")
                return default or key
            
            component_id = parts[1]
            field = parts[2]
            
            # ✅ ИСПРАВЛЕНИЕ: Проверяем пустое поле
            if not field:
                logger.warning(f"[ComponentLocalizationService] Пустое поле в ключе: {key}")
                return default or f"[field]"
            
            # 1. Проверяем кэш
            translation = self._get_from_cache(component_id, field)
            if translation:
                logger.debug(f"[ComponentLocalizationService] Найден в кэше: {translation}")
                return self._format_translation(translation, **kwargs)
            
            # 2. Пытаемся загрузить из IPFS
            translation = self._load_from_ipfs(component_id, field)
            if translation:
                logger.debug(f"[ComponentLocalizationService] Загружен из IPFS: {translation}")
                # Сохраняем в кэш
                self._save_to_cache(component_id, field, translation)
                return self._format_translation(translation, **kwargs)
            
            # 3. Используем fallback стратегию
            if self.fallback_service:
                translation = self._get_fallback_translation(component_id, field, default)
                if translation:
                    logger.debug(f"[ComponentLocalizationService] Fallback: {translation}")
                    return self._format_translation(translation, **kwargs)
            
            # 4. Пытаемся получить из fallback данных
            if component_id in self.fallback_data.get('components', {}):
                component_data = self.fallback_data['components'][component_id]
                if field in component_data:
                    translation = component_data[field]
                    logger.debug(f"[ComponentLocalizationService] Найден в fallback: {translation}")
                    return self._format_translation(translation, **kwargs)
            
            # Если ничего не найдено, возвращаем fallback
            logger.warning(f"[ComponentLocalizationService] Перевод не найден: {key}")
            return default or f"[{field}]"
            
        except Exception as e:
            logger.error(f"[ComponentLocalizationService] Ошибка при получении перевода '{key}': {e}")
            return default or key
    
    def _format_translation(self, translation: str, **kwargs) -> str:
        """
        Форматирует перевод с подстановкой параметров
        
        Args:
            translation: Текст перевода
            **kwargs: Параметры для подстановки
            
        Returns:
            str: Отформатированный текст
        """
        try:
            if kwargs:
                return translation.format(**kwargs)
            return translation
        except Exception as e:
            logger.error(f"[ComponentLocalizationService] Ошибка форматирования перевода: {e}")
            return translation
    
    def set_data(self, component_id: str, language: str, data: Dict[str, Any]) -> None:
        """
        Устанавливает данные перевода компонента
        
        Args:
            component_id: ID биологической единицы
            language: Язык перевода
            data: Словарь с переводами полей
        """
        cache_key = f"{component_id}_{language}"
        self.cache[cache_key] = data
        logger.info(f"[ComponentLocalizationService] Установлены данные для {component_id} на языке {language}")
    
    def get_cached_data(self, component_id: str, language: str) -> Optional[Dict[str, Any]]:
        """
        Получает кэшированные данные компонента
        
        Args:
            component_id: ID биологической единицы
            language: Язык перевода
            
        Returns:
            Dict[str, Any] или None: Кэшированные данные
        """
        cache_key = f"{component_id}_{language}"
        return self.cache.get(cache_key)
    
    def clear_cache(self) -> None:
        """Очищает кэш переводов"""
        self.cache.clear()
        logger.info("[ComponentLocalizationService] Кэш очищен")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Получает статистику кэша
        
        Returns:
            Dict[str, Any]: Статистика кэша
        """
        return {
            'cached_components': len(self.cache),
            'fallback_components': len(self.fallback_data.get('components', {})),
            'memory_usage': sum(len(str(data)) for data in self.cache.values()),
            'language': self.language,
            'supported_languages': len(self.supported_languages)
        }
    
    def _get_from_cache(self, component_id: str, field: str) -> Optional[str]:
        """
        Получает перевод из кэша
        
        Args:
            component_id: ID биологической единицы
            field: Поле для перевода
            
        Returns:
            str или None: Переведенный текст
        """
        try:
            # Проверяем локальный кэш
            cache_key = f"{component_id}_{self.language}"
            if cache_key in self.cache:
                component_data = self.cache[cache_key]
                if field in component_data:
                    return component_data[field]
            
            # Проверяем внешний кэш-сервис
            if self.cache_service:
                cache_key = f"component_{component_id}_{field}_{self.language}"
                cached_data = self.cache_service.get(cache_key, 'component')
                if cached_data:
                    return cached_data
            
            return None
            
        except Exception as e:
            logger.error(f"[ComponentLocalizationService] Ошибка получения из кэша: {e}")
            return None
    
    def _save_to_cache(self, component_id: str, field: str, translation: str) -> None:
        """
        Сохраняет перевод в кэш
        
        Args:
            component_id: ID биологической единицы
            field: Поле для перевода
            translation: Переведенный текст
        """
        try:
            # Сохраняем в локальный кэш
            cache_key = f"{component_id}_{self.language}"
            if cache_key not in self.cache:
                self.cache[cache_key] = {}
            self.cache[cache_key][field] = translation
            
            # Сохраняем во внешний кэш-сервис
            if self.cache_service:
                cache_key = f"component_{component_id}_{field}_{self.language}"
                self.cache_service.set(cache_key, translation, 'component')
                
        except Exception as e:
            logger.error(f"[ComponentLocalizationService] Ошибка сохранения в кэш: {e}")
    
    def _load_from_ipfs(self, component_id: str, field: str) -> Optional[str]:
        """
        Loads a translation from IPFS/Arweave.
        
        Args:
            component_id: Component business id (biounit_id)
            field: Field name
            
        Returns:
            str or None: Translation
        """
        try:
            if not self.ipfs_service:
                return None
            
            # Determine the field routing strategy
            if self._is_complex_field(field):
                # Global template (reserved; not used in current production flows)
                logger.warning(f"[ComponentLocalizationService] Complex field {field} запрошен, но не используется в production")
                return None
            else:
                # Per-component field → fetch ComponentDescription fields for this component_id+language.
                component_data = self.ipfs_service.get_component_translations(component_id, self.language)
                if component_data and field in component_data:
                    logger.debug(f"[ComponentLocalizationService] Загружен per-component field {field} из IPFS для {component_id}")
                    return component_data[field]
            
            return None
            
        except Exception as e:
            logger.error(f"[ComponentLocalizationService] Ошибка загрузки из IPFS: {e}")
            return None
    
    def _get_fallback_translation(self, component_id: str, field: str, default: Optional[str]) -> Optional[str]:
        """
        Returns a fallback translation for per-component fields.
        
        Args:
            component_id: Component business id (biounit_id)
            field: Field name
            default: Default value
            
        Returns:
            str or None
        """
        try:
            if not self.fallback_service:
                return None
            
            key = f"component.{component_id}.{field}"

            # Готовим источники переводов (nested dict под требования fallback сервиса)
            sources: Dict[str, Any] = {}
            
            # Determine the field routing strategy
            if self._is_complex_field(field):
                # Global template (reserved; not used in current production flows)
                logger.warning(f"[ComponentLocalizationService] Complex field {field} в fallback запрошен, но не используется в production")
                sources[self.language] = {}
                sources['ru'] = {}  # default language
            else:
                # Per-component field → build sources from cache and/or IPFS payload for fallback service.
                
                # requested language
                requested_data = self.get_cached_data(component_id, self.language) or {}
                if not requested_data and self.ipfs_service:
                    ipfs_payload = self.ipfs_service.get_component_translations(component_id, self.language) or {}
                    if isinstance(ipfs_payload, dict):
                        requested_data = ipfs_payload
                sources[self.language] = {"component": {component_id: requested_data}} if requested_data else {}

                # default language (ru)
                default_lang = 'ru'
                default_data = self.get_cached_data(component_id, default_lang) or {}
                if not default_data and self.ipfs_service:
                    ipfs_payload_default = self.ipfs_service.get_component_translations(component_id, default_lang) or {}
                    if isinstance(ipfs_payload_default, dict):
                        default_data = ipfs_payload_default
                sources[default_lang] = {"component": {component_id: default_data}} if default_data else {}
            
            # Вызов нового API fallback
            result = self.fallback_service.get_translation_with_fallback(
                key=key,
                requested_language=self.language,
                translation_sources=sources,
                default=default or f"[{field}]"
            )
            
            return getattr(result, "translation", None)
            
        except Exception as e:
            logger.error(f"[ComponentLocalizationService] Ошибка fallback перевода: {e}")
            return None
    
    def _get_translation_for_language(self, component_id: str, field: str, language: str) -> Optional[str]:
        """
        Получает перевод для конкретного языка
        
        Args:
            component_id: ID биологической единицы
            field: Поле для перевода
            language: Язык
            
        Returns:
            str или None: Перевод
        """
        try:
            # Проверяем кэш для конкретного языка
            cache_key = f"{component_id}_{language}"
            if cache_key in self.cache:
                component_data = self.cache[cache_key]
                if field in component_data:
                    return component_data[field]
            
            # Проверяем fallback данные
            if component_id in self.fallback_data.get('components', {}):
                component_data = self.fallback_data['components'][component_id]
                if field in component_data:
                    return component_data[field]
            
            return None
            
        except Exception as e:
            logger.error(f"[ComponentLocalizationService] Ошибка получения перевода для языка {language}: {e}")
            return None
    
    def set_component_data(self, component_id: str, language: str, data: Dict[str, Any]) -> None:
        """
        Устанавливает данные компонента для конкретного языка
        
        Args:
            component_id: ID биологической единицы
            language: Язык
            data: Данные компонента
        """
        try:
            cache_key = f"{component_id}_{language}"
            self.cache[cache_key] = data
            
            # Сохраняем во внешний кэш
            if self.cache_service:
                for field, value in data.items():
                    cache_key = f"component_{component_id}_{field}_{language}"
                    self.cache_service.set(cache_key, value, 'component')
            
            logger.info(f"[ComponentLocalizationService] Установлены данные для {component_id} на языке {language}")
            
        except Exception as e:
            logger.error(f"[ComponentLocalizationService] Ошибка установки данных: {e}")
    
    def get_supported_languages(self) -> List[str]:
        """
        Получает список поддерживаемых языков
        
        Returns:
            List[str]: Список языков
        """
        return self.supported_languages.copy()
    
    def is_language_supported(self, language: str) -> bool:
        """
        Проверяет, поддерживается ли язык
        
        Args:
            language: Код языка
            
        Returns:
            bool: True если поддерживается
        """
        return language in self.supported_languages
    
    def get_component_languages(self, component_id: str) -> List[str]:
        """
        Получает список языков, для которых есть переводы компонента
        
        Args:
            component_id: ID биологической единицы
            
        Returns:
            List[str]: Список языков
        """
        try:
            languages = []
            for cache_key in self.cache.keys():
                if cache_key.startswith(f"{component_id}_"):
                    language = cache_key.split('_', 1)[1]
                    if language in self.supported_languages:
                        languages.append(language)
            
            return languages
            
        except Exception as e:
            logger.error(f"[ComponentLocalizationService] Ошибка получения языков компонента: {e}")
            return []
    
    def preload_component_translations(self, component_id: str, languages: List[str] = None) -> None:
        """
        Предзагружает переводы компонента для указанных языков
        
        Args:
            component_id: ID биологической единицы
            languages: Список языков (если None, загружает все поддерживаемые)
        """
        try:
            if languages is None:
                languages = self.supported_languages
            
            for language in languages:
                if not self.is_language_supported(language):
                    continue
                
                # Проверяем, есть ли уже данные в кэше
                cache_key = f"{component_id}_{language}"
                if cache_key in self.cache:
                    continue
                
                # Загружаем из IPFS
                if self.ipfs_service:
                    component_data = self.ipfs_service.get_component_translations(component_id, language)
                    if component_data:
                        self.cache[cache_key] = component_data
                        logger.debug(f"[ComponentLocalizationService] Предзагружены переводы для {component_id} на языке {language}")
            
        except Exception as e:
            logger.error(f"[ComponentLocalizationService] Ошибка предзагрузки переводов: {e}")
