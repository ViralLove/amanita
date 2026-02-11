# Activity Services Architecture

**Версия**: 1.0  
**Дата создания**: 2026-01-27  
**Статус**: Архитектурный документ для реализации  
**Связанные документы**: 
- `docs/analysis/epics/epic-activities-api-production.md` - Epic с roadmap
- `docs/tech/activity-vertical-layers-analysis.md` - Вертикальная архитектура данных
- `docs/tech/activity-vertical-architecture-integration.md` - Интеграция архитектуры

---

## Обзор

Activity Services Architecture описывает структуру сервисов для работы с Activity в системе AMANITA. Архитектура следует паттернам Product Services, обеспечивая консистентность и переиспользование проверенных решений.

### Принципы архитектуры

1. **Разделение ответственности**: каждый сервис отвечает за одну область
2. **Dependency Injection**: зависимости передаются через конструктор
3. **Синглтон для BlockchainService**: переиспользование подключения к Web3
4. **Codec паттерн**: декодирование tuple результатов из контрактов
5. **Assembler паттерн**: сборка полного объекта из разных источников
6. **Cache паттерн**: кэширование для производительности
7. **Validation паттерн**: отдельный сервис для валидации

---

## Архитектурная диаграмма

```
┌─────────────────────────────────────────────────────────────┐
│                    API Layer (FastAPI)                      │
│  POST /activities/draft, PUT /activities/{id}, etc.         │
└────────────────────┬──────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│              ActivityApiService (Application)              │
│  Тонкий слой для API endpoints                             │
└────────────────────┬──────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│         ActivityRegistryService (Orchestration)             │
│  Координация всех операций с Activity                      │
└─────┬───────────┬───────────┬───────────┬─────────────────┘
      │           │           │           │
      ▼           ▼           ▼           ▼
┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐
│Storage   │ │Validation│ │Assembler │ │Search    │
│Service   │ │Service   │ │          │ │Service   │
└────┬─────┘ └──────────┘ └────┬─────┘ └────┬─────┘
     │                          │            │
     ▼                          ▼            ▼
┌──────────┐            ┌──────────┐  ┌──────────┐
│Arweave   │            │Blockchain│  │Supabase  │
│/IPFS     │            │(Ethereum)│  │(Search)  │
└──────────┘            └──────────┘  └──────────┘
```

---

## Сервисы и их зависимости

### 1. ActivityRegistryService (Orchestration Layer)

**Назначение**: Главный сервис-оркестратор для всех операций с Activity. Координирует взаимодействие между блокчейном, Arweave и Supabase.

**Зависимости**:
- `BlockchainService` (синглтон) - работа с блокчейном
- `ActivityStorageService` - работа с Arweave/IPFS
- `ActivityValidationService` - валидация данных
- `ActivityAssembler` - сборка полного Activity
- `ActivitySearchService` - индексация и поиск
- `ActivityCacheService` (синглтон) - кэширование
- `ActivityMetadataService` - работа с метаданными

**Основные методы**:
- `create_draft()` - создание Draft Activity
- `update_draft()` - обновление Draft Activity
- `submit_review()` - отправка на review (Draft → SentToReview)
- `publish()` - публикация (Approved → Published)
- `unpublish()` - снятие с публикации (Published → Draft)
- `get_activity()` - получение Activity по ID
- `list_activities()` - список Activity с фильтрами
- `search_activities()` - поиск Activity через SearchService

**Пример реализации** (на основе ProductRegistryService):

