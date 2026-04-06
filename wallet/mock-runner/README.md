# Wallet-mock runner (W6)

Приложение для localhost, эмулирующее Wallet в сценарии подписания: получает события от бота (sign_arweave, sign_contract), запрашивает данные для подписи и отправляет результат в arweave-uploader или в бота (submit).

## Зависимости

- **Bot** (W1–W5): GET /v1/pending-sign-requests, GET /v1/uploads/{upload_id}/sign-payload, GET/POST /v1/sign-requests/{id}.
- **arweave-uploader**: POST /v1/crystalize (для sign_arweave; опционально, если не задан URL — crystalize пропускается с логом).

## Конфиг (env)

Файл **`wallet/mock-runner/.env`** (рядом с `index.js`) подгружается при старте через **dotenv**; значения из окружения процесса (`export …`) **перекрывают** строки из файла.

Пример шаблона: **`wallet/mock-runner/.env.example`** → скопировать в `.env`. Инвариант POC identity — см. `wallet/docs/mock-runner-launch-guide.md` §5.

| Переменная | Обязательно | Описание |
|------------|-------------|----------|
| USER_ID | да | Идентификатор пользователя; передаётся в X-User-Id и в query user_id при опросе. |
| BOT_URL | нет | URL бота (по умолчанию http://localhost:8000). |
| POLL_INTERVAL_MS | нет | Интервал опроса в мс (по умолчанию 2000). |
| ARWEAVE_SERVICE_URL | нет | URL arweave-uploader; если не задан, берётся из ответа sign-payload (arweave_uploader_url). |
| WALLET_MOCK_ARWEAVE_SIGN_MODE | нет | По умолчанию **`local-valid`** — валидный ANS-104 Data Item через `arweave-uploader/tests/fixtures/valid-data-item.js`. **`dummy`** — заглушка (ошибка `signature_invalid` на реальном uploader). **`poc-jwk`** (алиас **`env-jwk`**) — подпись Data Item **реальным Arweave JWK** из env/файла (WAL-POC-7); JWK должен быть **RSA-2048** (как ожидает `validateDataItem` на uploader). |
| WALLET_MOCK_ARWEAVE_PRIVATE_KEY | для poc-jwk | JSON JWK одной строкой; приоритет выше, чем `WALLET_MOCK_ARWEAVE_PRIVATE_KEY_FILE` (как `ARWEAVE_PRIVATE_KEY` в arweave-uploader). |
| WALLET_MOCK_ARWEAVE_PRIVATE_KEY_FILE | для poc-jwk | Путь к файлу с JWK, если переменная выше не задана. |
| ARWEAVE_UPLOADER_PATH | нет | Каталог репозитория `arweave-uploader` (для импорта фикстуры и `deep-hash`). По умолчанию `../../arweave-uploader` от `wallet/mock-runner`. |
| WALLET_AUTH_MODE | нет | `challenge_signature` (по умолчанию) или `legacy`. В `challenge_signature` runner делает handshake `challenge -> verify` и использует Bearer токен. |
| WALLET_ALLOW_LEGACY_X_USER_ID | нет | `true` по умолчанию. Разрешает отправлять `X-User-Id` как fallback. Для strict режима установить `false`. |
| WALLET_MOCK_PRIVATE_KEY | для strict auth | Приватный EVM ключ wallet для подписи `canonical_message`. |
| WALLET_MOCK_ADDRESS | нет | Явный адрес wallet (если не удалось вывести из ключа). Обычно не нужен, если задан `WALLET_MOCK_PRIVATE_KEY`. |
| WALLET_AUTH_SCOPE | нет | Scope для challenge (по умолчанию `signing_flow`). |
| WALLET_MOCK_RPC_URL | для real submit | JSON-RPC URL той же сети, что `CHAIN_ID` / контракт у бота (например локальный anvil/hardhat). |
| WALLET_MOCK_SIGN_CONTRACT_MODE | нет | По умолчанию **`real`** — сборка и подпись tx `createActivity` на `ACTIVITY_REGISTRY` из GET `/sign-requests`. **`dummy`** — прежняя заглушка `signedTransaction` (нужна для отладки; на `BLOCKCHAIN_PROFILE=localhost` бот может не бродкастить). |
| WALLET_MOCK_ACTIVITY_TYPE | нет | `0` (Event) или `1` (Service) — аргумент `createActivity` (по умолчанию `0`). |

## Логи и секреты (WAL-POC-5)

Второй аргумент `log(..., data)` проходит через **`log-sanitize.mjs`**: не пишутся в stdout значения полей с подстроками `token` / `secret` / `password` и т.п., JWT-подобные строки, длинный base64; тело ошибок crystalize режется и вычищается от `upload_token` в тексте. **Приватный ключ** в лог не выводится (никогда не логируем `WALLET_MOCK_PRIVATE_KEY`). Полный сырой `signedTransaction` в лог не попадает.

## Запуск

```bash
cd wallet/mock-runner
export USER_ID=your-test-user-id
export BOT_URL=http://localhost:8000   # при необходимости
export WALLET_AUTH_MODE=challenge_signature
export WALLET_ALLOW_LEGACY_X_USER_ID=true
# export WALLET_MOCK_PRIVATE_KEY=0x...
npm start
# или
node index.js
```

## Полный E2E сценарий

1. Терминал 1: запустить bot (`cd bot && uvicorn api.main:app --reload`).
2. Терминал 2: запустить arweave-uploader (localhost, порт по конфигу).
3. Терминал 3: запустить wallet-mock-runner с USER_ID, совпадающим с пользователем draft.
4. Терминал 4: создать draft (POST /activities/draft или аналог) → получить upload_id; бот отправит пуш sign_arweave; runner заберёт событие, запросит sign-payload и вызовет crystalize. После callback от uploader бот отправит sign_contract; runner заберёт событие и вызовет POST submit.

**Примечание по auth:** в `challenge_signature` runner сначала получает challenge и отправляет подпись. Если ключ не задан или подпись не проходит, runner может работать через fallback `X-User-Id` (если это разрешено сервером).

**Примечание по crystalize:** по умолчанию режим **`local-valid`** (валидный RSA-PSS Data Item). Для подписи **своим** Arweave-ключом задайте `WALLET_MOCK_ARWEAVE_SIGN_MODE=poc-jwk` и JWK (**обязательно RSA-2048** для совместимости с uploader). Режим **`dummy`** — только для отладки невалидной подписи.

**Проверка крипто-слоя без секретов:** `npm test` — сначала **`npm run test:jwk-spki-preflight`** (размер SPKI 2048 vs 4096, WAL-FLOOU-1), затем **`npm run test:poc-jwk`** (круговой прогон с `validateDataItem`). Журнал WAL-POC-7: `wallet/docs/analysis/tasks/task-poc-arweave-env-jwk-signing-runner/TEST-RUN-LOG-WAL-POC-7.md`.
