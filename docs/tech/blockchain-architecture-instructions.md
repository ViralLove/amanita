# Архитектурные инструкции: Система смарт-контрактов с Python-слоем

## Обзор архитектуры

Данный документ описывает архитектуру системы смарт-контрактов Amanita с Python-слоем интеграции. Система построена на принципах модульности, централизованного управления контрактами и универсального Python-интерфейса.

## 1. Инфраструктура Hardhat

### 1.1 Структура проекта
```
project/
├── contracts/           # Смарт-контракты Solidity
├── scripts/            # Скрипты деплоя
├── test/               # Тесты контрактов
├── artifacts/          # Скомпилированные контракты (генерируется)
├── cache/              # Кэш Hardhat (генерируется)
├── hardhat.config.js   # Конфигурация Hardhat
├── package.json        # Зависимости Node.js
└── .env                # Переменные окружения
```

### 1.2 Конфигурация Hardhat (hardhat.config.js)

```javascript
require("@nomicfoundation/hardhat-toolbox");
require("dotenv").config();

module.exports = {
  defaultNetwork: 'localhost',
  solidity: {
    version: "0.8.20",
    settings: {
      optimizer: {
        enabled: true,
        runs: 200
      }
    }
  },
  networks: {
    localhost: {
      url: "http://localhost:8545",
      chainId: 31337,
      gasPrice: "auto",
      accounts: [process.env.DEPLOYER_PRIVATE_KEY]
    },
    polygon: {
      url: process.env.POLYGON_MAINNET_RPC,
      accounts: [process.env.DEPLOYER_PRIVATE_KEY],
      chainId: 137
    },
    mumbai: {
      url: process.env.POLYGON_MUMBAI_RPC,
      accounts: [process.env.DEPLOYER_PRIVATE_KEY],
      chainId: 80001
    }
  },
  etherscan: {
    apiKey: {
      polygon: process.env.POLYGONSCAN_API_KEY,
      polygonMumbai: process.env.POLYGONSCAN_API_KEY
    }
  },
  paths: {
    sources: "./contracts",
    tests: "./test",
    cache: "./cache",
    artifacts: "./artifacts"
  }
};
```

### 1.3 Зависимости (package.json)

```json
{
  "name": "hardhat-project",
  "scripts": {
    "deploy:registry": "hardhat run scripts/deploy_full.js 0",
    "deploy:all": "hardhat run scripts/deploy_full.js 1",
    "deploy:contracts": "hardhat run scripts/deploy_full.js 2",
    "deploy:invites": "hardhat run scripts/deploy_full.js 3",
    "deploy:catalog": "hardhat run scripts/deploy_full.js 4"
  },
  "devDependencies": {
    "@nomicfoundation/hardhat-toolbox": "^5.0.0",
    "hardhat": "^2.25.0"
  },
  "dependencies": {
    "@openzeppelin/contracts": "^5.3.0"
  }
}
```

### 1.4 Переменные окружения (.env)

```bash
# Ключи для деплоя
DEPLOYER_PRIVATE_KEY=0x...
SELLER_PRIVATE_KEY=0x...

# RPC URLs
POLYGON_MAINNET_RPC=https://...
POLYGON_MUMBAI_RPC=https://...

# API ключи для верификации
POLYGONSCAN_API_KEY=...

# Адрес реестра (генерируется после деплоя)
AMANITA_REGISTRY_CONTRACT_ADDRESS=0x...
```

## 2. Архитектура смарт-контрактов

### 2.1 Центральный реестр (AmanitaRegistry)

**Назначение**: Централизованное хранение адресов всех контрактов экосистемы.

**Ключевые функции**:
- `setAddress(name, address)` - установка адреса контракта
- `getAddress(name)` - получение адреса по имени
- `getAllContractNames()` - список всех контрактов

**Принципы**:
- Только owner может изменять адреса
- Имена контрактов должны быть уникальными
- Адреса не могут быть нулевыми

### 2.2 Контракт инвайтов (InviteNFT)

**Назначение**: Управление системой приглашений через NFT.

**Ключевые функции**:
- `mintInvites(codes, expiry)` - минтинг инвайтов
- `activateInvite(code, user)` - активация инвайта
- `validateInviteCode(code)` - валидация инвайта
- `isUserActivated(user)` - проверка активации пользователя
- `isSeller(user)` - проверка роли продавца