```python
class ActivityRegistryService:
    """
    Сервис для работы с реестром Activity.
    Координирует работу всех подсервисов и обеспечивает единый интерфейс.
    """
    
    def __init__(
        self,
        blockchain_service: Optional[BlockchainService] = None,
        storage_service: Optional[ActivityStorageService] = None,
        validation_service: Optional[ActivityValidationService] = None,
        assembler: Optional[ActivityAssembler] = None,
        search_service: Optional[ActivitySearchService] = None,
        cache_service: Optional[ActivityCacheService] = None,
        metadata_service: Optional[ActivityMetadataService] = None
    ):
        self.logger = logging.getLogger(__name__)
        
        # Используем синглтон BlockchainService если не передан
        self.blockchain_service = blockchain_service or BlockchainService()
        self.validation_service = validation_service or ActivityValidationService()
        self.storage_service = storage_service or ActivityStorageService()
        
        # Инициализируем кэш (синглтон)
        self.cache_service = cache_service or ActivityCacheService()
        
        # Инициализируем сервис метаданных
        self.metadata_service = metadata_service or ActivityMetadataService(self.storage_service)
        
        # Инициализируем Assembler
        if assembler is None:
            self.assembler = ActivityAssembler(
                storage_service=self.storage_service,
                metadata_service=self.metadata_service
            )
        else:
            self.assembler = assembler
        
        # Инициализируем SearchService
        if search_service is None:
            # Создаем зависимости для SearchService
            fragment_service = ActivityFragmentService()
            embedding_service = ActivityEmbeddingService()
            self.search_service = ActivitySearchService(
                fragment_service=fragment_service,
                embedding_service=embedding_service
            )
        else:
            self.search_service = search_service
    
    async def create_draft(
        self, 
        activity_data: Dict[str, Any], 
        creator_address: str
    ) -> Dict[str, Any]:
        """
        Создает Draft Activity: валидация → метаданные → Arweave → блокчейн → индексация.
        
        Args:
            activity_data: Данные Activity
            creator_address: Ethereum адрес создателя
            
        Returns:
            dict: Результат операции с полями activity_id, blockchain_id, metadata_cid, tx_hash, status, error
        """
        try:
            self.logger.info(f"🆕 Начинаем создание Draft Activity")
            
            # 1. Валидация данных
            validation_result = await self.validation_service.validate_activity_data(activity_data)
            if not validation_result.is_valid:
                self.logger.error(f"❌ Валидация не прошла: {validation_result.error_message}")
                return {
                    "status": "error",
                    "error": validation_result.error_message or "Validation failed"
                }
            
            # 2. Устанавливаем статус Draft если не указан
            if "status" not in activity_data or activity_data["status"] != "Draft":
                activity_data["status"] = "Draft"
            
            # 3. Загрузка метаданных в Arweave
            metadata_cid = await self.storage_service.upload_metadata(activity_data)
            if not metadata_cid:
                return {
                    "status": "error",
                    "error": "Ошибка загрузки метаданных в Arweave"
                }
            
            # 4. Определяем activity_type (из данных или по умолчанию)
            activity_type = activity_data.get("activity_type", "event")
            activity_type_enum = ActivityType.Event if activity_type == "event" else ActivityType.Service
            
            # 5. Создание Activity в блокчейне
            tx_hash = await self.blockchain_service.create_activity(
                activity_type_enum,
                metadata_cid
            )
            if not tx_hash:
                return {
                    "status": "error",
                    "error": "Ошибка записи в блокчейн"
                }
            
            # 6. Получение activity_id из транзакции
            activity_id = await self.blockchain_service.get_activity_id_from_tx(tx_hash)
            
            # 7. Индексация в Supabase (асинхронно, не блокируем основной flow)
            try:
                await self.search_service.index_activity(str(activity_id), metadata_cid)
            except Exception as e:
                self.logger.warning(f"⚠️ Ошибка индексации (не критично): {e}")
            
            self.logger.info(f"✅ Draft Activity создан: activity_id={activity_id}")
            return {
                "activity_id": str(activity_id),
                "blockchain_id": activity_id,
                "metadata_cid": metadata_cid,
                "tx_hash": str(tx_hash),
                "status": "success",
                "error": None
            }
        except Exception as e:
            self.logger.error(f"❌ Критическая ошибка при создании Activity: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
            return {
                "status": "error",
                "error": str(e)
            }
    
    async def get_activity(
        self, 
        activity_id: str, 
        language: str = "ru"
    ) -> Optional[Activity]:
        """
        Получает Activity по ID с использованием кэша.
        
        Args:
            activity_id: ID Activity
            language: Язык для локализации (по умолчанию "ru")
            
        Returns:
            Optional[Activity]: Activity объект или None если не найдено
        """
        # Проверяем кэш
        cached_activity = self.cache_service.get_cached_activity(activity_id)
        if cached_activity:
            self.logger.debug(f"✅ Activity {activity_id} найдено в кэше")
            return cached_activity
        
        try:
            # Получаем данные из блокчейна
            blockchain_data = await self.blockchain_service.get_activity(activity_id)
            if not blockchain_data:
                return None
            
            # Загружаем метаданные из Arweave
            metadata_cid = blockchain_data.metadata_cid
            metadata = await self.storage_service.download_metadata(metadata_cid)
            if not metadata:
                self.logger.warning(f"⚠️ Метаданные не найдены для CID: {metadata_cid}")
                return None
            
            # Собираем полный Activity
            activity = await self.assembler.assemble_activity(blockchain_data, metadata)
            
            # Сохраняем в кэш
            if activity:
                self.cache_service.set_cached_activity(activity_id, activity)
            
            return activity
        except Exception as e:
            self.logger.error(f"❌ Ошибка при получении Activity {activity_id}: {e}")
            return None
```

