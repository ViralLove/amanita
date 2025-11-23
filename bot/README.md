# 🍄 AMANITA Telegram Bot

**Telegram Bot + FastAPI Server** для экосистемы AMANITA

**Version**: 2.0 (Phase 4 Complete)  
**Status**: ✅ Production Ready

---

## 🚀 QUICK START (5 минут)

```bash
# 1. Установить зависимости
cd /Users/eslinko/Development/Amanita/bot
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 2. Настроить .env (см. ниже)
cp .env.example .env  # Если есть example
nano .env  # Добавить TELEGRAM_BOT_TOKEN и MAGIC_REGISTRY_CONTRACT_ADDRESS

# 3. Запустить Hardhat node (в отдельном терминале)
cd /Users/eslinko/Development/Amanita
npx hardhat node

# 4. Деплой контрактов (только первый раз)
DEPLOY_ACTION=1 npx hardhat run scripts/deploy_full.js --network localhost

# 5. Запустить бота
cd /Users/eslinko/Development/Amanita
export PYTHONPATH="."
python3 bot/main.py
```

✅ **Готово!** Бот запущен на `http://0.0.0.0:8000`

📖 **Подробнее**: См. [`docs/QUICK-START.md`](docs/QUICK-START.md)

---

## 📋 МИНИМАЛЬНАЯ КОНФИГУРАЦИЯ (.env)

```bash
# ============================================================================
# ОБЯЗАТЕЛЬНЫЕ ПЕРЕМЕННЫЕ
# ============================================================================

# Telegram Bot Token (from @BotFather)
TELEGRAM_BOT_TOKEN=123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11

# MagicRegistry Contract Address (ЕДИНСТВЕННЫЙ hardcoded адрес!)
MAGIC_REGISTRY_CONTRACT_ADDRESS=0x5FbDB2315678afecb367f032d93F642f64180aa3

# Web3 RPC URL
WEB3_PROVIDER_URI=http://localhost:8545

# Seller Credentials (localhost default)
SELLER_PRIVATE_KEY=0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80
SELLER_ADDRESS=0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266

# Webapp URL (from ngrok or deployment)
WALLET_APP_URL=https://your-url.ngrok.io/

# ============================================================================
# ОПЦИОНАЛЬНЫЕ (defaults работают)
# ============================================================================

BLOCKCHAIN_PROFILE=localhost
ENVIRONMENT=local
LOAD_CATALOG=true
DEPLOYMENT_PROFILE=localhost
```

**⚠️ ВАЖНО**: 
- ✅ Только `MAGIC_REGISTRY_CONTRACT_ADDRESS` нужен как hardcoded
- ✅ Все остальные контракты загружаются через `registry.functions.get()`
- ❌ НЕ нужны `SPIRAL_ENGINE_PROXY_ADDRESS`, `PRODUCT_REGISTRY_PROXY_ADDRESS` и т.д.

---

## 🏗️ АРХИТЕКТУРА

```
┌─────────────────────────────────────────────────────────┐
│ main.py (Entry Point)                                   │
│ ┌─────────────────────────────────────────────────────┐ │
│ │ asyncio.gather(                                     │ │
│ │   ├─ Telegram Bot Polling                          │ │
│ │   │   ├─ Handlers (onboarding, catalog, products)  │ │
│ │   │   ├─ FSM (state machines)                      │ │
│ │   │   └─ Middleware (localization, logging)        │ │
│ │   │                                                 │ │
│ │   └─ FastAPI Server                                │ │
│ │       ├─ REST API Endpoints                        │ │
│ │       ├─ Health Checks                             │ │
│ │       └─ Dependency Injection                      │ │
│ │ )                                                   │ │
│ └─────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
              ↓                            ↓
    ┌──────────────────┐        ┌──────────────────┐
    │ BlockchainService│        │ ComponentService │
    │ (Web3)           │        │ (Arweave)        │
    └──────────────────┘        └──────────────────┘
              ↓                            ↓
    ┌──────────────────┐        ┌──────────────────┐
    │ MagicRegistry    │        │ OrganicComponent │
    │ (Smart Contract) │        │ Registry         │
    └──────────────────┘        └──────────────────┘
```

**Key Components**:
- **BlockchainService**: Singleton для Web3 operations
- **MagicRegistry**: Single source of truth для contract addresses
- **ComponentService**: Fetching component metadata from Arweave
- **ProductAssembler**: Enriches products with component data
- **ProductFormatterService**: Formats для Telegram UI

---

## 🎯 FEATURES

### **Phase 1-3** (Complete):
- ✅ Onboarding (activate via invite)
- ✅ Product catalog
- ✅ Component registry integration
- ✅ Blockchain integration (Web3)
- ✅ Arweave storage
- ✅ Multi-language support (15 languages)

