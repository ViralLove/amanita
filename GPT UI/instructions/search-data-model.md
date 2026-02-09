# Search Dialogue — Детальная JSON Schema для Search Query

**Дата:** 2025-01-15  
**Источник:** Activity Data Model + Advanced Search Analysis  
**Цель:** Полная JSON схема для search query, соответствующая Activity Data Model

---

## 1. Обзор Структуры

Search query структура должна поддерживать:
- Поиск по **events** (fixed_dates, recurring)
- Поиск по **services** (availability_windows, by_request)
- Расширенные временные фильтры (конкретные даты, дни недели)
- Расширенные языковые фильтры
- Расширенные локационные фильтры
- Все остальные поля из Activity Data Model

---

## 2. Полная JSON Schema

```json
{
  "query": {
    // Семантический поиск
    "text": "string | null",
    
    // Тип активности (ключевой дискриминатор)
    "activity_type": "event" | "service" | null,
    
    // Фильтры
    "filters": {
      // ============================================
      // ВРЕМЕННЫЕ ФИЛЬТРЫ (расширенные)
      // ============================================
      "time": {
        // Для events: диапазон дат
        "date_range": {
          "start_date": "ISO 8601",
          "end_date": "ISO 8601",
          "timezone": "IANA timezone | null"
        } | null,
        
        // Для events: конкретные даты с временными диапазонами
        "specific_dates": [
          {
            "date": "YYYY-MM-DD",
            "time_range": {
              "start": "HH:MM",
              "end": "HH:MM"
            } | null,
            "timezone": "IANA timezone | null"
          }
        ] | null,
        
        // Для services и recurring events: расписание по дням недели
        "weekly_schedule": [
          {
            "day_of_week": "monday" | "tuesday" | "wednesday" | "thursday" | "friday" | "saturday" | "sunday",
            "time_range": {
              "start": "HH:MM",
              "end": "HH:MM"
            } | null,
            "timezone": "IANA timezone | null"
          }
        ] | null,
        
        // Упрощенные варианты (для обратной совместимости)
        "type": "specific_date" | "date_range" | "soon" | "this_week" | "recurring" | null,
        "start_date": "ISO 8601 | null",
        "end_date": "ISO 8601 | null"
      },
      
      // ============================================
      // ЯЗЫКОВЫЕ ТРЕБОВАНИЯ (расширенные)
      // ============================================
      "language_requirements": {
        "mode": "irrelevant" | "understand_only" | "speak_and_understand" | "mixed" | null,
        "languages_to_understand": ["ru", "en", "et"] | null,  // ISO 639-1 codes
        "languages_to_speak": ["ru", "en", "et"] | null,  // ISO 639-1 codes
        
        // Для семантического поиска (опционально, если backend поддерживает)
        "semantic_search": {
          "enabled": boolean,
          "threshold": number  // default 0.7, range 0.0-1.0
        } | null
      },
      
      // ============================================
      // ЛОКАЦИЯ (расширенная)
      // ============================================
      "location": {
        // Текстовый поиск (из Activity Data Model)
        "city": "string | null",
        "area": "string | null",
        "venue": "string | null",
        
        // Геолокация (если координаты доступны в будущем)
        "coordinates": {
          "longitude": number,
          "latitude": number,
          "radius_km": number
        } | null,
        
        // Для services: service_area
        "service_area": {
          "radius_km": number | null,
          "districts": ["string"] | null
        } | null
      },
      
      // ============================================
      // ОСНОВНЫЕ ФИЛЬТРЫ (из Activity Data Model)
      // ============================================
      
      // Формат активности
      "format": "session" | "workshop" | "ceremony" | "class_regular" | "class_single" | "retreat" | "performance" | "other" | null,
      
      // Категории (двухуровневая таксономия)
      "categories": {
        "primary": "string | null",
        "secondary": ["string"] | null,
        "freeform_tags": ["string"] | null  // для поиска по user tags
      } | null,
      
      // Возрастные группы
      "age_groups": [
        "babies" | "toddlers" | "primary_schoolers" | "teenagers" | 
        "youngsters_18_25" | "adults" | "seniors"
      ] | null,
      
      // Сопровождение родителей
      "parental_accompaniment": "allowed" | "required" | "optional" | null,
      
      // Режим доставки
      "delivery_mode": "in_person" | "online" | "hybrid" | null,
      
      // ============================================
      // ЦЕНООБРАЗОВАНИЕ (из Activity Data Model)
      // ============================================
      "pricing": {
        // Для events
        "event_pricing": {
          "pricing_type": "ticket_price" | "donation" | "free" | null,
          "max_ticket_price": number | null,
          "currency": "ISO 4217 | null"  // e.g., "EUR", "USD"
        } | null,
        
        // Для services
        "service_pricing": {
          "model": "per_session" | "per_hour" | "per_package" | "donation" | "free" | null,
          "max_price": number | null,
          "currency": "ISO 4217 | null"
        } | null,
        
        // Упрощенный вариант (для обратной совместимости)
        "type": "free" | "paid" | null,
        "max_price": number | null,
        "currency": "ISO 4217 | null"
      },
      
      // ============================================
      // УЧАСТИЕ И ВМЕСТИМОСТЬ (из Activity Data Model)
      // ============================================
      "participation": {
        // Для events
        "event_capacity": {
          "min_participants": number | null,
          "max_participants": number | null,
          "available_seats": number | null  // поиск по доступным местам
        } | null,
        
        // Для services
        "service_participation": {
          "session_mode": "one_to_one" | "family" | "small_group" | null
        } | null
      },
      
      // ============================================
      // ДОПОЛНИТЕЛЬНЫЕ ФИЛЬТРЫ
      // ============================================
      
      // Организатор/создатель (поиск по creator/owner_reference)
      "organizer": "string | null",
      
      // Статус активности (обычно только Published, но может быть фильтр)
      "status": "Draft" | "SentToReview" | "Approved" | "Published" | null,
      
      // Поиск по медиа/ссылкам
      "has_media": {
        "official_site": boolean | null,
        "social_links": boolean | null,
        "booking_url": boolean | null  // для services
      } | null
    },
    
    // ============================================
    // ДЕФОЛТНЫЕ ЗНАЧЕНИЯ
    // ============================================
    "defaults": {
      "status": "Published",  // только опубликованные активности
      "implicit_filters": []  // фильтры примененные, но не явно запрошенные
    }
  },
  
  // ============================================
  // ПАГИНАЦИЯ
  // ============================================
  "pagination": {
    "page": number,  // default: 1, min: 1
    "per_page": number  // default: 20, min: 1, max: 100
  },
  
  // ============================================
  // СОРТИРОВКА
  // ============================================
  "sort": {
    "field": "relevance" | "date" | "title" | "price" | "created_at" | null,
    "order": "asc" | "desc" | null
  }
}
```

