# E2E Full Floou: мануал по запуску теста и всех элементов системы

**Постоянная документация:** `bot/docs/tests/e2e-floou-manual.md`  
**Файл теста:** `bot/tests/integration/test_activity_full_floou_mock_wallet.py`  
**Маркеры:** `full_floou_mock_wallet` (in-process), `full_floou_real_services` (E2E с реальными сервисами)

---

## 1. Назначение

Сквозной тест полного floou загрузки и подписания Activity:

**draft** → **sign_arweave** (GET sign-payload → crystalize) → **callback** (uploader → Backend) → **sign_contract** (GET sign-request → POST submit) → проверка store (submitted, tx_hash).

Два варианта:

| Вариант | Маркер | Описание |
|--------|--------|----------|
| **In-process** | `full_floou_mock_wallet` | Тест сам выполняет все шаги в одном процессе (моки prepare/upload/blockchain). Не требует Node, arweave-uploader, JWT. Подходит для CI. |
| **E2E real services** | `full_floou_real_services` | Bot поднимается в потоке, **arweave-uploader** и **wallet-mock** — отдельные процессы. Требует Node, каталог arweave-uploader, пару JWT-ключей. Использует все локально задеплоенные элементы. |

Ниже — инструкции по запуску **E2E с реальными сервисами** и по ручному запуску всех элементов (для отладки).

---

## 2. Что нужно для E2E (`full_floou_real_services`)

- **Node.js** (≥18) — для arweave-uploader, wallet-mock и скрипта `build-full-cycle-data-item.js`.
- **Каталог arweave-uploader** — рядом с `bot` в репо или `ARWEAVE_UPLOADER_DIR`; собранный `dist/server.js`.
- **Пара JWT-ключей** (RS256) для upload token: приватный ключ для бота (подпись токена при prepare), публичный для uploader (проверка при crystalize). Одна и та же пара в обоих сервисах.

Если чего-то не хватает, тест будет **пропущен** (skip) с указанием причины.

---

## 3. Переменные окружения по компонентам

### 3.1 Bot (backend)

Запуск вручную: `uvicorn api.main:app --host 0.0.0.0 --port 8000` (порт по умолчанию — 8000).

| Переменная | Обязательно | По умолчанию | Описание |
|------------|-------------|--------------|----------|
| `EDGE_TO_BACKEND_SECRET` | для callback | — | Секрет для Bearer при вызовах uploader → Backend (PUT status, POST callback). Должен совпадать с секретом в uploader. |
| `UPLOAD_TOKEN_JWT_PRIVATE_KEY` или `UPLOAD_TOKEN_JWT_PRIVATE_KEY_FILE` | для E2E | — | Приватный ключ RS256 для подписи upload_token (prepare). Для E2E теста — обязательны. |

Остальные переменные (Supabase и т.д.) в E2E тесте не используются (моки). Для ручного запуска бота с реальной БД см. основную документацию.

### 3.2 arweave-uploader

Запуск: из каталога `arweave-uploader` выполнить `npm start` (порт по умолчанию — **3000**, задаётся через `PORT`).

| Переменная | Обязательно | По умолчанию | Описание |
|------------|-------------|--------------|----------|
| `PORT` | нет | `3000` | Порт, на котором слушает uploader (POST /v1/crystalize). |
| `BACKEND_URL` | да (для callback) | — | Базовый URL бота, например `http://localhost:8000`. Uploader вызывает PUT `/v1/uploads/{id}/status` и POST `/v1/uploads/callback`. |
| `EDGE_TO_BACKEND_SECRET` или `UPLOADER_TO_BACKEND_SECRET` | да (для callback) | — | Bearer-токен для вызовов к Backend. То же значение, что `EDGE_TO_BACKEND_SECRET` в боте. |
| `UPLOAD_TOKEN_JWT_PUBLIC_KEY` или `UPLOAD_TOKEN_JWT_PUBLIC_KEY_FILE` | да (для crystalize) | — | Публичный ключ RS256 для проверки JWT при POST /v1/crystalize. Пара к приватному ключу бота. |
| `ARWEAVE_PRIVATE_KEY_FILE` или `ARWEAVE_PRIVATE_KEY` | для старта сервера | — | Ключ Arweave (можно тестовый JWK). |
| `USE_REAL_ARWEAVE` | нет | — | `false` — мок публикации (200 с mock bundle_tx_id); не ходит в сеть Arweave. |

