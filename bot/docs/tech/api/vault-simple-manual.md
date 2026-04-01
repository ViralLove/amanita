# HashiCorp Vault: простой мануал для Amanita Bot

Короткая инструкция без лишней теории: что создать в HashiCorp, какие ключи положить и как связать с Railway.

## 0) Режимы секретов (`SECRETS_PROVIDER`)

| Режим | Когда | Переменные | Ключи |
|-------|--------|------------|--------|
| **`vault`** | Production с HCP Vault | `SECRETS_PROVIDER=vault` (или не задано при `DEPLOYMENT_PROFILE=polygon`), `VAULT_ADDR`, `VAULT_TOKEN`, при необходимости `VAULT_PATH` | В KV: `SELLER_PRIVATE_KEY`, `ARWEAVE_PRIVATE_KEY` |
| **`env`** | Dev или Polygon без Vault (например только Railway Variables) | `SECRETS_PROVIDER=env`, плюс обычные `DEPLOYMENT_PROFILE`, RPC и контракты | `SELLER_PRIVATE_KEY`, `ARWEAVE_PRIVATE_KEY` в env |

`DEPLOYMENT_PROFILE` задаёт контекст деплоя (сеть/окружение), **не** источник ключей. Источник — только `SECRETS_PROVIDER` (или inferred default: `polygon` → `vault`, иначе → `env`).

## 1) Важно: `Box` != Vault

Если ты видишь **Box / Vagrant** (как на скрине), это другой продукт HashiCorp.

Для нашего бота нужен именно:

- **HashiCorp Cloud Platform (HCP)**
- сервис **Vault**
- URL вида `https://...vault....hashicorp.cloud:8200`

## 2) Что именно мы хотим получить

Чтобы бот в режиме **Vault** на Polygon стартовал, нужны:

- в Railway Variables:
  - `DEPLOYMENT_PROFILE=polygon`
  - `SECRETS_PROVIDER=vault` (или опустить — для polygon по умолчанию всё ещё vault)
  - `VAULT_ADDR`
  - `VAULT_TOKEN`
  - `VAULT_PATH` (обычно `secret/data/amanita`)
- в Vault по этому path:
  - `SELLER_PRIVATE_KEY`
  - `ARWEAVE_PRIVATE_KEY`

Если Vault нет, но ключи уже есть в Variables: `DEPLOYMENT_PROFILE=polygon` и **`SECRETS_PROVIDER=env`**, плюс `SELLER_PRIVATE_KEY` / `ARWEAVE_PRIVATE_KEY` в env.

## 3) Что это за ключи

- `SELLER_PRIVATE_KEY`  
  Приватный EVM-ключ продавца (EOA). Им бот подписывает on-chain транзакции (Polygon).

- `ARWEAVE_PRIVATE_KEY`  
  JSON JWK ключ Arweave. Им бот/аплоадер подписывает операции публикации в Arweave.

Это не «воссоздаваемые» ключи. Их нужно взять из текущих рабочих секретов (где они у тебя сейчас хранятся) и перенести в Vault.

## 4) Пошагово: создать Vault и положить ключи

### Шаг A. Создать HCP Vault cluster

1. Зайти в HCP Dashboard (не Box Registry).
2. Create cluster -> выбрать **Vault**.
3. Получить **Public Cluster URL** -> это и будет `VAULT_ADDR`.

Формат:
`https://<cluster-name>.<...>.hashicorp.cloud:8200`

### Шаг B. Создать секреты

1. В Vault открыть `Secrets` (KV v2).
2. Создать path: `secret/amanita` (в UI обычно так; в env потом будет `secret/data/amanita`).
3. Добавить два поля:
   - `SELLER_PRIVATE_KEY` = `0x...` (64 hex после `0x`)
   - `ARWEAVE_PRIVATE_KEY` = `{...}` (полный JSON JWK)
4. Save.

### Шаг C. Создать read-only token

1. Vault -> Access -> Tokens -> Create.
2. Политика: read для `secret/data/amanita`.
3. Скопировать token (`hvs....`) -> это `VAULT_TOKEN`.

## 5) Что добавить в Railway

В сервисе бота (Variables):

```env
DEPLOYMENT_PROFILE=polygon
SECRETS_PROVIDER=vault
VAULT_ADDR=https://<your-cluster>.hashicorp.cloud:8200
VAULT_TOKEN=hvs.<your-token>
VAULT_PATH=secret/data/amanita
```

Остальные рабочие переменные (`WEB3_PROVIDER_URI`, адреса контрактов, `WALLET_APP_URL`, и т.д.) остаются как есть.

## 6) Как проверить, что всё работает

После deploy в логах должны быть:

- `[CONFIG] DEPLOYMENT_PROFILE: polygon`
- `[CONFIG] SECRETS_PROVIDER=...` или сообщение про inferred default
- `[CONFIG] 🔐 Секреты: Vault (SECRETS_PROVIDER=vault)`
- `[CONFIG] 🔐 Инициализация Vault: ...`
- `[CONFIG] ✅ Секреты успешно загружены из Vault`

Если видишь:

- `VaultServiceError: VAULT_ADDR не установлен...` -> режим vault, но не задан `VAULT_ADDR` (либо переключитесь на `SECRETS_PROVIDER=env`)
- `VaultServiceError: VAULT_TOKEN не установлен...` -> аналогично для токена
- `Секрет ... не найден` -> неверный `VAULT_PATH` или ключи не созданы в Vault

## 7) Практичный режим миграции (без простоя)

1. Сначала добавить Vault-переменные.
2. Убедиться, что бот стартует и читает секреты из Vault.
3. Только после этого удалять старые чувствительные переменные из Railway.

---

Подробнее (полные playbook-документы в проекте):

- `bot/docs/tech/VAULT_SETUP.md`
- `bot/docs/tech/VAULT_RAILWAY_SETUP.md`
- `bot/docs/tech/api/api-key-encryption-key.md` (раздел про `VAULT_*`)

