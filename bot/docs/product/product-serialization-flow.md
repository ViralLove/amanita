# 🔄 Сериализация и Десериализация Продуктов: Полный Поток

## 🎯 Обзор архитектуры

Продукты в системе Amanita хранятся в **трех источниках данных**:

1. **Blockchain (ProductRegistry)** — on-chain структура `Product`: `id`, `seller`, `businessId`, `componentIds[]`, `metadataCID`, `active`
2. **Arweave (метаданные)** — описание продукта без дублирования компонентов (название, формы, цены, ссылки на `component_id`)
3. **OrganicComponentRegistry (blockchain)** — централизованный реестр компонентов

**Десериализация** = преобразование blockchain + Arweave → Python модель `Product`

---

## 📊 ДИАГРАММА 1: Общий поток десериализации

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                        ИСТОЧНИКИ ДАННЫХ                                       │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                               │
│  ┌─────────────────┐     ┌──────────────────┐     ┌────────────────────┐    │
│  │  ProductRegistry│     │     Arweave      │     │ ComponentRegistry  │    │
│  │   (Blockchain)  │     │   (метаданные)   │     │   (Blockchain)     │    │
│  └────────┬────────┘     └────────┬─────────┘     └─────────┬──────────┘    │
│           │                       │                          │                │
│           │ (id, seller,          │ JSON метаданные          │ Component      │
│           │  businessId,          │ продукта (без компонентов│ полные данные  │
│           │  componentIds[],      │ внутри, только ссылки)   │                │
│           │  metadataCID, active) │                          │                │
└───────────┼───────────────────────┼──────────────────────────┼────────────────┘
            │                       │                          │
            ▼                       ▼                          │
   ┌─────────────────────────────────────────────────────┐    │
   │         ProductRegistryService                       │    │
   │  (Координатор: загружает продукты из blockchain)    │    │
   └─────────────────┬───────────────────────────────────┘    │
                     │                                         │
                     ▼                                         │
   ┌─────────────────────────────────────────────────────┐    │
   │            ProductAssembler                          │    │
   │  (Оркестратор: собирает Product из частей)          │    │
   │                                                      │    │
   │  1. Получает blockchain_data + metadata              │    │
   │  2. Определяет формат (SINGLE/MULTI)                 │    │
   │  3. Обогащает данными из ComponentRegistry ─────────────┤
   │  4. Валидирует обогащенные метаданные               │    │
   │  5. Создает Product объект                           │    │
   └─────────────────┬───────────────────────────────────┘    │
                     │                                         │
                     │                          ┌──────────────▼──────────────┐
                     │                          │   ComponentService          │
                     │                          │  (Загрузка компонентов)     │
                     │                          │                             │
                     │                          │  - get_component_full()     │
                     │                          │  - Кэширование (TTL + LRU)  │
                     │                          │  - Blockchain + Arweave     │
                     │                          └─────────────────────────────┘
                     ▼
   ┌─────────────────────────────────────────────────────┐
   │              Product (Python модель)                 │
   │                                                      │
   │  - business_id: str                                  │
   │  - blockchain_id: int                                │
   │  - organic_components: List[OrganicComponent]        │
   │  - title, categories, forms, species, prices, ...    │
   └──────────────────────────────────────────────────────┘
