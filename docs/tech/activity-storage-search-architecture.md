# Activity Storage & Search Architecture — Архитектура хранения и поиска Activity

## Обзор

Документ описывает архитектурные решения для хранения данных Activity и реализации высокоэффективного поиска через эмбеддинги в Supabase.

**Статус**: Проектирование и обсуждение  
**Дата**: 2026-01-27  
**Источники**: 
- `GPT UI/instructions/activity-data-model.md`
- `GPT UI/instructions/search-data-model.md`
- Вертикальная архитектура Product

---

## 1. Распределение данных: On-Chain vs Off-Chain

### 1.1 Данные в смарт-контракте (On-Chain)

**Принцип**: Минимальные критичные данные для экономии газа

**Структура** (`ActivityRegistry.sol`):
```solidity
struct Activity {
    uint256 id;              // Уникальный идентификатор
    address creator;         // Создатель (Activator)
    string activity_type;    // "event" | "service" (критично для валидации)
    string metadataCID;     // CID метаданных в Arweave/IPFS
    bool active;             // Активна ли активность
    uint8 status;            // 0=Draft, 1=SentToReview, 2=Approved, 3=Published
}
```

**Обоснование**:
- `id`, `creator`, `active`, `status` — критичны для управления lifecycle
- `activity_type` — критичен для валидации условных полей
- `metadataCID` — ссылка на полные метаданные (off-chain)

**Методы контракта**:
- `createActivity(string activity_type, string metadataCID)` → `uint256 activityId`
- `getActivity(uint256 activityId)` → `Activity`
- `updateActivityStatus(uint256 activityId, uint8 newStatus)` → `bool`
- `getActivitiesByCreator(address creator)` → `uint256[]`
- `getPublishedActivities()` → `uint256[]` (только Published)

---

### 1.2 Данные в Arweave/IPFS (Off-Chain)

**Принцип**: Полные метаданные Activity в едином JSON документе

**Структура JSON** (соответствует Activity Data Model):

```json
{
  // 1. Identity & Lifecycle
  "activity_id": "act_001",
  "activity_type": "event",
  "status": "Published",
  "versioning": {...},
  "creator_reference": "activator_123",
  "timestamps": {
    "created_at": "2025-01-15T10:00:00Z",
    "updated_at": "2025-01-20T14:30:00Z",
    "published_at": "2025-01-20T14:30:00Z"
  },
  
  // 2. Core Description
  "title": "Yoga Workshop",
  "short_summary": "Relaxing morning yoga",
  "full_description": "...",
  "format": "workshop",
  "categories": {...},
  "age_groups": ["adults"],
  "language_requirements": {...},
  "media": {...},
  
  // 3. Delivery & Location
  "delivery_mode": "in_person",
  "location_info": {...},
  "service_area": null,
  
  // 4. Timing (conditional)
  "event_timing": {...},  // или "service_timing": {...}
  
  // 5. Participation (conditional)
  "event_capacity": {...},  // или "service_participation": {...}
  
  // 6. Duration & Pricing (conditional)
  "event_duration": {...},
  "event_pricing": {...},  // или "service_duration_options": {...}, "service_pricing_model": {...}
  
  // 7. Booking / CTA (conditional)
  "event_cta": {...},  // или "service_cta": {...}
  
  // 8. Source & Provenance
  "sources": {...},
  
  // 9. Review Metadata
  "review_submission": {...},
  "policy_gate_result": {...}
}
```

**Особенности**:
- Единый JSON документ содержит все метаданные
- Условные поля зависят от `activity_type`
- JSON хранится в Arweave/IPFS по CID
- CID хранится в смарт-контракте

**Процесс хранения**:
1. Создание Activity → формирование JSON метаданных
2. Загрузка JSON в Arweave/IPFS → получение CID
3. Вызов `createActivity(activity_type, CID)` → сохранение CID в контракте

---

## 2. Архитектура поиска через эмбеддинги

### 2.1 Подход: Фрагментарное хранение в Supabase

**Вопрос**: Хранить полностью все или фрагменты по функциональным блокам?

**Ответ**: **Фрагментарное хранение** по функциональным блокам

