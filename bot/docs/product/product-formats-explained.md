# 📊 Форматы продуктов: Объяснение с реальными примерами

## 🎯 Архитектура

Все продукты используют централизованный реестр компонентов `OrganicComponentRegistry`:

```
Product → ссылается на component_id → ComponentRegistry → Единое описание для всех
```

**Преимущества:**
- ✅ Единый источник правды
- ✅ Обновление в одном месте → все продукты получают обновление
- ✅ Совместное использование компонентов между продавцами

---

## 📋 Два формата метаданных

### FORMAT_SINGLE — Чистый компонент

**Что это:** Продукт = один компонент из реестра в определенной форме/дозировке.

**Реальный пример из `/data/sellers/iveta/products/`:**

```json
{
  "business_id": "blue_lotus_tincture",
  "title": "Blue Lotus Tincture",
  "component_id": "blue_lotus",        ← КЛЮЧЕВОЕ: component_id на корневом уровне
  "proportion": "100%",
  "form": "tincture",
  "categories": ["flowers", "tinctures"],
  "species": ["Nymphaea caerulea"],
  "prices": [
    {
      "quantity": 50,
      "unit": "ml",
      "price": 20,
      "currency": "EUR"
    }
  ]
}
```

**Логика:**
1. ProductAssembler видит `component_id` на корневом уровне → SINGLE
2. Вызывает `ComponentService.get_component_full("blue_lotus")`
3. Получает полное описание из реестра (научное название, эффекты, дозировка и т.д.)
4. Создает `Product` с обогащенными данными

**Использование:**
- Настойки (tincture)
- Порошки (powder)  
- Сушеные травы (dried)
- Экстракты (extract)

---

### FORMAT_MULTI — Смесь компонентов

**Что это:** Продукт = смесь нескольких компонентов из реестра (blend).

**Пример:**

```json
{
  "business_id": "relaxation_blend",
  "title": "Relaxation Mushroom Blend",
  "organic_components": [               ← КЛЮЧЕВОЕ: массив компонентов
    {
      "component_id": "amanita_muscaria",  ← Ссылка на реестр
      "proportion": "50g"
    },
    {
      "component_id": "lions_mane",        ← Ссылка на реестр
      "proportion": "30g"
    },
    {
      "component_id": "passionflower",     ← Ссылка на реестр
      "proportion": "20g"
    }
  ],
  "categories": ["mushrooms", "blends", "relaxation"],
  "forms": ["powder"],
  "species": [
    "Amanita muscaria",
    "Hericium erinaceus", 
    "Passiflora incarnata"
  ]
}
```

**Логика:**
1. ProductAssembler видит `organic_components` массив → MULTI
2. Для КАЖДОГО компонента вызывает `ComponentService.get_component_full(component_id)`
3. Получает полные описания всех компонентов из реестра
4. Создает `Product` с обогащенными данными всех компонентов

**Использование:**
- Травяные чаи (herbal tea blends)
- Грибные смеси (mushroom blends)
- Адаптогенные формулы (adaptogen formulas)

---

## 🔍 Как определяется формат (_detect_product_format)

### Алгоритм определения:

```python
def _detect_product_format(metadata):
    # 1. Проверяем SINGLE
    if 'component_id' in metadata:  # component_id на корневом уровне
        return 'SINGLE'
    
    # 2. Проверяем MULTI
    if 'organic_components' in metadata:
        first = metadata['organic_components'][0]
        
        # MULTI: компоненты ссылаются на реестр
        if 'component_id' in first:
            return 'MULTI'
    
    # 3. Неизвестный формат → ошибка
    raise ValueError("Unknown format!")
```

### Таблица определения:

| Признак | Формат | Действие |
|---------|--------|----------|
| `component_id` на корневом уровне | SINGLE | ✅ Обработать |
| `organic_components` + `component_id` в элементах | MULTI | ✅ Обработать |
| Другое | Invalid | ❌ ValueError |

---

## 🔗 Связь с ProductRegistry и on-chain структурой

### Что уходит в смарт-контракт

- **SINGLE**: `component_id` на корневом уровне → превращается в `componentIds = [component_id]`.
- **MULTI**: каждый `organic_components[i].component_id` агрегируется в `componentIds[]`.
- `business_id` из метаданных = `businessId` в контракте.
- `metadataCID` загружается в Arweave/Pinata **без** дублирования компонентов (только ссылки).

```mermaid
flowchart LR
    A[metadata.component_id / organic_components[].component_id] --> B[collect_component_ids()]
    B --> C[componentIds[] в product_registry_upload_data.json]
    C --> D[ProductRegistry.createProduct(businessId, componentIds, metadataCID)]
```

