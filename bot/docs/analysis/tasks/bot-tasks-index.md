# Bot — Tasks Index

Индекс задач для `bot`-подсистемы (API, upload flow, signing flow, auth, e2e).  
Цель: единая точка входа по всем task-докам в `bot/docs/analysis/tasks/`, включая активные и исторические (закрытые/архивные).

Смежные документы:
- `docs/methodology/task-standard.md`
- `docs/methodology/index-standard-bullrun-fullpower.md`
- `bot/docs/tests/e2e-floou-manual.md`
- `bot/docs/tests/e2e-floou-orchestration-overview.md`

---

**Коды статусов:** ⚪ = 0 — Todo, 🟡 = 1 — In Progress, 🔵 = 2 — Implemented (Waiting Acceptance), 🟢 = 3 — Done/Closed.

### Cluster A — Activity Platform Phases (P2-P8)

| S | Key | Task | Type | Status | Scope / Notes |
|---|-----|------|------|--------|---------------|
| 🟢 | ACT-P2 | [task-implement-activity-data-models-phase2](./task-implement-activity-data-models-phase2/task-implement-activity-data-models-phase2.md) | implement | Done (historical) | Фаза 2 модели данных; по истории ранее закрывалась отдельным циклом. |
| ⚪ | ACT-P3-STORAGE | [task-implement-activity-storage-service-phase3](./task-implement-activity-storage-service-phase3/task-implement-activity-storage-service-phase3.md) | implement | Todo | Фаза 3.3: prepare/resolve CID, metadata download/validate. |
| ⚪ | ACT-P3-VALIDATION | [task-implement-activity-validation-metadata-services-phase3](./task-implement-activity-validation-metadata-services-phase3/task-implement-activity-validation-metadata-services-phase3.md) | implement | Todo | Фаза 3.4: validation + metadata services. |
| ⚪ | ACT-P4 | [task-implement-activity-assembler-phase4](./task-implement-activity-assembler-phase4/task-implement-activity-assembler-phase4.md) | implement | Todo | Фаза 4: assembler блокчейн + Arweave. |
| ⚪ | ACT-P5 | [task-implement-activity-search-infrastructure-phase5](./task-implement-activity-search-infrastructure-phase5/task-implement-activity-search-infrastructure-phase5.md) | implement | Todo | Фаза 5: search infra (fragments/embeddings/Supabase). |
| ⚪ | ACT-P6 | [task-implement-activity-registry-service-phase6](./task-implement-activity-registry-service-phase6/task-implement-activity-registry-service-phase6.md) | implement | Todo | Фаза 6: registry/cache lifecycle orchestration. |
| ⚪ | ACT-P7 | [task-implement-activity-api-layer-phase7](./task-implement-activity-api-layer-phase7/task-implement-activity-api-layer-phase7.md) | implement | Todo | Фаза 7: API layer integration. |
| ⚪ | ACT-P8 | [task-implement-activity-service-factory-e2e-finalization-phase8](./task-implement-activity-service-factory-e2e-finalization-phase8/task-implement-activity-service-factory-e2e-finalization-phase8.md) | implement | Todo | Фаза 8: service factory, e2e, finalization. |
| ⚪ | ACT-SUBMIT | [task-implement-activity-registry-create-activity-submit](./task-implement-activity-registry-create-activity-submit/task-implement-activity-registry-create-activity-submit.md) | implement | Todo | Submit-flow: createActivity(cid) в контракте. |

### Cluster B — Upload & Arweave Integration Core

