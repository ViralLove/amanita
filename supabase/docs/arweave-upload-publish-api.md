# Edge Function arweave-upload: API Publish (user signs, operator pays)

**Контекст:** Supabase Edge Function `arweave-upload`. Поток «user signs, operator pays»: приём signed Data Item и upload_token от Wallet; валидация JWT RS256 и Data Item; вызовы Backend (status, callback); bundling и публикация в Arweave с оплатой оператором.

**Связанные документы:** Epic Activities Phase 3 — [Arweave data upload](../../docs/analysis/epics/activities%20crud%20and%20search/Arweave%20data%20upload.md); таск 3.1 — [task-implement-arweave-upload-edge-function](analysis/tasks/task-implement-arweave-upload-edge-function/task-implement-arweave-upload-edge-function.md).

---

## 1. Endpoint

**POST** `/edge/v1/publish` (маршрут в Edge Function `arweave-upload`).

Клиент: Wallet или Backend-прокси. Тело запроса — JSON.

---

## 2. Request

| Поле | Тип | Обязательно | Описание |
|------|-----|-------------|----------|
| upload_token | string | да | JWT RS256, выпущенный Backend (claims: upload_id, max_bytes, exp) |
| upload_id | string (UUID) | да | Идентификатор upload |
| signed_data_item | string | да | Base64 бинарного Data Item (ANS-104), подписанный владельцем |
| payload_size | number | да | Размер payload в байтах (должен быть ≤ max_bytes из JWT) |
| item_id | string | нет | ID data item, если известен (опционально) |

---

## 3. Response

### 3.1 Успех (200)

Ответ отдаётся сразу после приёма и постановки в очередь; публикация в Arweave и callback в Backend выполняются асинхронно.

```json
{ "ack": true, "status": "queued_for_publish" }
```

### 3.2 Ошибка валидации (4xx)

| HTTP | code | Когда |
|------|------|--------|
| 400 | bad_request | Неверное тело (отсутствуют обязательные поля, невалидный JSON) |
| 401 | token_invalid | JWT невалиден, истёк или не совпадает upload_id / payload_size > max_bytes |
| 400 | signature_invalid | Data Item: невалидная подпись или тег Upload-Id ≠ upload_id |

Тело ошибки: `{ "code": "token_invalid" | "signature_invalid" | "publish_failed", "message": "..." }`.

**Примечание:** При ошибке публикации (после отдачи 200) клиент не получает ответ с `code: publish_failed` — Backend уведомляется через PUT status failed.

---

## 4. Вызовы Edge → Backend

Edge вызывает Backend с заголовком `Authorization: Bearer ${EDGE_TO_BACKEND_SECRET}`.

### 4.1 PUT /v1/uploads/{upload_id}/status

- После успешной валидации: `{ "status": "queued_for_publish" }`.
- При ошибке (token_invalid, signature_invalid, publish_failed): `{ "status": "failed", "failure_code": "token_invalid" | "signature_invalid" | "publish_failed" }`.

### 4.2 POST /v1/uploads/callback

После успешной публикации в Arweave: тело `{ "upload_id", "item_id", "bundle_tx_id", "published_at" }` (ISO 8601).

---

## 5. Конфигурация (Secrets / env)

| Переменная | Описание |
|------------|----------|
| UPLOAD_TOKEN_JWT_PUBLIC_KEY | Публичный ключ Backend (PEM или JWK JSON) для верификации JWT RS256 |
| BACKEND_URL | URL Backend API (без завершающего слеша) |
| EDGE_TO_BACKEND_SECRET | Секрет для заголовка Authorization при вызовах Backend |
| ARWEAVE_PRIVATE_KEY_FILE | Путь к JSON-файлу с JWK приватного ключа Arweave (подпись bundle tx) |

Локально: env; в Supabase: Secrets.

---

## 6. Порядок обработки

1. Парсинг тела, проверка обязательных полей → при ошибке 400.
2. Верификация JWT RS256 (подпись, exp, upload_id, payload_size ≤ max_bytes) → при ошибке 401, putStatus failed token_invalid.
3. Парсинг и проверка Data Item (подпись RSA-PSS, тег Upload-Id = upload_id) → при ошибке 400, putStatus failed signature_invalid.
4. putStatus queued_for_publish, ответ 200 { ack, status }.
5. Асинхронно: bundle из одного Data Item, подпись bundle tx оператором, отправка в Arweave; при успехе — postCallback; при ошибке — putStatus failed publish_failed.

---

**Версия:** 1.0  
**Дата:** 2026-01-29
