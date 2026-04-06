# Uploader ↔ Node (bot): авторизация и переменные окружения (референс)

**Версия:** 2.1  
**Статус:** референс по **фактическому коду** (arweave-uploader + bot)  
**Таск (исторический контекст):** [task-tests-phase3-full-cycle-real-db-real-arweave-uploader](../analysis/tasks/task-tests-phase3-full-cycle-real-db-real-arweave-uploader.md)

Документ фиксирует, как uploader вызывает bot после `POST /v1/crystalize` (**PUT** статуса, **POST** callback) и какие env-переменные должны совпасть. Расширенное описание на стороне uploader: [arweave-uploader/docs/backend-integration.md](../../../arweave-uploader/docs/backend-integration.md).

---

## 1. Направления и секреты

| Направление | Что проверяется | Где в коде |
|-------------|-----------------|------------|
| **uploader → bot** | Один общий секрет в `Authorization: Bearer` | uploader: `dist/publish/backend-calls.js`; bot: `api/routes/uploads.py` → `verify_edge_bearer` / `_get_edge_secret()` |
| **bot → uploader** (crystalize) | Отдельно: JWT на теле + опционально `RELAY_AUTH_TOKEN` на uploader | uploader: `verifyUploadToken`, `RELAY_AUTH_TOKEN`; bot — клиент crystalize в тестах/сервисах |

Ниже — только строка **uploader → bot** (callback / status).

---

## 2. Bot: приём PUT …/status и POST …/callback

| Файл | Реализация |
|------|------------|
| `bot/api/routes/uploads.py` | `_get_edge_secret()`: **`NODE_AUTH_TOKEN`** OR **`EDGE_TO_BACKEND_SECRET`** OR **`OWN_AUTH_TOKEN`** OR dev-fallback `mock-edge-to-backend-secret`. `verify_edge_bearer` сравнивает Bearer с этим значением (`compare_digest`). |

Тесты и curl часто выставляют **`EDGE_TO_BACKEND_SECRET`** или **`OWN_AUTH_TOKEN`** — это корректно, если **`NODE_AUTH_TOKEN`** не задан.

---

## 3. arweave-uploader: исходящие вызовы к bot

| Файл | Реализация |
|------|------------|
| `arweave-uploader/dist/publish/backend-calls.js` | База URL: **`BACKEND_URL`**. Секрет: **`NODE_AUTH_TOKEN`**. Заголовок: `Authorization: Bearer <секрет>`. Если нет URL или секрета — вызов не выполняется (лог с `publish.backend.skip`). |
| Режим без реального HTTP | **`BACKEND_USE_MOCK=true`** — см. [backend-mock-mode.md](../../../arweave-uploader/docs/backend-mock-mode.md) |

---

## 4. Сводка переменных (общий секрет `S`)

**Согласовать одну строку `S` на обеих сторонах (рекомендуется `NODE_AUTH_TOKEN`):**

| Сервис | Переменные |
|--------|------------|
| **arweave-uploader** | `BACKEND_URL` (origin bot, без `/v1`), `NODE_AUTH_TOKEN=S` |
| **bot** | `NODE_AUTH_TOKEN=S` (или `EDGE_TO_BACKEND_SECRET=S` / `OWN_AUTH_TOKEN=S` по приоритету в `_get_edge_secret`) |

**Входящий** crystalize на uploader не использует `OWN_AUTH_TOKEN` бота — для relay задаётся **`RELAY_AUTH_TOKEN`** на uploader; для JWT — пара ключей (см. `arweave-uploader/docs/api.md`).

---

## 5. Проверка (AC-ориентир)

| Критерий | Как сверить с кодом |
|----------|---------------------|
| Bearer на bot | `grep _get_edge_secret uploads.py` — порядок `NODE_AUTH_TOKEN`, `EDGE_TO_BACKEND_SECRET`, `OWN_AUTH_TOKEN`. |
| Исходящий вызов uploader | `grep NODE_AUTH_TOKEN backend-calls.js`, база `BACKEND_URL`. |
| Примеры env | `arweave-uploader/.env.example`, `bot/.env.example` (секции uploads / BACKEND). |

---

## 6. Ссылки

- **SSOT по callback/status:** [backend-integration.md](../../../arweave-uploader/docs/backend-integration.md)
- Внешний API uploader: [api.md](../../../arweave-uploader/docs/api.md)
- Исторические материалы таска (имена env могут отличаться от прод-кода): [vision-env-and-exact-solution.md](../analysis/tasks/task-tests-phase3-full-cycle-real-db-real-arweave-uploader/vision-env-and-exact-solution.md), [env-backend-and-secret.md](../analysis/tasks/task-tests-phase3-full-cycle-real-db-real-arweave-uploader/env-backend-and-secret.md)