```

---

## 📊 ДИАГРАММА 2: Детальный поток для SINGLE продукта

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  ПРИМЕР: Blue Lotus Tincture (SINGLE формат)                                │
└─────────────────────────────────────────────────────────────────────────────┘

ШАГ 1: Blockchain запрос
──────────────────────────
ProductRegistry.getProduct(42)
    ↓
blockchain_data = {
    "id": 42,
    "seller": "0xSeller...",
    "businessId": "blue_lotus_tincture",
    "componentIds": ["blue_lotus"],
    "metadataCID": "ar://xyz123",
    "active": true
}

ШАГ 2: Загрузка метаданных из Arweave
───────────────────────────────────────
Arweave.download("ar://xyz123")
    ↓
metadata = {
  "business_id": "blue_lotus_tincture",
  "title": "Blue Lotus Tincture",
  "component_id": "blue_lotus",        ← КЛЮЧ: component_id на корне (SINGLE)
  "proportion": "100%",
  "form": "tincture",
  "categories": ["flowers", "tinctures"],
  "species": ["Nymphaea caerulea"],
  "prices": [{"quantity": 50, "unit": "ml", "price": 20, "currency": "EUR"}]
}

ШАГ 3: ProductAssembler — определение формата
───────────────────────────────────────────────
assembler._detect_product_format(metadata)
    ↓
Видит: 'component_id' на корневом уровне
    ↓
Формат: SINGLE

> Важно: _componentIds_ уже есть в `blockchain_data`. Метаданные служат только для определения формата/пропорций, но список компонентов берётся из смарт-контракта.

ШАГ 4: ProductAssembler — обогащение
─────────────────────────────────────
assembler._enrich_single_component(metadata)  # внутри использует componentIds из blockchain_data
    ↓
┌───────────────────────────────────────────────────────────────┐
│ Вызов ComponentService.get_component_full("blue_lotus")       │
│                                                               │
│  Подпоток:                                                    │
│  1. Берёт `componentIds` из blockchain_data (`["blue_lotus"]`) │
│     и для каждого вызывает OrganicComponentRegistry.getComponent│
│     (здесь `getComponent("blue_lotus")`)                       │
│     → blockchain_tuple = (7, "blue_lotus", "0xCreator", ...) │
│                                                               │
│  2. Arweave.download(rootMetadataCID)                         │
│     → component_metadata = {                                  │
│         "biounit_id": "blue_lotus",                           │
│         "scientific_title": "Nymphaea caerulea",              │
│         "forms": ["dried", "tincture"],                       │
│         "features": {"common": ["relaxation", "meditation"]}  │
│       }                                                       │
│                                                               │
│  3. OrganicComponent.from_registry(blockchain, metadata)      │
│     → registry_component (полный объект из реестра)           │
└───────────────────────────────────────────────────────────────┘
    ↓
OrganicComponent.for_product(registry_component, proportion="100%")
    ↓
product_component = {
  "component_id": "blue_lotus",
  "scientific_title": "Nymphaea caerulea",
  "forms": ["dried", "tincture"],
  "features": {"common": ["relaxation", "meditation"]},
  "proportion": "100%"                    ← Из метаданных продукта
}
    ↓
enriched_metadata = {
  "business_id": "blue_lotus_tincture",
  "title": "Blue Lotus Tincture",
  "component_id": "blue_lotus",           ← Сохранено из исходных
  "proportion": "100%",                   ← Сохранено из исходных
  "organic_components": [                 ← ДОБАВЛЕНО
    {product_component полный объект}
  ],
  ...все остальные поля...
}

ШАГ 5: Валидация обогащенных метаданных
────────────────────────────────────────
assembler._validate_product_metadata(enriched_metadata)
    ↓
Проверки:
  ✅ business_id, title, categories, forms, species
  ✅ organic_components массив существует и не пуст
  ✅ component_id, proportion в компонентах
  ✅ scientific_title появился (обогащение сработало)

ШАГ 6: Создание Python объекта
───────────────────────────────
Product.from_dict(enriched_metadata)
    ↓
product = Product(
  business_id="blue_lotus_tincture",
  blockchain_id=42,                       ← Из blockchain_data
  status=1,                               ← Из blockchain_data (active=true)
  cid="ar://xyz123",                      ← Из blockchain_data
  title="Blue Lotus Tincture",
  organic_components=[
    OrganicComponent(
      component_id="blue_lotus",
      scientific_title="Nymphaea caerulea",
      forms=["dried", "tincture"],
      features={"common": ["relaxation", "meditation"]},
      proportion="100%"
    )
  ],
  categories=["flowers", "tinctures"],
  forms=["tincture"],
  species=["Nymphaea caerulea"],
  prices=[PriceInfo(...)]
)

ГОТОВО: Python модель Product готова к использованию в боте! ✅
```

---

