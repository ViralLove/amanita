# Инфраструктура интеграционных тестов

## 📋 Обзор

Документ описывает инфраструктуру для запуска интеграционных тестов в bot слое, включая:
- Порядок деплоя смарт-контрактов
- Переменные окружения
- Процесс инициализации
- Проверку работоспособности

**Важно:** Интеграционные тесты используют реальный блокчейн (Hardhat node) и требуют предварительного деплоя контрактов.

---

## 🏗️ Архитектура деплоя контрактов

### Порядок деплоя (Action 1)

При выполнении `DEPLOY_ACTION=1` контракты деплоятся в следующем порядке:

```
1. MagicRegistry (не UUPS)
   ↓ Центральный реестр всех контрактов
   
2. SpiralEngine (UUPS)
   ↓ Система инвайт-кодов
   ↓ Регистрируется в MagicRegistry
   
3. SBT Экосистема (не UUPS):
   - SoulboundCore
   - SoulMetadata (зависит от SoulboundCore)
   - SoulRecovery (зависит от SoulboundCore)
   - SoulIntegration (зависит от SpiralEngine + SoulboundCore)
   - SoulIdentity (зависит от SoulboundCore + SoulMetadata)
   ↓ Все регистрируются в MagicRegistry
   
4. ProductRegistry (UUPS)
   ↓ Каталог продуктов
   ↓ Регистрируется в MagicRegistry
   
5. OrganicComponentRegistry (UUPS)
   ↓ Реестр органических компонентов
   ↓ Регистрируется в MagicRegistry
   
6. AmanitaInternational (UUPS)
   ↓ Система локализации (complex/simple fields)
   ↓ Регистрируется в MagicRegistry
   
7. Setup System Connections
   ↓ Настройка связей между контрактами
```

### UUPS Архитектура

**Важно:** Для UUPS контрактов деплоятся два компонента:

1. **Logic Implementation** - содержит бизнес-логику (может обновляться)
2. **Proxy** - точка входа, хранит state (адрес фиксирован)

**Использование:**
- ✅ **Всегда используйте Proxy адрес** для взаимодействия
- ✅ **Logic адрес** нужен только для upgrade операций
- ✅ **MagicRegistry** содержит только Proxy адреса

**Контракты с UUPS:**
- `SpiralEngine` → `SPIRAL_ENGINE_PROXY_ADDRESS`
- `ProductRegistry` → `PRODUCT_REGISTRY_PROXY_ADDRESS`
- `OrganicComponentRegistry` → `ORGANIC_COMPONENT_REGISTRY_PROXY_ADDRESS`
- `AmanitaInternational` → `AMANITA_INTERNATIONAL_PROXY_ADDRESS`

---

## 🔧 Переменные окружения

### Обязательные переменные (bot/.env)

#### 1. Блокчейн подключение

```bash
# RPC URL для подключения к Hardhat node
WEB3_PROVIDER_URI=http://localhost:8545

# Профиль блокчейна
BLOCKCHAIN_PROFILE=localhost
```

#### 2. Центральный реестр контрактов

```bash
# ⚠️ ВАЖНО: Только MAGIC_REGISTRY_CONTRACT_ADDRESS нужен как hardcoded!
# Все остальные контракты (SpiralEngine, ProductRegistry, etc.) 
# загружаются автоматически через registry.functions.get()

MAGIC_REGISTRY_CONTRACT_ADDRESS=0x5FbDB2315678afecb367f032d93F642f64180aa3
```

**Как это работает:**
```python
# bot/services/core/blockchain.py
# 1. Загружается MagicRegistry по адресу MAGIC_REGISTRY_CONTRACT_ADDRESS
# 2. Через registry.functions.get("ProductRegistry").call() получается адрес ProductRegistry
# 3. Аналогично для других контрактов:
#    - SpiralEngine
#    - OrganicComponentRegistry
#    - SoulIdentity
#    - AmanitaInternational
```

#### 3. Приватные ключи

