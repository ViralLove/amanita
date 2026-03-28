# Activity Vertical Layers Analysis — Глубокий анализ вертикальных слоев хранения

## Обзор

Документ описывает глубокий анализ распределения данных Activity по вертикальным слоям: блокчейн (on-chain) и Arweave/IPFS (off-chain), с фокусом на оптимизацию газа через типизацию в контракте.

**Статус**: Глубокий анализ на основе реального кода  
**Дата**: 2026-01-27  
**Методология**: Анализ существующих контрактов и паттернов

---

## 1. Анализ существующих паттернов в кодовой базе

### 1.1 ProductRegistry — эталонный паттерн

**Файл**: `contracts/ProductRegistry.sol`

**Структура on-chain**:
```solidity
struct Product {
    uint256 id;          // Уникальный идентификатор товара
    address seller;      // Продавец (автор записи)
    string ipfsCID;      // Ссылка на JSON-описание (IPFS CID)
    bool active;         // Активен ли товар
}
```

**Наблюдения**:
- Минимальные данные: только `id`, `seller`, `ipfsCID`, `active`
- `string ipfsCID` — хранится как строка (не оптимизировано)
- Нет enum для статусов (используется `bool active`)
- Все метаданные хранятся off-chain

**Газовые затраты** (примерные):
- `uint256 id`: 1 slot (32 bytes) = 20,000 gas при записи
- `address seller`: 1 slot (20 bytes) = 20,000 gas
- `string ipfsCID`: ~2-3 slots (в зависимости от длины CID) = 40,000-60,000 gas
- `bool active`: упаковывается в существующий slot = 0 gas (если есть место)

**Итого**: ~80,000-100,000 gas на создание продукта

---

### 1.2 OrganicComponentRegistry — оптимизированный паттерн

**Файл**: `contracts/OrganicComponentRegistryLogic.sol`

**Структура on-chain**:
```solidity
struct Component {
    uint256 blockchain_id;
    address creator;
    uint256 created_at;
    uint256 last_updated;
    ComponentStatus status;  // ← enum вместо bool
    bool is_shared;
}

enum ComponentStatus {
    Inactive,    // 0
    Active,      // 1
    Pending,     // 2
    Suspended    // 3
}
```

**Наблюдения**:
- Использование `enum ComponentStatus` вместо `bool` (расширяемость)
- `enum` компилируется в `uint8` (экономия газа)
- Хранение временных меток (`created_at`, `last_updated`)
- Дополнительные флаги (`is_shared`)

**Газовые оптимизации**:
- `enum ComponentStatus`: хранится как `uint8` = 1 byte (упаковывается в slot)
- `bool is_shared`: упаковывается в тот же slot
- Экономия: ~20,000 gas на структуру

---

### 1.3 Паттерны типизации для экономии газа

**Найденные паттерны в кодовой базе**:

#### Паттерн 1: Enum для статусов
```solidity
enum Status {
    Draft,          // 0
    SentToReview,   // 1
    Approved,       // 2
    Published       // 3
}
```
**Преимущества**:
- Компилируется в `uint8` (1 byte)
- Упаковывается в storage slot
- Расширяемость (можно добавить новые статусы)

#### Паттерн 2: Bytes32 для констант
```solidity
bytes32 constant SELLER_ROLE = keccak256("SELLER_ROLE");
bytes32 constant ACTIVATOR_ROLE = keccak256("ACTIVATOR_ROLE");
```
**Преимущества**:
- Фиксированный размер (32 bytes)
- Эффективное сравнение
- Используется в AccessControl

#### Паттерн 3: Packed structs
```solidity
struct PackedData {
    uint128 field1;  // 16 bytes
    uint128 field2;  // 16 bytes
    // Упаковывается в 1 slot (32 bytes)
}
```
**Преимущества**:
- Экономия storage slots
- Меньше операций записи

---

## 2. Проектирование ActivityRegistry для Activity

### 2.1 Анализ требований Activity Data Model

