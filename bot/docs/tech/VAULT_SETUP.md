# 🔐 HashiCorp Vault Setup для Amanita Bot

**Дата**: 2025-10-10  
**Связано**: ADR-001-hashicorp-vault-integration.md

## 📋 Обзор

Этот документ содержит пошаговые инструкции для настройки HashiCorp Cloud Platform (HCP) Vault для хранения production секретов Amanita Bot.

## 🎯 Цели

- Безопасное хранение `SELLER_PRIVATE_KEY` и `ARWEAVE_PRIVATE_KEY`
- Централизованное управление секретами
- Audit trail всех обращений к ключам
- Возможность rotation без редеплоя приложения

---

## 🚀 Phase 4: Vault Setup

### Шаг 1: Создание HCP Vault Cluster

#### 1.1 Регистрация на HashiCorp Cloud Platform

1. Перейти на https://portal.cloud.hashicorp.com/sign-up
2. Зарегистрироваться (email + password или через Google/GitHub)
3. Подтвердить email

#### 1.2 Создание организации

1. После входа → **Create organization**
2. Название: `Amanita` (или любое другое)
3. Выбрать план: **Free Tier** (достаточно для production)

#### 1.3 Создание Vault Cluster

1. В Dashboard → **Create cluster**
2. **Cluster name**: `amanita-vault`
3. **Cloud provider**: AWS (или Azure/GCP по желанию)
4. **Region**: 
   - Рекомендуется: `eu-west-1` (Ireland) - близко к Европе
   - Или выбрать ближайший к Railway deployment region
5. **Tier**: **Development** (Free tier)
6. Нажать **Create cluster**

**⏰ Ожидание**: Создание кластера займет ~3-5 минут

#### 1.4 Получение Cluster URL

После создания кластера:

1. Перейти в **Vault cluster overview**
2. Скопировать **Public cluster URL**

**Формат**:
```
https://amanita-vault-XXXXX.vault.REGION.hashicorp.cloud:8200
```

**Пример**:
```
https://amanita-vault-abc123.vault.eu-west-1.hashicorp.cloud:8200
```

⚠️ **Сохранить** этот URL - он понадобится для Railway Variables

---

### Шаг 2: Настройка Secrets Engine

#### 2.1 Активация KV v2 Secrets Engine

1. В Vault UI → **Secrets** → **Enable new engine**
2. Выбрать **KV** (Key/Value)
3. **Version**: `Version 2` (обязательно!)
4. **Path**: `secret` (оставить по умолчанию)
5. Нажать **Enable**

KV v2 уже должен быть активен по умолчанию, но проверить не помешает.

---

### Шаг 3: Создание секретов

#### 3.1 Создание path для Amanita

1. В Vault UI → **Secrets** → `secret/`
2. Нажать **Create secret**
3. **Path for this secret**: `amanita`
4. Нажать **Next**

#### 3.2 Добавление SELLER_PRIVATE_KEY

1. **Secret key**: `SELLER_PRIVATE_KEY`
2. **Secret value**: `0x...` (ваш приватный ключ seller wallet)

**⚠️ ВАЖНО**:
- Копируйте ключ **БЕЗ пробелов** в начале/конце
- Ключ должен начинаться с `0x`
- Длина: 66 символов (0x + 64 hex символа)

**Пример**:
```
0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef
```

#### 3.3 Добавление ARWEAVE_PRIVATE_KEY

1. Нажать **+ Add** для добавления еще одного ключа
2. **Secret key**: `ARWEAVE_PRIVATE_KEY`
3. **Secret value**: `{"kty":"RSA",...}` (ваш ArWeave JWK)

**⚠️ ВАЖНО**:
- ArWeave ключ в формате JSON (JWK)
- Копируйте **весь JSON объект**
- Убедитесь что JSON валидный (без syntax errors)

**Пример**:
```json
{
  "kty": "RSA",
  "n": "...",
  "e": "AQAB",
  "d": "...",
  ...
}
```

#### 3.4 Сохранение секретов

1. Нажать **Save**
2. Убедиться что путь к секретам: `secret/amanita`

