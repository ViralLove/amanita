# 🔄 Система Сериализации/Десериализации Amanita

## 📋 Обзор

Система сериализации/десериализации Amanita представляет собой **многоуровневую архитектуру** для работы с данными продуктов, которые хранятся в двух местах:
1. **Блокчейн** - базовые метаданные (ID, seller, IPFS CID, active status)
2. **IPFS/Arweave** - полные метаданные продукта в JSON формате

Система обеспечивает **бесшовную интеграцию** между блокчейном и децентрализованным хранилищем, автоматически собирая полные данные продукта при запросах.

## 🏗️ Архитектурные Принципы

### 1.1 Разделение Данных
- **Блокчейн**: Минимальные метаданные для быстрого поиска и валидации
- **IPFS/Arweave**: Полные метаданные продукта (описания, изображения, цены)
- **Кэш**: Промежуточное хранение для оптимизации производительности

### 1.2 Асинхронная Обработка
- **Lazy Loading**: Данные загружаются только при необходимости
- **Batch Processing**: Пакетная обработка для оптимизации
- **Fallback Mechanisms**: Graceful degradation при ошибках

### 1.3 Валидация на Каждом Уровне
- **Blockchain Validation**: Проверка существования и активности продукта
- **IPFS Validation**: Валидация CID и структуры JSON
- **Model Validation**: Валидация через ValidationFactory

## 🏛️ Архитектурная Структура

### 2.1 Компоненты Системы

```
BlockchainService (Базовые метаданные)
    ↓
ProductRegistryService (Оркестрация)
    ↓
ProductStorageService (IPFS/Arweave)
    ↓
ProductMetadataService (Обработка метаданных)
    ↓
Product Model (Финальная модель)
```

### 2.2 Поток Данных

```
1. Blockchain Query (get_all_products)
   ↓
2. Raw Blockchain Data (id, seller, ipfsCID, active)
   ↓
3. IPFS Download (download_json)
   ↓
4. JSON Deserialization (process_product_metadata)
   ↓
5. Product Model Assembly
   ↓
6. Caching & Return
```

## 🔧 Ключевые Компоненты

### 3.1 BlockchainService - Источник Базовых Данных

```python
class BlockchainService:
    def get_all_products(self) -> List[dict]:
        """Получает все продукты из блокчейна"""
        try:
            # Получаем список ID активных продуктов
            product_ids = self._call_contract_read_function(
                "ProductRegistry",
                "getAllActiveProductIds",
                []
            )
            
            # Получаем полные данные для каждого продукта
            products = []
            for product_id in product_ids:
                product = self._call_contract_read_function(
                    "ProductRegistry",
                    "getProduct",
                    None,
                    product_id
                )
                if product:
                    products.append(product)
            
            return products
            
        except Exception as e:
            logger.error(f"Error getting products: {e}")
            return []
```

**Структура данных из блокчейна:**
```python
# ProductRegistry.Product struct
product_data = (
    id,           # uint256 - уникальный идентификатор
    seller,       # address - адрес продавца
    ipfsCID,     # string - CID метаданных в IPFS
    active        # bool - статус активности
)
```

### 3.2 ProductStorageService - Работа с IPFS/Arweave

```python
class ProductStorageService:
    async def download_json(self, cid: str) -> Optional[Dict[str, Any]]:
        """Загружает JSON из IPFS/Arweave"""
        try:
            if not self.validate_ipfs_cid(cid):
                self.logger.warning(f"Invalid CID format: {cid}")
                return None
                
            return await self.ipfs.download_json_async(cid)
            
        except Exception as e:
            self.logger.error(f"Error downloading JSON from IPFS: {e}")
            return None
```

**Поддерживаемые провайдеры:**
- **Pinata**: Основной IPFS провайдер
- **Arweave**: Альтернативное децентрализованное хранилище
- **IPFSFactory**: Единая точка доступа к хранилищам

### 3.3 ProductMetadataService - Обработка Метаданных

```python
class ProductMetadataService:
    def process_product_metadata(self, metadata: Dict[str, Any]) -> Optional[Product]:
        """Обрабатывает метаданные продукта из IPFS"""
        try:
            # Валидация метаданных через ValidationFactory
            validator = ValidationFactory.get_product_validator()
            validation_result = validator.validate(metadata)
            
            if not validation_result.is_valid:
                self.logger.error(f"❌ Валидация метаданных не прошла: {validation_result.error_message}")
                return None
            
            # Извлекаем базовые поля
            title = metadata.get('title', '')
            product_id = metadata.get('id', '')
            alias = metadata.get('id', '')
            
            # Обрабатываем органические компоненты
            organic_components = []
            for component_data in metadata.get('organic_components', []):
                component = OrganicComponent.from_dict(component_data)
                organic_components.append(component)
            
            # Обрабатываем цены
            prices = []
            for price_data in metadata.get('prices', []):
                price = PriceInfo.from_dict(price_data)
                prices.append(price)
            
            # Создаем объект Product
            product = Product(
                id=product_id,
                alias=alias,
                title=title,
                organic_components=organic_components,
                prices=prices,
                # ... остальные поля
            )
            
            return product
            
        except Exception as e:
            self.logger.error(f"Ошибка обработки метаданных: {e}")
            return None
```

