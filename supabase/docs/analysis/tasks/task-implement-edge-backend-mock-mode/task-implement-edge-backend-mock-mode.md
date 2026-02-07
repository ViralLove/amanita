# Task: implement — режим мока Backend в Edge Function (переменная окружения)

**Контекст:** `supabase/functions/arweave-upload`. Edge вызывает Backend (PUT status, POST callback). Backend (bot) может быть ещё не задеплоен; нужна возможность тестировать Edge с замоканными вызовами и явно задавать контекст через переменную окружения.

**Связанные документы:** [arweave-upload-publish-api.md](../../../arweave-upload-publish-api.md) (разд. 4, 5), [arweave-upload-deploy-guide.md](../../../arweave-upload-deploy-guide.md), [task-implement-arweave-upload-edge-function](../task-implement-arweave-upload-edge-function/task-implement-arweave-upload-edge-function.md).

---

## Цель

Добавить в Edge Function `arweave-upload` **режим использования мока Backend**, управляемый переменной окружения. В этом режиме вызовы `putStatus` и `postCallback` не выполняют реальный HTTP-запрос к Backend, а лишь логируют параметры и возвращают успех, что позволяет тестировать Edge (в т.ч. задеплоенную в облако) без развёрнутого Backend.

## Почему это важно (риск)

Пока Backend в разработке и не задеплоен, проверка Edge (валидация JWT, Data Item, публикация в Arweave) возможна только при подмене вызовов к Backend. Сейчас при отсутствии `BACKEND_URL` или `EDGE_TO_BACKEND_SECRET` вызовы просто пропускаются с `console.warn` — поведение неочевидно и не документировано как «режим мока». Явная переменная даёт однозначный контекст («сейчас мы с моком») и упрощает настройку облачного деплоя для тестов.

## Границы (что НЕ входит)

- Реализация самого Backend (bot) — таск 3.2.
- Изменение контракта API Backend (PUT/POST) — без изменений.
- Локальный mock-сервер (отдельный процесс), отвечающий на PUT/POST — не в scope; достаточно «no-op» внутри Edge.

---

## Вариативность ответов Backend (из интеграционных тестов bot)

Источник: контракты и сценарии, покрытые интеграционными тестами Backend (`bot/tests/integration/test_upload_flow_integration.py`), задают полный набор ответов, которые Backend может отдать Edge.

### Матрица ответов по эндпоинтам

| Эндпоинт | Успех | Ошибки (код, когда) |
|----------|--------|----------------------|
| **PUT /v1/uploads/{id}/status** | 200, `{ "ok": true }` | 404 — неизвестный upload_id; 409 — недопустимый переход статуса |
| **POST /v1/uploads/callback** | 200, `{ "ok": true }` | 404 — неизвестный upload_id; 409 — некорректное состояние (например, запись не в queued_for_publish) |

Интеграционные тесты явно проверяют: 200 + body для успеха, 404 для неизвестного id, 409 для конфликта (callback из prepared). Для тестирования Edge без реального Backend мок должен уметь **симулировать эти же исходы**, чтобы проверять поведение Edge при 404/409 (логирование, повтор, метрики и т.д.).

### Требование: переключение варианта ответа в моке

- **Способ переключения:** переменные окружения, по одной на эндпоинт (чтобы независимо задавать ответ PUT и callback).
- **Предлагаемые имена и значения:**
  - `BACKEND_MOCK_PUT_STATUS` = `200` | `404` | `409` (по умолчанию `200`).
  - `BACKEND_MOCK_CALLBACK` = `200` | `404` | `409` (по умолчанию `200`).
- **Поведение в режиме мока:**
  - `200`: не вызывать fetch, логировать вызов и параметры, завершать без ошибки (симуляция успеха).
  - `404` / `409`: не вызывать fetch, логировать симулированный код (например, `[mock] putStatus simulated 404`); либо пробрасывать структурированную ошибку (например, `BackendMockError { status: 404 }`), чтобы код Edge или тесты могли на неё реагировать. Выбор: на первом шаге достаточно логирования + опциональный throw с типизированной ошибкой, чтобы тесты Edge могли ставить env и проверять поведение при «backend вернул 404/409».
