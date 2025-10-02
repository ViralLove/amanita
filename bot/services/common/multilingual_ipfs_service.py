"""
MultilingualIPFSService - Сервис для работы с мультиязычными данными в IPFS

Обеспечивает загрузку, кэширование и валидацию переводов продуктов и компонентов
из IPFS с поддержкой fallback стратегий и оптимизации производительности.
"""

import logging
import json
import asyncio
from typing import Optional, Dict, Any, List, Union
from datetime import datetime, timedelta
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

@dataclass
class IPFSTranslationData:
    """Структура данных для мультиязычного перевода в IPFS"""
    business_id: str
    language: str
    data: Dict[str, Any]
    cid: str
    timestamp: datetime
    version: str = "1.0"

@dataclass
class IPFSCacheEntry:
    """Запись кэша IPFS данных"""
    data: Dict[str, Any]
    cid: str
    timestamp: float
    ttl: int
    language: str

class MultilingualIPFSService:
    """
    Сервис для работы с мультиязычными данными в IPFS
    
    Обеспечивает:
    - Загрузку переводов продуктов и компонентов из IPFS
    - Кэширование для оптимизации производительности
    - Валидацию структуры данных
    - Fallback стратегии при недоступности IPFS
    - Поддержку множественных языков
    """
    
    def __init__(self, ipfs_factory=None, cache_service=None, fallback_service=None):
        """
        Инициализация сервиса IPFS
        
        Args:
            ipfs_factory: Фабрика IPFS сервисов
            cache_service: Сервис кэширования (TranslationCacheService)
            fallback_service: Сервис fallback стратегий (FallbackLocalizationService)
        """
        self.logger = logging.getLogger(__name__)
        self.ipfs_factory = ipfs_factory
        self.cache_service = cache_service
        self.fallback_service = fallback_service
        
        # Локальный кэш IPFS данных
        self.ipfs_cache: Dict[str, IPFSCacheEntry] = {}
        
        # Поддерживаемые языки
        self.supported_languages = ['ru', 'en', 'es', 'fr', 'de', 'it', 'pt', 'zh', 'ja', 'ko', 'ar', 'hi', 'tr', 'pl', 'uk']
        
        # TTL для кэша IPFS данных
        self.cache_ttl = {
            'product': 300,      # 5 минут
            'component': 300,    # 5 минут
            'fallback': 1800     # 30 минут
        }
        
        # Статистика
        self.stats = {
            'ipfs_requests': 0,
            'ipfs_hits': 0,
            'ipfs_misses': 0,
            'cache_hits': 0,
            'fallback_hits': 0,
            'errors': 0
        }
        
        self.logger.info("[MultilingualIPFSService] Инициализирован")
    
    def get_product_translations(self, business_id: str, language: str) -> Optional[Dict[str, Any]]:
        """
        Получает переводы продукта из IPFS
        
        Args:
            business_id: ID продукта
            language: Язык перевода
            
        Returns:
            Dict[str, Any] или None: Переводы продукта
        """
        try:
            self.stats['ipfs_requests'] += 1
            
            # Проверяем кэш
            cache_key = f"product_{business_id}_{language}"
            cached_data = self._get_from_cache(cache_key, 'product')
            if cached_data:
                self.stats['cache_hits'] += 1
                self.logger.debug(f"[MultilingualIPFSService] Кэш hit для продукта {business_id} на языке {language}")
                return cached_data
            
            # Загружаем из IPFS
            product_data = self._load_from_ipfs(business_id, language, 'product')
            if product_data:
                self.stats['ipfs_hits'] += 1
                # Сохраняем в кэш
                self._save_to_cache(cache_key, product_data, 'product')
                self.logger.debug(f"[MultilingualIPFSService] Загружен из IPFS продукт {business_id} на языке {language}")
                return product_data
            
            # Используем fallback
            fallback_data = self._get_fallback_data(business_id, language, 'product')
            if fallback_data:
                self.stats['fallback_hits'] += 1
                self.logger.debug(f"[MultilingualIPFSService] Fallback для продукта {business_id} на языке {language}")
                return fallback_data
            
            self.stats['ipfs_misses'] += 1
            self.logger.warning(f"[MultilingualIPFSService] Не найдены переводы для продукта {business_id} на языке {language}")
            return None
            
        except Exception as e:
            self.stats['errors'] += 1
            self.logger.error(f"[MultilingualIPFSService] Ошибка получения переводов продукта {business_id}: {e}")
            return None
    
    def get_component_translations(self, biounit_id: str, language: str) -> Optional[Dict[str, Any]]:
        """
        Получает переводы компонента из IPFS
        
        Args:
            biounit_id: ID биологической единицы
            language: Язык перевода
            
        Returns:
            Dict[str, Any] или None: Переводы компонента
        """
        try:
            self.stats['ipfs_requests'] += 1
            
            # Проверяем кэш
            cache_key = f"component_{biounit_id}_{language}"
            cached_data = self._get_from_cache(cache_key, 'component')
            if cached_data:
                self.stats['cache_hits'] += 1
                self.logger.debug(f"[MultilingualIPFSService] Кэш hit для компонента {biounit_id} на языке {language}")
                return cached_data
            
            # Загружаем из IPFS
            component_data = self._load_from_ipfs(biounit_id, language, 'component')
            if component_data:
                self.stats['ipfs_hits'] += 1
                # Сохраняем в кэш
                self._save_to_cache(cache_key, component_data, 'component')
                self.logger.debug(f"[MultilingualIPFSService] Загружен из IPFS компонент {biounit_id} на языке {language}")
                return component_data
            
            # Используем fallback
            fallback_data = self._get_fallback_data(biounit_id, language, 'component')
            if fallback_data:
                self.stats['fallback_hits'] += 1
                self.logger.debug(f"[MultilingualIPFSService] Fallback для компонента {biounit_id} на языке {language}")
                return fallback_data
            
            self.stats['ipfs_misses'] += 1
            self.logger.warning(f"[MultilingualIPFSService] Не найдены переводы для компонента {biounit_id} на языке {language}")
            return None
            
        except Exception as e:
            self.stats['errors'] += 1
            self.logger.error(f"[MultilingualIPFSService] Ошибка получения переводов компонента {biounit_id}: {e}")
            return None
    
    def upload_product_translations(self, business_id: str, translations: Dict[str, Dict[str, Any]]) -> Optional[str]:
        """
        Загружает переводы продукта в IPFS
        
        Args:
            business_id: ID продукта
            translations: Словарь переводов {language: {field: value}}
            
        Returns:
            str или None: CID загруженных данных
        """
        try:
            if not self.ipfs_factory:
                self.logger.error("[MultilingualIPFSService] IPFS фабрика не инициализирована")
                return None
            
            # Валидируем данные
            if not self._validate_translations(translations, 'product'):
                return None
            
            # Подготавливаем данные для загрузки
            upload_data = {
                'business_id': business_id,
                'type': 'product',
                'versions': translations,
                'timestamp': datetime.now().isoformat(),
                'version': '1.0'
            }
            
            # Загружаем в IPFS
            ipfs_service = self.ipfs_factory.get_service()
            cid = ipfs_service.upload_json(upload_data)
            
            if cid:
                self.logger.info(f"[MultilingualIPFSService] Загружены переводы продукта {business_id} в IPFS: {cid}")
                return cid
            else:
                self.logger.error(f"[MultilingualIPFSService] Ошибка загрузки переводов продукта {business_id} в IPFS")
                return None
                
        except Exception as e:
            self.stats['errors'] += 1
            self.logger.error(f"[MultilingualIPFSService] Ошибка загрузки переводов продукта {business_id}: {e}")
            return None
    
    def upload_component_translations(self, biounit_id: str, translations: Dict[str, Dict[str, Any]]) -> Optional[str]:
        """
        Загружает переводы компонента в IPFS
        
        Args:
            biounit_id: ID биологической единицы
            translations: Словарь переводов {language: {field: value}}
            
        Returns:
            str или None: CID загруженных данных
        """
        try:
            if not self.ipfs_factory:
                self.logger.error("[MultilingualIPFSService] IPFS фабрика не инициализирована")
                return None
            
            # Валидируем данные
            if not self._validate_translations(translations, 'component'):
                return None
            
            # Подготавливаем данные для загрузки
            upload_data = {
                'biounit_id': biounit_id,
                'type': 'component',
                'versions': translations,
                'timestamp': datetime.now().isoformat(),
                'version': '1.0'
            }
            
            # Загружаем в IPFS
            ipfs_service = self.ipfs_factory.get_service()
            cid = ipfs_service.upload_json(upload_data)
            
            if cid:
                self.logger.info(f"[MultilingualIPFSService] Загружены переводы компонента {biounit_id} в IPFS: {cid}")
                return cid
            else:
                self.logger.error(f"[MultilingualIPFSService] Ошибка загрузки переводов компонента {biounit_id} в IPFS")
                return None
                
        except Exception as e:
            self.stats['errors'] += 1
            self.logger.error(f"[MultilingualIPFSService] Ошибка загрузки переводов компонента {biounit_id}: {e}")
            return None
    
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
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Получает статистику сервиса
        
        Returns:
            Dict[str, Any]: Статистика
        """
        total_requests = self.stats['ipfs_requests']
        if total_requests == 0:
            hit_rate = 0.0
        else:
            hit_rate = (self.stats['ipfs_hits'] / total_requests) * 100
        
        return {
            'ipfs_requests': total_requests,
            'ipfs_hits': self.stats['ipfs_hits'],
            'ipfs_misses': self.stats['ipfs_misses'],
            'cache_hits': self.stats['cache_hits'],
            'fallback_hits': self.stats['fallback_hits'],
            'errors': self.stats['errors'],
            'hit_rate_percent': round(hit_rate, 2),
            'cached_entries': len(self.ipfs_cache),
            'supported_languages': len(self.supported_languages)
        }
    
    def clear_cache(self) -> None:
        """Очищает кэш IPFS данных"""
        self.ipfs_cache.clear()
        self.logger.info("[MultilingualIPFSService] Кэш очищен")
    
    def _get_from_cache(self, cache_key: str, data_type: str) -> Optional[Dict[str, Any]]:
        """
        Получает данные из кэша
        
        Args:
            cache_key: Ключ кэша
            data_type: Тип данных (product, component)
            
        Returns:
            Dict[str, Any] или None: Кэшированные данные
        """
        try:
            # Проверяем локальный кэш
            if cache_key in self.ipfs_cache:
                entry = self.ipfs_cache[cache_key]
                if not self._is_cache_expired(entry):
                    return entry.data
                else:
                    # Удаляем истёкшую запись
                    del self.ipfs_cache[cache_key]
            
            # Проверяем внешний кэш-сервис
            if self.cache_service:
                cached_data = self.cache_service.get(cache_key, 'ipfs')
                if cached_data:
                    return cached_data
            
            return None
            
        except Exception as e:
            self.logger.error(f"[MultilingualIPFSService] Ошибка получения из кэша: {e}")
            return None
    
    def _save_to_cache(self, cache_key: str, data: Dict[str, Any], data_type: str) -> None:
        """
        Сохраняет данные в кэш
        
        Args:
            cache_key: Ключ кэша
            data: Данные для кэширования
            data_type: Тип данных (product, component)
        """
        try:
            # Сохраняем в локальный кэш
            ttl = self.cache_ttl.get(data_type, 300)
            entry = IPFSCacheEntry(
                data=data,
                cid="",  # Будет заполнено при загрузке из IPFS
                timestamp=datetime.now().timestamp(),
                ttl=ttl,
                language=data.get('language', 'unknown')
            )
            self.ipfs_cache[cache_key] = entry
            
            # Сохраняем во внешний кэш-сервис
            if self.cache_service:
                self.cache_service.set(cache_key, data, 'ipfs', ttl)
                
        except Exception as e:
            self.logger.error(f"[MultilingualIPFSService] Ошибка сохранения в кэш: {e}")
    
    def _load_from_ipfs(self, entity_id: str, language: str, entity_type: str) -> Optional[Dict[str, Any]]:
        """
        Загружает данные из IPFS
        
        Args:
            entity_id: ID сущности (product или component)
            language: Язык
            entity_type: Тип сущности (product, component)
            
        Returns:
            Dict[str, Any] или None: Загруженные данные
        """
        try:
            if not self.ipfs_factory:
                return None
            
            # Получаем IPFS сервис
            ipfs_service = self.ipfs_factory.get_service()
            
            # Формируем ключ для поиска в IPFS
            search_key = f"{entity_type}_{entity_id}_{language}"
            
            # Ищем данные в IPFS
            # В реальной реализации здесь будет поиск по CID или другим идентификаторам
            # Пока возвращаем None, так как это заглушка
            self.logger.debug(f"[MultilingualIPFSService] Поиск в IPFS: {search_key}")
            
            # TODO: Реализовать реальную загрузку из IPFS
            return None
            
        except Exception as e:
            self.logger.error(f"[MultilingualIPFSService] Ошибка загрузки из IPFS: {e}")
            return None
    
    def _get_fallback_data(self, entity_id: str, language: str, entity_type: str) -> Optional[Dict[str, Any]]:
        """
        Получает fallback данные
        
        Args:
            entity_id: ID сущности
            language: Язык
            entity_type: Тип сущности
            
        Returns:
            Dict[str, Any] или None: Fallback данные
        """
        try:
            if not self.fallback_service:
                return None
            
            # Используем fallback сервис для получения данных
            # В реальной реализации здесь будет загрузка из локальных файлов
            return None
            
        except Exception as e:
            self.logger.error(f"[MultilingualIPFSService] Ошибка получения fallback данных: {e}")
            return None
    
    def _validate_translations(self, translations: Dict[str, Dict[str, Any]], entity_type: str) -> bool:
        """
        Валидирует структуру переводов
        
        Args:
            translations: Словарь переводов
            entity_type: Тип сущности (product, component)
            
        Returns:
            bool: True если валидны
        """
        try:
            if not isinstance(translations, dict):
                self.logger.error(f"[MultilingualIPFSService] Неверный тип переводов для {entity_type}")
                return False
            
            # Проверяем, что есть хотя бы один язык
            if not translations:
                self.logger.error(f"[MultilingualIPFSService] Пустые переводы для {entity_type}")
                return False
            
            # Проверяем структуру для каждого языка
            for language, data in translations.items():
                if not isinstance(data, dict):
                    self.logger.error(f"[MultilingualIPFSService] Неверная структура данных для языка {language}")
                    return False
                
                # Проверяем обязательные поля в зависимости от типа
                if entity_type == 'product':
                    required_fields = ['title', 'description']
                elif entity_type == 'component':
                    required_fields = ['name', 'description']
                else:
                    required_fields = []
                
                for field in required_fields:
                    if field not in data:
                        self.logger.warning(f"[MultilingualIPFSService] Отсутствует поле {field} для языка {language}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"[MultilingualIPFSService] Ошибка валидации переводов: {e}")
            return False
    
    def _is_cache_expired(self, entry: IPFSCacheEntry) -> bool:
        """
        Проверяет, истёк ли кэш
        
        Args:
            entry: Запись кэша
            
        Returns:
            bool: True если истёк
        """
        try:
            current_time = datetime.now().timestamp()
            return current_time - entry.timestamp > entry.ttl
        except Exception as e:
            self.logger.error(f"[MultilingualIPFSService] Ошибка проверки истечения кэша: {e}")
            return True