## 📊 ДИАГРАММА 3: Детальный поток для MULTI продукта

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  ПРИМЕР: Relaxation Blend (MULTI формат)                                    │
└─────────────────────────────────────────────────────────────────────────────┘

ШАГ 1-2: Blockchain + Arweave
─────────────────────────────

```text
blockchain_data = {
  "id": 101,
  "seller": "0xSeller...",
  "businessId": "relaxation_blend",
  "componentIds": ["amanita_muscaria", "lions_mane", "passionflower"],
  "metadataCID": "ar://relaxation-blend",
  "active": true
}
```

```json
metadata = {
  "business_id": "relaxation_blend",
  "title": "Relaxation Blend",
  "organic_components": [
    {"component_id": "amanita_muscaria", "proportion": "50g"},
    {"component_id": "lions_mane", "proportion": "30g"},
    {"component_id": "passionflower", "proportion": "20g"}
  ],
  "categories": ["mushrooms", "blends"],
  "forms": ["powder"]
}
```

ШАГ 3: ProductAssembler — определение формата
───────────────────────────────────────────────
assembler._detect_product_format(metadata)
    ↓
Видит: 'organic_components' массив с 'component_id'
    ↓
Формат: MULTI

> Здесь `blockchain_data.componentIds = ["amanita_muscaria", ...]` — они служат входом для ComponentService; массив `organic_components` в metadata лишь сообщает пропорции/формы.

ШАГ 4: ProductAssembler — обогащение (ИТЕРАЦИЯ)
─────────────────────────────────────────────────
assembler._enrich_multi_component(metadata)  # берёт componentIds из blockchain_data
    ↓
Для КАЖДОГО componentId из `blockchain_data.componentIds`:

┌─────────────────────────────────────────────────────────────┐
│ [1/3] component_id="amanita_muscaria", proportion="50g"     │
│                                                             │
│  ComponentService.get_component_full("amanita_muscaria")    │
│      ↓                                                      │
│  registry_component (из реестра + кэш)                      │
│      ↓                                                      │
│  OrganicComponent.for_product(registry, proportion="50g")   │
│      ↓                                                      │
│  enriched[0] = {                                            │
│    "component_id": "amanita_muscaria",                      │
│    "scientific_title": "Amanita muscaria",                  │
│    "proportion": "50g",                                     │
│    "forms": [...], "features": {...}                        │
│  }                                                          │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ [2/3] component_id="lions_mane", proportion="30g"           │
│                                                             │
│  ComponentService.get_component_full("lions_mane")          │
│      ↓                                                      │
│  registry_component (из кэша или реестра)                   │
│      ↓                                                      │
│  OrganicComponent.for_product(registry, proportion="30g")   │
│      ↓                                                      │
│  enriched[1] = {                                            │
│    "component_id": "lions_mane",                            │
│    "scientific_title": "Hericium erinaceus",                │
│    "proportion": "30g",                                     │
│    "forms": [...], "features": {...}                        │
│  }                                                          │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ [3/3] component_id="passionflower", proportion="20g"        │
│                                                             │
│  ComponentService.get_component_full("passionflower")       │
│      ↓                                                      │
│  registry_component (из кэша или реестра)                   │
│      ↓                                                      │
│  OrganicComponent.for_product(registry, proportion="20g")   │
│      ↓                                                      │
│  enriched[2] = {                                            │
│    "component_id": "passionflower",                         │
│    "scientific_title": "Passiflora incarnata",              │
│    "proportion": "20g",                                     │
│    "forms": [...], "features": {...}                        │
│  }                                                          │
└─────────────────────────────────────────────────────────────┘
    ↓
enriched_metadata = {
  "business_id": "relaxation_blend",
  "organic_components": [enriched[0], enriched[1], enriched[2]]
  ...
}

ШАГ 5-6: Валидация + Создание (аналогично SINGLE)
───────────────────────────────────────────────────

