# Архитектура решения: Edge Function publish (user signs, operator pays)

**Таск:** [task-implement-arweave-upload-edge-function.md](../task-implement-arweave-upload-edge-function.md)  
**Дата:** 2026-01-29  
**Источники:** decision-points, sync-understanding, Arweave data upload.md.

**Постоянная версия (без привязки к таску):** [supabase/docs/arweave-upload-architecture.md](../../../arweave-upload-architecture.md).

---

## 1. Цель и границы

- **Цель:** в существующей Edge Function `arweave-upload` добавить поток POST /edge/v1/publish: приём signed Data Item + upload_token, валидация JWT RS256 и Data Item, два вызова Backend (status, callback), bundling и публикация в Arweave с оплатой оператором.
- **Границы:** только supabase/; Backend (endpoints, JWT выпуск) — таск 3.2 bot; Wallet (подпись Data Item) — отдельный таск.

---

## 2. Роли и потоки данных

```
Wallet (user)          Edge Function                    Backend (bot)              Arweave
     |                        |                                |                        |
     |  POST /edge/v1/publish |                                |                        |
     |  { upload_token,       |                                |                        |
     |    upload_id,          |                                |                        |
     |    signed_data_item,   |                                |                        |
     |    payload_size }      |                                |                        |
     |----------------------->|                                |                        |
     |                        | 1. validate JWT RS256         |                        |
     |                        | 2. validate Data Item          |                        |
     |                        | 3. PUT .../status              |------------------------>|
     |                        |    { status: queued_for_... } |                        |
     |                        | 4. bundle + sign bundle tx     |                        |
     |                        | 5. post to Arweave             |----------------------->|
     |                        | 6. POST .../callback           |                        |
     |                        |    { upload_id, bundle_tx_id } |----------------------->|
     |<-----------------------|                                |                        |
     | 200 { ack, status }    |                                |                        |
```

При любой ошибке (1, 2 или 5): ответ 4xx с `code`, вызов Backend PUT status с `status=failed`, `failure_code=token_invalid|signature_invalid|publish_failed`.

---

## 3. Модель данных (контракт)

### 3.1 Request POST /edge/v1/publish

| Поле | Тип | Обязательно | Описание |
|------|-----|-------------|----------|
| upload_token | string | да | JWT RS256 от Backend |
| upload_id | string (UUID) | да | Идентификатор upload |
| signed_data_item | string | да | Base64 бинарного Data Item (ANS-104) |
| item_id | string | нет | ID data item, если есть |
| payload_size | number | да | Размер payload в байтах |

### 3.2 Response 200 (успех)

```json
{ "ack": true, "status": "queued_for_publish" }
```

### 3.3 Response 4xx (ошибка)

```json
{ "code": "token_invalid" | "signature_invalid" | "publish_failed", "message": "..." }
```

### 3.4 Backend PUT /v1/uploads/{upload_id}/status

Тело: `{ "status": "queued_for_publish" }` или `{ "status": "failed", "failure_code": "token_invalid" | "signature_invalid" | "publish_failed" }`.  
Заголовок: `Authorization: Bearer ${EDGE_TO_BACKEND_SECRET}`.

### 3.5 Backend POST /v1/uploads/callback

Тело: `{ "upload_id", "item_id", "bundle_tx_id", "published_at" }`.  
Заголовок: тот же.

---

## 4. Модули и размещение кода

| Модуль | Файл | Назначение |
|--------|------|------------|
| Entry, роутинг | `index.ts` | Ветка path.endsWith('/edge/v1/publish'), оркестрация, ответы с code |
| Валидация JWT | `publish/validate-token.ts` | verifyJwtRs256(), проверка claims (exp, upload_id, payload_size <= max_bytes) |
| Валидация Data Item | `publish/validate-data-item.ts` | parseDataItem(base64), verifySignature(), getTagUploadId(), проверка Upload-Id === upload_id |
| Вызовы Backend | `publish/backend-calls.ts` | putStatus(upload_id, status, failure_code?), postCallback(upload_id, item_id, bundle_tx_id, published_at) |
| Bundle и публикация | `publish/bundle-publish.ts` (или в index + arweave/) | buildBundleFromDataItem(signedItemBytes), createAndSignBundleTx(), postToArweave(), возврат bundle_tx_id |
| Подпись Arweave tx | `crypto/arweave-rsa-pss.ts` | signArweaveTransaction(privateKey, signatureData) — Web Crypto RSASSA-PSS saltLength 32; разблокирует compatible.ts |
| Совместимость Arweave | `arweave/compatible.ts` | Без изменений импорта (arweave-rsa-pss); используется для подписи bundle tx |
| Тесты | `tests/publish-*.test.ts` | Моки Backend, сценарии token_invalid, signature_invalid, success, publish_failed |

