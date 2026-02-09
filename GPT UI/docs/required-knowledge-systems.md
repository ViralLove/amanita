# Системы мышления и знания для разработки GPT-модуля

**Дата:** 2025-01-13  
**Методология:** @analysis.mdc  
**Задача:** Разработка GPT-модуля как разговорного интерфейса и policy-оркестратора для экосистемы Amanita

---

## 🎯 Цель анализа

Идентифицировать все системы мышления (cognitive systems) и области знаний (knowledge domains), необходимые для успешной разработки GPT-модуля, который будет:
- Разговорным интерфейсом для работы с Activities
- Policy-оркестратором бизнес-логики
- Stateless API клиентом backend системы

---

## 🧠 Системы мышления (Cognitive Systems)

### 1. Conversational AI / Natural Language Understanding

**Описание:** Способность понимать свободный пользовательский ввод, извлекать намерения и контекст из естественного языка.

**Применение:**
- Интерпретация запросов пользователей в свободной форме
- Определение intent (search / add / update / help / policy)
- Извлечение сущностей из диалога (название Activity, дата, формат и т.д.)
- Управление контекстом многошаговых диалогов

**Ключевые навыки:**
- Intent classification
- Named Entity Recognition (NER)
- Context tracking в диалогах
- Disambiguation (разрешение неоднозначностей)
- Multi-turn conversation management

**Примеры использования:**
```
User: "Хочу создать сессию по медитации на следующей неделе"
→ Intent: add
→ Entities: type=сессия, topic=медитация, timeframe=next_week
→ Action: начать диалог ingest для создания Draft Activity
```

---

### 2. Policy & Rule-Based Reasoning

**Описание:** Способность применять бизнес-правила и политики для принятия решений о допустимости действий.

**Применение:**
- Проверка прав доступа (публичный vs активированный режим)
- Применение review workflow правил
- Валидация completeness данных перед отправкой
- Соблюдение GDPR ограничений

**Ключевые навыки:**
- Rule-based decision making
- Policy enforcement
- Conditional logic (if-then-else)
- State transition validation
- Constraint checking

**Примеры правил:**
```
IF user_mode == "guest" AND action == "publish":
    → DENY, explain: "Публикация требует активации"
    
IF activity_status == "Published" AND action == "edit":
    → DENY, explain: "Сначала нужно снять с публикации"
    
IF activity_status == "In Review" AND action == "edit":
    → DENY, explain: "Редактирование запрещено во время review"
```

---

### 3. State Machine / Workflow Orchestration

**Описание:** Понимание и управление состояниями и переходами в системе.

**Применение:**
- Управление lifecycle Activities (Draft → Review → Approved → Published)
- Отслеживание текущего состояния в диалоге
- Валидация допустимых переходов между состояниями
- Обработка edge cases в workflow

**Ключевые навыки:**
- Finite State Machine (FSM) design
- State transition validation
- Workflow orchestration
- State persistence (через API, не локально)
- Recovery from invalid states

**Workflow States:**
```
Draft
  ↓ [submit_for_review]
Sent to Review
  ↓ [approve] / [reject]
Approved / Rejected
  ↓ [publish] (if approved)
Published
  ↓ [unpublish]
Draft (for editing)
```

---

### 4. API Integration & Contract Understanding

**Описание:** Понимание REST API контрактов, структуры запросов/ответов, обработка ошибок.

**Применение:**
- Вызов backend API endpoints
- Структурирование данных под API контракты
- Обработка HTTP статусов и ошибок
- Интерпретация API ответов для пользователя

**Ключевые навыки:**
- REST API design patterns
- HTTP methods (GET, POST, PUT, DELETE)
- Request/Response schema understanding
- Error handling (4xx, 5xx)
- Authentication (HMAC, API keys)
- Rate limiting awareness

**API Patterns:**
```
GET /activities/search?query=...&filters=...
POST /activities/draft { ... }
PUT /activities/{id} { ... }
POST /activities/{id}/submit-review
POST /activities/{id}/publish
DELETE /activities/{id}/unpublish
```

