# Знания и мышление для таска: Edge Function (user signs, operator pays)

**Таск:** [task-implement-arweave-upload-edge-function.md](task-implement-arweave-upload-edge-function.md)  
**Дата:** 2026-01-29  
**Цель:** активировать нужные знания и тип мышления перед реализацией; ждать дальнейших указаний.

---

## 1. Необходимые знания (домены)

### 1.1 Supabase Edge Functions (Deno)

- **Роутинг:** `serve()`, `req.url` → `URL(pathname)`, ветвление по `path.endsWith('/edge/v1/publish')` и `req.method === 'POST'`.
- **Конфигурация:** `Deno.env.get()` для секретов; публичный ключ JWT и `BACKEND_URL` — из Supabase Secrets / env, не в коде.
- **Ответы:** JSON, CORS headers (уже есть в `index.ts`), коды 200/4xx/5xx, тело с `code` при ошибках (`token_invalid`, `signature_invalid`, `publish_failed`).
- **Контекст:** текущая функция — `/health`, `/upload-text`, `/upload-file`; добавить маршрут **POST /edge/v1/publish** без ломания существующих.

### 1.2 JWT RS256 в Deno

- **Контракт:** Backend подписывает JWT **приватным** RSA; Edge проверяет **публичным** ключом (JWK или PEM в Secrets).
- **Claims:** `upload_id`, `user_id`, `max_bytes`, `exp`. Проверки: подпись RS256, `exp > now`, `upload_id` из payload === `upload_id` из тела запроса, `payload_size <= max_bytes`.
- **Инструменты:** Web Crypto API (`crypto.subtle.importKey` для публичного ключа, верификация подписи) или библиотека типа **djwt** (Deno JWT) с алгоритмом RS256.
- **Ошибка:** невалидный/истёкший токен → ответ `code: token_invalid` + вызов Backend **PUT /v1/uploads/{upload_id}/status** с `status=failed`, `failure_code=token_invalid`.

### 1.3 Arweave Data Item (формат и проверка)

- **Вход:** `signed_data_item` (serialized) в теле запроса — по контракту от Wallet; типично **base64** или бинарный буфер.
- **Структура Data Item (ANS-104 / Arweave):** id, raw payload, signature, tags; подпись — RSA-PSS (пользователь подписывает в Wallet).
- **Sanity check в Edge:** (1) парсинг формата (десериализация); (2) проверка подписи Data Item (RSA-PSS, публичный ключ из item/owner); (3) наличие тега `Upload-Id` и совпадение значения с `upload_id` из запроса.
- **Ошибка:** невалидная подпись или тег → `code: signature_invalid` + Backend status=failed, `failure_code=signature_invalid`.
- **Уточнение:** точный формат serialized Data Item (binary layout ANS-104 vs JSON vs custom) и способ извлечения `item_id` / `owner_address` — согласовать с Wallet или взять из референса Arweave/архитектуры.

### 1.4 Arweave Bundles и публикация

- **Роль Edge:** принять **уже подписанный** Data Item от пользователя; **не** подписывать данные пользователя; собрать bundle (или один item), создать **bundle tx** (on-chain), подписать **bundle tx** кошельком оператора (operator JWK), отправить в Arweave.
- **Оператор платит:** только подпись и отправка **bundle-транзакции** (оплата комиссии); данные внутри bundle подписаны пользователем.
- **N=1:** по эпику допустимо публиковать один item сразу (без батча); при одном item — либо single-item bundle, либо одна Arweave tx с данными item по формату Arweave.
- **Существующий код:** `arweave/compatible.ts` + `crypto/` (pss_wasm или arweave-rsa-pss) — подпись **транзакции** оператором; переиспользовать для подписи **bundle tx**. Формат bundle: ANS-104 (bundle bytes = заголовок + data items).
- **Результат:** получить `bundle_tx_id` от Arweave, передать в Backend callback.

### 1.5 Вызовы Backend из Edge