product = Product(
  business_id="relaxation_blend",
  organic_components=[
    OrganicComponent(amanita_muscaria, 50g),
    OrganicComponent(lions_mane, 30g),
    OrganicComponent(passionflower, 20g)
  ],
  ...
)
```

---

## 📊 ДИАГРАММА 4: Слои абстракции (детально)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ СЛОЙ 1: ХРАНИЛИЩА (Blockchain + Arweave)                                    │
└─────────────────────────────────────────────────────────────────────────────┘

ProductRegistry (Solidity Contract)
├─ mapping(uint256 => Product) products
│  struct Product {
│    uint256 id;
│    address seller;
│    string businessId;
│    string[] componentIds;
│    string metadataCID;    ← CID метаданных продукта (без компонентов внутри)
│    bool active;
│  }

OrganicComponentRegistry (Solidity Contract)
├─ mapping(string => Component) components
│  struct Component {
│    uint256 id;
│    string componentId;
│    address creator;
│    string rootMetadataCID;  ← CID метаданных компонента в Arweave
│    bool active;
│    uint256 createdAt;
│  }

Arweave (Permanent Storage)
├─ Product Metadata JSON
│  {
│    "business_id": "...",
│    "title": "...",
│    "component_id": "..." (SINGLE) или
│    "organic_components": [...] (MULTI)
│  }
│
├─ Component Metadata JSON
│  {
│    "biounit_id": "...",
│    "scientific_title": "...",
│    "forms": [...],
│    "features": {...}
│  }

┌─────────────────────────────────────────────────────────────────────────────┐
│ СЛОЙ 2: СЕРВИСЫ (Python Backend)                                            │
└─────────────────────────────────────────────────────────────────────────────┘

BlockchainService
├─ get_all_products() → List[Tuple]
│  Вызывает: ProductRegistry.getAllProducts()
│  Возвращает: [(id, seller, businessId, componentIds[], metadataCID, active), ...]
│
└─ get_component(component_id) → Tuple
   Вызывает: OrganicComponentRegistry.getComponent(componentId)
   Возвращает: (id, componentId, creator, rootMetadataCID, active, createdAt)

ProductStorageService
├─ download_json(cid) → Dict
│  Загружает JSON из Arweave по CID
│  Парсит в Python dict

ComponentService (NEW)
├─ get_component_full(component_id) → OrganicComponent
│  │
│  ├─ Проверяет кэш (TTL + LRU)
│  ├─ BlockchainService.get_component(component_id) → blockchain_tuple
│  ├─ ProductStorageService.download_json(rootMetadataCID) → metadata
│  └─ OrganicComponent.from_registry(blockchain_tuple, metadata)
│
└─ Кэширование: {component_id: (component, cached_at)}

ProductAssembler (NEW архитектура)
├─ assemble_product(blockchain_data, metadata) → Product
│  │
│  ├─ _extract_blockchain_data(blockchain_data) → (id, businessId, componentIds[], metadataCID, active)
│  ├─ _validate_metadata(metadata) → bool
│  ├─ _create_product_from_metadata(metadata) → Product
│  │   │
│  │   ├─ _detect_product_format(metadata) → "SINGLE" или "MULTI"
│  │   ├─ if SINGLE: _enrich_single_component(metadata) ← использует `componentIds` из blockchain_data
│  │   │   └─ ComponentService.get_component_full(component_id)
│  │   ├─ if MULTI: _enrich_multi_component(metadata) ← итерация по `componentIds`
│  │   │   └─ ComponentService.get_component_full() для каждого component_id
│  │   ├─ _validate_product_metadata(enriched)
│  │   └─ Product.from_dict(enriched)
│  │
│  └─ _set_blockchain_data(product, id, businessId, componentIds[], metadataCID, active)

┌─────────────────────────────────────────────────────────────────────────────┐
│ СЛОЙ 3: МОДЕЛИ (Python Dataclasses)                                         │
└─────────────────────────────────────────────────────────────────────────────┘

@dataclass
class OrganicComponent:
    component_id: str
    scientific_title: Optional[str]
    forms: List[str]
    features: Dict[str, List[str]]
    proportion: Optional[str]           ← Для product components
    blockchain_id: Optional[int]        ← Для registry components
    creator: Optional[str]              ← Для registry components
    ...
    
    @classmethod from_registry(blockchain_tuple, metadata)
    @classmethod for_product(registry_component, proportion)

@dataclass
class Product:
    business_id: str
    blockchain_id: int
    organic_components: List[OrganicComponent]
    title: str
    categories: List[str]
    forms: List[str]
    species: str
    prices: List[PriceInfo]
    ...
    
    @classmethod from_dict(data: Dict)
```

