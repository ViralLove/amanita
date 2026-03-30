# Архитектура микросервиса arweave-uploader

Постоянный документ: архитектура решения, поток данных, обработка crystall (публикация в Arweave) и все конфигурируемые элементы.

**Версия:** 0.2.0  
**Статус:** Production (smoke: health 200, POST /v1/crystalize отвечает 400/401 без полного тела).

---

## 1. Назначение и границы

**Микросервис** — HTTP relay для публикации в Arweave **уже подписанных** Data Item (ANS-104). Принимает подписанный item по контракту, верифицирует подпись и тег Upload-Id, упаковывает в bundle и отправляет в Arweave. Данными владеет отправитель (подпись своим ключом).

- **Вход:** HTTP POST `POST /v1/crystalize` с телом `{ upload_id, upload_token, signed_data_item, payload_size }`.
- **Выход:** 200 + тело с `ack`, `status`, `bundle_tx_id`, `arweave_url` или коды ошибок (400/401/502).
- **Внешняя зависимость:** Arweave (gateway), опционально Backend (PUT status, POST callback).

---

## 2. Высокоуровневый поток (crystalize)

```
Клиент (backend, скрипт)
    │
    │  POST /v1/crystalize
    │  Body: { upload_id, upload_token (JWT), signed_data_item (base64 ANS-104), payload_size }
    ▼
┌─────────────────────────────────────────────────────────────────┐
│  arweave-uploader (Node, Fastify)                                │
│  1. Валидация body (обязательные поля)                          │
│  2. verifyUploadToken (JWT RS256, upload_id, max_bytes, exp)     │
│  3. validateDataItem (подпись RSA-PSS, тег Upload-Id)             │
│  4. putStatus(queued_for_publish)                                │
│  5. bundleAndPublish(signedDataItemBytes) → Arweave              │
│  6. postCallback(uploadId, itemId, bundleTxId)                   │
│  7. Ответ 200 { ack, status, bundle_tx_id, arweave_url } или 400/401/502 │
└─────────────────────────────────────────────────────────────────┘
```

- **Порт** задаётся платформой (`PORT`). Подпись bundle-транзакции — JWK из `ARWEAVE_PRIVATE_KEY` или `ARWEAVE_PRIVATE_KEY_FILE`.

---

## 3. Контракт API

### 3.1 GET /health

- **Назначение:** проверка живости сервиса (в т.ч. Railway, smoke).
- **Авторизация:** не требуется.
- **Ответ 200:** `{ "ok": true, "service": "arweave-uploader", "version": "0.2.0" }`.

---

## 4. Модули и ответственность

| Модуль | Файл | Ответственность |
|--------|------|-----------------|
| **Конфиг** | `config.js` | PORT, ARWEAVE_*; загрузка JWK из env или файла. |
| **Авторизация** | `auth.js` | Проверка `Authorization: Bearer` против `relayAuthToken` (опционально). |
| **Arweave-клиент** | `arweave-client.js` | Инициализация arweave и jwk для bundleAndPublish (подпись bundle-транзакции). |
| **Логирование** | `logging.js` | JSON в stdout: logInfo/logWarn/logError, sha256Hex, errorToMessage. |
| **Сервер** | `server.js` | Fastify, маршруты GET /health и POST /v1/crystalize, обработка ошибок. |
| **verifyUploadToken** | `publish/validate-token.js` | Проверка JWT RS256 (upload_id, max_bytes, exp); ключ из UPLOAD_TOKEN_JWT_PUBLIC_KEY. |
| **validateDataItem** | `publish/validate-data-item.js` | Парсинг ANS-104 Data Item, проверка подписи RSA-PSS и тега Upload-Id. |
| **deepHash** | `publish/deep-hash.js` | Arweave deep-hash для верификации Data Item (внутри validateDataItem). |
| **bundleAndPublish** | `publish/bundle-publish.js` | Сборка bundle из одного Data Item, подпись и отправка в Arweave. |

---

## 5. Конфигурируемые элементы (env)

Все настройки через переменные окружения; конфиг приложения порт не задаёт — его задаёт платформа (например Railway).

| Переменная | Обязательность | По умолчанию | Описание |
|------------|----------------|--------------|----------|
| **PORT** | нет | 3000 | Порт HTTP-сервера (в Railway обычно подставляется платформой). |
| **RELAY_AUTH_TOKEN** | нет | — | Секрет для `Authorization: Bearer`. Если не задан, endpoint открыт (в лог пишется предупреждение). |
| **ARWEAVE_PRIVATE_KEY** | да* | — | JWK ключ Arweave одной строкой (JSON). *Либо задаётся ARWEAVE_PRIVATE_KEY_FILE. |
| **ARWEAVE_PRIVATE_KEY_FILE** | да* | — | Путь к файлу с JWK (используется, если ARWEAVE_PRIVATE_KEY не задан). |
| **ARWEAVE_PROTOCOL** | нет | https | Протокол к gateway: `http` или `https`. |
| **ARWEAVE_HOST** | нет | arweave.net | Хост Arweave gateway. |
| **ARWEAVE_PORT** | нет | 443 (при https) / 80 (при http) | Порт gateway. |

Приоритет ключа: `ARWEAVE_PRIVATE_KEY` > `ARWEAVE_PRIVATE_KEY_FILE`; если ни одного нет — старт приложения падает с ошибкой.

