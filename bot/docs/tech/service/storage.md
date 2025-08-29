# Storage Service Layer - Техническая документация

## 📋 **Обзор архитектуры**

Storage Service Layer в Amanita Bot представляет собой многоуровневую систему для работы с децентрализованными хранилищами (IPFS/Arweave). Система спроектирована с учетом гибкости, производительности и возможности легкого переключения между провайдерами.

**Основные принципы:**
- **Абстракция провайдеров** - единый интерфейс для разных хранилищ
- **Адаптивные режимы коммуникации** - sync/async/hybrid подходы
- **Интеграция с веб-приложением** - через FastAPI и dependency injection
- **Обработка ошибок** - типизированные исключения и стратегии восстановления

## 🏗️ **Архитектурные слои**

### **1. Базовый интерфейс (BaseStorageProvider)**

```python
# bot/services/core/storage/base.py
class BaseStorageProvider(ABC):
    @abstractmethod
    def upload_file(self, file_path_or_data: Union[str, dict], file_name: Optional[str] = None) -> str:
        """Загружает файл в хранилище"""
        pass
    
    @abstractmethod
    def download_json(self, identifier: str) -> Optional[Dict[str, Any]]:
        """Загружает JSON данные из хранилища"""
        pass
    
    @abstractmethod
    def get_public_url(self, identifier: str) -> str:
        """Формирует публичный URL для доступа к файлу"""
        pass
    
    def is_valid_identifier(self, identifier: str) -> bool:
        """Проверяет валидность идентификатора для текущего типа хранилища"""
        pass
```

**Назначение:** Определяет общий контракт для всех провайдеров хранилищ, обеспечивая единообразие API.

### **2. Конкретные реализации (Concrete Implementations)**

#### **SecurePinataUploader**
- **Файл:** `bot/services/core/storage/pinata.py`
- **Наследование:** `BaseStorageProvider`
- **Особенности:**
  - Поддержка rate limiting и circuit breaker
  - Кэширование загруженных файлов
  - Метрики производительности
  - Валидация файлов и MIME-типов
  - Batch операции для массовых загрузок
  - Retry логика с экспоненциальной задержкой
  - Поддержка различных типов контента

#### **ArWeaveUploader**
- **Файл:** `bot/services/core/storage/ar_weave.py`
- **Наследование:** `BaseStorageProvider`
- **Особенности:**
  - Интеграция с Supabase Edge Functions
  - Асинхронная загрузка через HTTP API
  - Поддержка различных типов контента
  - Постоянное хранение данных
  - HTTP-based операции с retry логикой

### **3. Фабрика провайдеров (IPFSFactory)**

```python
# bot/services/core/ipfs_factory.py
class IPFSFactory:
    def __init__(self):
        self.set_storage(STORAGE_TYPE)
    
    def set_storage(self, storage_type: str):
        if storage_type.lower() == 'pinata':
            self.storage = SecurePinataUploader()
        elif storage_type.lower() == 'arweave':
            self.storage = ArWeaveUploader()
        else:
            raise ValueError(f"Неподдерживаемый тип хранилища: {storage_type}")
```

**Назначение:** Создает и управляет экземплярами провайдеров на основе переменной окружения `STORAGE_TYPE`.

### **4. Сервисный слой (ProductStorageService)**

```python
# bot/services/product/storage.py
class ProductStorageService:
    def __init__(self, storage_provider=None):
        if storage_provider is None:
            self.ipfs = IPFSFactory().get_storage()
        else:
            self.ipfs = storage_provider
            
        self.communication_type = STORAGE_COMMUNICATION_TYPE
```

**Назначение:** Абстрагирует работу с хранилищами для бизнес-логики, обеспечивая единый интерфейс независимо от выбранного провайдера.

### **5. Интеграция с веб-приложением**

#### **API маршруты**
```python
# bot/api/routes/media.py
@router.post("/upload")
async def upload_media(file: UploadFile = File(...)):
    storage_service = ProductStorageService()
    cid = storage_service.upload_media_file(temp_path)
    return {"cid": cid, "filename": file.filename, "status": "success"}

# bot/api/routes/description.py
@router.post("/upload")
async def upload_description(request: Request):
    storage_service = ProductStorageService()
    cid = storage_service.upload_json(json_data)
    return {"cid": cid, "status": "success"}
```

#### **Dependency Injection**
```python
# bot/api/dependencies.py
def get_product_storage_service(storage_provider=None) -> ProductStorageService:
    return ProductStorageService(storage_provider=storage_provider)

def get_product_registry_service(
    blockchain_service: BlockchainService = None,
    storage_service: ProductStorageService = None,
    # ... другие зависимости
) -> ProductRegistryService:
    if storage_service is None:
        storage_service = get_product_storage_service()
    # ... создание сервиса
```

