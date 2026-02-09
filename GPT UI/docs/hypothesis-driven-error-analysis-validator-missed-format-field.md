# Worklog: Валидатор пропустил проверку обязательного поля `format` перед отправкой на ревью

**Дата:** 2026-01-23  
**Задача:** Тестирование GPT инструкций  
**Проблема:** Activity была отправлена на ревью, но потом выяснилось, что недостаточно полей (отсутствует `format`). Валидатор должен был проверить это перед отправкой, но почему-то пропустил.

---

## 1. Описание ошибки

### Симптомы

**Сообщение от GPT:**
```
Сейчас не хватает 1 обязательного поля

format — выбери одно значение (можно просто словом ответить):
- performance (похоже на концерт/саунд-перформанс)
- session
- workshop
- ceremony
- class_single / class_regular
- retreat
- other (тогда нужно ещё format_other_label)

Напиши, пожалуйста, одним словом: performance или другое из списка — и я зафиксирую статус SentToReview-ready и передам дальше в КоныРода Gate по правильному workflow.
```

**Контекст:**
- Пользователь отправил Activity на ревью (статус `SentToReview`)
- GPT выполнил операцию `POST /activities/{id}/submit-review`
- После отправки выяснилось, что не хватает обязательного поля `format`
- Валидатор должен был проверить это **до** отправки на ревью, но не сделал этого

**Ожидаемое поведение:**
- Валидатор должен проверить все обязательные поля для статуса `SentToReview-ready` (Section 4.2 в `ingest-validation.md`)
- Если поле `format` отсутствует → REJECT, запросить у пользователя
- НЕ отправлять на ревью до тех пор, пока все обязательные поля не заполнены

**Фактическое поведение:**
- Валидатор пропустил проверку поля `format`
- Activity была отправлена на ревью без обязательного поля
- Ошибка обнаружена только после отправки (возможно, на стороне backend или в Gate)

### Диагностическая информация

**Обязательные поля для `SentToReview-ready` (из `ingest-validation.md` Section 4.2):**
- All Draft requirements +
- `full_description` (string) — required, minimum 50 characters
- `format` (enum) — required ← **ЭТО ПОЛЕ ОТСУТСТВУЕТ**
- `delivery_mode` (enum) — required
- `location_info` (object) — required if `delivery_mode != "online"`
- `event_timing` (object) — required if `activity_type = "event"`

**Workflow согласно архитектуре:**
```
1. Base Instruction → определяет INGEST mode
2. Ingest Validation → валидирует данные для SentToReview-ready
3. KоныРода Gate → проверяет policy compliance (если SentToReview-ready)
4. Activity Normalizer → нормализует данные
5. API Orchestrator → вызывает POST /activities/{id}/submit-review
```

**Критично:** Валидация должна происходить **ДО** вызова API Orchestrator (шаг 2), но похоже, что она либо не была вызвана, либо была вызвана некорректно.

---

## 2. Анализ возможных источников проблемы

### 2.1 Валидация не была вызвана перед submit-review

**Гипотеза:** GPT пропустил вызов Ingest Validation перед отправкой на ревью. Вместо этого GPT напрямую передал данные в API Orchestrator, минуя валидацию.

**Обоснование:**
- API Orchestrator НЕ выполняет валидацию данных (явно указано в `api-orchestrator.md`: "API Orchestrator does NOT validate data structure (already validated by Normalizer)")
- API Orchestrator проверяет только минимальный input contract (структура JSON, наличие `activity_type`, `status`, `title`)
- Если Validation не была вызвана, API Orchestrator не знает о недостающих полях
- Workflow может быть нарушен, если пользователь напрямую попросил "отправить на ревью" без явного прохождения валидации

**Вероятность:** 🔴 Высокая (наиболее вероятная причина)

**Влияние:** P0 (критично, блокирует корректную работу workflow)

**Сложность проверки:** Средняя (требует анализа логов GPT или тестирования workflow)

**Как проверить:**
- Проверить логи GPT: была ли вызвана Ingest Validation перед submit-review?
- Протестировать сценарий: попросить GPT "отправить на ревью" без явного прохождения валидации
- Проверить, есть ли в инструкциях явное требование вызывать Validation перед submit-review

---

### 2.2 Валидация была вызвана, но только для Draft, а не для SentToReview-ready

**Гипотеза:** GPT вызвал валидацию для статуса `Draft`, но не вызвал валидацию для статуса `SentToReview-ready` перед отправкой на ревью. Валидация для Draft не проверяет поле `format` (оно требуется только для SentToReview).