- **Игнорирование:** если `BACKEND_USE_MOCK` не включён, переменные `BACKEND_MOCK_*` не используются.

### Переключение на лету из тестов (задеплоенная функция)

При вызове **уже задеплоенной** функции тесты не могут менять env (они заданы при деплое). Чтобы в разных сценариях проверять то «успех», то «putStatus 404», то «callback 409» без передеплоя, нужен **режим вызова с переопределением состояния мока на один запрос**.

**Идея: специальный режим вызова** — запрос к `/edge/v1/publish` может нести **тестовые заголовки**, которые задают симулированный ответ мока **только для этого запроса**. Функция учитывает их только при включённой «разрешённости переопределения» (отдельная переменная или секрет), чтобы в проде такие заголовки игнорировались.

**Предлагаемая схема:**

1. **Условие учёта переопределения:** переопределение по запросу учитывается только если выполнено одно из:
   - задана переменная окружения `BACKEND_MOCK_ALLOW_REQUEST_OVERRIDE=true` (или `1`), **или**
   - в запросе передан заголовок `X-Backend-Mock-Secret`, совпадающий со значением секрета из env/Secret `BACKEND_MOCK_TEST_SECRET` (для облака: только в тестовом проекте/стейдже).
2. **Заголовки переопределения (имеют смысл только при включённом моке и разрешённом override):**
   - `X-Backend-Mock-Put-Status`: `200` | `404` | `409` — симулированный код ответа для PUT status на этот запрос.
   - `X-Backend-Mock-Callback`: `200` | `404` | `409` — симулированный код ответа для POST callback на этот запрос.
3. **Поведение:** обработчик publish в `index.ts` перед вызовами `putStatus`/`postCallback` читает эти заголовки (только при `BACKEND_MOCK_ALLOW_REQUEST_OVERRIDE=true` или при валидном `X-Backend-Mock-Secret`), нормализует значения к 200|404|409 и передаёт их в `putStatus`/`postCallback` как **опциональный аргумент «override для этого запроса»**. В `backend-calls.ts` при наличии такого аргумента использовать его вместо env `BACKEND_MOCK_PUT_STATUS` / `BACKEND_MOCK_CALLBACK` для данного вызова.
4. **Итог для тестов:** тест против задеплоенной функции (staging/test project) задаёт в env проекта `BACKEND_USE_MOCK=true` и `BACKEND_MOCK_ALLOW_REQUEST_OVERRIDE=true` (или задаёт `BACKEND_MOCK_TEST_SECRET` и передаёт его в заголовке). В каждом сценарии тест шлёт один и тот же URL с разными заголовками, например:
   - сценарий «успех»: без заголовков или `X-Backend-Mock-Put-Status: 200`, `X-Backend-Mock-Callback: 200`;
   - сценарий «putStatus 404»: `X-Backend-Mock-Put-Status: 404`;
   - сценарий «callback 409»: `X-Backend-Mock-Callback: 409`.
   Передеплой не требуется, состояние мока переключается на лету через заголовки запроса.

---

## Факты из кода (Code Facts / SSOT)

### 1) Вызовы Backend в Edge

- `supabase/functions/arweave-upload/publish/backend-calls.ts`
  - `putStatus(uploadId, status, failureCode?)`: читает `BACKEND_URL` и `EDGE_TO_BACKEND_SECRET`; при отсутствии любого — `console.warn` и `return` (строки 12–16). Иначе — `fetch` PUT на `${baseUrl}/v1/uploads/${uploadId}/status`.
  - `postCallback(uploadId, itemId, bundleTxId, publishedAt)`: аналогично (строки 45–50); POST на `${baseUrl}/v1/uploads/callback`.

### 2) Использование в обработчике publish