## ⚙️ **Конфигурация и переменные окружения**

### **Основные параметры:**

```bash
# Тип хранилища (pinata | arweave)
STORAGE_TYPE=pinata

# Режим коммуникации (sync | async | hybrid)
STORAGE_COMMUNICATION_TYPE=sync
```

### **Провайдер-специфичные параметры:**

#### **Pinata:**
```bash
PINATA_API_KEY=your_api_key
PINATA_API_SECRET=your_api_secret
PINATA_JWT=your_jwt_token
```

#### **ArWeave:**
```bash
ARWEAVE_PRIVATE_KEY=your_private_key
SUPABASE_URL=your_supabase_url
SUPABASE_ANON_KEY=your_supabase_key
```

### **Конфигурация API**
```python
# bot/config.py
STORAGE_COMMUNICATION_TYPE = os.getenv("STORAGE_COMMUNICATION_TYPE", "sync")
if STORAGE_COMMUNICATION_TYPE not in ["sync", "async", "hybrid"]:
    logging.warning(f"STORAGE_COMMUNICATION_TYPE '{STORAGE_COMMUNICATION_TYPE}' не поддерживается, используем 'sync'")
    STORAGE_COMMUNICATION_TYPE = "sync"
```

## 🔄 **Режимы коммуникации**

### **Sync Mode**
- **Описание:** Синхронные вызовы методов провайдера
- **Использование:** Pinata, мок-провайдеры
- **Преимущества:** Простота, предсказуемость
- **Недостатки:** Блокировка выполнения
- **Реализация:** Прямые вызовы методов провайдера

### **Async Mode**
- **Описание:** Асинхронные вызовы через `asyncio.run()`
- **Использование:** ArWeave, HTTP-based провайдеры
- **Преимущества:** Неблокирующее выполнение
- **Недостатки:** Сложность, overhead
- **Реализация:** Обертка async методов через asyncio.run()

### **Hybrid Mode**
- **Описание:** Комбинация sync и async подходов
- **Использование:** Оптимизация для разных сценариев
- **Преимущества:** Гибкость, производительность
- **Недостатки:** Сложность логики
- **Реализация:** Адаптивный выбор на основе доступных методов

### **Адаптивная логика в ProductStorageService**

```python
def download_json(self, cid: str) -> Optional[Dict[str, Any]]:
    # Проверяем доступные методы у провайдера
    has_async = hasattr(self.ipfs, 'download_json_async')
    has_sync = hasattr(self.ipfs, 'download_json')
    
    if self.communication_type == "sync":
        if has_sync:
            return self.ipfs.download_json(cid)  # Прямой вызов
        else:
            # Fallback для async провайдеров в sync режиме
            return asyncio.run(self.ipfs.download_json_async(cid))
    
    elif self.communication_type == "async":
        if has_async:
            return asyncio.run(self.ipfs.download_json_async(cid))
        elif has_sync:
            # Fallback: sync метод напрямую
            return self.ipfs.download_json(cid)
```

## 📡 **API и методы**

### **Основные операции:**

#### **Загрузка файлов:**
```python
# Загрузка файла по пути
cid = storage.upload_file("/path/to/file.jpg")

# Загрузка данных
cid = storage.upload_file({"file_path": "/path/to/file.jpg", "content_type": "image/jpeg"})

# Загрузка медиафайлов через API
@router.post("/media/upload")
async def upload_media(file: UploadFile = File(...)):
    storage_service = ProductStorageService()
    cid = storage_service.upload_media_file(temp_path)
    return {"cid": cid, "filename": file.filename, "status": "success"}
```

#### **Загрузка данных:**
```python
# Загрузка JSON
data = storage.download_json("QmCID123...")

# Загрузка файла
content = storage.download_file("QmCID123...")

# Загрузка описаний через API
@router.post("/description/upload")
async def upload_description(request: Request):
    storage_service = ProductStorageService()
    cid = storage_service.upload_json(json_data)
    return {"cid": cid, "status": "success"}
```

#### **Формирование URL:**
```python
# Получение публичного URL
url = storage.get_public_url("QmCID123...")
# Результат: https://gateway.pinata.cloud/ipfs/QmCID123... (Pinata)
# Результат: https://arweave.net/tx_id... (ArWeave)

# Gateway URLs для разных провайдеров
def get_gateway_url(self, cid: str, gateway: str = "ipfs") -> Optional[str]:
    if gateway == "ipfs":
        return f"https://ipfs.io/ipfs/{cid}"
    elif gateway == "arweave":
        return f"https://arweave.net/{cid}"
    return None
```