```bash
# Приватный ключ продавца (для подписи транзакций в тестах)
SELLER_PRIVATE_KEY=0x59c6995e998f97a5a0044966f0945389dc9e86dae88c7a8412f4603b6b78690d

# Адрес продавца (соответствует SELLER_PRIVATE_KEY)
SELLER_ADDRESS=0x70997970C51812dc3A010C7d01b50e0d17dc79C8

# Приватный ключ деплоера (для деплоя контрактов)
DEPLOYER_PRIVATE_KEY=0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80
```

**Примечание:** Для localhost Hardhat node используются стандартные тестовые аккаунты:
- Account #0 (DEPLOYER): `0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80`
- Account #1 (SELLER): `0x59c6995e998f97a5a0044966f0945389dc9e86dae88c7a8412f4603b6b78690d`

#### 4. Storage (опционально, для тестов с реальным IPFS/Arweave)

```bash
# Тип хранилища (mock/pinata/arweave)
INTEGRATION_STORAGE=mock

# Для Pinata (если INTEGRATION_STORAGE=pinata)
PINATA_API_KEY=...
PINATA_API_SECRET=...
PINATA_JWT=...

# Для Arweave (если INTEGRATION_STORAGE=arweave)
ARWEAVE_PRIVATE_KEY=...
```

### Сводная таблица переменных окружения

| Переменная | Обязательная | Описание | Пример значения |
|-----------|--------------|----------|-----------------|
| `WEB3_PROVIDER_URI` | ✅ Да | RPC URL для Hardhat node | `http://localhost:8545` |
| `MAGIC_REGISTRY_CONTRACT_ADDRESS` | ✅ Да | Адрес центрального реестра | `0x5FbDB2315678afecb367f032d93F642f64180aa3` |
| `SELLER_PRIVATE_KEY` | ✅ Да | Приватный ключ продавца | `0x59c6995e998f97a5a0044966f0945389dc9e86dae88c7a8412f4603b6b78690d` |
| `SELLER_ADDRESS` | ✅ Да | Адрес продавца | `0x70997970C51812dc3A010C7d01b50e0d17dc79C8` |
| `DEPLOYER_PRIVATE_KEY` | ⚠️ Для деплоя | Приватный ключ деплоера | `0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80` |
| `INTEGRATION_STORAGE` | ❌ Нет | Тип хранилища (mock/pinata/arweave) | `mock` |
| `PINATA_API_KEY` | ⚠️ Если storage=pinata | API ключ Pinata | - |
| `ARWEAVE_PRIVATE_KEY` | ⚠️ Если storage=arweave | Приватный ключ Arweave | - |

---

## 🧩 Фикстуры для интеграционных тестов

### `seller_address`

Фикстура для получения адреса селлера как строки. Используется во всех интеграционных тестах для единообразного доступа к адресу селлера.

**Тип возврата:** `str` (Ethereum адрес в lowercase)

**Источники адреса (в порядке приоритета):**

1. **SELLER_ADDRESS env var** (приоритет 1)
   - Если переменная окружения `SELLER_ADDRESS` установлена, используется её значение

2. **seller_account.address** (приоритет 2)
   - Если фикстура `seller_account` доступна (требует `SELLER_PRIVATE_KEY`), используется адрес из неё

3. **SELLER_PRIVATE_KEY → Account** (приоритет 3)
   - Если `SELLER_PRIVATE_KEY` установлен, создаётся `Account` и извлекается адрес

