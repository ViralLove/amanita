# Архитектура каталога в Telegram боте Amanita

## 📋 **Обзор системы**

Каталог продуктов в Telegram боте представляет собой многоуровневую архитектуру, которая обеспечивает:
- **Кэширование** для быстрого доступа к данным
- **Валидацию** через единую систему ValidationFactory
- **Хранение** в IPFS (Pinata/Arweave) с гибридными режимами коммуникации
- **Синхронизацию** с блокчейном для актуальности данных

## 🏗️ **Архитектурные слои**

### 1. **Telegram Bot Layer** (`bot/handlers/catalog.py`)
```python
@router.callback_query(F.data == "menu:catalog")
async def show_catalog(callback: CallbackQuery):
    # 1. Получаем user_id и язык пользователя
    # 2. Получаем каталог через ProductRegistryService (с кэшированием)
    # 3. Для каждого продукта формируем описание и отправляем в чат
```

**Ключевые компоненты:**
- **Router**: Обработчик callback-запросов для каталога
- **Localization**: Многоязычная поддержка (ru/en)
- **UserSettings**: Управление настройками пользователя
- **ProductRegistryService**: Основной сервис для работы с продуктами

### 2. **Service Layer** (`bot/services/product/`)

#### **ProductRegistryService** - Центральный координатор
```python
class ProductRegistryService:
    def __init__(self, 
                 blockchain_service: BlockchainService,
                 storage_service: ProductStorageService,
                 validation_service: ProductValidationService,
                 account_service: AccountService):
        self.cache_service = ProductCacheService()
        self.metadata_service = ProductMetadataService(storage_service)
```

**Основные методы:**
- `async def get_all_products() -> List[Product]` - получение всех продуктов с кэшированием
- `async def get_product(product_id) -> Product` - получение конкретного продукта
- `async def create_product(product_data) -> dict` - создание нового продукта

**Стратегия кэширования:**
```python
CACHE_TTL = {
    'catalog': timedelta(minutes=5),      # Каталог продуктов
    'description': timedelta(hours=24),   # Описания продуктов
    'image': timedelta(hours=12)          # Изображения
}
```

#### **ProductCacheService** - Многоуровневое кэширование
```python
class ProductCacheService:
    def __init__(self):
        self.catalog_cache: Dict = {}      # {"version": int, "products": List[Product], "timestamp": datetime}
        self.description_cache: Dict[str, Tuple[Description, datetime]] = {}
        self.image_cache: Dict[str, Tuple[str, datetime]] = {}
```

**Валидация кэша:**
```python
def _validate_cached_data(self, data: Any, data_type: str) -> ValidationResult:
    if data_type == 'catalog':
        # Валидируем структуру каталога
        if isinstance(data, dict) and 'version' in data and 'products' in data:
            return ValidationResult.success()
        else:
            return ValidationResult.failure("Неверная структура каталога")
```

#### **ProductStorageService** - Адаптивное хранилище
```python
class ProductStorageService:
    def __init__(self, storage_provider=None):
        self.communication_type = STORAGE_COMMUNICATION_TYPE  # sync/async/hybrid
        self.ipfs = IPFSFactory().get_storage()
```

**Режимы коммуникации:**
- **`sync`**: Прямые вызовы для Pinata, моков
- **`async`**: Через `asyncio.run()` для Arweave
- **`hybrid`**: Комбинированный подход

**Метод `download_json`:**
```python
def download_json(self, cid: str) -> Optional[Dict[str, Any]]:
    # Автоматически адаптируется к типу провайдера и режиму коммуникации
    if self.communication_type == "sync":
        if hasattr(self.ipfs, 'download_json'):
            return self.ipfs.download_json(cid)  # Прямой вызов
        else:
            return asyncio.run(self.ipfs.download_json_async(cid))  # Fallback
```

### 3. **Storage Layer** (`bot/services/core/storage/`)

#### **IPFSFactory** - Фабрика провайдеров
```python
class IPFSFactory:
    def __init__(self):
        self.set_storage(STORAGE_TYPE)  # pinata/arweave
        
    def set_storage(self, storage_type: str):
        if storage_type.lower() == 'pinata':
            self.storage = SecurePinataUploader()
        elif storage_type.lower() == 'arweave':
            self.storage = ArWeaveUploader()
```

#### **SecurePinataUploader** - Синхронный провайдер
```python
def download_json(self, cid: str) -> Optional[Dict]:
    url = f"{self.gateway_url}/{cid}"
    response = self._make_request('GET', url)
    return response.json()
```

**Особенности:**
- **Синхронные вызовы** - блокирующие операции
- **Rate limiting** - автоматические повторные попытки
- **Gateway URLs** - преобразование CID в HTTP URL

### 4. **Validation Layer** (`bot/validation/`)

#### **ValidationFactory** - Централизованная валидация
```python
class ValidationFactory:
    @classmethod
    def get_product_validator(cls) -> ProductValidator:
        if cls._product_validator is None:
            cls._product_validator = ProductValidator()
        return cls._product_validator
```

**Доступные валидаторы:**
- `CIDValidator` - валидация IPFS CID
- `ProductValidator` - валидация структуры продукта
- `PriceValidator` - валидация цен
- `ProportionValidator` - валидация пропорций