Конфигурация: `UPLOAD_TOKEN_JWT_PUBLIC_KEY`, `BACKEND_URL`, `EDGE_TO_BACKEND_SECRET` из Deno.env (Secrets/env).

---

## 5. Фазы реализации (план по фазам)

### Phase 0: Инфраструктура подписи (разблокировать compatible.ts)

**Цель:** наличие `crypto/arweave-rsa-pss.ts`, чтобы импорт в compatible.ts работал и существующие upload-text/upload-file не падали.

| Шаг | Действие | Артефакт | Проверка |
|-----|----------|----------|----------|
| 0.1 | Реализовать `crypto/arweave-rsa-pss.ts`: signArweaveTransaction(privateKey, signatureData), Web Crypto RSASSA-PSS saltLength 32, вычисление transaction ID по Arweave | Файл arweave-rsa-pss.ts | deno check compatible.ts; при необходимости unit-тест подписи |
| 0.2 | Убедиться, что compatible.ts успешно импортирует и вызывается | — | Локально вызвать upload-text (если есть ключ) или deno check index.ts |

**Критерий завершения Phase 0:** `deno check index.ts` и импорт compatible.ts без ошибок.

---

### Phase 1: Контракт, маршрут, JWT RS256 и вызов Backend status

**Цель:** POST /edge/v1/publish принимает тело, проверяет JWT; при невалидном токене — 4xx + PUT status failed; при валидном — вызов PUT status queued_for_publish и ответ 200.

| Шаг | Действие | Артефакт | Проверка |
|-----|----------|----------|----------|
| 1.1 | В index.ts добавить ветку path.endsWith('/edge/v1/publish') && POST; парсинг body (upload_token, upload_id, signed_data_item, payload_size) | index.ts | Роут отвечает 400 при неверном body |
| 1.2 | Модуль publish/validate-token.ts: загрузка публичного ключа из env, verify JWT RS256, проверка exp, upload_id, payload_size <= max_bytes | validate-token.ts | Unit-тест: валидный/невалидный/истёкший токен |
| 1.3 | При token_invalid: ответ 401/400 с code: token_invalid, вызов backend-calls.putStatus(upload_id, 'failed', 'token_invalid') | index.ts, backend-calls.ts | Тест с моком Backend: при невалидном токене вызывается PUT status failed |
| 1.4 | Модуль publish/backend-calls.ts: putStatus(upload_id, status, failure_code?), fetch BACKEND_URL, Authorization: Bearer EDGE_TO_BACKEND_SECRET | backend-calls.ts | Мок Backend или интеграционный вызов |
| 1.5 | При валидном токене: вызов putStatus(upload_id, 'queued_for_publish'), ответ 200 { ack: true, status: 'queued_for_publish' } | index.ts | Тест: при валидном токене — 200 и вызов PUT status queued_for_publish |

**Критерий завершения Phase 1:** валидный JWT → 200 + Backend получает queued_for_publish; невалидный JWT → 4xx + Backend получает failed token_invalid.

---

### Phase 2: Data Item и signature_invalid

**Цель:** парсинг signed_data_item (base64 → Data Item), проверка подписи и тега Upload-Id; при ошибке — code: signature_invalid и PUT status failed.

| Шаг | Действие | Артефакт | Проверка |
|-----|----------|----------|----------|
| 2.1 | Модуль publish/validate-data-item.ts: decode base64, парсинг ANS-104 (или минимальный парсер: id, signature, tags, payload), извлечение owner (публичный ключ для проверки) | validate-data-item.ts | Unit-тест: валидный/невалидный base64, наличие тегов |
| 2.2 | Проверка подписи Data Item (RSA-PSS, saltLength 32) по owner из item; проверка тега Upload-Id === upload_id | validate-data-item.ts | Тест: подпись ок/не ок, тег Upload-Id совпадает/не совпадает |
| 2.3 | В оркестрации после JWT: вызов validateDataItem(); при signature_invalid — ответ 4xx, putStatus(upload_id, 'failed', 'signature_invalid') | index.ts | Тест: при невалидной подписи/теге — 4xx и PUT status failed |

