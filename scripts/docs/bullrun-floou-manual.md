# Bullrun Floou — мануал

Скрипт: **`scripts/run-bullrun-floou.sh`** (запуск из корня репозитория).

## Что делает

В режиме **local** поднимает **bot**, **arweave-uploader** и **wallet/mock-runner**, ждёт `/health`, затем шлёт **POST `/activities/draft`** телом из фиксированного файла, дожидается цикла подписей в mock-runner и делает **GET** итоговой activity. В режиме **remote** локально стартует только **mock-runner**; bot и uploader должны уже быть доступны по URL из окружения.

Блокчейн-нода должна быть запущена отдельно. Подробнее по шагам Floou: `bot/docs/tests/e2e-floou-manual.md`.

## Два параметра, которые задаёт оператор

| Переменная | Значение |
|------------|----------|
| **`FLOOU_MODE`** | `local` (по умолчанию) или `remote` |
| **`USER_ID`** | UUID для заголовка `X-User-Id` (если не задан — дефолтный тестовый UUID в скрипте) |

Всё остальное ( **`BOT_URL`**, **`ARWEAVE_SERVICE_URL`**, ключи, режимы кошелька) настраивается в **`wallet/mock-runner/.env`** — скрипт подхватывает этот файл при старте, если он есть. Дополнительно подключаются `.env` в **`bot/`** и **`arweave-uploader/`** при локальном запуске этих процессов.

## Тело POST `/activities/draft`

Фиксированный путь: **`scripts/floou-draft-request.json`**. Шаблон без своих данных: **`scripts/floou-draft-request.json.example`**. Файл с рабочим телом в git не коммитим (см. `.gitignore`).

- **`local`:** если файла нет или JSON невалиден — используется встроенное минимальное тело.
- **`remote`:** файл обязателен (непустой валидный JSON), иначе скрипт завершится с ошибкой до запуска mock-runner.

## Примеры

```bash
./scripts/run-bullrun-floou.sh

USER_ID='xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx' ./scripts/run-bullrun-floou.sh

FLOOU_MODE=remote USER_ID='…' ./scripts/run-bullrun-floou.sh
```

Для remote URL бота и uploader должны быть в **`wallet/mock-runner/.env`** (или экспортированы в shell до запуска).

Если на боте включён **`GPT_ACTIONS_BEARER_SECRET`**, сам скрипт **не** подставляет заголовок `Authorization` к `curl` — для такого API используйте окружение без этого секрета на время прогона или доработайте обёртку вручную; каноника: `bot/docs/tech/api/api.md` §3.3.

## Дополнительно (не обязательно)

- **`FLOOU_STRICT=true`** или **`./scripts/run-bullrun-floou.sh --strict`** — жёсткая проверка сводки в конце.
- **`FLOOU_LOG_DISABLE=true`** — не писать большой лог в `scripts/logs/`.
- **`FLOOU_SUBMIT_TIMEOUT_SEC`** — таймаут ожидания цикла подписей.

Сводка полей **`FLOOU_SUMMARY_*`**, strict, лог-файл: **`scripts/docs/DEBUG_DEPLOY.md`** (раздел Bullrun Floou).