**Структуры данных**:
- `inviteCodeToTokenId` - маппинг код → tokenId
- `isInviteUsed` - маппинг tokenId → использован ли
- `userInvites` - маппинг пользователь → список инвайтов

### 2.3 Реестр продуктов (ProductRegistry)

**Назначение**: Хранение каталога продуктов с IPFS-ссылками.

**Ключевые функции**:
- `createProduct(ipfsCID)` - создание продукта
- `activateProduct(productId)` - активация продукта
- `deactivateProduct(productId)` - деактивация продукта
- `getProduct(productId)` - получение продукта
- `getProductsBySellerFull()` - продукты продавца

**Структура Product**:
```solidity
struct Product {
    uint256 id;          // Уникальный ID
    address seller;      // Адрес продавца
    string ipfsCID;      // IPFS CID метаданных
    bool active;         // Активен ли продукт
}
```

## 3. Python-слой интеграции

### 3.1 Архитектура BlockchainService

**Принципы**:
- Синглтон паттерн для единого экземпляра
- Автоматическая загрузка контрактов из реестра
- Универсальные методы для работы с контрактами
- Обработка ошибок и fallback-значения

### 3.2 Структура сервиса

```python
class BlockchainService:
    """Сервис для работы с блокчейном - реализован как синглтон"""
    
    _instance = None
    
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, '_initialized'):
            self.web3 = self._init_web3()
            self.chain_id = self.web3.eth.chain_id
            self.registry = self._load_registry_contract()
            self.contracts = self._load_contracts()
            self.seller_key = SELLER_PRIVATE_KEY
            self.seller_account = Account.from_key(SELLER_PRIVATE_KEY)
            self._initialized = True
```

### 3.3 Ключевые методы

#### Инициализация и загрузка
- `_init_web3()` - подключение к Web3
- `_load_registry_contract()` - загрузка реестра
- `_load_contracts()` - загрузка всех контрактов из реестра

#### Работа с контрактами
- `get_contract(name)` - получение контракта по имени
- `call_contract_function(name, func, *args)` - вызов read-only функций
- `transact_contract_function(name, func, private_key, *args)` - вызов с транзакцией

#### Специализированные методы
- `validate_invite_code(code)` - валидация инвайта
- `create_product(ipfs_cid)` - создание продукта
- `set_product_active(product_id, is_active)` - управление активностью

### 3.4 Загрузка ABI

**Принципы**:
- Поддержка форматов Hardhat и плоской структуры
- Автоматическое определение пути к ABI
- Подробное логирование процесса загрузки

```python
def load_abi(contract_name):
    hh_path = os.path.join(ABI_BASE_DIR, f"{contract_name}.sol", f"{contract_name}.json")
    flat_path = os.path.join(ABI_BASE_DIR, f"{contract_name}.json")
    
    if os.path.exists(hh_path):
        abi_path = hh_path
    elif os.path.exists(flat_path):
        abi_path = flat_path
    else:
        raise FileNotFoundError(f"ABI-файл для {contract_name} не найден")
    
    with open(abi_path, "r") as f:
        abi_data = json.load(f)
        return abi_data.get("abi", abi_data)
```

## 4. Система тестирования

### 4.1 Структура тестов

```
tests/
├── conftest.py                    # Центральные фикстуры
├── test_blockchain.py            # Тесты BlockchainService
├── test_product_registry_unit.py # Unit-тесты продуктов
├── test_product_registry_integration.py # Интеграционные тесты
└── fixtures/                     # Тестовые данные
```

### 4.2 Фикстуры и моки

**Принципы**:
- Мокирование только blockchain-слоя
- Реальные тесты для бизнес-логики
- Фикстуры для изоляции тестов

```python
@pytest.fixture
def mock_blockchain_service(monkeypatch):
    """Мок для BlockchainService (только для unit-тестов продуктов)"""
    
    class MockBlockchainService:
        def __init__(self):
            self._next_blockchain_id = 1
            self.product_statuses = {}
            self.product_cids = {}
        
        def _generate_next_blockchain_id(self):
            next_id = self._next_blockchain_id
            self._next_blockchain_id += 1
            return next_id
```

### 4.3 Типы тестов

#### Unit-тесты
- Тестирование бизнес-логики без blockchain
- Мокирование внешних зависимостей
- Быстрое выполнение

#### Интеграционные тесты
- Тестирование с реальными контрактами
- Проверка end-to-end сценариев
- Использование локальной сети Hardhat