---

## 3. Детальное Описание Полей

### 3.1 Временные Фильтры

#### `time.date_range`
**Назначение:** Поиск activities в диапазоне дат  
**Применимо к:**
- Events: поиск в `event_timing.fixed_dates` или `event_timing.recurring.start_date/end_date`
- Services: не применимо (services не имеют конкретных дат)

**Пример:**
```json
{
  "date_range": {
    "start_date": "2025-02-01T00:00:00Z",
    "end_date": "2025-02-28T23:59:59Z",
    "timezone": "Europe/Tallinn"
  }
}
```

#### `time.specific_dates`
**Назначение:** Поиск по конкретным датам с опциональными временными диапазонами  
**Применимо к:**
- Events: поиск в `event_timing.fixed_dates` или вычисление из `recurring`
- Services: не применимо

**Пример:**
```json
{
  "specific_dates": [
    {
      "date": "2025-02-15",
      "time_range": {
        "start": "19:00",
        "end": "21:00"
      },
      "timezone": "Europe/Tallinn"
    },
    {
      "date": "2025-02-16",
      "time_range": null,
      "timezone": null
    }
  ]
}
```

#### `time.weekly_schedule`
**Назначение:** Поиск по дням недели с опциональными временными окнами  
**Применимо к:**
- Services: поиск в `service_timing.availability_windows`
- Recurring Events: поиск в `event_timing.recurring` (если RRULE содержит day_of_week)

**Пример:**
```json
{
  "weekly_schedule": [
    {
      "day_of_week": "monday",
      "time_range": {
        "start": "10:00",
        "end": "12:00"
      },
      "timezone": "Europe/Tallinn"
    },
    {
      "day_of_week": "wednesday",
      "time_range": null,
      "timezone": null
    }
  ]
}
```

#### `time.type` (упрощенный вариант)
**Назначение:** Обратная совместимость с текущей схемой  
**Значения:**
- `"specific_date"` — конкретная дата
- `"date_range"` — диапазон дат
- `"soon"` — скоро (сегодня, завтра, на этой неделе)
- `"this_week"` — на этой неделе
- `"recurring"` — повторяющиеся события

