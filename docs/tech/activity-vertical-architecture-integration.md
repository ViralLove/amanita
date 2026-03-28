# Activity Vertical Architecture Integration — Интеграция Activity в вертикальную архитектуру

## Обзор

Документ описывает глубокий анализ структуры Activity и её интеграцию с вертикальной архитектурой данных, описанной в `vertical-data-architecture.md`. Activity будет использовать тот же архитектурный подход, что и Product, но с учетом специфики модели данных.

**Статус**: Анализ и проектирование  
**Дата**: 2026-01-27  
**Источник**: `GPT UI/instructions/activity-data-model.md`

---

## 1. Анализ текущего состояния Activity

### 1.1 Существующая реализация

**Файлы**:
- `bot/api/models/activity.py` — Pydantic модели для API (минимальные)
- `bot/api/services/activity_storage.py` — In-memory хранилище (моки)
- `bot/api/routes/activities.py` — API эндпоинты

**Текущий статус**:
- ✅ Полная модель данных определена в `activity-data-model.md`
- ✅ API эндпоинты реализованы (lifecycle, search, retrieval)
- ✅ In-memory хранилище для тестирования GPT UI
- ❌ Нет смарт-контракта (ActivityRegistry.sol)
- ❌ Нет блокчейн-интеграции
- ❌ Нет вертикальной архитектуры (on-chain → off-chain → enrichment → model)

### 1.2 Структура данных Activity

**Ключевые особенности**:

1. **Дискриминатор типа**: `activity_type` (`"event"` | `"service"`)
   - Определяет структуру условных полей
   - Влияет на валидацию и бизнес-логику

2. **Условные поля** (mutually exclusive):
   - Event: `event_timing`, `event_capacity`, `event_duration`, `event_pricing`, `event_cta`
   - Service: `service_timing`, `service_participation`, `service_duration_options`, `service_pricing_model`, `service_cta`

3. **Общие поля**:
   - Identity & Lifecycle: `activity_id`, `status`, `versioning`, `creator_reference`, `timestamps`
   - Core Description: `title`, `short_summary`, `full_description`, `format`, `categories`, `age_groups`, `language_requirements`, `media`
   - Delivery & Location: `delivery_mode`, `location_info`, `service_area`
   - Source & Provenance: `sources`
   - Review Metadata: `review_submission`, `policy_gate_result`

4. **Lifecycle статусы**:
   - `Draft` → `SentToReview` → `Approved` → `Published`
   - Валидация переходов через `validate_state_transition()`

---

## 2. Проектирование вертикальной архитектуры для Activity

### 2.1 Сравнение с Product

| Аспект | Product | Activity |
|--------|---------|----------|
| **On-chain данные** | `id`, `seller`, `ipfsCID`, `active`, `componentIds[]` | `id`, `creator`, `ipfsCID`, `active`, `activity_type` |
| **Обогащение** | Компоненты из OrganicComponentRegistry | Возможно: категории, локации, форматы (если будут реестры) |
| **Условные поля** | Нет (единая структура) | Да (`event_*` vs `service_*`) |
| **Валидация** | Компоненты, цены, CID | Тип активности, условные поля, lifecycle |

### 2.2 Уровни архитектуры для Activity

#### Уровень 1: Смарт-контракт (On-Chain)

**Предполагаемая структура** (`ActivityRegistry.sol`):

```solidity
struct Activity {
    uint256 id;              // Уникальный идентификатор активности
    address creator;         // Создатель (Activator)
    string activity_type;    // "event" | "service" (ключевой дискриминатор)
    string ipfsCID;          // Ссылка на JSON-метаданные (IPFS CID)
    bool active;             // Активна ли активность
    uint8 status;            // 0=Draft, 1=SentToReview, 2=Approved, 3=Published
}
```

**Особенности**:
- Минимальные данные on-chain (экономия газа)
- `activity_type` хранится on-chain (критично для валидации)
- `status` хранится on-chain (для lifecycle управления)
- Метаданные хранятся off-chain (IPFS/Arweave)

