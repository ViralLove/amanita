# Анализ модели данных Activity
## Изучение раздела "Data Model" из Estonian Eventify PDF

**Методология:** @analysis.mdc  
**Источник:** `GPT UI/docs/Zeya888 — Estonians888 — Estonian Eventify.pdf`  
**Дата анализа:** 2025-01-13

---

## 1. Суть модели данных (Core Concept)

### 1.1 Ключевое архитектурное решение: Event vs Service

**Критическое различие:**

Модель данных вводит **first-class discriminator** `activity_type` с двумя значениями:
- `event` — события с фиксированным расписанием
- `service` — услуги по запросу/назначению

**Почему это важно на уровне модели:**

Это **не UI-различие** и **не вариация поля**. Это фундаментальное семантическое различие, которое влияет на:
- представление времени (schedule vs availability),
- интерпретацию capacity (групповые события vs индивидуальные сессии),
- структуру pricing (билеты vs почасовая оплата),
- логику поиска и фильтрации,
- какие поля обязательны на разных стадиях.

**Архитектурное следствие:**

Попытка представить services как "events without dates" или events как "services with slots" приводит к:
- двусмысленности,
- сложности валидации,
- поломке логики discovery.

---

## 2. Структура модели данных (8 разделов)

### Раздел 0: Identity & Lifecycle (общие для всех)

**Поля:**
- `activity_id` — уникальный идентификатор
- `activity_type`: `event` | `service` ☑ **ключ дифференциации**
- `status`: `Draft` | `SentToReview` | `Approved` | `Published`
- `versioning` — черновики/версии, audit trail
- `creator/owner reference` — псевдонимный идентификатор Activator (без PII)
- `timestamps` — created/updated/published

**Наблюдения:**
- `activity_type` стоит первым после ID — это подчёркивает его критичность
- `creator/owner` — это reference, не PII (соответствует privacy-first подходу)
- `versioning` — поддержка истории изменений

---

### Раздел 1: Core Description (общие для всех)

**Поля:**
- `title`
- `short_summary`
- `full_description`
- `format` — контролируемый список + "other"
- `categories / taxonomy` — 2 уровня + fallback user suggestion
- `age_groups` — babies...seniors
- `parental_accompaniment` — `allowed` | `required` | `optional` (для детских)
- `language_requirements`:
  - `mode`: `irrelevant` | `understand_only` | `speak_and_understand` | `mixed`
  - `languages_to_understand[]`
  - `languages_to_speak[]`
- `media & external links`:
  - official site
  - social links (enum)
  - event/service-specific links
- `policy notes` — опционально: дисклеймеры/ограничения, без клиники

**Наблюдения:**
- `format` — контролируемый список с fallback "other"
- `taxonomy` — двухуровневая с возможностью user suggestions
- `language_requirements` — структурированная модель (mode + списки языков)
- `parental_accompaniment` — специфично для детских активностей

---

### Раздел 2: Delivery & Location (общие, но с нюансом)

**Поля:**
- `delivery_mode`: `in_person` | `online` | `hybrid`
- `location_info`:
  - `city` / `area`
  - `venue` (если применимо)
  - `online platform` / `link` (если применимо)
- `service_area` — ♟ чаще нужно для service
  - `radius` / `districts` / `travel notes` (может быть общим полем, но заполняется обычно в service)

**Наблюдения:**
- `service_area` — пример поля, которое чаще используется для services, но может быть общим
- `delivery_mode` — общий для обоих типов

---

### Раздел 3: Timing (главная точка дифференциации)

**Критическое различие:**

**Если `activity_type = event`:**
- `event_timing`
- `schedule model` (fixed dates / recurring)
- `exceptions` / `overrides`
- `ability to compute next occurrence`

**Если `activity_type = service`:**
- `service_timing`
- `availability_type`: `by_request` | `fixed_windows` | (future) `bookable_slots`
- `optional availability windows` (если фиксированные)
- `booking policy` (как записаться)

**☑ Правило:** `event_timing` и `service_timing` **взаимоисключающие**.

**Наблюдения:**
- Это единственный раздел, где структура данных **полностью различается** по типу
- Event — это фиксированные даты/расписание
- Service — это availability/booking policy
- Взаимоисключающие поля — явное архитектурное решение против двусмысленности

---

### Раздел 4: Participation & Capacity (дифференциация смысла)

**Event:**
- `event_capacity`
- `group capacity` / `seats`
- (optional) `min/max participants`

**Service:**
- `service_participation`
- `session_mode`: `one_to_one` | `family` | `small_group`
- `concurrent_clients` (обычно 1)
- `practitioner-to-client model` (без персонализации)

**Наблюдения:**
- Event — фокус на групповой capacity (места, участники)
- Service — фокус на режиме сессии (1:1, семья, малая группа)
- `concurrent_clients` — специфично для services (обычно 1, но может быть больше)

---

### Раздел 5: Duration & Pricing (частично общие, но структура разная)

**Event:**
- `event_duration`:
  - derived per occurrence OR fixed duration
- `event_pricing`:
  - ticket price / donation / free
  - price range

**Service:**
- `service_duration_options`:
  - 30/60/90/custom etc.
