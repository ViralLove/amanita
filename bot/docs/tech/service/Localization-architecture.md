# 🌐 Архитектура системы локализации

## 📋 Что уже реализовано

### 1. Базовая инфраструктура
- ✅ **LocalizationService** - универсальный сервис локализации
- ✅ **TranslationCacheService** - 3-уровневое кэширование (Memory, File, IPFS)
- ✅ **FallbackLocalizationService** - каскадная стратегия fallback
- ✅ **CacheManager** - централизованное управление кэшами
- ✅ **MultilingualIPFSService** - загрузка переводов из IPFS

### 2. Специализированные сервисы
- ✅ **ProductLocalizationService** - локализация продуктов
- ✅ **ComponentLocalizationService** - локализация компонентов
- ✅ **ProductFormatterService** - интеграция с форматированием

### 3. Система кэширования
- ✅ **Memory Cache** - быстрый доступ (1ms)
- ✅ **File Cache** - персистентное хранение (10ms)
- ✅ **IPFS Cache** - кэширование IPFS данных (100ms)
- ✅ **TTL Management** - управление временем жизни кэша

## 🏗️ Новая архитектура IPFS

### 1. Классификация полей по типам

#### **Простые поля (Enum-значения)**
- **Структура**: `class.field` → все языки в одном JSON
- **Примеры**: `product.forms`, `dosage.type`
- **Формат**: `{class}.{field}`

#### **Названия (Title-значения)**
- **Структура**: `class.field` → все языки в одном JSON  
- **Примеры**: `product.title`, `description.scientific_name`
- **Формат**: `{class}.{field}`

#### **Сложные поля (Description-значения)**
- **Структура**: `class` → все поля класса на одном языке в одном JSON
- **Примеры**: `ComponentDescription`, `Description`
- **Формат**: `{class}`

### 2. Схема архитектуры

```
┌─────────────────────────────────────────────────────────────────┐
│                    TELEGRAM BOT LAYER                          │
├─────────────────────────────────────────────────────────────────┤
│  [User Request] → [Language Selection] → [Product Request]     │
└─────────────────────┬───────────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────────┐
│                LOCALIZATION LAYER                              │
├─────────────────────────────────────────────────────────────────┤
│  LocalizationService.t(key, lang)                              │
│  ├─ ProductLocalizationService (product.*, description.*)     │
│  └─ ComponentLocalizationService (ComponentDescription.*)     │
└─────────────────────┬───────────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────────┐
│                 CACHING LAYER                                  │
├─────────────────────────────────────────────────────────────────┤
│  TranslationCacheService                                        │
│  ├─ Level 1: Memory Cache (1ms)                               │
│  ├─ Level 2: File Cache (10ms)                                │
│  └─ Level 3: IPFS Cache (100ms)                               │
└─────────────────────┬───────────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────────┐
│                FALLBACK LAYER                                  │
├─────────────────────────────────────────────────────────────────┤
│  FallbackLocalizationService                                   │
│  ├─ Level 1: Requested Language                               │
│  ├─ Level 2: Russian (Default)                                │
│  ├─ Level 3: Translation Key                                  │
│  └─ Level 4: Placeholder                                      │
└─────────────────────┬───────────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────────┐
│                 IPFS LAYER                                     │
├─────────────────────────────────────────────────────────────────┤
│  MultilingualIPFSService                                       │
│  ├─ CID Resolution (AmanitaInternational)                     │
│  ├─ IPFS Data Retrieval                                       │
│  └─ JSON Parsing & Language Extraction                        │
└─────────────────────┬───────────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────────┐
│               BLOCKCHAIN LAYER                                 │
├─────────────────────────────────────────────────────────────────┤
│  AmanitaInternational.sol                                      │
│  ├─ simpleFieldCIDs["product.forms"] → CID                    │
│  ├─ simpleFieldCIDs["product.title"] → CID                    │
│  └─ complexFieldCIDs["ComponentDescription.ru"] → CID         │
└─────────────────────┬───────────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────────┐
│                 IPFS NETWORK                                   │
├─────────────────────────────────────────────────────────────────┤
│  JSON Structure:                                               │
│  {                                                             │
│    "label": "product.forms",                                  │
│    "languages": {                                              │
│      "ru": {"powder": "Порошок", "capsules": "Капсулы"},      │
│      "en": {"powder": "Powder", "capsules": "Capsules"}       │
│    }                                                           │
│  }                                                             │
└─────────────────────────────────────────────────────────────────┘
```