**Методы контракта**:
- `createActivity(string activity_type, string ipfsCID)` → `uint256 activityId`
- `getActivity(uint256 activityId)` → `Activity`
- `updateActivityStatus(uint256 activityId, uint8 newStatus)` → `bool`
- `getActivitiesByCreator(address creator)` → `uint256[]`
- `getPublishedActivities()` → `uint256[]`

---

#### Уровень 2: Блокчейн-декодирование (Codec Layer)

**Файл**: `bot/services/core/contracts/activity_registry_codec.py`

**Структура данных**:
```python
@dataclass(frozen=True)
class ActivityRegistryGetActivity:
    id: int
    creator: str
    activity_type: str  # "event" | "service"
    metadata_cid: str
    active: bool
    status: int  # 0=Draft, 1=SentToReview, 2=Approved, 3=Published
```

**Процесс декодирования**:
1. Получение сырого кортежа из `ActivityRegistry.getActivity()`
2. Валидация структуры (ожидается 6 элементов)
3. Валидация `activity_type` (должен быть "event" или "service")
4. Валидация `status` (должен быть 0-3)
5. Преобразование типов и возврат типизированной структуры

**Особенности**:
- `activity_type` критичен — определяет структуру метаданных
- `status` должен соответствовать lifecycle модели

---

#### Уровень 3: Загрузка метаданных (Storage Layer)

**Файл**: `bot/services/product/storage.py` (переиспользование)

**Процесс**:
1. Получение CID из блокчейн-данных (`metadata_cid`)
2. Загрузка JSON из IPFS/Arweave через `ProductStorageService.download_json(cid)`
3. Возврат словаря с метаданными Activity

**Структура метаданных** (пример для event):
```json
{
  "activity_id": "act_001",
  "activity_type": "event",
  "status": "Published",
  "title": "Yoga Workshop",
  "short_summary": "Relaxing morning yoga",
  "full_description": "...",
  "format": "workshop",
  "delivery_mode": "in_person",
  "location_info": {
    "city": "Tallinn",
    "venue": "Studio Lumina"
  },
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
  "event_capacity": {
    "group_capacity": 20,
    "max_participants": 20
  },
  "event_duration": {
    "duration_type": "per_occurrence",
    "per_occurrence": {
      "duration_minutes": 90
    }
  },
  "event_pricing": {
    "pricing_type": "ticket_price",
    "ticket_price": {
      "amount": 25,
      "currency": "EUR"
    }
  },
  "event_cta": {
    "event_page_link": "https://example.com/yoga",
    "tickets_link": "https://example.com/tickets"
  }
}
```

**Особенности**:
- Метаданные содержат полную структуру Activity
- Условные поля зависят от `activity_type`
- Валидация соответствия `activity_type` между blockchain и metadata

---

#### Уровень 4: Обогащение (Enrichment Layer) — опционально

**Файл**: `bot/services/activity/assembler.py` → `_enrich_activity()`

**Назначение**: Обогащение метаданных данными из внешних источников (если потребуется)

**Возможные источники обогащения**:
1. **Категории** (если будет CategoryRegistry)
   - Загрузка полных данных категорий из реестра
   - Добавление локализованных названий

2. **Локации** (если будет LocationRegistry)
   - Загрузка полных данных локаций
   - Добавление координат, описаний

3. **Форматы** (если будет FormatRegistry)
   - Загрузка описаний форматов
   - Добавление локализованных метаданных

**Текущий статус**: Обогащение не требуется на начальном этапе
- Activity метаданные самодостаточны
- Нет внешних реестров для обогащения (в отличие от Product с компонентами)

**Будущее расширение**:
- Если появятся реестры категорий/локаций/форматов, можно добавить обогащение аналогично Product

---

#### Уровень 5: Сборка Activity (Assembly Layer)

**Файл**: `bot/services/activity/assembler.py` → `assemble_activity()`

**Процесс сборки**:

#### Шаг 1: Извлечение данных блокчейна
```python
blockchain_info = _extract_blockchain_data(blockchain_data)
# (activity_id, creator, activity_type, metadata_cid, active, status)
```

