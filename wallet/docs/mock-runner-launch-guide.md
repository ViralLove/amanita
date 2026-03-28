# Гайд: запуск wallet-mock runner для отладки процесса загрузки

Постоянный документ по запуску приложения-заглушки Wallet на localhost для отладки полного floou загрузки и подписания (draft → sign_arweave → crystalize → callback → sign_contract → submit).

---

## 1. Назначение

**Wallet-mock runner** — приложение в репозитории `wallet`, которое эмулирует клиент с кошельком: опрашивает бота на предмет событий «требуется подпись», запрашивает данные для подписи и отправляет результат в arweave-uploader (sign_arweave) или в бота (sign_contract). Используется для:

- отладки процесса загрузки Activity без реального мобильного/веб-приложения;
- проверки цепочки: бот → пуш → runner забирает событие → sign-payload/sign-request → crystalize/submit;
- подготовки к E2E-тестам полного floou (W7).

Код: `wallet/mock-runner/` (Node.js ≥18).

---

## 2. Зависимости

Перед запуском runner должны быть доступны:

| Сервис | Назначение |
|--------|------------|
| **Bot** (W1–W5) | GET /v1/pending-sign-requests (события), GET /v1/uploads/{id}/sign-payload, GET/POST /v1/sign-requests/{id}. |
| **arweave-uploader** (опционально) | POST /v1/crystalize для sign_arweave; если URL не задан или сервис недоступен, runner логирует и продолжает цикл. |

---

## 3. Конфигурация (env)

Задаётся переменными окружения:

| Переменная | Обязательно | По умолчанию | Описание |
|------------|-------------|--------------|----------|
| `USER_ID` | да | — | Идентификатор пользователя; должен совпадать с X-User-Id при создании draft. |
| `BOT_URL` | нет | `http://localhost:8000` | Базовый URL API бота. |
| `POLL_INTERVAL_MS` | нет | `2000` | Интервал опроса pending-sign-requests (мс). |
| `ARWEAVE_SERVICE_URL` | нет | из ответа sign-payload | URL arweave-uploader; если не задан, берётся из поля `arweave_uploader_url` ответа sign-payload. |
| `WALLET_AUTH_MODE` | нет | `challenge_signature` | Режим wallet->bot auth. В этом режиме runner использует `POST /v1/wallet-auth/challenge` и `POST /v1/wallet-auth/verify`, затем отправляет `Authorization: Bearer ...`. |
| `WALLET_ALLOW_LEGACY_X_USER_ID` | нет | `true` | Разрешить fallback заголовка `X-User-Id` для localhost/transition режима. |
| `WALLET_MOCK_PRIVATE_KEY` | для strict auth | — | Приватный EVM ключ для подписи `canonical_message`. |
| `WALLET_MOCK_ADDRESS` | нет | из ключа | Явный wallet address (если нужно). |
| `WALLET_AUTH_SCOPE` | нет | `signing_flow` | Scope, отправляемый в challenge endpoint. |

**Поведение при старте:** перед циклом опроса `pending-sign-requests` runner выполняет ожидание **`GET ${BOT_URL}/health`** (до ~30 с). Это снижает шум при параллельном запуске с `uvicorn` и оркестраторами вроде `run-bullrun-floou.sh`.

Пример `.env` в `wallet/mock-runner/` (не коммитить секреты):

```bash
USER_ID=test-user-123
BOT_URL=http://localhost:8000
POLL_INTERVAL_MS=2000
WALLET_AUTH_MODE=challenge_signature
WALLET_ALLOW_LEGACY_X_USER_ID=true
# WALLET_MOCK_PRIVATE_KEY=0x...
# ARWEAVE_SERVICE_URL=http://localhost:3000
```

---

## 4. Запуск

### 4.1 Только runner

```bash
cd wallet/mock-runner
export USER_ID=your-test-user-id
export BOT_URL=http://localhost:8000   # если бот не на 8000
npm start
# или
node index.js
```

Без `USER_ID` процесс завершится с ошибкой. Runner выводит в консоль старт, опросы и обработанные события.

### 4.2 Полный сценарий для отладки загрузки (три терминала + запросы)

1. **Терминал 1 — Bot**
   ```bash
   cd bot
   uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
   ```

2. **Терминал 2 — arweave-uploader** (если нужен crystalize)
   ```bash
   cd arweave-uploader
   npm start
   # порт по конфигу (например 3000)
   ```

3. **Терминал 3 — Wallet-mock runner**
   ```bash
   cd wallet/mock-runner
   export USER_ID=deployer   # или тот user_id, с которым будете создавать draft
   export BOT_URL=http://localhost:8000
   npm start
   ```

4. **Терминал 4 (или Postman/curl) — создание draft и проверка**
   - Создать draft с заголовком `X-User-Id: deployer` (то же значение, что `USER_ID` у runner).
   - В логах runner должно появиться событие `sign_arweave` и вызов GET sign-payload, затем POST crystalize (если uploader поднят).
   - Эмулировать callback от uploader на бота (POST /v1/uploads/callback с upload_id, bundle_tx_id и т.д.).
   - В логах runner — событие `sign_contract` и вызов GET sign-request, POST submit.

Таким образом можно пошагово отлаживать: опрос событий, получение sign-payload/sign-request, вызовы crystalize и submit.

---

## 5. Ограничения и отладка

- **Crystalize:** Runner отправляет в crystalize заглушку подписи Data Item. Реальный uploader вернёт 400 `signature_invalid`. Для полного прохода до ответа 200 нужен валидный подписанный Data Item (тестовый ключ + формат ANS-104) или специальный режим uploader.
- **Auth:** В `challenge_signature` runner автоматически refresh-ит токен при auth ошибках (`401/403/409`) и повторяет запрос один раз.
- **Submit:** Отправка submit с заглушкой `signedTransaction` принимается ботом (200); для реального вызова контракта нужна настоящая подпись (W8).
- При ошибках сети или 4xx/5xx от бота/uploader runner логирует и продолжает цикл опроса; процесс не завершается.

---

## 6. Связанные документы

- Описание модуля и контракта с ботом: `wallet/mock-runner/README.md`.
- Краткая ссылка в docs: `wallet/docs/mock-runner.md`.
- Таск постановки: `wallet/docs/analysis/tasks/task-implement-wallet-mock-runner-localhost/`.
