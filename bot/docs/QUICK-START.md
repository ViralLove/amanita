# 🚀 AMANITA Bot — Quick Start Guide

**Version**: 2.0  
**Date**: 2025-11-02  
**Status**: ✅ Production Ready (Phase 4 Complete)

---

## 📋 ОБЗОР

AMANITA Bot — это Telegram бот с интегрированным FastAPI сервером для работы с экосистемой AMANITA:
- 🤖 **Telegram Bot**: Пользовательский интерфейс (каталог, onboarding, продукты)
- 🌐 **FastAPI Server**: REST API для внешних интеграций
- 🔗 **Blockchain Integration**: Web3 для смарт-контрактов
- 📦 **Component Descriptions**: Rich локализованный контент из Arweave

---

## ⚡ БЫСТРЫЙ СТАРТ (5 минут)

### **Шаг 1: Клонировать и перейти в директорию**

```bash
cd /Users/eslinko/Development/Amanita/bot
```

---

### **Шаг 2: Установить зависимости**

```bash
# Создать virtual environment (если еще нет)
python3 -m venv venv

# Активировать venv
source venv/bin/activate

# Установить dependencies
pip install -r requirements.txt
```

**Что устанавливается**:
- `aiogram` — Telegram Bot Framework
- `fastapi` + `uvicorn` — Web server
- `web3` — Blockchain integration
- `aiohttp` — HTTP client для Arweave
- `python-dotenv` — Environment variables
- `pytest` — Testing framework
- И другие (см. requirements.txt)

---

### **Шаг 3: Настроить .env файл**

**Обязательные переменные**:

```bash
# bot/.env

# ============================================================================
# TELEGRAM BOT
# ============================================================================
TELEGRAM_BOT_TOKEN=your_bot_token_from_@BotFather

# ============================================================================
# BLOCKCHAIN (SINGLE SOURCE OF TRUTH)
# ============================================================================
MAGIC_REGISTRY_CONTRACT_ADDRESS=0x5FbDB2315678afecb367f032d93F642f64180aa3
# ☝️ ЭТО ЕДИНСТВЕННЫЙ hardcoded адрес контракта!
# Все остальные контракты загружаются через MagicRegistry.get()

WEB3_PROVIDER_URI=http://localhost:8545
BLOCKCHAIN_PROFILE=localhost

# ============================================================================
# SELLER CREDENTIALS
# ============================================================================
SELLER_PRIVATE_KEY=0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80
SELLER_ADDRESS=0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266

# ============================================================================
# WEBAPP
# ============================================================================
WALLET_APP_URL=https://your-ngrok-url.ngrok.io/

# ============================================================================
# ENVIRONMENT
# ============================================================================
ENVIRONMENT=local
LOAD_CATALOG=true
APP_ROOT_DIR=app
DEPLOYMENT_PROFILE=localhost

# ============================================================================
# LOGGING (optional)
# ============================================================================
LOG_LEVEL=INFO
LOG_FILE=logs/bot.log
```

---

### **Шаг 4: Запустить Hardhat Node (локальный blockchain)**

**В отдельном терминале**:

```bash
# Из корня проекта
cd /Users/eslinko/Development/Amanita

# Запустить Hardhat node
npx hardhat node

# Ожидаемый вывод:
# Started HTTP and WebSocket JSON-RPC server at http://127.0.0.1:8545/
# 
# Accounts
# ========
# Account #0: 0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266 (10000 ETH)
# Private Key: 0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80
```

**Важно**: Оставьте этот терминал открытым! Node должен работать постоянно.

---

### **Шаг 5: Деплой контрактов и инициализация seller (если еще не задеплоены)**

**Только если это ПЕРВЫЙ запуск или после рестарта Hardhat node**:

#### 5.1 Деплой контрактов