**Обоснование:**
- В `ingest-validation.md` есть два уровня валидации:
  - Section 4.1: Draft-Level Validation (не требует `format`)
  - Section 4.2: Review-Level Validation (требует `format`)
- Если GPT валидировал только для Draft, поле `format` не проверялось
- Когда пользователь попросил "отправить на ревью", GPT мог не вызвать Review-Level Validation

**Вероятность:** 🔴 Высокая

**Влияние:** P0 (критично, блокирует корректную работу workflow)

**Сложность проверки:** Средняя (требует анализа логов GPT или тестирования workflow)

**Как проверить:**
- Проверить логи GPT: какой уровень валидации был вызван (Draft или SentToReview)?
- Протестировать сценарий: создать Draft, затем попросить "отправить на ревью" и проверить, вызывается ли Review-Level Validation
- Проверить инструкции: есть ли явное требование вызывать Review-Level Validation перед submit-review?

---

### 2.3 GPT неправильно интерпретировал intent и пропустил валидацию

**Гипотеза:** Пользователь попросил "отправить на ревью", GPT интерпретировал это как прямую команду к API Orchestrator, минуя валидацию. GPT не понял, что перед отправкой на ревью нужно сначала проверить все обязательные поля.

**Обоснование:**
- Base Instruction определяет intent и роутит в соответствующий модуль
- Если пользователь говорит "отправить на ревью", GPT может интерпретировать это как прямую команду, а не как запрос на прохождение workflow
- В инструкциях может не быть явного требования вызывать Validation перед submit-review в контексте прямого запроса пользователя

**Вероятность:** 🟡 Средняя

**Влияние:** P0 (критично, блокирует корректную работу workflow)

**Сложность проверки:** Средняя (требует анализа инструкций и тестирования intent interpretation)

**Как проверить:**
- Проверить инструкции Base Instruction: как обрабатывается intent "отправить на ревью"?
- Протестировать сценарий: попросить GPT "отправить на ревью" и проверить, вызывается ли Validation
- Проверить, есть ли в инструкциях явное требование: "Перед submit-review ВСЕГДА вызывать Review-Level Validation"

---

### 2.4 Валидация была вызвана, но GPT не дождался результата и продолжил

**Гипотеза:** GPT вызвал валидацию, но не дождался полного результата проверки всех полей и продолжил выполнение, отправив данные в API Orchestrator. Возможно, валидация была прервана или GPT неправильно интерпретировал результат валидации.

**Обоснование:**
- Валидация может быть асинхронной или многошаговой
- GPT может неправильно интерпретировать результат валидации (например, если валидация вернула "Draft-ready" вместо "SentToReview-ready")
- Если валидация не завершилась полностью, GPT мог продолжить выполнение

**Вероятность:** 🟢 Низкая

**Влияние:** P1 (важно, влияет на функциональность)

**Сложность проверки:** Долгая (требует анализа внутреннего состояния GPT и логирования)

**Как проверить:**
- Проверить логи GPT: была ли валидация вызвана и какой результат она вернула?
- Протестировать сценарий: вызвать валидацию и проверить, дожидается ли GPT полного результата
- Проверить инструкции: есть ли явное требование дожидаться завершения валидации перед продолжением?

---

### 2.5 Ошибка в логике валидации: поле `format` не проверяется корректно

**Гипотеза:** Валидация была вызвана, но в логике валидации есть ошибка: поле `format` не проверяется корректно, или проверка происходит только при определенных условиях, которые не были выполнены.

**Обоснование:**
- В `ingest-validation.md` Section 4.2 есть алгоритм проверки `format`:
  ```
  - If format missing → REJECT
    - Error: "Format is required for review submission..."
    - Request format
  ```
- Но возможно, эта проверка происходит только при определенных условиях (например, только если `activity_type` определен)
- Или проверка `format` происходит после других проверок, и если одна из предыдущих проверок не прошла, проверка `format` не выполняется

**Вероятность:** 🟡 Средняя

**Влияние:** P0 (критично, блокирует корректную работу workflow)

**Сложность проверки:** Средняя (требует анализа кода валидации в инструкциях)

**Как проверить:**
- Прочитать `ingest-validation.md` Section 4.2 и проверить логику проверки `format`
- Протестировать сценарий: создать Activity без поля `format` и попросить отправить на ревью, проверить, вызывается ли проверка `format`
- Проверить, есть ли условия, при которых проверка `format` пропускается