Подробнее: `arweave-uploader/docs/local-run-and-smoke.md`, `arweave-uploader/docs/api.md`.

### 3.3 wallet-mock runner

Запуск: из каталога `wallet/mock-runner` выполнить `node index.js` (или `npm start`).

| Переменная | Обязательно | По умолчанию | Описание |
|------------|-------------|--------------|----------|
| `USER_ID` | да | — | Идентификатор пользователя; должен совпадать с `X-User-Id` при создании draft. При реальной БД (Supabase) таблица `uploads.user_id` имеет тип UUID — задайте валидный UUID (например `00000000-0000-0000-0000-000000000001`). |
| `BOT_URL` | нет | `http://localhost:8000` | Базовый URL API бота. |
| `POLL_INTERVAL_MS` | нет | `2000` | Интервал опроса GET /v1/pending-sign-requests (мс). |
| `ARWEAVE_SERVICE_URL` | для sign_arweave | из sign-payload | URL arweave-uploader для POST crystalize. Для E2E теста (sign_contract только) не обязателен. |
| `WALLET_MOCK_ARWEAVE_SIGN_MODE` | нет | `dummy` | Режим подписи Data Item: `dummy` — заглушка (uploader вернёт 400 signature_invalid); **`local-valid`** — реальный ANS‑104 Data Item через `arweave-uploader/tests/fixtures/valid-data-item.js` (полный floou до callback и sign_contract). Только для localhost. |
| `ARWEAVE_UPLOADER_PATH` | для local-valid | `../../arweave-uploader` от mock-runner | Путь к каталогу arweave-uploader (для загрузки valid-data-item.js). При запуске из скрипта из корня репо — по умолчанию подходит. |
| `WALLET_AUTH_MODE` | нет | `challenge_signature` | Режим wallet->bot auth для signing endpoints. |
| `WALLET_ALLOW_LEGACY_X_USER_ID` | нет | `true` | Разрешает fallback `X-User-Id` в localhost/transition режиме. |
| `WALLET_MOCK_PRIVATE_KEY` | для strict auth | — | Приватный EVM ключ для challenge/signature handshake. |

Подробнее: `wallet/docs/mock-runner-launch-guide.md`.

---

## 4. Порты (сводка)

| Компонент | Порт по умолчанию | Переменная |
|-----------|-------------------|------------|
| **Bot** | 8000 | при запуске: `--port 8000` |
| **arweave-uploader** | 3000 | `PORT` |
| **wallet-mock** | не слушает порт (клиент) | — |

При ручном запуске всех трёх элементов задайте в uploader `BACKEND_URL=http://localhost:8000` (или тот порт, на котором реально слушает бот), в wallet-mock — `BOT_URL=http://localhost:8000` и при необходимости `ARWEAVE_SERVICE_URL=http://localhost:3000`.

В **E2E тесте** порты выбираются автоматически (свободные сокеты); тест передаёт в subprocess нужные `BACKEND_URL`, `PORT`, `BOT_URL`.

---

## 5. Запуск E2E теста (автоматический старт сервисов)

Тест сам поднимает bot в потоке, arweave-uploader и wallet-mock в виде subprocess. Достаточно задать окружение и запустить pytest.

Из папки **bot**:

```bash
cd bot

# Переменные (можно в .env): JWT-ключи и секрет для callback
export EDGE_TO_BACKEND_SECRET=mock-edge-to-backend-secret
export UPLOAD_TOKEN_JWT_PRIVATE_KEY_FILE=../keys/private.pem
export UPLOAD_TOKEN_JWT_PUBLIC_KEY_FILE=../keys/public.pem

# Опционально: каталог arweave-uploader, если не рядом с bot
# export ARWEAVE_UPLOADER_DIR=/path/to/arweave-uploader

python3 -m pytest tests/integration/test_activity_full_floou_mock_wallet.py -m full_floou_real_services -v
```