| S | Key | Task | Type | Status | Scope / Notes |
|---|-----|------|------|--------|---------------|
| 🟢 | UPLOAD-CORE | [task-implement-upload-flow-core-phase3](./task-implement-upload-flow-core-phase3/task-implement-upload-flow-core-phase3.md) | implement | Done (historical) | Upload ядро (исторически закрывалось отдельным run-task циклом). |
| 🟢 | UPLOAD-MOCK | [task-implement-uploads-api-mock-endpoints](./task-implement-uploads-api-mock-endpoints/task-implement-uploads-api-mock-endpoints.md) | implement | Done (historical) | Mock endpoints для проверки upload callback контракта. |
| ⚪ | UPLOAD-DRAFT | [task-implement-draft-prepare-payload-cache-push](./task-implement-draft-prepare-payload-cache-push/task-implement-draft-prepare-payload-cache-push.md) | implement | Todo | Draft→prepare/payload cache/push sign_arweave. |
| ⚪ | UPLOAD-SIGN-PAYLOAD | [task-implement-get-uploads-sign-payload](./task-implement-get-uploads-sign-payload/task-implement-get-uploads-sign-payload.md) | implement | Todo | GET `/v1/uploads/{upload_id}/sign-payload`. |
| ⚪ | UPLOAD-CALLBACK | [task-implement-callback-sign-request-push](./task-implement-callback-sign-request-push/task-implement-callback-sign-request-push.md) | implement | Todo | Callback -> sign_request + push sign_contract. |
| ⚪ | UPLOAD-REALTIME | [task-implement-upload-flow-realtime-on-finalized](./task-implement-upload-flow-realtime-on-finalized/task-implement-upload-flow-realtime-on-finalized.md) | implement | Todo | Realtime на `finalized`. |
| ⚪ | UPLOAD-REAL-CYCLE | [task-tests-phase3-full-cycle-real-db-real-arweave-uploader](./task-tests-phase3-full-cycle-real-db-real-arweave-uploader/task-tests-phase3-full-cycle-real-db-real-arweave-uploader.md) | tests | Todo | Полный реальный цикл uploader+db; см. acceptance-файл в той же папке. |
| ⚪ | UPLOAD-JWT-TEMP | [task-temp-test-jwt-key-pair-alignment](./task-tests-phase3-full-cycle-real-db-real-arweave-uploader/task-temp-test-jwt-key-pair-alignment.md) | tests | Todo | Временный вспомогательный task внутри Phase3 full-cycle. |
| ⚪ | ACT-RESOLVE | [task-implement-activity-resolve-by-upload-id](./task-implement-activity-resolve-by-upload-id/task-implement-activity-resolve-by-upload-id.md) | implement | Todo | Umbrella: resolve полной Activity по `upload_id` (кэш → Arweave → опционально on-chain); SSOT и оценка сложности в файле. |
| ⚪ | ACT-RESOLVE-A | [task-analyze-activity-resolve-by-upload-id-decision-contract](./task-implement-activity-resolve-by-upload-id/subtask-a-decision-contract/task-analyze-activity-resolve-by-upload-id-decision-contract.md) | analyze | Todo | Subtask: decision record path/query/ответ/ошибки → `decision-points-activity-resolve-by-upload-id.md`. |
| ⚪ | ACT-RESOLVE-B | [task-implement-activity-resolve-by-upload-id-service-and-route](./task-implement-activity-resolve-by-upload-id/subtask-b-service-http-di/task-implement-activity-resolve-by-upload-id-service-and-route.md) | implement | Todo | Subtask: сервис + HTTP + DI, кэш→Arweave, без on-chain. |
| ⚪ | ACT-RESOLVE-C | [task-tests-activity-resolve-by-upload-id](./task-implement-activity-resolve-by-upload-id/subtask-c-tests/task-tests-activity-resolve-by-upload-id.md) | tests | Todo | Subtask: unit/integration, мок gateway, auth/not found. |
| ⚪ | ACT-RESOLVE-D | [task-implement-activity-resolve-by-upload-id-docs-sync](./task-implement-activity-resolve-by-upload-id/subtask-d-docs-e2e-gpt/task-implement-activity-resolve-by-upload-id-docs-sync.md) | implement | Todo | Subtask: e2e-доки + P2 GPT `api-methods-reference`. |
| ⚪ | ACT-RESOLVE-E | [task-implement-activity-resolve-by-upload-id-onchain-enrichment](./task-implement-activity-resolve-by-upload-id/subtask-e-onchain-optional/task-implement-activity-resolve-by-upload-id-onchain-enrichment.md) | implement | Todo | Subtask (опционально): on-chain после ACT-SUBMIT / registry-read. |

### Cluster C — Signing Flow & E2E Orchestration