---

### 2.6 Поле `format` было удалено или потеряно между валидацией и отправкой

**Гипотеза:** Валидация была вызвана и прошла успешно (поле `format` было проверено), но между валидацией и отправкой на ревью поле `format` было удалено или потеряно (например, в процессе нормализации или передачи данных между модулями).

**Обоснование:**
- Workflow включает несколько модулей: Validation → Gate → Normalizer → API Orchestrator
- Если один из модулей удаляет или модифицирует поле `format`, оно может быть потеряно
- Normalizer может удалить поле, если оно не соответствует каноническому формату

**Вероятность:** 🟢 Низкая

**Влияние:** P1 (важно, влияет на функциональность)

**Сложность проверки:** Средняя (требует анализа передачи данных между модулями)

**Как проверить:**
- Проверить инструкции Normalizer: может ли он удалить поле `format`?
- Протестировать сценарий: создать Activity с полем `format`, пройти через весь workflow и проверить, сохраняется ли поле `format`
- Проверить логи передачи данных между модулями

---

## 3. Приоритизация гипотез

**Порядок проверки (по убыванию приоритета):**

1. **Гипотеза 2.1: Валидация не была вызвана перед submit-review** (🔴 Высокая вероятность, P0, Средняя сложность)
2. **Гипотеза 2.2: Валидация была вызвана только для Draft, а не для SentToReview-ready** (🔴 Высокая вероятность, P0, Средняя сложность)
3. **Гипотеза 2.5: Ошибка в логике валидации** (🟡 Средняя вероятность, P0, Средняя сложность)
4. **Гипотеза 2.3: GPT неправильно интерпретировал intent** (🟡 Средняя вероятность, P0, Средняя сложность)
5. **Гипотеза 2.4: Валидация была вызвана, но GPT не дождался результата** (🟢 Низкая вероятность, P1, Долгая сложность)
6. **Гипотеза 2.6: Поле `format` было удалено между валидацией и отправкой** (🟢 Низкая вероятность, P1, Средняя сложность)

---

## 4. Рекомендуемое решение

### Решение 1: Добавить явное требование вызывать Review-Level Validation перед submit-review (приоритет: P0)

**Действие:** Добавить в инструкции явное требование, что перед операцией `submit-review` ВСЕГДА должна быть вызвана Review-Level Validation (Section 4.2 из `ingest-validation.md`).

**Где добавить:**
- `base.md`: Добавить правило в Section 1 (INGEST Mode) или Section 2 (State Transitions)
- `api-orchestrator.md`: Добавить проверку в Pre-Execution Validation (Section 17.2)
- `ingest-validation.md`: Добавить явное требование в Section 4.2, что валидация должна быть вызвана перед submit-review

**Реализация:**

**В `base.md` (Section 2 - State Transitions):**
```markdown
### Draft → SentToReview Transition

**Before transitioning to SentToReview:**
1. MUST call Review-Level Validation (ingest-validation.md Section 4.2)
2. MUST verify validation_status = "SentToReview-ready"
3. MUST NOT proceed if validation fails
4. MUST request missing fields from user if validation fails

**If validation_status is not "SentToReview-ready":**
- DO NOT call submit-review API
- Explain to user: "Before submitting for review, the following fields are required: [list missing fields]"
- Request missing fields
```

**В `api-orchestrator.md` (Section 17.2 - Pre-Execution Validation):**
```markdown
**4. State Transition Validation (for submit-review):**

Before executing submit-review operation:
- MUST verify that Review-Level Validation was called
- MUST verify that validation_status = "SentToReview-ready"
- MUST verify that all required fields for SentToReview are present:
  * full_description (≥50 characters)
  * format (enum)
  * delivery_mode (enum)
  * location_info (if delivery_mode != "online")
  * event_timing (if activity_type = "event")
  * service_timing (if activity_type = "service")
- IF any required field is missing:
    → DO NOT call submit-review API
    → Explain to user: "Before submitting for review, the following fields are required: [list missing fields]"
    → Request missing fields from user
```

**Преимущества:**
- ✅ Решает проблему пропуска валидации (гипотезы 2.1, 2.2, 2.3)
- ✅ Явное требование в инструкциях предотвращает ошибки
- ✅ Минимальные изменения в коде (только инструкции)

---

### Решение 2: Добавить проверку обязательных полей в API Orchestrator Pre-Execution Validation (приоритет: P0)