### **Phase 4** (NEW — Just Completed):
- ✅ Type detection (SINGLE/MULTI products)
- ✅ Component formatting (scientific titles, features, forms)
- ✅ ComponentDescription fetching (nested CIDs from Arweave)
- ✅ Two-Stage UI (concise card + detailed sections on demand)
- ✅ Interactive navigation (inline keyboards)
- ✅ Localization (137 keys across 15 languages)

---

## 🧪 TESTING

```bash
# All tests (627 total)
pytest

# Unit tests only
pytest tests/unit/

# Phase 4 tests (45 tests, quality 9.7/10)
pytest tests/unit/test_product_formatter*.py
pytest tests/integration/test_product_formatter*.py

# With coverage
pytest --cov=services --cov=handlers --cov-report=html
open htmlcov/index.html
```

**Test Quality**: 9.7/10 (from test-qualification audit)

---

## 📂 PROJECT STRUCTURE

```
bot/
├── main.py                      # Entry point (Bot + API)
├── config.py                    # Configuration
├── .env                         # Environment variables
│
├── handlers/                    # Telegram handlers
│   ├── catalog/
│   │   ├── catalog_handlers.py
│   │   ├── product_handlers.py
│   │   └── component_handlers.py  # Phase 4: Description UI
│   ├── onboarding_fsm.py
│   └── menu.py
│
├── services/                    # Business logic
│   ├── core/
│   │   └── blockchain.py        # Web3 integration
│   ├── product/
│   │   ├── assembler.py         # Product assembly
│   │   ├── component_service.py # Arweave fetching
│   │   └── registry.py
│   └── common/
│       └── localization.py
│
├── api/                         # FastAPI server
│   ├── main.py
│   ├── routes/
│   └── middleware/
│
├── model/                       # Data models
│   ├── product.py
│   ├── organic_component.py
│   └── component_description.py # Phase 4: Rich descriptions
│
├── templates/                   # i18n (15 languages)
│   ├── ru.json
│   ├── en.json
│   └── ... (13 more)
│
├── tests/                       # 627 tests
│   ├── unit/
│   ├── integration/
│   └── api/
│
└── docs/                        # Documentation
    ├── QUICK-START.md           # This guide
    ├── AIJournal.md
    ├── tech/
    ├── product/
    └── analysis/
```

---

## 🌐 DEPLOYMENT PROFILES

### **localhost** (Development):

```yaml
DEPLOYMENT_PROFILE: localhost
RPC: http://localhost:8545 (Hardhat node)
Secrets: From .env file
Blockchain: Local network (chainId: 31337)
Storage: Arweave (testnet or mainnet)
```

### **polygon** (Production):

```yaml
DEPLOYMENT_PROFILE: polygon
RPC: https://polygon-rpc.com/ (Polygon mainnet)
Secrets: From HashiCorp Vault
Blockchain: Polygon (chainId: 137)
Storage: Arweave mainnet
```

---

## 📊 STATUS

```yaml
Code_Quality: ✅ 10/10 (zero linter errors)
Test_Coverage: ✅ 70% (627 tests)
Documentation: ✅ Comprehensive
Production_Ready: ✅ YES (after manual testing)

Phase_4_Implementation: ✅ COMPLETE (11/11 task groups)
  - Type detection
  - Component formatting
  - Description fetching
  - Two-Stage UI
  - Interactive navigation
  - 45 tests (9.7/10 quality)
```

---

## 🔗 LINKS

- **Documentation**: [`docs/`](docs/)
- **Quick Start**: [`docs/QUICK-START.md`](docs/QUICK-START.md)
- **Architecture**: [`docs/tech/telegram/Technical Architecture.md`](docs/tech/telegram/Technical%20Architecture.md)
- **API Docs**: [`api/README.md`](api/README.md)
- **Tests**: [`tests/`](tests/)

---

## 🛠️ DEVELOPMENT

```bash
# Install dev dependencies
pip install pytest pytest-cov pylint black

# Format code
black .

# Lint
pylint handlers/ services/ api/

# Type checking
mypy .

# Run tests with coverage
pytest --cov=. --cov-report=html
```

---

## 📞 SUPPORT

**Issues**: См. `docs/AIJournal.md` для known issues  
**Logs**: `logs/bot.log`  
**Debug**: `LOG_LEVEL=DEBUG python3 bot/main.py`

---

**Built with**: Python 3.11, aiogram, FastAPI, Web3.py, Arweave  
**Blockchain**: Ethereum-compatible (Hardhat, Polygon)  
**Storage**: Arweave (decentralized)  
**License**: See LICENSE file