- `supabase/functions/arweave-upload/index.ts`
  - Импорт: `import { putStatus, postCallback } from "./publish/backend-calls.ts"` (строка 7).
  - Вызовы: `putStatus(uploadId, "failed", "token_invalid")` (229), `putStatus(uploadId, "failed", "signature_invalid")` (239), `putStatus(uploadId, "queued_for_publish")` (246), `postCallback(...)` (258), `putStatus(uploadId, "failed", "publish_failed")` (262, 266).

### 3) Конфигурация в документации

- `supabase/docs/arweave-upload-publish-api.md` разд. 5: перечислены `BACKEND_URL`, `EDGE_TO_BACKEND_SECRET`; режим мока не описан.
- `supabase/docs/arweave-upload-deploy-guide.md`: переменные для локального и облачного запуска; упоминания «mock»/«skip backend» нет.

---

## Gap / Проблема

1. Нет явного переключателя «использовать мок Backend». Текущее поведение при отсутствии `BACKEND_URL`/`EDGE_TO_BACKEND_SECRET` — тихий skip с warn, что не эквивалентно задекларированному «режиму тестирования с моками».
2. В облаке при деплое Edge для тестов оператор вынужден либо не задавать Backend-переменные (неочевидное поведение), либо поднимать заглушку Backend. Желательно задать одну переменную (например, `BACKEND_USE_MOCK=true`) и не слать запросы вовсе.
3. В доке и в deploy-guide не описано, как включить контекст «Backend замокан» и какие переменные для этого задавать.
4. Мок не поддерживает вариативность ответов: интеграционные тесты Backend опираются на ответы 200 / 404 / 409 по PUT и POST; для тестов Edge и сценариев «backend вернул 404/409» нужна возможность переключать симулированный ответ мока (по эндпоинту) через env.
5. Нет способа переключать режим мока **на лету** при вызове задеплоенной функции: тесты извне не могут менять env между сценариями; нужен специальный режим вызова (например, заголовки запроса), задающий состояние мока на один запрос.

---

## AC/DoD (Acceptance Criteria / Definition of Done)

### Режим мока (P0)

- [ ] Введена переменная окружения, управляющая режимом вызовов Backend (например, `BACKEND_USE_MOCK`). Значение `true` (или `1`) означает «не выполнять реальный fetch к Backend».
- [ ] При включённом режиме мока: `putStatus` и `postCallback` не вызывают `fetch`; логируют факт вызова и параметры (без секретов). Поведение по умолчанию — симуляция успеха (return без ошибки).
- [ ] При выключенном режиме мока поведение без изменений: если заданы `BACKEND_URL` и `EDGE_TO_BACKEND_SECRET` — реальный HTTP; если не заданы — текущий warn + skip.

### Вариативность ответов мока (P0, из интеграционных тестов Backend)

- [ ] Введены переменные переключения симулированного ответа (действуют только при `BACKEND_USE_MOCK=true`):
  - `BACKEND_MOCK_PUT_STATUS` = `200` | `404` | `409` (по умолчанию `200`);
  - `BACKEND_MOCK_CALLBACK` = `200` | `404` | `409` (по умолчанию `200`).
- [ ] При значении `200`: лог + return без ошибки (как выше).
- [ ] При значении `404` или `409`: не вызывать fetch; логировать симулированный код (например, `[mock] putStatus simulated 404`); опционально — выбрасывать типизированную ошибку (например, объект с полем `status: number`), чтобы вызывающий код или тесты Edge могли проверять реакцию на «backend вернул 404/409».

### Переключение на лету из тестов (P0)

