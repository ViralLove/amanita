# POC E2E Playbook: Custom GPT → бот → uploader → кошелёк (mock-runner)

**Ключ таска:** WAL-POC-6 · **Слой:** L4 · **Методология:** `@.cursor/commands/run-analysis.md` (верификация по чекпоинтам ниже).

**Назначение:** один воспроизводимый сценарий приёмки и triage без «застревания на кошельке»: на каждом шаге — **вход**, **ожидаемый результат**, **где смотреть подтверждение** (логи runner, HTTP, при необходимости бот/uploader).

**Связанные документы:** [`mock-runner-launch-guide.md`](mock-runner-launch-guide.md) (детальный запуск), [`mock-runner/README.md`](../mock-runner/README.md), [`bot/docs/tech/api/api.md`](../../bot/docs/tech/api/api.md). Оркестратор полного floou: `scripts/shell/run-bullrun-floou.sh`.

**Версия документа:** 1.1 · **Дата:** 2026-04-02

---

## Чекпоинты процесса (run-analysis)

| Этап | Содержание | Критерий «готово» |
|------|------------|-------------------|
| **1. Pre-flight** | Health бота, согласованный `USER_ID`, bearer для Actions, uploader при необходимости | Таблица §1 без красных флагов |
| **2. Run** | Создание draft → очередь → runner обрабатывает `sign_arweave` и `sign_contract` | Маркеры логов §2 появляются по порядку |
| **3. Verify** | Сверка артефактов §5 | Заполнен чеклист или зафиксирован обходной сценарий |
| **4. Triage при сбое** | §3 | Выбрана строка таблицы, выполнено действие |

Полное закрытие таска по методологии включает **верификацию AC** в постановке и при необходимости запись в `acceptance-verification-WAL-POC-6.md` (папка таска).

---

## 1. Pre-flight (precheck)

Выполните до «реального» шага в GPT/curl.

| # | Проверка | Как | Ожидание |
|---|----------|-----|----------|
| 1.1 | Бот поднят | `curl -sS -o /dev/null -w "%{http_code}" "${BOT_URL:-http://localhost:8000}/health"` | `200` |
| 1.2 | Один `user_id` на весь путь | Сравнить: `USER_ID` runner, `X-User-Id` при draft, query `pending-sign-requests` | Три строки **совпадают** (SSOT §3.1 launch-guide) |
| 1.3 | GPT Actions / draft с Bearer | Если на боте задан секрет Actions — заголовок `Authorization: Bearer <секрет>` на защищённые маршруты | Нет **401** до этапа кошелька |
| 1.4 | arweave-uploader (для crystalize) | Сервис слушает URL из `ARWEAVE_SERVICE_URL` или из `sign-payload.arweave_uploader_url` | `POST /v1/crystalize` достижим с runner |
| 1.5 | mock-runner env | `wallet/mock-runner/.env.example` + `WALLET_MOCK_PRIVATE_KEY` если нужны challenge и EVM submit | См. README runner |
| 1.6 | Railway web wallet (опционально, WAL-POC-4) | HTTPS URL из деплоя | Только для ручного UX; **не** обязателен для цепочки mock-runner |

**Лог чекпоинта:** записать `BOT_URL`, выбранный `USER_ID`, флаг «uploader OK / skip».

---

## 2. Основной сценарий (run) и маркеры в логах runner

Цепочка: **draft → sign_arweave → crystalize → callback → sign_contract → submit**.

Порядок событий в логах может смещаться по времени; **первый** обработанный тип зависит от пуша бота. Ниже — типичный happy-path и строки **`msg`** из `wallet/mock-runner/index.js` (первый аргумент `log()`).

| Шаг | Действие | Ожидаемый результат | Маркер(ы) в консоли runner |
|-----|----------|---------------------|----------------------------|
| 2.1 | Старт runner | Ожидание `/health`, затем цикл опроса | `bot health ok` **или** `bot health wait timeout...`; затем `wallet-mock-runner start` с конфигом |
| 2.2 | Wallet-auth (если `challenge_signature` + ключ) | Сессия с Bearer | `wallet auth verified` с `signerAddress` |
| 2.3 | Создание draft/upload (вне runner: GPT/curl) | Появляется работа для пользователя A | — |
| 2.4 | Бот кладёт `sign_arweave` в очередь | Runner забирает событие | `events received` с `count` ≥ 1; затем `handleSignArweave` с `requestId` (= `upload_id`) |
| 2.5 | sign-payload + crystalize | 2xx от uploader при валидной подписи | `crystalize ok` (объект с `bundle_tx_id` при успехе) **или** `crystalize error` (тело санитизировано, WAL-POC-5) |
| 2.6 | Callback uploader → бот | Бот создаёт `sign_request`, пуш `sign_contract` | После callback в логах бота (не runner) — переход к следующему событию |
| 2.7 | `sign_contract` | Runner вызывает GET sign-request, POST submit | `handleSignContract`; затем `sign_contract: signed createActivity tx` **или** dummy; затем **`submit ok`** с `tx_hash` при успехе |
| 2.8 | Оркестратор (опционально) | Файл-маркер floou | `FLOOU_DONE_MARKER_FILE` — строка JSON без секретов |

**Poll без событий:** отсутствие `events received` при активном сценарии → сначала проверить **1.2** и очередь:  
`curl -sS "${BOT_URL}/v1/pending-sign-requests?user_id=${USER_ID}"`.