### 3.2 Языковые Требования

#### `language_requirements.mode`
**Назначение:** Фильтр по режиму языковых требований  
**Значения:**
- `"irrelevant"` — язык не важен
- `"understand_only"` — требуется только понимание
- `"speak_and_understand"` — требуется и понимание, и говорение
- `"mixed"` — смешанные требования

**Пример использования:**
- Поиск activities где язык не важен: `mode: "irrelevant"`
- Поиск activities где требуется понимание: `mode: "understand_only"`

#### `language_requirements.languages_to_understand`
**Назначение:** Поиск по языкам, которые нужно понимать  
**Формат:** Массив ISO 639-1 кодов (например, `["ru", "en", "et"]`)

#### `language_requirements.languages_to_speak`
**Назначение:** Поиск по языкам, на которых нужно говорить  
**Формат:** Массив ISO 639-1 кодов

#### `language_requirements.semantic_search`
**Назначение:** Включить семантический поиск через embeddings (опционально)  
**Параметры:**
- `enabled`: boolean — включить/выключить семантический поиск
- `threshold`: number — порог схожести (0.0-1.0, default 0.7)

### 3.3 Локация

#### `location.city`, `location.area`, `location.venue`
**Назначение:** Текстовый поиск по локации (из `location_info` в Activity Data Model)

#### `location.coordinates`
**Назначение:** Геолокационный поиск с радиусом (если координаты доступны)  
**Примечание:** Текущая модель не содержит координат, это для будущего расширения

#### `location.service_area`
**Назначение:** Поиск по service area (для services)  
**Поля:**
- `radius_km`: радиус в километрах
- `districts`: массив названий районов

### 3.4 Ценообразование

#### `pricing.event_pricing`
**Назначение:** Фильтры для event pricing  
**Поля:**
- `pricing_type`: тип ценообразования (ticket_price, donation, free)
- `max_ticket_price`: максимальная цена билета
- `currency`: валюта (ISO 4217)

#### `pricing.service_pricing`
**Назначение:** Фильтры для service pricing  
**Поля:**
- `model`: модель ценообразования (per_session, per_hour, per_package, donation, free)
- `max_price`: максимальная цена
- `currency`: валюта

#### `pricing.type`, `pricing.max_price`, `pricing.currency`
**Назначение:** Упрощенный вариант для обратной совместимости

### 3.5 Участие и Вместимость

#### `participation.event_capacity`
**Назначение:** Фильтры для event capacity  
**Поля:**
- `min_participants`: минимальное количество участников
- `max_participants`: максимальное количество участников
- `available_seats`: поиск по доступным местам

#### `participation.service_participation`
**Назначение:** Фильтры для service participation  
**Поля:**
- `session_mode`: режим сессии (one_to_one, family, small_group)

---

## 4. Правила Использования

### 4.1 Условная Логика

**Если `activity_type = "event"`:**
- Используйте `time.date_range`, `time.specific_dates` для временных фильтров
- Используйте `pricing.event_pricing` для фильтров по цене
- Используйте `participation.event_capacity` для фильтров по вместимости

**Если `activity_type = "service"`:**
- Используйте `time.weekly_schedule` для временных фильтров
- Используйте `pricing.service_pricing` для фильтров по цене
- Используйте `participation.service_participation` для фильтров по участию

**Если `activity_type = null`:**
- Backend должен искать в обоих типах
- Применять соответствующие фильтры к каждому типу

### 4.2 Приоритет Фильтров

1. **Временные фильтры:**
   - Если указаны `specific_dates` или `weekly_schedule`, они имеют приоритет над `date_range`
   - Если указан `time.type`, он используется как fallback

2. **Языковые фильтры:**
   - Если указан `mode`, он применяется как основной фильтр
   - `languages_to_understand` и `languages_to_speak` применяются дополнительно

3. **Локационные фильтры:**
   - Если указаны `coordinates`, они имеют приоритет над текстовым поиском
   - `service_area` применяется только для services

### 4.3 Обратная Совместимость

Для обратной совместимости с текущей схемой:
- `time.type`, `time.start_date`, `time.end_date` поддерживаются
- `pricing.type`, `pricing.max_price`, `pricing.currency` поддерживаются
- Backend должен интерпретировать упрощенные варианты и преобразовывать их в расширенные

---

## 5. Примеры Запросов

### 5.1 Поиск Events в Конкретную Дату