- [ ] Введена возможность **per-request override** состояния мока: при определённых условиях запрос к publish может передавать заголовки `X-Backend-Mock-Put-Status` и/или `X-Backend-Mock-Callback` со значениями `200` | `404` | `409`; они задают симулированный ответ мока только для этого запроса.
- [ ] Учёт заголовков переопределения только если включён мок и выполнено одно из: `BACKEND_MOCK_ALLOW_REQUEST_OVERRIDE=true` в env, или заголовок `X-Backend-Mock-Secret` совпадает с `BACKEND_MOCK_TEST_SECRET`. Иначе заголовки игнорируются (без ошибки).
- [ ] Обработчик publish в `index.ts` перед вызовами `putStatus`/`postCallback` читает эти заголовки (при разрешённом override), нормализует значения и передаёт их в `putStatus`/`postCallback`. В `backend-calls.ts` функции принимают опциональный аргумент «override для этого вызова»; при его наличии используется он вместо env.

### Конфигурация и доки (P0)

- [ ] В [arweave-upload-publish-api.md](../../../arweave-upload-publish-api.md) (разд. конфигурация) добавлены переменные: `BACKEND_USE_MOCK`, `BACKEND_MOCK_PUT_STATUS`, `BACKEND_MOCK_CALLBACK`, `BACKEND_MOCK_ALLOW_REQUEST_OVERRIDE`, `BACKEND_MOCK_TEST_SECRET` — имена, назначение, допустимые значения, примеры; описание заголовков `X-Backend-Mock-Put-Status`, `X-Backend-Mock-Callback`, `X-Backend-Mock-Secret` для переключения на лету.
- [ ] В [arweave-upload-deploy-guide.md](../../../arweave-upload-deploy-guide.md) добавлен подпункт «Режим мока Backend»: когда использовать, как задать переменные локально и в Secrets; как переключать симулированные ответы (200/404/409); как тестировать задеплоенную функцию с переключением на лету (заголовки запроса, примеры curl/тестов).

### Тесты (P1)

- [ ] Существующие тесты publish-flow (в т.ч. с моками `fetch`) продолжают проходить.
- [ ] При необходимости: отдельный сценарий или описание проверки, что при `BACKEND_USE_MOCK=true` вызовы `putStatus`/`postCallback` не приводят к реальному `fetch` (например, через мок `fetch` в тесте и проверку, что при мок-режиме fetch не вызывается).

---

## Где менять код (Code Changes Location)

| Роль | Файл | Действие |
|------|------|----------|
| Runtime | `supabase/functions/arweave-upload/publish/backend-calls.ts` | Чтение `BACKEND_USE_MOCK`; при включённом моке — источник симулированного кода: опциональный аргумент override (per-request), при отсутствии — env `BACKEND_MOCK_PUT_STATUS` / `BACKEND_MOCK_CALLBACK`. Нормализация 200/404/409, default 200. В `putStatus(..., mockOverride?: number)`: при моке и 200 — лог + return; при моке и 404/409 — лог + опционально throw. Аналогично `postCallback(..., mockOverride?)`. Иначе — текущая логика с fetch. |
| Runtime | `supabase/functions/arweave-upload/index.ts` | В обработчике POST /edge/v1/publish: при `BACKEND_USE_MOCK` и (`BACKEND_MOCK_ALLOW_REQUEST_OVERRIDE` или валидный `X-Backend-Mock-Secret`) читать заголовки `X-Backend-Mock-Put-Status`, `X-Backend-Mock-Callback`, нормализовать к 200|404|409; формировать объект override и передавать его в каждый вызов `putStatus`/`postCallback` (например, `putStatus(uploadId, status, failureCode, requestMockOverride?.putStatus)`). |
| Документация | `supabase/docs/arweave-upload-publish-api.md` | Разд. 5: переменные `BACKEND_USE_MOCK`, `BACKEND_MOCK_*`, `BACKEND_MOCK_ALLOW_REQUEST_OVERRIDE`, `BACKEND_MOCK_TEST_SECRET`; подраздел про заголовки переопределения (X-Backend-Mock-*). |
| Документация | `supabase/docs/arweave-upload-deploy-guide.md` | Подраздел «Режим мока Backend»: переменные, переключение по env; переключение на лету из тестов (заголовки, примеры вызова задеплоенной функции). |


## Команды проверки (Verification Commands)

