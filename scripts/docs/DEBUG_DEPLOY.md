# Debug Guide для Deploy Script

## 🔍 Включение Debug Логирования

### Метод 1: Переменная окружения LOG_LEVEL
```bash
LOG_LEVEL=debug DEPLOY_ACTION=1 npx hardhat run scripts/deploy_full.js --network ganache
```

### Метод 2: Переменная окружения DEBUG
```bash
DEBUG=1 DEPLOY_ACTION=1 npx hardhat run scripts/deploy_full.js --network ganache
```

### Метод 3: Комбинированный запуск
```bash
LOG_LEVEL=debug DEBUG=1 DEPLOY_ACTION=1 npx hardhat run scripts/deploy_full.js --network ganache
```

---

## 📋 Что проверяется в Debug режиме

### 1. RPC URL Configuration
Debug логи показывают:
- `RPC_URL` из .env
- `WEB3_PROVIDER_URI` из .env
- Выбранный RPC URL (приоритет: RPC_URL > WEB3_PROVIDER_URI > fallback)
- Chain ID подключенной сети
- Номер текущего блока

### 2. Private Key Configuration
Debug логи показывают:
- `deployOptions.privateKey` (если передается явно)
- `config.deployer.privateKey` (из .env)
- Какой ключ используется (с маскированием для безопасности)
- Адрес deployer'а, вычисленный из ключа

### 3. Balance Check
Debug логи показывают:
- Адрес deployer'а
- Баланс в ETH и wei
- Chain ID сети
- Provider URL
- ⚠️ **WARNING** если баланс = 0 (деплой будет прерван ДО попытки отправки транзакции)

---

## 🔧 Решение проблем

### Проблема: "Sender doesn't have enough funds"

**Симптомы:**
```
[ERROR] Deployer account 0x... has ZERO balance!
[ERROR] Please fund the account in Ganache or check if correct private key is used.
```

**Решения:**

1. **Проверьте адрес в Ganache:**
   - Откройте Ganache GUI
   - Найдите адрес, соответствующий `DEPLOYER_PRIVATE_KEY`
   - Убедитесь, что баланс > 0 ETH

2. **Проверьте правильность private key:**
   ```bash
   # Включите debug и проверьте адрес
   LOG_LEVEL=debug DEPLOY_ACTION=1 npx hardhat run scripts/deploy_full.js --network ganache
   ```
   - Сравните адрес в логах с адресом в Ganache
   - Если не совпадает - проверьте `DEPLOYER_PRIVATE_KEY` в .env

3. **Проверьте RPC URL:**
   - Debug логи покажут, какой RPC URL используется
   - Для Ganache должен быть: `http://127.0.0.1:7545`
   - Если используется другой - добавьте в .env:
     ```bash
     RPC_URL=http://127.0.0.1:7545
     # или
     WEB3_PROVIDER_URI=http://127.0.0.1:7545
     ```

### Проблема: Подключение к неправильной сети

**Симптомы:**
```
Connected to network: 31337  # Hardhat вместо Ganache (1337)
```

**Решение:**
1. Проверьте `RPC_URL` или `WEB3_PROVIDER_URI` в .env
2. Убедитесь, что Ganache запущен на порту 7545
3. Включите debug для проверки:
   ```bash
   LOG_LEVEL=debug DEPLOY_ACTION=1 npx hardhat run scripts/deploy_full.js --network ganache
   ```

### Проблема: Private key не найден

**Симптомы:**
```
[ERROR] No private key available!
[ERROR] Set DEPLOYER_PRIVATE_KEY in .env
```

**Решение:**
1. Проверьте наличие `DEPLOYER_PRIVATE_KEY` в .env
2. Убедитесь, что ключ начинается с `0x` или скрипт автоматически добавит
3. Включите debug для детальной диагностики:
   ```bash
   LOG_LEVEL=debug DEPLOY_ACTION=1 npx hardhat run scripts/deploy_full.js --network ganache
   ```

---

## 📝 Пример .env для Ganache

```bash
# Network Configuration
RPC_URL=http://127.0.0.1:7545
# или
WEB3_PROVIDER_URI=http://127.0.0.1:7545

# Deployer Configuration (Account 0 from Ganache)
DEPLOYER_PRIVATE_KEY=<ваш_приватный_ключ_из_ganache>
DEPLOYER_ADDRESS=0x62836d3c48751940e18ec199844b4ed408969ae5

# Seller Configuration (Account 1 from Ganache)
SELLER_PRIVATE_KEY=<ваш_приватный_ключ_селлера>
SELLER_ADDRESS=0x1da3f2664a7218adeffc428980b083f39dda2ab1

# Debug Logging (опционально)
LOG_LEVEL=debug
# или
DEBUG=1
```