---

## 📊 ДИАГРАММА 5: Полный End-to-End поток

```
┌──────────────────────────────────────────────────────────────────────────────┐
│  Telegram Bot: Пользователь запрашивает каталог                              │
└──────────────────────────────────────────────────────────────────────────────┘
                              ↓
         ┌────────────────────────────────────────┐
         │  ProductRegistryService                │
         │  .get_all_products()                   │
         └────────┬───────────────────────────────┘
                  │
                  ├─ blockchain_service.get_all_products()
                  │      ↓
                  │  [
                  │    (1, "0xSeller1", "prod_blue_lotus", ["blue_lotus"], "ar://prod1", true),
                  │    (2, "0xSeller2", "prod_relaxation", ["amanita_muscaria","lions_mane"], "ar://prod2", true),
                  │    ...
                  │  ]
                  │
                  ├─ ДЛЯ КАЖДОГО продукта:
                  │  │
                  │  ├─ storage_service.download_json("ar://prod1")
                  │  │      ↓
                  │  │  {metadata продукта}
                  │  │
                  │  └─ assembler.assemble_product(blockchain_data, metadata)
                  │         ↓
                  │     ┌─────────────────────────────────────────────┐
                  │     │  ProductAssembler.assemble_product()        │
                  │     ├─────────────────────────────────────────────┤
                  │     │                                             │
                  │     │ ШАГ 1: Extract blockchain data              │
                  │     │   (id, businessId, componentIds[],          │
                  │     │    metadataCID, active)                     │
                  │     │                                             │
                  │     │ ШАГ 2: Validate base metadata               │
                  │     │   ValidationFactory.validate()              │
                  │     │                                             │
                  │     │ ШАГ 3: Create Product                       │
                  │     │   ↓                                         │
                  │     │ ┌─────────────────────────────────────────┐ │
                  │     │ │ _create_product_from_metadata()         │ │
                  │     │ ├─────────────────────────────────────────┤ │
                  │     │ │                                         │ │
                  │     │ │ 3.1: Detect format                      │ │
                  │     │ │   SINGLE или MULTI?                     │ │
                  │     │ │                                         │ │
                  │     │ │ 3.2: Enrich from registry               │ │
                  │     │ │   Берём componentIds из blockchain_data │ │
                  │     │ │   → ComponentService.get_component_full │ │
                  │     │ │        ↓                                │ │
                  │     │ │   ┌──────────────────────────────────┐  │ │
                  │     │ │   │ ComponentService                 │  │ │
                  │     │ │   ├──────────────────────────────────┤  │ │
                  │     │ │   │ 1. Check cache                   │  │ │
                  │     │ │   │ 2. Blockchain.get_component()    │  │ │
                  │     │ │   │ 3. Arweave.download(metadata)    │  │ │
                  │     │ │   │ 4. OrganicComponent.from_registry│  │ │
                  │     │ │   │ 5. Cache result                  │  │ │
                  │     │ │   └──────────────────────────────────┘  │ │
                  │     │ │        ↓                                │ │
                  │     │ │   OrganicComponent.for_product()        │ │
                  │     │ │                                         │ │
                  │     │ │ 3.3: Validate enriched                  │ │
                  │     │ │   _validate_product_metadata()          │ │
                  │     │ │                                         │ │
                  │     │ │ 3.4: Create Product object              │ │
                  │     │ │   Product.from_dict()                   │ │
                  │     │ └─────────────────────────────────────────┘ │
                  │     │                                             │
                  │     │ ШАГ 4: Set blockchain data                  │
                  │     │   product.blockchain_id = id                │
                  │     │   product.business_id = businessId          │
                  │     │   product.blockchain_component_ids = componentIds
                  │     │   product.cid = metadataCID                 │
                  │     │   product.status = active                   │
                  │     └─────────────────────────────────────────────┘
                  │                 ↓
                  │            Product объект
                  │
                  └─ List[Product]
                         ↓
         ┌────────────────────────────────────────┐
         │  Telegram Bot                          │
         │  Отправляет каталог пользователю       │
         └────────────────────────────────────────┘
```