**Ключевые поля для on-chain**:
1. `activity_id` — уникальный идентификатор (можно использовать `uint256`)
2. `creator` — создатель (`address`)
3. `activity_type` — тип активности (`"event"` | `"service"`)
4. `status` — статус lifecycle (`Draft`, `SentToReview`, `Approved`, `Published`)
5. `metadataCID` — CID метаданных в Arweave/IPFS
6. `active` — активна ли активность

**Критичные для валидации**:
- `activity_type` — определяет структуру условных полей
- `status` — управляет lifecycle переходами

---

### 2.2 Оптимизированная структура on-chain

**Вариант 1: Минималистичный (как ProductRegistry)**
```solidity
struct Activity {
    uint256 id;
    address creator;
    string activity_type;    // "event" | "service" (string)
    string metadataCID;     // CID метаданных
    bool active;
    uint8 status;           // 0=Draft, 1=SentToReview, 2=Approved, 3=Published
}
```

**Газовые затраты**:
- `uint256 id`: 1 slot = 20,000 gas
- `address creator`: 1 slot = 20,000 gas
- `string activity_type`: ~1 slot (6-7 bytes) = 20,000 gas
- `string metadataCID`: ~2-3 slots (43-64 bytes) = 40,000-60,000 gas
- `bool active`: упаковывается = 0 gas
- `uint8 status`: упаковывается = 0 gas

**Итого**: ~100,000-120,000 gas

**Проблемы**:
- `string activity_type` — неэффективно (можно использовать `enum`)
- `string metadataCID` — можно оптимизировать через `bytes32` (если CID фиксированной длины)

---

**Вариант 2: Оптимизированный (с enum и bytes32)**
```solidity
enum ActivityType {
    Event,      // 0
    Service     // 1
}

enum ActivityStatus {
    Draft,          // 0
    SentToReview,   // 1
    Approved,       // 2
    Published       // 3
}

struct Activity {
    uint256 id;
    address creator;
    ActivityType activity_type;  // ← enum вместо string
    bytes32 metadataCID;          // ← bytes32 вместо string (для фиксированных CID)
    bool active;
    ActivityStatus status;        // ← enum вместо uint8
}
```

**Газовые затраты**:
- `uint256 id`: 1 slot = 20,000 gas
- `address creator`: 1 slot = 20,000 gas
- `ActivityType activity_type`: упаковывается (1 byte) = 0 gas
- `bytes32 metadataCID`: 1 slot = 20,000 gas (если CID ≤ 32 bytes)
- `bool active`: упаковывается = 0 gas
- `ActivityStatus status`: упаковывается (1 byte) = 0 gas

**Итого**: ~60,000 gas (экономия ~40,000-60,000 gas!)

**Ограничения**:
- `bytes32` работает только для CID фиксированной длины (≤ 32 bytes)
- IPFS CID v0 (Qm...) = 46 символов (не влезает в bytes32)
- IPFS CID v1 (bafy...) = 55+ символов (не влезает в bytes32)
- Arweave transaction ID = 43 символа (не влезает в bytes32)

**Вывод**: `bytes32` не подходит для CID (они длиннее 32 байт)

---

**Вариант 3: Компромиссный (enum + string для CID)**
```solidity
enum ActivityType {
    Event,      // 0
    Service     // 1
}

enum ActivityStatus {
    Draft,          // 0
    SentToReview,   // 1
    Approved,       // 2
    Published       // 3
}

struct Activity {
    uint256 id;
    address creator;
    ActivityType activity_type;  // ← enum (экономия газа)
    string metadataCID;          // ← string (необходимо для CID)
    bool active;
    ActivityStatus status;        // ← enum (экономия газа)
}
```

**Газовые затраты**:
- `uint256 id`: 1 slot = 20,000 gas
- `address creator`: 1 slot = 20,000 gas
- `ActivityType activity_type`: упаковывается = 0 gas
- `string metadataCID`: ~2-3 slots = 40,000-60,000 gas
- `bool active`: упаковывается = 0 gas
- `ActivityStatus status`: упаковывается = 0 gas

**Итого**: ~80,000-100,000 gas (экономия ~20,000 gas за счет enum)