**Преимущества фрагментарного подхода**:
1. **Гранулярность поиска**: Поиск по конкретным блокам (локация, время, контент)
2. **Эффективность эмбеддингов**: Каждый блок имеет свой контекст для эмбеддинга
3. **Гибкость**: Можно обновлять отдельные блоки без пересчета всего документа
4. **Производительность**: Меньшие эмбеддинги = быстрее поиск
5. **Масштабируемость**: Легче масштабировать отдельные блоки

**Недостатки**:
1. Сложность синхронизации между блоками
2. Необходимость объединения результатов из разных блоков

**Решение**: Фрагментарное хранение с референсом на полный документ

---

### 2.2 Функциональные блоки данных

**Блоки для фрагментации** (на основе Activity Data Model и Search Data Model):

#### Блок 1: Identity & Lifecycle
```json
{
  "activity_id": "act_001",
  "activity_type": "event",
  "status": "Published",
  "creator_reference": "activator_123",
  "timestamps": {...}
}
```
**Использование**: Фильтрация по статусу, типу, создателю

#### Блок 2: Core Content (Контент)
```json
{
  "title": "Yoga Workshop",
  "short_summary": "Relaxing morning yoga",
  "full_description": "...",
  "format": "workshop",
  "categories": {...},
  "age_groups": ["adults"],
  "parental_accompaniment": null
}
```
**Использование**: Семантический поиск по тексту, фильтрация по формату, категориям, возрастным группам

#### Блок 3: Language Requirements (Языковые требования)
```json
{
  "language_requirements": {
    "mode": "understand_only",
    "languages_to_understand": ["ru", "en"],
    "languages_to_speak": ["ru"]
  }
}
```
**Использование**: Фильтрация и семантический поиск по языковым требованиям

#### Блок 4: Location (Локация)
```json
{
  "delivery_mode": "in_person",
  "location_info": {
    "city": "Tallinn",
    "area": "Kesklinn",
    "venue": "Studio Lumina"
  },
  "service_area": null
}
```
**Использование**: Поиск по локации, фильтрация по delivery_mode, service_area

#### Блок 5: Timing (Время) — Event
```json
{
  "event_timing": {
    "schedule_model": "fixed_dates",
    "fixed_dates": [
      {
        "start": "2025-02-15T09:00:00Z",
        "end": "2025-02-15T10:30:00Z",
        "timezone": "Europe/Tallinn"
      }
    ]
  }
}
```
**Использование**: Поиск по датам, временным диапазонам, дням недели

#### Блок 6: Timing (Время) — Service
```json
{
  "service_timing": {
    "availability_type": "fixed_windows",
    "availability_windows": [
      {
        "day_of_week": "monday",
        "start_time": "10:00",
        "end_time": "12:00",
        "timezone": "Europe/Tallinn"
      }
    ],
    "booking_policy": "..."
  }
}
```
**Использование**: Поиск по дням недели, временным окнам

#### Блок 7: Participation & Capacity (Участие)
```json
{
  "event_capacity": {
    "group_capacity": 20,
    "seats": 15,
    "min_participants": 5,
    "max_participants": 20
  }
}
```
или
```json
{
  "service_participation": {
    "session_mode": "one_to_one",
    "concurrent_clients": 1
  }
}
```
**Использование**: Фильтрация по вместимости, режиму сессии

#### Блок 8: Pricing (Ценообразование)
```json
{
  "event_pricing": {
    "pricing_type": "ticket_price",
    "ticket_price": {
      "amount": 25,
      "currency": "EUR"
    }
  }
}
```
или
```json
{
  "service_pricing_model": {
    "model": "per_session",
    "package_definition": {...}
  }
}
```
**Использование**: Фильтрация по цене, типу ценообразования

#### Блок 9: CTA & Booking (Призыв к действию)
```json
{
  "event_cta": {
    "event_page_link": "https://example.com/yoga",
    "tickets_link": "https://example.com/tickets"
  }
}
```
или
```json
{
  "service_cta": {
    "booking_url": "https://calendly.com/example",
    "contact_channel": {...}
  }
}
```
**Использование**: Фильтрация по наличию ссылок, booking URL