## 🎯 **Сценарии использования**

### **1. Telegram Bot - Отображение изображений**
```python
# bot/handlers/catalog.py
if product.cover_image_url:
    # Автоматическое формирование URL в зависимости от провайдера
    image_url = storage_service.get_public_url(product.cover_image_url)
    # Загрузка и отправка изображения
```

### **2. Product Registry - Загрузка метаданных**
```python
# Автоматический выбор провайдера и режима коммуникации
metadata = storage_service.download_json(product_cid)
```

### **3. Batch Operations - Массовая загрузка**
```python
# Поддержка batch операций в Pinata
results = storage.upload_files_batch([
    ("/path/file1.jpg", "file1.jpg"),
    ("/path/file2.jpg", "file2.jpg")
])
```

### **4. Веб-приложение - Загрузка медиафайлов**
```python
# API endpoint для загрузки файлов
@router.post("/media/upload")
async def upload_media(file: UploadFile = File(...)):
    # Валидация файла
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(status_code=415, detail="Недопустимый тип файла")
    
    # Сохранение во временный файл
    temp_path = f"/tmp/{file.filename}"
    with open(temp_path, "wb") as f:
        f.write(await file.read())
    
    try:
        # Загрузка через storage service
        storage_service = ProductStorageService()
        cid = storage_service.upload_media_file(temp_path)
        return {"cid": cid, "filename": file.filename, "status": "success"}
    finally:
        # Очистка временного файла
        os.remove(temp_path)
```

### **5. WordPress Plugin - Синхронизация продуктов**
```python
# Загрузка метаданных продукта
@router.post("/products/upload")
async def upload_products(request: ProductUploadRequest):
    registry_service = ProductRegistryService(
        storage_service=get_product_storage_service()
    )
    
    for product in request.products:
        result = await registry_service.create_product(product_dict)
        # Автоматическое создание IPFS CID для метаданных
```

## 🔧 **Обработка ошибок**

### **Иерархия исключений:**

```python
# bot/services/core/storage/exceptions.py
StorageError (базовый класс)
├── StorageAuthError (ошибки аутентификации)
├── StoragePermissionError (ошибки прав доступа)
├── StorageRateLimitError (превышение лимитов)
├── StorageNotFoundError (файл не найден)
├── StorageValidationError (ошибки валидации)
├── StorageTimeoutError (таймауты)
├── StorageNetworkError (сетевые ошибки)
├── StorageConfigError (ошибки конфигурации)
└── StorageProviderError (ошибки провайдера)
```

### **Стратегии восстановления:**

1. **Автоматические повторные попытки** с экспоненциальной задержкой
2. **Circuit Breaker** для предотвращения каскадных сбоев
3. **Fallback механизмы** при недоступности основного провайдера
4. **Кэширование** для снижения нагрузки на хранилища

### **Retry логика в Pinata**

```python
def retry_with_backoff(retries=3, backoff_in_seconds=1):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            x = 0
            while True:
                try:
                    return func(*args, **kwargs)
                except requests.exceptions.HTTPError as e:
                    if e.response.status_code == 429:  # Too Many Requests
                        if x == retries:
                            raise
                        else:
                            sleep = (backoff_in_seconds * 2 ** x + random.uniform(0, 1))
                            logger.warning(f"Rate limit hit, waiting {sleep:.2f} seconds...")
                            time.sleep(sleep)
                            x += 1
                    else:
                        raise
        return wrapper
    return decorator
```

## 📊 **Метрики и мониторинг**

### **Сбор метрик:**

- **Время загрузки** файлов
- **Количество ошибок** по типам
- **Hit/miss ratio** кэша
- **Rate limiting** статистика

### **PinataMetrics класс**

```python
class PinataMetrics:
    def __init__(self):
        self.upload_times: List[float] = []
        self.error_counts: Dict[str, int] = {}
        self.cache_hits: int = 0
        self.cache_misses: int = 0
        self.last_metrics_dump: Optional[datetime] = None
        self.metrics_dump_interval = timedelta(hours=1)
    
    def track_upload(self, duration: float):
        """Записывает время загрузки файла"""
        self.upload_times.append(duration)
        self._check_metrics_dump()
    
    def track_error(self, error_type: str):
        """Записывает ошибку определенного типа"""
        self.error_counts[error_type] = self.error_counts.get(error_type, 0) + 1
        self._check_metrics_dump()
```

### **Логирование:**