### 5.1 Режим мока Backend

Когда микросервис вызывает Backend (PUT status, POST callback), для тестов без развёрнутого Backend можно включить режим мока. Полное описание: **[docs/backend-mock-mode.md](backend-mock-mode.md)**.

| Переменная | Назначение |
|------------|------------|
| **BACKEND_USE_MOCK** | `true`/`1` — не выполнять реальный fetch к Backend; логировать вызовы и при необходимости симулировать 200/404/409. |
| **BACKEND_MOCK_PUT_STATUS** | Симулированный код для PUT …/status: `200` \| `404` \| `409` (по умолчанию 200). |
| **BACKEND_MOCK_CALLBACK** | Симулированный код для POST …/callback: `200` \| `404` \| `409` (по умолчанию 200). |
| **BACKEND_MOCK_ALLOW_REQUEST_OVERRIDE** | `true`/`1` — разрешить переопределение симулированного ответа по заголовкам запроса (X-Backend-Mock-Put-Status, X-Backend-Mock-Callback). |
| **BACKEND_MOCK_TEST_SECRET** | Секрет для заголовка X-Backend-Mock-Secret (учёт override только при совпадении). |
| **UPLOAD_TOKEN_JWT_PUBLIC_KEY** | Публичный ключ (PEM или JWK) для проверки JWT RS256 в теле запроса POST /v1/crystalize. Обязателен для приёма crystalize. |
| **UPLOAD_TOKEN_DEBUG_PEM** / **DEBUG_PEM** | `true` / `1` / `yes` (без учёта регистра) — подробные логи `[pem-diag]` при нормализации ключа. По умолчанию выключено; при ошибке декодирования PEM диагностика всё равно пишется. |

### Реальный Backend (бот)

Если **не** включён `BACKEND_USE_MOCK`, для `PUT …/v1/uploads/…/status` и `POST …/v1/uploads/callback` нужны **`BACKEND_URL`** и секрет **`UPLOADER_TO_BACKEND_SECRET`** или **`EDGE_TO_BACKEND_SECRET`** (одинаковая строка с приёмником на bot). Подробно: **[backend-integration.md](backend-integration.md)**.

---

### 5.2 POST /v1/crystalize (Data Item → bundle → Arweave)

Маршрут принимает тело с полями: `upload_token` (JWT RS256), `upload_id`, `signed_data_item` (base64 Data Item ANS-104), `payload_size` (число). Порядок: проверка body → `verifyUploadToken` → `validateDataItem` (подпись RSA-PSS, тег Upload-Id) → `putStatus(queued_for_publish)` → `bundleAndPublish` → при успехе `postCallback`, иначе `putStatus(failed, publish_failed)`. Коды: 400 (missing/signature_invalid), 401 (token_invalid), 502 (publish_failed). Логи: `publish.request.received`, `publish.token_invalid`, `publish.data_item_invalid`, `publish.bundle_failed`, `publish.bundle_success` (без тела токена и signed_data_item).

**Ответ 200 при успехе:** `{ "ack": true, "status": "queued_for_publish", "bundle_tx_id": "<id транзакции бандла в Arweave>", "arweave_url": "<protocol>://<host>/<bundle_tx_id>" }`. Поле `arweave_url` формируется из конфига (`ARWEAVE_PROTOCOL`, `ARWEAVE_HOST`).

**Версионность API:** префикс `/v1/` — версия контракта; имя действия — `crystalize`. При несовместимых изменениях в будущем вводится `/v2/crystalize`.

---

## 6. Сборка и запуск

- **Сборка:** `npm run build` → `dist/` (Node ESM).
- **Запуск:** `node dist/server.js` (или `npm start`); в Docker — тот же CMD, порт из `PORT`.
- **Деплой:** см. `docs/deploy/railway-docker.md`, `docs/deploy/deploy-options.md`.
- **Проверка после деплоя:** `docs/deploy/railway-docker.md` (curl, smoke `scripts/smoke-deployed.sh`). Опционально: реальная загрузка в Arweave (шаг 3 smoke) — см. переменные `SMOKE_REAL`, `SMOKE_JWT_PRIVATE_KEY_*` в `.env.example`; на деплое задать соответствующий `UPLOAD_TOKEN_JWT_PUBLIC_KEY`.

---

## 7. Связанные документы

- **Интеграция с bot (реальные callback/status):** `docs/backend-integration.md` — `BACKEND_URL`, секрет, связка с `OWN_AUTH_TOKEN` / `EDGE_TO_BACKEND_SECRET` на боте.
- **Режим мока Backend:** `docs/backend-mock-mode.md` — переменные, заголовки, переключение на лету.
- **Деплой и проверка:** `docs/deploy/railway-docker.md`, `docs/deploy/deploy-options.md`
- **Тесты:** Unit: `npm run test:unit` (см. `docs/testing-unit.md`). Сводные publish: `node tests/publish-flow.test.js` (требуют ARWEAVE_PRIVATE_KEY, BACKEND_USE_MOCK=true).
- **Авторизация:** `docs/analysis/audit-bearer-auth.md`
- **Интеграция (Supabase/issue):** `docs/analysis/tasks/.../integration-contract-supabase.md`
- **Мерж Edge → uploader и polling vs callback:** `docs/analysis/gap-analysis-merge-edge-to-uploader.md`, `docs/analysis/analysis-polling-vs-callback.md`