---

### 2.3 Структура таблиц в Supabase

**Таблица 1: `activities` (основная таблица)**
```sql
CREATE TABLE activities (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  blockchain_id BIGINT NOT NULL UNIQUE,
  activity_id TEXT NOT NULL UNIQUE,
  activity_type TEXT NOT NULL CHECK (activity_type IN ('event', 'service')),
  status TEXT NOT NULL CHECK (status IN ('Draft', 'SentToReview', 'Approved', 'Published')),
  creator_reference TEXT NOT NULL,
  metadata_cid TEXT NOT NULL,  -- CID полного JSON в Arweave
  active BOOLEAN NOT NULL DEFAULT true,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  published_at TIMESTAMPTZ
);

CREATE INDEX idx_activities_status ON activities(status);
CREATE INDEX idx_activities_type ON activities(activity_type);
CREATE INDEX idx_activities_creator ON activities(creator_reference);
CREATE INDEX idx_activities_published ON activities(published_at) WHERE status = 'Published';
```

**Таблица 2: `activity_content_blocks` (фрагменты с эмбеддингами)**
```sql
CREATE TABLE activity_content_blocks (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  activity_id TEXT NOT NULL REFERENCES activities(activity_id) ON DELETE CASCADE,
  block_type TEXT NOT NULL CHECK (block_type IN (
    'identity',
    'content',
    'language',
    'location',
    'timing_event',
    'timing_service',
    'participation_event',
    'participation_service',
    'pricing_event',
    'pricing_service',
    'cta_event',
    'cta_service'
  )),
  block_data JSONB NOT NULL,  -- Данные блока
  embedding vector(1536),  -- OpenAI embedding (1536 dimensions)
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_content_blocks_activity ON activity_content_blocks(activity_id);
CREATE INDEX idx_content_blocks_type ON activity_content_blocks(block_type);
CREATE INDEX idx_content_blocks_embedding ON activity_content_blocks USING ivfflat (embedding vector_cosine_ops);
```

**Таблица 3: `activity_search_index` (индексированные поля для фильтрации)**
```sql
CREATE TABLE activity_search_index (
  activity_id TEXT PRIMARY KEY REFERENCES activities(activity_id) ON DELETE CASCADE,
  
  -- Core filters
  format TEXT,
  categories JSONB,  -- {"primary": {...}, "secondary": [...]}
  age_groups TEXT[],
  delivery_mode TEXT,
  
  -- Location (denormalized for fast filtering)
  city TEXT,
  area TEXT,
  venue TEXT,
  service_area_radius NUMERIC,
  service_area_districts TEXT[],
  
  -- Timing (denormalized for fast filtering)
  -- Event timing
  event_start_date TIMESTAMPTZ,
  event_end_date TIMESTAMPTZ,
  event_recurring BOOLEAN DEFAULT false,
  event_recurring_days TEXT[],  -- ['monday', 'wednesday']
  
  -- Service timing
  service_availability_days TEXT[],  -- ['monday', 'wednesday']
  service_availability_type TEXT,
  
  -- Participation
  event_max_participants INTEGER,
  event_available_seats INTEGER,
  service_session_mode TEXT,
  
  -- Pricing
  event_pricing_type TEXT,
  event_price NUMERIC,
  event_currency TEXT,
  service_pricing_model TEXT,
  service_price NUMERIC,
  service_currency TEXT,
  
  -- Language
  language_mode TEXT,
  languages_to_understand TEXT[],
  languages_to_speak TEXT[],
  
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_search_format ON activity_search_index(format);
CREATE INDEX idx_search_age_groups ON activity_search_index USING GIN(age_groups);
CREATE INDEX idx_search_delivery_mode ON activity_search_index(delivery_mode);
CREATE INDEX idx_search_city ON activity_search_index(city);
CREATE INDEX idx_search_event_dates ON activity_search_index(event_start_date, event_end_date);
CREATE INDEX idx_search_service_days ON activity_search_index USING GIN(service_availability_days);
CREATE INDEX idx_search_languages ON activity_search_index USING GIN(languages_to_understand);
```