### 2. Простые поля и названия (1 CID для всех языков)

**product.forms.json**
```json
{
  "label": "product.forms",
  "type": "simple_fields",
  "version": "1.0",
  "timestamp": "2024-01-15T10:30:00Z",
  "author": "0x1234...",
  "languages": {
    "ru": {
      "powder": "Порошок",
      "capsules": "Капсулы",
      "tea": "Чай",
      "tincture": "Настойка",
      "extract": "Экстракт"
    },
    "en": {
      "powder": "Powder",
      "capsules": "Capsules",
      "tea": "Tea",
      "tincture": "Tincture",
      "extract": "Extract"
    },
    "de": {
      "powder": "Pulver",
      "capsules": "Kapseln",
      "tea": "Tee",
      "tincture": "Tinktur",
      "extract": "Extrakt"
    }
  },
  "metadata": {
    "supported_languages": ["ru", "en", "de"],
    "total_units": 5,
    "last_updated": "2024-01-15T10:30:00Z"
  }
}
```

**product.title.json**
```json
{
  "label": "product.title",
  "type": "simple_fields",
  "version": "1.0",
  "timestamp": "2024-01-15T10:30:00Z",
  "author": "0x1234...",
  "languages": {
    "ru": {
      "amanita_powder_001": "Порошок Аманиты",
      "amanita_capsules_001": "Капсулы Аманиты",
      "amanita_tea_001": "Чай Аманиты"
    },
    "en": {
      "amanita_powder_001": "Amanita Powder",
      "amanita_capsules_001": "Amanita Capsules",
      "amanita_tea_001": "Amanita Tea"
    },
    "de": {
      "amanita_powder_001": "Amanita Pulver",
      "amanita_capsules_001": "Amanita Kapseln",
      "amanita_tea_001": "Amanita Tee"
    }
  },
  "metadata": {
    "supported_languages": ["ru", "en", "de"],
    "total_units": 3,
    "last_updated": "2024-01-15T10:30:00Z"
  }
}
```

### 3. Сложные поля (1 CID на класс.язык)

**ComponentDescription.ru.json**
```json
{
  "label": "ComponentDescription",
  "type": "complex_fields",
  "version": "1.0",
  "timestamp": "2024-01-15T10:30:00Z",
  "author": "0x1234...",
  "language": "ru",
  "fields": {
    "generic_description": "Мухомор красный - один из самых узнаваемых грибов в мире. Характеризуется ярко-красной шляпкой с белыми пятнами и белой ножкой с кольцом.",
    "effects": "Содержит иботеновую кислоту и мусцимол, которые оказывают психоактивное воздействие. В малых дозах вызывает расслабление и сонливость.",
    "shamanic": "Священный гриб в культурах Сибири и Северной Америки. Шаманы использовали его для входа в транс, общения с духами и исцеления.",
    "warnings": "Очень токсичен в сыром виде! Требует специальной обработки перед употреблением. Не рекомендуется новичкам.",
    "features": [
      "Ярко-красная шляпка с белыми пятнами",
      "Белая ножка с кольцом",
      "Растет в хвойных лесах",
      "Образует микоризу с хвойными деревьями"
    ],
    "dosage_instructions": [
      {
        "type": "dried",
        "title": "Сушеный гриб",
        "description": "0.5-2 грамма сушеных шляпок. Начинайте с минимальной дозы."
      },
      {
        "type": "tincture",
        "title": "Настойка",
        "description": "5-15 капель настойки в стакане воды. Принимайте натощак."
      }
    ]
  },
  "metadata": {
    "field_types": ["generic_description", "effects", "shamanic", "warnings", "features", "dosage_instructions"],
    "character_count": 2100,
    "last_updated": "2024-01-15T10:30:00Z"
  }
}
```