В `ProductRegistry` хранится структура:
```solidity
struct Product {
    uint256 id;
    address seller;
    string businessId;
    string[] componentIds; // ← формируется из metadata
    string metadataCID;
    bool active;
}
```

### Почему метаданные остаются «тонкими»

- Полные описания компонентов берутся через `ComponentService.get_component_full(component_id)` на backend.
- ProductAssembler обогащает продукт, подтягивая данные из OrganicComponentRegistry по on-chain `componentIds`.
- Это позволяет обновлять описания/локализации компонентов централизованно без перепаковки всех продуктов.

### Как подготовить данные перед загрузкой

1. При генерации `product_registry_upload_data.json` всегда формируйте `componentIds[]` на основе формата:
   ```
   componentIds = metadata.get("component_id")
       ? [metadata["component_id"]]
       : [c["component_id"] for c in metadata["organic_components"]]
   ```
2. Проверяйте, что каждый `component_id` зарегистрирован в OrganicComponentRegistry (иначе контракт выдаст `ComponentNotFound`).
3. Передавайте `componentIds[]` в `createProduct` **в том же порядке**, в каком они перечислены в метаданных — это упрощает сопоставление и валидацию.

> См. также `product-structure.md` для полной on-chain структуры и `product-catalog-population.md` для пайплайна подготовки `componentIds[]`.

---

## 📊 Реальные данные в системе

### Реестр компонентов (`/data/components/`)

**Структура:**
```
data/components/
├── amanita_muscaria/
│   ├── amanita_muscaria.json          ← Основные данные компонента
│   └── complex_fields/
│       ├── amanita_muscaria.ComponentDescription.en.json  ← Описание на английском
│       ├── amanita_muscaria.ComponentDescription.ru.json  ← Описание на русском
│       └── ...                                            ← Другие языки
├── blue_lotus/
├── lions_mane/
└── ...
```

**Пример компонента (`amanita_muscaria.json`):**
```json
{
  "biounit_id": "amanita_muscaria",      ← Читается как component_id (совместимость)
  "scientific_title": "Amanita muscaria",
  "forms": ["dried", "powder", "extract"],
  "features": {
    "common": [
      "stress_relief",
      "consciousness_expansion",
      "meditation_practice"
    ]
  }
}
```

### Продукты продавцов (`/data/sellers/iveta/products/`)

**Структура:**
```
data/sellers/iveta/products/
├── blue_lotus_tincture/
│   └── blue_lotus_tincture.json       ← SINGLE формат
├── amanita_pantherina_powder/
│   └── amanita_pantherina_powder.json ← SINGLE формат
└── ...
```

**Пример продукта (`blue_lotus_tincture.json`):**
```json
{
  "product_id": "blue_lotus_tincture",
  "components": [
    {
      "component_business_id": "blue_lotus",  ← Будет преобразован в component_id
      "proportion": "100%",
      "form": "tincture"
    }
  ]
}
```

---

## ✅ Итоговая архитектура

```
┌─────────────────────────────────────────────────────────────┐
│                    ProductAssembler                          │
│                                                              │
│  1. Получает метаданные продукта из Arweave                 │
│  2. Определяет формат: _detect_product_format()             │
│     - SINGLE → component_id на корневом уровне              │
│     - MULTI  → organic_components массив                    │
│                                                              │
│  3. Обогащает данными из реестра:                           │
│     - SINGLE: _enrich_single_component()                    │
│     - MULTI:  _enrich_multi_component()                     │
│                                                              │
│  4. Создает Product с полными данными                       │
└─────────────────────────────────────────────────────────────┘
                            │
                            │ component_service (REQUIRED)
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    ComponentService                          │
│                                                              │
│  - get_component_full(component_id)                         │
│    → Blockchain + Arweave метаданные                        │
│  - get_component_description(component_id, language)        │
│    → Локализованные описания                                │
│  - Кэширование (TTL + LRU)                                  │
│  - Graceful degradation                                     │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│            OrganicComponentRegistry (Blockchain)             │
│                                                              │
│  Централизованное хранилище компонентов:                    │
│  - amanita_muscaria                                         │
│  - blue_lotus                                               │
│  - lions_mane                                               │
│  - ... (все компоненты системы)                             │
└─────────────────────────────────────────────────────────────┘
```

---

**Документ:** Объяснение форматов продуктов с реальными примерами  
**Версия:** 2.0  
**Дата:** 2025-01-08  
**Статус:** Актуальный