```bash
# Из корня проекта
cd /Users/eslinko/Development/Amanita

# Action 1: Deploy all contracts + register in MagicRegistry
DEPLOY_ACTION=1 npx hardhat run scripts/deploy_full.js --network localhost

# Ожидаемый вывод (в конце):
# MAGIC_REGISTRY_CONTRACT_ADDRESS=0x5FbDB2315678afecb367f032d93F642f64180aa3
# 
# ✅ All contracts deployed and registered in MagicRegistry
```

**Важно**: Скопируйте `MAGIC_REGISTRY_CONTRACT_ADDRESS` в `bot/.env`

#### 5.2 Создание рутовых инвайтов

```bash
# Создать директорию для инвайтов
mkdir -p bot/flowers

# Action 777: Generate root invites for deployer
DEPLOY_ACTION=777 npx hardhat run scripts/deploy_full.js --network localhost

# ✓ Проверка:
cat bot/flowers/deployer_invites_localhost.txt
# → Должно быть 12 инвайтов
```

**⚠️ ВАЖНО**: Скопируйте **ДВА РАЗНЫХ** инвайта для следующих шагов!

#### 5.3 Активация seller + загрузка компонентов

```bash
# Action 555: Activate seller + upload components
DEPLOY_ACTION=555 DEPLOYER_INVITE=<PASTE_INVITE_1_HERE> \
npx hardhat run scripts/deploy_full.js --network localhost

# Пример (используйте свой инвайт!):
# DEPLOY_ACTION=555 DEPLOYER_INVITE=AMANITA-3VQL-L08F npx hardhat run scripts/deploy_full.js --network localhost
```

**Результат**:
- ✅ Seller активирован
- ✅ Seller получил SELLER_ROLE
- ✅ Компоненты загружены в OrganicComponentRegistry

#### 5.4 🔑 Назначение ACTIVATOR_ROLE (КРИТИЧНО!)

```bash
# Action 9: Grant ACTIVATOR_ROLE to seller
DEPLOY_ACTION=9 npx hardhat run scripts/deploy_full.js --network localhost

# ✓ Ожидается в логах:
#   🔑 Назначаем ACTIVATOR_ROLE для: 0x70997970...
#   ✅ ACTIVATOR_ROLE назначена успешно
```

**⚠️ БЕЗ ЭТОГО ШАГА ОНБОРДИНГ НОВЫХ ПОЛЬЗОВАТЕЛЕЙ НЕ РАБОТАЕТ!**

Seller должен иметь `ACTIVATOR_ROLE` чтобы активировать пользователей через функцию `activateUser()`.

**Проверка ролей:**

```bash
# Action 13: Check seller diagnostics
DEPLOY_ACTION=13 npx hardhat run scripts/deploy_full.js --network localhost

# Ожидаемый вывод:
# 🔑 Роли:
#    SELLER_ROLE: ✅ Есть
#    ACTIVATOR_ROLE: ✅ Есть  ← ДОЛЖЕН БЫТЬ!
```

#### 5.5 Инициализация каталога

```bash
# Action 444: Initialize seller catalog
DEPLOY_ACTION=444 npx hardhat run scripts/deploy_full.js --network localhost
```

#### 5.6 Создание продуктов (опционально)

```bash
# Action 888: Full seller setup + create products
DEPLOY_ACTION=888 DEPLOYER_INVITE=<PASTE_INVITE_2_HERE> \
npx hardhat run scripts/deploy_full.js --network localhost

# ⚠️ ВАЖНО: Используйте ДРУГОЙ инвайт (не тот, что в 5.3)!
```

---

### **Шаг 6: Запустить бота**

**Вариант A: Через main.py** (Рекомендуется)

```bash
cd /Users/eslinko/Development/Amanita
export PYTHONPATH="."
python3 bot/main.py
```

**Вариант B: Через helper script**

```bash
cd /Users/eslinko/Development/Amanita
./run_debug_bot.sh
```

**Ожидаемый вывод**:

```
=== STARTING AMANITA BOT + API INITIALIZATION ===
[INFO] Загружаем .env из: /Users/eslinko/Development/Amanita/bot/.env
[INFO] Инициализация ServiceFactory...
[INFO] Создание экземпляра бота...
[INFO] Бот успешно создан: @your_bot_username
[INFO] Регистрация обработчиков...
[INFO] Все обработчики успешно зарегистрированы
[INFO] Запуск фоновой загрузки каталога продуктов...
[INFO] Создание FastAPI приложения...
[INFO] Запуск бота и API сервера параллельно...
[INFO] === AMANITA Bot + API Server запущены и готовы к работе ===

INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

✅ **Бот запущен!** Можете открывать Telegram и тестировать.

---

## 🔧 АРХИТЕКТУРА ЗАПУСКА

### **Что запускается**:

```
main.py
   ↓
├─ Telegram Bot (aiogram Dispatcher)
│  ├─ Polling бота
│  ├─ Handlers (onboarding, catalog, component_handlers)
│  └─ Middleware (localization, logging)
│
└─ FastAPI Server (uvicorn)
   ├─ REST API endpoints
   ├─ Health checks
   └─ Product/Component API

Parallel Launch: asyncio.gather(bot.polling, server.serve)
```

---

### **Используемые порты**:

```yaml
Telegram Bot: WebSocket to Telegram servers (no local port)
FastAPI Server: 
  - Default: 8000
  - Railway: $PORT (auto-assigned)
  
Health Check Endpoint: http://localhost:8000/health
```

---

## 📡 ПРОВЕРКА РАБОТОСПОСОБНОСТИ

### **1. Проверить Hardhat Node**

```bash
curl -X POST http://localhost:8545 \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"eth_blockNumber","params":[],"id":1}'

# Ожидаемый ответ:
# {"jsonrpc":"2.0","id":1,"result":"0x..."}
```

---

### **2. Проверить FastAPI Server**

```bash
curl http://localhost:8000/health

# Ожидаемый ответ:
# {"status": "healthy", "version": "1.0", ...}
```

---

### **3. Проверить Telegram Bot**

Откройте Telegram → найдите вашего бота → `/start`

**Ожидаемое поведение**:
- Бот отвечает приветственным сообщением
- Показывает кнопки (У меня есть приглашение / Я уже был здесь)

---

## 🎯 ОСНОВНЫЕ КОНФИГУРАЦИИ

### **MagicRegistry Pattern**:

```yaml
Architecture:
  MAGIC_REGISTRY_CONTRACT_ADDRESS: Единственный hardcoded адрес
  All other contracts: Loaded via registry.functions.get()
  
Contract Loading Flow:
  1. Load MagicRegistry from .env
  2. Call registry.functions.get("SpiralEngine")
  3. Load contract with returned address
  4. Repeat for all contracts

Benefits:
  ✅ Single source of truth
  ✅ Easy contract upgrades (update registry only)
  ✅ No hardcoded addresses in code
```

**Loaded Contracts** (via MagicRegistry):
- `SpiralEngine` — User activation, invite system
- `ProductRegistry` — Product catalog
- `OrganicComponentRegistry` — Component metadata
- `SoulIdentity` — Soulbound identity tokens

---

### **Environment Profiles**:

```yaml
DEPLOYMENT_PROFILE=localhost:
  Secrets: From .env file
  RPC: http://localhost:8545
  Storage: Arweave (testnet or mainnet)

DEPLOYMENT_PROFILE=polygon:
  Secrets: From HashiCorp Vault
  RPC: Polygon RPC URL
  Storage: Arweave mainnet