```json
{
  "query": {
    "text": "yoga classes",
    "activity_type": "event",
    "filters": {
      "time": {
        "specific_dates": [
          {
            "date": "2025-02-15",
            "time_range": {
              "start": "19:00",
              "end": "21:00"
            },
            "timezone": "Europe/Tallinn"
          }
        ]
      },
      "format": "class_regular"
    }
  },
  "pagination": {
    "page": 1,
    "per_page": 20
  },
  "sort": {
    "field": "date",
    "order": "asc"
  }
}
```

### 5.2 Поиск Services по Дням Недели

```json
{
  "query": {
    "text": "coaching",
    "activity_type": "service",
    "filters": {
      "time": {
        "weekly_schedule": [
          {
            "day_of_week": "monday",
            "time_range": {
              "start": "10:00",
              "end": "12:00"
            },
            "timezone": "Europe/Tallinn"
          },
          {
            "day_of_week": "wednesday",
            "time_range": {
              "start": "14:00",
              "end": "16:00"
            },
            "timezone": "Europe/Tallinn"
          }
        ]
      },
      "language_requirements": {
        "languages_to_understand": ["ru", "en"]
      }
    }
  }
}
```

### 5.3 Поиск с Расширенными Языковыми Фильтрами

```json
{
  "query": {
    "text": "workshops",
    "filters": {
      "language_requirements": {
        "mode": "understand_only",
        "languages_to_understand": ["ru"],
        "semantic_search": {
          "enabled": true,
          "threshold": 0.7
        }
      },
      "age_groups": ["adults"],
      "delivery_mode": "in_person",
      "location": {
        "city": "Tallinn"
      }
    }
  }
}
```

### 5.4 Поиск с Фильтрами по Цене

```json
{
  "query": {
    "activity_type": "event",
    "filters": {
      "pricing": {
        "event_pricing": {
          "pricing_type": "ticket_price",
          "max_ticket_price": 50,
          "currency": "EUR"
        }
      },
      "time": {
        "date_range": {
          "start_date": "2025-02-01T00:00:00Z",
          "end_date": "2025-02-28T23:59:59Z"
        }
      }
    }
  }
}
```

---

## 6. Маппинг на Activity Data Model

### 6.1 Events

| Search Query Field | Activity Data Model Field |
|-------------------|---------------------------|
| `time.date_range` | `event_timing.fixed_dates[*].start/end` или `event_timing.recurring.start_date/end_date` |
| `time.specific_dates` | `event_timing.fixed_dates[*]` или вычисление из `recurring` |
| `time.weekly_schedule` | `event_timing.recurring` (если RRULE содержит day_of_week) |
| `pricing.event_pricing` | `event_pricing` |
| `participation.event_capacity` | `event_capacity` |

### 6.2 Services

| Search Query Field | Activity Data Model Field |
|-------------------|---------------------------|
| `time.weekly_schedule` | `service_timing.availability_windows[*]` |
| `pricing.service_pricing` | `service_pricing_model` |
| `participation.service_participation` | `service_participation` |
| `location.service_area` | `service_area` |

### 6.3 Общие Поля

| Search Query Field | Activity Data Model Field |
|-------------------|---------------------------|
| `text` | `title`, `short_summary`, `full_description` |
| `filters.format` | `format` |
| `filters.categories` | `categories` |
| `filters.age_groups` | `age_groups` |
| `filters.language_requirements` | `language_requirements` |
| `filters.delivery_mode` | `delivery_mode` |
| `filters.location.city/area/venue` | `location_info` |

---

## 7. Рекомендации по Реализации

### 7.1 Backend Implementation

1. **Валидация:**
   - Проверять соответствие фильтров `activity_type`
   - Валидировать форматы дат, времени, timezone
   - Проверять ISO коды языков и валют

2. **Обработка:**
   - Преобразовывать упрощенные варианты в расширенные
   - Применять фильтры к соответствующему типу активности
   - Обрабатывать `activity_type = null` (поиск в обоих типах)

3. **Оптимизация:**
   - Использовать индексы для временных фильтров
   - Использовать индексы для языковых фильтров
   - Кэшировать результаты семантического поиска

### 7.2 Frontend/GPT Implementation

1. **Natural Language Processing:**
   - Извлекать конкретные даты из natural language
   - Извлекать дни недели и временные окна
   - Извлекать языковые требования

2. **Query Building:**
   - Использовать расширенные фильтры когда возможно
   - Fallback на упрощенные варианты для обратной совместимости
   - Валидировать структуру перед отправкой

---

**Статус:** ✅ Детальная JSON Schema готова  
**Использование:** Reference для Search Dialogue Instruction и API Orchestrator
