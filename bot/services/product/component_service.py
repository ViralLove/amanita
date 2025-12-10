"""
Сервис для работы с органическими компонентами.

Этот сервис обеспечивает бизнес-логику для взаимодействия с OrganicComponentRegistry
и объединяет данные из блокчейна (on-chain) с метаданными из Arweave (off-chain).

Основные возможности:
- Получение полной информации о компоненте (blockchain + Arweave metadata)
- Кэширование данных компонентов для повышения производительности
- Резолвинг мультиязычных описаний (7 языков)
- Извлечение features, forms, titles компонентов
"""

from typing import Optional, Dict, Any, List, TYPE_CHECKING
import logging
from datetime import datetime, timedelta

# Import services
from services.core.blockchain import BlockchainService
from services.product.storage import ProductStorageService
from services.core.ipfs_factory import IPFSFactory
# Ленивый импорт для избежания циклической зависимости
# from dependencies import get_localization_service

# TYPE_CHECKING для аннотаций типов без циклических зависимостей
if TYPE_CHECKING:
    from model.organic_component import OrganicComponent
    from model.component_description import ComponentDescription

logger = logging.getLogger(__name__)


class ComponentService:
    """
    Бизнес-логический сервис для работы с органическими компонентами.
    
    Ответственности:
    - Оркестрация взаимодействия между BlockchainService и StorageService
    - Объединение on-chain данных (OrganicComponentRegistry) с off-chain метаданными (Arweave)
    - Кэширование часто используемых компонентов (in-memory cache с TTL)
    - Резолвинг мультиязычных описаний из вложенных Arweave CID
    - Предоставление удобного API для ProductAssembler и других потребителей
    
    Архитектура:
        ComponentService
            ↓
        BlockchainService (OrganicComponentRegistry contract calls)
            ↓
        ProductStorageService (Arweave metadata fetching)
            ↓
        Unified component data (cached)
    
    Кэширование:
    - Стратегия: In-memory dict с TTL и LRU eviction
    - TTL: 1 час (компоненты в Arweave неизменяемы)
    - Max size: 100 компонентов
    - Cache key: component_id (business ID)
    
    Пример использования:
        ```python
        service = ComponentService()
        
        # Получить полные данные компонента
        component = service.get_component_full("amanita_muscaria")
        
        # Получить локализованное описание
        description = service.get_component_description("amanita_muscaria", "ru")
        
        # Получить список features
        features = service.get_component_features("amanita_muscaria")
        ```
    """
    
    # Константы кэширования
    CACHE_TTL = 3600  # Time-to-live в секундах (1 час)
    CACHE_MAX_SIZE = 100  # Максимальное количество компонентов в кэше
    
    def __init__(
        self,
        blockchain_service: Optional[BlockchainService] = None,
        storage_service: Optional[ProductStorageService] = None,
        multilingual_ipfs_service: Optional[Any] = None
    ):
        """
        Инициализирует ComponentService с зависимостями.
        
        Args:
            blockchain_service: Сервис для взаимодействия с блокчейном.
                              Если None, создается новый экземпляр BlockchainService.
            storage_service: Сервис для работы с хранилищем (Arweave/IPFS).
                           Если None, создается ProductStorageService с Arweave провайдером.
            multilingual_ipfs_service: Сервис для работы с мультиязычными данными в IPFS.
                                     Если None, создается новый экземпляр MultilingualIPFSService.
        
        Примечания:
        - Dependency injection позволяет передавать mock-объекты для тестирования
        - Если зависимости не переданы, создаются реальные сервисы с default конфигурацией
        - Cache инициализируется как пустой dict при каждом создании экземпляра
        """
        # Инициализация BlockchainService
        if blockchain_service is None:
            self.blockchain_service = BlockchainService()
            logger.info("ComponentService: создан новый BlockchainService")
        else:
            self.blockchain_service = blockchain_service
            logger.info(f"ComponentService: использован переданный BlockchainService ({type(blockchain_service).__name__})")
        
        # Инициализация ProductStorageService
        if storage_service is None:
            # Создаем ProductStorageService с провайдером через IPFSFactory
            # Фабрика вернет нужный провайдер (Arweave/Pinata/Mock) на основе конфига
            storage_provider = IPFSFactory().get_storage()
            self.storage_service = ProductStorageService(storage_provider=storage_provider)
            logger.info("ComponentService: создан ProductStorageService с провайдером из IPFSFactory")
        else:
            self.storage_service = storage_service
            logger.info(f"ComponentService: использован переданный StorageService ({type(storage_service).__name__})")
        
        # Инициализация MultilingualIPFSService (для чтения complex fields из блокчейна)
        if multilingual_ipfs_service is None:
            # Ленивый импорт для избежания циклических зависимостей
            from services.common.multilingual_ipfs_service import MultilingualIPFSService
            from services.common.translation_cache_service import TranslationCacheService
            from services.common.fallback_localization_service import FallbackLocalizationService
            
            ipfs_factory = IPFSFactory()
            cache_service = TranslationCacheService(cache_dir="cache/translations", default_ttl=3600)
            fallback_service = FallbackLocalizationService(default_language='ru')
            
            self.multilingual_ipfs_service = MultilingualIPFSService(
                ipfs_factory=ipfs_factory,
                cache_service=cache_service,
                fallback_service=fallback_service,
                blockchain_service=self.blockchain_service
            )
            logger.info("ComponentService: создан MultilingualIPFSService")
        else:
            self.multilingual_ipfs_service = multilingual_ipfs_service
            logger.info(f"ComponentService: использован переданный MultilingualIPFSService ({type(multilingual_ipfs_service).__name__})")
        
        # Инициализация кэша
        self._cache: Dict[str, Dict[str, Any]] = {}
        logger.info(f"ComponentService: инициализирован кэш (TTL={self.CACHE_TTL}s, MAX_SIZE={self.CACHE_MAX_SIZE})")
        
        logger.info("✅ ComponentService успешно инициализирован")
    
    # ============================================================================
    # CACHE METHODS
    # ============================================================================
    
    def _get_from_cache(self, component_id: str) -> Optional[Any]:
        """
        Получает компонент из кэша, если он еще не устарел.
        
        Args:
            component_id: Business ID компонента
        
        Returns:
            Cached component data or None if not cached or expired
        """
        if component_id not in self._cache:
            return None
        
        cache_entry = self._cache[component_id]
        cached_at = cache_entry.get("cached_at")
        
        # Check TTL
        if datetime.now() - cached_at > timedelta(seconds=self.CACHE_TTL):
            logger.debug(f"Cache expired for '{component_id}' (age: {datetime.now() - cached_at})")
            del self._cache[component_id]
            return None
        
        logger.debug(f"Cache hit for '{component_id}'")
        return cache_entry.get("data")
    
    def _set_cache(self, component_id: str, data: Any) -> None:
        """
        Сохраняет компонент в кэш с TTL.
        
        Args:
            component_id: Business ID компонента
            data: Component data to cache
        """
        # Evict oldest entry if cache is full
        if len(self._cache) >= self.CACHE_MAX_SIZE:
            self._evict_cache()
        
        self._cache[component_id] = {
            "data": data,
            "cached_at": datetime.now()
        }
        logger.debug(f"Cached '{component_id}' (cache size: {len(self._cache)})")
    
    def _evict_cache(self) -> None:
        """
        Удаляет самую старую запись из кэша (LRU eviction).
        """
        if not self._cache:
            return
        
        # Find oldest entry
        oldest_key = min(
            self._cache.keys(),
            key=lambda k: self._cache[k]["cached_at"]
        )
        
        logger.debug(f"Evicting oldest cache entry: '{oldest_key}'")
        del self._cache[oldest_key]
    
    def clear_cache(self) -> None:
        """
        Очищает весь кэш компонентов.
        
        Используется для:
        - Принудительной инвалидации кэша
        - Тестирования
        - Освобождения памяти
        
        Example:
            service.clear_cache()
            # Cache is now empty
        """
        cache_size = len(self._cache)
        self._cache.clear()
        logger.info(f"🧹 Cache cleared ({cache_size} entries removed)")
    
    # ============================================================================
    # PUBLIC API METHODS
    # ============================================================================
    
    def get_component_full(self, component_id: str) -> Optional['OrganicComponent']:
        """
        Get complete component data from registry.
        
        Combines:
        - On-chain data (OrganicComponentRegistry)
        - Off-chain metadata (Arweave)
        - Caches result (1 hour TTL)
        
        Args:
            component_id: Component business ID (e.g., "amanita_muscaria")
        
        Returns:
            OrganicComponent: Registry component (no proportion) or None
        
        Example:
            component = service.get_component_full("amanita_muscaria")
            print(component.scientific_title)  # "Amanita muscaria"
            print(component.forms)  # ["dried"]
            print(component.proportion)  # None (registry component)
        """
        from model.organic_component import OrganicComponent
        
        try:
            # Step 1: Check cache
            cached = self._get_from_cache(component_id)
            if cached:
                logger.info(f"✅ Component '{component_id}' found in cache")
                return cached

            logger.info(f"🔍 Component '{component_id}' not in cache, fetching from blockchain...")

            # ========================================
            # Step 2: Fetch Component struct from chain
            # ========================================
            component_struct = self.blockchain_service.get_component(component_id)
            if not component_struct:
                logger.warning(f"❌ Component '{component_id}' not found in OrganicComponentRegistry")
                return None

            # Normalize contract response
            if isinstance(component_struct, dict):
                logger.warning(
                    "⚠️ Expected tuple from contract, received dict for '%s'. Normalizing for backward compatibility.",
                    component_id,
                )
                component_struct = (
                    component_struct.get("id"),
                    component_struct.get("creator"),
                    component_struct.get("created_at"),
                    component_struct.get("last_updated", component_struct.get("created_at")),
                    component_struct.get("status", 0),
                    component_struct.get("is_shared", True),
                )

            if not isinstance(component_struct, (tuple, list)) or len(component_struct) < 6:
                logger.error(
                    "❌ Unexpected component structure for '%s': %s",
                    component_id,
                    type(component_struct),
                )
                return None

            blockchain_id = component_struct[0]
            creator = component_struct[1]
            created_at = component_struct[2]
            last_updated = component_struct[3]
            status = component_struct[4]
            is_shared = component_struct[5]

            logger.info(
                "✅ Component struct fetched (id=%s, creator=%s, status=%s, shared=%s)",
                blockchain_id,
                (creator[:10] + "...") if isinstance(creator, str) else creator,
                status,
                is_shared,
            )

            # ========================================
            # Step 3: Resolve business_id from mapping
            # ========================================
            business_id_from_chain = None
            if blockchain_id is not None:
                business_id_from_chain = self.blockchain_service.get_component_business_id(blockchain_id)

            if business_id_from_chain:
                if business_id_from_chain != component_id:
                    logger.warning(
                        "⚠️ Business ID mismatch: input='%s', chain='%s'. Using on-chain value.",
                        component_id,
                        business_id_from_chain,
                    )
            else:
                logger.warning(
                    "⚠️ No business_id mapping for component ID %s. Falling back to input '%s'.",
                    blockchain_id,
                    component_id,
                )
                business_id_from_chain = component_id

            # ========================================
            # Step 4: Resolve root metadata CID from mapping
            # ========================================
            root_cid = self.blockchain_service.get_component_root_metadata(component_id)
            if not root_cid:
                logger.error(
                    "⚠️ Component '%s' has no metadata CID. Returning blockchain-only data.",
                    component_id,
                )
                component = OrganicComponent(
                    component_id=business_id_from_chain,
                    blockchain_id=blockchain_id,
                    creator=creator,
                    active=(status == 0),
                    created_at=created_at,
                )
                self._set_cache(component_id, component)
                return component

            clean_cid = root_cid.replace("ar://", "")
            logger.info(f"📥 Fetching metadata from Arweave: {clean_cid}")

            # ========================================
            # Step 5: Fetch metadata from storage
            # ========================================
            try:
                metadata = self.storage_service.download_json(clean_cid)

                if not metadata:
                    logger.error(
                        "❌ Failed to fetch metadata for '%s' from %s. Returning blockchain-only data.",
                        component_id,
                        clean_cid,
                    )
                    component = OrganicComponent(
                        component_id=business_id_from_chain,
                        blockchain_id=blockchain_id,
                        creator=creator,
                        active=(status == 0),
                        created_at=created_at,
                    )
                    self._set_cache(component_id, component)
                    return component

                logger.info(
                    "✅ Metadata fetched for '%s' (%s bytes)",
                    component_id,
                    len(str(metadata)),
                )

            except Exception as e:
                logger.error(
                    "⚠️ Error fetching metadata for '%s': %s. Returning blockchain-only data.",
                    component_id,
                    e,
                )
                component = OrganicComponent(
                    component_id=business_id_from_chain,
                    blockchain_id=blockchain_id,
                    creator=creator,
                    active=(status == 0),
                    created_at=created_at,
                )
                self._set_cache(component_id, component)
                return component

            # ========================================
            # Step 6: Assemble OrganicComponent
            # ========================================
            component = OrganicComponent(
                component_id=business_id_from_chain,
                scientific_title=metadata.get("scientific_title") if isinstance(metadata, dict) else None,
                forms=metadata.get("forms") if isinstance(metadata, dict) else None,
                features=metadata.get("features") if isinstance(metadata, dict) else None,
                localizations=metadata.get("localizations") if isinstance(metadata, dict) else None,
                blockchain_id=blockchain_id,
                creator=creator,
                active=(status == 0),
                created_at=created_at,
            )

            logger.info(f"✅ Component '{component_id}' assembled successfully")

            # ========================================
            # Step 7: Cache result and return
            # ========================================
            self._set_cache(component_id, component)
            return component

        except Exception as e:
            logger.error(f"💥 Critical error in get_component_full('{component_id}'): {e}")
            return None
    
    async def get_component_description(
        self, 
        component_id: str, 
        language: str = "en"
    ) -> Optional['ComponentDescription']:
        """
        Get localized component description via LocalizationService (blockchain path).
        
        Fetches description from blockchain through LocalizationService:
        - LocalizationService → MultilingualIPFSService → AmanitaInternational contract → IPFS
        
        Caching:
        - Cache key: "desc:{component_id}:{language}"
        - TTL: 1 hour (same as component cache)
        - LRU eviction
        
        Args:
            component_id: Component business ID (e.g., "amanita_muscaria")
            language: Language code (e.g., "ru", "en", "es")
                     Defaults to "en"
        
        Returns:
            ComponentDescription: Localized description or None
        
        Example:
            # Get Russian description
            desc = service.get_component_description("amanita_muscaria", "ru")
            print(desc.generic_description)  # "🔬 Активные компоненты: ..."
        """
        from model.component_description import ComponentDescription
        
        try:
            # Step 0: Check cache (Task 8.3)
            cache_key = f"desc:{component_id}:{language}"
            cached_description = self._get_from_cache(cache_key)
            if cached_description:
                logger.debug(f"💨 Description cache hit: {cache_key}")
                return cached_description
            
            # Step 1: Get full component (uses component cache)
            component = self.get_component_full(component_id)
            if not component:
                logger.warning(f"❌ Component '{component_id}' not found")
                return None
            
            logger.info(f"🌍 Fetching description for '{component_id}' in language '{language}'")
            
            # Step 2: Load description via MultilingualIPFSService (blockchain path for complex fields)
            # Используем новый метод _load_component_description_from_ipfs() который формирует
            # className с biounit_id для соответствия scripts слою
            description_data = None
            try:
                # Загружаем ComponentDescription напрямую из блокчейна через MultilingualIPFSService
                # Метод формирует className = "ComponentDescription.{component_id}" для соответствия scripts слою
                description_data = self.multilingual_ipfs_service._load_component_description_from_ipfs(
                    component_id,
                    language
                )
                
                if description_data:
                    logger.info(f"✅ ComponentDescription loaded via MultilingualIPFSService (blockchain path) for '{component_id}' (lang: {language})")
                else:
                    logger.warning(f"⚠️ MultilingualIPFSService не вернул данные для '{component_id}' (lang: {language})")
            except Exception as e:
                logger.error(f"❌ Error using MultilingualIPFSService for '{component_id}' (lang: {language}): {e}")
                description_data = None
            
            # Step 3: No description available
            if not description_data:
                logger.warning(f"❌ No description available for '{component_id}' (lang: {language})")
                return None
            
            # Step 5: Create ComponentDescription from fetched data
            description = ComponentDescription.from_dict(description_data)
            logger.info(f"✅ ComponentDescription created for '{component_id}' ({language})")
            
            # Step 6: Cache description (Task 8.3)
            self._set_cache(cache_key, description)
            logger.debug(f"💾 Description cached: {cache_key}")
            
            # Step 7: Return
            return description
            
        except Exception as e:
            logger.error(f"💥 Critical error in get_component_description('{component_id}', '{language}'): {e}")
            return None
    
    # ============================================================================
    # NESTED CID RESOLUTION (Task 8.1)
    # ============================================================================
    
    async def _fetch_nested_cid_content(
        self,
        root_data: Dict,
        nested_path: List[str]
    ) -> Optional[Dict]:
        """
        Fetch content from nested CID structure.
        
        Navigates through nested dict structure to find CID reference,
        then fetches content from that CID.
        
        Example:
            root_data = {
                "localizations": {
                    "complex_fields": {
                        "ru": {"cid": "ar://xyz123"}
                    }
                }
            }
            nested_path = ["complex_fields", "ru"]
            
            Flow:
            1. Navigate root_data → localizations → complex_fields → ru
            2. Extract CID from result
            3. Fetch CID content from Arweave
            4. Return fetched content
        
        Args:
            root_data: Root dictionary to navigate (e.g., component.localizations)
            nested_path: Path to nested CID (e.g., ["complex_fields", "ru"])
            
        Returns:
            Dict: Content from nested CID, or None if not found
        
        Raises:
            None: Returns None on all errors (graceful degradation)
        """
        try:
            # Navigate nested path
            current = root_data
            for key in nested_path:
                if not isinstance(current, dict) or key not in current:
                    logger.warning(f"⚠️ Nested path broken at key '{key}'. Path: {nested_path}")
                    return None
                current = current[key]
            
            # Current should contain CID reference
            if not isinstance(current, dict) or 'cid' not in current:
                logger.warning(f"⚠️ No 'cid' field in nested data. Keys: {current.keys() if isinstance(current, dict) else type(current)}")
                return None
            
            # Extract and clean CID
            nested_cid = current['cid']
            if not isinstance(nested_cid, str):
                logger.error(f"⚠️ CID is not a string: {type(nested_cid)}")
                return None
            
            clean_cid = nested_cid.replace("ar://", "")
            logger.info(f"📥 Fetching nested CID content: {clean_cid}")
            
            # Fetch nested CID content
            nested_content = self.storage_service.download_json(clean_cid)
            
            if not nested_content:
                logger.error(f"❌ Failed to fetch content from nested CID: {clean_cid}")
                return None
            
            logger.info(f"✅ Nested CID content fetched: {len(str(nested_content))} bytes")
            return nested_content
            
        except Exception as e:
            logger.error(f"💥 Error fetching nested CID content: {e}")
            return None
    
    # ============================================================================
    # HELPER METHODS (Simple field extraction)
    # ============================================================================
    
    def get_component_features(self, component_id: str) -> List[str]:
        """
        Get common features list for component.
        
        Extracts features.common from component registry metadata.
        Leverages get_component_full() cache for performance.
        
        Args:
            component_id: Component business ID (e.g., "amanita_muscaria")
        
        Returns:
            List[str]: List of common features or empty list
        
        Example:
            features = service.get_component_features("amanita_muscaria")
            # ["stress_relief", "vitality_boost"]
        """
        component = self.get_component_full(component_id)
        if component and component.features:
            return component.features.get("common", [])
        return []
    
    def get_component_forms(self, component_id: str) -> List[str]:
        """
        Get available forms list for component.
        
        Extracts forms from component registry metadata.
        Leverages get_component_full() cache for performance.
        
        Args:
            component_id: Component business ID (e.g., "amanita_muscaria")
        
        Returns:
            List[str]: List of available forms or empty list
        
        Example:
            forms = service.get_component_forms("amanita_muscaria")
            # ["dried", "tincture", "powder"]
        """
        component = self.get_component_full(component_id)
        if component and component.forms:
            return component.forms
        return []
    
    def get_component_title(
        self, 
        component_id: str, 
        language: str = "en"
    ) -> Optional[str]:
        """
        Get component title (scientific name).
        
        Returns scientific_title from component registry metadata.
        Future: Could be extended to fetch localized titles from simple_fields.
        Leverages get_component_full() cache for performance.
        
        Args:
            component_id: Component business ID (e.g., "amanita_muscaria")
            language: Language code (currently unused, for future compatibility)
        
        Returns:
            Optional[str]: Scientific title or None
        
        Example:
            title = service.get_component_title("amanita_muscaria")
            # "Amanita muscaria"
        """
        component = self.get_component_full(component_id)
        if component and component.scientific_title:
            return component.scientific_title
        return None