Если Node или arweave-uploader или JWT не настроены, тест будет **пропущен** с сообщением вида:  
`Для E2E задайте UPLOAD_TOKEN_JWT_PUBLIC_KEY или ... (uploader)`.

---

## 6. Bullrun: скрипт «всё в одном» (репо)

Из **корня репозитория** можно запустить все сервисы и вызов точки входа одним скриптом **`scripts/shell/run-bullrun-floou.sh`** (bullrun floou; обёртка `scripts/run-bullrun-floou.sh`):

```bash
./scripts/shell/run-bullrun-floou.sh
```

Скрипт:

- Экспортирует переменные **URL и портов**: `BOT_URL`, `ARWEAVE_SERVICE_URL`, `USER_ID`, `EDGE_TO_BACKEND_SECRET`, `PORT`, `BACKEND_URL` (остальное из `.env` каждого проекта).
- Поднимает **Bot**, **arweave-uploader**, **wallet-mock** в фоне.
- Ждёт готовности Bot и Uploader (`/health`).
- Вызывает **точку входа** `POST /activities/draft` (имитация входа из Custom GPT), заголовок `X-User-Id`, тело с `activity_type`, `title`, `short_summary`.
- Ждёт обработки **двух подписей** кошелька (wallet-mock опрашивает pending-sign-requests; оркестратор ждёт маркерный файл после успешного submit).
- Выводит **итог загрузки**: ответ draft, затем `GET /activities/{activity_id}` и краткую сводку.

**Предполагается:** блокчейн-нода уже запущена с задеплоенными контрактами. Остановка: Ctrl+C (скрипт завершит все три процесса).

**Протокол прогона (артефакт):** при каждом завершении `scripts/shell/run-bullrun-floou.sh` (успех, ошибка или код **130** при прерывании) в каталоге `scripts/logs/` создаётся **один** текстовый файл с именем по шаблону `{S1}.{S2}.{S3}.{S4}.{S5}.{S6}-{ddMMyyyyHHmm}.txt` — шесть целочисленных сегментов через точку и двенадцатизначная метка **локального** времени (день, месяц, год, час, минута). В файле: метаданные, хронология шагов оркестратора и полные stdout/stderr процессов Bot, arweave-uploader и wallet-mock. Запись в файл отключить: `FLOOU_LOG_DISABLE=true`. Подробности — `scripts/docs/analysis/tasks/task-implement-run-full-floou-structured-log-artifact/decision-points-run-full-floou-structured-log.md`.

Переопределение портов и пользователя:

```bash
BOT_PORT=8000 UPLOADER_PORT=3000 USER_ID=my-user ./scripts/shell/run-bullrun-floou.sh
```

---

## 7. Ручной запуск всех элементов (для отладки)

Удобно для пошаговой отладки без pytest: поднять сервисы вручную, затем создавать draft и смотреть логи.

### Терминал 1 — Bot

```bash
cd bot
export EDGE_TO_BACKEND_SECRET=your-shared-secret
export UPLOAD_TOKEN_JWT_PRIVATE_KEY_FILE=../keys/private.pem
# при необходимости: SUPABASE_*, и т.д.
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

### Терминал 2 — arweave-uploader

```bash
cd arweave-uploader
export PORT=3000
export BACKEND_URL=http://localhost:8000
export EDGE_TO_BACKEND_SECRET=your-shared-secret
export UPLOAD_TOKEN_JWT_PUBLIC_KEY_FILE=../keys/public.pem
export ARWEAVE_PRIVATE_KEY_FILE=tests/fixtures/minimal-jwk.json
export USE_REAL_ARWEAVE=false
npm start
```

### Терминал 3 — wallet-mock runner

```bash
cd wallet/mock-runner
export USER_ID=test-user-123
export BOT_URL=http://localhost:8000
export ARWEAVE_SERVICE_URL=http://localhost:3000
export POLL_INTERVAL_MS=2000
export WALLET_AUTH_MODE=challenge_signature
export WALLET_ALLOW_LEGACY_X_USER_ID=true
# export WALLET_MOCK_PRIVATE_KEY=0x...
node index.js
```

### Создание draft (curl или Postman)

```bash
curl -X POST http://localhost:8000/activities/draft \
  -H "Content-Type: application/json" \
  -H "X-User-Id: test-user-123" \
  -d '{"activity_type":"event","title":"Test","short_summary":"Summary"}'