```

---

## 📁 СТРУКТУРА ПРОЕКТА

```
Amanita/
├── bot/
│   ├── main.py                    ← Entry point (Bot + API)
│   ├── config.py                  ← Configuration (loads .env)
│   ├── .env                       ← Environment variables
│   │
│   ├── handlers/                  ← Telegram handlers
│   │   ├── catalog/
│   │   │   ├── catalog_handlers.py
│   │   │   ├── product_handlers.py
│   │   │   └── component_handlers.py  ← NEW (Phase 4)
│   │   ├── onboarding_fsm.py
│   │   └── menu.py
│   │
│   ├── services/                  ← Business logic
│   │   ├── core/
│   │   │   └── blockchain.py      ← Blockchain integration
│   │   ├── product/
│   │   │   ├── assembler.py       ← Product assembly
│   │   │   ├── component_service.py  ← Component fetching
│   │   │   └── registry.py        ← Product registry
│   │   └── common/
│   │       └── localization.py
│   │
│   ├── api/                       ← FastAPI server
│   │   ├── main.py
│   │   ├── routes/
│   │   └── middleware/
│   │
│   ├── model/                     ← Data models
│   │   ├── product.py
│   │   ├── organic_component.py
│   │   └── component_description.py  ← NEW (Phase 4)
│   │
│   ├── templates/                 ← Localization (15 languages)
│   │   ├── ru.json
│   │   ├── en.json
│   │   └── ... (13 more)
│   │
│   └── tests/                     ← Test suite (627 tests)
│       ├── unit/
│       ├── integration/
│       └── api/
│
└── scripts/                       ← Deployment scripts
    └── deploy_full.js             ← Contract deployment
```

---

## 🧪 ТЕСТИРОВАНИЕ

### **Запуск всех тестов**:

```bash
cd /Users/eslinko/Development/Amanita/bot

# All tests
pytest

# Only unit tests
pytest tests/unit/

# Only integration tests
pytest tests/integration/

# Phase 4 tests (37 unit + 8 integration)
pytest tests/unit/test_product_formatter*.py
pytest tests/integration/test_product_formatter*.py

# With coverage
pytest --cov=services --cov=handlers --cov-report=html
```

---

### **Test Statistics**:

```yaml
Total_Tests: 627 tests
  Unit: 124 tests
  Integration: 43 tests
  API: ~130 tests
  Validation: ~150 tests
  Telegram: ~35 tests
  Other: ~145 tests

Phase_4_Tests: 45 tests
  Quality_Score: 9.7/10

Runtime: ~2-3 minutes (full suite)
```

---

## 🔍 TROUBLESHOOTING

### **Error: "Failed to connect to Web3"**

**Причина**: Hardhat node не запущен

**Решение**:
```bash
# В отдельном терминале
cd /Users/eslinko/Development/Amanita
npx hardhat node
```

---

### **Error: "MAGIC_REGISTRY_CONTRACT_ADDRESS не установлен"**

**Причина**: Отсутствует адрес в .env

**Решение**:
```bash
# Проверить .env
grep MAGIC_REGISTRY bot/.env

# Если пусто — задеплоить контракты
DEPLOY_ACTION=1 npx hardhat run scripts/deploy_full.js --network localhost

# Скопировать выведенный адрес в bot/.env:
# MAGIC_REGISTRY_CONTRACT_ADDRESS=0x5FbDB2315678afecb367f032d93F642f64180aa3
```

---

### **Error: "TELEGRAM_BOT_TOKEN not found"**

**Причина**: Нет токена бота

**Решение**:
1. Создайте бота через @BotFather в Telegram
2. Получите токен
3. Добавьте в `bot/.env`:
   ```
   TELEGRAM_BOT_TOKEN=123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11
   ```

---

### **Error: Module not found**

**Причина**: PYTHONPATH не установлен

**Решение**:
```bash
# Всегда запускайте из корня проекта с PYTHONPATH
cd /Users/eslinko/Development/Amanita
export PYTHONPATH="."
python3 bot/main.py
```

---

### **Bot запустился, но каталог пуст**

**Причина 1**: Каталог не загружен в blockchain

**Решение**:
```bash
# Загрузить каталог
cd /Users/eslinko/Development/Amanita
DEPLOY_ACTION=4 npx hardhat run scripts/deploy_full.js --network localhost
```

**Причина 2**: LOAD_CATALOG=false

**Решение**:
```bash
# В bot/.env установить:
LOAD_CATALOG=true
```

---

## 🌐 ЗАПУСК КОМПОНЕНТОВ

### **Только Telegram Bot** (без API):

Измените `bot/main.py`:

```python
# Вместо:
await asyncio.gather(
    dp.start_polling(bot),
    server.serve()
)

