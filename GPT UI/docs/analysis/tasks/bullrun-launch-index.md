## GPT Instruction Modules — Tasks Index (табличный, Jira-style)

**Зона:** `GPT UI/docs/analysis/tasks/`  
**Цель:** живая карта постановок Custom GPT (ингест, политика, API, поиск) со статусами и приоритетами в одном экране; точка входа для run-task / run-phase без дублирования полных постановок.

**Стандарт оформления:** [index-standard-bullrun-fullpower.md](../../../../docs/methodology/index-standard-bullrun-fullpower.md) · **Постановки:** [task-standard.md](../../../../docs/methodology/task-standard.md) · **Анализ:** `@.cursor/commands/run-analysis.md`

**Соседние индексы:** Bot API / backend — точка входа [bullrun-launch-index.md](../../../../bot/docs/analysis/tasks/bullrun-launch-index.md) · полная таблица [bot-tasks-index.md](../../../../bot/docs/analysis/tasks/bot-tasks-index.md).

**Канон вне `task-*.md` (не строки таблицы):**

- Модель данных Activity: [data-model.md](../../data-model.md) (SSOT полей для инструкций).
- Bot API для интеграции: [api.md](../../../../bot/docs/tech/api/api.md).

**Граф зависимостей (кратко):** Data Model → Base → (Safety ∥ Ingest: Deep Parsing → Validation → KоныРода Gate → Normalizer → API Orchestrator); Search Dialogue → API Orchestrator; опционально Results Presenter / Deduplication после ядра.

---

### 0. Foundation

**Коды статусов:** ⚪ = 0 — Todo, 🟡 = 1 — In Progress, 🔵 = 2 — Implemented (Waiting Acceptance), 🟢 = 3 — Done.

Для **инструкционных** модулей GPT колонка **Status** уточняет: доставлена ли инструкция в `GPT UI/instructions/` и закрыт ли приёмочный контур таска; коммиты в git — отдельное решение по методике.

| S | Key | Task | Type | Status | Scope / Notes |
|---|-----|------|------|--------|---------------|
| 🟢 | GIM-BAS-1 | [task-base-functions](./task-base-functions.md) | implement | Done (instruction) | Функциональная конституция Base Instruction (`base.md`): режимы, lifecycle, privacy, authority. |
| 🟢 | GIM-BAS-2 | [task-base-functions-implementation-algorithm](./task-base-functions-implementation-algorithm.md) | data | Done | Алгоритм внедрения/синхронизации с модулями (опорный документ к BAS-1). |

---

### 1. Safety & Ingest (ввод)

| S | Key | Task | Type | Status | Scope / Notes |
|---|-----|------|------|--------|---------------|
| 🟢 | GIM-SAF-1 | [task-Safety & Compliance](./task-Safety%20%26%20Compliance.md) | implement | Done (instruction) | `safety-compliance.md`; override authority; интеграция с Base. |
| 🟢 | GIM-ING-1 | [task-Ingest-Deep-Parsing](./task-Ingest-Deep-Parsing.md) | implement | Done (instruction) | `ingest-deep-parsing.md`; парсинг форматов; контракт для Validation. |
| 🟢 | GIM-ING-2 | [task-Ingest-validation](./task-Ingest-validation.md) | implement | Done (instruction) | `ingest-validation.md`; правила Draft/SentToReview/Approved. |
| 🟢 | GIM-ING-1P | [task-Ingest-Deep-Parsing-implementation-plan](./task-Ingest-Deep-Parsing-implementation-plan.md) | data | Done | План фаз для ING-1 (см. таск ING-1 как SSOT постановки). |
| 🟢 | GIM-ING-2P | [task-Ingest-Validation-implementation-plan](./task-Ingest-Validation-implementation-plan.md) | data | Done | План фаз для ING-2. |

---

### 2. Policy & Normalization

| S | Key | Task | Type | Status | Scope / Notes |
|---|-----|------|------|--------|---------------|
| 🟢 | GIM-KON-1 | [task-Kоны-Рода-Gate](./task-Kоны-Рода-Gate.md) | implement | Done (instruction) | `konyrody-gate.md`; admission после Validation. |
| 🟢 | GIM-NOR-1 | [task-activity-normalizer](./task-activity-normalizer.md) | implement | Done (instruction) | `activity-normalizer.md`; canonical JSON для API Orchestrator. |
| 🟢 | GIM-KON-1P | [task-KоныРода-Gate-implementation-plan](./task-KоныРода-Gate-implementation-plan.md) | data | Done | План фаз для KON-1. |
| 🟢 | GIM-NOR-1P | [task-Activity-Normalizer-implementation-plan](./task-Activity-Normalizer-implementation-plan.md) | data | Done | План фаз для NOR-1. |