### 3.4 ProductRegistryService - Оркестрация Процесса

```python
class ProductRegistryService:
    async def _deserialize_product(self, product_data: tuple) -> Optional[Product]:
        """Десериализует продукт из кортежа блокчейна и метаданных IPFS"""
        try:
            if not hasattr(product_data, '__getitem__') or len(product_data) < 4:
                self.logger.error(f"Некорректная структура product_data: {product_data}")
                return None

            product_id = product_data[0]  # Блокчейн ID
            ipfs_cid = product_data[2]   # IPFS CID
            is_active = bool(product_data[3])  # Статус активности

            # Загружаем метаданные из IPFS
            metadata = self.storage_service.download_json(ipfs_cid)
            if not metadata:
                self.logger.warning(f"Не удалось получить метаданные для продукта {product_id}")
                return None

            # Обрабатываем метаданные через сервис
            product = self.metadata_service.process_product_metadata(metadata)
            if product:
                # Дополняем данными из блокчейна
                product.id = product_id
                product.cid = ipfs_cid
                product.is_active = is_active
                product.status = 1 if is_active else 0
                
            return product
            
        except Exception as e:
            self.logger.error(f"Ошибка десериализации продукта: {e}")
            return None
```

## 🔄 Процесс Сборки Продукта

### 4.1 Получение Каталога (get_all_products)

```python
async def get_all_products(self) -> List[Product]:
    """Получает все продукты с кэшированием"""
    try:
        # 1. Проверяем версию каталога
        catalog_version = self.blockchain_service.get_catalog_version()
        
        # 2. Проверяем кэш
        cached_catalog = self.cache_service.get_cached_item("catalog", "catalog")
        if cached_catalog and cached_catalog.get("version") == catalog_version:
            return cached_catalog.get('products', [])
        
        # 3. Загружаем из блокчейна
        products_data = self.blockchain_service.get_all_products()
        products = []
        
        # 4. Десериализуем каждый продукт
        for product_data in products_data:
            product = await self._deserialize_product(product_data)
            if product:
                products.append(product)
        
        # 5. Обновляем кэш
        self.cache_service.set_cached_item("catalog", {
            "version": catalog_version,
            "products": products
        }, "catalog")
        
        return products
        
    except Exception as e:
        self.logger.error(f"Error getting all products: {e}")
        return []
```

### 4.2 Получение Отдельного Продукта (get_product)

```python
async def get_product(self, product_id: Union[str, int]) -> Optional[Product]:
    """Получает продукт по ID"""
    try:
        # 1. Проверяем кэш
        cached_product = self.cache_service.get_cached_item("product", str(product_id))
        if cached_product:
            return cached_product
        
        # 2. Получаем из блокчейна
        product_data = self.blockchain_service.get_product(product_id)
        if not product_data:
            return None
        
        # 3. Десериализуем продукт
        product = await self._deserialize_product(product_data)
        
        # 4. Кэшируем результат
        if product:
            self.cache_service.set_cached_item("product", product, str(product_id))
        
        return product
        
    except Exception as e:
        self.logger.error(f"Error getting product {product_id}: {e}")
        return None
```

## 📊 Структура Данных

### 5.1 Блокчейн Структура (ProductRegistry.sol)

```solidity
struct Product {
    uint256 id;          // Уникальный идентификатор товара
    address seller;      // Продавец (автор записи)
    string ipfsCID;      // Ссылка на JSON-описание (IPFS CID)
    bool active;         // Активен ли товар
}
```

### 5.2 IPFS JSON Структура

```json
{
    "id": "product_001",
    "title": "Amanita Muscaria Powder",
    "organic_components": [
        {
            "biounit_id": "amanita_muscaria",
            "description_cid": "QmDescriptionHash...",
            "proportion": "100%"
        }
    ],
    "cover_image": "QmImageHash...",
    "categories": ["mushroom", "powder"],
    "forms": ["powder"],
    "species": "Amanita muscaria",
    "prices": [
        {
            "price": "30.00",
            "currency": "EUR",
            "weight": "100",
            "weight_unit": "g",
            "form": "powder"
        }
    ],
    "created_at": "2024-01-01T00:00:00Z"
}
```

### 5.3 Финальная Модель Product