#### Шаг 2: Валидация метаданных
```python
validation_result = _validate_metadata(metadata)
# Использует ValidationFactory.get_activity_validator()
# Проверяет соответствие activity_type между blockchain и metadata
```

#### Шаг 3: Валидация условных полей
```python
# Проверка условных полей в зависимости от activity_type
if activity_type == "event":
    _validate_event_fields(metadata)
    # Проверка: event_timing, event_capacity, event_duration, event_pricing, event_cta
    # Проверка отсутствия: service_* полей
elif activity_type == "service":
    _validate_service_fields(metadata)
    # Проверка: service_timing, service_participation, service_duration_options, service_pricing_model, service_cta
    # Проверка отсутствия: event_* полей
```

#### Шаг 4: Обогащение (если требуется)
```python
# Пока не требуется, но может быть добавлено в будущем
enriched_metadata = await _enrich_activity(metadata, language)
```

#### Шаг 5: Создание объекта Activity
```python
activity = Activity.from_dict(enriched_metadata)
# Создает типизированный объект с валидацией
```

#### Шаг 6: Установка блокчейн-данных
```python
_set_blockchain_data(activity, activity_id, metadata_cid, active, status)
# Устанавливает blockchain_id, cid, active, status
```

---

#### Уровень 6: Бизнес-модель (Model Layer)

**Файл**: `bot/model/activity.py` (будущая реализация)

**Структура данных**:
```python
@dataclass
class Activity:
    # Identity & Lifecycle
    activity_id: str
    blockchain_id: Union[int, str]
    activity_type: Literal["event", "service"]
    status: Literal["Draft", "SentToReview", "Approved", "Published"]
    versioning: Optional[Dict]
    creator_reference: str
    timestamps: Dict[str, Optional[str]]  # created_at, updated_at, published_at
    
    # Core Description
    title: str
    short_summary: Optional[str]
    full_description: Optional[str]
    format: str
    format_other_label: Optional[str]
    categories: Optional[Dict]
    age_groups: Optional[List[str]]
    parental_accompaniment: Optional[str]
    language_requirements: Optional[Dict]
    media: Optional[Dict]
    policy_notes: Optional[str]
    
    # Delivery & Location
    delivery_mode: str
    location_info: Dict
    service_area: Optional[Dict]
    
    # Timing (conditional)
    event_timing: Optional[Dict]  # Если activity_type == "event"
    service_timing: Optional[Dict]  # Если activity_type == "service"
    
    # Participation & Capacity (conditional)
    event_capacity: Optional[Dict]  # Если activity_type == "event"
    service_participation: Optional[Dict]  # Если activity_type == "service"
    
    # Duration & Pricing (conditional)
    event_duration: Optional[Dict]  # Если activity_type == "event"
    event_pricing: Optional[Dict]  # Если activity_type == "event"
    service_duration_options: Optional[List[Dict]]  # Если activity_type == "service"
    service_pricing_model: Optional[Dict]  # Если activity_type == "service"
    
    # Booking / CTA (conditional)
    event_cta: Optional[Dict]  # Если activity_type == "event"
    service_cta: Optional[Dict]  # Если activity_type == "service"
    
    # Source & Provenance
    sources: Optional[Dict]
    
    # Review Metadata
    review_submission: Optional[Dict]
    policy_gate_result: Optional[Dict]
    
    # Blockchain data
    cid: str
    active: bool
```

**Валидация**:
- Автоматическая валидация через `__post_init__()`
- Проверка условных полей в зависимости от `activity_type`
- Валидация lifecycle переходов
- Использование `ValidationFactory` для единообразной валидации

**Особенности**:
- Условные поля должны быть валидированы на основе `activity_type`
- Mutually exclusive поля не должны присутствовать одновременно
- Lifecycle статусы должны соответствовать правилам переходов

---

## 3. Поток данных для Activity

### Полный цикл от блокчейна до модели