**Итоговая структура в Vault**:
```
secret/
└── amanita/
    ├── SELLER_PRIVATE_KEY = "0x..."
    └── ARWEAVE_PRIVATE_KEY = "{...}"
```

---

### Шаг 4: Создание Access Policy

#### 4.1 Создание read-only policy

1. В Vault UI → **Policies** → **Create ACL policy**
2. **Name**: `amanita-bot-readonly`
3. **Policy**:

```hcl
# Read-only access для Amanita Bot
path "secret/data/amanita" {
  capabilities = ["read"]
}

# List доступ для проверки существования secrets
path "secret/metadata/amanita" {
  capabilities = ["list", "read"]
}
```

4. Нажать **Create policy**

**Объяснение**:
- `secret/data/amanita` - путь к данным в KV v2 (автоматически добавляется `/data`)
- `capabilities = ["read"]` - только чтение, НЕТ write/delete
- `secret/metadata/amanita` - метаданные (для list operations)

---

### Шаг 5: Создание Token для Railway

#### 5.1 Создание сервисного токена

1. В Vault UI → **Access** → **Tokens** → **Create token**
2. **Token type**: `Service Token`
3. **Policies**: Выбрать `amanita-bot-readonly`
4. **TTL** (Time To Live):
   - Рекомендуется: `720h` (30 дней)
   - Или `renewable: true` для auto-renewal
5. **Display name**: `Railway Bot Token`
6. Нажать **Create token**

#### 5.2 Копирование токена

⚠️ **ВАЖНО**: Токен показывается **только один раз**!

1. Скопировать токен (формат: `hvs.XXXXXXXXXXXXXXXXX`)
2. Сохранить в **безопасное место** (password manager)
3. Этот токен будет использован в Railway Variables

**Пример токена**:
```
hvs.CAESIJkf2nH8XyZ4QqP9L1MxNvK3R7bT6wU0cE5dV8sY2fA1Giog...
```

---

### Шаг 6: Проверка доступа

#### 6.1 Тест через Vault CLI (опционально)

Если у вас установлен Vault CLI:

```bash
# Установка Vault CLI (macOS)
brew install vault

# Экспорт переменных
export VAULT_ADDR="https://amanita-vault-XXXXX.vault.eu-west-1.hashicorp.cloud:8200"
export VAULT_TOKEN="hvs.XXXXXXXXXXXXXXXXX"

# Проверка аутентификации
vault token lookup

# Чтение секретов
vault kv get secret/amanita

# Ожидаемый вывод:
# ====== Data ======
# Key                    Value
# ---                    -----
# ARWEAVE_PRIVATE_KEY    {...}
# SELLER_PRIVATE_KEY     0x...
```

#### 6.2 Тест через Python (локально)

Создать тестовый скрипт `test_vault.py`:

```python
#!/usr/bin/env python3
"""
Тест подключения к Vault и чтения секретов.
"""
import os
import hvac

# Vault configuration
VAULT_ADDR = "https://amanita-vault-XXXXX.vault.REGION.hashicorp.cloud:8200"
VAULT_TOKEN = "hvs.XXXXXXXXXXXXXXXXX"  # Ваш токен

# Инициализация клиента
client = hvac.Client(url=VAULT_ADDR, token=VAULT_TOKEN)

# Проверка аутентификации
if not client.is_authenticated():
    print("❌ Authentication failed!")
    exit(1)

print("✅ Authentication successful!")

# Чтение секретов
try:
    response = client.secrets.kv.v2.read_secret_version(path="amanita")
    data = response['data']['data']
    
    print(f"\n✅ Secrets found: {len(data)} keys")
    print(f"   - SELLER_PRIVATE_KEY: {data['SELLER_PRIVATE_KEY'][:10]}...")
    print(f"   - ARWEAVE_PRIVATE_KEY: {data['ARWEAVE_PRIVATE_KEY'][:20]}...")
    
except Exception as e:
    print(f"❌ Error reading secrets: {e}")
    exit(1)
```

Запустить:
```bash
pip install hvac
python test_vault.py
```

**Ожидаемый вывод**:
```
✅ Authentication successful!
✅ Secrets found: 2 keys
   - SELLER_PRIVATE_KEY: 0x12345678...
   - ARWEAVE_PRIVATE_KEY: {"kty":"RSA","n...
```

