"""
MultilingualIPFSService.

High-level responsibility:
- resolve CIDs from AmanitaInternational (on-chain mapping)
- download JSON payloads via SSOT `ProductStorageService`
- cache results and apply safe fallbacks

Terminology (SSOT for this repo):
- "AmanitaInternational complex field": `getComplexFieldCID(className, language)` → CID
  - per-component description uses `className="ComponentDescription.<component_id>"`
  - global template (reserved) uses `className="ComponentDescription"`
  - NOTE: `language` is a separate argument, not a suffix in `className`
- The stored JSON for ComponentDescription is commonly a *plain dict* of fields
  (see `data/components/.../complex_fields/*.json`). We normalize it to a wrapper
  `{label,type,fields}` internally to keep caching and downstream logic uniform.
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
    Multilingual IPFS/Arweave integration service.

    What it does:
    - Loads product/component translations (JSON) by resolving CIDs from the AmanitaInternational contract.
    - Uses SSOT storage layer (`ProductStorageService`) for I/O (sync/async/hybrid + CID validation).
    - Caches payloads and supports graceful fallback.

    AmanitaInternational mapping (important):
    - Simple fields: `getSimpleFieldCID(fieldKey)` → CID
    - Complex fields: `getComplexFieldCID(className, language)` → CID
      - per-component ComponentDescription: `className="ComponentDescription.<component_id>"`
      - global template (reserved): `className="ComponentDescription"`

    Payload formats for ComponentDescription:
    - Plain dict (real data): `{"generic_description": "...", "effects": "...", ...}`
    - Wrapper (some tests/mocks): `{"label": "...", "type": "...", "fields": {...}}`
    Internally we normalize plain dict → wrapper to keep downstream logic consistent.
    """
    
    def __init__(
        self,
        cache_service=None,
        fallback_service=None,
        blockchain_service=None,
        storage_service=None,
    ):
        """
        Инициализация сервиса IPFS
        
        Args:
            cache_service: Сервис кэширования (TranslationCacheService)
            fallback_service: Сервис fallback стратегий (FallbackLocalizationService)
            blockchain_service: Сервис работы с блокчейном (BlockchainService)
            storage_service: SSOT слой I/O по CID (ProductStorageService совместимый интерфейс)
        """
        self.logger = logging.getLogger(__name__)
        self.cache_service = cache_service
        self.fallback_service = fallback_service
        # DI: BlockchainService для доступа к AmanitaInternational контракту
        self.blockchain_service = blockchain_service

        # SSOT: storage_service отвечает за download_json(cid) (sync/async/hybrid + CID validation)
        # NOTE: storage_provider может быть как реальный провайдер (ArWeaveUploader),
        # так и тестовый InMemoryIPFSService (у него есть download_json/upload_json).
        self.storage_service = storage_service
        if self.storage_service is None:
            try:
                from services.product.storage import ProductStorageService
                # Важно: MultilingualIPFSService больше не должен сам обращаться к IPFSFactory.
                # Если storage_service не прокинут через DI, создаём дефолтный ProductStorageService,
                # который уже сам использует SSOT-проводку к провайдеру.
                self.storage_service = ProductStorageService()
            except Exception as e:
                # Fail-safe: не ломаем создание сервиса, но дальнейшая загрузка из IPFS будет невозможна.
                self.logger.error(f"[MultilingualIPFSService] storage_service init failed: {e}")
                self.storage_service = None
        
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
        
        # Conceptual classification of complex fields (component descriptions / templates).
        # Actual contract mapping is resolved via getComplexFieldCID(className, language).
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
        Получает переводы компонента из IPFS через complex fields (per-component данные).
        
        ПРИМЕЧАНИЕ: Этот метод использует COMPLEX FIELDS для per-component данных.
        component_id = biounit_id (строка, например "amanita_muscaria").
        Данные загружаются через блокчейн маппинг: complexFieldCIDs["ComponentDescription.{biounit_id}.{language}"]
        
        Формат соответствует scripts слою, который записывает данные с className = "ComponentDescription.{biounit_id}".
        
        Для глобальных шаблонов (если понадобятся) используйте get_component_description_template().
        
        Args:
            component_id: ID биологической единицы (biounit_id, строка, например "amanita_muscaria")
            language: Язык перевода (например, "ru")
            
        Returns:
            Dict[str, Any] или None: Переводы компонента (fields из ComponentDescription complex field)
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
            
            # Загружаем из IPFS через complex fields (соответствует scripts слою)
            # Используем _load_component_description_from_ipfs() который формирует
            # className = "ComponentDescription.{component_id}" для соответствия scripts слою
            component_data = self._load_component_description_from_ipfs(component_id, language)
            if component_data:
                self.stats['ipfs_hits'] += 1
                # Сохраняем в кэш
                self._save_to_cache(cache_key, component_data, 'component')
                self.logger.debug(f"[MultilingualIPFSService] Загружен из IPFS компонент {component_id} на языке {language} через complex fields")
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
            if not self.storage_service:
                self.logger.error("[MultilingualIPFSService] storage_service не инициализирован")
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
            
            # Загружаем JSON через SSOT storage_service (а не через ipfs_factory)
            cid = self.storage_service.upload_json(upload_data)
            
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
            if not self.storage_service:
                self.logger.error("[MultilingualIPFSService] storage_service не инициализирован")
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
            
            # Загружаем JSON через SSOT storage_service (а не через ipfs_factory)
            cid = self.storage_service.upload_json(upload_data)
            
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

    def _build_simple_field_key(self, entity_type: str, entity_id: str, field: str) -> Optional[str]:
        """
        SSOT helper: builds AmanitaInternational Simple Field key (fieldKey) used by scripts + on-chain ABI.

        Important:
        - language must NOT be part of fieldKey (Solidity ABI: getSimpleFieldCID(string fieldKey)).
        - This helper must follow the scripts-layer contract:
          - product title: "ProductName.<productId>" (see `scripts/lib/product_upload_steps.js`)
          - component title: "ComponentDescription.title" (see `scripts/lib/upload_steps.js`)
          - dosage types: "DosageInstruction.description" (see `scripts/lib/upload_steps.js`)
        """
        try:
            entity_type_norm = (entity_type or "").strip().lower()
            field_norm = (field or "").strip().lower()
            entity_id_norm = (entity_id or "").strip()

            if not entity_type_norm or not field_norm:
                return None

            # Product-level simple fields
            if entity_type_norm == "product":
                # MVP scope: product title only (drives WooCommerce Name + UI title).
                if field_norm in ("title", "name"):
                    if not entity_id_norm:
                        return None
                    return f"ProductName.{entity_id_norm}"
                return None

            # Component/global simple fields (not per-component; scripts store them as global keys)
            if entity_type_norm == "component":
                if field_norm in ("title",):
                    return "ComponentDescription.title"
                if field_norm in ("dosage_types", "dosage", "dosage_type", "dosage_instructions"):
                    return "DosageInstruction.description"
                return None

            return None
        except Exception:
            # Fail-safe: never raise from builder; caller will handle None.
            return None
    
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
            if not self.storage_service:
                self.logger.warning("[MultilingualIPFSService] storage_service не инициализирован")
                return None
            
            # 1) Получаем CID через blockchain_service напрямую (Simple Field ABI: getSimpleFieldCID(fieldKey))
            cid: Optional[str] = None
            try:
                if self.blockchain_service:
                    contract = self.blockchain_service.get_contract("AmanitaInternational")
                    if contract:
                        # MVP: For product translations we currently resolve only product title.
                        # SSOT fieldKey is built from entity_type/entity_id/field (language is NOT part of fieldKey).
                        field_for_key = "title" if (entity_type or "").strip().lower() == "product" else "*"
                        field_key = self._build_simple_field_key(entity_type, entity_id, field_for_key)
                        if not field_key:
                            self.logger.warning(
                                f"[MultilingualIPFSService] Не удалось построить fieldKey для simple field "
                                f"(entity_type={entity_type}, entity_id={entity_id}, field={field_for_key})"
                            )
                            return None

                        cid = contract.functions.getSimpleFieldCID(field_key).call()
                        self.logger.debug(
                            f"[MultilingualIPFSService] CID от blockchain_service: {cid} "
                            f"(fieldKey={field_key}, lang={language})"
                        )
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
            
            # 2) Загружаем JSON с IPFS/Arweave по CID
            payload = self.storage_service.download_json(cid)
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

            # 2.1) Normalize product-title payload into ProductLocalizationService-friendly dict
            # SSOT (scripts): product title payload is a language map like {"ru": "...", "en": "..."} stored under a single CID.
            entity_type_norm = (entity_type or "").strip().lower()
            if entity_type_norm == "product":
                title_value = payload.get(language)
                if not isinstance(title_value, str) or not title_value.strip():
                    # Graceful: do not raise; let fallback chain handle it.
                    self.logger.warning(
                        f"[MultilingualIPFSService] Некорректный формат title payload для продукта {entity_id}: "
                        f"ожидался dict(lang->str), lang={language}, keys={list(payload.keys())}"
                    )
                    return None
                return {"title": title_value.strip()}

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
        Получает CID для complex field через блокчейн контракт.
        
        ПРИМЕЧАНИЕ: Complex fields используются для:
        - Per-component данных: className = "ComponentDescription.{biounit_id}" (используется в production)
        - Глобальных шаблонов: className = "ComponentDescription" (НЕ используется в production)
        
        Args:
            className: Имя класса (например, "ComponentDescription" или "ComponentDescription.amanita_muscaria")
            language: Язык (например, "ru")
            
        Returns:
            str или None: CID для complex field
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
        Загружает complex field из IPFS через блокчейн маппинг.
        
        ПРИМЕЧАНИЕ: Complex fields используются для:
        - Per-component данных: className = "ComponentDescription.{biounit_id}" (используется в production)
        - Глобальных шаблонов: className = "ComponentDescription" (НЕ используется в production)
        
        Args:
            className: Имя класса (например, "ComponentDescription" или "ComponentDescription.amanita_muscaria")
            language: Язык (например, "ru")
            
        Returns:
            Dict[str, Any] или None: JSON с полями complex field (структура: {label, type, fields})
        """
        try:
            if not self.storage_service:
                self.logger.warning("[MultilingualIPFSService] storage_service не инициализирован для complex field")
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
            payload = self.storage_service.download_json(cid)
            
            if payload is None:
                self.logger.warning(f"[MultilingualIPFSService] Пустой IPFS payload для complex field {className}.{language} CID={cid}")
                return None
            
            if not isinstance(payload, dict):
                self.logger.error(f"[MultilingualIPFSService] Некорректный тип IPFS payload для complex field {className}.{language} (type={type(payload)})")
                return None

            # 5) Нормализация формата payload (SSOT-факт: реальные ComponentDescription данные часто плоские)
            #
            # Поддерживаем 2 формата:
            # 1) Wrapper: {"label": "...", "type": "...", "fields": {...}}
            # 2) Plain dict (legacy/real data): {"generic_description": "...", "effects": "...", ...}
            #
            # Внутренний SSOT-контракт: ниже по цепочке мы работаем с wrapper (чтобы кэш/вызовы были единообразны).
            if 'fields' not in payload:
                # Heuristic: treat as ComponentDescription fields if it looks like a description dict.
                looks_like_description_fields = any(
                    key in payload for key in ("generic_description", "effects", "shamanic", "warnings", "title")
                )
                if looks_like_description_fields:
                    payload = {
                        "label": "ComponentDescription",
                        "type": "ComponentDescription",
                        "fields": payload,
                    }
                    self.logger.info(
                        f"[MultilingualIPFSService] Нормализован плоский payload в wrapper для complex field "
                        f"{className}.{language} CID={cid}"
                    )
                else:
                    self.logger.error(
                        f"[MultilingualIPFSService] Отсутствует поле 'fields' и payload не похож на ComponentDescription "
                        f"для complex field {className}.{language}"
                    )
                    return None

            # 6) Валидация структуры wrapper (label, type, fields)
            if 'label' not in payload:
                self.logger.error(f"[MultilingualIPFSService] Отсутствует поле 'label' в complex field {className}.{language}")
                return None
            
            if 'type' not in payload:
                self.logger.error(f"[MultilingualIPFSService] Отсутствует поле 'type' в complex field {className}.{language}")
                return None
            
            if not isinstance(payload.get('fields'), dict):
                self.logger.error(f"[MultilingualIPFSService] Поле 'fields' должно быть словарем в complex field {className}.{language}")
                return None
            
            # 7) Кэширование через TranslationCacheService
            self._save_to_cache(cache_key, payload, 'component')
            
            self.stats['ipfs_hits'] += 1
            self.logger.info(f"[MultilingualIPFSService] Успешно загружен complex field {className}.{language} CID={cid}")
            return payload
            
        except Exception as e:
            self.stats['errors'] += 1
            self.logger.error(f"[MultilingualIPFSService] Ошибка загрузки complex field {className}.{language}: {e}")
            return None
    
    def _load_component_description_from_ipfs(self, component_id: str, language: str) -> Optional[Dict[str, Any]]:
        """
        Загружает ComponentDescription для конкретного компонента из IPFS через блокчейн маппинг (complex field).
        
        Использует формат className с biounit_id для соответствия scripts слою:
        - Scripts записывает: "ComponentDescription.{biounit_id}.{lang}"
        - Этот метод читает: "ComponentDescription.{component_id}.{lang}"
        
        Args:
            component_id: ID биологической единицы (biounit_id, например "amanita_muscaria")
            language: Язык (например, "ru")
            
        Returns:
            Dict[str, Any] или None: JSON с полями ComponentDescription (fields) для компонента
        """
        try:
            # Формируем className с biounit_id (соответствует scripts слою)
            className = f"ComponentDescription.{component_id}"
            
            # Проверяем кэш с правильным ключом (включает component_id)
            cache_key = f"complex_{className}_{language}"
            cached_data = self._get_from_cache(cache_key, 'component')
            if isinstance(cached_data, dict):
                # Если данные в кэше, извлекаем fields
                fields = cached_data.get('fields')
                if isinstance(fields, dict):
                    self.stats['cache_hits'] += 1
                    self.logger.debug(f"[MultilingualIPFSService] Кэш hit для ComponentDescription {component_id} (lang: {language})")
                    return fields
            
            # Загружаем complex field через существующий метод
            complex_data = self._load_complex_field_from_ipfs(className, language)
            if not complex_data:
                self.logger.warning(f"[MultilingualIPFSService] Не удалось загрузить ComponentDescription для {component_id} (lang: {language})")
                return None
            
            # Возвращаем только fields из complex data
            fields = complex_data.get('fields')
            if not isinstance(fields, dict):
                self.logger.warning(f"[MultilingualIPFSService] Поле 'fields' не является словарем для ComponentDescription.{component_id}.{language}")
                return None
            
            self.logger.info(f"[MultilingualIPFSService] Успешно загружен ComponentDescription для {component_id} (lang: {language})")
            return fields
        except Exception as e:
            self.logger.error(f"[MultilingualIPFSService] Ошибка получения ComponentDescription для {component_id} (lang: {language}): {e}")
            return None
    
    def get_component_description_template(self, language: str) -> Optional[Dict[str, Any]]:
        """
        Получает глобальный шаблон ComponentDescription из IPFS через блокчейн маппинг (complex field).
        
        ПРИМЕЧАНИЕ: Этот метод предназначен для загрузки ГЛОБАЛЬНЫХ ШАБЛОНОВ ComponentDescription.
        Per-component данные НЕ загружаются через этот метод!
        Для per-component данных используйте _load_component_description_from_ipfs(component_id, language).
        
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