```
┌─────────────────────────────────────────────────────────────┐
│ 1. Смарт-контракт ActivityRegistry                          │
│    struct Activity { id, creator, activity_type, ipfsCID,  │
│                      active, status }                       │
└────────────────────┬──────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. BlockchainService.get_activity()                         │
│    → Web3 вызов ActivityRegistry.getActivity(id)            │
│    → Возвращает сырой кортеж (tuple)                       │
└────────────────────┬──────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. ActivityRegistryCodec.decode_get_activity_tuple()        │
│    → Валидация структуры (6 элементов)                     │
│    → Валидация activity_type ("event" | "service")         │
│    → Валидация status (0-3)                                 │
│    → ActivityRegistryGetActivity(id, creator, activity_type,│
│       metadata_cid, active, status)                        │
└────────────────────┬──────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. ProductStorageService.download_json(metadata_cid)        │
│    → Загрузка JSON из IPFS/Arweave по CID                   │
│    → Возврат словаря с метаданными Activity               │
└────────────────────┬──────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ 5. ActivityAssembler.assemble_activity()                    │
│    ├─ _extract_blockchain_data()                           │
│    ├─ _validate_metadata()                                 │
│    ├─ _validate_activity_type_match()                      │
│    ├─ _validate_conditional_fields() ────────┐            │
│    │   ├─ Если event: _validate_event_fields()│            │
│    │   └─ Если service: _validate_service_fields()         │
│    ├─ _enrich_activity() (опционально, будущее)           │
│    ├─ Activity.from_dict(enriched_metadata)                │
│    └─ _set_blockchain_data()                                │
└────────────────────┬──────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ 6. Activity (финальная модель)                             │
│    → Полностью валидированный объект с условными полями    │
│    → Готов для использования в бизнес-логике               │
└─────────────────────────────────────────────────────────────┘
```

---

## 4. Ключевые отличия от Product

### 4.1 Условные поля

**Product**: Единая структура для всех продуктов
- Все продукты имеют одинаковые поля
- Нет условной логики на уровне модели

**Activity**: Условные поля в зависимости от `activity_type`
- Event и Service имеют разные наборы полей
- Требуется валидация условных полей
- Mutually exclusive поля не должны присутствовать одновременно

**Решение**: Валидация в `ActivityAssembler._validate_conditional_fields()`

---

### 4.2 Обогащение

**Product**: Обязательное обогащение компонентов
- Компоненты загружаются из OrganicComponentRegistry
- Добавляются описания из MultilingualIPFSService

**Activity**: Обогащение не требуется на начальном этапе
- Метаданные самодостаточны
- Нет внешних реестров для обогащения
- Может быть добавлено в будущем (категории, локации, форматы)

---

### 4.3 Lifecycle управление

**Product**: Простой статус (`active` / `inactive`)
- Активация/деактивация через смарт-контракт

**Activity**: Сложный lifecycle (`Draft` → `SentToReview` → `Approved` → `Published`)
- Валидация переходов через `validate_state_transition()`
- Статус хранится on-chain для управления lifecycle
- Требуется проверка прав доступа для каждого перехода

---

### 4.4 Валидация

**Product**: Валидация компонентов, цен, CID
- Проверка соответствия `componentIds` между blockchain и metadata
- Валидация пропорций компонентов

**Activity**: Валидация условных полей, lifecycle, типов
- Проверка соответствия `activity_type` между blockchain и metadata
- Валидация условных полей в зависимости от типа
- Валидация lifecycle переходов

---

## 5. План реализации

### Фаза 1: Модель и валидация (текущая)
- ✅ Определение структуры данных (`activity-data-model.md`)
- ✅ API модели (`bot/api/models/activity.py`)
- ✅ In-memory хранилище (`bot/api/services/activity_storage.py`)
- ✅ API эндпоинты (`bot/api/routes/activities.py`)

### Фаза 2: Бизнес-модель (следующая)
- [ ] Создание `bot/model/activity.py` с полной моделью
- [ ] Реализация валидации условных полей
- [ ] Интеграция с `ValidationFactory`
- [ ] Тесты модели

### Фаза 3: Смарт-контракт (будущее)
- [ ] Создание `contracts/ActivityRegistry.sol`
- [ ] Реализация методов контракта
- [ ] Деплой и тестирование