---

## 📊 ДИАГРАММА 6: Кэширование в ComponentService

```
ComponentService.get_component_full("amanita_muscaria")
    ↓
┌─────────────────────────────────────────────────────────────┐
│ Проверка кэша (TTL: 1 час, LRU: 100 компонентов)            │
└─────────────────────────────────────────────────────────────┘
    │
    ├─ CACHE HIT (компонент в кэше, TTL не истек)
    │  └─ return cached_component ⚡ БЫСТРО
    │
    └─ CACHE MISS (компонента нет или TTL истек)
       │
       ├─ BlockchainService.get_component("amanita_muscaria")
       │  └─ OrganicComponentRegistry.getComponent()
       │     → (7, "amanita_muscaria", "0xCreator", "ar://comp123", true, 1234567)
       │
       ├─ ProductStorageService.download_json("ar://comp123")
       │  └─ Arweave HTTP GET
       │     → {
       │         "biounit_id": "amanita_muscaria",
       │         "scientific_title": "Amanita muscaria",
       │         "forms": ["dried", "powder"],
       │         "features": {...}
       │       }
       │
       ├─ OrganicComponent.from_registry(blockchain, metadata)
       │  └─ Создает полный OrganicComponent объект
       │
       ├─ Сохранить в кэш
       │  cache["amanita_muscaria"] = {
       │    "component": component,
       │    "cached_at": datetime.now()
       │  }
       │
       └─ return component

СЛЕДУЮЩИЙ ЗАПРОС того же компонента:
    ↓
CACHE HIT → instant return (нет blockchain/Arweave запросов) ⚡
```

---

## 🔄 Ключевые концепции

### 1. Separation of Concerns (Разделение ответственности)

```yaml
ProductRegistryService:
  role: "Координатор"
  knows: "Как получить список продуктов из blockchain"
  delegates_to: "ProductAssembler для сборки каждого продукта"

ProductAssembler:
  role: "Оркестратор сборки"
  knows: "Как собрать Product из blockchain + Arweave метаданных"
  delegates_to: "ComponentService для обогащения компонентами"

ComponentService:
  role: "Провайдер компонентов"
  knows: "Как загрузить OrganicComponent из реестра по componentIds из blockchain_data"
  uses: "BlockchainService, ProductStorageService"
  features: "Кэширование для оптимизации"

BlockchainService:
  role: "Интерфейс к blockchain"
  knows: "Как вызывать Solidity контракты"

ProductStorageService:
  role: "Интерфейс к Arweave"
  knows: "Как загружать JSON по CID"
```

### 2. Data Flow (Поток данных)

```
Blockchain (минимум)
    ↓  (on-chain businessId + componentIds[])
Arweave (метаданные с ссылками на компоненты)
    ↓
ComponentService (обогащение ссылок → полные данные)
    ↓
Product (Python модель с полными данными)
```

> 💡 Список компонентов (`componentIds[]`) берётся из ProductRegistry и считается единственным источником правды. Метаданные содержат только ссылки; ProductAssembler никогда не доверяет им без cross-check с on-chain данными.

### 3. Два формата продуктов

| Формат | Исходные метаданные | После обогащения |
|--------|---------------------|------------------|
| **SINGLE** | `component_id` на корне | `organic_components: [1 компонент]` |
| **MULTI** | `organic_components: [ссылки]` | `organic_components: [полные данные]` |

### 4. Кэширование (оптимизация)

```
Без кэша:
  Продукт с 3 компонентами → 3 blockchain запроса + 3 Arweave запроса

С кэшем (ComponentService):
  Первый продукт: 3 blockchain + 3 Arweave (кэш заполняется)
  Второй продукт (те же компоненты): 0 запросов (все из кэша) ⚡
```

---

## 🎯 Пример: Полный поток для конкретного продукта

### Входные данные