---

### 5. Error Handling & User Experience Design

**Описание:** Способность обрабатывать ошибки и переводить технические сообщения в понятный UX.

**Применение:**
- Интерпретация API ошибок (403, 404, 422, 500)
- Объяснение причин отказов пользователю
- Предложение альтернативных действий
- Graceful degradation при недоступности сервисов

**Ключевые навыки:**
- Error classification (user error vs system error)
- User-friendly error messages
- Recovery suggestions
- Fallback strategies
- Empathy in error communication

**Error Mapping:**
```
403 not_activated → "Для публикации нужна активация через Invite"
403 forbidden → "У вас нет прав на это действие"
404 not_found → "Activity не найдена"
422 validation_error → "Проверьте заполнение полей: [список]"
500 server_error → "Временная проблема, попробуйте позже"
```

---

### 6. Data Validation & Completeness Checking

**Описание:** Проверка полноты и корректности данных перед отправкой в API.

**Применение:**
- Валидация обязательных полей Activity
- Проверка форматов данных (даты, email, URLs)
- Проверка completeness перед submit_for_review
- Предупреждение о недостающих данных

**Ключевые навыки:**
- Schema validation
- Required field checking
- Format validation (regex, types)
- Completeness scoring
- Progressive data collection

**Validation Rules:**
```
Required fields:
- title (string, 1-200 chars)
- description (string, min 50 chars)
- format (enum: session/workshop/retreat/...)
- date (ISO 8601, future date)
- age_group (enum: ...)

Optional but recommended:
- location
- duration
- max_participants
```

---

### 7. Privacy-First Design Thinking

**Описание:** Понимание принципов privacy-first архитектуры и GDPR compliance.

**Применение:**
- Минимизация сбора персональных данных
- Не создание пользовательских профилей
- Не использование персонализации
- Ссылки на Privacy Policy

**Ключевые навыки:**
- Data minimization
- Privacy by design
- GDPR awareness
- Anonymization techniques
- Consent management

**Privacy Rules:**
```
❌ Не спрашивать email/телефон без необходимости
❌ Не сохранять чувствительный контент
❌ Не создавать профили пользователей
❌ Не персонализировать поиск
✅ Ссылаться на Privacy Policy (Arweave)
✅ Объяснять privacy-подход
```

---

## 📚 Области знаний (Knowledge Domains)

### 1. Domain Knowledge: Amanita Ecosystem

**Что нужно знать:**
- Концепция Activators и Activities
- Review workflow (Draft → Review → Approved → Published)
- Gated publication model (публичный поиск, gated публикация)
- On-chain активация через Invite (SpiralEngine)
- Privacy-first принципы экосистемы

**Источники знаний:**
- `GPT UI/docs/concept-and-goals.md`
- `docs/concept/manifest.md`
- `docs/concept/system-layers-overview.md`
- `docs/analysis/basic-documentation-analysis.md`

---

### 2. API Knowledge: Backend API Contracts

**Что нужно знать:**
- Endpoints для работы с Activities
- Request/Response schemas
- Authentication механизм (HMAC, API keys)
- Error codes и их значения
- Rate limiting и quotas

**Источники знаний:**
- `bot/api/docs/API Docs.md`
- `docs/tech/webapi-overview.md`
- `bot/docs/tech/api/api.md`
- Backend API documentation (OpenAPI/Swagger)

**Критические API endpoints:**
```
GET  /activities/search          # Публичный поиск
GET  /activities/{id}           # Получение Activity
POST /activities/draft           # Создание Draft
PUT  /activities/{id}            # Обновление Draft
POST /activities/{id}/submit-review  # Отправка на review
POST /activities/{id}/publish    # Публикация
DELETE /activities/{id}/unpublish # Снятие с публикации
GET  /reference/formats          # Справочник форматов
GET  /reference/taxonomy         # Таксономия
GET  /reference/age-groups       # Возрастные группы
```