---

### 3. Execution, Search & Backend wire-up

| S | Key | Task | Type | Status | Scope / Notes |
|---|-----|------|------|--------|---------------|
| 🟢 | GIM-ORC-1 | [task-API-Orchestrator](./task-API-Orchestrator.md) | implement | Done (instruction) | `api-orchestrator.md`; единственный модуль прямых вызовов backend API из GPT. Аудит: `../api-orchestrator-critical-audit.md`. |
| 🟢 | GIM-ORC-1P | [task-API-Orchestrator-implementation-plan](./task-API-Orchestrator-implementation-plan.md) | data | Done | План фаз для ORC-1. |
| 🟢 | GIM-REQ-1 | [task-API-Methods-Requirements](./task-API-Methods-Requirements.md) | data | Done | Требования к методам API (опора для ORC / reference). |
| 🟢 | GIM-BCK-0 | [task-implement-gpt-actions-api-key-bearer-activities](../../../../bot/docs/analysis/tasks/task-implement-gpt-actions-api-key-bearer-activities/task-implement-gpt-actions-api-key-bearer-activities.md) | implement | Done (код + доки) | **Bullrun / Custom GPT Actions:** `GPT_ACTIONS_BEARER_SECRET` + middleware на `/activities`, `/reference`; `api.md` §3.3; фрагмент `securitySchemes` в `GPT UI/instructions/api-methods-reference.md`. **Оператор:** задать секрет в `.env` и в GPT Actions (API Key → Bearer). **Связь с BCK-1:** prod Action — выставить секрет на стенде перед E2E. |
| 🟢 | GIM-BCK-0A | [task-add-custom-gpt-actions-openapi-yaml](./task-add-custom-gpt-actions-openapi-yaml/task-add-custom-gpt-actions-openapi-yaml.md) | add | Done | **OpenAPI YAML:** `GPT UI/docs/custom-gpt-actions-activities-reference.openapi.yaml`; лог `BULLRUN-PHASE-LOG.md`, приёмка `acceptance-verification-gim-bck-0a.md`. Ссылки в `api-methods-reference`, `operator-deploy-checklist`, `bot/docs/tech/api/README.md`. Автоген из `app.openapi()` пока блокируется Pydantic — схема ручная по роутам. |
| 🟡 | GIM-BCK-1 | [task-implement-gpt-backend-activity-creation-integration](./task-implement-gpt-backend-activity-creation-integration/task-implement-gpt-backend-activity-creation-integration.md) | implement | In Progress | Папка таска + bullrun-лог, operator checklist, правки `api-orchestrator` / `api-methods-reference` / architecture doc (SSOT vs Bearer). **Осталось:** E2E curl/Action + заполнить `acceptance-verification-*.md`; коммиты по согласованию. **Зависимость (prod):** см. **GIM-BCK-0** — иначе Bearer в настройках GPT не даёт границы на сервере. |
| ⚪ | GIM-BCK-2 | [task-implement-activity-resolve-by-upload-id](../../../../bot/docs/analysis/tasks/task-implement-activity-resolve-by-upload-id/task-implement-activity-resolve-by-upload-id.md) | implement | Todo (backend) | **Новая строка (bullrun):** связка upload→activity для GPT после подписи. **Код:** в `bot/api` нет маршрута `GET /activities/by-upload/{upload_id}` (подтверждено grep по `bot/api`); в `api.md` §9 помечено как пробел. GPT-интеграция логически следует за BCK-1. Таск ведётся в `bot/docs/analysis/tasks/`. |
| 🟢 | GIM-SEA-1 | [task-Search Dialogue](./task-Search%20Dialogue.md) | implement | Done (instruction) | `search-dialogue.md`; поиск через Orchestrator. Аудит: `../search-dialogue-final-acceptance-audit.md`. |
| 🟢 | GIM-SEA-1P | [task-Search-Dialogue-implementation-plan](./task-Search-Dialogue-implementation-plan.md) | data | Done | План фаз для SEA-1. |

---

### 4. Presentation & optional layers

| S | Key | Task | Type | Status | Scope / Notes |
|---|-----|------|------|--------|---------------|
| ⚪ | GIM-PRE-1 | [task-Results Presenter](./task-Results%20Presenter.md) | implement | Todo | **Почему открыт:** в `GPT UI/instructions/` нет модуля results-presenter (glob по `*results*` пуст). **Факт:** файл постановки `./task-Results Presenter.md` начинается с заголовка «Search Dialogue Instruction» — **дубликат содержимого Search Dialogue**, не спецификация Presenter; без исправления постановки или нового task-файла инструкцию не написать. Search Dialogue явно исключает «result presentation formatting» (см. свой task). |
| ⚪ | GIM-DED-1 | [task-Deduplication](./task-Deduplication.md) | implement | Todo | **Почему открыт:** постановка в task-файле есть, файла инструкции в `GPT UI/instructions/` нет (glob `*dedup*` пуст). Реализация не начиналась; в диалоге приоритет был у цепочки ingest→API. |