- `service_pricing_model`:
  - `per_session` | `per_hour` | `per_package` | `donation` | `free`
  - optional package definition

**Наблюдения:**
- Event — фиксированная duration на событие
- Service — варианты duration (30/60/90 минут)
- Event — pricing как билет/цена события
- Service — pricing model (per_session, per_hour, per_package)

---

### Раздел 6: Booking / CTA (call-to-action) (дифференциация)

**Event:**
- `event_cta`:
  - event page link
  - tickets link (optional)

**Service:**
- `service_cta`:
  - `booking_url` (Calendly/сайт/форма)
  - or contact via public channel (social link)
  - or "Amanita booking (future)"

**Наблюдения:**
- Event — ссылки на страницу события и билеты
- Service — booking URL или контакт через публичный канал
- Упоминание "Amanita booking (future)" — платформа может предоставлять booking в будущем

---

### Раздел 7: Source & Provenance (общие для всех)

**Поля:**
- `sources`:
  - `canonical_url` (если есть)
  - `source_type` (manual/link/screenshot/pdf)
  - (optional) `raw_asset_ref` (TTL)
  - `dedup hints` (possible duplicates, update vs new)

**Наблюдения:**
- `sources` — отслеживание происхождения данных
- `dedup hints` — поддержка дедупликации и обновлений
- `raw_asset_ref` с TTL — временное хранение исходных файлов

---

### Раздел 8: Review Metadata (общие для всех)

**Поля:**
- `review_submission`:
  - `submitted_at`
  - `notes` (опционально)
- `policy_gate_result`:
  - `approved` / `rejected` / `needs_clarification`
  - `reasons` (структурировано)
  - `policy_ref` (КоныРода version)

**Наблюдения:**
- `policy_gate_result` — результат проверки через КоныРода Gate
- `reasons` — структурированные причины (не free-form текст)
- `policy_ref` — версия политики, по которой проверяли

---

## 3. Архитектурные принципы модели

### 3.1 Unified Lifecycle, Divergent Semantics

**Принцип:**
Оба типа (`event` и `service`):
- используют **одинаковый lifecycle** (Draft → Review → Approved → Published),
- проходят через **одинаковый policy gate** (КоныРода),
- появляются в **одинаковом discovery surface**,
- подчиняются **одинаковым privacy и compliance правилам**.

**Различаются только там, где семантика действительно расходится:**
- timing (schedule vs availability),
- participation (group capacity vs session mode),
- booking (event page vs booking URL).

**Вывод:**
Модель сохраняет архитектурную ясность, позволяя платформе представлять широкий спектр человеческих активностей без принуждения к искусственной event-only модели.

---

### 3.2 One Field → One Meaning

**Принцип:**
- Одно поле → одно значение
- Нет перегруженных или двусмысленных полей
- Нет free-form текста там, где существуют контролируемые значения
- Все enums и категории должны быть каноническими

**Примеры из модели:**
- `activity_type` — строго `event` | `service` (не "event_or_service")
- `delivery_mode` — строго `in_person` | `online` | `hybrid` (не free-form)
- `language_requirements.mode` — строго enum (не free-form текст)

---

### 3.3 Conditional Fields Based on Type

**Принцип:**
Некоторые поля **взаимоисключающие** в зависимости от `activity_type`:
- `event_timing` vs `service_timing` — никогда не оба одновременно
- `event_capacity` vs `service_participation` — разные структуры для разных типов
- `event_pricing` vs `service_pricing_model` — разные модели ценообразования

**Реализация:**
Это должно быть валидировано на уровне схемы:
- Если `activity_type = event` → `event_timing` обязателен, `service_timing` запрещён
- Если `activity_type = service` → `service_timing` обязателен, `event_timing` запрещён

---

## 4. Критические наблюдения для парсинга

### 4.1 Определение типа активности при парсинге

**Задача для Ingest Deep Parsing:**

При парсинге ввода GPT должен определить:
- Это `event` или `service`?

**Индикаторы для `event`:**
- Упоминание конкретных дат/времени
- "Мероприятие", "событие", "event"
- Упоминание билетов, регистрации на событие
- Групповой формат (workshop, ceremony, performance)

**Индикаторы для `service`:**
- "По запросу", "по назначению", "by appointment"
- Индивидуальные сессии (therapy, coaching, tutoring)
- "Записаться", "связаться", "booking"
- 1:1 или малая группа

**Если неясно:**
- Пометить как ambiguous
- Запросить уточнение у пользователя

---

### 4.2 Поля, которые нужно извлекать по-разному

**Timing:**
- Event → извлекать schedule (даты, recurrence)
- Service → извлекать availability (by_request, fixed_windows)

**Capacity:**
- Event → извлекать group capacity, seats
- Service → извлекать session_mode (one_to_one, family, small_group)

**Pricing:**
- Event → извлекать ticket price, price range
- Service → извлекать pricing model (per_session, per_hour, per_package)

**CTA:**
- Event → извлекать event page link, tickets link
- Service → извлекать booking URL, contact channel

---

### 4.3 Поля, общие для обоих типов

