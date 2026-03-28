# AMANITA Bot API — техническая документация (SSOT: код)

**Последняя сверка с кодом:** 2026-03-28 (GPT Actions Bearer)  
**Источники истины:** `bot/api/main.py`, `bot/api/middleware/auth.py`, `bot/api/config.py`, `bot/api/routes/*.py`.  
**Канонические схемы запросов/ответов:** интерактивно — `GET /docs`, `GET /openapi.json` (генерируется FastAPI).

---

## 1. Назначение и состав

REST API на **FastAPI** (зависимость: `fastapi>=0.104.0` в корневом `requirements.txt`). Две практически независимые зоны использования:

| Зона | Префиксы | Аутентификация (см. §3) |
|------|-----------|-------------------------|
| **E-commerce / реестр** | `/api-keys`, `/products`, `/media`, `/description` | **HMAC** (`X-API-Key`, `X-Timestamp`, `X-Nonce`, `X-Signature`) |
| **Activities / reference (GPT, моки)** | `/activities`, `/reference` | **Без HMAC**; при заданном `GPT_ACTIONS_BEARER_SECRET` — обязательный **`Authorization: Bearer`** (см. §3.3) |
| **Uploads / подписи (floou, mock-wallet)** | `/v1/uploads`, `/v1/sign-requests`, `/v1/pending-sign-requests` | **Без HMAC** на этих префиксах; см. §2.7–§3.2 |
| **Wallet auth (challenge/verify)** | `/v1/wallet-auth` | **HMAC не снят** с префикса в middleware — для вызова нужны те же заголовки HMAC, что и для commerce, либо расширение `skip_prefixes` в коде |

Точка входа приложения: `create_api_app()` в `bot/api/main.py`; для uvicorn в проде обычно монтируется `bot.api.main:app`.

Дополнительно в `main.py`:

- **Lifespan:** фоновый цикл финализатора upload (`run_finalizer`), интервал `UPLOAD_FINALIZER_INTERVAL_SEC` (по умолчанию `300` с).
- **Sentry:** `init_sentry()` при импорте модуля.
- Публичные точки: `/`, `/hello`, `/health`, `/health/detailed`, `/auth-test` (последний — проверка HMAC).

---

## 2. Реестр маршрутов (факт)

Пути ниже — **полные** HTTP path (без хоста). Методы — как в коде.

### 2.1 Без префикса роутера (`main.py`)

| Метод | Путь | Назначение |
|--------|------|------------|
| GET | `/` | Статус сервиса |
| GET | `/hello` | Smoke |
| GET | `/health` | Health (uptime, версия) |
| GET | `/health/detailed` | Health + компоненты + system metrics |
| POST | `/auth-test` | Проверка HMAC; в ответе `client_address` из `request.state` |

### 2.2 `/api-keys` (`routes/api_keys.py`)

| Метод | Путь | Примечание |
|--------|------|------------|
| POST | `/api-keys/` | Создание ключа |
| GET | `/api-keys/{client_address}` | Список ключей клиента |
| DELETE | `/api-keys/{api_key}` | Отзыв |
| GET | `/api-keys/validate/{api_key}` | Валидация |

### 2.3 `/products` (`routes/products.py`)

| Метод | Путь | Примечание |
|--------|------|------------|
| GET | `/products/{seller_address}` | Каталог продавца; `seller_address` — Ethereum `0x…` (не строка `upload`) |
| POST | `/products/upload` | Массовая загрузка/обновление |
| PUT | `/products/{product_id}` | Обновление продукта |
| POST | `/products/{product_id}/status` | Смена статуса |

### 2.4 `/media`, `/description`

| Метод | Путь | Файл |
|--------|------|------|
| POST | `/media/upload` | `routes/media.py` |
| POST | `/description/upload` | `routes/description.py` |

### 2.5 `/activities` (`routes/activities.py`) — мок/GPT lifecycle

| Метод | Путь |
|--------|------|
| POST | `/activities/draft` |
| GET | `/activities/me` |
| GET | `/activities/search` |
| POST | `/activities/search` |
| PUT | `/activities/{activity_id}` |
| POST | `/activities/{activity_id}/submit-review` |
| POST | `/activities/{activity_id}/publish` |
| DELETE | `/activities/{activity_id}/unpublish` |
| GET | `/activities/{activity_id}` |

Во многих хендлерах поддерживается query `simulate_error=…` для матрицы ошибок (см. описания в OpenAPI).

Заголовок **`X-User-Id`**: используется в `POST /activities/draft` (mock user при отсутствии); иначе auth на уровне HMAC не требуется для префикса `/activities`.

### 2.6 `/reference` (`routes/reference.py`)

| Метод | Путь |
|--------|------|
| GET | `/reference/formats` |
| GET | `/reference/taxonomy` |
| GET | `/reference/age-groups` |
| GET | `/reference/languages` |

### 2.7 `/v1` uploads (`routes/uploads.py`)