---

### 2. ActivityCacheService (Cache Layer)

**Назначение**: Кэширование Activity для производительности. Синглтон, аналогичен ProductCacheService.

**Зависимости**: 
- `ActivityStorageService` (lazy loading) - для валидации CID

**Основные методы**:
- `get_cached_activity()` - получение Activity из кэша
- `set_cached_activity()` - сохранение Activity в кэш
- `get_cached_metadata()` - получение метаданных из кэша
- `set_cached_metadata()` - сохранение метаданных в кэш
- `invalidate_activity()` - инвалидация Activity из кэша
- `invalidate_cache()` - очистка кэша

**Пример реализации** (на основе ProductCacheService):

```python
class ActivityCacheService:
    """Единый сервис кэширования для Activity с интеграцией Arweave хранилища"""
    
    # Время жизни кэша для разных типов данных
    CACHE_TTL = {
        'activity': timedelta(hours=1),
        'metadata': timedelta(hours=24)
    }
    
    _instance = None
    
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        if not hasattr(self, 'activity_cache'):
            self.activity_cache: Dict[str, Tuple[Activity, datetime]] = {}
        if not hasattr(self, 'metadata_cache'):
            self.metadata_cache: Dict[str, Tuple[Dict, datetime]] = {}
        
        self._storage_service = None  # Lazy loading
    
    @property
    def storage_service(self):
        """Lazy loading storage service для избежания циркулярных зависимостей"""
        if self._storage_service is None:
            from services.activity.storage import ActivityStorageService
            self._storage_service = ActivityStorageService()
        return self._storage_service
    
    def get_cached_activity(self, activity_id: str) -> Optional[Activity]:
        """
        Получает Activity из кэша.
        
        Args:
            activity_id: ID Activity
            
        Returns:
            Optional[Activity]: Activity из кэша или None
        """
        if activity_id not in self.activity_cache:
            return None
        
        activity, timestamp = self.activity_cache[activity_id]
        
        if self._is_cache_valid(timestamp, 'activity'):
            self.logger.debug(f"✅ Activity {activity_id} найдено в валидном кэше")
            return activity
        else:
            # Кэш устарел, удаляем
            del self.activity_cache[activity_id]
            return None
    
    def set_cached_activity(self, activity_id: str, activity: Activity) -> bool:
        """
        Сохраняет Activity в кэш.
        
        Args:
            activity_id: ID Activity
            activity: Activity объект
            
        Returns:
            bool: True если успешно сохранено
        """
        self.activity_cache[activity_id] = (activity, datetime.utcnow())
        self.logger.debug(f"✅ Activity {activity_id} сохранено в кэш")
        return True
    
    def invalidate_activity(self, activity_id: str) -> None:
        """
        Инвалидирует Activity из кэша.
        
        Args:
            activity_id: ID Activity
        """
        if activity_id in self.activity_cache:
            del self.activity_cache[activity_id]
            self.logger.info(f"🗑️ Activity {activity_id} удалено из кэша")
    
    def _is_cache_valid(self, timestamp: datetime, cache_type: str) -> bool:
        """Проверяет актуальность кэша на основе TTL"""
        ttl = self.CACHE_TTL.get(cache_type)
        if not ttl:
            return False
        
        age = datetime.utcnow() - timestamp
        return age < ttl
```

---

### 3. ActivityApiService (Application Layer)

**Назначение**: Тонкий слой для API endpoints. Координирует между routes и RegistryService.

**Зависимости**:
- `ActivityRegistryService` - для всех операций с Activity