**Преимущества**:
- ✅ Использование `enum` для `activity_type` и `status` (экономия газа)
- ✅ Поддержка CID любой длины через `string`
- ✅ Расширяемость (можно добавить новые типы/статусы)

---

### 2.3 Финальная структура ActivityRegistry

**Рекомендуемая структура**:
```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.22;

enum ActivityType {
    Event,      // 0
    Service     // 1
}

enum ActivityStatus {
    Draft,          // 0
    SentToReview,   // 1
    Approved,       // 2
    Published       // 3
}

contract ActivityRegistry {
    struct Activity {
        uint256 id;
        address creator;
        ActivityType activity_type;
        string metadataCID;
        bool active;
        ActivityStatus status;
    }
    
    mapping(uint256 => Activity) private activities;
    mapping(address => uint256[]) private activitiesByCreator;
    uint256[] private publishedActivityIds;
    uint256 private _activityIdCounter;
    
    // Events
    event ActivityCreated(
        uint256 indexed activityId,
        address indexed creator,
        ActivityType activity_type,
        string metadataCID,
        ActivityStatus status
    );
    
    event ActivityStatusUpdated(
        uint256 indexed activityId,
        ActivityStatus oldStatus,
        ActivityStatus newStatus
    );
    
    // Functions
    function createActivity(
        ActivityType activity_type,
        string calldata metadataCID
    ) external returns (uint256) {
        // Implementation
    }
    
    function getActivity(uint256 activityId) 
        external 
        view 
        returns (Activity memory) 
    {
        // Implementation
    }
    
    function updateActivityStatus(
        uint256 activityId,
        ActivityStatus newStatus
    ) external {
        // Implementation
    }
}
```

**Газовые оптимизации**:
1. ✅ `enum ActivityType` вместо `string` (экономия ~20,000 gas)
2. ✅ `enum ActivityStatus` вместо `uint8` (экономия ~20,000 gas)
3. ✅ `calldata` для параметров (экономия ~300-500 gas на функцию)
4. ✅ `indexed` в событиях для фильтрации (экономия off-chain)

---

## 3. Структура данных в Arweave/IPFS

### 3.1 Анализ существующих паттернов

**Файл**: `bot/services/product/storage.py`

**Паттерн хранения JSON**:
```python
def upload_json(self, data: Dict[str, Any]) -> Optional[str]:
    """Загружает JSON в IPFS"""
    return self.ipfs.upload_json(data)
```

**Формат JSON для Product** (из анализа кода):
```json
{
  "business_id": "product_001",
  "title": "Amanita Muscaria Dried",
  "organic_components": [...],
  "cover_image_url": "Qm...",
  "categories": [...],
  "forms": [...],
  "species": "Amanita muscaria",
  "prices": [...]
}
```

**Наблюдения**:
- Единый JSON документ содержит все метаданные
- Структура соответствует модели данных
- CID возвращается после загрузки

---

### 3.2 Структура JSON для Activity

**Полный JSON документ** (соответствует Activity Data Model):