```python
logger.info(f"[Pinata] Успешно загружен файл: {cid}")
logger.error(f"[ArWeave] Ошибка загрузки: {error}")
logger.debug(f"[Storage] Режим коммуникации: {communication_type}")
logger.debug(f"[ProductStorageService] Провайдер {type(self.ipfs)}: async={has_async}, sync={has_sync}")
```

## 🚀 **Производительность и оптимизация**

### **Стратегии оптимизации:**

1. **Многоуровневое кэширование** (память + файл)
2. **Batch операции** для массовых загрузок
3. **Connection pooling** для HTTP клиентов
4. **Асинхронная обработка** где возможно
5. **Rate limiting** для предотвращения блокировок

### **Кэширование в Pinata**

```python
class SecurePinataUploader(BaseStorageProvider):
    def __init__(self):
        # Инициализация кэша
        self.cache = {}
        self.cache_ttl = timedelta(hours=24)
        self.metrics = PinataMetrics()
    
    def _get_cached_file(self, file_path: str) -> Optional[str]:
        """Получает CID из кэша если файл не изменился"""
        if file_path in self.cache:
            cache_entry = self.cache[file_path]
            if datetime.now() - cache_entry['timestamp'] < self.cache_ttl:
                self.metrics.track_cache_hit()
                return cache_entry['cid']
        self.metrics.track_cache_miss()
        return None
```

### **Мониторинг производительности:**

- **Response time** для операций
- **Throughput** (операций в секунду)
- **Error rate** и типы ошибок
- **Resource usage** (память, CPU, сеть)

## 🔗 **Интеграция с веб-приложением**

### **FastAPI интеграция**

```python
# bot/api/main.py
def create_api_app(service_factory=None, log_level: str = "INFO", log_file: Optional[str] = None) -> FastAPI:
    app = FastAPI(**fastapi_config)
    
    # Настройка CORS для веб-клиентов
    app.add_middleware(CORSMiddleware, **cors_config)
    
    # Настройка Trusted Host для безопасности
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=APIConfig.TRUSTED_HOSTS)
    
    # Интеграция с ServiceFactory
    if service_factory:
        app.state.service_factory = service_factory
        logger.info("ServiceFactory интегрирован в приложение")
    
    return app
```

### **Маршруты для веб-приложения**

#### **Media Management**
```python
# bot/api/routes/media.py
router = APIRouter(prefix="/media", tags=["media"])

ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 МБ

@router.post("/upload")
async def upload_media(file: UploadFile = File(...)):
    # Валидация типа и размера файла
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(status_code=415, detail="Недопустимый тип файла")
    
    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="Превышен размер файла")
    
    # Загрузка через storage service
    temp_path = f"/tmp/{file.filename}"
    with open(temp_path, "wb") as f:
        f.write(contents)
    
    try:
        storage_service = ProductStorageService()
        cid = storage_service.upload_media_file(temp_path)
        return {"cid": cid, "filename": file.filename, "status": "success"}
    finally:
        os.remove(temp_path)
```

#### **Description Management**
```python
# bot/api/routes/description.py
router = APIRouter(prefix="/description", tags=["description"])

MAX_JSON_SIZE = 128 * 1024  # 128 КБ

@router.post("/upload")
async def upload_description(request: Request):
    # Проверка размера JSON
    body = await request.body()
    if len(body) > MAX_JSON_SIZE:
        raise HTTPException(status_code=413, detail="Превышен размер JSON")
    
    # Парсинг и валидация JSON
    try:
        json_data = await request.json()
    except Exception as e:
        raise HTTPException(status_code=400, detail="Невалидный JSON")
    
    # Загрузка через storage service
    storage_service = ProductStorageService()
    cid = storage_service.upload_json(json_data)
    return {"cid": cid, "status": "success"}
```

### **Dependency Injection система**

```python
# bot/api/dependencies.py
def get_product_storage_service(storage_provider=None) -> ProductStorageService:
    """FastAPI dependency provider для ProductStorageService"""
    return ProductStorageService(storage_provider=storage_provider)

def get_product_registry_service(
    blockchain_service: BlockchainService = None,
    storage_service: ProductStorageService = None,
    validation_service: ProductValidationService = None,
    account_service: AccountService = None,
) -> ProductRegistryService:
    """FastAPI dependency provider для ProductRegistryService"""
    if storage_service is None:
        storage_service = get_product_storage_service()
    
    return ProductRegistryService(
        blockchain_service=blockchain_service,
        storage_service=storage_service,
        validation_service=validation_service,
        account_service=account_service
    )
```

