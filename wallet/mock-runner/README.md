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

## Запуск

```bash
cd wallet/mock-runner
export USER_ID=your-test-user-id
export BOT_URL=http://localhost:8000   # при необходимости
npm start
# или
node index.js
```

## Полный E2E сценарий

1. Терминал 1: запустить bot (`cd bot && uvicorn api.main:app --reload`).
2. Терминал 2: запустить arweave-uploader (localhost, порт по конфигу).
3. Терминал 3: запустить wallet-mock-runner с USER_ID, совпадающим с пользователем draft.
4. Терминал 4: создать draft (POST /activities/draft или аналог) → получить upload_id; бот отправит пуш sign_arweave; runner заберёт событие, запросит sign-payload и вызовет crystalize. После callback от uploader бот отправит sign_contract; runner заберёт событие и вызовет POST submit.

**Примечание:** для успешного ответа 200 от crystalize нужен валидный подписанный Data Item (RSA-PSS). Текущая реализация использует заглушку подписи; uploader вернёт 400 signature_invalid. Для полного прохода используйте тестовый ключ и сборку Data Item по формату ANS-104 или режим uploader с ослабленной проверкой (если есть).
