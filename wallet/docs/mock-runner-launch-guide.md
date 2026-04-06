# Гайд: запуск wallet-mock runner

Постоянный документ для отладки полного floou: **draft → sign_arweave → crystalize → callback → sign_contract → submit**.

**Архитектура и потоки:** [`mock-runner.md`](mock-runner.md) · **Код:** `wallet/mock-runner/` (Node.js ≥18) · **Пример env:** `wallet/mock-runner/.env.example`

---

## 1. Назначение

**Wallet-mock runner** эмулирует клиент с кошельком: опрашивает бота, забирает события подписи, вызывает uploader (crystalize) и снова бота (submit). Без мобильного/web wallet.

---

## 2. Зависимости

| Сервис | Нужен для |
|--------|-----------|
| **Bot** | Очередь, sign-payload, sign-requests, wallet-auth |
| **arweave-uploader** | `POST /v1/crystalize` (если URL неизвестен — частично из ответа sign-payload) |
| **EVM RPC** | Только для реального `sign_contract` (`WALLET_MOCK_RPC_URL`) |

### 2.1 Контракт `POST /v1/crystalize` (отправка из runner)

Первоисточник: **[`arweave-uploader/docs/api.md`](../../arweave-uploader/docs/api.md)** и **[`api.openapi.yaml`](../../arweave-uploader/docs/api.openapi.yaml)**.

| Поле JSON | Назначение |
|-----------|------------|
| `upload_id` | Совпадает с JWT и тегом `Upload-Id` в Data Item |
| `upload_token` | JWT RS256 от бота (`upload_id`, `max_bytes`, `exp`) |
| `signed_data_item` | ANS-104 Data Item, **base64** (Node `Buffer` / uploader декодер; в api.md также указано base64url) |
| `payload_size` | Размер полезной нагрузки в байтах, ≤ `max_bytes` из JWT |

Заголовки: `Content-Type: application/json`. Если на деплое uploader задан **`RELAY_AUTH_TOKEN`**, добавить **`Authorization: Bearer …`**.

После успешной публикации uploader **сам** вызывает bot: **`PUT …/status`**, **`POST …/callback`** — см. [`arweave-uploader/docs/backend-integration.md`](../../arweave-uploader/docs/backend-integration.md). Поток внутри сервиса: [`architecture.md`](../../arweave-uploader/docs/architecture.md) §2.

### 2.2 Оркестратор `run-bullrun-floou.sh` vs ручной `npm start`

По **[`scripts/docs/bullrun-floou-manual.md`](../../scripts/docs/bullrun-floou-manual.md)** §3 дочерний mock-runner получает env из **`scripts/.env` / export родителя**; файл **`wallet/mock-runner/.env` оркестратор не подмешивает**. Для bullrun задавайте **`USER_ID`**, **`BOT_URL`**, **`ARWEAVE_SERVICE_URL`**, режим **`WALLET_MOCK_ARWEAVE_SIGN_MODE`** (по умолчанию в скрипте часто **`local-valid`**) в одном месте со стартом скрипта.

### 2.3 `BOT_URL` для исходящих запросов Node

Не используйте **`http://0.0.0.0:PORT`** как клиентский адрес бота — для **`fetch`** задавайте **`http://127.0.0.1:PORT`** или **`http://localhost:PORT`**. Подробнее: [`wallet/docs/analysis/floou-mock-runner-poll-fetch-failed.md`](analysis/floou-mock-runner-poll-fetch-failed.md).

### 2.4 Режим `poc-jwk` и размер ключа

Uploader и runner ожидают **RSA-2048** (DER SPKI **294** байт). Типичный Arweave-кошелёк **4096** — **crystalize не пройдёт** без доработки uploader. При старте runner логирует **preflight** `poc-jwk preflight: …`, если SPKI не 294. Опечатка в `.env`: **`poc-jw`** нормализуется в **`poc-jwk`** в коде.

---

## 3. Проверка `.env` (частые ошибки)

**Подгрузка:** при `npm start` / `node index.js` читается **`wallet/mock-runner/.env`** (не нужно вручную `source .env`, если файл лежит рядом с `index.js`). Переменные, уже заданные в shell, имеют приоритет над файлом.

1. **`USER_ID`** задан и **совпадает** с `X-User-Id` при draft — иначе очередь пустая (см. §5).
2. **`BOT_URL`** и при необходимости **`ARWEAVE_SERVICE_URL`** — **полный URL с схемой**, например `https://your-bot.up.railway.app`. Значение вида `host.name` **без** `https://` в Node `fetch` даёт неверный запрос.
3. **Режим Arweave:** при **`WALLET_MOCK_ARWEAVE_SIGN_MODE=local-valid`** (дефолт) файл **`WALLET_MOCK_ARWEAVE_PRIVATE_KEY_FILE`** и переменная **`WALLET_MOCK_ARWEAVE_PRIVATE_KEY`** **не используются** — их можно убрать для упрощения. Они нужны только для **`poc-jwk`** / **`env-jwk`**.
4. **`WALLET_MOCK_ADDRESS`** — опционален, если задан **`WALLET_MOCK_PRIVATE_KEY`** (адрес выводится из ключа).
5. Секреты не коммитить; для Railway храните env в панели или локальном `.env` вне git.

---

## 4. Конфигурация: минимум vs полный профиль

### 4.1 Минимум (только poll + `local-valid` crystalize, без своего Arweave JWK)

