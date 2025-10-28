# 🚂 Railway Configuration для HashiCorp Vault Integration

**Дата**: 2025-10-10  
**Связано**: ADR-001-hashicorp-vault-integration.md

## 📋 Обзор

Этот документ содержит пошаговые инструкции для настройки Railway Variables для работы с HashiCorp Vault в production окружении (polygon profile).

## ⚠️ Важно: Порядок миграции

**НЕ удаляйте старые переменные до полной проверки новой конфигурации!**

### Безопасный порядок миграции:

1. ✅ Создать секреты в Vault (Phase 4)
2. ✅ Добавить новые Vault переменные в Railway
3. ✅ Задеплоить новый код с Vault integration
4. ✅ **Проверить работу бота** - загружаются ли ключи из Vault
5. ✅ Только после проверки - удалить старые переменные

---

## 🔧 Phase 3: Railway Configuration

### Шаг 1: Открыть Railway Dashboard

1. Перейти на https://railway.app/
2. Войти в аккаунт
3. Выбрать проект **Amanita Bot**
4. Перейти в раздел **Variables**

### Шаг 2: Добавить новые переменные для Vault

**Добавить следующие переменные:**

#### DEPLOYMENT_PROFILE
```
Variable name: DEPLOYMENT_PROFILE
Value: polygon
```
**Описание**: Указывает боту использовать Vault для загрузки секретов

---

#### VAULT_ADDR
```
Variable name: VAULT_ADDR
Value: https://amanita-vault-XXXXX.vault.REGION.hashicorp.cloud:8200
```
**Описание**: URL адрес вашего HCP Vault cluster  
**Где найти**: HashiCorp Cloud Platform → Vault → Overview → Public Cluster URL

**Пример**:
```
https://amanita-vault-abcd1234.vault.eu-west-1.hashicorp.cloud:8200
```

---

#### VAULT_TOKEN
```
Variable name: VAULT_TOKEN
Value: hvs.XXXXXXXXXXXXXXXXXXXXXXXXXXXX
```
**Описание**: Read-only token для аутентификации в Vault  
**Где найти**: В Vault UI → Access → Tokens → Create Token

**Требования к токену**:
- ✅ Read-only access к `secret/data/amanita/*`
- ✅ TTL >= 30 days (или renewable)
- ❌ NO write/delete permissions

**Пример**:
```
hvs.CAESIJkf2nH8XyZ4QqP9L1MxNvK3R7bT6wU0cE5dV8sY2fA1
```

---

#### VAULT_PATH (опционально)
```
Variable name: VAULT_PATH
Value: secret/data/amanita
```
**Описание**: Путь к секретам в Vault KV v2  
**По умолчанию**: `secret/data/amanita` (можно не указывать)

---

### Шаг 3: Проверить существующие переменные

**Убедиться что эти переменные уже установлены:**

```
✅ TELEGRAM_BOT_TOKEN
✅ WALLET_APP_URL
✅ BLOCKCHAIN_PROFILE
✅ WEB3_PROVIDER_URI (RPC URL для Polygon)
✅ MAGIC_REGISTRY_CONTRACT_ADDRESS
✅ SUPABASE_URL
✅ SUPABASE_ANON_KEY
```

**НЕ удаляйте пока** (удалим после проверки):
```
⚠️ SELLER_PRIVATE_KEY - будет перемещен в Vault
⚠️ ARWEAVE_PRIVATE_KEY - будет перемещен в Vault
```

---

### Шаг 4: Deploy новой версии кода

1. После добавления Vault переменных в Railway
2. Railway автоматически запустит новый deployment
3. Следить за логами:

```bash
# В Railway dashboard → Deployments → Latest → View Logs
```

**Ожидаемые логи при успешном запуске:**

```
[CONFIG] DEPLOYMENT_PROFILE: polygon
[CONFIG] 🔐 Polygon profile: загружаем секреты из Vault
[CONFIG] 🔐 Инициализация Vault: https://....vault.hashicorp.cloud:8200
[CONFIG] 🔐 Vault path: secret/data/amanita
Инициализация VaultService: https://...
✅ VaultService успешно инициализирован и аутентифицирован
[CONFIG] ✅ Секреты успешно загружены из Vault
```

---

### Шаг 5: Проверка работы бота

**После успешного deployment проверить:**

1. **Bot запустился без ошибок**
   - Проверить Railway logs - нет VaultConnectionError
   - Проверить что бот отвечает в Telegram

2. **Транзакции работают**
   - Протестировать любую операцию с blockchain (например, активация пользователя)
   - Убедиться что транзакция подписывается и отправляется

3. **Ключи загружаются из Vault**
   - В логах есть `✅ Секреты успешно загружены из Vault`
   - НЕТ логов `📁 Localhost profile: загружаем секреты из .env`

**Если все проверки пройдены → переходим к Шагу 6**

---

### Шаг 6: Удалить старые переменные (только после проверки!)

**⚠️ ВАЖНО: Удалять только после подтверждения что Vault работает!**

