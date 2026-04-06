# Shell-скрипты (`scripts/shell/`)

Каталог для bash-обвязки вокруг репозитория. Запуск из **корня репозитория** обычно так:

```bash
./scripts/shell/<script>.sh
```

Для обратной совместимости часть команд продублирована обёртками в `scripts/` (тот же `exec` в `scripts/shell/…`).

| Скрипт | Назначение |
|--------|------------|
| `run-bullrun-floou.sh` | Полный E2E Floou: local/remote, bot, uploader, mock-runner, draft → подписи → summary |
| `post-floou-draft.sh` | Только **POST /activities/draft** из `scripts/floou-draft-request.json` (ручной wallet/uploader) |
| `sync_artifacts_to_bot.sh` | Копирование `artifacts/contracts` → `bot/artifacts/contracts` после `hardhat compile` |

Переменные окружения для draft: **`scripts/.env`** (см. `scripts/docs/bullrun-floou-manual.md`): `BOT_URL`, `USER_ID`, `GPT_ACTIONS_BEARER_SECRET`, и т.д.