| Переменная | Значение |
|------------|----------|
| `USER_ID` | строка A (одна на весь POC) |
| `BOT_URL` | `https://…` |
| `WALLET_AUTH_MODE` | `challenge_signature` (если бот требует wallet-auth) |
| `WALLET_MOCK_PRIVATE_KEY` | hex EVM ключа для challenge/submit |

Опционально: `ARWEAVE_SERVICE_URL`, `POLL_INTERVAL_MS`, `WALLET_ALLOW_LEGACY_X_USER_ID`.

### 4.2 Удалённый стек (Railway) + реальный `sign_contract`

Добавьте **`WALLET_MOCK_RPC_URL`** (сеть должна совпадать с `chain_id` у бота). Без RPC реальный submit пропускается (см. логи runner).

### 4.3 Подпись Arweave своим JWK (`poc-jwk`)

| Переменная | Назначение |
|------------|------------|
| `WALLET_MOCK_ARWEAVE_SIGN_MODE` | `poc-jwk` |
| `WALLET_MOCK_ARWEAVE_PRIVATE_KEY` **или** `WALLET_MOCK_ARWEAVE_PRIVATE_KEY_FILE` | JWK; для uploader нужен **RSA-2048** (см. README mock-runner) |

В режиме **`local-valid`** строки JWK **не нужны** — см. §3.

### 4.4 Полная таблица (справочник)

| Переменная | Обяз. | По умолчанию | Описание |
|------------|-------|--------------|----------|
| `USER_ID` | да | — | SSOT с draft и `pending-sign-requests` |
| `BOT_URL` | нет | `http://localhost:8000` | С **https://** для прод/стейдж |
| `POLL_INTERVAL_MS` | нет | `2000` | Интервал опроса (мс) |
| `ARWEAVE_SERVICE_URL` | нет | из sign-payload | Базовый URL uploader |
| `WALLET_AUTH_MODE` | нет | `challenge_signature` | challenge → verify → Bearer |
| `WALLET_ALLOW_LEGACY_X_USER_ID` | нет | `true` | Fallback `X-User-Id` |
| `WALLET_MOCK_PRIVATE_KEY` | для auth + real submit | — | EVM hex |
| `WALLET_MOCK_ADDRESS` | нет | из ключа | Редко нужен отдельно |
| `WALLET_AUTH_SCOPE` | нет | `signing_flow` | Scope challenge |
| `WALLET_MOCK_ARWEAVE_SIGN_MODE` | нет | `local-valid` | `local-valid` / `dummy` / `poc-jwk` |
| `WALLET_MOCK_ARWEAVE_PRIVATE_KEY` | для poc-jwk | — | JWK строкой |
| `WALLET_MOCK_ARWEAVE_PRIVATE_KEY_FILE` | для poc-jwk | — | Путь к JWK |
| `WALLET_MOCK_RPC_URL` | для real sign_contract | — | JSON-RPC |
| `WALLET_MOCK_SIGN_CONTRACT_MODE` | нет | `real` | `real` / `dummy` |
| `WALLET_MOCK_ACTIVITY_TYPE` | нет | `0` | `0` Event / `1` Service |

Перед циклом runner ждёт **`GET ${BOT_URL}/health`** (~30 с таймаут в цикле ожидания).

---

## 5. POC Identity SSOT

| Место | Одно и то же значение строки A |
|-------|----------------------------------|
| `USER_ID` в env runner | A |
| `X-User-Id` при `POST /activities/draft` | A |
| `user_id` в `GET /v1/pending-sign-requests?user_id=` | A |

Bearer для защищённых маршрутов GPT Actions — см. `bot/docs/tech/api/api.md` §3.3. Если `X-User-Id` не передан, бот может подставить `mock_user` — runner с другим `USER_ID` очередь не увидит.

---

## 6. Запуск

### 6.1 Только runner

```bash
cd wallet/mock-runner
# задать USER_ID, BOT_URL (и при необходимости остальное через .env)
npm start
```

Без `USER_ID` процесс завершится с ошибкой.

### 6.2 Локально: три терминала

1. **Bot:** `cd bot && uvicorn api.main:app --reload --host 0.0.0.0 --port 8000`
2. **Uploader:** `cd arweave-uploader && npm start`
3. **Runner:** `cd wallet/mock-runner && npm start`

Затем создайте draft с тем же `X-User-Id`, что `USER_ID`.

---

## 7. Ограничения и отладка

- **`local-valid`:** валидный Data Item и динамический `payload` с бэкенда; ключ подписи — из **фикстуры** uploader, не из вашего JWK. Свой JWK — режим **`poc-jwk`** (WAL-POC-7).
- **Auth:** при `401/403/409` с признаками auth runner обновляет сессию и повторяет запрос.
- **Submit:** real-режим требует баланс gas и корректные `ACTIVITY_REGISTRY` / `chain_id` на стороне бота.
- **Логи:** санитизация в `log-sanitize.mjs` (WAL-POC-5).

---

## 8. Связанные документы

- [`mock-runner.md`](mock-runner.md) — архитектура, mermaid, два домена подписи.
- [`mock-runner/README.md`](../mock-runner/README.md) — детали env и `npm run test:poc-jwk`.
- [`poc-e2e-gpt-wallet-flow-playbook.md`](poc-e2e-gpt-wallet-flow-playbook.md) — pre-flight, triage.

**Версия:** 2.1 · **Дата:** 2026-04-04 — контракт crystalize (api.md), bullrun env, BOT_URL, preflight JWK (WAL-FLOOU-1).