#### **ProductValidator** - Валидация продуктов
```python
class ProductValidator(ValidationRule[Dict[str, Any]]):
    def validate(self, value: Dict[str, Any]) -> ValidationResult:
        # Проверяем обязательные поля
        required_fields = ['business_id', 'title', 'cover_image_url', 'species', 'organic_components']
        for field in required_fields:
            if field not in value:
                return ValidationResult.failure(f"Отсутствует обязательное поле: {field}")
```

### 5. **Blockchain Layer** (`bot/services/core/blockchain.py`)

#### **BlockchainService** - Взаимодействие с смарт-контрактами
```python
class BlockchainService:
    def get_catalog_version(self) -> int:
        """Получает текущую версию каталога"""
        return self._call_contract_read_function(
            "ProductRegistry", "getMyCatalogVersion", 0
        )
    
    def get_all_products(self) -> List[dict]:
        """Получает все продукты из блокчейна"""
        product_ids = self._call_contract_read_function(
            "ProductRegistry", "getAllActiveProductIds", []
        )
        # Получаем полные данные для каждого продукта
        products = []
        for product_id in product_ids:
            product = self._call_contract_read_function(
                "ProductRegistry", "getProduct", None, product_id
            )
            if product:
                products.append(product)
        return products
```

## 🔄 **Поток данных каталога**

### **При запуске бота:**
```python
# bot/main.py
async def preload_catalog():
    await product_registry_service.get_all_products()
    logger.info("Фоновая загрузка каталога завершена!")

asyncio.create_task(preload_catalog())
```

### **При запросе каталога:**
1. **Проверка кэша** - `cache_service.get_cached_item("catalog", "catalog")`
2. **Валидация версии** - сравнение с `blockchain_service.get_catalog_version()`
3. **Загрузка из блокчейна** (если кэш устарел)
4. **Десериализация продуктов** - `_deserialize_product()`
5. **Обновление кэша** - `cache_service.set_cached_item()`

### **При десериализации продукта:**
1. **Загрузка метаданных** - `storage_service.download_json(ipfs_cid)`
2. **Валидация данных** - `validation_service.validate_product_data()`
3. **Создание объекта Product** - `Product.from_dict()`

## 🎨 **Форматирование для Telegram**

### **Структурированные функции форматирования:**
```python
def format_product_for_telegram(product, loc: Localization) -> Dict[str, str]:
    return {
        'main_info': format_main_info_ux(product, loc),
        'composition': format_composition_ux(product, loc),
        'pricing': format_pricing_ux(product, loc),
        'details': format_details_ux(product, loc)
    }
```

### **UX-оптимизированное отображение:**
- **🏷️ Название продукта** - самое важное
- **🌿 Вид продукта** - для понимания что это
- **✅ Статус** - активен ли для покупки
- **💰 Цены** - с валютами и весами
- **🌱 Органические компоненты** - состав продукта

## 🔧 **Конфигурация и настройки**

### **Переменные окружения:**
```bash
# .env
STORAGE_TYPE=pinata                    # pinata/arweave
STORAGE_COMMUNICATION_TYPE=sync        # sync/async/hybrid
PINATA_API_KEY=your_pinata_key
PINATA_SECRET_KEY=your_pinata_secret
ARWEAVE_PRIVATE_KEY=your_arweave_key
```

### **Настройка логирования:**
```python
# bot/config.py
LOG_LEVEL = "INFO"
LOG_FILE = "logs/amanita_api.log"
LOG_MAX_SIZE = 10 * 1024 * 1024  # 10MB
LOG_BACKUP_COUNT = 5
```

## 📊 **Метрики и производительность**

### **Время жизни кэша:**
- **Каталог**: 5 минут (часто обновляется)
- **Описания**: 24 часа (стабильные данные)
- **Изображения**: 12 часов (медиа-контент)

### **Стратегии оптимизации:**
1. **Фоновая загрузка** при старте бота
2. **Многоуровневое кэширование** в памяти
3. **Валидация версий** для инвалидации устаревших данных
4. **Адаптивные режимы коммуникации** с хранилищами

## 🚨 **Обработка ошибок**

### **Типы ошибок:**
- **StorageError** - проблемы с IPFS/Arweave
- **ValidationError** - невалидные данные
- **BlockchainError** - проблемы с блокчейном
- **CacheError** - проблемы с кэшированием

### **Стратегии восстановления:**
1. **Автоматические повторные попытки** для сетевых ошибок
2. **Fallback на альтернативные провайдеры**
3. **Очистка поврежденного кэша**
4. **Логирование всех ошибок** для диагностики

## 🔮 **Будущие улучшения**

### **Планируемые функции:**
1. **Кнопки действий** - "Подробнее", "В корзину"
2. **Детальный просмотр** продуктов с полной информацией
3. **Фильтрация и поиск** по категориям
4. **Пагинация** для больших каталогов
5. **Оффлайн-режим** с локальным кэшем

### **Технические улучшения:**
1. **Redis кэш** для распределенных систем
2. **CDN** для изображений
3. **WebSocket** для real-time обновлений
4. **GraphQL** для гибких запросов
5. **Микросервисная архитектура** для масштабирования