---

### Шаг 7: Настройка Audit Logging (опционально, но рекомендуется)

#### 7.1 Активация File Audit Device

1. В Vault UI → **Audit Devices** → **Enable audit device**
2. **Type**: `File`
3. **Path**: `/vault/audit.log`
4. Нажать **Enable**

#### 7.2 Просмотр Audit Logs

1. В Vault UI → **Audit** → **Logs**
2. Фильтр по:
   - **Path**: `secret/data/amanita`
   - **Operation**: `read`

**Что будет логироваться**:
- Время обращения к секретам
- IP адрес (Railway deployment)
- Token ID
- Операция (read)
- Результат (success/failure)

---

## 📊 Финальная конфигурация

### В HashiCorp Vault:

```
✅ Cluster: amanita-vault (создан)
✅ Secrets Engine: secret/ (KV v2)
✅ Secrets Path: secret/amanita
   ├── SELLER_PRIVATE_KEY
   └── ARWEAVE_PRIVATE_KEY
✅ Policy: amanita-bot-readonly (read-only)
✅ Token: hvs.XXXXX (с policy amanita-bot-readonly)
✅ Audit Device: File (опционально)
```

### Для Railway Variables:

Передать эти значения в Railway (см. VAULT_RAILWAY_SETUP.md):

```
VAULT_ADDR=https://amanita-vault-XXXXX.vault.REGION.hashicorp.cloud:8200
VAULT_TOKEN=hvs.XXXXXXXXXXXXXXXXX
VAULT_PATH=secret/data/amanita
DEPLOYMENT_PROFILE=polygon
```

---

## 🔄 Rotation Strategy

### Когда ротировать токен:

- **Регулярно**: Каждые 30-90 дней (best practice)
- **При подозрении**: Если токен мог быть скомпрометирован
- **При истечении TTL**: Если не используется renewable token

### Как ротировать токен:

1. **Создать новый токен** в Vault UI (Шаг 5)
2. **Обновить VAULT_TOKEN** в Railway Variables
3. **Railway auto-redeploy** бота
4. **Проверить логи** - новый токен работает
5. **Отозвать старый токен** в Vault UI

**⏰ Downtime**: ~2-3 минуты (время редеплоя Railway)

### Как ротировать приватные ключи:

1. **Создать новые wallet addresses**
2. **Обновить секреты в Vault**:
   ```bash
   vault kv patch secret/amanita \
     SELLER_PRIVATE_KEY="0xNEW_KEY" \
     ARWEAVE_PRIVATE_KEY="{...NEW_JWK...}"
   ```
3. **Перезапустить бота** в Railway (Manual trigger или wait for auto-restart)
4. **Проверить логи** - новые ключи загружены
5. **Перевести средства** со старых адресов на новые
6. **Обновить адреса** в контрактах (если hardcoded)

**⏰ Downtime**: ~5-10 минут (зависит от blockchain transactions)

---

## 🐛 Troubleshooting

### Проблема: "Permission denied" при чтении секретов

**Причина**: Токен не имеет правильной policy

**Решение**:
1. Проверить что policy `amanita-bot-readonly` применена к токену
2. Проверить синтаксис policy (path должен быть `secret/data/amanita`)
3. Создать новый токен с правильной policy

---

### Проблема: Секреты не найдены (404)

**Причина**: Неправильный path к секретам

**Решение**:
1. Проверить что секреты созданы по пути `secret/amanita`
2. В Railway VAULT_PATH должен быть `secret/data/amanita` (с `/data` для KV v2)
3. Убедиться что используется KV v2, а не v1

---

### Проблема: Token expired

**Причина**: Истек TTL токена

**Решение**:
1. Создать новый токен (Шаг 5)
2. Обновить VAULT_TOKEN в Railway
3. В будущем: использовать renewable tokens

---

### Проблема: Cluster недоступен

**Причина**: HCP Vault cluster в maintenance или ошибка сети