| S | Key | Task | Type | Status | Scope / Notes |
|---|-----|------|------|--------|---------------|
| 🔵 | FLOOU-1 | [task-tests-full-flow-signing-mock-wallet-localhost](./task-tests-full-flow-signing-mock-wallet-localhost/task-tests-full-flow-signing-mock-wallet-localhost.md) | tests | Implemented (Waiting Acceptance) | Сквозной цикл подписаний `draft -> sign_arweave -> callback -> sign_contract -> submit` с mock wallet на localhost; в коде путь реализован, task-док ещё формально `draft`. |
| ⚪ | FLOOU-SIGN-STORE | [task-implement-sign-requests-get-submit](./task-implement-sign-requests-get-submit/task-implement-sign-requests-get-submit.md) | implement | Todo | Sign requests store + GET/SUBMIT endpoints. |
| ⚪ | FLOOU-PUSH-STUB | [task-implement-push-sender-interface-stub](./task-implement-push-sender-interface-stub/task-implement-push-sender-interface-stub.md) | implement | Todo | PushSender interface + StubPushSender. |

### Cluster D — Wallet-Bot Security

| S | Key | Task | Type | Status | Scope / Notes |
|---|-----|------|------|--------|---------------|
| 🟡 | AUTH-WALLET | [task-implement-wallet-bot-auth-server-shared](./task-implement-wallet-bot-auth-server-shared/task-implement-wallet-bot-auth-server-shared.md) | implement | In Progress | Wallet->bot auth для pending/sign-payload/sign-request/submit; A/B/C выполнены, финальный e2e AC заблокирован runtime startup контрактов. |
| 🔵 | AUTH-WALLET-A | [task-implement-wallet-auth-challenge-signature-contract](./task-implement-wallet-bot-auth-server-shared/subtask-a-auth-protocol-contract/task-implement-wallet-auth-challenge-signature-contract.md) | implement | Implemented (Waiting Acceptance) | Subtask A: protocol contract challenge + EVM signature, TTL/replay/error contract. |
| 🔵 | AUTH-WALLET-B | [task-implement-wallet-auth-server-enforcement-signing-endpoints](./task-implement-wallet-bot-auth-server-shared/subtask-b-bot-server-enforcement/task-implement-wallet-auth-server-enforcement-signing-endpoints.md) | implement | Implemented (Waiting Acceptance) | Subtask B: server enforcement на signing endpoints + auth tests. |
| 🔵 | AUTH-WALLET-C | [task-implement-wallet-auth-local-compat-and-mock-runner](./task-implement-wallet-bot-auth-server-shared/subtask-c-local-compat-wallet-mock/task-implement-wallet-auth-local-compat-and-mock-runner.md) | implement | Implemented (Waiting Acceptance) | Subtask C: localhost compatibility + wallet-mock integration/runbook sync. |
| ⚪ | AUTH-JWT-ACT | [task-refactor-jwt-bearer-authentication-activities-api](./task-refactor-jwt-bearer-authentication-activities-api/task-refactor-jwt-bearer-authentication-activities-api.md) | refactor | Todo | JWT/Bearer auth для Activities API. |
| 🟢 | GPT-ACTIONS-KEY | [task-implement-gpt-actions-api-key-bearer-activities](./task-implement-gpt-actions-api-key-bearer-activities/task-implement-gpt-actions-api-key-bearer-activities.md) | implement | Done | `GPT_ACTIONS_BEARER_SECRET`, middleware `gpt_actions_bearer`; доки `api.md`, `api-methods-reference.md`; bullrun **GIM-BCK-0**. Оператор: секрет в `.env` + Custom GPT. |

### Cluster E — WooCommerce Export & Mapping

| S | Key | Task | Type | Status | Scope / Notes |
|---|-----|------|------|--------|---------------|
| ⚪ | WOO-MAP-VAR | [task-adapt-woo-id-mapping-for-variations](./task-adapt-woo-id-mapping-for-variations/task-adapt-woo-id-mapping-for-variations.md) | implement | Todo | Вариации + merge для Woo mapping. |
| ⚪ | WOO-SHORT-FIELD | [task-add-product-short-description-simple-field](./task-add-product-short-description-simple-field/task-add-product-short-description-simple-field.md) | implement | Todo | Product short description как simple-field контракт. |
| ⚪ | WOO-SHORT-EXPORT | [task-implement-woocommerce-short-description-export](./task-implement-woocommerce-short-description-export/task-implement-woocommerce-short-description-export.md) | implement | Todo | Генерация `Short description` в CSV. |
| ⚪ | WOO-CMO | [task-cmo-short-description-content](./task-cmo-short-description-content/task-cmo-short-description-content.md) | content | Todo | Контент-стратегия short description. |

### Cluster F — Telegram Catalog & Localization Quality