```

Дальше runner подхватит события sign_arweave и sign_contract (после callback).  
**Важно:** wallet-mock при sign_arweave отправляет заглушку подписи; реальный uploader вернёт 400 `signature_invalid`. Для полного прохода crystalize нужен валидный Data Item (например, скрипт `arweave-uploader/scripts/build-full-cycle-data-item.js` или E2E тест).

---

## 8. Запуск in-process теста (без внешних сервисов)

Не требует Node, arweave-uploader, JWT. Подходит для CI.

```bash
cd bot
python3 -m pytest tests/integration/test_activity_full_floou_mock_wallet.py -m full_floou_mock_wallet -v
```

---

## 9. Причины skip E2E и что проверить

| Сообщение skip | Что сделать |
|----------------|-------------|
| Node.js не найден | Установить Node.js ≥18, убедиться, что `node` в PATH. |
| ARWEAVE_UPLOADER_DIR или каталог arweave-uploader не найден | Положить `arweave-uploader` рядом с `bot` в репо или задать `ARWEAVE_UPLOADER_DIR`. |
| dist/server.js не найден | В каталоге arweave-uploader выполнить сборку (например `npm run build` или скопировать dist из репо). |
| Для E2E задайте UPLOAD_TOKEN_JWT_PRIVATE_KEY... (bot) | Задать в env (или в `bot/.env`) приватный ключ: `UPLOAD_TOKEN_JWT_PRIVATE_KEY` или `UPLOAD_TOKEN_JWT_PRIVATE_KEY_FILE`. |
| Для E2E задайте UPLOAD_TOKEN_JWT_PUBLIC_KEY... (uploader) | Задать в env публичный ключ (тест передаёт os.environ в subprocess uploader): `UPLOAD_TOKEN_JWT_PUBLIC_KEY` или `UPLOAD_TOKEN_JWT_PUBLIC_KEY_FILE`. |

Проверка ключей: одна пара RS256; приватный — для бота (подпись), публичный — для uploader (проверка). См. также `arweave-uploader/docs/local-run-and-smoke.md`.

---

## 10. Связанные документы

| Документ | Описание |
|----------|----------|
| **`scripts/shell/run-bullrun-floou.sh`** (bullrun, из корня репо) | Скрипт: export URL/портов, старт bot + uploader + wallet-mock, curl draft, ожидание двух подписей, итог. |
| [`bot/docs/analysis/tasks/task-tests-full-flow-signing-mock-wallet-localhost.md`](../analysis/tasks/task-tests-full-flow-signing-mock-wallet-localhost.md) | Таск и критерии приёмки. |
| [`bot/docs/analysis/tasks/.../e2e-real-services-design.md`](../analysis/tasks/task-tests-full-flow-signing-mock-wallet-localhost/e2e-real-services-design.md) | Дизайн E2E: поток, верификация, ограничение wallet-mock. |
| [`wallet/docs/mock-runner-launch-guide.md`](../../../wallet/docs/mock-runner-launch-guide.md) | Запуск wallet-mock, переменные, сценарий отладки. |
| [`arweave-uploader/docs/local-run-and-smoke.md`](../../../arweave-uploader/docs/local-run-and-smoke.md) | Локальный запуск uploader, JWT, smoke crystalize. |
| [`arweave-uploader/docs/api.md`](../../../arweave-uploader/docs/api.md) | API uploader (POST /v1/crystalize и др.). |
| [`bot/docs/tests/data-upload-integration-tests.md`](./data-upload-integration-tests.md) | Интеграционные тесты upload flow (Supabase, контракты API). |

---

**Версия:** v1.0, 2026-01-29.