В Railway Variables **удалить**:

```
❌ SELLER_PRIVATE_KEY
❌ ARWEAVE_PRIVATE_KEY
```

**Эти ключи теперь хранятся только в Vault!**

---

## 🔒 Итоговая конфигурация Railway Variables

**После миграции должны остаться:**

### Vault Variables (новые)
```
✅ DEPLOYMENT_PROFILE=polygon
✅ VAULT_ADDR=https://....vault.hashicorp.cloud:8200
✅ VAULT_TOKEN=hvs.XXXXXXXXX
✅ VAULT_PATH=secret/data/amanita (опционально)
```

### Application Variables (существующие)
```
✅ TELEGRAM_BOT_TOKEN
✅ WALLET_APP_URL
✅ BLOCKCHAIN_PROFILE
✅ WEB3_PROVIDER_URI
✅ MAGIC_REGISTRY_CONTRACT_ADDRESS
✅ SUPABASE_URL
✅ SUPABASE_ANON_KEY
✅ ENVIRONMENT
✅ APP_ROOT_DIR
✅ STORAGE_COMMUNICATION_TYPE
✅ AMANITA_API_KEY
✅ AMANITA_API_SECRET
```

### Удалены (перемещены в Vault)
```
❌ SELLER_PRIVATE_KEY → теперь в Vault
❌ ARWEAVE_PRIVATE_KEY → теперь в Vault
```

---

## 🐛 Troubleshooting

### Ошибка: "VaultService недоступен (hvac не установлен)"

**Причина**: hvac library не установлена в Railway environment

**Решение**:
```bash
# Убедитесь что hvac>=2.1.0 есть в bot/requirements.txt
# Railway автоматически установит при следующем deploy
```

---

### Ошибка: "VAULT_ADDR не установлен для polygon profile"

**Причина**: Забыли добавить VAULT_ADDR в Railway Variables

**Решение**:
1. Перейти в Railway → Variables
2. Добавить `VAULT_ADDR` с URL вашего Vault cluster

---

### Ошибка: "Не удалось аутентифицироваться в Vault"

**Причина**: Невалидный или expired VAULT_TOKEN

**Решение**:
1. Проверить что токен не истек (TTL)
2. Создать новый токен в Vault UI
3. Обновить VAULT_TOKEN в Railway Variables

---

### Ошибка: "Секрет 'SELLER_PRIVATE_KEY' не найден в Vault"

**Причина**: Секреты не загружены в Vault или неправильный VAULT_PATH

**Решение**:
1. Проверить что секреты созданы в Vault (см. Phase 4)
2. Проверить правильность VAULT_PATH
3. Проверить что токен имеет read access к этому path

---

### Bot не запускается после миграции

**Rollback план**:

1. **Немедленно**: Изменить в Railway Variables
   ```
   DEPLOYMENT_PROFILE=localhost
   ```

2. **Добавить обратно** старые переменные:
   ```
   SELLER_PRIVATE_KEY=0x...
   ARWEAVE_PRIVATE_KEY=...
   ```

3. **Revert code** (если нужно):
   ```bash
   git revert <commit-hash-vault-integration>
   git push
   ```

4. **Проверить** что бот работает с .env configuration

5. **Исследовать** проблему в логах Railway

---

## 📊 Мониторинг и Алерты

### Рекомендуемые проверки

**Ежедневно** (первая неделя после миграции):
- [ ] Проверить Railway logs на VaultConnectionError
- [ ] Проверить что транзакции отправляются
- [ ] Проверить Vault audit logs на anomalies

**Еженедельно**:
- [ ] Проверить TTL токена (продлить если нужно)
- [ ] Review Vault access logs
- [ ] Проверить что bot restarts работают без проблем

**Ежемесячно**:
- [ ] Rotate Vault token (best practice)
- [ ] Review и update access policies
- [ ] Security audit секретов

---

## 🎯 Критерии успеха

**Миграция считается успешной если:**

- ✅ Bot запускается с `DEPLOYMENT_PROFILE=polygon`
- ✅ Логи показывают `✅ Секреты успешно загружены из Vault`
- ✅ Транзакции подписываются и отправляются
- ✅ Старые переменные удалены из Railway
- ✅ Vault audit logs показывают read operations
- ✅ 0 ошибок в течение 24 часов после миграции

---

## 📚 Связанные документы

- [ADR-001: HashiCorp Vault Integration](../adr/ADR-001-hashicorp-vault-integration.md)
- [VAULT_SETUP.md](./VAULT_SETUP.md) - инструкции по настройке Vault
- [AIJournal.md](../bot/docs/AIJournal.md) - подробный анализ интеграции
- [SECURITY-AUDIT-2025-10-09.md](./SECURITY-AUDIT-2025-10-09.md)

---

**Автор**: eslinko  
**Дата создания**: 2025-10-10  
**Последнее обновление**: 2025-10-10  
**Статус**: ✅ Ready for Production

