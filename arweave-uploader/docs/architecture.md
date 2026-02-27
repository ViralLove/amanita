# Архитектура микросервиса arweave-uploader

Постоянный документ: архитектура решения, поток данных, обработка canonical issue и все конфигурируемые элементы.

**Версия:** 0.1.0  
**Статус:** Production (smoke: health 200, POST /upload-canonical-issue 200 с transaction_id и url).

---

## 1. Назначение и границы

**Микросервис** — HTTP relay для публикации **canonical issue** в Arweave. Принимает JSON payload по контракту, подписывает транзакцию ключом, отправляет в Arweave gateway и возвращает `transaction_id` и URL.

- **Вход:** HTTP POST с телом `{ data, contentHash }` и опциональной Bearer-авторизацией.
- **Выход:** 200 + `{ success, transaction_id, url }` или коды ошибок (400/401/502/500).
- **Внешняя зависимость:** Arweave (сеть + gateway, например `arweave.net`).

---

## 2. Высокоуровневый поток (canonical issue → Arweave)

```
Клиент (Supabase/issue, curl, скрипт)
    │
    │  POST /upload-canonical-issue
    │  Authorization: Bearer <RELAY_AUTH_TOKEN>
    │  Body: { "data": "<json string>", "contentHash": "<64 hex>" }
    ▼
┌─────────────────────────────────────────────────────────────────┐
│  arweave-uploader (Node, Fastify)                                │
│  1. Auth (если задан RELAY_AUTH_TOKEN)                           │
│  2. Validation (Zod: data string, contentHash 64 hex)            │
│  3. Log (upload.request.received)                                │
│  4. ArweaveClient.uploadCanonicalIssue(payload)                  │
│     ├── createTransaction({ data })                              │
│     ├── addTag(App-Name, Schema, Content-Type, Content-Hash)     │
│     ├── sign(tx, jwk)                                            │
│     └── post(tx) → gateway                                       │
│  5. Ответ: 200 + { transaction_id, url } или 502/500             │
└─────────────────────────────────────────────────────────────────┘
    │
    │  HTTPS → arweave.net (или ARWEAVE_HOST:ARWEAVE_PORT)
    ▼
Arweave gateway → сеть Arweave
```

- **Порт приложения** задаётся платформой (например Railway через `PORT`), не зашит в коде.
- **Ключ подписи** — JWK из `ARWEAVE_PRIVATE_KEY` (строка JSON) или из файла `ARWEAVE_PRIVATE_KEY_FILE`.

---

## 3. Контракт API

### 3.1 GET /health

- **Назначение:** проверка живости сервиса (в т.ч. Railway, smoke).
- **Авторизация:** не требуется.
- **Ответ 200:** `{ "ok": true, "service": "arweave-uploader", "version": "0.1.0" }`.

### 3.2 POST /upload-canonical-issue

- **Headers:** `Content-Type: application/json`, при включённой защите — `Authorization: Bearer <RELAY_AUTH_TOKEN>`.
- **Body (JSON):**
  - `data` (string) — содержимое транзакции (например JSON canonical issue), минимум 1 символ.
  - `contentHash` (string) — SHA-256 хеш содержимого в hex, ровно 64 символа `[a-f0-9]`.
- **Успех 200:**  
  `{ "success": true, "transaction_id": "<txid>", "url": "https://arweave.net/<txid>" }`.
- **Ошибки:**
  - 400 — не прошла валидация тела (`VALIDATION_ERROR`).
  - 401 — нет/неверный Bearer (`UNAUTHORIZED`).
  - 502 — Arweave вернул status >= 400 (`ARWEAVE_POST_FAILED`).
  - 500 — исключение при обработке (`INTERNAL_ERROR`).

Теги транзакции в Arweave: `App-Name: DOGEESTONIA`, `Schema: canonical-issue-v1`, `Content-Type: application/json`, `Content-Hash: <payload.contentHash>`.

---

## 4. Модули и ответственность

| Модуль | Файл | Ответственность |
|--------|------|-----------------|
| **Конфиг** | `config.ts` | PORT, RELAY_AUTH_TOKEN, ARWEAVE_*; загрузка JWK из env или файла. |
| **Авторизация** | `auth.ts` | Проверка `Authorization: Bearer` против `relayAuthToken`; при отсутствии токена — пропуск. |
| **Валидация** | `validation.ts` | Zod-схема для тела запроса: `data`, `contentHash` (64 hex). |
| **Arweave-клиент** | `arweave-client.ts` | createTransaction → теги → sign → post; возврат tx id и status. |
| **Логирование** | `logging.ts` | JSON в stdout: logInfo/logWarn/logError, sha256Hex, errorToMessage. |
| **Типы** | `types.ts` | UploadCanonicalIssueRequest, UploadSuccessResponse, UploadErrorResponse. |
| **Сервер** | `server.ts` | Fastify, маршруты /health и /upload-canonical-issue, сборка конфига и ArweaveClient, обработка ошибок. |

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

---

## 6. Поток данных (canonical issue)

1. **Клиент** формирует canonical issue (JSON), считает SHA-256 от строки `data` в hex — это `contentHash`.
2. **Клиент** шлёт `POST /upload-canonical-issue` с `{ data, contentHash }`.
3. **Сервер** проверяет Bearer (если задан `RELAY_AUTH_TOKEN`).
4. **Сервер** валидирует тело (Zod); при ошибке — 400.
5. **ArweaveClient** создаёт транзакцию с `data` (как bytes), добавляет теги (в т.ч. `Content-Hash`), подписывает JWK, шлёт в gateway.
6. **Сервер** по status ответа gateway: 2xx → 200 и `{ transaction_id, url }`; иначе 502 с `ARWEAVE_POST_FAILED`.
7. Любое исключение в цепочке (сеть, парсинг, ключ) → лог `upload.failed`, ответ 500 `INTERNAL_ERROR`.

Ссылка на контент после успеха: `https://arweave.net/<transaction_id>`.

---

## 7. Сборка и запуск

- **Сборка:** `npm run build` → `dist/` (Node ESM).
- **Запуск:** `node dist/server.js` (или `npm start`); в Docker — тот же CMD, порт из `PORT`.
- **Деплой:** см. `docs/deploy/railway-docker.md`, `docs/deploy/deploy-options.md`.
- **Проверка после деплоя:** `docs/deploy/railway-docker.md` (curl, smoke `scripts/smoke-deployed.sh`).

---

## 8. Связанные документы

- **Режим мока Backend:** `docs/backend-mock-mode.md` — переменные, заголовки, переключение на лету.
- **Деплой и проверка:** `docs/deploy/railway-docker.md`, `docs/deploy/deploy-options.md`
- **Тесты:** `docs/testing/run-tests.md`
- **Авторизация:** `docs/analysis/audit-bearer-auth.md`
- **Интеграция (Supabase/issue):** `docs/analysis/tasks/.../integration-contract-supabase.md`
- **Мерж Edge → uploader и polling vs callback:** `docs/analysis/gap-analysis-merge-edge-to-uploader.md`, `docs/analysis/analysis-polling-vs-callback.md`