**ComponentDescription.en.json**
```json
{
  "label": "ComponentDescription",
  "type": "complex_fields",
  "version": "1.0",
  "timestamp": "2024-01-15T10:30:00Z",
  "author": "0x1234...",
  "language": "en",
  "fields": {
    "generic_description": "Red Fly Agaric is one of the most recognizable mushrooms in the world. Characterized by bright red cap with white spots and white stem with ring.",
    "effects": "Contains ibotenic acid and muscimol, which have psychoactive effects. In small doses causes relaxation and drowsiness.",
    "shamanic": "Sacred mushroom in Siberian and North American cultures. Shamans used it for entering trance, communicating with spirits and healing.",
    "warnings": "Very toxic when raw! Requires special processing before consumption. Not recommended for beginners.",
    "features": [
      "Bright red cap with white spots",
      "White stem with ring",
      "Grows in coniferous forests",
      "Forms mycorrhiza with coniferous trees"
    ],
    "dosage_instructions": [
      {
        "type": "dried",
        "title": "Dried mushroom",
        "description": "0.5-2 grams of dried caps. Start with minimal dose."
      },
      {
        "type": "tincture",
        "title": "Tincture",
        "description": "5-15 drops of tincture in a glass of water. Take on empty stomach."
      }
    ]
  },
  "metadata": {
    "field_types": ["generic_description", "effects", "shamanic", "warnings", "features", "dosage_instructions"],
    "character_count": 1800,
    "last_updated": "2024-01-15T10:30:00Z"
  }
}
```

## 🔧 AmanitaInternational.sol

### Схема маппингов