| Метод | Путь | Авторизация |
|--------|------|-------------|
| PUT | `/v1/uploads/{upload_id}/status` | `Authorization: Bearer <EDGE_TO_BACKEND_SECRET>` |
| POST | `/v1/uploads/callback` | То же Bearer |
| GET | `/v1/uploads/{upload_id}/sign-payload` | `authenticate_wallet_request`: `WALLET_AUTH_MODE`, `Authorization: Bearer <wallet_auth_token>` при challenge-режиме, иначе при `ALLOW_X_USER_ID_FALLBACK=true` — **обязателен `X-User-Id`** |

Тела статуса/callback — см. Pydantic-модели `PutStatusBody`, `CallbackBody` в том же файле.

### 2.8 `/v1` sign requests (`routes/sign_requests.py`)

| Метод | Путь |
|--------|------|
| GET | `/v1/sign-requests/{sign_request_id}` |
| POST | `/v1/sign-requests/{sign_request_id}/submit` |

### 2.9 `/v1` pending (`routes/pending_sign_requests.py`)

| Метод | Путь |
|--------|------|
| GET | `/v1/pending-sign-requests` |

### 2.10 `/v1/wallet-auth` (`routes/wallet_auth.py`)

| Метод | Путь | Тело |
|--------|------|------|
| POST | `/v1/wallet-auth/challenge` | `ChallengeBody`: `wallet_address`, `user_id`, `auth_scope` |
| POST | `/v1/wallet-auth/verify` | `VerifyBody`: `challenge_id`, `wallet_address`, `user_id`, `signature` |

Ответ verify при успехе: `wallet_auth_token`, `expires_at`, `token_type: bearer`. Ошибки — HTTP 401/403/409 с `detail.error_code` (см. код).

---

## 3. Аутентификация и middleware

### 3.1 HMAC (`middleware/auth.py`)

Заголовки: `X-API-Key`, `X-Timestamp`, `X-Nonce`, `X-Signature`.  
Строка для подписи: `{method}\n{path}\n{body}\n{timestamp}\n{nonce}` (тело для GET/DELETE — пустая строка).

**Пропуск HMAC** (`_should_skip_auth`), если путь:

- Точное совпадение: `/`, `/health`, `/health/detailed`, `/hello`, `/docs`, `/redoc`, `/openapi.json`
- Префиксы: `/activities`, `/reference`, `/v1/uploads`, `/v1/pending-sign-requests`, `/v1/sign-requests`

**Не входят в пропуск:** `/api-keys`, `/products`, `/media`, `/description`, `/auth-test`, **`/v1/wallet-auth`**.

Окно времени и nonce: `APIConfig.HMAC_TIMESTAMP_WINDOW`, `APIConfig.HMAC_NONCE_CACHE_TTL` (env: `AMANITA_API_HMAC_TIMESTAMP_WINDOW`, `AMANITA_API_HMAC_NONCE_CACHE_TTL`). Секрет для fallback-проверки подписи при отсутствии `ApiKeyService`: `AMANITA_API_HMAC_SECRET_KEY` (`APIConfig.HMAC_SECRET_KEY`).

### 3.2 Заголовок `X-User-Id` и wallet bearer

Логика для чувствительных read/write upload flow: `api/utils/wallet_auth_guard.py`:

- `WALLET_AUTH_MODE` (по умолчанию `challenge_signature`): при наличии `Authorization: Bearer` валидируется сессия через `WalletAuthService`.
- `ALLOW_X_USER_ID_FALLBACK` (по умолчанию `true`): при отсутствии валидного bearer допускается только `X-User-Id` (режим mock/local).

Интеграторам: для production отключения fallback см. env и протокол в `bot/docs/tech/wallet-auth-challenge-signature-protocol.md`.

### 3.3 Custom GPT Actions — Bearer на `/activities` и `/reference` (`middleware/gpt_actions_bearer.py`)

- **Переменная:** `GPT_ACTIONS_BEARER_SECRET` (читается в `APIConfig`; пустая строка или отсутствие — **проверка выключена**).
- **Префиксы:** `/activities`, `/reference` (все пути, начинающиеся с них).
- **Требование:** заголовок `Authorization: Bearer <секрет>`; сравнение через `secrets.compare_digest` (при неравной длине токена и секрета — 401 без исключения).
- **Ответ 401:** JSON с `success: false`, `error: gpt_actions_auth_error`, `error_code`: `missing_bearer` | `invalid_bearer`, `path`, `timestamp`.
- **Не путать с:** `EDGE_TO_BACKEND_SECRET` (Edge → upload status/callback), wallet session token из `POST /v1/wallet-auth/verify`.

Порядок в стеке: middleware регистрируется в `main.py` **до** `HMACMiddleware`, чтобы после пропуска HMAC для `/activities` запрос доходил до этой проверки.

---

## 4. Конфигурация окружения (факт из кода)

Общие (класс `APIConfig` в `bot/api/config.py`):