### Фаза 4: Вертикальная архитектура (будущее)
- [ ] Создание `bot/services/core/contracts/activity_registry_codec.py`
- [ ] Создание `bot/services/activity/assembler.py`
- [ ] Интеграция с `BlockchainService`
- [ ] Интеграция с `ProductStorageService` (переиспользование)
- [ ] Тесты сборки Activity

### Фаза 5: Обогащение (опционально, будущее)
- [ ] Создание реестров (если потребуется)
- [ ] Реализация обогащения в `ActivityAssembler`
- [ ] Интеграция с внешними сервисами

---

## 6. Примеры использования

### Пример 1: Загрузка Activity по ID

```python
# 1. Получение данных из блокчейна
blockchain_data = blockchain_service.get_activity_structured(activity_id)

# 2. Загрузка метаданных
metadata = storage_service.download_json(blockchain_data.metadata_cid)

# 3. Сборка Activity
activity = await assembler.assemble_activity(
    blockchain_data=(
        blockchain_data.id,
        blockchain_data.creator,
        blockchain_data.activity_type,
        blockchain_data.metadata_cid,
        blockchain_data.active,
        blockchain_data.status
    ),
    metadata=metadata,
    language="ru"
)
```

### Пример 2: Валидация условных полей

```python
# Внутри ActivityAssembler._validate_conditional_fields()
if activity_type == "event":
    # Проверка наличия event_* полей
    required_event_fields = [
        "event_timing",
        "event_capacity",
        "event_duration",
        "event_pricing",
        "event_cta"
    ]
    for field in required_event_fields:
        if field not in metadata:
            raise ValueError(f"Missing required field for event: {field}")
    
    # Проверка отсутствия service_* полей
    forbidden_service_fields = [
        "service_timing",
        "service_participation",
        "service_duration_options",
        "service_pricing_model",
        "service_cta"
    ]
    for field in forbidden_service_fields:
        if field in metadata:
            raise ValueError(f"Forbidden field for event: {field}")

elif activity_type == "service":
    # Аналогичная валидация для service
    ...
```

---

## 7. Интеграция с существующими компонентами

### 7.1 Переиспользование компонентов

**ProductStorageService**:
- Используется для загрузки метаданных Activity
- Не требует изменений

**ValidationFactory**:
- Добавление `get_activity_validator()`
- Валидация условных полей
- Валидация lifecycle переходов

**BlockchainService**:
- Добавление методов для работы с ActivityRegistry
- Аналогично методам для ProductRegistry

### 7.2 Новые компоненты

**ActivityRegistryCodec**:
- Аналогично `ProductRegistryCodec`
- Декодирование данных Activity из блокчейна

**ActivityAssembler**:
- Аналогично `ProductAssembler`
- Специфичная валидация условных полей
- Управление lifecycle

**Activity Model**:
- Полная модель с условными полями
- Валидация на основе `activity_type`

---

## 8. Заключение

Activity будет использовать вертикальную архитектуру данных, аналогичную Product, но с учетом специфики:

1. **Условные поля**: Валидация на основе `activity_type`
2. **Lifecycle управление**: Сложный lifecycle с валидацией переходов
3. **Обогащение**: Не требуется на начальном этапе, может быть добавлено в будущем
4. **Валидация**: Специфичная для Activity (условные поля, lifecycle)

Архитектурный подход остается тем же:
- Минимальные данные on-chain
- Метаданные off-chain (IPFS/Arweave)
- Сборка через Assembler
- Типизированные модели с валидацией

Это обеспечивает консистентность архитектуры и переиспользование паттернов.

---

## Связанные документы

- `docs/tech/vertical-data-architecture.md` — Вертикальная архитектура данных
- `GPT UI/instructions/activity-data-model.md` — Модель данных Activity
- `bot/api/models/activity.py` — API модели Activity
- `bot/api/services/activity_storage.py` — Хранилище Activity
- `bot/api/routes/activities.py` — API эндпоинты Activity

---

**Версия**: 1.0  
**Дата**: 2026-01-27  
**Автор**: Анализ на основе Activity Data Model и вертикальной архитектуры Product