---

## 3. Разбиение на эмбеддинги

### 3.1 Стратегия эмбеддингов по блокам

**Принцип**: Каждый функциональный блок имеет свой эмбеддинг для семантического поиска

**Блоки с эмбеддингами**:

#### 1. Content Block (Контент) — основной для текстового поиска
```python
content_text = f"""
Title: {title}
Summary: {short_summary}
Description: {full_description}
Format: {format}
Categories: {categories}
Age Groups: {', '.join(age_groups)}
"""
embedding = openai.embeddings.create(
    model="text-embedding-3-large",
    input=content_text
)
```

#### 2. Language Requirements Block (Языковые требования)
```python
language_text = f"""
Language Mode: {language_mode}
Languages to Understand: {', '.join(languages_to_understand)}
Languages to Speak: {', '.join(languages_to_speak)}
"""
embedding = openai.embeddings.create(...)
```

#### 3. Location Block (Локация)
```python
location_text = f"""
Delivery Mode: {delivery_mode}
City: {city}
Area: {area}
Venue: {venue}
Service Area: {service_area}
"""
embedding = openai.embeddings.create(...)
```

#### 4. Timing Block — Event (Время для событий)
```python
timing_text = f"""
Schedule Model: {schedule_model}
Fixed Dates: {format_dates(fixed_dates)}
Recurring Rule: {recurrence_rule}
Timezone: {timezone}
"""
embedding = openai.embeddings.create(...)
```

#### 5. Timing Block — Service (Время для сервисов)
```python
timing_text = f"""
Availability Type: {availability_type}
Availability Windows: {format_windows(availability_windows)}
Booking Policy: {booking_policy}
"""
embedding = openai.embeddings.create(...)
```

**Блоки БЕЗ эмбеддингов** (только структурированные данные):
- Identity & Lifecycle — фильтрация по индексам
- Participation & Capacity — числовые фильтры
- Pricing — числовые фильтры
- CTA & Booking — фильтрация по наличию ссылок

---

### 3.2 Процесс создания эмбеддингов

**Триггер**: При создании/обновлении Activity

**Процесс**:
1. Загрузка полного JSON из Arweave по CID
2. Разбиение на функциональные блоки
3. Генерация эмбеддингов для блоков с текстовым контентом
4. Сохранение блоков в `activity_content_blocks`
5. Денормализация данных в `activity_search_index` для быстрой фильтрации

**Код** (пример):
```python
async def index_activity(activity_id: str, metadata_cid: str):
    # 1. Загрузка JSON из Arweave
    metadata = storage_service.download_json(metadata_cid)
    
    # 2. Разбиение на блоки
    blocks = split_into_blocks(metadata)
    
    # 3. Генерация эмбеддингов
    for block in blocks:
        if block.needs_embedding():
            embedding = await generate_embedding(block.get_text())
            block.embedding = embedding
    
    # 4. Сохранение в Supabase
    await save_blocks_to_supabase(activity_id, blocks)
    
    # 5. Денормализация для фильтрации
    await update_search_index(activity_id, metadata)
```

---

## 4. Поиск через эмбеддинги

### 4.1 Гибридный поиск (Hybrid Search)

**Подход**: Комбинация векторного поиска (эмбеддинги) + структурированных фильтров

**Процесс**:
1. **Векторный поиск** по эмбеддингам блоков (семантический поиск)
2. **Структурированные фильтры** по `activity_search_index` (точные фильтры)
3. **Объединение результатов** с ранжированием