```
┌─────────────────────────────────────────────────────────────────┐
│                    AMANITA INTERNATIONAL MAPPINGS              │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  SIMPLE FIELDS (1 CID для всех языков)                         │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │ simpleFieldCIDs mapping:                                   ││
│  │ ├─ "product.forms" → "QmXxXxXx..." (все языки)            ││
│  │ ├─ "product.title" → "QmYyYyYy..." (все языки)            ││
│  │ ├─ "product.species" → "QmZzZzZz..." (все языки)          ││
│  │ ├─ "description.scientific_name" → "QmAaAaAa..." (все языки)││
│  │ └─ "dosage.type" → "QmBbBbBb..." (все языки)              ││
│  └─────────────────────────────────────────────────────────────┘│
│                                                                 │
│  COMPLEX FIELDS (1 CID на класс.язык)                          │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │ complexFieldCIDs mapping:                                  ││
│  │ ├─ "Description.ru" → "QmCcCcCc..." (все поля на русском)  ││
│  │ ├─ "Description.en" → "QmDdDdDd..." (все поля на английском)││
│  │ ├─ "ComponentDescription.ru" → "QmEeEeEe..." (все поля)    ││
│  │ ├─ "ComponentDescription.en" → "QmFfFfFf..." (все поля)    ││
│  │ ├─ "DosageInstruction.ru" → "QmGgGgGg..." (все поля)       ││
│  │ └─ "DosageInstruction.en" → "QmHhHhHh..." (все поля)       ││
│  └─────────────────────────────────────────────────────────────┘│
│                                                                 │
│  EVENTS:                                                        │
│  ├─ SimpleFieldRegistered(fieldKey, cid)                       │
│  └─ ComplexFieldRegistered(class, language, cid)               │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Код контракта

```solidity
contract AmanitaInternational {
    // Простые поля и названия (1 CID для всех языков)
    mapping(string => string) public simpleFieldCIDs;  // "product.forms" -> CID
    
    // Сложные поля (1 CID на класс.язык)
    mapping(string => string) public complexFieldCIDs; // "ComponentDescription.ru" -> CID
    
    // События
    event SimpleFieldRegistered(string indexed fieldKey, string cid);
    event ComplexFieldRegistered(string indexed class, string indexed language, string cid);
    
    // Функции для простых полей
    function setSimpleFieldCID(string memory fieldKey, string memory cid) external;
    function getSimpleFieldCID(string memory fieldKey) external view returns (string memory);
    
    // Функции для сложных полей
    function setComplexFieldCID(string memory class, string memory language, string memory cid) external;
    function getComplexFieldCID(string memory class, string memory language) external view returns (string memory);
    
    // Вспомогательные функции
    function getAllSimpleFields() external view returns (string[] memory);
    function getComplexFieldsForClass(string memory class) external view returns (string[] memory);
}
```

## 📊 Маппинг полей

### Простые поля (1 CID для всех языков)
- `product.forms` - формы продуктов (enum)
- `product.title` - названия продуктов (title)
- `product.species` - биологические виды (title)
- `description.scientific_name` - научные названия (title)
- `dosage.type` - типы дозировки (enum)

### Сложные поля (1 CID на класс.язык)
- `Description` - описания продуктов
  - `generic_description`, `effects`, `shamanic`, `warnings`
- `ComponentDescription` - описания компонентов
  - `generic_description`, `effects`, `shamanic`, `warnings`, `features`, `dosage_instructions`
- `DosageInstruction` - инструкции по дозировке
  - `title`, `description`

## 🔄 Цепочка получения перевода

### Схема обработки запросов

```
┌─────────────────────────────────────────────────────────────────┐
│                    REQUEST FLOW DIAGRAM                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  USER REQUEST: "product.forms.powder" (language: "en")         │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │ 1. LocalizationService.t("product.forms.powder")           ││
│  │    ├─ Key parsing: class="product", field="forms", value="powder"││
│  │    └─ Route to: ProductLocalizationService                  ││
│  └─────────────────────────────────────────────────────────────┘│
│                              │                                 │
│  ┌───────────────────────────▼─────────────────────────────────┐│
│  │ 2. ProductLocalizationService.get_translation()            ││
│  │    ├─ Check Memory Cache: "product.forms.powder_en"        ││
│  │    ├─ Check File Cache: "product_forms_powder_en"          ││
│  │    └─ Check IPFS Cache: "product.forms"                    ││
│  └───────────────────────────┬─────────────────────────────────┘│
│                              │ (miss)                          │
│  ┌───────────────────────────▼─────────────────────────────────┐│
│  │ 3. MultilingualIPFSService.load_from_ipfs()                ││
│  │    ├─ Get CID: AmanitaInternational.getSimpleFieldCID()    ││
│  │    ├─ Load JSON: IPFS.get_json(cid)                        ││
│  │    └─ Extract: data["languages"]["en"]["powder"]           ││
│  └───────────────────────────┬─────────────────────────────────┘│
│                              │                                 │
│  ┌───────────────────────────▼─────────────────────────────────┐│
│  │ 4. Cache & Return                                          ││
│  │    ├─ Save to Memory Cache                                 ││
│  │    ├─ Save to File Cache                                   ││
│  │    └─ Return: "Powder"                                     ││
│  └─────────────────────────────────────────────────────────────┘│
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 1. Запрос от пользователя
```
Пользователь выбирает язык: "en"
Пользователь запрашивает: "product.forms" -> "powder"
```

### 2. Обработка в Telegram боте
```python
# 1. Инициализация локализации
localization_service = LocalizationService(lang="en")

# 2. Запрос перевода простого поля
form_name = localization_service.t("product.forms.powder")
# → "Powder"

# 3. Запрос перевода сложного поля
description = localization_service.t("ComponentDescription.generic_description")
# → "Red Fly Agaric is one of the most recognizable mushrooms..."
```

### 3. Цепочка получения перевода

**Шаг 1: LocalizationService**
```python
def t(self, key, default=None, **kwargs):
    if '.' in key and not key.startswith('product.') and not key.startswith('description.'):
        # Сложное поле: ComponentDescription.generic_description
        return self.component_localization.get_translation(key, default, **kwargs)
    else:
        # Простое поле: product.forms.powder
        return self.product_localization.get_translation(key, default, **kwargs)
```