---

## 3. Triage: симптом → причина → проверка → действие

| Симптом | Вероятная причина | Где проверить | Действие |
|---------|-------------------|---------------|----------|
| **401** на `/activities` / draft | Неверный или отсутствующий Bearer Actions | `bot/.env`, `api.md` §3.3 | Выставить тот же секрет, что в боте |
| Очередь **пустая**, runner молчит | Несовпадение `USER_ID` и `X-User-Id` draft | Query pending вручную | Выровнять строку A на всём пути (WAL-POC-1) |
| **`wallet auth refresh failed`** | Неверная подпись challenge или ключ | Лог `errorCode`, ключ и `USER_ID` | Проверить `WALLET_MOCK_PRIVATE_KEY`, scope |
| **`ARWEAVE_SERVICE_URL ... missing`** | Нет URL uploader в env и в sign-payload | Ответ sign-payload | Задать `ARWEAVE_SERVICE_URL` или поле в боте |
| **`crystalize error`** / 401 uploader | JWT / токен upload не принят | Логи uploader, ключи JWT бот↔uploader | Сверить env uploader и бота |
| **`signature_invalid`** (тело/лог uploader) | Режим `dummy` Arweave | `WALLET_MOCK_ARWEAVE_SIGN_MODE` | Переключить на `local-valid` (WAL-POC-2) или **`poc-jwk`** с RSA-2048 JWK (WAL-POC-7) |
| **`poc-jwk: createSignedDataItemFromJwk failed`** с текстом про 4096-bit | Ключ Arweave не RSA-2048 | Формат JWK | Для текущего uploader нужен **2048-bit** SPKI; иначе оставить `local-valid` |
| **`createValidDataItem failed`** | Путь к фикстуре / `ARWEAVE_UPLOADER_PATH` | Файловая система | Проверить `ARWEAVE_UPLOADER_PATH` |
| **Нет `sign_contract`** после crystalize | Callback не дошёл до бота | Логи бота `POST /uploads/callback` | Повторить callback; см. launch-guide §4 |
| **`sign_contract: skip`** (нет ключа/RPC) | Нет `WALLET_MOCK_PRIVATE_KEY` или `WALLET_MOCK_RPC_URL` | env runner | Задать или `WALLET_MOCK_SIGN_CONTRACT_MODE=dummy` для stub |
| **`submit exception`** | Невалидная tx, сеть, ACL контракта | `message` в логе (без секретов) | Проверить `CHAIN_ID`, баланс gas, адрес ActivityRegistry |
| **`poll error`** / HTTP на pending | Бот недоступен или 403 | `curl /health`, auth заголовки | Восстановить бот и токен |

---

## 4. Артефакты успешного прогона (зафиксировать вручную)

Минимальный набор для повторяемости и отладки:

| Артефакт | Пример / источник |
|----------|-------------------|
| `user_id` | Та же строка, что везде |
| `upload_id` | Из draft / события `sign_arweave` |
| `bundle_tx_id` | Из ответа crystalize / лога `crystalize ok` |
| `sign_request_id` | UUID из ветки `sign_contract` / лога `submit ok` |
| `tx_hash` | Из ответа `POST .../submit` (может быть mock на localhost) |
| Время | ISO отметки начала/конца прогона |
| Версии | Коммит репозитория, `BOT_URL`, режимы env runner |

**Шаблон записи прогона (P1 таска — заполняет оператор после реального run):**

```
Дата: 
Оператор: 
Результат: success / partial / fail
upload_id: 
sign_request_id: 
bundle_tx_id: 
tx_hash: 
Заметки:
```

---

## 5. Команды проверки (относительные пути)

```bash
# Health
curl -sS -i "${BOT_URL:-http://localhost:8000}/health"

# Очередь (подставьте USER_ID)
curl -sS -i "${BOT_URL:-http://localhost:8000}/v1/pending-sign-requests?user_id=${USER_ID}"

# Runner
cd wallet/mock-runner
USER_ID="<POC_USER_ID>" npm start
```

Полуавтоматический floou: из корня репозитория при необходимости `scripts/shell/run-bullrun-floou.sh` (см. комментарии в скрипте и `scripts/docs/...` при наличии).

---

## 6. Риски и самопроверка (кратко)

- Несколько разных Bearer (Actions vs wallet JWT) — не смешивать в одном заголовке без понимания маршрута.
- **Частичный успех:** HTTP 200 на submit при `dummy` или localhost stub — не равен валидному ончейн-эффекту; сверять WAL-POC-3 и профиль blockchain.
- Асинхронность: callback позже poll-интервала — увеличить ожидание или `POLL_INTERVAL_MS`, не считать сразу «зависло».

**Самопроверка AC WAL-POC-6 (черновик):**

- [x] Единый документ: precheck → run → verify/triage.
- [x] У шагов §2 указаны входы, ожидания, маркеры логов.
- [x] Таблица triage §3.
- [x] Набор артефактов §4.
- [ ] Один полевой прогон с заполненным §4 — **вне агента**, оператор.

---

## 7. Ретроспектива (шаблон)

| Вопрос | Ответ |
|--------|--------|
| Где потеряли больше всего времени? | |
| Какой симптом из §3 оказался актуальным? | |
| Что обновить в playbook после прогона? | |
| Готовность к коммиту документации: да/нет | |

---

*Конец playbook.*
