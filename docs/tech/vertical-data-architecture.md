# Vertical Data Architecture — Вертикальная иерархия форматов данных

## Обзор

Документ описывает архитектурный подход к вертикальной иерархии форматов данных, реализованный для продуктов (Product) в социальной экономике Amanita. Этот подход будет использоваться для других объектов (Activity и др.).

**Вертикальная архитектура** — это система трансформации данных от минимального on-chain представления через обогащение и валидацию к полной бизнес-модели.

---

## Архитектурные принципы

### 1. Минимализм on-chain
- **Принцип**: Хранить в блокчейне только критичные данные и ссылки
- **Реализация**: Смарт-контракт хранит `id`, `seller`, `ipfsCID`, `active`, `componentIds[]`
- **Экономия газа**: Большие данные (метаданные, описания, изображения) хранятся off-chain

### 2. Обогащение через внешние источники
- **Принцип**: Данные обогащаются из реестров и хранилищ по мере необходимости
- **Реализация**: ComponentService загружает полные данные компонентов из OrganicComponentRegistry + Arweave
- **Локализация**: Мультиязычные описания загружаются через MultilingualIPFSService

### 3. Единая точка трансформации
- **Принцип**: Все трансформации данных происходят в одном месте (Assembler)
- **Реализация**: ProductAssembler координирует весь процесс сборки
- **Валидация**: Каждый этап валидируется через ValidationFactory

### 4. Неизменяемость структуры
- **Принцип**: Структура данных на каждом уровне четко определена
- **Реализация**: Типизированные модели (dataclass) с валидацией
- **Контракты**: Четкие интерфейсы между слоями

---

## Уровни архитектуры

### Уровень 1: Смарт-контракт (On-Chain)

**Файл**: `contracts/ProductRegistry.sol`

**Структура данных**:
```solidity
struct Product {
    uint256 id;          // Уникальный идентификатор товара
    address seller;      // Продавец (автор записи)
    string ipfsCID;     // Ссылка на JSON-описание (IPFS CID)
    bool active;        // Активен ли товар
}
```

**Особенности**:
- Минимальный набор данных для экономии газа
- Только ссылка на метаданные (CID), не сами данные
- Список `componentIds[]` хранится отдельно (в UUPS версии)
- Все операции чтения — `view` функции (бесплатные)

**Методы контракта**:
- `getProduct(uint256 productId)` → `Product`
- `getAllActiveProductIds()` → `uint256[]`
- `getProductsBySeller(address seller)` → `uint256[]`

---

### Уровень 2: Блокчейн-декодирование (Codec Layer)

**Файл**: `bot/services/core/contracts/product_registry_codec.py`

**Назначение**: Преобразование сырого кортежа из Web3 в типизированную структуру

**Структура данных**:
```python
@dataclass(frozen=True)
class ProductRegistryGetProduct:
    id: int
    seller: str
    business_id: str
    component_ids: list[str]
    metadata_cid: str
    active: bool
```

**Процесс декодирования**:
1. Получение сырого кортежа из `ProductRegistry.getProduct()`
2. Валидация структуры (ожидается 6 элементов для UUPS версии)
3. Преобразование типов (address → str, list → list[str])
4. Возврат типизированной структуры

**Обработка legacy**:
- Поддержка старого формата (4 элемента) через `allow_legacy=True`
- Автоматическое заполнение пустых полей для обратной совместимости

---

### Уровень 3: Загрузка метаданных (Storage Layer)

**Файл**: `bot/services/product/storage.py`

**Назначение**: Загрузка метаданных из IPFS/Arweave по CID

**Процесс**:
1. Получение CID из блокчейн-данных (`metadata_cid`)
2. Загрузка JSON из IPFS/Arweave через `ProductStorageService.download_json(cid)`
3. Возврат словаря с метаданными

**Структура метаданных** (пример):
```json
{
  "business_id": "product_001",
  "title": "Amanita Muscaria Dried",
  "organic_components": [
    {
      "component_id": "amanita_muscaria",
      "proportion": "100g"
    }
  ],
  "cover_image_url": "Qm...",
  "categories": ["mushrooms"],
  "forms": ["dried"],
  "species": "Amanita muscaria",
  "prices": [
    {
      "price": "50.00",
      "currency": "EUR",
      "quantity": "100",
      "unit": "g"
    }
  ]
}
```

**Особенности**:
- Метаданные содержат только ссылки на компоненты (`component_id`)
- Полные данные компонентов загружаются отдельно
- Поддержка мультиязычности через вложенные CID