```json
{
  // 1. Identity & Lifecycle
  "activity_id": "act_001",
  "activity_type": "event",
  "status": "Published",
  "versioning": {
    "version": 1,
    "previous_versions": []
  },
  "creator_reference": "activator_123",
  "timestamps": {
    "created_at": "2025-01-15T10:00:00Z",
    "updated_at": "2025-01-20T14:30:00Z",
    "published_at": "2025-01-20T14:30:00Z"
  },
  
  // 2. Core Description
  "title": "Yoga Workshop",
  "short_summary": "Relaxing morning yoga for all levels.",
  "full_description": "Join us for a 90-minute workshop...",
  "format": "workshop",
  "format_other_label": null,
  "categories": {
    "primary": {"id": "wellbeing", "name": "Wellbeing"},
    "secondary": [{"id": "yoga", "name": "Yoga"}],
    "freeform_user_tags": []
  },
  "age_groups": ["adults"],
  "parental_accompaniment": null,
  "language_requirements": {
    "mode": "understand_only",
    "languages_to_understand": ["ru", "en"],
    "languages_to_speak": []
  },
  "media": {
    "official_site": "https://example.com/yoga",
    "social_links": [
      {"platform": "instagram", "url": "https://instagram.com/example"}
    ]
  },
  "policy_notes": null,
  
  // 3. Delivery & Location
  "delivery_mode": "in_person",
  "location_info": {
    "city": "Tallinn",
    "area": "Kesklinn",
    "venue": "Studio Lumina"
  },
  "service_area": null,
  
  // 4. Timing (conditional - только для event)
  "event_timing": {
    "schedule_model": "fixed_dates",
    "fixed_dates": [
      {
        "start": "2025-02-15T09:00:00Z",
        "end": "2025-02-15T10:30:00Z",
        "timezone": "Europe/Tallinn"
      }
    ]
  },
  
  // 5. Participation (conditional - только для event)
  "event_capacity": {
    "group_capacity": 20,
    "seats": 15,
    "min_participants": 5,
    "max_participants": 20
  },
  
  // 6. Duration & Pricing (conditional - только для event)
  "event_duration": {
    "duration_type": "per_occurrence",
    "per_occurrence": {"duration_minutes": 90}
  },
  "event_pricing": {
    "pricing_type": "ticket_price",
    "ticket_price": {
      "amount": 25,
      "currency": "EUR"
    }
  },
  
  // 7. Booking / CTA (conditional - только для event)
  "event_cta": {
    "event_page_link": "https://example.com/yoga",
    "tickets_link": "https://example.com/tickets"
  },
  
  // 8. Source & Provenance
  "sources": {
    "canonical_url": "https://example.com/yoga",
    "source_type": "manual",
    "raw_asset_ref": null,
    "dedup_hints": null
  },
  
  // 9. Review Metadata
  "review_submission": {
    "submitted_at": "2025-01-18T12:00:00Z",
    "notes": null
  },
  "policy_gate_result": {
    "status": "approved",
    "reasons": [],
    "policy_ref": "konyrody_v1.0"
  }
}
```

**Особенности**:
- Единый JSON документ содержит все метаданные
- Условные поля зависят от `activity_type`
- Структура соответствует Activity Data Model
- Размер: ~2-5 KB (в зависимости от описаний)

---

### 3.3 Процесс загрузки в Arweave

**Файл**: `bot/services/core/storage/ar_weave.py`

**Текущий процесс**:
1. Формирование JSON метаданных
2. Вызов `upload_json(data)` → `ArWeaveUploader.upload_json()`
3. Загрузка через Supabase Edge Function (`/functions/v1/arweave-upload/upload-text`)
4. Получение transaction ID (CID)
5. Возврат CID

**Код**:
```python
def upload_json(self, data: Dict[str, Any]) -> Optional[str]:
    """Загружает JSON в IPFS"""
    try:
        return self.ipfs.upload_json(data)
    except Exception as e:
        self.logger.error(f"Error uploading JSON to IPFS: {e}")
        return None
```

**Edge Function** (`supabase/functions/arweave-upload/index.ts`):
- Принимает JSON данные
- Подписывает транзакцию RSASSA-PSS
- Загружает в Arweave
- Возвращает transaction ID

---

### 3.4 Архитектура использования Supabase Edge Function

**Вопрос**: Зачем использовать Supabase Edge Function для загрузки в Arweave?

**Ответ**: Архитектурное решение для обхода ограничений Python SDK

**Проблема**:
- Python SDK для Arweave требует RSASSA-PSS подпись с `saltLength = 32`
- Реализация RSASSA-PSS в Python проблематична (требует WebAssembly или нативные библиотеки)
- Deno имеет нативную поддержку Web Crypto API для RSASSA-PSS с saltLength=32
- Deno (Supabase Edge Functions) имеет лучшую поддержку криптографии

**Архитектура**:

```
┌─────────────────────────────────────────────────────────────┐
│ Python Backend (bot/services/core/storage/ar_weave.py)     │
│                                                             │
│ 1. Формирование JSON метаданных                            │
│ 2. Вызов ArWeaveUploader.upload_json()                     │
│    → HTTP POST к Supabase Edge Function                    │
│    → Headers: Authorization: Bearer SUPABASE_ANON_KEY     │
│    → Body: {"data": json_string, "contentType": "application/json"} │
└────────────────────┬──────────────────────────────────────┘
                     │ HTTP POST
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ Supabase Edge Function                                      │
│ (supabase/functions/arweave-upload/index.ts)                │
│                                                             │
│ 1. Получение запроса через Deno HTTP server                │
│ 2. Валидация данных (validateTextUpload)                  │
│ 3. Загрузка приватного ключа из env (ARWEAVE_PRIVATE_KEY)  │
│ 4. Создание транзакции Arweave                            │
│    → arweave.createTransaction({data: ...}, privateKey)    │
│ 5. Добавление тегов (Content-Type)                         │
│ 6. Подпись транзакции RSASSA-PSS                          │
│    → signTransaction(arweave, transaction, privateKey)     │
│    → Использует Web Crypto API для RSASSA-PSS (saltLength=32) │
│ 7. Отправка транзакции в Arweave                          │
│    → arweave.transactions.post(transaction)                │
│ 8. Возврат transaction ID (CID)                           │
└────────────────────┬──────────────────────────────────────┘
                     │ JSON Response
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ Python Backend получает transaction ID                      │
│ → Сохранение CID для использования в блокчейне             │
└─────────────────────────────────────────────────────────────┘
```

**Преимущества архитектуры**:

1. **Разделение ответственности**:
   - Python Backend: бизнес-логика, формирование данных
   - Edge Function: криптография, взаимодействие с Arweave

2. **Безопасность**:
   - Приватный ключ хранится в Supabase Secrets (не в Python коде)
   - Edge Function изолирована от основного приложения
   - HTTPS коммуникация между компонентами

3. **Производительность**:
   - Edge Function выполняется на edge (ближе к пользователям)
   - Deno имеет нативную поддержку Web Crypto API для RSASSA-PSS
   - Параллельная обработка запросов

4. **Масштабируемость**:
   - Edge Functions автоматически масштабируются
   - Не требует управления инфраструктурой
   - Pay-per-use модель

**Альтернативы** (отклонены):

1. **Прямая загрузка из Python**:
   - ❌ Проблемы с RSASSA-PSS подписью
   - ❌ Требует WebAssembly или нативные библиотеки
   - ❌ Сложность поддержки

2. **Отдельный микросервис**:
   - ❌ Дополнительная инфраструктура
   - ❌ Управление деплоем и масштабированием
   - ❌ Увеличение сложности

**Вывод**: Использование Supabase Edge Function — оптимальное решение для обхода ограничений Python SDK при сохранении простоты архитектуры.

---

### 3.4 Архитектура использования Supabase Edge Function

**Вопрос**: Зачем использовать Supabase Edge Function для загрузки в Arweave?

**Ответ**: Архитектурное решение для обхода ограничений Python SDK

**Проблема**:
- Python SDK для Arweave требует RSASSA-PSS подпись с `saltLength = 32`
- Реализация RSASSA-PSS в Python проблематична (требует WebAssembly или нативные библиотеки)
- Deno имеет нативную поддержку Web Crypto API для RSASSA-PSS с saltLength=32
- Deno (Supabase Edge Functions) имеет лучшую поддержку криптографии

**Архитектура**:

```
┌─────────────────────────────────────────────────────────────┐
│ Python Backend (bot/services/core/storage/ar_weave.py)     │
│                                                             │
│ 1. Формирование JSON метаданных                            │
│ 2. Вызов ArWeaveUploader.upload_json()                     │
│    → HTTP POST к Supabase Edge Function                    │
│    → Headers: Authorization: Bearer SUPABASE_ANON_KEY     │
│    → Body: {"data": json_string, "contentType": "application/json"} │
└────────────────────┬──────────────────────────────────────┘
                     │ HTTP POST
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ Supabase Edge Function                                      │
│ (supabase/functions/arweave-upload/index.ts)                │
│                                                             │
│ 1. Получение запроса через Deno HTTP server                │
│ 2. Валидация данных (validateTextUpload)                  │
│ 3. Загрузка приватного ключа из env (ARWEAVE_PRIVATE_KEY)  │
│ 4. Создание транзакции Arweave                            │
│    → arweave.createTransaction({data: ...}, privateKey)    │
│ 5. Добавление тегов (Content-Type)                         │
│ 6. Подпись транзакции RSASSA-PSS                          │
│    → signTransaction(arweave, transaction, privateKey)     │
│    → Использует Web Crypto API для RSASSA-PSS (saltLength=32) │
│ 7. Отправка транзакции в Arweave                          │
│    → arweave.transactions.post(transaction)                 │
│ 8. Возврат transaction ID (CID)                           │
└────────────────────┬──────────────────────────────────────┘
                     │ JSON Response
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ Python Backend получает transaction ID                      │
│ → Сохранение CID для использования в блокчейне              │
└─────────────────────────────────────────────────────────────┘
```

**Преимущества архитектуры**:

1. **Разделение ответственности**:
   - Python Backend: бизнес-логика, формирование данных
   - Edge Function: криптография, взаимодействие с Arweave

2. **Безопасность**:
   - Приватный ключ хранится в Supabase Secrets (не в Python коде)
   - Edge Function изолирована от основного приложения
   - HTTPS коммуникация между компонентами

3. **Производительность**:
   - Edge Function выполняется на edge (ближе к пользователям)
   - Deno имеет нативную поддержку Web Crypto API для RSASSA-PSS
   - Параллельная обработка запросов

4. **Масштабируемость**:
   - Edge Functions автоматически масштабируются
   - Не требует управления инфраструктурой
   - Pay-per-use модель

**Альтернативы** (отклонены):

1. **Прямая загрузка из Python**:
   - ❌ Проблемы с RSASSA-PSS подписью
   - ❌ Требует WebAssembly или нативные библиотеки
   - ❌ Сложность поддержки

2. **Отдельный микросервис**:
   - ❌ Дополнительная инфраструктура
   - ❌ Управление деплоем и масштабированием
   - ❌ Увеличение сложности

**Вывод**: Использование Supabase Edge Function — оптимальное решение для обхода ограничений Python SDK при сохранении простоты архитектуры.

**Примечание**: Deno поддерживает RSASSA-PSS с `saltLength = 32` через Web Crypto API. Подробный анализ совместимости см. в `supabase/functions/arweave-upload/deno-webcrypto-rsassa-pss-analysis.md`.

**Код реализации** (из `bot/services/core/storage/ar_weave.py`):

```python
def _call_edge_function(self, endpoint: str, data: Dict[str, Any], is_file: bool = False) -> Optional[str]:
    """
    Вызывает Supabase Edge Function для загрузки данных
    
    Args:
        endpoint: Endpoint edge function (/upload-text или /upload-file)
        data: Данные для отправки
        is_file: True если загружается файл (использует multipart)
    
    Returns:
        transaction_id или None при ошибке
    """
    url = f"{self.edge_function_url}{endpoint}"
    
    # Для JSON используем POST с JSON body
    response = requests.post(
        url,
        json=data,
        headers={
            'Authorization': f'Bearer {SUPABASE_ANON_KEY}',
            'Content-Type': 'application/json'
        },
        timeout=self.timeout
    )
    
    if response.status_code == 200:
        result = response.json()
        return result.get('transaction_id')
    return None
```

---

## 4. Синхронизация между слоями

### 4.1 Поток данных: создание Activity

```
┌─────────────────────────────────────────────────────────────┐
│ 1. Формирование метаданных (Backend)                       │
│    → Создание JSON согласно Activity Data Model            │
│    → Валидация структуры                                   │
└────────────────────┬──────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. Загрузка в Arweave (ProductStorageService)              │
│    → upload_json(metadata)                                 │
│    → ArWeaveUploader.upload_json()                         │
│    → HTTP POST к Supabase Edge Function                    │
│    → Edge Function: подпись RSASSA-PSS + загрузка         │
│    → Получение transaction ID (CID)                        │
└────────────────────┬──────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. Создание записи в блокчейне (ActivityRegistry)          │
│    → createActivity(activity_type, metadataCID)            │
│    → Сохранение Activity struct в mapping                 │
│    → Эмиссия события ActivityCreated                       │
└─────────────────────────────────────────────────────────────┘
```