**Пример запроса**:
```python
async def search_activities(query: SearchQuery):
    results = []
    
    # 1. Векторный поиск по контенту (если есть text query)
    if query.text:
        content_embedding = await generate_embedding(query.text)
        vector_results = await supabase.rpc('match_content_blocks', {
            'query_embedding': content_embedding,
            'match_threshold': 0.7,
            'match_count': 100
        })
        results.extend(vector_results)
    
    # 2. Структурированные фильтры
    filter_query = supabase.table('activity_search_index').select('activity_id')
    
    if query.filters.activity_type:
        filter_query = filter_query.eq('activity_type', query.filters.activity_type)
    
    if query.filters.format:
        filter_query = filter_query.eq('format', query.filters.format)
    
    if query.filters.location.city:
        filter_query = filter_query.eq('city', query.filters.location.city)
    
    if query.filters.time.date_range:
        filter_query = filter_query.gte('event_start_date', query.filters.time.date_range.start_date)
        filter_query = filter_query.lte('event_end_date', query.filters.time.date_range.end_date)
    
    filter_results = await filter_query.execute()
    
    # 3. Объединение и ранжирование
    combined_results = combine_and_rank(vector_results, filter_results)
    
    return combined_results
```

---

### 4.2 Функция поиска в Supabase (PostgreSQL)

```sql
-- Функция для векторного поиска по контенту
CREATE OR REPLACE FUNCTION match_content_blocks(
  query_embedding vector(1536),
  match_threshold float DEFAULT 0.7,
  match_count int DEFAULT 100,
  block_types text[] DEFAULT ARRAY['content', 'language', 'location', 'timing_event', 'timing_service']
)
RETURNS TABLE (
  activity_id text,
  block_type text,
  similarity float,
  block_data jsonb
)
LANGUAGE plpgsql
AS $$
BEGIN
  RETURN QUERY
  SELECT
    acb.activity_id,
    acb.block_type,
    1 - (acb.embedding <=> query_embedding) as similarity,
    acb.block_data
  FROM activity_content_blocks acb
  WHERE
    acb.block_type = ANY(block_types)
    AND acb.embedding IS NOT NULL
    AND 1 - (acb.embedding <=> query_embedding) > match_threshold
  ORDER BY acb.embedding <=> query_embedding
  LIMIT match_count;
END;
$$;
```

---

## 5. Single Point of Failure (SPOF) анализ

### 5.1 Риски

**Supabase как SPOF**:
- Если Supabase недоступен, поиск не работает
- Если данные в Supabase не синхронизированы с блокчейном, результаты неактуальны

**Mitigation**:
1. **Fallback на блокчейн**: Если Supabase недоступен, использовать прямые запросы к блокчейну
2. **Кэширование**: Кэшировать результаты поиска
3. **Репликация**: Использовать read replicas Supabase
4. **Мониторинг**: Мониторить синхронизацию данных

### 5.2 Архитектура отказоустойчивости

```
┌─────────────────────────────────────────────────────────────┐
│ Поисковый запрос                                            │
└────────────────────┬──────────────────────────────────────┘
                     │
                     ▼
         ┌───────────────────────┐
         │ Supabase (Primary)    │
         │ - Vector Search       │
         │ - Structured Filters  │
         └───────────┬───────────┘
                     │
         ┌───────────▼───────────┐
         │ Fallback: Blockchain  │
         │ - Direct queries      │
         │ - Basic filtering     │
         └───────────────────────┘
```

---

## 6. Рекомендации

### 6.1 Хранение данных

✅ **Рекомендуется**:
- Фрагментарное хранение по функциональным блокам
- Эмбеддинги только для текстовых блоков
- Денормализация структурированных данных для быстрой фильтрации
- Референс на полный JSON в Arweave для восстановления

### 6.2 Поиск

✅ **Рекомендуется**:
- Гибридный поиск (векторный + структурированный)
- Индексы на часто используемые поля
- Кэширование популярных запросов
- Fallback на блокчейн при недоступности Supabase

### 6.3 Синхронизация

✅ **Рекомендуется**:
- Синхронизация при создании/обновлении Activity
- Периодическая проверка синхронизации
- Логирование расхождений

---

## 7. Вопросы для обсуждения

1. **Фрагментация**: Подходит ли предложенная структура блоков?
2. **Эмбеддинги**: Какие блоки точно нуждаются в эмбеддингах?
3. **Денормализация**: Какие поля критичны для денормализации?
4. **SPOF**: Достаточны ли меры по предотвращению SPOF?
5. **Производительность**: Нужны ли дополнительные оптимизации?

---

**Версия**: 1.0  
**Дата**: 2026-01-27  
**Статус**: Проектирование, требует обсуждения