```python
@dataclass
class Product:
    id: Union[str, int]           # Блокчейн ID
    alias: str                     # Бизнес-идентификатор
    status: int                    # Статус (0/1)
    cid: str                       # IPFS CID
    title: str                     # Название
    organic_components: List[OrganicComponent]  # Компоненты
    cover_image_url: Optional[str] # URL изображения
    categories: List[str]          # Категории
    forms: List[str]               # Формы
    species: str                   # Вид
    prices: List[PriceInfo]        # Цены
```

## 🔗 Интеграция в API

### 6.1 Bot Handler (Telegram)

```python
@router.callback_query(F.data == "menu:catalog")
async def show_catalog(callback: CallbackQuery):
    """Обработчик для показа каталога товаров"""
    try:
        # Получаем каталог через ProductRegistryService (с кэшированием)
        products = product_registry_service.get_all_products()
        
        if not products:
            await callback.message.answer(loc.t("catalog.empty"))
            return

        # Отправляем каждый продукт отдельным сообщением
        for product in products:
            # Формируем текст описания продукта
            product_text = format_product_description(product, lang)
            await callback.message.answer(product_text)
            
    except Exception as e:
        logger.error(f"Ошибка показа каталога: {e}")
        await callback.message.answer(loc.t("catalog.error"))
```

### 6.2 API Endpoints (FastAPI)

```python
# TODO: Добавить endpoint для получения каталога
@router.get("/catalog", response_model=List[ProductResponse])
async def get_catalog(
    registry_service: ProductRegistryService = Depends(get_product_registry_service)
):
    """Получение каталога продуктов"""
    products = await registry_service.get_all_products()
    return [ProductResponse.from_product(product) for product in products]

@router.get("/products/{product_id}", response_model=ProductResponse)
async def get_product(
    product_id: str,
    registry_service: ProductRegistryService = Depends(get_product_registry_service)
):
    """Получение продукта по ID"""
    product = await registry_service.get_product(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return ProductResponse.from_product(product)
```

## 🧪 Тестирование Системы

### 7.1 Mock Система

```python
@pytest.fixture(scope="function")
def mock_ipfs_storage():
    """Универсальный мок для IPFS/Arweave storage"""
    class MockIPFSStorage:
        def __init__(self):
            self._storage = {}  # CID -> data mapping
            self._counter = 0   # Счетчик для генерации уникальных CID
        
        def download_json(self, cid: str) -> Optional[Dict]:
            return self._storage.get(cid)
        
        def upload_json(self, data: Dict) -> str:
            cid = f"QmMockCID{self._counter:06d}"
            self._storage[cid] = data
            self._counter += 1
            return cid
    
    return MockIPFSStorage()
```

### 7.2 Тестовые Фикстуры

```python
@pytest.fixture(scope="function")
def mock_blockchain_service():
    """Mock для BlockchainService"""
    class MockBlockchainService:
        def get_catalog_version(self):
            return 1
        
        def get_all_products(self):
            return [
                (1, "0x123", "QmCID1", True),
                (2, "0x456", "QmCID2", True),
                (3, "0x789", "QmCID3", True)
            ]
    
    return MockBlockchainService()
```

## 🔍 Отладка и Диагностика

### 8.1 Логирование Процесса

```python
def _deserialize_product(self, product_data: tuple) -> Optional[Product]:
    """Десериализует продукт с детальным логированием"""
    try:
        self.logger.info(f"🔍 Начинаем десериализацию продукта: {product_data}")
        
        # Извлекаем данные из блокчейна
        product_id = product_data[0]
        ipfs_cid = product_data[2]
        is_active = bool(product_data[3])
        
        self.logger.info(f"🔍 Данные из блокчейна: ID={product_id}, CID={ipfs_cid}, Active={is_active}")
        
        # Загружаем метаданные из IPFS
        self.logger.info(f"🔍 Загружаем метаданные из IPFS: {ipfs_cid}")
        metadata = self.storage_service.download_json(ipfs_cid)
        
        if not metadata:
            self.logger.warning(f"⚠️ Метаданные не найдены для CID: {ipfs_cid}")
            return None
        
        self.logger.info(f"🔍 Метаданные загружены: {len(metadata)} полей")
        
        # Обрабатываем метаданные
        product = self.metadata_service.process_product_metadata(metadata)
        
        if product:
            self.logger.info(f"✅ Продукт успешно десериализован: {product.id}")
        else:
            self.logger.error(f"❌ Ошибка обработки метаданных для продукта {product_id}")
        
        return product
        
    except Exception as e:
        self.logger.error(f"💥 Критическая ошибка десериализации: {e}")
        return None
```

### 8.2 Метрики Производительности