---

## 🎯 Быстрая диагностика

```bash
# 1. Включите debug режим
LOG_LEVEL=debug DEPLOY_ACTION=1 npx hardhat run scripts/deploy_full.js --network ganache

# 2. Найдите в выводе:
#    - [DEBUG] RPC URL sources:  <- Проверка RPC
#    - [DEBUG] Private key sources:  <- Проверка ключа
#    - [DEBUG] Deployer information:  <- Адрес deployer'а
#    - [DEBUG] Balance and network check:  <- Баланс и сеть

# 3. Если баланс = 0:
#    - Проверьте адрес в Ganache
#    - Убедитесь, что правильный private key используется
#    - Проверьте, что Ganache запущен на правильном порту
```

---

## Bullrun Floou (`run-bullrun-floou.sh`): strict mode и summary

Запуск, режимы **local** / **remote**, файл **`scripts/floou-draft-request.json`**, переменные **`FLOOU_MODE`** и **`USER_ID`**, подхват **`wallet/mock-runner/.env`** — в **[bullrun-floou-manual.md](./bullrun-floou-manual.md)**.

Оркестратор в конце прогона печатает **structured summary** в двух форматах:

- блок `=== FLOOU_SUMMARY_JSON ===` — одна строка JSON, удобно копировать в отчёт или парсить в CI;
- блок `=== FLOOU_SUMMARY_PLAIN ===` — те же поля построчно.

Поля сводки:

| Поле | Смысл |
|------|--------|
| `draft_created` | HTTP 201 на POST `/activities/draft` |
| `crystalize_ok` | wallet-mock получил 200 от POST `.../crystalize` (см. маркер в `FLOOU_DONE_MARKER_FILE`) |
| `callback_ok` | подтверждение цепочки до `sign_contract` (в текущей архитектуре событие `sign_contract` возможно только после callback uploader → bot) |
| `submit_ok` | успешный POST `.../sign-requests/{id}/submit` и маркер `ok: true` |
| `tx_hash` | значение из ответа submit после broadcast (или mock-хэш на localhost) |

**Режим по умолчанию (мягкий):** как раньше — достаточно маркера `ok: true` в таймауте ожидания; сводка печатается для наблюдаемости, без дополнительных проверок.

**Strict mode:** включается флагом **`--strict`** или **`FLOOU_STRICT=true`** (также `1` / `yes`). После успешного маркера скрипт проверяет, что все этапы и `tx_hash` явно подтверждены; при несоответствии печатается `=== FLOOU_STRICT_FAIL ===` в stderr и **exit 1**. Нужен актуальный wallet-mock, который пишет расширенный JSON маркера (`crystalize_ok`, `callback_ok`, `submit_ok`, `tx_hash`).

При ошибках и таймаутах сводка тоже выводится, но strict-проверка **не** применяется (чтобы не дублировать код выхода).

Примеры:

```bash
./scripts/run-bullrun-floou.sh
FLOOU_STRICT=true ./scripts/run-bullrun-floou.sh
./scripts/run-bullrun-floou.sh --strict
```

**Полный текстовый протокол прогона** оркестратором `run-bullrun-floou.sh` (метаданные, хронология, stdout/stderr bot / uploader / wallet-mock) пишется в `scripts/logs/{S1}.{S2}.{S3}.{S4}.{S5}.{S6}-{ddMMyyyyHHmm}.txt` (локальное время). Отключить файл: `FLOOU_LOG_DISABLE=true`. Подробности — `scripts/docs/analysis/tasks/task-implement-run-full-floou-structured-log-artifact/decision-points-run-full-floou-structured-log.md`.

---

## 📚 См. также

- `scripts/docs/arweave-transaction-signing.md` — где в `deploy_full` / `upload_steps` подписывается Arweave-транзакция (JWK), пример на JS
- `scripts/docs/bullrun-floou-manual.md` — мануал по `run-bullrun-floou.sh`
- `hardhat.config.js` - конфигурация сетей
- `.env` - переменные окружения
- `scripts/lib/config/index.js` - логика загрузки конфигурации

