# Документация Bot API (`bot/docs/tech/api/`)

Единый **SSOT по маршрутам, auth и env** — **[`api.md`](./api.md)** (сверка с `bot/api/main.py`, `middleware`, `routes`).

| Файл | Назначение |
|------|------------|
| [**api.md**](./api.md) | Реестр путей, зоны HMAC / Bearer / wallet, переменные окружения, тесты, безопасность, пробелы |
| [**api-key-encryption-key.md**](./api-key-encryption-key.md) | Что такое `AMANITA_API_ENCRYPTION_KEY`, генерация ключа, проверка формата, безопасная ротация |
| [**vault-simple-manual.md**](./vault-simple-manual.md) | Простой гайд по HCP Vault: что создать, какие ключи положить, как связать с Railway (`polygon`) |
| [**commerce-upload-flow.md**](./commerce-upload-flow.md) | Поток e-commerce: `/media/upload` → `/description/upload` → `/products/upload`, схема тела, FAQ |
| [**auth-hmac-and-architecture.md**](./auth-hmac-and-architecture.md) | HMAC: строка подписи, пропуск путей, порядок middleware, связь с `ServiceFactory` (без дублирования таблиц из `api.md`) |
| [**wordpress-integration-requirements.md**](./wordpress-integration-requirements.md) | Продуктовые требования WooCommerce: что уже покрыто REST API, что вне текущего Bot API |
| [**logging.md**](./logging.md) | Логгер `amanita_api`, env, ротация, просмотр логов |
| [**activity-x-user-id.md**](./activity-x-user-id.md) | `X-User-Id` при `POST /activities/draft`: валидация, default `mock_user`, связка с upload и wallet-auth |
| **Activity vertical (ASG-3)** | Оркестратор `ActivityRegistryService`: `bot/services/application/activity/`; DI: `api.dependencies.get_activity_registry_service`; норматив: [`activity-services-architecture.md`](../activity-services-architecture.md); umbrella: [`task-umbrella-activity-evm-signing-gap-closure`](../../analysis/tasks/task-umbrella-activity-evm-signing-gap-closure/task-umbrella-activity-evm-signing-gap-closure.md) |

**Быстрый старт кода:** `bot/api/README.md`. **Схемы запросов:** `GET /docs`, `GET /openapi.json` на запущенном сервере. **Bullrun-таски Bot API:** [`bot/docs/analysis/tasks/bullrun-launch-index.md`](../../analysis/tasks/bullrun-launch-index.md).

**Custom GPT Actions (subset `/activities` + `/reference`):** готовый OpenAPI YAML в репозитории — `GPT UI/docs/custom-gpt-actions-activities-reference.openapi.yaml` (Bearer = `GPT_ACTIONS_BEARER_SECRET`, см. `api.md` §3.3). Пример проверки Bearer:

```bash
curl -sS -o /dev/null -w "%{http_code}" -H "Authorization: Bearer $GPT_ACTIONS_BEARER_SECRET" \
  "https://<host>/reference/languages"
```

---

При добавлении нового файла в эту папку — обновите таблицу выше и при необходимости §0 в `api.md`.