### 4.2 Поток данных: чтение Activity

```
┌─────────────────────────────────────────────────────────────┐
│ 1. Запрос из блокчейна (BlockchainService)                  │
│    → getActivity(activityId)                                │
│    → Получение Activity struct                             │
│    → Извлечение metadataCID                                │
└────────────────────┬──────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. Загрузка метаданных из Arweave (ProductStorageService)   │
│    → download_json(metadataCID)                            │
│    → Загрузка JSON из Arweave по transaction ID            │
│    → Возврат словаря с метаданными                         │
└────────────────────┬──────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. Сборка Activity (ActivityAssembler)                      │
│    → Объединение on-chain и off-chain данных              │
│    → Валидация условных полей                              │
│    → Создание Activity модели                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 5. Оптимизации и рекомендации

### 5.1 Газовые оптимизации

**Примененные оптимизации**:
1. ✅ `enum ActivityType` вместо `string` (экономия ~20,000 gas)
2. ✅ `enum ActivityStatus` вместо `uint8` (экономия ~20,000 gas)
3. ✅ `calldata` для параметров функций (экономия ~300-500 gas)
4. ✅ `indexed` в событиях для фильтрации (экономия off-chain)

**Дополнительные возможности**:
- Packed structs (если добавить больше полей)
- Custom errors вместо require (экономия ~50-100 gas)
- Unchecked блоки для безопасных операций (экономия ~100-200 gas)

### 5.2 Структура JSON в Arweave

**Рекомендации**:
1. ✅ Единый JSON документ (простота загрузки/чтения)
2. ✅ Соответствие Activity Data Model (консистентность)
3. ✅ Валидация перед загрузкой (предотвращение ошибок)
4. ✅ Версионирование структуры (обратная совместимость)

### 5.3 Синхронизация

**Рекомендации**:
1. ✅ Атомарность операций (сначала Arweave, потом блокчейн)
2. ✅ Проверка CID перед созданием записи в блокчейне
3. ✅ События для отслеживания изменений
4. ✅ Fallback механизмы при недоступности Arweave

---

## 6. Сравнение с Product

| Аспект | Product | Activity |
|--------|---------|----------|
| **On-chain структура** | `uint256 id`, `address seller`, `string ipfsCID`, `bool active` | `uint256 id`, `address creator`, `ActivityType activity_type`, `string metadataCID`, `bool active`, `ActivityStatus status` |
| **Типизация** | `bool active` (нет enum) | `enum ActivityType`, `enum ActivityStatus` |
| **Газ на создание** | ~80,000-100,000 gas | ~80,000-100,000 gas (с enum экономия ~20,000) |
| **Off-chain JSON** | Единый документ | Единый документ |
| **Размер JSON** | ~1-3 KB | ~2-5 KB (больше полей) |
| **Условные поля** | Нет | Да (`event_*` vs `service_*`) |

---

## 7. Заключение

**Рекомендуемая архитектура**:

1. **On-chain (ActivityRegistry)**:
   - Использование `enum` для `activity_type` и `status`
   - Минимальные данные: `id`, `creator`, `activity_type`, `metadataCID`, `active`, `status`
   - Газовые оптимизации через типизацию

2. **Off-chain (Arweave/IPFS)**:
   - Единый JSON документ с полными метаданными
   - Структура соответствует Activity Data Model
   - Размер: ~2-5 KB

3. **Синхронизация**:
   - Сначала загрузка в Arweave → получение CID
   - Затем создание записи в блокчейне с CID
   - События для отслеживания изменений

**Экономия газа**: ~20,000-40,000 gas на создание Activity за счет использования `enum` вместо `string`/`uint8`.

---

**Версия**: 1.0  
**Дата**: 2026-01-27  
**Статус**: Глубокий анализ на основе реального кода