## 🔮 **Расширяемость и будущее развитие**

### **Добавление новых провайдеров:**

1. **Реализовать** `BaseStorageProvider`
2. **Добавить** в `IPFSFactory`
3. **Настроить** конфигурацию
4. **Протестировать** интеграцию

### **Планируемые улучшения:**

- **Multi-provider** поддержка (загрузка в несколько хранилищ)
- **Content addressing** для дедупликации
- **Compression** и оптимизация файлов
- **CDN integration** для популярного контента
- **Encryption** для чувствительных данных
- **WebSocket** поддержка для real-time уведомлений
- **GraphQL** API для сложных запросов

### **Интеграция с новыми технологиями**

#### **IPFS Cluster**
```python
class IPFSClusterProvider(BaseStorageProvider):
    def __init__(self, cluster_urls: List[str]):
        self.cluster_urls = cluster_urls
        self.current_node = 0
    
    def upload_file(self, file_path_or_data: Union[str, dict], file_name: Optional[str] = None) -> str:
        # Распределенная загрузка по узлам кластера
        pass
```

#### **Filecoin Integration**
```python
class FilecoinProvider(BaseStorageProvider):
    def __init__(self, lotus_rpc_url: str):
        self.lotus_rpc_url = lotus_rpc_url
    
    def upload_file(self, file_path_or_data: Union[str, dict], file_name: Optional[str] = None) -> str:
        # Загрузка с оплатой через Filecoin
        pass
```

## 📝 **Примеры использования**

### **Базовое использование:**

```python
from bot.services.core.ipfs_factory import IPFSFactory

# Получение провайдера
storage = IPFSFactory().get_storage()

# Загрузка файла
cid = storage.upload_file("/path/to/image.jpg")

# Формирование URL
url = storage.get_public_url(cid)
```

### **Через ProductStorageService:**

```python
from bot.services.product.storage import ProductStorageService

# Создание сервиса
storage_service = ProductStorageService()

# Загрузка метаданных продукта
metadata = storage_service.download_json(product_cid)

# Валидация CID
is_valid = storage_service.validate_ipfs_cid(cid)
```

### **В FastAPI приложении:**

```python
from fastapi import Depends
from bot.api.dependencies import get_product_storage_service

@router.post("/upload")
async def upload_file(
    file: UploadFile,
    storage_service: ProductStorageService = Depends(get_product_storage_service)
):
    cid = storage_service.upload_media_file(file_path)
    return {"cid": cid, "status": "success"}
```

### **Интеграция с Telegram Bot:**

```python
# bot/handlers/catalog.py
async def show_product_catalog(update: Update, context: ContextTypes.DEFAULT_TYPE):
    storage_service = ProductStorageService()
    
    for product in products:
        if product.cover_image_url:
            # Автоматическое формирование URL
            image_url = storage_service.get_public_url(product.cover_image_url)
            await context.bot.send_photo(
                chat_id=update.effective_chat.id,
                photo=image_url,
                caption=product.title
            )
```

## 🧪 **Тестирование**

### **Unit тесты**

```python
# tests/test_storage_service.py
def test_pinata_uploader():
    uploader = SecurePinataUploader()
    cid = uploader.upload_file("test_file.txt")
    assert cid is not None
    assert uploader.is_valid_identifier(cid)

def test_arweave_uploader():
    uploader = ArWeaveUploader()
    cid = uploader.upload_file("test_file.txt")
    assert cid is not None
```

### **Integration тесты**

```python
# tests/test_storage_integration.py
def test_storage_service_with_mock():
    mock_storage = MockStorageProvider()
    service = ProductStorageService(storage_provider=mock_storage)
    
    result = service.download_json("test_cid")
    assert result is not None
```

### **API тесты**

```python
# tests/test_api_storage.py
def test_media_upload_endpoint(client):
    with open("test_image.jpg", "rb") as f:
        response = client.post("/media/upload", files={"file": f})
        assert response.status_code == 200
        assert "cid" in response.json()
```

## ✅ **Заключение**

Storage Service Layer обеспечивает:

- **Гибкость** - легкое переключение между провайдерами
- **Производительность** - оптимизированные режимы коммуникации
- **Надежность** - обработка ошибок и стратегии восстановления
- **Расширяемость** - простое добавление новых провайдеров
- **Единообразие** - общий API для всех типов хранилищ
- **Интеграция** - бесшовная работа с веб-приложением через FastAPI
- **Мониторинг** - детальная метрика и логирование операций

Система готова к production использованию и дальнейшему развитию, обеспечивая надежную основу для децентрализованного хранения данных в экосистеме Amanita.