```bash
# Из корня репозитория или из supabase/
cd supabase/functions/arweave-upload
deno test tests/ --allow-env
```

Локальная проверка с моком (после реализации):

```bash
# В .env задать BACKEND_USE_MOCK=true (и не задавать BACKEND_URL или оставить пустым)
supabase functions serve arweave-upload --env-file .env
# Вызвать POST /edge/v1/publish с валидным телом; в логах — вызов putStatus/postCallback без ошибок сети.
```

Проверка переключения симулированного ответа (env):

```bash
# Симуляция 404 на PUT status
BACKEND_USE_MOCK=true BACKEND_MOCK_PUT_STATUS=404 supabase functions serve arweave-upload --env-file .env
# После вызова publish в логах ожидается [mock] putStatus simulated 404 (и при реализации с throw — соответствующая ошибка).
```

Проверка переключения на лету (заголовки запроса, задеплоенная функция):

```bash
# В Secrets заданы: BACKEND_USE_MOCK=true, BACKEND_MOCK_ALLOW_REQUEST_OVERRIDE=true (или BACKEND_MOCK_TEST_SECRET)
EDGE_URL="https://YOUR_PROJECT_REF.supabase.co/functions/v1/arweave-upload"
ANON_KEY="..."

# Сценарий «успех» (без заголовков или 200)
curl -X POST "$EDGE_URL/edge/v1/publish" \
  -H "Authorization: Bearer $ANON_KEY" -H "apikey: $ANON_KEY" \
  -H "Content-Type: application/json" \
  -d '{"upload_token":"...","upload_id":"...","signed_data_item":"...","payload_size":0}'

# Сценарий «putStatus 404» — тот же URL, другой заголовок
curl -X POST "$EDGE_URL/edge/v1/publish" \
  -H "Authorization: Bearer $ANON_KEY" -H "apikey: $ANON_KEY" \
  -H "Content-Type: application/json" \
  -H "X-Backend-Mock-Put-Status: 404" \
  -d '{"upload_token":"...","upload_id":"...","signed_data_item":"...","payload_size":0}'
# В логах функции ожидается симуляция 404 для putStatus.
```

---

## Решение: способ переключения в моках

- **Включение мока:** одна переменная `BACKEND_USE_MOCK=true` (или `1`). Остальные переменные мока учитываются только при включённом моке.
- **Вариант ответа по эндпоинту (env):** переменные `BACKEND_MOCK_PUT_STATUS` и `BACKEND_MOCK_CALLBACK` (200|404|409, по умолчанию 200). Используются, если не задано переопределение на запрос.
- **Переключение на лету из тестов (задеплоенная функция):** специальный режим вызова — заголовки запроса `X-Backend-Mock-Put-Status`, `X-Backend-Mock-Callback` задают симулированный ответ только для этого запроса. Учитываются только при `BACKEND_MOCK_ALLOW_REQUEST_OVERRIDE=true` или при совпадении `X-Backend-Mock-Secret` с `BACKEND_MOCK_TEST_SECRET`. Обработчик publish читает заголовки и передаёт override в `putStatus`/`postCallback`; в backend-calls при наличии аргумента override использовать его вместо env. Статус мока переключается без передеплоя.
- **Реализация:** в `backend-calls.ts` — опциональный аргумент override в сигнатурах; при моке источник кода: override ?? env. В `index.ts` — чтение заголовков при разрешённом override, передача значений в вызовы.
- **Обратная совместимость:** без новых переменных и заголовков поведение как раньше; без override в вызове используется env.

---

## Метаданные

| Поле | Значение |
|------|----------|
| **Приоритет** | P1 |
| **Сложность** | M (режим мока + вариативность + переключение на лету) |
| **Оценка времени** | 1.5–2 часа |
| **Зависимости** | task-implement-arweave-upload-edge-function (реализован); контракт ответов Backend — bot интеграционные тесты (test_upload_flow_integration.py) |
| **Тэги** | edge-function, arweave-upload, backend-mock, config, integration-tests |
| **Статус** | draft |