- **PUT /v1/uploads/{upload_id}/status** — тело `{ "status": "queued_for_publish" }` или `{ "status": "failed", "failure_code": "token_invalid" | "signature_invalid" | "publish_failed" }`. Вызывать: после успешной валидации (queued_for_publish); при любой ошибке валидации/публикации (failed + code).
- **POST /v1/uploads/callback** — тело `{ upload_id, item_id, bundle_tx_id, published_at }`. Вызывать только после успешной публикации в Arweave.
- **Авторизация:** по контракту bot–Edge (секрет в заголовке, например `Authorization: Bearer EDGE_TO_BACKEND_SECRET` или отдельный заголовок); Backend проверяет, что вызов от Edge. URL Backend — из env (`BACKEND_URL`).
- **Реализация:** `fetch(BACKEND_URL + "/v1/uploads/" + upload_id + "/status", { method: "PUT", headers, body: JSON.stringify(...) })` и аналогично для callback; обрабатывать сетевые ошибки и при необходимости вызывать status=failed (publish_failed).

### 1.6 Обработка ошибок и коды

- **Единая схема:** при любой ошибке (token, signature, publish) — ответ клиенту с полем `code`; вызов Backend **PUT status** с `status=failed` и соответствующим `failure_code`, чтобы Backend и клиент (realtime) были в консистентном состоянии.
- **Не логировать:** payload, signed_data_item, секреты, ключи; логировать только факты: «запрос принят», «токен ок/не ок», «Data Item ок/не ок», «вызов status», «публикация ок/не ок», «callback отправлен».

---

## 2. Тип мышления (reasoning)

- **Контракт-первый:** каждый шаг сверять с [Arweave data upload.md](../../../docs/analysis/epics/activities%20crud%20and%20search/Arweave%20data%20upload.md) (разд. 4.2, 4.3, 10) и с таском 3.2 (bot) — форматы запроса/ответа, тел PUT/POST, коды ошибок.
- **Безопасность:** без валидного токена и валидной подписи Data Item — не вызывать публикацию; при любой ошибке — уведомить Backend (status=failed), чтобы не оставлять upload в подвешенном состоянии.
- **Разделение ответственности:** Edge не выпускает токены, не хранит приватный ключ пользователя; только проверяет JWT (публичный ключ Backend), проверяет подпись Data Item, подписывает bundle tx ключом оператора.
- **Тестируемость:** вынести валидацию токена, валидацию Data Item и вызовы Backend в отдельные модули (например `publish/validate-token.ts`, `publish/validate-data-item.ts`, `publish/backend-calls.ts`), чтобы покрыть unit-тестами с моками.
- **Пошаговый план:** следовать плану из таска (контракт и маршрут → JWT RS256 → Data Item → Backend status → bundling/публикация → Backend callback → тесты); не переходить к публикации до рабочей валидации и вызова status.

---

## 3. Открытые точки (уточнить при реализации)

| Вопрос | Варианты / референс |
|--------|----------------------|
| Формат `signed_data_item` (serialized) | Base64 бинарного Data Item (ANS-104)? Или JSON с полями? Согласовать с Wallet / Arweave data upload. |
| Где брать публичный ключ для проверки подписи Data Item | Из самого Data Item (owner / id); Arweave формат допускает извлечение. |
| Bundle при N=1 | Один item упаковать в ANS-104 bundle из одного элемента или отправить как одну Arweave tx — проверить по Arweave SDK и контракту. |
| Существующий `arweave-rsa-pss.ts` | В `compatible.ts` импорт из `../crypto/arweave-rsa-pss.ts`; в `crypto/` есть только `pss_wasm.ts`. Либо добавить файл, либо переключить compatible на pss_wasm для подписи bundle tx. |

---

## 4. Активировано

- Домены: Edge (Deno) роутинг и env; JWT RS256 верификация; Data Item формат и проверка подписи; Arweave bundle и подпись bundle tx оператором; вызовы Backend (PUT status, POST callback); коды ошибок и логирование.
- Мышление: контракт-первый, безопасность (token + signature gate), разделение ответственности, модульность для тестов, пошаговый план по таску.
- Открытые точки зафиксированы для уточнения при реализации.

**Жду дальнейших указаний.**