# Используйте:
await dp.start_polling(bot)
```

---

### **Только API Server** (без бота):

```bash
cd /Users/eslinko/Development/Amanita/bot
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

**API Endpoints**:
- `GET /health` — Health check
- `GET /api/products` — List products
- `GET /api/products/{id}` — Get product details
- `GET /api/components/{id}` — Get component details

---

## 📊 PRODUCTION DEPLOYMENT

### **Railway.app** (Рекомендуется):

**1. Подготовить переменные**:

```bash
# Railway Environment Variables
TELEGRAM_BOT_TOKEN=...
MAGIC_REGISTRY_CONTRACT_ADDRESS=0x...  # ← Polygon mainnet address
WEB3_PROVIDER_URI=https://polygon-rpc.com/
BLOCKCHAIN_PROFILE=polygon
DEPLOYMENT_PROFILE=polygon
ENVIRONMENT=prod

# Vault credentials (for polygon profile)
VAULT_ADDR=https://your-vault-server.com
VAULT_TOKEN=...
VAULT_PATH=secret/data/amanita
```

**2. Deploy**:

```bash
# Railway автоматически обнаружит Dockerfile
# И запустит: docker build → docker run
```

**3. Verify**:

```bash
# Health check
curl https://your-app.railway.app/health

# Logs
railway logs
```

---

### **Docker** (Manual):

```bash
cd /Users/eslinko/Development/Amanita/bot

# Build
docker build -t amanita-bot .

# Run
docker run -d \
  --name amanita-bot \
  --env-file .env \
  -p 8000:8000 \
  amanita-bot

# Logs
docker logs -f amanita-bot
```

---

## 🎨 FEATURES (Phase 4 Complete)

### **Component Descriptions** (NEW):

```yaml
Feature: Two-Stage UI для детальных описаний компонентов

SINGLE_Product:
  Display: 
    - Marker: "Монокомпонентный продукт"
    - Scientific title: "Amanita Muscaria"
    - Features: Top 5
    - Forms: All available
    - Buttons: 4 section buttons
      [🔬 Активные компоненты ]
      [🌿 Целительное действие]
      [🌀 Шаманская перспектива]
      [⚠️ Предостережения     ]

MULTI_Product:
  Display:
    - Marker: "Мультикомпонентный продукт (N)"
    - Components: List with separators
    - Adaptive features: 2-5 per component
    - Buttons: One per component
      [📖 Amanita Muscaria]
      [📖 Blue Lotus      ]
      
  Navigation:
    Component button → Menu (4 sections) → Section content
```

**Performance**:
- First load: ~1 second (Arweave fetch)
- Cached: ~0.2ms (instant!)
- Languages: 15 supported

---

## 📚 ДОПОЛНИТЕЛЬНАЯ ДОКУМЕНТАЦИЯ

### **Архитектура**:
- `bot/docs/tech/telegram/Technical Architecture.md` — Telegram bot architecture
- `bot/docs/tech/service/Services Architecture.md` — Services overview
- `bot/docs/tech/api/api.md` — API documentation
- `bot/docs/analysis/phase-4-final-architecture-and-plan.md` — Phase 4 implementation

### **Deployment**:
- `bot/docs/tech/railway-guide.md` — Railway deployment
- `bot/Dockerfile` — Docker configuration
- `scripts/quick_start_automation.md` — Full automation

### **Development**:
- `bot/docs/AIJournal.md` — Development history
- `bot/docs/tests/overview.md` — Testing guide
- `bot/docs/product/catalog_pipeline.md` — Catalog architecture

---

## 🎯 QUICK COMMANDS REFERENCE