**Решение**:
1. Проверить статус HCP в https://status.hashicorp.com/
2. Проверить что Railway может достучаться до Vault URL
3. Временно: rollback на localhost profile (см. VAULT_RAILWAY_SETUP.md)

---

## 🔒 Security Best Practices

### DO ✅

- ✅ Используйте **отдельные токены** для production и staging
- ✅ Настройте **Audit Logging** для отслеживания доступа
- ✅ Используйте **короткий TTL** для токенов (30-90 дней)
- ✅ **Ротируйте токены** регулярно
- ✅ Храните токены в **password manager** (1Password, LastPass)
- ✅ Используйте **read-only policy** для application tokens
- ✅ Настройте **alerting** на suspicious access patterns

### DON'T ❌

- ❌ НЕ коммитьте токены в Git
- ❌ НЕ используйте root token для applications
- ❌ НЕ давайте write/delete permissions application tokens
- ❌ НЕ используйте один токен для всех environments
- ❌ НЕ храните токены в plaintext файлах
- ❌ НЕ делитесь токенами через insecure channels (Slack, email)

---

## 📈 Мониторинг и Алерты

### Метрики для отслеживания

**В Vault Audit Logs**:
- Количество read operations в день
- Failed authentication attempts
- Access patterns (IP addresses, timestamps)

**В Railway Logs**:
- VaultConnectionError count
- Время загрузки секретов (latency)
- Bot restart frequency

### Рекомендуемые алерты

**Critical**:
- ⚠️ Failed Vault authentication (immediate alert)
- ⚠️ Bot не может стартовать из-за Vault errors

**Warning**:
- ⚠️ Token TTL < 7 дней (напоминание о rotation)
- ⚠️ Unusual access patterns (много reads за короткое время)

**Info**:
- ℹ️ Successful token rotation
- ℹ️ Secrets updated in Vault

---

## 📚 Дополнительные ресурсы

### Документация

- [HashiCorp Vault Documentation](https://www.vaultproject.io/docs)
- [KV v2 Secrets Engine](https://www.vaultproject.io/docs/secrets/kv/kv-v2)
- [Vault Policies](https://www.vaultproject.io/docs/concepts/policies)
- [HVAC Python Client](https://hvac.readthedocs.io/)

### Связанные документы

- [ADR-001: HashiCorp Vault Integration](../adr/ADR-001-hashicorp-vault-integration.md)
- [VAULT_RAILWAY_SETUP.md](./VAULT_RAILWAY_SETUP.md)
- [AIJournal.md](../bot/docs/AIJournal.md)
- [SECURITY-AUDIT-2025-10-09.md](./SECURITY-AUDIT-2025-10-09.md)

---

## ✅ Checklist: Готовность к Production

Перед переходом на Vault в production убедитесь:

**Vault Setup**:
- [ ] HCP Vault cluster создан и активен
- [ ] KV v2 secrets engine активен
- [ ] Секреты `SELLER_PRIVATE_KEY` и `ARWEAVE_PRIVATE_KEY` загружены
- [ ] Read-only policy `amanita-bot-readonly` создана
- [ ] Service token создан с правильной policy
- [ ] Token TTL >= 30 дней (или renewable)
- [ ] Audit logging активировано (рекомендуется)

**Local Testing**:
- [ ] Vault CLI test успешен (опционально)
- [ ] Python test script работает
- [ ] Секреты читаются корректно

**Railway Configuration**:
- [ ] VAULT_ADDR добавлен в Railway Variables
- [ ] VAULT_TOKEN добавлен в Railway Variables
- [ ] DEPLOYMENT_PROFILE=polygon установлен
- [ ] Новый код задеплоен в Railway

**Validation**:
- [ ] Bot запустился без VaultConnectionError
- [ ] Логи показывают "✅ Секреты успешно загружены из Vault"
- [ ] Транзакции работают (ключи валидны)
- [ ] Vault audit logs показывают read operations

**Final Step**:
- [ ] Старые SELLER_PRIVATE_KEY и ARWEAVE_PRIVATE_KEY удалены из Railway

---

**Автор**: eslinko  
**Дата создания**: 2025-10-10  
**Последнее обновление**: 2025-10-10  
**Статус**: ✅ Ready for Implementation

