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
    
    АРХИТЕКТУРА ДАННЫХ:
    - Simple fields (per-component): используются для per-component данных через get_component_translations(biounit_id, language)
      Формат ключа в блокчейне: "component.{biounit_id}.*.{language}"
      Пример: "component.amanita_muscaria.*.ru" → CID с переводами для amanita_muscaria
    
    - Complex fields (глобальные шаблоны): предназначены для глобальных шаблонов через get_component_description_template(language)
      Формат ключа в блокчейне: "{className}.{language}"
      Пример: "ComponentDescription.ru" → CID с глобальным шаблоном (НЕ используется в production)
    """
    
    def __init__(self, ipfs_factory=None, cache_service=None, fallback_service=None, blockchain_service=None):
        """
        Инициализация сервиса IPFS
        
        Args:
            ipfs_factory: Фабрика IPFS сервисов
            cache_service: Сервис кэширования (TranslationCacheService)
            fallback_service: Сервис fallback стратегий (FallbackLocalizationService)
            blockchain_service: Сервис работы с блокчейном (BlockchainService)
        """
        self.logger = logging.getLogger(__name__)
        self.ipfs_factory = ipfs_factory
        self.cache_service = cache_service
        self.fallback_service = fallback_service
        # DI: BlockchainService для доступа к AmanitaInternational контракту
        self.blockchain_service = blockchain_service
        
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
        
        # Complex fields - поля, которые хранятся как полный JSON на класс и язык
        self.COMPLEX_FIELDS = {
            'component': {
                'description', 'generic_description', 'effects', 'shamanic', 'warnings'
            },
            'product': {
                # Будут добавлены позже, если понадобится
            }
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
            
            cache_key = f"product_{business_id}_{language}"
            # Сначала локальный кэш — короткий путь (не трогаем IPFS)
            if cache_key in self.ipfs_cache:
                entry = self.ipfs_cache[cache_key]
                if not self._is_cache_expired(entry) and isinstance(entry.data, dict):
                    self.stats['cache_hits'] += 1
                    self.logger.debug(f"[MultilingualIPFSService] Кэш hit (local) для продукта {business_id} на языке {language}")
                    return entry.data
            
            # Внешний кэш (ipfs-слой) — при успехе сразу возвращаем и восстанавливаем локальный кэш
            cached_data = self._get_from_cache(cache_key, 'product')
            if isinstance(cached_data, dict):
                self.stats['cache_hits'] += 1
                self.logger.debug(f"[MultilingualIPFSService] Кэш hit (external) для продукта {business_id} на языке {language}")
                # восстановим локальный кэш из внешнего и вернём
                self._save_to_local_cache_only(cache_key, cached_data, 'product')
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
    
    def get_component_translations(self, component_id: str, language: str) -> Optional[Dict[str, Any]]:
        """
        Получает переводы компонента из IPFS через simple fields (per-component данные).
        
        ПРИМЕЧАНИЕ: Этот метод использует SIMPLE FIELDS для per-component данных.
        component_id = biounit_id (строка, например "amanita_muscaria").
        Данные загружаются через блокчейн маппинг: simpleFieldCIDs["component.{biounit_id}.*.{language}"]
        
        Для глобальных шаблонов (если понадобятся) используйте get_component_description_template().
        
        Args:
            component_id: ID биологической единицы (biounit_id, строка, например "amanita_muscaria")
            language: Язык перевода (например, "ru")
            
        Returns:
            Dict[str, Any] или None: Переводы компонента (per-component данные через simple fields)
        """
        try:
            self.stats['ipfs_requests'] += 1
            
            cache_key = f"component_{component_id}_{language}"
            # Сначала локальный кэш — короткий путь
            if cache_key in self.ipfs_cache:
                entry = self.ipfs_cache[cache_key]
                if not self._is_cache_expired(entry) and isinstance(entry.data, dict):
                    self.stats['cache_hits'] += 1
                    self.logger.debug(f"[MultilingualIPFSService] Кэш hit (local) для компонента {component_id} на языке {language}")
                    return entry.data
            
            # Внешний кэш — при успехе сразу возвращаем и восстанавливаем локальный кэш
            cached_data = self._get_from_cache(cache_key, 'component')
            if isinstance(cached_data, dict):
                self.stats['cache_hits'] += 1
                self.logger.debug(f"[MultilingualIPFSService] Кэш hit (external) для компонента {component_id} на языке {language}")
                # восстановим локальный кэш из внешнего и вернём
                self._save_to_local_cache_only(cache_key, cached_data, 'component')
                return cached_data
            
            # Загружаем из IPFS
            component_data = self._load_from_ipfs(component_id, language, 'component')
            if component_data:
                self.stats['ipfs_hits'] += 1
                # Сохраняем в кэш
                self._save_to_cache(cache_key, component_data, 'component')
                self.logger.debug(f"[MultilingualIPFSService] Загружен из IPFS компонент {component_id} на языке {language}")
                return component_data
            
            # Используем fallback
            fallback_data = self._get_fallback_data(component_id, language, 'component')
            if fallback_data:
                self.stats['fallback_hits'] += 1
                self.logger.debug(f"[MultilingualIPFSService] Fallback для компонента {component_id} на языке {language}")
                return fallback_data
            
            self.stats['ipfs_misses'] += 1
            self.logger.warning(f"[MultilingualIPFSService] Не найдены переводы для компонента {component_id} на языке {language}")
            return None
            
        except Exception as e:
            self.stats['errors'] += 1
            self.logger.error(f"[MultilingualIPFSService] Ошибка получения переводов компонента {component_id}: {e}")
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
    
    def upload_component_translations(self, component_id: str, translations: Dict[str, Dict[str, Any]]) -> Optional[str]:
        """
        Загружает переводы компонента в IPFS
        
        Args:
            component_id: ID биологической единицы
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
                'component_id': component_id,
                'type': 'component',
                'versions': translations,
                'timestamp': datetime.now().isoformat(),
                'version': '1.0'
            }
            
            # Загружаем в IPFS
            ipfs_service = self.ipfs_factory.get_service()
            cid = ipfs_service.upload_json(upload_data)
            
            if cid:
                self.logger.info(f"[MultilingualIPFSService] Загружены переводы компонента {component_id} в IPFS: {cid}")
                return cid
            else:
                self.logger.error(f"[MultilingualIPFSService] Ошибка загрузки переводов компонента {component_id} в IPFS")
                return None
                
        except Exception as e:
            self.stats['errors'] += 1
            self.logger.error(f"[MultilingualIPFSService] Ошибка загрузки переводов компонента {component_id}: {e}")
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
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Получает статистику сервиса с экспортом всех метрик
        
        Возвращает основные метрики:
        - ipfs_requests: общее количество запросов к IPFS
        - ipfs_hits: успешные загрузки из IPFS
        - ipfs_misses: промахи IPFS (не найдены переводы)
        - cache_hits: попадания в кэш (local + external)
        - fallback_hits: использования fallback стратегий
        - errors: количество ошибок
        
        И производные метрики:
        - hit_rate_percent: процент успешных загрузок из IPFS (ipfs_hits / ipfs_requests * 100)
        - cache_hit_rate_percent: процент попаданий в кэш (cache_hits / ipfs_requests * 100)
        - fallback_rate_percent: процент использования fallback (fallback_hits / ipfs_requests * 100)
        - error_rate_percent: процент ошибок (errors / ipfs_requests * 100)
        
        Дополнительные метрики:
        - cached_entries: количество записей в локальном кэше
        - supported_languages: количество поддерживаемых языков
        
        Returns:
            Dict[str, Any]: Статистика сервиса с основными и производными метриками
        """
        total_requests = self.stats['ipfs_requests']
        
        # Вычисляем производные метрики (защита от деления на ноль)
        if total_requests == 0:
            hit_rate = 0.0
            cache_hit_rate = 0.0
            fallback_rate = 0.0
            error_rate = 0.0
        else:
            hit_rate = (self.stats['ipfs_hits'] / total_requests) * 100
            cache_hit_rate = (self.stats['cache_hits'] / total_requests) * 100
            fallback_rate = (self.stats['fallback_hits'] / total_requests) * 100
            error_rate = (self.stats['errors'] / total_requests) * 100
        
        return {
            # Основные метрики
            'ipfs_requests': total_requests,
            'ipfs_hits': self.stats['ipfs_hits'],
            'ipfs_misses': self.stats['ipfs_misses'],
            'cache_hits': self.stats['cache_hits'],
            'fallback_hits': self.stats['fallback_hits'],
            'errors': self.stats['errors'],
            # Производные метрики
            'hit_rate_percent': round(hit_rate, 2),
            'cache_hit_rate_percent': round(cache_hit_rate, 2),
            'fallback_rate_percent': round(fallback_rate, 2),
            'error_rate_percent': round(error_rate, 2),
            # Дополнительные метрики
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
                    return entry.data if isinstance(entry.data, dict) else None
                else:
                    # Удаляем истёкшую запись
                    del self.ipfs_cache[cache_key]
            
            # Проверяем внешний кэш-сервис
            if self.cache_service:
                cached_data = self.cache_service.get(cache_key, 'ipfs')
                if isinstance(cached_data, dict):
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
            # Валидация данных перед записью
            if not isinstance(data, dict) or not data:
                self.logger.error(f"[MultilingualIPFSService] Попытка записи невалидных данных в кэш: "
                                  f"type={type(data)} key={cache_key}")
                return
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
            self.logger.debug(f"[MultilingualIPFSService] Local cache WRITE: {cache_key}, TTL={ttl}s")
            
            # Сохраняем во внешний кэш-сервис
            if self.cache_service:
                try:
                    self.cache_service.set(cache_key, data, 'ipfs', ttl)
                    self.logger.debug(f"[MultilingualIPFSService] External cache WRITE: {cache_key}, layer=ipfs, TTL={ttl}s")
                except Exception as cache_err:
                    self.logger.error(f"[MultilingualIPFSService] External cache WRITE FAILED: {cache_key}, error={cache_err}")
                    # Не падаем: локальная запись уже есть
            else:
                self.logger.warning("[MultilingualIPFSService] cache_service не инициализирован — пропуск external cache")
                
        except Exception as e:
            self.logger.error(f"[MultilingualIPFSService] Ошибка сохранения в кэш: {e}")
    
    def _save_to_local_cache_only(self, cache_key: str, data: Dict[str, Any], data_type: str) -> None:
        """
        Восстанавливает локальный кэш из внешнего без записи обратно во внешний.
        """
        try:
            ttl = self.cache_ttl.get(data_type, 300)
            entry = IPFSCacheEntry(
                data=data,
                cid=data.get('cid', ''),
                timestamp=datetime.now().timestamp(),
                ttl=ttl,
                language=data.get('language', 'unknown')
            )
            self.ipfs_cache[cache_key] = entry
            self.logger.debug(f"[MultilingualIPFSService] Локальный кэш восстановлен из внешнего: {cache_key}")
        except Exception as e:
            self.logger.error(f"[MultilingualIPFSService] Ошибка восстановления локального кэша: {e}")
    
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
                self.logger.warning("[MultilingualIPFSService] ipfs_factory не инициализирован")
                return None
            ipfs_service = self.ipfs_factory.get_service()
            
            # 1) Получаем CID через blockchain_service напрямую
            cid: Optional[str] = None
            try:
                if self.blockchain_service:
                    contract = self.blockchain_service.get_contract("AmanitaInternational")
                    if contract:
                        cid = contract.functions.getSimpleFieldCID(entity_type, entity_id, "*", language).call()
                        self.logger.debug(f"[MultilingualIPFSService] CID от blockchain_service: {cid} "
                                          f"(entity_type={entity_type}, entity_id={entity_id}, lang={language})")
                    else:
                        self.logger.warning("[MultilingualIPFSService] AmanitaInternational контракт не найден")
                else:
                    self.logger.debug("[MultilingualIPFSService] BlockchainService недоступен — пропуск CID запроса")
            except Exception as e:
                self.logger.error(f"[MultilingualIPFSService] Ошибка получения CID: {e}")
                cid = None

            if not cid:
                self.logger.warning(f"[MultilingualIPFSService] Пустой CID для {entity_type}:{entity_id} lang={language}")
                return None
            
            # 2) Загружаем JSON с IPFS по CID
            payload = ipfs_service.download_json(cid)
            # Строгая валидация результата загрузки
            if payload is None:
                self.logger.warning(f"[MultilingualIPFSService] Пустой IPFS payload для CID={cid}")
                return None
            if not isinstance(payload, dict):
                self.logger.error(f"[MultilingualIPFSService] Некорректный тип IPFS payload (type={type(payload)}), CID={cid}")
                return None
            if not payload:
                self.logger.warning(f"[MultilingualIPFSService] Пустой словарь IPFS payload для CID={cid}")
                return None

            # 3) Валидация структуры по типу (минимальная)
            if entity_type not in ("product", "component"):
                self.logger.warning(f"[MultilingualIPFSService] Неизвестный entity_type={entity_type}")
            # Можно добавить строгую схему при необходимости

            self.logger.info(f"[MultilingualIPFSService] Успешно загружен IPFS JSON для {entity_type}:{entity_id} "
                             f"lang={language} CID={cid}")
            return payload
            
        except Exception as e:
            self.logger.error(f"[MultilingualIPFSService] Ошибка загрузки из IPFS: {e}")
            return None
    
    def _get_complex_field_cid(self, className: str, language: str) -> Optional[str]:
        """
        Получает CID для complex field (глобальный шаблон) через блокчейн контракт.
        
        ПРИМЕЧАНИЕ: Complex fields предназначены для глобальных шаблонов (например, ComponentDescription.ru).
        Per-component данные хранятся как simple fields через get_component_translations(biounit_id, language).
        В production complex fields не используются для per-component данных.
        
        Args:
            className: Имя класса (например, "ComponentDescription")
            language: Язык (например, "ru")
            
        Returns:
            str или None: CID для complex field (глобального шаблона)
        """
        if not self.blockchain_service:
            self.logger.debug("[MultilingualIPFSService] BlockchainService недоступен для complex field")
            return None
        
        try:
            contract = self.blockchain_service.get_contract("AmanitaInternational")
            if not contract:
                self.logger.warning("[MultilingualIPFSService] AmanitaInternational контракт не найден для complex field")
                return None
            
            cid = contract.functions.getComplexFieldCID(className, language).call()
            if not isinstance(cid, str) or not cid:
                self.logger.debug(f"[MultilingualIPFSService] Пустой CID для complex field {className}.{language}")
                return None
            
            self.logger.debug(f"[MultilingualIPFSService] CID для complex field {className}.{language}: {cid}")
            return cid
        except Exception as e:
            self.logger.error(f"[MultilingualIPFSService] Ошибка получения CID для complex field {className}.{language}: {e}")
            return None
    
    def _load_complex_field_from_ipfs(self, className: str, language: str) -> Optional[Dict[str, Any]]:
        """
        Загружает complex field (глобальный шаблон) из IPFS через блокчейн маппинг.
        
        ПРИМЕЧАНИЕ: Complex fields предназначены для глобальных шаблонов (например, ComponentDescription.ru).
        Per-component данные хранятся как simple fields через get_component_translations(biounit_id, language).
        В production complex fields не используются для per-component данных.
        
        Args:
            className: Имя класса (например, "ComponentDescription")
            language: Язык (например, "ru")
            
        Returns:
            Dict[str, Any] или None: JSON с полями complex field (глобального шаблона)
        """
        try:
            if not self.ipfs_factory:
                self.logger.warning("[MultilingualIPFSService] ipfs_factory не инициализирован для complex field")
                return None
            
            cache_key = f"complex_{className}_{language}"
            
            # 1) Проверка кэша (локальный и внешний)
            cached_data = self._get_from_cache(cache_key, 'component')
            if isinstance(cached_data, dict):
                self.stats['cache_hits'] += 1
                self.logger.debug(f"[MultilingualIPFSService] Кэш hit для complex field {className}.{language}")
                # Если данные из внешнего кэша, восстанавливаем локальный
                if cache_key not in self.ipfs_cache:
                    self._save_to_local_cache_only(cache_key, cached_data, 'component')
                return cached_data
            
            # 3) Получение CID через блокчейн
            cid = self._get_complex_field_cid(className, language)
            if not cid:
                self.logger.warning(f"[MultilingualIPFSService] Пустой CID для complex field {className}.{language}")
                return None
            
            # 4) Загрузка JSON из IPFS
            ipfs_service = self.ipfs_factory.get_service()
            payload = ipfs_service.download_json(cid)
            
            if payload is None:
                self.logger.warning(f"[MultilingualIPFSService] Пустой IPFS payload для complex field {className}.{language} CID={cid}")
                return None
            
            if not isinstance(payload, dict):
                self.logger.error(f"[MultilingualIPFSService] Некорректный тип IPFS payload для complex field {className}.{language} (type={type(payload)})")
                return None
            
            # 5) Валидация структуры (label, type, fields)
            if 'label' not in payload:
                self.logger.error(f"[MultilingualIPFSService] Отсутствует поле 'label' в complex field {className}.{language}")
                return None
            
            if 'type' not in payload:
                self.logger.error(f"[MultilingualIPFSService] Отсутствует поле 'type' в complex field {className}.{language}")
                return None
            
            if 'fields' not in payload:
                self.logger.error(f"[MultilingualIPFSService] Отсутствует поле 'fields' в complex field {className}.{language}")
                return None
            
            if not isinstance(payload['fields'], dict):
                self.logger.error(f"[MultilingualIPFSService] Поле 'fields' должно быть словарем в complex field {className}.{language}")
                return None
            
            # 6) Кэширование через TranslationCacheService
            self._save_to_cache(cache_key, payload, 'component')
            
            self.stats['ipfs_hits'] += 1
            self.logger.info(f"[MultilingualIPFSService] Успешно загружен complex field {className}.{language} CID={cid}")
            return payload
            
        except Exception as e:
            self.stats['errors'] += 1
            self.logger.error(f"[MultilingualIPFSService] Ошибка загрузки complex field {className}.{language}: {e}")
            return None
    
    def get_component_description_template(self, language: str) -> Optional[Dict[str, Any]]:
        """
        Получает глобальный шаблон ComponentDescription из IPFS через блокчейн маппинг (complex field).
        
        ПРИМЕЧАНИЕ: Этот метод предназначен для загрузки ГЛОБАЛЬНЫХ ШАБЛОНОВ ComponentDescription.
        Per-component данные НЕ загружаются через этот метод!
        Для per-component данных используйте get_component_translations(biounit_id, language).
        
        В production глобальные шаблоны НЕ используются - каждый компонент имеет свое описание.
        Этот метод зарезервирован для будущего использования, если понадобятся глобальные шаблоны.
        
        Args:
            language: Язык (например, "ru")
            
        Returns:
            Dict[str, Any] или None: JSON с полями ComponentDescription (fields) из глобального шаблона
        """
        try:
            complex_data = self._load_complex_field_from_ipfs("ComponentDescription", language)
            if not complex_data:
                return None
            
            # Возвращаем только fields из complex data
            fields = complex_data.get('fields')
            if not isinstance(fields, dict):
                self.logger.warning(f"[MultilingualIPFSService] Поле 'fields' не является словарем для ComponentDescription.{language}")
                return None
            
            return fields
        except Exception as e:
            self.logger.error(f"[MultilingualIPFSService] Ошибка получения ComponentDescription шаблона для языка {language}: {e}")
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
                self.logger.debug("[MultilingualIPFSService] fallback_service не подключён")
                return None
            
            # Ключ для fallback-логики на верхнем уровне без конкретного поля
            key = f"{entity_type}.{entity_id}"

            # Источники переводов для fallback-решения (минимальные заглушки)
            translation_sources: Dict[str, Any] = {
                language: {},  # попытка языка пользователя
                'ru': {}       # язык по умолчанию
            }

            result = self.fallback_service.get_translation_with_fallback(
                key=key,
                requested_language=language,
                translation_sources=translation_sources,
                default=None
            )

            # Совместимость: если сервис возвращает dataclass FallbackResult, извлекаем translation; иначе — возвращаем как есть
            if isinstance(result, dict):
                self.logger.info(f"[MultilingualIPFSService] Возврат fallback данных (dict) для {key}")
                return result
            translation = getattr(result, "translation", None)
            if isinstance(translation, dict):
                self.logger.info(f"[MultilingualIPFSService] Возврат fallback данных (FallbackResult) для {key}")
                return translation

            self.logger.warning(f"[MultilingualIPFSService] Fallback не вернул dict для {key}")
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
