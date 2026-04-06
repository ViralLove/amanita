# AMANITA Bot API

REST-слой на **FastAPI** в каталоге `bot/api/`. Полная матрица маршрутов и auth — **`bot/docs/tech/api/api.md`** (SSOT). Оглавление всех материалов по API — **`bot/docs/tech/api/README.md`**. Интерактивные схемы: **`GET /docs`**, **`GET /openapi.json`**.

---

## Запуск (из каталога `bot/`)

```bash
python3 -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

Проверка:

```bash
curl -s http://127.0.0.1:8000/health
open http://127.0.0.1:8000/docs
```

Точка входа в коде: `create_api_app()` в `api/main.py`.

---

## Зоны аутентификации (конспект)

| Зона | Префиксы | Что нужно клиенту |
|------|-----------|-------------------|
| Commerce / каталог | `/api-keys`, `/products`, `/media`, `/description` | **HMAC** (`X-API-Key`, `X-Timestamp`, `X-Nonce`, `X-Signature`) |
| Activities / reference | `/activities`, `/reference` | HMAC **не** требуется; при **`GPT_ACTIONS_BEARER_SECRET`** — **`Authorization: Bearer`** с тем же значением |
| Uploads / подписи (floou, mock-wallet) | `/v1/uploads`, `/v1/sign-requests`, `/v1/pending-sign-requests` | Свои правила (Bearer edge, кошелёк и т.д.) — см. `api.md` §2.7–§3.2 |
| Wallet auth | `/v1/wallet-auth` | HMAC **не** снят в `skip_prefixes` — нужны заголовки HMAC, если не менять код |

Публично без HMAC (точные пути): `/`, `/hello`, `/health`, `/health/detailed`, `/docs`, `/redoc`, `/openapi.json`.

Подробности: **`bot/docs/tech/api/api.md`** (§3 — middleware, §4 — env).

---

## Переменные окружения (черновик)

Полный список и значения по умолчанию — в **`api/config.py`** и **`bot/.env.example`**.

Обязательно иметь в виду для интеграций:

- HMAC: `AMANITA_API_HMAC_SECRET_KEY`, окно времени и nonce — см. `.env.example`.
- Custom GPT Actions (опционально): **`GPT_ACTIONS_BEARER_SECRET`** — пусто = проверка Bearer выключена.
- Edge → backend (uploads): **`NODE_AUTH_TOKEN`** (или fallback `EDGE_TO_BACKEND_SECRET` / `OWN_AUTH_TOKEN` в `uploads.py`) — не смешивать с секретом GPT.

---

## Дополнительные материалы

См. **`bot/docs/tech/api/README.md`**: commerce-поток, HMAC/архитектура, требования WordPress, логирование. Вертикаль Activities (оркестратор `ActivityRegistryService`): **`bot/services/application/activity/`** — строка в оглавлении `bot/docs/tech/api/README.md`. Устаревший каталог `bot/api/docs/` не используется.

---

## Тесты

```bash
cd bot
python3 -m pytest tests/api/ tests/unit/test_gpt_actions_bearer_middleware.py -q
```

Аудит и практики по тестам API: `tests/api/README.md`.

---

## Блокчейн-адреса и прод

Контракты и RPC не хардкодятся в этом README: берите из деплоя и конфигурации узла (`ServiceFactory`, env, сеть).