```bash
# ============================================================================
# DEVELOPMENT
# ============================================================================

# Start Hardhat node (separate terminal)
npx hardhat node

# Deploy contracts (first time only)
DEPLOY_ACTION=1 npx hardhat run scripts/deploy_full.js --network localhost

# Start bot (development)
export PYTHONPATH="." && python3 bot/main.py

# Run tests
pytest

# Run specific test file
pytest tests/unit/test_product_formatter_type_detection.py

# Check linter
cd bot && python3 -m pylint handlers/common/formatting/product_formatter_service.py

# ============================================================================
# PRODUCTION
# ============================================================================

# Build Docker image
cd bot && docker build -t amanita-bot .

# Run in Docker
docker run -d --env-file .env -p 8000:8000 amanita-bot

# Deploy to Railway
railway up

# Check Railway logs
railway logs

# ============================================================================
# BLOCKCHAIN
# ============================================================================

# Deploy all contracts
DEPLOY_ACTION=1 npx hardhat run scripts/deploy_full.js --network localhost

# Mint invites for seller
DEPLOY_ACTION=777 npx hardhat run scripts/deploy_full.js --network localhost

# Activate seller
DEPLOY_ACTION=888 npx hardhat run scripts/deploy_full.js --network localhost

# Upload catalog
DEPLOY_ACTION=4 npx hardhat run scripts/deploy_full.js --network localhost

# ============================================================================
# DEBUGGING
# ============================================================================

# Enable debug logging
export LOG_LEVEL=DEBUG
python3 bot/main.py

# Check blockchain connection
cd bot && python3 test_connection.py

# Inspect MagicRegistry
cd /Users/eslinko/Development/Amanita
node -e "
const { ethers } = require('hardhat');
const MagicRegistry = require('./artifacts/contracts/MagicRegistry.sol/MagicRegistry.json');
(async () => {
  const provider = new ethers.JsonRpcProvider('http://localhost:8545');
  const registry = new ethers.Contract('0x5FbDB2315678afecb367f032d93F642f64180aa3', MagicRegistry.abi, provider);
  
  const contracts = ['SpiralEngine', 'ProductRegistry', 'OrganicComponentRegistry', 'SoulIdentity'];
  for (const name of contracts) {
    const addr = await registry.get(name);
    console.log(\`\${name}: \${addr}\`);
  }
})();
"
```

---

## ✅ УСПЕШНЫЙ ЗАПУСК

Вы успешно запустили AMANITA Bot если видите:

```
✅ Hardhat node running on http://localhost:8545
✅ Bot polling started (logs show "Бот успешно создан: @your_bot")
✅ API server running on http://0.0.0.0:8000
✅ Health check returns {"status": "healthy"}
✅ Telegram bot responds to /start
✅ Catalog loads (if LOAD_CATALOG=true)
✅ Products display with component descriptions
✅ Description buttons work (Phase 4)
```

---

## 🚀 NEXT STEPS

После успешного запуска:

1. **Test in Telegram**:
   - Open catalog
   - View SINGLE product → test 4 section buttons
   - View MULTI product → test component buttons
   - Test navigation between sections

2. **Review logs**:
   - Check `logs/bot.log` for any warnings
   - Verify no errors in startup

3. **Performance check**:
   - First component description load (~1 second expected)
   - Subsequent loads (instant, cached)

4. **Deploy to staging** (if tests pass):
   - Railway.app
   - With DEPLOYMENT_PROFILE=polygon

---

## 📞 SUPPORT

**Issues**:
- Check `bot/logs/bot.log`
- Enable DEBUG logging
- Review `bot/docs/AIJournal.md` for known issues

**Documentation**:
- Technical: `bot/docs/tech/`
- Product: `bot/docs/product/`
- Tests: `bot/docs/tests/`

---

**Guide Version**: 2.0  
**Last Updated**: 2025-11-02  
**Status**: ✅ Phase 4 Complete