| Переменная | Назначение |
|------------|------------|
| `AMANITA_API_ENVIRONMENT` | Окружение |
| `AMANITA_API_HOST`, `AMANITA_API_PORT` | Bind сервера |
| `AMANITA_API_LOG_LEVEL`, `AMANITA_API_LOG_FILE`, `AMANITA_API_LOG_MAX_SIZE`, `AMANITA_API_LOG_BACKUP_COUNT` | Логи |
| `AMANITA_API_CORS_ORIGINS`, `AMANITA_API_CORS_ALLOW_CREDENTIALS` | CORS |
| `AMANITA_API_TRUSTED_HOSTS` | TrustedHostMiddleware |
| `AMANITA_API_HMAC_SECRET_KEY`, `AMANITA_API_HMAC_TIMESTAMP_WINDOW`, `AMANITA_API_HMAC_NONCE_CACHE_TTL` | HMAC |
| `AMANITA_API_DOCS_URL`, `AMANITA_API_REDOC_URL`, `AMANITA_API_OPENAPI_URL` | Доки |
| `GPT_ACTIONS_BEARER_SECRET` | Опционально: включает Bearer-границу для `/activities` и `/reference` (Custom GPT Actions); см. §3.3 |

Upload / edge / finalizer:

| Переменная | Где используется |
|------------|------------------|
| `EDGE_TO_BACKEND_SECRET` | `uploads.py` Bearer для status/callback |
| `ARWEAVE_SERVICE_URL` | Ответ `sign-payload` |
| `UPLOAD_FINALIZER_INTERVAL_SEC` | `main.py` lifespan |

Wallet:

| Переменная | Где |
|------------|-----|
| `WALLET_AUTH_MODE`, `ALLOW_X_USER_ID_FALLBACK` | `wallet_auth_guard.py` |

---

## 5. Ответы и ошибки

Успешные ответы Activities/uploads часто собираются через `build_success_response` / `JSONResponse` с полем `success: true` там, где это заложено в роуте.

Глобальные обработчики подключены в `main.py`: `RequestValidationError`, `ValidationError`, `HTTPException`, `StarletteHTTPException`, общий `Exception` (см. `bot/api/error_handlers.py`).

Для HMAC-ошибок middleware возвращает JSON со `success: false`, `error: authentication_error`, полем `path` и `timestamp`.

---

## 6. Развёртывание

```bash
# из корня репозитория, с настроенным PYTHONPATH при необходимости
uvicorn bot.api.main:app --host 0.0.0.0 --port 8000
```

Режим разработки в `if __name__ == "__main__"` использует `reload=True` и снова создаёт `app` через `create_api_app()`.

---

## 7. Тестирование

Структура тестов проекта — под каталогом **`bot/tests/`** (unit, integration), а не `tests/api/` (устаревший путь из старых шаблонов).

Примеры:

```bash
cd bot && python3 -m pytest tests/ -q --tb=short
cd bot && python3 -m pytest tests/unit/test_wallet_auth_enforcement.py -v
```

Маркеры и опции см. `bot/pytest.ini` и `bot/pyproject.toml` (`[tool.pytest.ini_options]`).

---

## 8. Безопасность (кратко)

1. **HMAC** на commerce-маршрутах; окно timestamp и одноразовый nonce.  
2. **Bearer** секрет Edge → backend на `PUT/POST` upload status/callback — не логировать.  
3. **Wallet token** и **X-User-Id fallback** — явно конфигурируемы; для публичного API отключать fallback.  
4. **CORS / Trusted Host** — через env.  
5. Заголовки безопасности в ответах HMAC-middleware: `X-Content-Type-Options`, `X-Frame-Options`, `X-XSS-Protection`.  
6. **GPT Actions:** задавайте `GPT_ACTIONS_BEARER_SECRET` в production на публичном хосте; ротируйте ключ при утечке из настроек ChatGPT; один секрет не даёт per-user изоляции — для этого OAuth/прокси.

Адреса контрактов в клиентах **не хардкодить** из документации — брать из деплоя и конфигурации узла.

---

## 9. Планы и пробелы (для интеграции)

- **Единый префикс версии** (`/v1`) сейчас только у части маршрутов; клиенты должны собирать полный path как в §2.  
- **`GET /activities/by-upload/{upload_id}`** (resolve по upload) в коде на дату сверки **отсутствует** — см. таск `task-implement-activity-resolve-by-upload-id`.  
- При необходимости **публичного** `POST /v1/wallet-auth/challenge` без HMAC — требуется изменение `_should_skip_auth` в `auth.py` и отдельный security review.

---

## 10. Заключение

Документ описывает **фактическое** поведение Bot API для интеграции. Детальные JSON-схемы и примеры тел запросов — в **OpenAPI** (`/docs`). При расхождении кода и этой заметки приоритет у **кода**; этот файл следует обновлять при добавлении роутеров или изменении middleware.
