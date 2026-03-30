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
| **UPLOADER_TO_BACKEND_SECRET** | да* | Общий секрет; уходит в `Authorization: Bearer <значение>`. |
| **EDGE_TO_BACKEND_SECRET** | да* | Альтернативное имя той же переменной; если задано и `UPLOADER_TO_BACKEND_SECRET` нет — используется оно. |

\* Достаточно одного из двух. Если ни `BACKEND_URL`, ни секрет не заданы, вызовы не выполняются (лог: `publish.backend.skip`).

**Отключить реальные вызовы:** `BACKEND_USE_MOCK=true` — см. [backend-mock-mode.md](./backend-mock-mode.md).

---

## Согласование с bot (Amanita)

В **bot** эндпоинты `PUT /v1/uploads/.../status` и `POST /v1/uploads/callback` читают секрет так:

**Приоритет:** `EDGE_TO_BACKEND_SECRET` → при отсутствии → **`OWN_AUTH_TOKEN`** → иначе дефолт только для dev.

Значит:

- Если в `.env` бота задаёте **только** `OWN_AUTH_TOKEN` (как в `bot/.env.example`), на uploader должно быть **то же строковое значение** в `UPLOADER_TO_BACKEND_SECRET` или `EDGE_TO_BACKEND_SECRET`.
- Либо на боте явно задайте `EDGE_TO_BACKEND_SECRET` тем же значением, что на uploader — оба варианта эквивалентны приёмщику.

**Итоговая матрица (один общий секрет `S`):**

| Сервис | Переменная |
|--------|------------|
| arweave-uploader | `UPLOADER_TO_BACKEND_SECRET=S` или `EDGE_TO_BACKEND_SECRET=S` |
| bot | `EDGE_TO_BACKEND_SECRET=S` **или** `OWN_AUTH_TOKEN=S` |

`BACKEND_URL` на uploader = **origin** вашего FastAPI бота (тот же хост/порт, с которого доступен `/v1/...`).

---

## Код (SSOT)

- Uploader: `dist/publish/backend-calls.js` — `putStatus`, `postCallback`; заголовок `Authorization: Bearer ${secret}`.
- Bot: `bot/api/routes/uploads.py` — `verify_edge_bearer`, `_get_edge_secret()`.

---

## Связанные документы

- [architecture.md](./architecture.md) — общий поток crystalize и env.
- [backend-mock-mode.md](./backend-mock-mode.md) — мок без реального backend.
- [api.md](./api.md) — внешний API uploader для клиента crystalize.