**Действие:** Добавить в API Orchestrator проверку обязательных полей для `SentToReview-ready` перед вызовом `submit-review` API, даже если валидация уже была вызвана.

**Где добавить:**
- `api-orchestrator.md` Section 17.2 (Pre-Execution Validation)

**Реализация:**

```markdown
**4. State Transition Validation (for submit-review):**

Before executing submit-review operation:
- MUST verify that all required fields for SentToReview are present:
  * full_description (string, ≥50 characters)
  * format (enum, required)
  * delivery_mode (enum, required)
  * location_info (object, required if delivery_mode != "online")
  * event_timing (object, required if activity_type = "event")
  * service_timing (object, required if activity_type = "service")
- IF any required field is missing:
    → DO NOT call submit-review API
    → Explain to user: "Before submitting for review, the following fields are required: [list missing fields]"
    → Request missing fields from user
    → Reference: ingest-validation.md Section 4.2
```

**Преимущества:**
- ✅ Дополнительная защита на уровне API Orchestrator
- ✅ Решает проблему даже если валидация была пропущена
- ✅ Соответствует принципу "defense in depth"

**Недостатки:**
- ⚠️ Дублирует логику валидации (но это приемлемо для критичных проверок)

---

### Решение 3: Улучшить логику валидации в ingest-validation.md (приоритет: P1)

**Действие:** Убедиться, что проверка поля `format` выполняется корректно и не пропускается при любых условиях.

**Где проверить:**
- `ingest-validation.md` Section 4.2 (Review-Level Validation)

**Проверка:**
- Убедиться, что проверка `format` происходит в правильном порядке (после проверки Draft requirements, но до проверки conditional fields)
- Убедиться, что проверка `format` не зависит от других условий (кроме наличия самого поля)
- Убедиться, что ошибка для `format` возвращается явно и понятно

**Преимущества:**
- ✅ Улучшает качество валидации
- ✅ Предотвращает ошибки в логике валидации (гипотеза 2.5)

---

## 5. Выбор решения

**Рекомендуется применить все три решения:**

1. **Решение 1 (P0):** Добавить явное требование вызывать Review-Level Validation перед submit-review
2. **Решение 2 (P0):** Добавить проверку обязательных полей в API Orchestrator Pre-Execution Validation
3. **Решение 3 (P1):** Улучшить логику валидации в ingest-validation.md

**Обоснование:**
- Решение 1 предотвращает пропуск валидации на уровне workflow
- Решение 2 добавляет дополнительную защиту на уровне API Orchestrator (defense in depth)
- Решение 3 улучшает качество самой валидации

**Приоритет внедрения:**
1. Сначала Решение 1 (критично, предотвращает основную проблему)
2. Затем Решение 2 (дополнительная защита)
3. Затем Решение 3 (улучшение качества)

---

## 6. Тестирование после исправления

**Чек-лист проверки:**

- [ ] Создать Activity без поля `format`
- [ ] Попросить GPT "отправить на ревью"
- [ ] Проверить, что GPT вызывает Review-Level Validation
- [ ] Проверить, что GPT обнаруживает отсутствие поля `format`
- [ ] Проверить, что GPT НЕ вызывает submit-review API до заполнения `format`
- [ ] Проверить, что GPT запрашивает поле `format` у пользователя
- [ ] Заполнить поле `format`
- [ ] Попросить GPT "отправить на ревью" снова
- [ ] Проверить, что GPT вызывает submit-review API только после успешной валидации

---

## 7. Вывод

**Наиболее вероятные причины:**
1. Валидация не была вызвана перед submit-review (гипотеза 2.1)
2. Валидация была вызвана только для Draft, а не для SentToReview-ready (гипотеза 2.2)

**Рекомендуемое решение:**
- Добавить явное требование вызывать Review-Level Validation перед submit-review
- Добавить проверку обязательных полей в API Orchestrator Pre-Execution Validation
- Улучшить логику валидации в ingest-validation.md

**Следующие шаги:**
1. Применить Решение 1: Добавить явное требование в `base.md` и `api-orchestrator.md`
2. Применить Решение 2: Добавить проверку обязательных полей в `api-orchestrator.md` Section 17.2
3. Протестировать исправления согласно чек-листу
4. Если проблема сохраняется, проверить гипотезы 2.3, 2.4, 2.5, 2.6

---

**Версия:** 1.0  
**Последнее обновление:** 2026-01-23  
**Статус:** Анализ завершен, решения определены