**Основные методы**:
- `create_draft()` - создание Draft через RegistryService
- `update_draft()` - обновление Draft через RegistryService
- `submit_review()` - отправка на review через RegistryService
- `publish()` - публикация через RegistryService
- `unpublish()` - снятие с публикации через RegistryService
- `get_activity()` - получение Activity через RegistryService
- `list_my_activities()` - список Activity через RegistryService
- `search_activities()` - поиск через RegistryService

**Пример реализации**:

```python
class ActivityApiService:
    """
    Тонкий слой для API endpoints Activity.
    Координирует между routes и RegistryService.
    """
    
    def __init__(self, registry_service: ActivityRegistryService):
        self.registry_service = registry_service
        self.logger = logging.getLogger(__name__)
    
    async def create_draft(
        self,
        activity_data: Dict[str, Any],
        creator_address: str
    ) -> Dict[str, Any]:
        """
        Создает Draft Activity через RegistryService.
        
        Args:
            activity_data: Данные Activity из API request
            creator_address: Ethereum адрес создателя (из authentication)
            
        Returns:
            dict: Результат операции для API response
        """
        result = await self.registry_service.create_draft(activity_data, creator_address)
        
        # Трансформируем результат для API response
        if result.get("status") == "success":
            return {
                "activity_id": result["activity_id"],
                "blockchain_id": result["blockchain_id"],
                "metadata_cid": result["metadata_cid"],
                "tx_hash": result["tx_hash"],
                "status": "success"
            }
        else:
            # Обрабатываем ошибки для API response
            error = result.get("error", "Unknown error")
            if "Validation failed" in error:
                raise ValidationError(error)
            elif "Insufficient permissions" in error:
                raise AuthorizationError(error)
            else:
                raise InternalServerError(error)
    
    async def get_activity(
        self,
        activity_id: str,
        language: str = "ru"
    ) -> Optional[Dict[str, Any]]:
        """
        Получает Activity через RegistryService и трансформирует в dict для API.
        
        Args:
            activity_id: ID Activity
            language: Язык для локализации
            
        Returns:
            Optional[Dict[str, Any]]: Activity в формате для API response или None
        """
        activity = await self.registry_service.get_activity(activity_id, language)
        
        if not activity:
            return None
        
        # Трансформируем Activity dataclass в dict для API response
        return self._transform_activity_to_dict(activity)
    
    def _transform_activity_to_dict(self, activity: Activity) -> Dict[str, Any]:
        """
        Трансформирует Activity dataclass в dict для API response.
        
        Args:
            activity: Activity объект
            
        Returns:
            dict: Activity в формате для API response
        """
        result = {
            "activity_id": activity.activity_id,
            "activity_type": activity.activity_type,
            "status": activity.status,
            "title": activity.title,
            "short_summary": activity.short_summary,
            "full_description": activity.full_description,
            # ... все остальные поля из Activity Data Model
        }
        
        # Обрабатываем условные поля (event_* vs service_*)
        if activity.activity_type == "event":
            result["event_timing"] = activity.event_timing
            result["event_capacity"] = activity.event_capacity
            result["event_pricing"] = activity.event_pricing
            result["event_cta"] = activity.event_cta
        elif activity.activity_type == "service":
            result["service_timing"] = activity.service_timing
            result["service_participation"] = activity.service_participation
            result["service_pricing_model"] = activity.service_pricing_model
            result["service_cta"] = activity.service_cta
        
        return result
```

---

### 4. Dependency Injection через ServiceFactory

**Назначение**: Единая точка создания Activity сервисов с правильной DI цепочкой.

**Пример реализации** (расширение ServiceFactory):

