# ProductRegistryService - Сервис реестра продуктов

## Обзор

`ProductRegistryService` - центральный сервис для работы с продуктами в системе AMANITA. Координирует создание, управление и получение продуктов через блокчейн и IPFS.

## Архитектура

### Зависимости сервиса

```python
class ProductRegistryService:
    def __init__(self, 
                 blockchain_service: BlockchainService,
                 storage_service: ProductStorageService,
                 validation_service: ProductValidationService,
                 account_service: AccountService):
        self.blockchain_service = blockchain_service
        self.storage_service = storage_service
        self.validation_service = validation_service
        self.account_service = account_service
        self.cache_service = ProductCacheService()
        self.metadata_service = ProductMetadataService(storage_service)
```

### Компоненты системы

- **BlockchainService** - взаимодействие с ProductRegistry контрактом
- **ProductStorageService** - загрузка/скачивание из IPFS
- **ProductValidationService** - валидация данных продуктов
- **ProductCacheService** - кэширование каталога и метаданных
- **ProductMetadataService** - обработка метаданных продуктов
- **AccountService** - управление аккаунтами продавцов

## Основные методы

### Создание продукта

```python
async def create_product(self, product_data: dict) -> dict:
    """
    Создает новый продукт: валидация → метаданные → IPFS → блокчейн
    """
```

**Процесс:**
1. **Валидация** - проверка обязательных полей и форматов
2. **Метаданные** - создание структурированных метаданных
3. **IPFS** - загрузка метаданных в IPFS
4. **Блокчейн** - создание записи в ProductRegistry контракте
5. **ID** - получение blockchain_id из транзакции

**Возвращает:**
```python
{
    "id": "product_id",
    "metadata_cid": "Qm...",
    "blockchain_id": "42",
    "tx_hash": "0x...",
    "status": "success",
    "error": None
}
```

### Получение каталога

```python
def get_all_products(self) -> List[Product]:
    """
    Получает все продукты с кэшированием
    """
```

**Логика:**
1. Проверка версии каталога в блокчейне
2. Проверка кэша (TTL: 5 минут)
3. Загрузка из блокчейна при необходимости
4. Обработка метаданных через IPFS
5. Обновление кэша

### Получение продукта

```python
def get_product(self, product_id: Union[str, int]) -> Optional[Product]:
    """
    Получает продукт по ID
    """
```

### Обновление продукта

```python
async def update_product(self, product_id: str, product_data: dict) -> dict:
    """
    Полное обновление продукта (только владелец)
    """
```

**Проверки:**
- Существование продукта
- Права доступа (владелец)
- Валидация новых данных
- Обновление метаданных в IPFS

### Управление статусами

```python
async def update_product_status(self, product_id: int, new_status: int) -> bool
async def deactivate_product(self, product_id: int) -> bool
```

## Кэширование

### Стратегия кэширования

```python
CACHE_TTL = {
    'catalog': timedelta(minutes=5),      # Каталог продуктов
    'description': timedelta(hours=24),   # Описания
    'image': timedelta(hours=12)          # Изображения
}
```

### Методы кэширования

```python
def clear_cache(self, cache_type: Optional[str] = None)
def _get_cached_description(self, description_cid: str) -> Optional[Description]
def _get_cached_image(self, image_cid: str) -> Optional[str]
```

## Валидация данных

### Обязательные поля продукта

```python
required_fields = [
    'title',           # Название продукта
    'description_cid', # CID описания в IPFS
    'categories',      # Список категорий
    'cover_image',     # CID изображения
    'form',           # Форма выпуска
    'species',        # Вид растения/гриба
    'prices'          # Список цен
]
```

### Валидация цен

```python
# Поддерживаемые валюты
currencies = ['EUR', 'USD']

# Поддерживаемые единицы
weight_units = ['g', 'kg']
volume_units = ['ml', 'l']

# Структура цены
{
    "weight": "100",
    "weight_unit": "g", 
    "price": "30",
    "currency": "EUR"
}
```

### Валидация CID

```python
IPFS_CID_PATTERN = r'^(Qm[1-9A-HJ-NP-Za-km-z]{44}|bafy[A-Za-z2-7]{55})$'
```

## Обработка метаданных

### Структура метаданных