4. **Hardcoded fallback** (приоритет 4)
   - Fallback для localhost: `0x70997970c51812dc3a010c7d01b50e0d17dc79c8` (Hardhat Account #1)

**Проверка соответствия:**

Фикстура автоматически проверяет соответствие между `SELLER_ADDRESS` и `seller_account.address` (если оба доступны). При несоответствии выводится предупреждение, но тест продолжает работать, используя `SELLER_ADDRESS` (приоритет 1).

**Использование:**

```python
def test_example(seller_address):
    """Тест с использованием фикстуры seller_address"""
    assert seller_address.startswith("0x")
    assert len(seller_address) == 42
    assert seller_address == "0x70997970c51812dc3a010c7d01b50e0d17dc79c8"
    
    # Использование в тестах
    result = some_service.get_products_by_seller(seller_address)
    assert result is not None
```

**Преимущества:**

- ✅ Единая точка истины для адреса селлера
- ✅ Не требует `SELLER_PRIVATE_KEY` (может использовать `SELLER_ADDRESS` или fallback)
- ✅ Автоматическая нормализация к lowercase
- ✅ Логирование источника адреса для отладки
- ✅ Предупреждение при несоответствии адресов

**Связанные фикстуры:**

- `seller_account` — возвращает объект `Account` из `eth_account` (требует `SELLER_PRIVATE_KEY`)
- `integration_registry_service_real_full` — использует `seller_address` для проверок и логирования

---

### Фикстура `integration_registry_service_real_full`

**Назначение:**
Фикстура для создания `ProductRegistryService` с ПОЛНОСТЬЮ реальными сервисами (блокчейн, Arweave, validation, account).

**Использует:**
- ✅ Реальный `BlockchainService` (Hardhat node)
- ✅ Реальный `ArWeaveUploader`, обернутый в `ProductStorageService`
- ✅ Реальный `ProductValidationService`
- ✅ Реальный `AccountService`
- ✅ Реальный `ProductAssembler` и `ComponentService`

**Требования:**
- `SELLER_PRIVATE_KEY` в `.env`
- `ARWEAVE_PRIVATE_KEY` в `.env`
- Запущенный Hardhat node на `localhost:8545`

**Использование:**
```python
@pytest.mark.asyncio
async def test_example(integration_registry_service_real_full):
    products = await integration_registry_service_real_full.get_all_products()
    assert len(products) > 0
```

**Особенности:**
- Фикстура пропускает тест (`pytest.skip`) с понятным сообщением, если сервисы недоступны
- Рекомендуется использовать вместе с `real_catalog_products` для получения реальных продуктов
- Подходит для интеграционных тестов, где нужны реальные данные селлера

**Связанные фикстуры:**
- `seller_address` — для получения адреса селлера
- `real_catalog_products` — для получения реальных продуктов из контракта

---

### Фикстура `real_catalog_products`

**Назначение:**
Фикстура для получения реальных продуктов из контракта `ProductRegistry`. Используется в интеграционных тестах для работы с реальными данными, загруженными через Action 444.

**Зависимости:**
- `integration_registry_service_real_full` — сервис для доступа к контракту
- `seller_address` — адрес селлера для фильтрации продуктов (если необходимо)

**Тип возврата:** `List[Product]` — список реальных продуктов из контракта

**Источник данных:**
- Продукты, загруженные через Action 444
- Получаются через `get_all_products()`
- Фильтруются по `seller_address` (если необходимо)

**Требования:**
- Action 444 должен быть выполнен заранее
- В контракте должно быть продуктов (ожидается 17 после Action 444)
- Hardhat node должен быть запущен
- Контракты должны быть задеплоены

**Использование:**
```python
@pytest.mark.asyncio
async def test_example(real_catalog_products):
    """Тест с использованием реальных продуктов из контракта"""
    # Проверяем наличие продуктов
    assert len(real_catalog_products) > 0, "Должны быть продукты в контракте"
    
    # Используем первый продукт для тестирования
    product = real_catalog_products[0]
    assert product.business_id is not None
    assert product.blockchain_id is not None
    assert product.status is not None
```

**Особенности:**
- Фикстура автоматически фильтрует продукты по `seller_address` (если поле доступно)
- Выводит предупреждение, если количество продуктов не соответствует ожидаемому (17 после Action 444)
- Тест будет пропущен (`pytest.skip`), если продуктов нет в контракте
- Возвращает список объектов `Product` с полной информацией из блокчейна

**Ожидаемое количество продуктов:**
- После Action 444: 17 продуктов
- Если количество отличается — выводится предупреждение, но тест продолжается

**Связанные фикстуры:**
- `integration_registry_service_real_full` — используется для получения продуктов
- `seller_address` — используется для фильтрации продуктов

**Примечание:**
Эта фикстура заменяет устаревшую `integration_test_data`, которая загружала данные из файла `fixtures/products.json`. Теперь используется реальный каталог из блокчейна.

---

## 🚀 Процесс инициализации

### ⚠️ КРИТИЧНО: Тесты НЕ деплоят контракты сами!

**Интеграционные тесты только ИСПОЛЬЗУЮТ уже задеплоенные контракты.**

Они:
- ✅ Подключаются к уже задеплоенным контрактам через `BlockchainService()`
- ✅ Читают данные из контрактов
- ✅ Вызывают методы контрактов
- ❌ **НЕ деплоят контракты сами**

**Вывод:** Контракты нужно деплоить **ЗАРАНЕЕ**, до запуска тестов.

### Шаг 1: Запуск Hardhat node

```bash
# Terminal 1: Запуск локальной ноды
cd /Users/eslinko/Development/Amanita
npx hardhat node

# Проверка:
lsof -ti:8545
# Должен вернуть PID процесса
```

### Шаг 2: Деплой контрактов (Action 1) - ОБЯЗАТЕЛЬНО ПЕРЕД ТЕСТАМИ

```bash
# Terminal 2: Деплой всех контрактов
cd /Users/eslinko/Development/Amanita

# Деплой контрактов (ОБЯЗАТЕЛЬНО перед запуском тестов!)
DEPLOY_ACTION=1 npx hardhat run scripts/deploy_full.js --network localhost
```

**Что происходит:**
1. Деплоится `MagicRegistry` (центральный реестр)
2. Деплоятся все остальные контракты в правильном порядке
3. Все контракты регистрируются в `MagicRegistry`
4. Адреса контрактов выводятся в консоль

**Важно:** После деплоя скрипт автоматически обновит `.env` с правильными адресами (если настроено).

### Шаг 3: Проверка переменных окружения

```bash
# Проверка обязательных переменных
cd /Users/eslinko/Development/Amanita/bot

grep MAGIC_REGISTRY_CONTRACT_ADDRESS .env
grep SELLER_PRIVATE_KEY .env
grep SELLER_ADDRESS .env
grep WEB3_PROVIDER_URI .env
```

**Должно быть:**
```bash
MAGIC_REGISTRY_CONTRACT_ADDRESS=0x5FbDB2315678afecb367f032d93F642f64180aa3
SELLER_PRIVATE_KEY=0x59c6995e998f97a5a0044966f0945389dc9e86dae88c7a8412f4603b6b78690d
SELLER_ADDRESS=0x70997970C51812dc3A010C7d01b50e0d17dc79C8
WEB3_PROVIDER_URI=http://localhost:8545
```

### Шаг 4: Запуск интеграционных тестов

```bash
# Запуск интеграционных тестов
cd /Users/eslinko/Development/Amanita/bot
pytest tests/test_product_registry_integration.py -v
```

---

## 📋 Контракты, используемые в bot слое

### Как загружаются контракты

**Код в `bot/services/core/blockchain.py`:**

```python
def _load_contracts(self) -> Dict[str, Any]:
    """Загружает все контракты из реестра"""
    contracts = {}
    
    # Получаем список всех контрактов из реестра
    contract_names = [
        "SpiralEngine",
        "ProductRegistry",
        "OrganicComponentRegistry",
        "SoulIdentity",
        "AmanitaInternational"
    ]
    
    for name in contract_names:
        # Получаем адрес контракта из реестра
        address = self.registry.functions.get(name).call()
        
        # Загружаем ABI
        abi = load_abi(name)
        
        # Создаем контракт
        contract = self.web3.eth.contract(
            address=address,
            abi=abi
        )
        
        contracts[name] = contract
```

### Контракты, используемые в интеграционных тестах

#### 1. ProductRegistry

**Назначение:** Каталог продуктов продавцов

**Использование в тестах:**
- `get_all_products()` - получение всех продуктов
- `get_product(blockchain_id)` - получение продукта по ID
- `create_product()` - создание продукта
- `update_product_status()` - обновление статуса продукта

**Загрузка:**
```python
contract = blockchain_service.get_contract("ProductRegistry")
```

#### 2. AmanitaInternational

**Назначение:** Система локализации (complex/simple fields)

**Использование в тестах:**
- `getSimpleFieldCID()` - получение CID для простых полей
- `setSimpleFieldCID()` - установка CID для простых полей
- `getComplexFieldCID()` - получение CID для complex полей
- `setComplexFieldCID()` - установка CID для complex полей

**Загрузка:**
```python
contract = blockchain_service.get_contract("AmanitaInternational")
```

#### 3. MagicRegistry

**Назначение:** Центральный реестр всех контрактов

**Использование:**
- Автоматическая загрузка адресов других контрактов
- Не используется напрямую в тестах

**Загрузка:**
```python
# Загружается автоматически при инициализации BlockchainService
registry = blockchain_service.registry
```

---

## 🔍 Проверка инфраструктуры

### Проверка Hardhat node

```bash
# Проверка доступности Hardhat node
curl -X POST http://localhost:8545 \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"eth_blockNumber","params":[],"id":1}'
```

**Ожидаемый результат:**
```json
{"jsonrpc":"2.0","id":1,"result":"0x..."}
```

### Проверка контрактов через Python

```python
from bot.services.core.blockchain import BlockchainService

# Инициализация
blockchain = BlockchainService()

# Проверка подключения
assert blockchain.web3.is_connected()

# Проверка загрузки контрактов
contracts = ["SpiralEngine", "ProductRegistry", "AmanitaInternational"]
for name in contracts:
    contract = blockchain.get_contract(name)
    assert contract is not None, f"Контракт {name} не загружен"
    print(f"✅ {name}: {contract.address}")
```

### Проверка переменных окружения

```python
import os
from dotenv import load_dotenv

load_dotenv("bot/.env")

required_vars = [
    "MAGIC_REGISTRY_CONTRACT_ADDRESS",
    "SELLER_PRIVATE_KEY",
    "SELLER_ADDRESS",
    "WEB3_PROVIDER_URI"
]

for var in required_vars:
    value = os.getenv(var)
    if value:
        print(f"✅ {var}: {value[:20]}...")
    else:
        print(f"❌ {var}: НЕ УСТАНОВЛЕН")
```

---

## ✅ Чеклист перед запуском интеграционных тестов

**⚠️ КРИТИЧНО:** Контракты должны быть задеплоены **ДО** запуска тестов!

- [ ] Hardhat node запущен (`npx hardhat node`)
- [ ] **Контракты задеплоены** (`DEPLOY_ACTION=1 npx hardhat run scripts/deploy_full.js --network localhost`) - **ОБЯЗАТЕЛЬНО!**
- [ ] `MAGIC_REGISTRY_CONTRACT_ADDRESS` установлен в `.env` (после деплоя)
- [ ] `SELLER_PRIVATE_KEY` установлен в `.env`
- [ ] `SELLER_ADDRESS` установлен в `.env`
- [ ] `WEB3_PROVIDER_URI` установлен в `.env` (указывает на `http://localhost:8545`)
- [ ] `DEPLOYER_PRIVATE_KEY` установлен (для деплоя контрактов)
- [ ] Проверено подключение к Hardhat node
- [ ] Проверена загрузка контрактов через `BlockchainService`

---

## 🎯 Ключевые моменты

1. **Инфраструктура деплоя:**
   - Контракты деплоятся в правильном порядке через `deploy_full.js`
   - Все контракты регистрируются в `MagicRegistry`
   - UUPS контракты деплоятся как Logic + Proxy

2. **Переменные окружения:**
   - Только `MAGIC_REGISTRY_CONTRACT_ADDRESS` нужен как hardcoded
   - Остальные контракты загружаются автоматически через реестр
   - `SELLER_PRIVATE_KEY` и `SELLER_ADDRESS` обязательны для тестов

3. **Процесс инициализации:**
   - Запуск Hardhat node
   - **Деплой контрактов (Action 1) - ОБЯЗАТЕЛЬНО ПЕРЕД ТЕСТАМИ**
   - Проверка переменных окружения
   - Запуск тестов

4. **⚠️ КРИТИЧНО:**
   - **Тесты НЕ деплоят контракты сами**
   - **Контракты нужно деплоить ЗАРАНЕЕ**
   - **Тесты только ИСПОЛЬЗУЮТ уже задеплоенные контракты**

---

## 📚 Связанные документы

- `bot/docs/tests/registry.md` - Тестирование ProductRegistryService
- `bot/docs/tests/QUICK_START_TESTING.txt` - Быстрый старт тестирования
- `scripts/docs/Deploy_Full.md` - Детальная документация по деплою контрактов

