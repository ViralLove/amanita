# BULLRUN phase log — SECRETS-PROVIDER (optional Vault для polygon)

**Таск:** [task-refactor-optional-vault-secrets-loading-for-polygon.md](./task-refactor-optional-vault-secrets-loading-for-polygon.md)  
**Дата:** 2026-04-01

| Фаза | Содержание | Статус |
|------|------------|--------|
| 0 | Структура `task-<slug>/` под `bot/docs/analysis/tasks/`; ссылка в `bot-tasks-index.md`; плоский файл удалён | done |
| 1 | Рефактор `bot/config.py`: `SECRETS_PROVIDER=vault\|env`, inferred default (`polygon` → vault, иначе → env), лог выбора | done |
| 2 | `.env.example` + `vault-simple-manual.md` + `api-key-encryption-key.md` — матрица режимов | done |
| 3 | Smoke импорта `config` (env OK, vault fail-fast OK); статус в `bot-tasks-index.md` 🔵 | done |

**Инференс по умолчанию:** если `SECRETS_PROVIDER` не задан — при `DEPLOYMENT_PROFILE=polygon` считается `vault` (как раньше); иначе `env`. Для Railway с ключами только в Variables на polygon задать явно `SECRETS_PROVIDER=env`.

**Ожидает оператора:** подтвердить приёмку AC/DoD и при необходимости добавить `acceptance-verification-secrets-provider.md`.