```python
metadata = {
    "id": "product_id",
    "title": "Название продукта",
    "description_cid": "Qm...",
    "cover_image": "Qm...",
    "categories": ["категория1", "категория2"],
    "form": "powder",
    "species": "Amanita muscaria",
    "prices": [
        {
            "weight": "100",
            "weight_unit": "g",
            "price": "30",
            "currency": "EUR"
        }
    ],
    "created_at": "2024-01-01T00:00:00Z"
}
```

### Обработка метаданных

```python
def _process_product_metadata(self, product_id, ipfs_cid, active) -> Optional[Product]:
    """
    Обрабатывает метаданные продукта из IPFS
    """
```

**Процесс:**
1. Валидация CID
2. Загрузка JSON из IPFS
3. Обработка описания (description_cid)
4. Обработка изображений (cover_image, gallery)
5. Обработка цен
6. Создание объекта Product

## Обработка ошибок

### Типы ошибок

- **ValidationError** - ошибки валидации данных
- **BlockchainError** - ошибки взаимодействия с блокчейном
- **StorageError** - ошибки IPFS хранилища
- **CacheError** - ошибки кэширования

### Стратегия обработки

```python
try:
    result = await self.some_operation()
    return result
except ValidationError as e:
    self.logger.error(f"Validation error: {e}")
    return {"status": "error", "error": str(e)}
except Exception as e:
    self.logger.error(f"Unexpected error: {e}")
    return {"status": "error", "error": str(e)}
```

## Логирование

### Уровни логирования

- **INFO** - основные операции (создание, получение продуктов)
- **WARNING** - потенциальные проблемы (устаревший кэш, отсутствующие описания)
- **ERROR** - ошибки операций с детальной трассировкой

### Ключевые события

```python
# Создание продукта
self.logger.info(f"[ProductRegistry] Создание продукта в смарт-контракте с CID: {ipfs_cid}")

# Получение каталога
self.logger.info(f"[ProductRegistry] Текущая версия каталога: {catalog_version}")

# Обработка метаданных
self.logger.info(f"[ProductRegistry] Обработка метаданных продукта {product_id}")
```

## Использование

### Базовый пример

```python
# Создание сервиса
registry = ProductRegistryService(
    blockchain_service=blockchain_service,
    storage_service=storage_service,
    validation_service=validation_service,
    account_service=account_service
)

# Создание продукта
product_data = {
    "id": "amanita_powder_001",
    "title": "Amanita Muscaria Powder",
    "description_cid": "QmDescriptionCID123",
    "categories": ["mushroom", "powder"],
    "cover_image": "QmImageCID123",
    "form": "powder",
    "species": "Amanita muscaria",
    "prices": [{"weight": "100", "weight_unit": "g", "price": "80", "currency": "EUR"}]
}

result = await registry.create_product(product_data)
print(f"Product created: {result}")

# Получение каталога
products = registry.get_all_products()
print(f"Total products: {len(products)}")

# Получение продукта
product = registry.get_product("amanita_powder_001")
print(f"Product: {product.title}")
```

### Обработка ошибок

```python
result = await registry.create_product(product_data)
if result["status"] == "error":
    print(f"Error: {result['error']}")
    # Обработка ошибки
else:
    print(f"Success: {result['blockchain_id']}")
```

## Ограничения и особенности

### Текущие ограничения

1. **Обновление метаданных** - не реализовано в блокчейне (TODO: TASK-002.2)
2. **Права доступа** - только владелец может обновлять продукт
3. **Валюты** - поддерживаются только EUR и USD
4. **IPFS провайдеры** - Pinata и ArWeave

### Производительность

- **Кэш каталога** - 5 минут TTL
- **Кэш описаний** - 24 часа TTL
- **Кэш изображений** - 12 часов TTL
- **Асинхронные операции** - создание и обновление продуктов

### Безопасность

- **Валидация входных данных** - все поля проверяются
- **Права доступа** - проверка владельца продукта
- **CID валидация** - проверка формата IPFS CID
- **Логирование** - все операции логируются

## Заключение

`ProductRegistryService` обеспечивает полный цикл управления продуктами в системе AMANITA:

- ✅ Создание продуктов с валидацией
- ✅ Получение каталога с кэшированием
- ✅ Обновление продуктов (владелец)
- ✅ Управление статусами
- ✅ Интеграция с блокчейном и IPFS
- ✅ Обработка ошибок и логирование

Сервис готов к production использованию и поддерживает основные операции с продуктами. 