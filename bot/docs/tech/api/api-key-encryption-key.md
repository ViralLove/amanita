# `AMANITA_API_ENCRYPTION_KEY` — назначение и эксплуатация

Этот документ описывает, что делает переменная `AMANITA_API_ENCRYPTION_KEY`, как сгенерировать валидное значение готовыми инструментами и как безопасно внедрять/ротировать ключ в продакшене.

## 1) Что это и зачем

`AMANITA_API_ENCRYPTION_KEY` используется в `bot/services/core/api_key.py` (`ApiKeyService`) как ключ шифрования `Fernet`:

- шифрует `secret_key` API-ключей перед сохранением;
- расшифровывает `secret_key` при валидации.

Важно:

- это **симметричный** ключ (один ключ и для encrypt, и для decrypt);
- это **не** blockchain/private key и не ключ ABI/Web3;
- не влияет на загрузку ABI или роли в смарт-контрактах напрямую.

Если переменная не задана, сервис генерирует временный ключ на старте. После рестарта новый ключ уже не сможет расшифровать старые зашифрованные данные.

## 2) Ожидаемый формат

Ключ должен быть в формате Fernet key:

- URL-safe base64 строка;
- обычно длина строки `44` символа (включая `=` в конце).

Пример вида (не использовать как есть):

`JX4VxwQ4F4rFgQ8h7lYjQv2x5wA2P1m9u8J8n5mYwQ0=`

## 3) Генерация ключа (готовые тулзы)

### Вариант A (рекомендуется): Python + `cryptography`

```bash
python3 - <<'PY'
from cryptography.fernet import Fernet
print(Fernet.generate_key().decode())
PY
```

Если `cryptography` не установлен:

```bash
python3 -m pip install cryptography
```

### Вариант B: OpenSSL + Python base64 (без установки `cryptography`)

```bash
openssl rand -base64 32 | tr -d '\n' | python3 - <<'PY'
import base64, sys
raw = base64.b64decode(sys.stdin.read())
print(base64.urlsafe_b64encode(raw).decode())
PY
```

## 4) Проверка валидности ключа

Проверка через `cryptography`:

```bash
python3 - <<'PY'
import os
from cryptography.fernet import Fernet
key = os.environ.get("AMANITA_API_ENCRYPTION_KEY", "")
Fernet(key.encode())
print("OK: valid Fernet key")
PY
```

## 5) Куда прописывать

### Railway (production)

Добавить переменную окружения сервиса:

- `AMANITA_API_ENCRYPTION_KEY=<your-generated-key>`

После этого сделать redeploy/restart сервиса.

### Local

Добавить в `bot/.env`:

`AMANITA_API_ENCRYPTION_KEY=<your-generated-key>`

## 6) Ротация ключа (важно)

Ротация без миграции приведет к невозможности расшифровки старых `encrypted_secret`.

Безопасный порядок:

1. Выгрузить/мигрировать существующие зашифрованные записи (если используются вне MVP).
2. Задать новый ключ в окружении.
3. Перезапустить сервис.
4. Пересоздать/перешифровать секреты, зависящие от старого ключа.

Если у вас только MVP-режим и локальное `api_keys.json`, после ротации возможно потребуется повторно выпустить API keys.

## 7) Безопасность

- Никогда не логировать значение `AMANITA_API_ENCRYPTION_KEY`.
- Не хранить ключ в git (`.env`, Railway Variables, Vault/secret manager).
- Не передавать ключ в тикеты/чаты в открытом виде.

## 8) Минимальный чек-лист после настройки

1. В логах нет warning про `AMANITA_API_ENCRYPTION_KEY не установлен`.
2. Создание/валидация API key работает после рестарта.
3. В логах нет утечек `Authorization`, `apikey`, `Bearer`, raw RPC токенов.

## 9) `VAULT_*` — зачем, когда нужны, где используются

### Краткий вывод аудита

`VAULT_*` в текущем `bot`-коде используются **осознанно**, не случайно:

- в `bot/config.py` источник ключей задаётся **`SECRETS_PROVIDER`** (`vault` | `env`);
- если переменная не задана: **inferred default** — при `DEPLOYMENT_PROFILE=polygon` подразумевается `vault` (обратная совместимость), иначе `env`;
- при **`SECRETS_PROVIDER=vault`** секреты `SELLER_PRIVATE_KEY` / `ARWEAVE_PRIVATE_KEY` читаются из HashiCorp Vault (**fail-fast**, если нет `VAULT_ADDR` / `VAULT_TOKEN`);
- при **`SECRETS_PROVIDER=env`** те же ключи читаются из окружения (в том числе на `polygon`, если явно включить режим).

### Где в коде это зашито

- `bot/config.py`
  - `_resolve_secrets_provider()` → `vault` или `env`;
  - `_load_secrets_from_vault()` при `SECRETS_PROVIDER=vault`;
  - `_load_secrets_from_env()` при `SECRETS_PROVIDER=env`.
- `bot/services/vault_service.py`
  - реальный клиент `hvac` для чтения KV v2 секретов;
  - ожидает путь в формате типа `secret/data/amanita` (по умолчанию).

### Почему по умолчанию для `polygon` всё ещё Vault

- **Рекомендуемая** схема для Polygon — `SECRETS_PROVIDER=vault`: ключи в KV, не в plain env на платформе.
- **Допустимый** сценарий без Vault — `SECRETS_PROVIDER=env` и ключи в Railway Variables (осознанно, с пониманием модели угроз).
- `localhost` обычно работает с `env` (в т.ч. через inferred default).

### Набор переменных и значения

Обязательные при **`SECRETS_PROVIDER=vault`** (независимо от `DEPLOYMENT_PROFILE`):

- `VAULT_ADDR` — публичный URL Vault кластера  
  Пример: `https://<cluster-id>.hashicorp.cloud:8200`
- `VAULT_TOKEN` — токен Vault с правами чтения нужного пути
- `VAULT_PATH` — путь к секретам KV v2 (если не задан, используется `secret/data/amanita`)

Опционально:

- `VAULT_VERIFY_SSL` — `true|false` (по умолчанию `true`)

В самом Vault по `VAULT_PATH` должны быть ключи:

- `SELLER_PRIVATE_KEY`
- `ARWEAVE_PRIVATE_KEY`

### Где брать значения

- `VAULT_ADDR`: HCP Vault -> Cluster Overview -> Public URL.
- `VAULT_TOKEN`: Vault UI -> Access/Tokens -> создать read-only token.
- `VAULT_PATH`: путь, где реально сохранены секреты в KV v2 (обычно `secret/data/amanita`).

### Быстрый выбор для Railway (что делать тебе сейчас)

Вариант A (рекомендуемый для production):

1. `DEPLOYMENT_PROFILE=polygon`, `SECRETS_PROVIDER=vault` (или не задавать provider — на polygon по умолчанию vault).
2. Добавить `VAULT_ADDR`, `VAULT_TOKEN`, `VAULT_PATH`.
3. Проверить, что в Vault есть `SELLER_PRIVATE_KEY` и `ARWEAVE_PRIVATE_KEY`.

Вариант B (ключи в Variables без Vault):

1. `DEPLOYMENT_PROFILE=polygon`, **`SECRETS_PROVIDER=env`**.
2. `SELLER_PRIVATE_KEY` и `ARWEAVE_PRIVATE_KEY` в Railway Variables.
3. Понимать, что это weaker security model по сравнению с Vault.

### Как понять, что Vault подключился успешно

В логах должны быть строки:

- `[CONFIG] DEPLOYMENT_PROFILE: polygon`
- `[CONFIG] SECRETS_PROVIDER=...` (или лог про inferred default)
- `[CONFIG] 🔐 Секреты: Vault (SECRETS_PROVIDER=vault)`
- `[CONFIG] 🔐 Инициализация Vault: ...`
- `[CONFIG] ✅ Секреты успешно загружены из Vault`

Если есть:

- `VaultServiceError: VAULT_ADDR не установлен...`
- `VaultServiceError: VAULT_TOKEN не установлен...`

значит включён **`SECRETS_PROVIDER=vault`**, но Vault-переменные неполные (либо переключитесь на `SECRETS_PROVIDER=env`).