**Шаг 2: ProductLocalizationService (простые поля)**
```python
def get_translation(self, key, default=None, **kwargs):
    # 1. Парсинг ключа: "product.forms.powder" -> field="product.forms", value="powder"
    field, value = self._parse_simple_key(key)
    
    # 2. Проверка кэша
    translation = self._get_from_cache(field, value)
    if translation: return translation
    
    # 3. Загрузка из IPFS
    translation = self._load_from_ipfs(field, value)
    if translation: 
        self._save_to_cache(field, value, translation)
        return translation
    
    # 4. Fallback стратегия
    return self._get_fallback_translation(field, value, default)
```

**Шаг 3: ComponentLocalizationService (сложные поля)**
```python
def get_translation(self, key, default=None, **kwargs):
    # 1. Парсинг ключа: "ComponentDescription.generic_description" -> class="ComponentDescription", field="generic_description"
    class_name, field = self._parse_complex_key(key)
    
    # 2. Проверка кэша
    translation = self._get_from_cache(class_name, field)
    if translation: return translation
    
    # 3. Загрузка из IPFS
    translation = self._load_from_ipfs(class_name, field)
    if translation: 
        self._save_to_cache(class_name, field, translation)
        return translation
    
    # 4. Fallback стратегия
    return self._get_fallback_translation(class_name, field, default)
```

## 💾 Система кэширования (3-уровневая)

### Схема кэширования

```
┌─────────────────────────────────────────────────────────────────┐
│                    CACHING ARCHITECTURE                        │
├─────────────────────────────────────────────────────────────────┤
│  [Translation Request] → [Key Parsing] → [Cache Lookup]        │
└─────────────────────┬───────────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────────┐
│                 LEVEL 1: MEMORY CACHE (1ms)                   │
├─────────────────────────────────────────────────────────────────┤
│  Key Format: "class.field.value_language"                      │
│  Examples:                                                      │
│  ├─ "product.forms.powder_en" → "Powder"                      │
│  ├─ "product.title.amanita_powder_001_ru" → "Порошок Аманиты" │
│  └─ "ComponentDescription.generic_description_en" → "Red Fly..."│
└─────────────────────┬───────────────────────────────────────────┘
                      │ (miss)
┌─────────────────────▼───────────────────────────────────────────┐
│                 LEVEL 2: FILE CACHE (10ms)                    │
├─────────────────────────────────────────────────────────────────┤
│  Key Format: "class_field_value_language"                      │
│  Examples:                                                      │
│  ├─ "product_forms_powder_en" → "Powder"                      │
│  ├─ "product_title_amanita_powder_001_ru" → "Порошок Аманиты" │
│  └─ "ComponentDescription_generic_description_en" → "Red Fly..."│
└─────────────────────┬───────────────────────────────────────────┘
                      │ (miss)
┌─────────────────────▼───────────────────────────────────────────┐
│                 LEVEL 3: IPFS CACHE (100ms)                   │
├─────────────────────────────────────────────────────────────────┤
│  Key Format: "class.field" or "class.language"                 │
│  Examples:                                                      │
│  ├─ "product.forms" → {full JSON with all languages}          │
│  ├─ "product.title" → {full JSON with all languages}          │
│  └─ "ComponentDescription.en" → {full JSON with all fields}   │
└─────────────────────┬───────────────────────────────────────────┘
                      │ (miss)
┌─────────────────────▼───────────────────────────────────────────┐
│                 FALLBACK STRATEGY                              │
├─────────────────────────────────────────────────────────────────┤
│  Level 1: Requested Language → Level 2: Russian →              │
│  Level 3: Translation Key → Level 4: Placeholder               │
└─────────────────────────────────────────────────────────────────┘
```

### Уровень 1: Memory Cache (1ms)
```python
# Локальный кэш в памяти сервиса
cache = {
    "product.forms.powder_en": "Powder",
    "ComponentDescription.generic_description_en": "Red Fly Agaric is one of the most recognizable mushrooms..."
}
```