```python
class ServiceFactory:
    """Фабрика для создания сервисов с правильной DI цепочкой"""
    
    def __init__(self):
        # Используем синглтон BlockchainService
        self.blockchain = BlockchainService()
    
    def create_activity_registry_service(self) -> ActivityRegistryService:
        """
        Создает ActivityRegistryService с полной DI цепочкой.
        
        Returns:
            ActivityRegistryService: Сервис с правильно настроенными зависимостями
        """
        # 1. Создаем ActivityStorageService
        storage_service = ActivityStorageService()
        
        # 2. Создаем ActivityValidationService
        validation_service = ActivityValidationService()
        
        # 3. Создаем ActivityMetadataService
        metadata_service = ActivityMetadataService(storage_service)
        
        # 4. Создаем ActivityAssembler
        assembler = ActivityAssembler(
            storage_service=storage_service,
            metadata_service=metadata_service
        )
        
        # 5. Создаем SearchService с зависимостями
        fragment_service = ActivityFragmentService()
        embedding_service = ActivityEmbeddingService()
        search_service = ActivitySearchService(
            fragment_service=fragment_service,
            embedding_service=embedding_service
        )
        
        # 6. Создаем ActivityCacheService (синглтон)
        cache_service = ActivityCacheService()
        
        # 7. Создаем ActivityRegistryService со всеми зависимостями
        return ActivityRegistryService(
            blockchain_service=self.blockchain,  # Синглтон
            storage_service=storage_service,
            validation_service=validation_service,
            assembler=assembler,
            search_service=search_service,
            cache_service=cache_service,
            metadata_service=metadata_service
        )
    
    def create_activity_api_service(self) -> ActivityApiService:
        """
        Создает ActivityApiService с ActivityRegistryService.
        
        Returns:
            ActivityApiService: Сервис для API endpoints
        """
        registry_service = self.create_activity_registry_service()
        return ActivityApiService(registry_service=registry_service)
```

---

### 5. Интеграция с API Routes

**Назначение**: Использование ActivityApiService в FastAPI routes через Dependency Injection.

**Пример реализации** (обновление routes):

```python
# bot/api/routes/activities.py

from fastapi import APIRouter, Depends, HTTPException
from api.dependencies import get_activity_api_service
from services.application.activity.api_service import ActivityApiService

router = APIRouter(prefix="/activities", tags=["activities"])

@router.post("/draft")
async def create_draft(
    body: ActivityCreateRequest,
    creator_address: str = Depends(get_current_user_address),  # Из authentication
    api_service: ActivityApiService = Depends(get_activity_api_service)
):
    """
    Создать Draft Activity.
    """
    try:
        activity_data = body.model_dump(exclude_none=True)
        result = await api_service.create_draft(activity_data, creator_address)
        return JSONResponse(
            status_code=201,
            content=build_success_response(activity=result)
        )
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except AuthorizationError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{activity_id}")
async def get_activity(
    activity_id: str,
    api_service: ActivityApiService = Depends(get_activity_api_service)
):
    """
    Получить Activity по ID.
    """
    activity = await api_service.get_activity(activity_id)
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")
    
    return JSONResponse(
        status_code=200,
        content=build_success_response(activity=activity)
    )
```

---

## Диаграмма Dependency Injection цепочки

```
ServiceFactory
    │
    ├── BlockchainService (singleton)
    │
    ├── ActivityStorageService
    │   └── IPFSFactory().get_storage() → ArWeaveUploader
    │
    ├── ActivityValidationService
    │
    ├── ActivityMetadataService
    │   └── ActivityStorageService
    │
    ├── ActivityAssembler
    │   ├── ActivityStorageService
    │   └── ActivityMetadataService
    │
    ├── ActivityFragmentService
    │
    ├── ActivityEmbeddingService
    │   └── OpenAI API (для генерации эмбеддингов)
    │
    ├── ActivitySearchService
    │   ├── ActivityFragmentService
    │   ├── ActivityEmbeddingService
    │   └── Supabase (для векторного поиска)
    │
    ├── ActivityCacheService (singleton)
    │   └── ActivityStorageService (lazy loading)
    │
    └── ActivityRegistryService
        ├── BlockchainService (singleton)
        ├── ActivityStorageService
        ├── ActivityValidationService
        ├── ActivityAssembler
        ├── ActivitySearchService
        ├── ActivityCacheService (singleton)
        └── ActivityMetadataService
```

---

## Поток данных: создание Activity

```
1. POST /activities/draft (API Request)
   ↓
2. ActivityApiService.create_draft()
   ↓
3. ActivityRegistryService.create_draft()
   ↓
4. ActivityValidationService.validate_activity_data()
   ↓
5. ActivityStorageService.upload_metadata() → Arweave
   ↓
6. Получение CID (transaction ID)
   ↓
7. BlockchainService.create_activity() → Blockchain
   ↓
8. Получение activity_id из транзакции
   ↓
9. ActivitySearchService.index_activity() → Supabase (асинхронно)
   ↓
10. ActivityCacheService.set_cached_activity() (кэширование)
   ↓
11. Возврат результата через ActivityApiService
   ↓
12. API Response (JSON)
```

---

## Поток данных: получение Activity