| S | Key | Task | Type | Status | Scope / Notes |
|---|-----|------|------|--------|---------------|
| ⚪ | TG-COVERAGE | [task-bot-telegram-catalog-test-coverage-gaps](./task-bot-telegram-catalog-test-coverage-gaps/task-bot-telegram-catalog-test-coverage-gaps.md) | analysis | Todo | Анализ test coverage gaps Telegram catalog flow. |
| ⚪ | TG-CART-GAP | [task-tests-telegram-cart-callback-gap](./task-tests-telegram-cart-callback-gap/task-tests-telegram-cart-callback-gap.md) | tests | Todo | Кнопка `product:cart:*` без handler. |
| ⚪ | TG-REGISTRY-WIRING | [task-tests-telegram-registry-singleton-wiring](./task-tests-telegram-registry-singleton-wiring/task-tests-telegram-registry-singleton-wiring.md) | tests | Todo | Проверка wiring CatalogService <-> registry_singleton. |
| ⚪ | LOC-ASSEMBLY-GAP | [task-tests-localization-product-assembly-gap](./task-tests-localization-product-assembly-gap/task-tests-localization-product-assembly-gap.md) | tests | Todo | Gap локализации vs ProductAssembler. |
| ⚪ | REF-TERM-PAYLOAD | [task-refactor-terminology-componentdescription-payload](./task-refactor-terminology-componentdescription-payload/task-refactor-terminology-componentdescription-payload.md) | refactor | Todo | Унификация терминологии payload/localization contracts. |
| ⚪ | DOCS-CODE-MISMATCH | [task-bot-docs-vs-code-mismatches](./task-bot-docs-vs-code-mismatches/task-bot-docs-vs-code-mismatches.md) | analysis | Todo | Системные рассинхроны docs vs code/deploy в bot. |

### Cluster G — Legacy/Archived (Closed, file removed)

| S | Key | Task | Type | Status | Scope / Notes |
|---|-----|------|------|--------|---------------|
| 🟢 | ARCH-1 | `task-tests-telegram-catalogservice-send-catalog` | tests | Done/Closed | Исторически выполнено и удалено из каталога задач. |
| 🟢 | ARCH-2 | `task-tests-telegram-product-details-flow` | tests | Done/Closed | Исторически выполнено и удалено из каталога задач. |
| 🟢 | ARCH-3 | `task-tests-telegram-component-desc-handlers` | tests | Done/Closed | Исторически выполнено и удалено из каталога задач. |
| 🟢 | ARCH-4 | `task-refactor-multilingual-ipfs-use-productstorageservice` | refactor | Done/Closed | Исторически выполнено и удалено из каталога задач. |
| 🟢 | ARCH-5 | `task-refactor-multilingual-ipfs-remove-ipfs-factory-param` | refactor | Done/Closed | Исторически выполнено и удалено из каталога задач. |
| 🟢 | ARCH-6 | `task-fix-sku-priority-from-mapping` | fix | Done/Closed | Исторически выполнено и удалено из каталога задач. |
| 🟢 | ARCH-7 | `task-refactor-woocommerce-columns-constants` | refactor | Done/Closed | Исторически выполнено и удалено из каталога задач. |

### Cluster H — Deploy/Secrets Configuration

| S | Key | Task | Type | Status | Scope / Notes |
|---|-----|------|------|--------|---------------|
| 🔵 | SECRETS-PROVIDER | [task-refactor-optional-vault-secrets-loading-for-polygon](./task-refactor-optional-vault-secrets-loading-for-polygon/task-refactor-optional-vault-secrets-loading-for-polygon.md) | refactor | Implemented (Waiting Acceptance) | `SECRETS_PROVIDER=vault|env`; default если не задан: polygon→vault, иначе→env. Доки и `.env.example` синхронизированы. Приёмка: оператор + при необходимости `acceptance-verification-*.md`. |

---

## Как пользоваться этим индексом

- **Todo (0 / ⚪)** — постановка есть, реализация не начата.
- **In Progress (1 / 🟡)** — идёт выполнение фаз run-task.
- **Implemented (2 / 🔵)** — реализация готова, ждёт формальной приёмки.
- **Done (3 / 🟢)** — предметно завершено/закрыто, включая архивные задачи.

Правила:
- одна строка = один task-файл;
- индекс включает активные и закрытые задачи `bot`;
- для закрытых удалённых задач храним минимум: key, имя, тип, статус, примечание.