### Уровень 2: File Cache (10ms)
```python
# Персистентный кэш на диске
cache/translations.json = {
    "product_forms_powder_en": "Powder",
    "ComponentDescription_generic_description_en": "Red Fly Agaric is one of the most recognizable mushrooms..."
}
```

### Уровень 3: IPFS Cache (100ms)
```python
# Кэш IPFS данных (если доступен)
ipfs_cache = {
    "product.forms": {
        "data": {...},
        "cid": "QmXxXxXx...",
        "timestamp": 1705312200,
        "ttl": 300
    }
}
```

## 🎯 Преимущества новой структуры

✅ **Композитные ключи** - логичная группировка полей по `class.field`
✅ **Упрощенная структура** - убраны избыточные индексы типа `amanita_powder_001`
✅ **Оптимизация** - меньше CID'ов, более эффективное кэширование
✅ **Масштабируемость** - легко добавлять новые поля и языки
✅ **Децентрализация** - готовность к краудсорсингу
✅ **Производительность** - оптимальный баланс между размером файлов и количеством запросов

## 🏗️ Итоговая архитектура

```
┌─────────────────────────────────────────────────────────────────┐
│                    ENHANCED LOCALIZATION ARCHITECTURE          │
├─────────────────────────────────────────────────────────────────┤
│  [User Request] → [Language Selection] → [Product Request]     │
│  ↓                                                             │
│  [LocalizationService] → [Caching Layer] → [Fallback Layer]   │
│  ↓                                                             │
│  [IPFS Layer] → [Blockchain Layer] → [IPFS Network]           │
│  ↓                                                             │
│  [Quality Control] → [Versioning] → [Moderation]              │
│  ↓                                                             │
│  [Analytics] → [Security] → [Offline Support]                 │
└─────────────────────────────────────────────────────────────────┘

DETAILED FLOW:
┌─────────────────────────────────────────────────────────────────┐
│  COMPOSITE KEYS: "class.field.value" → "translation"           │
│  ├─ Simple Fields: "product.forms.powder" → "Powder"           │
│  ├─ Titles: "product.title.amanita_001" → "Amanita Powder"     │
│  └─ Complex: "ComponentDescription.generic_description" → "..." │
│                                                                 │
│  CACHING STRATEGY: 3-Level Hierarchy                           │
│  ├─ Memory: "class.field.value_lang" → "translation" (1ms)     │
│  ├─ File: "class_field_value_lang" → "translation" (10ms)      │
│  └─ IPFS: "class.field" → {full JSON} (100ms)                  │
│                                                                 │
│  BLOCKCHAIN MAPPINGS: AmanitaInternational.sol                 │
│  ├─ simpleFieldCIDs["product.forms"] → CID                     │
│  └─ complexFieldCIDs["ComponentDescription.ru"] → CID          │
│                                                                 │
│  IPFS STRUCTURE: Optimized JSON Layout                         │
│  ├─ Simple: {languages: {ru: {value: "..."}, en: {value: "..."}}}│
│  └─ Complex: {fields: {field1: "...", field2: "..."}}         │
└─────────────────────────────────────────────────────────────────┘
```


## 🚀 Приоритизация развития

### Phase 1 (Критично - 1-2 недели)
1. **Обновление AmanitaInternational.sol** - новая структура маппингов
2. **Обновление MultilingualIPFSService** - поддержка новой структуры JSON

### Phase 2 (Важно - 2-4 недели)
3. **Обновление сервисов локализации** - поддержка композитных ключей
4. **Система синхронизации кэша** - для стабильности

### Phase 3 (Желательно - 1-2 месяца)
5. **Batch Processing Service** - для производительности
6. **Translation Quality Service** - для качества

### Phase 4 (Долгосрочно - 2-3 месяца)
7. **Translation Security Service** - для безопасности
8. **Community Review System** - для экосистемы

**Результат**: Оптимизированная, масштабируемая система локализации с композитными ключами и готовностью к децентрализации! 🚀
