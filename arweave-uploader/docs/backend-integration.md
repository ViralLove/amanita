# Интеграция с Backend (бот, нода): статусы и callback

После `POST /v1/crystalize` uploader при **не** мокированном backend пытается уведомить ваш сервис:

1. **PUT** `{BACKEND_URL}/v1/uploads/{upload_id}/status` — когда статус ставится в `queued_for_publish` или `failed` (с `failure_code`).
2. **POST** `{BACKEND_URL}/v1/uploads/callback` — после успешной публикации bundle в Arweave (тело: `upload_id`, `item_id`, `bundle_tx_id`, `published_at`).

Обе операции используют один и тот же заголовок авторизации.

---

## Переменные окружения на arweave-uploader

| Переменная | Обязательность | Описание |
|------------|----------------|----------|
| **BACKEND_URL** | да (для реальных вызовов) | Базовый URL API бота **без** суффикса `/v1`. Пример: `https://your-bot.up.railway.app` |
| **NODE_AUTH_TOKEN** | да* | Общий секрет; уходит в `Authorization: Bearer <значение>`. Должен совпадать с приёмником на bot (см. ниже). |

\* Если ни `BACKEND_URL`, ни `NODE_AUTH_TOKEN` не заданы, вызовы не выполняются (лог: `publish.backend.skip`).

**Отключить реальные вызовы:** `BACKEND_USE_MOCK=true` — см. [backend-mock-mode.md](./backend-mock-mode.md).

---

## Согласование с bot (Amanita)

В **bot** эндпоинты `PUT /v1/uploads/.../status` и `POST /v1/uploads/callback` читают секрет так (`_get_edge_secret`):

**Приоритет:** `NODE_AUTH_TOKEN` → `EDGE_TO_BACKEND_SECRET` → `OWN_AUTH_TOKEN` → иначе дефолт только для dev.

Рекомендуемая настройка: задать **одинаковое** значение **`NODE_AUTH_TOKEN`** и на uploader, и на bot.

**Итоговая матрица (один общий секрет `S`):**

| Сервис | Переменная |
|--------|------------|
| arweave-uploader | `NODE_AUTH_TOKEN=S` |
| bot | `NODE_AUTH_TOKEN=S` (или `EDGE_TO_BACKEND_SECRET=S` / `OWN_AUTH_TOKEN=S` для совместимости) |

`BACKEND_URL` на uploader = **origin** вашего FastAPI бота (тот же хост/порт, с которого доступен `/v1/...`).

---

## Код (SSOT)

- Uploader: `dist/publish/backend-calls.js` — `putStatus`, `postCallback`; заголовок `Authorization: Bearer ${NODE_AUTH_TOKEN}`.
- Bot: `bot/api/routes/uploads.py` — `verify_edge_bearer`, `_get_edge_secret()`.

---

## Связанные документы

- [architecture.md](./architecture.md) — общий поток crystalize и env.
- [backend-mock-mode.md](./backend-mock-mode.md) — мок без реального backend.
- [api.md](./api.md) — внешний API uploader для клиента crystalize.
