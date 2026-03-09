# Wallet-mock runner (W6)

Эмулирует приложение с Wallet на localhost для E2E сценария подписаний: опрос событий у бота, обработка sign_arweave (sign-payload → crystalize) и sign_contract (sign-request → submit).

- **Код:** `wallet/mock-runner/` (Node.js, точка входа `index.js`).
- **Гайд по запуску для отладки загрузки:** [mock-runner-launch-guide.md](mock-runner-launch-guide.md) — постоянный документ.
- **Конфиг:** env `BOT_URL`, `USER_ID`, `POLL_INTERVAL_MS`, `ARWEAVE_SERVICE_URL` (опционально).
- **Запуск:** `cd wallet/mock-runner && USER_ID=... npm start`.

Подробности и контракт с ботом — в [mock-runner/README.md](../mock-runner/README.md). Зависимости: bot W1–W5 (в т.ч. GET /v1/pending-sign-requests), arweave-uploader для crystalize.