---

### 5. Cross-cutting (strict protocol, bootstrap, вводной сетап)

| S | Key | Task | Type | Status | Scope / Notes |
|---|-----|------|------|--------|---------------|
| ⚪ | GIM-SPT-1 | [task-implement-strict-protocol-mode-ingest-workflow](./task-implement-strict-protocol-mode-ingest-workflow.md) | implement | Todo (draft в таске) | **Почему открыт:** в таске `**Статус:** draft`; формальные AC/фазы 8–9 по `task-execution-process.md` не зафиксированы как закрытые. **Код/инструкции:** в `base.md` уже есть §1.5 Strict Protocol Mode, handoff rules и связка с артефактами; часть целей таска **вшита в инструкцию**, но постановка таска описывает полный CI/CD-like контур (шире одной секции). Закрытие: либо сузить scope таска под фактический текст, либо добрать недостающее в модулях и пройти верификацию. Логи: `../strict-protocol-*.md`. |
| ⚪ | GIM-SPT-1P | [task-implement-strict-protocol-mode-ingest-workflow-implementation-plan](./task-implement-strict-protocol-mode-ingest-workflow-implementation-plan.md) | data | Todo | Открыт вслед за SPT-1; обновить после смены статуса родительского таска. |
| 🟡 | GIM-COM-1 | [task-implement-communication-bootstrap-implementation-plan](./task-implement-communication-bootstrap-implementation-plan.md) | implement | In Progress (сверка) | **Почему не «Done» в индексе раньше:** в диалоге оставались пошаговые чеклисты (Bootstrap в root/base) без финального прогона сценариев и обновления `**Статус:**` в плане. **Факт кода:** `bootstrap.md` существует; `root.md` §Communication Bootstrap ссылается на него; `base.md` §8 Communication Context Application (`comm_context`) — **реализация в репо есть**. Несоответствие: документ «План реализации» vs фактическая доставка; нужно закрыть AC в плане или переименовать ключ в Done после явной приёмки. |
| ⚪ | GIM-INT-1 | [task-Intro-setup](./task-Intro-setup.md) | data | Todo | **Почему открыт:** в таске статус «task готов»; не перенесён в операционный чеклист Custom GPT / не синхронизирован с текущими файлами пресетов в `instruction-modules-index.md`. Нет блокирующей зависимости от кода бекенда. |

---

### 6. Как пользоваться этим индексом

- **Новая работа по модулю:** найти секцию (Foundation / Ingest / …) и строку **Key**; открыть **Task**; вести run-task по `task-execution-process.md`; обновить здесь **S** и **Status**, когда меняется блок `**Статус:**` в файле таска.
- **Новый gap:** завести `task-<тип>-<slug>.md` по [task-standard.md](../../../../docs/methodology/task-standard.md), добавить **одну** строку в подходящую таблицу; **Key** в формате `GIM-<AREA>-<NN>`.
- **Источник истины по содержанию:** файл постановки таска; индекс только агрегирует ссылки и метаданные.
- **Статусы (Jira-style, см. bullrun):**
  - **Todo (⚪)** — постановка есть, работа не начата или не перенесена в инструкцию.
  - **In Progress (🟡)** — активные фазы run-task / правки инструкции.
  - **Implemented / Waiting Acceptance (🔵)** — черновик инструкции или кода есть, нужна формальная приёмка (редко для чистых GPT-инструкций).
  - **Done (🟢)** — для строк с инструкцией: модуль в `GPT UI/instructions/` доставлен и таск закрыт по AC; коммиты/push — отдельно.

---

### 7. Риски «костылей» по порядку модулей (напоминание)

1. Validation до Deep Parsing — двойная переделка валидации.  
2. Normalizer до Validation — нормализация невалидных данных.  
3. API Orchestrator до Normalizer — нормализация внутри оркестратора.  
4. Safety после всех модулей — ретро-встраивание проверок.  
5. KоныРода Gate после Normalizer — policy по уже нормализованным данным без договорённости.

---

**Последнее обновление индекса:** 2026-03-29 — **GIM-BCK-0A** закрыт (YAML артефакт + доки); см. `BULLRUN-PHASE-LOG.md` в папке таска. Имя файла индекса: `bullrun-launch-index.md`.