**Blockchain:**
```python
blockchain_data = {
    "id": 42,
    "seller": "0xSellerAddress",
    "businessId": "blue_lotus_tincture",
    "componentIds": ["blue_lotus"],
    "metadataCID": "ar://xyz123abc",
    "active": True
}
```

**Arweave (ar://xyz123abc):**
```json
{
  "business_id": "blue_lotus_tincture",
  "title": "Blue Lotus Tincture 50ml",
  "component_id": "blue_lotus",
  "proportion": "100%",
  "form": "tincture",
  "categories": ["flowers", "tinctures"],
  "species": ["Nymphaea caerulea"],
  "prices": [{"quantity": 50, "unit": "ml", "price": 20, "currency": "EUR"}]
}
```

### Процесс обработки

**1. ProductAssembler.assemble_product(blockchain_data, metadata)**

```python
# Извлечение blockchain данных
product_id = 42
ipfs_cid = "ar://xyz123abc"
is_active = True

# Определение формата
format = _detect_product_format(metadata)
# → "SINGLE" (есть component_id на корне)

# Обогащение
enriched = _enrich_single_component(metadata)
```

**2. _enrich_single_component() → ComponentService**

```python
component_id = "blue_lotus"
proportion = "100%"

# Загрузка из реестра
registry_component = component_service.get_component_full("blue_lotus")
# → OrganicComponent(
#     component_id="blue_lotus",
#     scientific_title="Nymphaea caerulea",
#     forms=["dried", "tincture"],
#     features={"common": ["relaxation", "meditation", ...]},
#     blockchain_id=7,
#     creator="0xCreator",
#     ...
#   )

# Создание product component
product_component = OrganicComponent.for_product(registry_component, "100%")
# → OrganicComponent (копия registry + proportion="100%")

# Обогащенные метаданные
enriched_metadata = {
  ...все поля из metadata...,
  "organic_components": [product_component.to_dict()]
}
```

**3. Product.from_dict(enriched_metadata)**

```python
product = Product(
  business_id="blue_lotus_tincture",
  blockchain_id=42,                    ← Из blockchain_data
  status=1,                            ← Из blockchain_data (active=True)
  cid="ar://xyz123abc",                ← Из blockchain_data
  title="Blue Lotus Tincture 50ml",
  organic_components=[
    OrganicComponent(
      component_id="blue_lotus",
      scientific_title="Nymphaea caerulea",
      forms=["dried", "tincture"],
      features={"common": ["relaxation", ...]},
      proportion="100%"
    )
  ],
  categories=["flowers", "tinctures"],
  forms=["tincture"],
  species=["Nymphaea caerulea"],
  prices=[PriceInfo(quantity=50, unit="ml", price=20, currency="EUR")]
)
```

### Выходные данные

Python объект `Product` готов для:
- Отображения в Telegram боте
- Сериализации в JSON для API
- Хранения в кэше
- Фильтрации/поиска

---

## ✅ Преимущества новой архитектуры

### 1. Централизация компонентов
```
Было (OLD):
  Product 1 → description_cid_1 → Описание компонента A (дубликат 1)
  Product 2 → description_cid_2 → Описание компонента A (дубликат 2)
  Product 3 → description_cid_3 → Описание компонента A (дубликат 3)

Стало (NEW):
  Product 1 ─┐
  Product 2 ─┼─→ component_id="A" → OrganicComponentRegistry → Единое описание
  Product 3 ─┘
```

### 2. Кэширование
```
ComponentService кэширует компоненты → повторные запросы мгновенные ⚡
```

### 3. Единая логика
```
Было: if storage_service → OLD логика, else → NEW логика
Стало: Только NEW логика (SINGLE/MULTI)
```

### 4. Чистая архитектура
```
ProductAssembler НЕ знает про Blockchain/Arweave детали
    ↓
ComponentService инкапсулирует всю логику загрузки компонентов
    ↓
Простота тестирования (mock ComponentService)
```

---

**Документ:** Архитектура сериализации/десериализации продуктов  
**Версия:** 1.0  
**Дата:** 2025-01-08  
**Статус:** Актуальный

