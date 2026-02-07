# План реализации: режим мока Backend (Edge Function)

**Таск:** task-implement-edge-backend-mock-mode  
**Источники:** task-implement-edge-backend-mock-mode.md, solution-architecture.md

---

## Phase 0: backend-calls.ts — режим мока и override

| Шаг | Файл | Действие | Критерий приёмки |
|-----|------|----------|------------------|
| 0.1 | `supabase/functions/arweave-upload/publish/backend-calls.ts` | В начале файла: хелпер `isBackendMockEnabled()` (читать BACKEND_USE_MOCK, true при "true"/"1" без учёта регистра). Хелпер `normalizeMockStatus(v): 200\|404\|409` (пусто/невалидно → 200). | Функции экспортировать не обязательно; используются внутри модуля. |
| 0.2 | Там же | В начале `putStatus`: опциональный 4-й аргумент `requestMockPutStatus?: number`. Если мок включён — не вызывать fetch; вычислить код = requestMockPutStatus ?? normalizeMockStatus(Deno.env.get("BACKEND_MOCK_PUT_STATUS")); при 200 — console.log параметров, return; при 404/409 — console.log "[mock] putStatus simulated N", return. Иначе (мок выключен) — текущая логика (baseUrl/secret, fetch). | putStatus при BACKEND_USE_MOCK=true не дергает fetch; при 404/409 в логах симуляция. |
| 0.3 | Там же | В `postCallback`: опциональный 5-й аргумент `requestMockCallback?: number`. Аналогично: при моке код = override ?? env BACKEND_MOCK_CALLBACK; лог и return. | postCallback при моке не дергает fetch. |

---

## Phase 1: index.ts — чтение заголовков и передача override

| Шаг | Файл | Действие | Критерий приёмки |
|-----|------|----------|------------------|
| 1.1 | `supabase/functions/arweave-upload/index.ts` | В обработчике POST /edge/v1/publish, до первого вызова putStatus: вычислить, разрешён ли request override (BACKEND_USE_MOCK и (BACKEND_MOCK_ALLOW_REQUEST_OVERRIDE=true или req.header X-Backend-Mock-Secret === BACKEND_MOCK_TEST_SECRET)). Если да — прочитать заголовки X-Backend-Mock-Put-Status, X-Backend-Mock-Callback и нормализовать к 200|404|409 (хелпер можно дублировать в index или импортировать из backend-calls). Сформировать объект { putStatus?: number, callback?: number }. | При наличии заголовков и разрешении — override передаётся в вызовы. |
| 1.2 | Там же | Во всех вызовах putStatus добавить 4-й аргумент: requestMockOverride?.putStatus. Во всех вызовах postCallback добавить 5-й аргумент: requestMockOverride?.callback. | Все вызовы putStatus/postCallback в publish получают override. |

---

## Phase 2: Документация

| Шаг | Файл | Действие | Критерий приёмки |
|-----|------|----------|------------------|
| 2.1 | `supabase/docs/arweave-upload-publish-api.md` | В разд. 5 (Конфигурация) добавить в таблицу переменных: BACKEND_USE_MOCK, BACKEND_MOCK_PUT_STATUS, BACKEND_MOCK_CALLBACK, BACKEND_MOCK_ALLOW_REQUEST_OVERRIDE, BACKEND_MOCK_TEST_SECRET. Добавить подраздел про заголовки переопределения: X-Backend-Mock-Put-Status, X-Backend-Mock-Callback, X-Backend-Mock-Secret (когда учитываются, примеры). | Доки содержат все переменные и заголовки. |
| 2.2 | `supabase/docs/arweave-upload-deploy-guide.md` | Добавить подпункт «Режим мока Backend»: когда использовать, переменные, переключение по env; переключение на лету (заголовки, пример curl к задеплоенной функции). | Deploy-guide описывает мок и тесты против деплоя. |

---

## Phase 3: Верификация

| Шаг | Действие | Критерий приёмки |
|-----|----------|------------------|
| 3.1 | Запуск тестов: `cd supabase/functions/arweave-upload && deno test tests/ --allow-env` | Все существующие тесты проходят. |
| 3.2 | Сверка кода и тестов с AC таска; заполнить acceptance-verification.md в папке таска. | Все пункты AC отмечены выполненными или N/A с обоснованием. |