```
1. GET /activities/{activity_id} (API Request)
   ↓
2. ActivityApiService.get_activity()
   ↓
3. ActivityCacheService.get_cached_activity() (проверка кэша)
   │
   ├── Если есть в кэше → возврат из кэша
   │
   └── Если нет в кэше:
       ↓
       4. ActivityRegistryService.get_activity()
       ↓
       5. BlockchainService.get_activity() → Blockchain
       ↓
       6. ActivityStorageService.download_metadata() → Arweave
       ↓
       7. ActivityAssembler.assemble_activity()
       │   ├── ActivityOnChain (из блокчейна)
       │   └── ActivityMetadata (из Arweave)
       │   └── → Activity (полный объект)
       ↓
       8. ActivityCacheService.set_cached_activity() (кэширование)
       ↓
       9. ActivityApiService._transform_activity_to_dict()
       ↓
       10. API Response (JSON)
```

---

## Сравнение с Product Services

| Аспект | Product | Activity |
|--------|---------|----------|
| **RegistryService** | ProductRegistryService | ActivityRegistryService |
| **StorageService** | ProductStorageService | ActivityStorageService |
| **ValidationService** | ProductValidationService | ActivityValidationService |
| **Assembler** | ProductAssembler | ActivityAssembler |
| **CacheService** | ProductCacheService | ActivityCacheService |
| **MetadataService** | ProductMetadataService | ActivityMetadataService |
| **SearchService** | Нет (не требуется) | ActivitySearchService (критично) |
| **ApiService** | Нет (routes напрямую) | ActivityApiService (тонкий слой) |

**Отличия Activity от Product**:
- ✅ Search интегрирован в доменный слой (для Activity критичен)
- ✅ EmbeddingService выделен отдельно (специфично для Activity)
- ✅ FragmentService для подготовки данных к индексации (специфично для Activity)
- ✅ ApiService как тонкий слой (для Activity требуется трансформация)

---

## State Machine для Activity Lifecycle

```
Draft
  ↓ [submit_review]
SentToReview
  ↓ [approve]        ↓ [reject]
Approved             Draft
  ↓ [publish]
Published
  ↓ [unpublish]
Draft
```

**Валидация переходов**: через `state_transitions.validate_state_transition()`

**Ограничения**:
- Published нельзя редактировать напрямую (требуется unpublish)
- SentToReview нельзя редактировать (ожидание approval/rejection)
- Draft → Published запрещен (требуется review)

---

## Кэширование стратегия

### ActivityCacheService

**TTL для разных типов данных**:
- `activity`: 1 час (часто изменяемые данные)
- `metadata`: 24 часа (стабильные метаданные)

**Инвалидация**:
- При обновлении Activity → `invalidate_activity(activity_id)`
- При изменении статуса → `invalidate_activity(activity_id)`
- При обновлении метаданных → `invalidate_cache("metadata")`

**Валидация кэшированных данных**:
- Проверка TTL
- Проверка структуры данных (опционально)

---

## Обработка ошибок

### Уровни обработки ошибок

1. **RegistryService уровень**:
   - Возвращает dict с `"status": "error"` и `"error": str`
   - Логирует ошибки с traceback

2. **ApiService уровень**:
   - Трансформирует ошибки в HTTP exceptions
   - ValidationError → 422
   - AuthorizationError → 403
   - NotFoundError → 404
   - InternalServerError → 500

3. **Routes уровень**:
   - Обрабатывает HTTP exceptions
   - Формирует error responses через `simulate_error_response()` или стандартные HTTP exceptions

**Пример обработки ошибок**:

```python
# В RegistryService
try:
    result = await self.blockchain_service.create_activity(...)
except Exception as e:
    self.logger.error(f"❌ Ошибка создания Activity в блокчейне: {e}")
    return {
        "status": "error",
        "error": f"Blockchain error: {str(e)}"
    }

# В ApiService
result = await self.registry_service.create_draft(...)
if result.get("status") == "error":
    error = result.get("error", "Unknown error")
    if "Validation failed" in error:
        raise ValidationError(error)
    elif "Blockchain error" in error:
        raise InternalServerError(error)
```

---

## Тестирование

### Unit тесты

**Паттерн**: Моки всех зависимостей, тестирование логики сервиса

**Пример**:

```python
@pytest.mark.asyncio
async def test_create_draft_success():
    # Arrange
    mock_blockchain = Mock()
    mock_storage = Mock()
    mock_validation = Mock()
    mock_search = Mock()
    
    mock_blockchain.create_activity.return_value = "0x123..."
    mock_blockchain.get_activity_id_from_tx.return_value = 1
    mock_storage.upload_metadata.return_value = "arweave_cid_123"
    mock_validation.validate_activity_data.return_value = ValidationResult.success()
    
    service = ActivityRegistryService(
        blockchain_service=mock_blockchain,
        storage_service=mock_storage,
        validation_service=mock_validation,
        search_service=mock_search
    )
    
    # Act
    result = await service.create_draft({"title": "Test"}, "0xabc...")
    
    # Assert
    assert result["status"] == "success"
    assert result["activity_id"] == "1"
    mock_storage.upload_metadata.assert_called_once()
    mock_blockchain.create_activity.assert_called_once()
```

### Integration тесты

**Паттерн**: Реальные сервисы, тестирование взаимодействия между слоями

**Пример**:

```python
@pytest.mark.asyncio
@pytest.mark.integration
async def test_create_draft_integration():
    # Используем реальные сервисы
    storage_service = ActivityStorageService()
    validation_service = ActivityValidationService()
    # ... создаем все зависимости
    
    service = ActivityRegistryService(...)
    
    # Act
    result = await service.create_draft(activity_data, creator_address)
    
    # Assert
    assert result["status"] == "success"
    # Проверяем что Activity создан в блокчейне
    blockchain_data = await blockchain_service.get_activity(result["activity_id"])
    assert blockchain_data is not None
```

### E2E тесты

**Паттерн**: Полный flow от API до блокчейна/Arweave/Supabase

**Пример**:

```python
@pytest.mark.e2e
@pytest.mark.asyncio
async def test_e2e_create_draft_activity(e2e_harness, e2e_snapshot):
    # Используем реальную инфраструктуру
    factory = ServiceFactory()
    api_service = factory.create_activity_api_service()
    
    # Act
    result = await api_service.create_draft(activity_data, creator_address)
    
    # Assert
    assert result["status"] == "success"
    # Проверяем синхронизацию между всеми слоями
```

---

## Производительность

### Оптимизации

1. **Кэширование**:
   - Activity кэшируются на 1 час
   - Метаданные кэшируются на 24 часа
   - Инвалидация при обновлении

2. **Асинхронная индексация**:
   - Индексация в Supabase не блокирует основной flow
   - Ошибки индексации логируются, но не критичны

3. **Batch операции**:
   - Возможность batch загрузки метаданных (для будущих оптимизаций)

### Метрики производительности

**Целевые показатели**:
- Создание Draft: < 5 секунд (блокчейн транзакция)
- Получение Activity: < 500ms (с кэшем), < 2 секунды (без кэша)
- Поиск Activity: < 1 секунда (Supabase векторный поиск)

---

## Безопасность

### Authentication/Authorization

- **Создание/обновление**: Только authenticated users
- **Публикация**: Только activated users
- **Проверка прав**: creator_address должен совпадать с creator из блокчейна

### Валидация данных

- **Входные данные**: Валидация через ActivityValidationService
- **State transitions**: Валидация через `validate_state_transition()`
- **CID валидация**: Проверка формата Arweave CID

---

## Расширяемость

### Добавление новых сервисов

1. Создать сервис по паттерну существующих
2. Добавить в ServiceFactory.create_activity_registry_service()
3. Добавить unit тесты
4. Добавить integration тесты (если требуется)

### Добавление новых методов

1. Добавить метод в RegistryService
2. Добавить метод в ApiService (если требуется для API)
3. Добавить endpoint в routes (если требуется для API)
4. Добавить тесты

---

## Связанные документы

- **Epic**: `docs/analysis/epics/epic-activities-api-production.md`
- **Вертикальная архитектура**: `docs/tech/activity-vertical-layers-analysis.md`
- **Интеграция архитектуры**: `docs/tech/activity-vertical-architecture-integration.md`
- **Search архитектура**: `docs/tech/activity-storage-search-architecture.md`
- **Product Services**: `bot/services/product/registry.py` (эталон)

---

**Версия**: 1.0  
**Дата создания**: 2026-01-27  
**Автор**: Development Team  
**Статус**: Архитектурный документ для реализации