---

### Уровень 4: Обогащение компонентов (Enrichment Layer)

**Файл**: `bot/services/product/assembler.py` → `_enrich_components()`

**Назначение**: Обогащение метаданных полными данными компонентов из реестра

**Процесс обогащения**:

#### Шаг 1: Извлечение ссылок на компоненты
```python
# Из метаданных извлекаем массив organic_components
for comp_ref in metadata['organic_components']:
    component_id = comp_ref['component_id']  # "amanita_muscaria"
    proportion = comp_ref['proportion']       # "100g"
```

#### Шаг 2: Загрузка полных данных компонента
```python
# ComponentService загружает из OrganicComponentRegistry + Arweave
registry_component = component_service.get_component_full(component_id)
# Возвращает OrganicComponent с полными данными:
# - scientific_title
# - forms
# - features
# - localizations
# - blockchain_id, creator, active, created_at
```

#### Шаг 3: Создание product component
```python
# Добавляем proportion к registry component
product_component = OrganicComponent.for_product(
    registry_component=registry_component,
    proportion=proportion
)
```

#### Шаг 4: Загрузка локализованного описания
```python
# Загружаем ComponentDescription для указанного языка
description = await component_service.get_component_description(
    component_id,
    language  # "ru", "en", etc.
)
# Добавляем к product_component
product_component.description = description
```

**Результат обогащения**:
```python
{
  "component_id": "amanita_muscaria",
  "proportion": "100g",
  "scientific_title": "Amanita muscaria",
  "forms": ["dried", "tincture", "powder"],
  "features": {...},
  "description": {
    "generic_description": "...",
    "effects": "...",
    "shamanic": "...",
    "warnings": "..."
  }
}
```

---

### Уровень 5: Сборка продукта (Assembly Layer)

**Файл**: `bot/services/product/assembler.py` → `assemble_product()`

**Назначение**: Координация всего процесса сборки продукта

**Процесс сборки**:

#### Шаг 1: Извлечение данных блокчейна
```python
blockchain_info = _extract_blockchain_data(blockchain_data)
# (product_id, seller, component_ids, ipfs_cid, is_active)
```

#### Шаг 2: Валидация метаданных
```python
validation_result = _validate_metadata(metadata)
# Использует ValidationFactory.get_product_validator()
```

#### Шаг 3: Валидация соответствия componentIds
```python
# Проверка соответствия componentIds из blockchain и organic_components из metadata
_validate_component_ids_match(component_ids, metadata)
```

#### Шаг 4: Обогащение компонентов
```python
enriched_metadata = await _enrich_components(metadata, language)
# Обогащает каждый компонент данными из реестра
```

#### Шаг 5: Создание объекта Product
```python
product = Product.from_dict(enriched_metadata)
# Создает типизированный объект с валидацией
```

#### Шаг 6: Установка блокчейн-данных
```python
_set_blockchain_data(product, product_id, ipfs_cid, is_active)
# Устанавливает blockchain_id, cid, status
```

---

### Уровень 6: Бизнес-модель (Model Layer)

**Файл**: `bot/model/product.py`

**Структура данных**:
```python
@dataclass
class Product:
    business_id: str
    blockchain_id: Union[int, str]
    status: int
    cid: str
    title: str
    organic_components: List[OrganicComponent]
    cover_image_url: str
    categories: List[str]
    forms: List[str]
    species: str
    prices: List[PriceInfo]
```

**Вложенные модели**:

#### OrganicComponent
```python
@dataclass
class OrganicComponent:
    component_id: str
    scientific_title: Optional[str]
    forms: Optional[List[str]]
    features: Optional[Dict]
    localizations: Optional[Dict]
    blockchain_id: Optional[int]
    creator: Optional[str]
    active: Optional[bool]
    created_at: Optional[int]
    proportion: Optional[str]  # Только для product usage
    description: Optional[ComponentDescription]
```

#### PriceInfo
```python
@dataclass
class PriceInfo:
    price: Union[int, float, str, Decimal]
    currency: str
    quantity: Optional[Union[int, float, str]]
    unit: Optional[str]
    form: Optional[str]
```

**Валидация**:
- Автоматическая валидация через `__post_init__()`
- Использование `ValidationFactory` для единообразной валидации
- Проверка обязательных полей и форматов

---

## Поток данных (Data Flow)

### Полный цикл от блокчейна до модели

