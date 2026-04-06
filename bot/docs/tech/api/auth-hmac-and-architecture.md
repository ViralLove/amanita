# Аутентификация и слой API (HMAC, middleware)

**Канон:** таблицы зон, пропусков и env — **[`api.md`](./api.md)** §1, §3, §4. Здесь — алгоритм HMAC и архитектурный контекст без повторения реестра маршрутов.

## Роль FastAPI

- Приложение создаётся в **`create_api_app()`** (`bot/api/main.py`), опционально с **`ServiceFactory`** для `ApiKeyService` в HMAC.
- Документация и схемы — **OpenAPI** (`/docs`, `/openapi.json`).

## HMAC: строка подписи и заголовки

Заголовки: `X-API-Key`, `X-Timestamp`, `X-Nonce`, `X-Signature`.

Строка для подписи (как в `middleware/auth.py`):

```text
{method}\n{path}\n{body}\n{timestamp}\n{nonce}
```

Для GET/DELETE тело — пустая строка. Подпись: HMAC-SHA256 от секрета ключа (детали валидации ключа и окна времени — в коде и `api.md` §3.1).

## Какие пути не проходят HMAC

Список `skip_paths` и `skip_prefixes` — **только в коде** `_should_skip_auth`; кратко в [`api.md`](./api.md) §3.1.

Важно: отсутствие HMAC ≠ отсутствие авторизации (uploads — Bearer edge; activities/reference — опциональный `GPT_ACTIONS_BEARER_SECRET`, см. `api.md` §3.3).

## Порядок middleware (входящий запрос)

Регистрация в `main.py`: CORS → TrustedHost → **GptActionsBearerMiddleware** → **HMACMiddleware** (последний добавленный выполняется первым → сначала HMAC, затем Bearer, …). Подробно — `api.md` §3.3.

## Связь с ботом и сервисами

- Общие сервисы (блокчейн, каталог и т.д.) приходят через **`ServiceFactory`**, передаваемый в `create_api_app(service_factory=...)`.
- Telegram-бот и API могут жить в одном репозитории и разделять сервисы; точка входа API для uvicorn — модуль **`api.main`**, а не смешивание с polling в одном процессе без явной оркестрации.

## Дальнейшее чтение

- Wallet / upload guard: `api.md` §3.2, `bot/docs/tech/wallet-auth-challenge-signature-protocol.md`.
- Протокол Edge → backend: `api.md` §2.7.