**Критерий завершения Phase 2:** невалидная подпись или неверный Upload-Id → 4xx signature_invalid и Backend status failed.

---

### Phase 3: Bundling и публикация в Arweave, callback

**Цель:** собрать bundle из одного Data Item (ANS-104), создать bundle tx, подписать оператором (compatible.ts + arweave-rsa-pss), отправить в Arweave; при успехе — POST callback; при ошибке — putStatus failed publish_failed.

| Шаг | Действие | Артефакт | Проверка |
|-----|----------|----------|----------|
| 3.1 | Модуль publish/bundle-publish.ts (или аналог): buildBundleFromDataItem(signedItemBytes) — ANS-104 bundle из одного item; createBundleTx(bundleBytes); sign через compatible.signTransaction(arweave, tx, operatorKey); arweave.transactions.post(tx) | bundle-publish.ts, использование arweave, compatible | Проверить формат ANS-104 (документация/спека); при отсутствии bundle API в arweave SDK — минимальный builder |
| 3.2 | В оркестрации после валидации Data Item: вызов bundleAndPublish(); при успехе — postCallback(upload_id, item_id, bundle_tx_id, published_at); при ошибке — putStatus(upload_id, 'failed', 'publish_failed'), ответ 4xx publish_failed | index.ts, backend-calls.ts (postCallback) | Тест с моком Arweave: успех → callback вызван; ошибка → status failed, 4xx |
| 3.3 | backend-calls.postCallback(upload_id, item_id, bundle_tx_id, published_at) | backend-calls.ts | Мок Backend принимает callback |

**Критерий завершения Phase 3:** успешная публикация → Backend получает callback с bundle_tx_id; ошибка публикации → Backend получает status failed publish_failed, клиент — 4xx publish_failed.

---

### Phase 4: Тесты и безопасность

**Цель:** полное покрытие сценариев; логирование без payload/секретов; конфигурация из env.

| Шаг | Действие | Артефакт | Проверка |
|-----|----------|----------|----------|
| 4.1 | Сводные тесты: (1) token_invalid → 4xx + PUT failed; (2) signature_invalid → 4xx + PUT failed; (3) успешный путь → 200 + PUT queued + callback; (4) publish_failed → 4xx + PUT failed | tests/publish-flow.test.ts (или разбить по сценариям) | deno test tests/ |
| 4.2 | Логирование: принят запрос, токен ок/не ок, Data Item ок/не ок, вызов status, публикация ок/не ок, callback; не логировать body.signed_data_item, токены, секреты | index.ts, модули publish/ | Ручная проверка логов |
| 4.3 | README или комментарии: перечень env/Secrets (UPLOAD_TOKEN_JWT_PUBLIC_KEY, BACKEND_URL, EDGE_TO_BACKEND_SECRET, ARWEAVE_PRIVATE_KEY_FILE) | README в arweave-upload или в папке таска | — |

**Критерий завершения Phase 4:** все тесты зелёные; конфигурация и логирование соответствуют P1.

---

## 6. Порядок выполнения и зависимости

```
Phase 0 (arweave-rsa-pss) → Phase 1 (маршрут, JWT, Backend status) → Phase 2 (Data Item) → Phase 3 (bundle, publish, callback) → Phase 4 (тесты, безопасность)
```

Phase 1 можно частично тестировать с моком signed_data_item (например, пустая строка или заглушка), если проверка Data Item выполняется после JWT. Phase 2 добавляет реальную проверку item; Phase 3 замыкает цикл с Arweave и callback.

---

## 7. Риски и митигации

| Риск | Митигация |
|------|-----------|
| Arweave SDK не содержит готовый bundle API | Минимальная сборка bundle bytes по спецификации ANS-104; либо поиск отдельной библиотеки arweave/bundle. |
| Формат Data Item (ANS-104) сложный для парсинга | Начать с минимального парсера (достаточно для извлечения owner, signature, тегов); при необходимости привлечь спеку ANS-104. |
| Backend (таск 3.2) ещё не готов | Моки Backend в тестах; для E2E дождаться реализации 3.2. |

---

**Итог этапа 3:** архитектура решения зафиксирована; фазы 0–4 с шагами и артефактами заданы. Следующий шаг: Этап 4 — план реализации (implementation-plan) по файлам и конкретным действиям.