```
┌─────────────────────────────────────────────────────────────┐
│ 1. Смарт-контракт ProductRegistry                           │
│    struct Product { id, seller, ipfsCID, active }          │
│    + componentIds[] (в UUPS версии)                        │
└────────────────────┬──────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. BlockchainService.get_product()                          │
│    → Web3 вызов ProductRegistry.getProduct(id)            │
│    → Возвращает сырой кортеж (tuple)                       │
└────────────────────┬──────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. ProductRegistryCodec.decode_get_product_tuple()         │
│    → Валидация структуры (6 элементов для UUPS)             │
│    → Преобразование типов (address → str)                  │
│    → ProductRegistryGetProduct(id, seller, business_id,   │
│       component_ids, metadata_cid, active)                 │
└────────────────────┬──────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. ProductStorageService.download_json(metadata_cid)         │
│    → Загрузка JSON из IPFS/Arweave по CID                   │
│    → Возврат словаря с метаданными                         │
└────────────────────┬──────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ 5. ProductAssembler.assemble_product()                     │
│    ├─ _extract_blockchain_data()                           │
│    ├─ _validate_metadata()                                 │
│    ├─ _validate_component_ids_match()                      │
│    ├─ _enrich_components() ────────────────┐              │
│    │   ├─ component_service.get_component_full()          │
│    │   │   → OrganicComponentRegistry + Arweave          │
│    │   ├─ OrganicComponent.for_product()                 │
│    │   └─ component_service.get_component_description()   │
│    │       → MultilingualIPFSService                      │
│    ├─ Product.from_dict(enriched_metadata)                │
│    └─ _set_blockchain_data()                              │
└────────────────────┬──────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ 6. Product (финальная модель)                               │
│    → Полностью обогащенный объект с валидацией             │
│    → Готов для использования в бизнес-логике                │
└─────────────────────────────────────────────────────────────┘
```

---

## Ключевые паттерны

### 1. Factory Method для компонентов

**Паттерн**: `OrganicComponent.for_product()`

**Назначение**: Создание product component из registry component + proportion

**Использование**:
```python
registry_component = component_service.get_component_full("amanita_muscaria")
product_component = OrganicComponent.for_product(
    registry_component=registry_component,
    proportion="100g"
)
```

**Преимущества**:
- Четкое разделение registry component и product component
- Единая точка создания product components
- Валидация пропорции при создании

---

### 2. Enrichment Pattern

**Паттерн**: Обогащение данных из внешних источников

**Реализация**:
- Метаданные содержат только ссылки (`component_id`)
- Assembler загружает полные данные из реестра
- Обогащение происходит асинхронно (async/await)

**Преимущества**:
- Разделение ответственности (метаданные vs реестр)
- Переиспользование данных компонентов
- Локализация по требованию

---

### 3. Validation Factory

**Паттерн**: Единая система валидации через `ValidationFactory`

**Использование**:
```python
cid_validator = ValidationFactory.get_cid_validator()
proportion_validator = ValidationFactory.get_proportion_validator()
product_validator = ValidationFactory.get_product_validator()
```

**Преимущества**:
- Единообразие валидации
- Централизованное управление правилами
- Легкое тестирование

---

### 4. Codec Pattern

**Паттерн**: Декодирование сырых данных блокчейна в типизированные структуры

**Реализация**:
- `ProductRegistryCodec` преобразует tuple → `ProductRegistryGetProduct`
- Валидация структуры перед преобразованием
- Поддержка legacy форматов

**Преимущества**:
- Типобезопасность
- Обработка изменений ABI
- Единая точка декодирования

---

## Валидация на каждом уровне

### Уровень 1: Смарт-контракт
- Проверка существования продукта (`product.id != 0`)
- Модификаторы доступа (`onlyOwnSellerProduct`)

### Уровень 2: Codec
- Валидация структуры кортежа (ожидается 6 элементов)
- Проверка типов данных

### Уровень 3: Storage
- Валидация CID перед загрузкой
- Проверка наличия метаданных

### Уровень 4: Assembler
- Валидация метаданных через `ValidationFactory`
- Проверка соответствия `componentIds` между blockchain и metadata
- Валидация обогащенных компонентов

### Уровень 5: Model
- Автоматическая валидация в `__post_init__()`
- Проверка обязательных полей
- Валидация форматов (CID, пропорции, цены)

---

## Применение для других объектов

### Activity (будущая реализация)

**Аналогичная структура**:

1. **Смарт-контракт**: `ActivityRegistry.sol`
   - Минимальные данные: `id`, `creator`, `ipfsCID`, `active`
   - Ссылки на связанные объекты (если нужны)

2. **Codec**: `activity_registry_codec.py`
   - Декодирование кортежа из контракта
   - Типизированная структура `ActivityRegistryGetActivity`

3. **Storage**: Использует существующий `ProductStorageService`
   - Загрузка метаданных по CID

4. **Assembler**: `ActivityAssembler`
   - Обогащение через внешние сервисы (если нужны)
   - Валидация метаданных
   - Создание объекта `Activity`

5. **Model**: `bot/model/activity.py`
   - Типизированная модель `Activity`
   - Валидация через `ValidationFactory`

**Ключевые отличия**:
- Activity может не требовать обогащения компонентов
- Может иметь другие связанные объекты (участники, события)
- Может иметь другую структуру метаданных

---

## Преимущества архитектуры

### 1. Масштабируемость
- Легко добавлять новые уровни обогащения
- Поддержка новых источников данных без изменения модели

### 2. Производительность
- Минимальные данные on-chain (экономия газа)
- Кэширование на уровне ComponentService
- Ленивая загрузка описаний (только при необходимости)

### 3. Гибкость
- Поддержка legacy форматов через codec
- Мультиязычность через MultilingualIPFSService
- Расширяемость моделей без изменения контрактов

### 4. Надежность
- Валидация на каждом уровне
- Обработка ошибок с graceful degradation
- Типобезопасность через типизированные модели

### 5. Тестируемость
- Четкое разделение ответственности
- Легко мокировать внешние зависимости
- Единая система валидации

---

## Ограничения и соображения

### 1. Зависимость от внешних источников
- **Проблема**: Метаданные и компоненты загружаются из IPFS/Arweave
- **Решение**: Кэширование и graceful degradation при недоступности

### 2. Асинхронность
- **Проблема**: Обогащение требует async операций
- **Решение**: Использование async/await на всех уровнях

### 3. Валидация соответствия
- **Проблема**: `componentIds` из blockchain могут не совпадать с metadata
- **Решение**: Валидация соответствия с предупреждениями (не блокирует сборку)

### 4. Legacy поддержка
- **Проблема**: Старые форматы данных требуют специальной обработки
- **Решение**: Codec с поддержкой legacy через `allow_legacy=True`

---

## Примеры использования

### Пример 1: Загрузка продукта по ID

```python
# 1. Получение данных из блокчейна
blockchain_data = blockchain_service.get_product_structured(product_id)

# 2. Загрузка метаданных
metadata = storage_service.download_json(blockchain_data.metadata_cid)

# 3. Сборка продукта
product = await assembler.assemble_product(
    blockchain_data=(blockchain_data.id, blockchain_data.seller, 
                     blockchain_data.component_ids, 
                     blockchain_data.metadata_cid, 
                     blockchain_data.active),
    metadata=metadata,
    language="ru"
)
```

### Пример 2: Обогащение компонентов

```python
# Внутри ProductAssembler._enrich_components()
for comp_ref in metadata['organic_components']:
    component_id = comp_ref['component_id']
    proportion = comp_ref['proportion']
    
    # Загрузка полных данных компонента
    registry_component = component_service.get_component_full(component_id)
    
    # Создание product component
    product_component = OrganicComponent.for_product(
        registry_component=registry_component,
        proportion=proportion
    )
    
    # Загрузка описания
    description = await component_service.get_component_description(
        component_id, 
        language
    )
    product_component.description = description
```

---

## Заключение

Вертикальная архитектура данных обеспечивает:

1. **Эффективность**: Минимальные данные on-chain, обогащение по требованию
2. **Гибкость**: Легко расширять и добавлять новые источники данных
3. **Надежность**: Валидация на каждом уровне, обработка ошибок
4. **Переиспользование**: Единый подход для разных объектов (Product, Activity, etc.)

Этот подход может быть применен к любым объектам в системе, требующим обогащения данных из внешних источников.

---

## Связанные документы

- `contracts/ProductRegistry.sol` — Смарт-контракт реестра продуктов
- `bot/model/product.py` — Модель продукта
- `bot/services/product/assembler.py` — Сборщик продуктов
- `bot/services/product/component_service.py` — Сервис компонентов
- `bot/services/core/contracts/product_registry_codec.py` — Декодер данных блокчейна

---

**Версия**: 1.0  
**Дата**: 2026-01-27  
**Автор**: Анализ архитектуры на основе кода проекта Amanita