---

### 3. Technical Knowledge: GPT/LLM Architecture

**Что нужно знать:**
- Custom GPT инструкции структура
- Function calling / Tool use
- Context window management
- Prompt engineering для intent classification
- Instruction Tree design patterns

**Ключевые концепции:**
- System prompts vs user prompts
- Few-shot learning examples
- Chain-of-thought reasoning
- Structured output (JSON schemas)
- Error recovery patterns

---

### 4. UX Knowledge: Conversational Design

**Что нужно знать:**
- Диалоговые паттерны (ingest, search, help)
- Progressive disclosure (постепенное раскрытие информации)
- Confirmation patterns
- Error recovery flows
- Onboarding flows

**Диалоговые паттерны:**
```
Ingest Pattern:
1. Приветствие и объяснение процесса
2. Пошаговый сбор данных (title → description → format → ...)
3. Подтверждение перед отправкой
4. Обработка ошибок валидации

Search Pattern:
1. Понимание поискового запроса
2. Уточнение фильтров (если нужно)
3. Показ результатов с пагинацией
4. Детальный просмотр выбранного Activity
```

---

### 5. Security Knowledge: Authentication & Authorization

**Что нужно знать:**
- HMAC authentication механизм
- API key management
- Public vs authenticated endpoints
- On-chain activation verification (через backend)
- Error handling для 403 responses

**Security Patterns:**
```
Public Mode:
- Только GET /activities/search
- Только GET /activities/{id}
- Никаких write операций

Authenticated Mode:
- Все операции доступны
- Backend проверяет activation status
- GPT реагирует на 403 not_activated
```

---

## 🔄 Интеграция систем мышления

### Workflow: Обработка запроса пользователя

```
1. Conversational AI
   ↓ [понимание ввода]
   Intent Classification
   
2. Policy & Rule-Based Reasoning
   ↓ [проверка правил]
   Access Control Check
   
3. State Machine
   ↓ [проверка состояния]
   Workflow Validation
   
4. Data Validation
   ↓ [проверка данных]
   Completeness Check
   
5. API Integration
   ↓ [вызов API]
   Backend Request
   
6. Error Handling
   ↓ [обработка ответа]
   User-Friendly Response
```

---

## 📋 Матрица компетенций

| Система мышления | Критичность | Сложность | Приоритет изучения |
|-----------------|-------------|-----------|-------------------|
| **Conversational AI** | P0 | High | 1 |
| **Policy & Rule-Based Reasoning** | P0 | Medium | 2 |
| **State Machine / Workflow** | P0 | Medium | 2 |
| **API Integration** | P0 | Medium | 1 |
| **Error Handling & UX** | P1 | Medium | 3 |
| **Data Validation** | P1 | Low | 3 |
| **Privacy-First Design** | P1 | Low | 4 |

---

## 🎓 Рекомендуемые источники знаний

### Обязательные документы для изучения:

1. **GPT UI/docs/concept-and-goals.md** — архитектурный контекст GPT-модуля
2. **docs/concept/system-layers-overview.md** — общая архитектура экосистемы
3. **bot/api/docs/API Docs.md** — API контракты
4. **docs/tech/webapi-overview.md** — обзор Web API

### Дополнительные ресурсы:

- OpenAI Custom GPT documentation
- REST API design best practices
- Conversational AI patterns
- GDPR compliance guidelines

---

## ✅ Чеклист готовности

Перед началом разработки Instruction Tree необходимо:

- [ ] Изучить все обязательные документы
- [ ] Понять API контракты для Activities
- [ ] Разобраться в review workflow
- [ ] Изучить privacy-first принципы
- [ ] Понять концепцию Activators и Activities
- [ ] Разобраться в gated publication model

---

**Версия документа:** 1.0  
**Дата создания:** 2025-01-13  
**Методология:** @analysis.mdc  
**Статус:** ✅ COMPLETE