Эти поля извлекаются одинаково независимо от типа:
- `title`, `short_summary`, `full_description`
- `format`, `categories`, `taxonomy`
- `age_groups`, `parental_accompaniment`
- `language_requirements`
- `delivery_mode`, `location_info`
- `media & external links`
- `sources`, `review_metadata`

---

## 5. Вопросы для уточнения

### 5.1 Структура JSON схемы

**Вопрос:**
Нужна ли полная JSON схема со всеми вложенными структурами?

**Например:**
```json
{
  "activity_id": "...",
  "activity_type": "event",
  "status": "Draft",
  "core_description": {
    "title": "...",
    "short_summary": "...",
    "full_description": "...",
    "format": "workshop",
    "categories": {
      "primary": {...},
      "secondary": [...]
    },
    "age_groups": ["adults"],
    "language_requirements": {
      "mode": "understand_only",
      "languages_to_understand": ["Russian"],
      "languages_to_speak": []
    }
  },
  "event_timing": {
    "schedule_model": "recurring",
    "recurrence_rule": "...",
    "exceptions": []
  },
  // ...
}
```

---

### 5.2 Обязательность полей на разных стадиях

**Вопрос:**
Какие поля обязательны для:
- Draft (минимальная полнота)?
- SentToReview (полнота для review)?
- Approved (полнота для publication)?

**Наблюдение из модели:**
В разделе 3 (Timing) упоминается:
> "which fields are required at review and publication stages"

Это означает, что требования к полноте различаются по стадиям.

---

### 5.3 Формат enum значений

**Вопрос:**
Нужны ли точные enum значения для:
- `format` (workshop, ceremony, class_regular, class_single, session, retreat, performance, other)?
- `delivery_mode` (in_person, online, hybrid)?
- `session_mode` (one_to_one, family, small_group)?
- `availability_type` (by_request, fixed_windows, bookable_slots)?
- `pricing_model` (per_session, per_hour, per_package, donation, free)?

---

### 5.4 Структура schedule/recurrence

**Вопрос:**
Как именно структурирован `event_timing`?
- Используется ли RRULE формат?
- Как представляются exceptions (EXDATE)?
- Как вычисляется "next occurrence"?

---

### 5.5 Структура taxonomy

**Вопрос:**
Как структурирована двухуровневая taxonomy?
- Какие категории уровня 1?
- Какие категории уровня 2?
- Как работает fallback user suggestion?

---

## 6. Выводы для task-Ingest-Deep-Parsing.md

### 6.1 Что нужно добавить в TODO секции

1. **TODO 1 (Section 2):** Добавить полную JSON схему Activity с:
   - всеми 8 разделами
   - условными полями (event_timing vs service_timing)
   - enum значениями для всех контролируемых полей

2. **TODO 2 (Section 4):** Для каждого поля extraction rules добавить:
   - точное имя поля в JSON схеме
   - тип данных (string, enum, object, array)
   - условность (обязательно для event, обязательно для service, общее)
   - enum значения (если применимо)

3. **TODO 3 (Section 6):** Output structure должен:
   - точно соответствовать JSON схеме
   - включать `activity_type` как первый определяющий фактор
   - условно включать event_timing или service_timing (не оба)
   - условно включать event_capacity или service_participation
   - условно включать event_pricing или service_pricing_model

---

### 6.2 Новые алгоритмы парсинга

**Алгоритм определения activity_type:**

```
1. Анализ ввода на индикаторы:
   - Event индикаторы: конкретные даты, "мероприятие", билеты, групповой формат
   - Service индикаторы: "по запросу", "по назначению", индивидуальные сессии, booking

2. Если индикаторы противоречивы:
   - Пометить как ambiguous
   - Запросить уточнение: "Это событие с фиксированным расписанием или услуга по запросу?"

3. Если неясно:
   - По умолчанию: event (если есть даты) или service (если есть "booking"/"записаться")
   - Пометить confidence score как низкий
   - Запросить подтверждение
```

---

### 6.3 Условная экстракция полей

**Правило:**
После определения `activity_type`, парсинг должен:
- Если `activity_type = event`:
  - Извлекать `event_timing`, `event_capacity`, `event_pricing`, `event_cta`
  - НЕ извлекать `service_timing`, `service_participation`, `service_pricing_model`, `service_cta`
  
- Если `activity_type = service`:
  - Извлекать `service_timing`, `service_participation`, `service_pricing_model`, `service_cta`
  - НЕ извлекать `event_timing`, `event_capacity`, `event_pricing`, `event_cta`

---

## 7. Следующие шаги

1. **Получить полную JSON схему** от пользователя
2. **Дополнить task-Ingest-Deep-Parsing.md** с:
   - алгоритмом определения activity_type
   - условной экстракцией полей
   - точными enum значениями
   - структурой вложенных объектов
3. **Обновить task-Ingest-Validation.md** с требованиями к валидации условных полей
4. **Обновить task-Activity-Normalizer.md** с правилами нормализации для event vs service

---

**Статус анализа:** ✅ Завершён  
**Готовность к обсуждению:** ✅ Да  
**Требуется уточнение:** JSON схема, enum значения, структура вложенных объектов
