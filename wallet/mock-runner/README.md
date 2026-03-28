# Wallet-mock runner (W6)

Приложение для localhost, эмулирующее Wallet в сценарии подписания: получает события от бота (sign_arweave, sign_contract), запрашивает данные для подписи и отправляет результат в arweave-uploader или в бота (submit).

## Зависимости

- **Bot** (W1–W5): GET /v1/pending-sign-requests, GET /v1/uploads/{upload_id}/sign-payload, GET/POST /v1/sign-requests/{id}.
- **arweave-uploader**: POST /v1/crystalize (для sign_arweave; опционально, если не задан URL — crystalize пропускается с логом).

## Конфиг (env)

| Переменная | Обязательно | Описание |
|------------|-------------|----------|
| USER_ID | да | Идентификатор пользователя; передаётся в X-User-Id и в query user_id при опросе. |
| BOT_URL | нет | URL бота (по умолчанию http://localhost:8000). |
| POLL_INTERVAL_MS | нет | Интервал опроса в мс (по умолчанию 2000). |
| ARWEAVE_SERVICE_URL | нет | URL arweave-uploader; если не задан, берётся из ответа sign-payload (arweave_uploader_url). |
| WALLET_AUTH_MODE | нет | `challenge_signature` (по умолчанию) или `legacy`. В `challenge_signature` runner делает handshake `challenge -> verify` и использует Bearer токен. |
| WALLET_ALLOW_LEGACY_X_USER_ID | нет | `true` по умолчанию. Разрешает отправлять `X-User-Id` как fallback. Для strict режима установить `false`. |
| WALLET_MOCK_PRIVATE_KEY | для strict auth | Приватный EVM ключ wallet для подписи `canonical_message`. |
| WALLET_MOCK_ADDRESS | нет | Явный адрес wallet (если не удалось вывести из ключа). Обычно не нужен, если задан `WALLET_MOCK_PRIVATE_KEY`. |
| WALLET_AUTH_SCOPE | нет | Scope для challenge (по умолчанию `signing_flow`). |

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

**Примечание по crystalize:** для успешного ответа 200 нужен валидный signed Data Item (RSA-PSS). Используйте `WALLET_MOCK_ARWEAVE_SIGN_MODE=local-valid` для локального полного цикла.
