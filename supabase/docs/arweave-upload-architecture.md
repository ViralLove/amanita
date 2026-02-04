# Архитектура Edge Function arweave-upload (publish: user signs, operator pays)

**Назначение:** постоянный документ с описанием цели, границ, ролей, потока данных, контрактов и модулей Edge Function `arweave-upload` для потока POST /edge/v1/publish.

**Связанные документы:** [arweave-upload-publish-api.md](./arweave-upload-publish-api.md), [arweave-upload-security.md](./arweave-upload-security.md), [arweave-upload-deploy-guide.md](./arweave-upload-deploy-guide.md).

---

## 1. Цель и границы

- **Цель:** в Edge Function `arweave-upload` реализован поток POST /edge/v1/publish: приём signed Data Item и upload_token, валидация JWT RS256 и Data Item, два вызова Backend (status, callback), bundling и публикация в Arweave с оплатой оператором.
- **Границы:** реализация в рамках `supabase/`; Backend (endpoints, выпуск JWT) и Wallet (подпись Data Item) — отдельные системы, контракт с ними описан в [arweave-upload-publish-api.md](./arweave-upload-publish-api.md) и [arweave-upload-security.md](./arweave-upload-security.md).

---

## 2. Роли и поток данных

```
Wallet (user)          Edge Function                    Backend (bot)              Arweave
     |                        |                                |                        |
     |  POST /edge/v1/publish |                                |                        |
     |  { upload_token,       |                                |                        |
     |    upload_id,           |                                |                        |
     |    signed_data_item,    |                                |                        |
     |    payload_size }       |                                |                        |
     |------------------------>|                                |                        |
     |                         | 1. validate JWT RS256          |                        |
     |                         | 2. validate Data Item          |                        |
     |                         | 3. PUT .../status              |------------------------>|
     |                         |    { status: queued_for_... } |                        |
     |                         | 4. bundle + sign bundle tx     |                        |
     |                         | 5. post to Arweave             |----------------------->|
     |                         | 6. POST .../callback           |                        |
     |                         |    { upload_id, bundle_tx_id } |------------------------>|
     |<------------------------|                                |                        |
     | 200 { ack, status }     |                                |                        |
```

При любой ошибке на шагах 1, 2 или 5: ответ 4xx с полем `code`, вызов Backend PUT status с `status=failed` и `failure_code=token_invalid | signature_invalid | publish_failed`.

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

Тело: `{ "upload_id", "item_id", "bundle_tx_id", "published_at" }` (ISO 8601).  
Заголовок: тот же.

---

## 4. Модули и размещение кода

| Модуль | Файл | Назначение |
|--------|------|------------|
| Entry, роутинг | `index.ts` | Ветка path.endsWith('/edge/v1/publish'), оркестрация, ответы с code |
| Валидация JWT | `publish/validate-token.ts` | verifyJwtRs256(), проверка claims (exp, upload_id, payload_size ≤ max_bytes) |
| Валидация Data Item | `publish/validate-data-item.ts` | parseDataItem(base64), verifySignature(), getTagUploadId(), проверка Upload-Id === upload_id |
| Вызовы Backend | `publish/backend-calls.ts` | putStatus(upload_id, status, failure_code?), postCallback(upload_id, item_id, bundle_tx_id, published_at) |
| Bundle и публикация | `publish/bundle-publish.ts` | buildBundleFromDataItem(signedItemBytes), ANS-104 bundle из одного item, подпись bundle tx, postToArweave(), возврат bundle_tx_id |
| Подпись Arweave tx | `crypto/arweave-rsa-pss.ts` | signArweaveTransaction(privateKey, signatureData) — Web Crypto RSASSA-PSS saltLength 32 |
| Совместимость Arweave | `arweave/compatible.ts` | Использует arweave-rsa-pss для подписи bundle tx |

Конфигурация: `UPLOAD_TOKEN_JWT_PUBLIC_KEY`, `BACKEND_URL`, `EDGE_TO_BACKEND_SECRET`, `ARWEAVE_PRIVATE_KEY_FILE` (или `ARWEAVE_PRIVATE_KEY`) из Deno.env / Supabase Secrets.

---

## 5. Порядок обработки

1. Парсинг тела, проверка обязательных полей → при ошибке 400.
2. Верификация JWT RS256 (подпись, exp, upload_id, payload_size ≤ max_bytes) → при ошибке 401, putStatus failed token_invalid.
3. Парсинг и проверка Data Item (подпись RSA-PSS, тег Upload-Id = upload_id) → при ошибке 400, putStatus failed signature_invalid.
4. putStatus queued_for_publish, ответ 200 { ack, status }.
5. Асинхронно: bundle из одного Data Item, подпись bundle tx оператором, отправка в Arweave; при успехе — postCallback; при ошибке — putStatus failed publish_failed.

---

## 6. Риски и митигации

| Риск | Митигация |
|------|-----------|
| Arweave SDK не содержит готовый bundle API | Минимальная сборка bundle bytes по спецификации ANS-104; при необходимости отдельная библиотека arweave/bundle. |
| Сложный формат Data Item (ANS-104) | Минимальный парсер (достаточно owner, signature, теги); при необходимости — спецификация ANS-104. |
| Backend не готов | Моки Backend в тестах; для E2E — согласование контракта и реализации Backend. |

---

**Версия:** 1.0  
**Дата:** 2026-01-29