## 5. Процесс развертывания

### 5.1 Последовательность деплоя

1. **Деплой реестра** (`action=0`)
   - Создание AmanitaRegistry
   - Сохранение адреса в .env

2. **Деплой всех контрактов** (`action=1`)
   - Создание InviteNFT и ProductRegistry
   - Регистрация в реестре
   - Настройка ролей

3. **Генерация инвайтов** (`action=3`)
   - Минтинг 88 инвайтов
   - Сохранение в файл

4. **Загрузка каталога** (`action=4`)
   - Создание продуктов из JSON
   - Проверка корректности

### 5.2 Скрипт деплоя (deploy_full.js)

**Ключевые функции**:
- `deployContract(name, args, options)` - универсальный деплой
- `setupSellerRole(inviteNFT)` - настройка ролей
- `creatingInvites(inviteNFT)` - генерация инвайтов
- `createCatalog(productRegistry)` - загрузка каталога

## 6. Конфигурация Python

### 6.1 Переменные окружения

```python
# Настройки для блокчейна
BLOCKCHAIN_PROFILE = os.getenv("BLOCKCHAIN_PROFILE", "localhost")
ACTIVE_PROFILE = BLOCKCHAIN_PROFILE
RPC_URL = os.getenv("WEB3_PROVIDER_URI", "http://localhost:8545")

# Ключ продавца
SELLER_PRIVATE_KEY = os.getenv("SELLER_PRIVATE_KEY")

# Адрес реестра контрактов
AMANITA_REGISTRY_CONTRACT_ADDRESS = os.getenv("AMANITA_REGISTRY_CONTRACT_ADDRESS")

# Настройки путей
ABI_BASE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "artifacts", "contracts")
```

### 6.2 Профили сетей

```python
PROFILES = {
    "localhost": {
        "RPC": "http://127.0.0.1:8545"
    },
    "mainnet": {
        "RPC": "https://polygon-mainnet.infura.io/v3/YOUR_INFURA_KEY"
    },
    "amoy": {
        "RPC": "https://rpc-amoy.polygon.technology"
    }
}
```

## 7. Инструкции по развертыванию

### 7.1 Подготовка окружения

```bash
# Установка зависимостей
npm install

# Создание .env файла
cp .env.example .env
# Заполнение переменных окружения

# Компиляция контрактов
npx hardhat compile
```

### 7.2 Запуск локальной сети

```bash
# В отдельном терминале
npx hardhat node
```

### 7.3 Деплой контрактов

```bash
# Деплой реестра
npm run deploy:registry

# Деплой всех контрактов
npm run deploy:all

# Генерация инвайтов
npm run deploy:invites

# Загрузка каталога
npm run deploy:catalog
```

### 7.4 Тестирование

```bash
# Unit-тесты
pytest bot/tests/ -v -m "not integration"

# Интеграционные тесты
pytest bot/tests/ -v -m "integration"

# Все тесты
pytest bot/tests/ -v
```

## 8. Принципы архитектуры

### 8.1 Модульность
- Каждый контракт отвечает за свою область
- Реестр обеспечивает связность системы
- Python-слой абстрагирует детали блокчейна

### 8.2 Безопасность
- Проверка ролей на уровне контрактов
- Валидация входных данных
- Обработка ошибок с fallback-значениями

### 8.3 Масштабируемость
- Легкое добавление новых контрактов
- Универсальные методы в Python-слое
- Поддержка множественных сетей

### 8.4 Тестируемость
- Разделение unit и integration тестов
- Мокирование blockchain-слоя
- Фикстуры для изоляции тестов

## 9. Рекомендации по развитию

### 9.1 Добавление новых контрактов
1. Создать контракт в `contracts/`
2. Добавить в список в `deploy_full.js`
3. Реализовать методы в `BlockchainService`
4. Добавить тесты

### 9.2 Оптимизация газа
- Использование batch-операций
- Оптимизация структур данных
- Кэширование часто используемых значений

### 9.3 Мониторинг
- Логирование всех операций
- Метрики производительности
- Алерты при ошибках

## 10. Заключение

Данная архитектура обеспечивает:
- **Надежность**: Централизованное управление контрактами
- **Гибкость**: Легкое добавление новых функций
- **Тестируемость**: Разделение слоев и мокирование
- **Масштабируемость**: Модульная структура
- **Безопасность**: Проверка ролей и валидация

Система готова к production-использованию и дальнейшему развитию.