```python
import time

async def get_all_products(self) -> List[Product]:
    """Получает все продукты с измерением производительности"""
    start_time = time.time()
    
    try:
        # Проверяем кэш
        cache_start = time.time()
        cached_catalog = self.cache_service.get_cached_item("catalog", "catalog")
        cache_time = time.time() - cache_start
        
        if cached_catalog and self._is_cache_valid(cached_catalog):
            self.logger.info(f"⚡ Кэш найден за {cache_time:.3f}s")
            return cached_catalog.get('products', [])
        
        # Загружаем из блокчейна
        blockchain_start = time.time()
        products_data = self.blockchain_service.get_all_products()
        blockchain_time = time.time() - blockchain_start
        
        # Десериализуем продукты
        deserialize_start = time.time()
        products = []
        for product_data in products_data:
            product = await self._deserialize_product(product_data)
            if product:
                products.append(product)
        deserialize_time = time.time() - deserialize_start
        
        total_time = time.time() - start_time
        
        self.logger.info(f"📊 Метрики производительности:")
        self.logger.info(f"  - Кэш: {cache_time:.3f}s")
        self.logger.info(f"  - Блокчейн: {blockchain_time:.3f}s")
        self.logger.info(f"  - Десериализация: {deserialize_time:.3f}s")
        self.logger.info(f"  - Общее время: {total_time:.3f}s")
        self.logger.info(f"  - Продуктов: {len(products)}")
        
        return products
        
    except Exception as e:
        self.logger.error(f"Error getting all products: {e}")
        return []
```

## 🔧 Конфигурация и Настройки

### 9.1 Настройка Хранилищ

```python
# .env файл
STORAGE_TYPE=pinata  # или arweave
PINATA_API_KEY=your_pinata_key
PINATA_SECRET_KEY=your_pinata_secret
ARWEAVE_PRIVATE_KEY=your_arweave_key

# IPFSFactory автоматически выбирает провайдера
storage_service = IPFSFactory().get_storage()
```

### 9.2 Настройка Кэширования

```python
# Настройки кэша в ProductCacheService
CACHE_TTL = 3600  # 1 час
CATALOG_CACHE_TTL = 1800  # 30 минут для каталога
PRODUCT_CACHE_TTL = 7200  # 2 часа для отдельных продуктов
```

## 🚀 Оптимизации Производительности

### 10.1 Batch Processing

```python
async def _deserialize_products_batch(self, products_data: List[tuple]) -> List[Product]:
    """Пакетная десериализация продуктов для оптимизации"""
    tasks = [self._deserialize_product(data) for data in products_data]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    products = []
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            self.logger.error(f"Ошибка десериализации продукта {i}: {result}")
        elif result:
            products.append(result)
    
    return products
```

### 10.2 Lazy Loading

```python
class Product:
    def __init__(self, **kwargs):
        self._description = None
        self._images = None
        # ... остальные поля
    
    @property
    def description(self) -> Optional[Description]:
        """Lazy loading описания"""
        if self._description is None and self.description_cid:
            self._description = self._load_description()
        return self._description
    
    def _load_description(self) -> Optional[Description]:
        """Загружает описание по CID"""
        try:
            storage_service = ProductStorageService()
            description_data = storage_service.download_json(self.description_cid)
            if description_data:
                return Description.from_dict(description_data)
        except Exception as e:
            logger.error(f"Ошибка загрузки описания: {e}")
        return None
```

## 🔮 Будущие Улучшения

### 11.1 Планируемые Функции
- [ ] **Streaming API** для больших каталогов
- [ ] **GraphQL** для гибких запросов
- [ ] **Real-time синхронизация** с блокчейном
- [ ] **Distributed caching** через Redis Cluster

### 11.2 Оптимизации Архитектуры
- [ ] **Connection pooling** для IPFS gateways
- [ ] **Circuit breaker** для отказоустойчивости
- [ ] **Rate limiting** для внешних API
- [ ] **Metrics collection** для мониторинга

## ✅ Заключение

Система сериализации/десериализации Amanita представляет собой **высокооптимизированное решение** для работы с гибридными данными:

1. **🏗️ Модульная архитектура** с четким разделением ответственности
2. **⚡ Высокая производительность** благодаря кэшированию и batch processing
3. **🔒 Надежность** с fallback механизмами и обработкой ошибок
4. **📊 Мониторинг** производительности и детальное логирование
5. **🧪 Полная тестируемость** с comprehensive mock системой
6. **🔄 Бесшовная интеграция** между блокчейном и IPFS

Архитектура обеспечивает **эффективную сборку продуктов** из двух источников данных, **оптимизированную производительность** через кэширование и **надежную обработку ошибок** на каждом уровне.

---

*Последнее обновление: $(date)*
*Версия документа: 1.0.0*
*Автор: Amanita Team*
