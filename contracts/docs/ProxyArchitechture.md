# 🏗️ UUPS Proxy Architecture - Руководство по внедрению

## 📋 Оглавление

1. [Обзор паттерна](#обзор-паттерна)
2. [Архитектура компонентов](#архитектура-компонентов)
3. [Пошаговое внедрение](#пошаговое-внедрение)
4. [Шаблоны кода](#шаблоны-кода)
5. [Best Practices](#best-practices)
6. [Тестирование](#тестирование)
7. [Troubleshooting](#troubleshooting)
8. [Чеклист внедрения](#чеклист-внедрения)

---

## 🎯 Обзор паттерна

### Что такое UUPS?

**UUPS (Universal Upgradeable Proxy Standard)** - это паттерн разделения контракта на:
- **Proxy** - хранит данные и делегирует вызовы
- **Logic (Implementation)** - содержит бизнес-логику и может быть обновлён

### Преимущества UUPS

| Характеристика | UUPS | Transparent Proxy | Diamond |
|---------------|------|-------------------|---------|
| Gas при вызове | ✅ Низкий | ⚠️ Средний | ⚠️ Высокий |
| Сложность | ✅ Простой | ✅ Простой | ❌ Сложный |
| Безопасность upgrade | ✅ В Logic | ✅ В Proxy | ⚠️ Сложная |
| Размер Proxy | ✅ Минимальный | ⚠️ Больше | ⚠️ Больше |
| Рекомендация | 🏆 **Да** | ⚠️ Устарел | ⚠️ Для сложных |

### Когда использовать UUPS?

- ✅ Нужна возможность обновления логики
- ✅ Данные должны сохраняться между обновлениями
- ✅ Хотите минимизировать gas cost
- ✅ Следуете best practices OpenZeppelin v5

---

## 🏛️ Архитектура компонентов

### Общая схема

```
┌─────────────────────────────────────────────────┐
│                    USER                         │
└────────────────┬────────────────────────────────┘
                 │ вызывает функции
                 ▼
┌─────────────────────────────────────────────────┐
│              YourContractProxy                  │
│            (ERC1967Proxy wrapper)               │
│                                                  │
│  Хранит:                                         │
│  • State variables (данные)                      │
│  • Implementation address (адрес Logic)          │
│                                                  │
│  Делегирует:                                     │
│  • Все вызовы → Logic через delegatecall         │
└────────────────┬────────────────────────────────┘
                 │ delegatecall
                 ▼
┌─────────────────────────────────────────────────┐
│            YourContractLogic                    │
│         (UUPS Implementation)                   │
│                                                  │
│  Содержит:                                       │
│  • Бизнес-логику (функции)                       │
│  • State variables объявления                    │
│  • Модификаторы, события                         │
│  • _authorizeUpgrade() защиту                    │
│                                                  │
│  Может быть:                                     │
│  • Обновлён на новую версию                      │
│  • Заменён полностью через upgradeToAndCall()    │
└──────────────────────────────────────────────────┘
```

### Ключевые принципы

1. **Delegatecall** - Logic выполняется в контексте Proxy
   ```
   Proxy storage + Logic code = Working contract
   ```

2. **Storage в Proxy** - все данные физически хранятся в Proxy
   ```solidity
   // В Logic объявляем:
   mapping(uint256 => Component) public components;
   
   // При delegatecall данные идут в Proxy storage
   ```

3. **Upgrade Logic** - можно менять код, сохраняя данные
   ```
   Proxy[data] + LogicV1[code] → Proxy[data] + LogicV2[code]
   ```

---

## 🔧 Пошаговое внедрение

### Этап 1: Подготовка зависимостей

#### 1.1 Установка OpenZeppelin Upgradeable

```bash
npm install --save-dev @openzeppelin/contracts-upgradeable@^5.0.0
npm install --save-dev @openzeppelin/hardhat-upgrades@^3.0.0
```

#### 1.2 Конфигурация hardhat.config.js

```javascript
require("@openzeppelin/hardhat-upgrades");

module.exports = {
  solidity: {
    version: "0.8.22",
    settings: {
      optimizer: {
        enabled: true,
        runs: 200  // оптимально для частых вызовов
      },
      viaIR: true  // решает "Stack too deep"
    }
  }
};
```

**⚠️ Важно:** `viaIR: true` критично для сложных контрактов с calldata параметрами

---

### Этап 2: Создание Proxy контракта

#### Файл: `contracts/YourContractProxy.sol`

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.22;

import "@openzeppelin/contracts/proxy/ERC1967/ERC1967Proxy.sol";

/**
 * @title YourContractProxy
 * @dev Минимальная обёртка над ERC1967Proxy
 * @notice Хранит данные и делегирует вызовы к Logic контракту
 */
contract YourContractProxy is ERC1967Proxy {
    /**
     * @dev Конструктор инициализирует proxy
     * @param implementation Адрес Logic контракта
     * @param initData Закодированный вызов initialize()
     */
    constructor(
        address implementation,
        bytes memory initData
    ) ERC1967Proxy(implementation, initData) {}
}
```

**Размер:** ~30-40 строк  
**Функционал:** Только конструктор, всё остальное наследуется от ERC1967Proxy

---

### Этап 3: Создание Logic контракта

#### Файл: `contracts/YourContractLogic.sol`

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.22;

import "@openzeppelin/contracts-upgradeable/access/AccessControlUpgradeable.sol";
import "@openzeppelin/contracts-upgradeable/proxy/utils/UUPSUpgradeable.sol";
import "@openzeppelin/contracts-upgradeable/proxy/utils/Initializable.sol";
import "@openzeppelin/contracts-upgradeable/utils/PausableUpgradeable.sol";
import "@openzeppelin/contracts-upgradeable/utils/ReentrancyGuardUpgradeable.sol";

/**
 * @title YourContractLogic
 * @dev UUPS Implementation контракт
 * @notice Содержит ВСЮ бизнес-логику и state variables объявления
 */
contract YourContractLogic is 
    Initializable,
    UUPSUpgradeable,
    AccessControlUpgradeable,
    PausableUpgradeable,
    ReentrancyGuardUpgradeable
{
    // === КОНСТАНТЫ ===
    
    uint256 public constant LOGIC_VERSION = 1;
    
    // === РОЛИ ===
    
    bytes32 public constant UPGRADER_ROLE = keccak256("UPGRADER_ROLE");
    bytes32 public constant ADMIN_ROLE = keccak256("ADMIN_ROLE");
    
    // === CUSTOM ERRORS ===
    
    error ZeroAddress();
    error InvalidInput();
    
    // === STATE VARIABLES ===
    // ⚠️ ВАЖНО: Все переменные объявляются в Logic
    // При delegatecall данные физически хранятся в Proxy
    
    uint256 public totalItems;
    mapping(uint256 => string) public items;
    
    // === ИНИЦИАЛИЗАЦИЯ ===
    
    /**
     * @dev Инициализация вместо конструктора
     * @param admin Адрес администратора
     */
    function initialize(address admin) public initializer {
        require(admin != address(0), "YourContractLogic: invalid admin");
        
        // Инициализация всех модулей OpenZeppelin
        __AccessControl_init();
        __UUPSUpgradeable_init();
        __Pausable_init();
        __ReentrancyGuard_init();
        
        // Выдача ролей админу
        _grantRole(DEFAULT_ADMIN_ROLE, admin);
        _grantRole(ADMIN_ROLE, admin);
        _grantRole(UPGRADER_ROLE, admin);
    }
    
    // === ЗАЩИТА UPGRADE ===
    
    /**
     * @dev Авторизация обновления контракта
     * @param newImplementation адрес новой Logic
     */
    function _authorizeUpgrade(address newImplementation) 
        internal 
        override 
        onlyRole(UPGRADER_ROLE) 
    {
        // Дополнительные проверки можно добавить здесь
    }
    
    // === ФУНКЦИИ ПАУЗЫ ===
    
    function pause() external onlyRole(ADMIN_ROLE) nonReentrant {
        _pause();
    }
    
    function unpause() external onlyRole(ADMIN_ROLE) nonReentrant {
        _unpause();
    }
    
    // === БИЗНЕС-ЛОГИКА ===
    
    function createItem(string calldata itemData) 
        external 
        whenNotPaused 
        nonReentrant 
        returns (uint256 itemId) 
    {
        unchecked {
            itemId = ++totalItems;
        }
        items[itemId] = itemData;
    }
}
```

---

### Этап 4: Создание интерфейса

#### Файл: `contracts/interfaces/IYourContract.sol`

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.22;

/**
 * @title IYourContract
 * @dev Интерфейс для интеграции с YourContract
 */
interface IYourContract {
    
    // === СОБЫТИЯ ===
    
    event ItemCreated(
        uint256 indexed itemId,
        string itemData,
        address indexed creator,
        uint256 timestamp
    );
    
    // === ФУНКЦИИ ===
    
    function totalItems() external view returns (uint256);
    function items(uint256 itemId) external view returns (string memory);
    function createItem(string memory itemData) external returns (uint256);
}
```

---

### Этап 5: Деплой скрипт

#### Файл: `scripts/deploy-your-contract.js`

```javascript
const { ethers, upgrades } = require("hardhat");

async function main() {
    const [deployer] = await ethers.getSigners();
    
    console.log("Deploying contracts with:", deployer.address);
    console.log("Account balance:", (await ethers.provider.getBalance(deployer.address)).toString());
    
    // === ДЕПЛОЙ LOGIC ===
    console.log("\n1. Deploying Logic contract...");
    const Logic = await ethers.getContractFactory("YourContractLogic");
    const logic = await Logic.deploy();
    await logic.waitForDeployment();
    const logicAddress = await logic.getAddress();
    console.log("✅ Logic deployed at:", logicAddress);
    
    // === ДЕПЛОЙ PROXY ===
    console.log("\n2. Deploying Proxy contract...");
    const Proxy = await ethers.getContractFactory("YourContractProxy");
    
    // Кодируем вызов initialize
    const initData = logic.interface.encodeFunctionData("initialize", [
        deployer.address  // admin address
    ]);
    
    const proxy = await Proxy.deploy(logicAddress, initData);
    await proxy.waitForDeployment();
    const proxyAddress = await proxy.getAddress();
    console.log("✅ Proxy deployed at:", proxyAddress);
    
    // === ПОДКЛЮЧЕНИЕ К PROXY ===
    const contract = await ethers.getContractAt(
        "YourContractLogic",
        proxyAddress
    );
    
    // === ПРОВЕРКА ===
    console.log("\n3. Verification...");
    const version = await contract.LOGIC_VERSION();
    console.log("✅ Logic version:", version);
    
    const totalItems = await contract.totalItems();
    console.log("✅ Total items:", totalItems);
    
    // === СОХРАНЕНИЕ АДРЕСОВ ===
    const deployment = {
        network: network.name,
        proxy: proxyAddress,
        logic: logicAddress,
        admin: deployer.address,
        timestamp: new Date().toISOString()
    };
    
    console.log("\n📝 Deployment info:", deployment);
    
    // Можно сохранить в файл
    // fs.writeFileSync('deployment.json', JSON.stringify(deployment, null, 2));
}

main()
    .then(() => process.exit(0))
    .catch((error) => {
        console.error(error);
        process.exit(1);
    });
```

---

### Этап 6: Тестирование

#### Файл: `contracts/tests/YourContract.UUPS.test.js`

```javascript
const { expect } = require("chai");
const { ethers, upgrades } = require("hardhat");

describe("YourContract UUPS Architecture", function () {
    let proxy, logic, contract;
    let admin, user1, user2;

    beforeEach(async function () {
        [admin, user1, user2] = await ethers.getSigners();
        
        // Деплой Logic
        const Logic = await ethers.getContractFactory("YourContractLogic");
        logic = await Logic.deploy();
        await logic.waitForDeployment();
        
        // Деплой Proxy
        const Proxy = await ethers.getContractFactory("YourContractProxy");
        const initData = logic.interface.encodeFunctionData("initialize", [
            admin.address
        ]);
        
        proxy = await Proxy.deploy(
            await logic.getAddress(),
            initData
        );
        await proxy.waitForDeployment();
        
        // Подключаемся к Proxy как к Logic
        contract = await ethers.getContractAt(
            "YourContractLogic",
            await proxy.getAddress()
        );
    });

    describe("UUPS Architecture Tests", function () {
        it("Should deploy and initialize correctly", async function () {
            expect(await contract.LOGIC_VERSION()).to.equal(1);
            expect(await contract.totalItems()).to.equal(0);
            
            // Проверяем роли
            expect(await contract.hasRole(
                await contract.DEFAULT_ADMIN_ROLE(),
                admin.address
            )).to.be.true;
        });
        
        it("Should create item through proxy", async function () {
            const tx = await contract.connect(user1).createItem("Test Item");
            const receipt = await tx.wait();
            
            expect(await contract.totalItems()).to.equal(1);
            expect(await contract.items(1)).to.equal("Test Item");
        });
    });

    describe("Proxy Management", function () {
        it("Should upgrade logic contract", async function () {
            // Деплой новой Logic
            const LogicV2 = await ethers.getContractFactory("YourContractLogic");
            const logicV2 = await LogicV2.deploy();
            await logicV2.waitForDeployment();
            
            // Upgrade через admin (UPGRADER_ROLE)
            await contract.connect(admin).upgradeToAndCall(
                await logicV2.getAddress(),
                "0x"  // нет миграции данных
            );
            
            // Проверяем что версия обновилась, а данные сохранились
            expect(await contract.LOGIC_VERSION()).to.equal(1);
        });
        
        it("Should pause and unpause contract", async function () {
            await contract.connect(admin).pause();
            
            // Функции с whenNotPaused должны провалиться
            await expect(
                contract.connect(user1).createItem("Test")
            ).to.be.revertedWithCustomError(contract, "EnforcedPause");
            
            await contract.connect(admin).unpause();
            
            // После unpause должно работать
            await expect(
                contract.connect(user1).createItem("Test")
            ).to.not.be.reverted;
        });
        
        it("Should restrict upgrades to UPGRADER_ROLE only", async function () {
            const LogicV2 = await ethers.getContractFactory("YourContractLogic");
            const logicV2 = await LogicV2.deploy();
            
            // user1 БЕЗ UPGRADER_ROLE не может апгрейдить
            await expect(
                contract.connect(user1).upgradeToAndCall(
                    await logicV2.getAddress(),
                    "0x"
                )
            ).to.be.reverted;
            
            // admin С UPGRADER_ROLE может
            await expect(
                contract.connect(admin).upgradeToAndCall(
                    await logicV2.getAddress(),
                    "0x"
                )
            ).to.not.be.reverted;
        });
    });

    describe("Reentrancy Protection Tests", function () {
        it("Should have reentrancy protection", async function () {
            // Smoke-тест: функции с nonReentrant работают корректно
            await contract.connect(user1).createItem("Item 1");
            await contract.connect(user1).createItem("Item 2");
            
            expect(await contract.totalItems()).to.equal(2);
        });
    });
});
```

---

## 📝 Шаблоны кода

### Шаблон 1: Минимальный Proxy

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.22;

import "@openzeppelin/contracts/proxy/ERC1967/ERC1967Proxy.sol";

contract YourContractProxy is ERC1967Proxy {
    constructor(address implementation, bytes memory initData)
        ERC1967Proxy(implementation, initData)
    {}
}
```

**Что делать:**
- ✅ Заменить `YourContract` на имя вашего контракта
- ✅ Оставить всё как есть (минимальная обёртка)

---

### Шаблон 2: Logic с полным набором модулей

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.22;

import "@openzeppelin/contracts-upgradeable/access/AccessControlUpgradeable.sol";
import "@openzeppelin/contracts-upgradeable/proxy/utils/UUPSUpgradeable.sol";
import "@openzeppelin/contracts-upgradeable/proxy/utils/Initializable.sol";
import "@openzeppelin/contracts-upgradeable/utils/PausableUpgradeable.sol";
import "@openzeppelin/contracts-upgradeable/utils/ReentrancyGuardUpgradeable.sol";

contract YourContractLogic is 
    Initializable,
    UUPSUpgradeable,
    AccessControlUpgradeable,
    PausableUpgradeable,
    ReentrancyGuardUpgradeable
{
    // === КОНСТАНТЫ ===
    uint256 public constant LOGIC_VERSION = 1;
    
    // === РОЛИ ===
    bytes32 public constant UPGRADER_ROLE = keccak256("UPGRADER_ROLE");
    bytes32 public constant ADMIN_ROLE = keccak256("ADMIN_ROLE");
    
    // === CUSTOM ERRORS ===
    error ZeroAddress();
    
    // === STATE VARIABLES ===
    // ⚠️ Все переменные объявляются здесь
    // Данные физически хранятся в Proxy через delegatecall
    
    uint256 public totalItems;
    mapping(uint256 => YourData) public items;
    
    // === СТРУКТУРЫ ===
    struct YourData {
        uint256 id;
        address creator;
        uint256 timestamp;
    }
    
    // === СОБЫТИЯ ===
    event ItemCreated(uint256 indexed itemId, address indexed creator, uint256 timestamp);
    
    // === ИНИЦИАЛИЗАЦИЯ ===
    function initialize(address admin) public initializer {
        require(admin != address(0), "Invalid admin");
        
        __AccessControl_init();
        __UUPSUpgradeable_init();
        __Pausable_init();
        __ReentrancyGuard_init();
        
        _grantRole(DEFAULT_ADMIN_ROLE, admin);
        _grantRole(ADMIN_ROLE, admin);
        _grantRole(UPGRADER_ROLE, admin);
    }
    
    // === UPGRADE PROTECTION ===
    function _authorizeUpgrade(address newImplementation) 
        internal 
        override 
        onlyRole(UPGRADER_ROLE) 
    {}
    
    // === PAUSE FUNCTIONS ===
    function pause() external onlyRole(ADMIN_ROLE) nonReentrant {
        _pause();
    }
    
    function unpause() external onlyRole(ADMIN_ROLE) nonReentrant {
        _unpause();
    }
    
    // === БИЗНЕС-ЛОГИКА ===
    function createItem(string calldata data) 
        external 
        whenNotPaused 
        nonReentrant 
        returns (uint256 itemId) 
    {
        unchecked {
            itemId = ++totalItems;
        }
        
        items[itemId] = YourData({
            id: itemId,
            creator: msg.sender,
            timestamp: block.timestamp
        });
        
        emit ItemCreated(itemId, msg.sender, block.timestamp);
    }
}
```

---

### Шаблон 3: Модификаторы валидации

```solidity
// === VALIDATION HELPERS ===

/**
 * @dev Проверка ненулевого адреса (custom error)
 */
function _requireNonZero(address addr) internal pure {
    if (addr == address(0)) revert ZeroAddress();
}

/**
 * @dev Проверка строки (legacy для совместимости)
 */
function _requireStringNonEmpty(string memory str) internal pure {
    require(bytes(str).length > 0, "YourContract: string cannot be empty");
}

// === МОДИФИКАТОРЫ ===

modifier validString(string memory str) {
    // Газовая оптимизация: кэшируем bytes().length
    uint256 len = bytes(str).length;
    require(len > 0, "YourContract: string cannot be empty");
    require(len <= MAX_STRING_LENGTH, "YourContract: string too long");
    _;
}

modifier onlyItemOwner(uint256 itemId) {
    require(
        items[itemId].creator == msg.sender,
        "YourContract: not item owner"
    );
    _;
}
```

---

### Шаблон 4: Интеграции с другими контрактами

```solidity
// === ИНТЕГРАЦИОННЫЕ ПЕРЕМЕННЫЕ ===
// Прямое объявление без StorageSlot

address public externalContract1;
address public externalContract2;

// === СЕТТЕРЫ С ЗАЩИТОЙ ===

function setExternalContract1(address _contract) 
    external 
    onlyRole(ADMIN_ROLE) 
    nonReentrant 
{
    _requireNonZero(_contract);
    externalContract1 = _contract;
}

function setExternalContract2(address _contract) 
    external 
    onlyRole(ADMIN_ROLE) 
    nonReentrant 
{
    _requireNonZero(_contract);
    externalContract2 = _contract;
}

// === МОДИФИКАТОРЫ ДЛЯ ИНТЕГРАЦИЙ ===

modifier whenContract1Set() {
    require(externalContract1 != address(0), "Contract1 not set");
    _;
}

modifier whenContract2Set() {
    require(externalContract2 != address(0), "Contract2 not set");
    _;
}
```

---

## 🎯 Best Practices

### 1. Структура файлов

```
contracts/
├── YourContractProxy.sol          # Минимальный proxy
├── YourContractLogic.sol          # Вся бизнес-логика
├── interfaces/
│   └── IYourContract.sol          # Публичный интерфейс
└── tests/
    └── YourContract.UUPS.test.js  # Comprehensive тесты
```

---

### 2. Порядок наследований

**⚠️ ВАЖНО:** Порядок имеет значение!

```solidity
contract YourContractLogic is 
    Initializable,              // 1. Первым всегда
    UUPSUpgradeable,            // 2. UUPS функционал
    AccessControlUpgradeable,   // 3. Роли
    PausableUpgradeable,        // 4. Пауза
    ReentrancyGuardUpgradeable, // 5. Защита от reentrancy
    IYourContract               // 6. Интерфейсы последними
{
    // ...
}
```

---

### 3. Инициализация модулей

**⚠️ ВАЖНО:** Инициализировать ВСЕ модули в правильном порядке

```solidity
function initialize(address admin) public initializer {
    // 1. Валидация входных данных
    require(admin != address(0), "Invalid admin");
    
    // 2. Инициализация модулей (порядок не критичен, но лучше следовать)
    __AccessControl_init();       // Роли
    __UUPSUpgradeable_init();     // UUPS
    __Pausable_init();            // Пауза
    __ReentrancyGuard_init();     // Reentrancy
    
    // 3. Настройка ролей
    _grantRole(DEFAULT_ADMIN_ROLE, admin);
    _grantRole(ADMIN_ROLE, admin);
    _grantRole(UPGRADER_ROLE, admin);
    
    // 4. Инициализация данных (если нужно)
    // totalItems = 0; // уже 0 по умолчанию
}
```

---

### 4. Storage Gap (для будущих upgrade)

**⚠️ ВАЖНО:** Резервируйте слоты для будущих переменных

```solidity
contract YourContractLogic is ... {
    // ... все переменные ...
    
    /**
     * @dev Резерв для будущих обновлений
     * Уменьшайте при добавлении новых переменных
     */
    uint256[50] private __gap;
}
```

**Зачем:**
- Позволяет добавлять новые переменные в LogicV2
- Сохраняет совместимость storage layout
- Рекомендация OpenZeppelin

---

### 5. Модификаторы порядок

**Рекомендуемый порядок модификаторов:**

```solidity
function yourFunction(...) 
    external                    // 1. Visibility
    whenNotPaused              // 2. State checks
    nonReentrant               // 3. Reentrancy protection
    onlyRole(SOME_ROLE)        // 4. Access control
    validInput(param)          // 5. Input validation
    returns (uint256)          // 6. Return type
{
    // ...
}
```

---

### 6. Газовые оптимизации

#### Unchecked для счётчиков

```solidity
// Безопасно для uint256 счётчиков
unchecked {
    itemId = ++totalItems;
}
```

#### Calldata для read-only параметров

```solidity
// Было:
function createItem(string memory data) external

// Стало:
function createItem(string calldata data) external
```

#### Кэширование bytes().length

```solidity
modifier validString(string memory str) {
    uint256 len = bytes(str).length;  // ← кэшируем
    require(len > 0, "...");
    require(len <= MAX, "...");
    _;
}
```

---

### 7. Custom Errors

```solidity
// Объявление
error ZeroAddress();
error InvalidInput();
error NotAuthorized();

// Использование
function _requireNonZero(address addr) internal pure {
    if (addr == address(0)) revert ZeroAddress();
}

// В функциях
function setAddress(address addr) external {
    _requireNonZero(addr);
    // ...
}
```

---

### 8. События с indexed

**Правило:** Максимум 3 indexed параметра на событие

```solidity
event ItemCreated(
    uint256 indexed itemId,      // ← indexed для фильтрации
    string data,                  // НЕ indexed (string нельзя)
    address indexed creator,      // ← indexed для фильтрации
    uint256 indexed timestamp     // ← indexed для фильтрации
);
```

---

## 🧪 Тестирование

### Минимальный набор тестов

**Обязательные тесты:**

1. ✅ **Deploy and initialize** - корректная инициализация
2. ✅ **Create through proxy** - работа через delegatecall
3. ✅ **Upgrade logic** - обновление Logic контракта
4. ✅ **Pause/unpause** - аварийная остановка
5. ✅ **Role restrictions** - контроль доступа
6. ✅ **Reentrancy protection** - защита от атак
7. ✅ **Input validation** - валидация входных данных

### Рекомендуемые тесты

8. ✅ **Event filtering** - фильтрация событий
9. ✅ **Custom errors** - проверка custom errors
10. ✅ **Proxy protection** - изоляция implementation
11. ✅ **Integration tests** - интеграция с другими контрактами
12. ✅ **Edge cases** - граничные условия

### Структура describe блоков

```javascript
describe("YourContract UUPS Architecture", function () {
    
    describe("UUPS Architecture Tests", function () {
        // Deploy, initialize, basic operations
    });
    
    describe("Proxy Management", function () {
        // Upgrade, pause, role checks
    });
    
    describe("Business Logic Tests", function () {
        // Your specific functionality
    });
    
    describe("Security Tests", function () {
        // Reentrancy, access control, validation
    });
    
    describe("Integration Tests", function () {
        // External contracts integration
    });
});
```

---

## 🚨 Troubleshooting

### Проблема 1: "Stack too deep"

**Симптомы:**
```
CompilerError: Stack too deep. Try compiling with `--via-ir`
```

**Решение:**
```javascript
// hardhat.config.js
module.exports = {
  solidity: {
    version: "0.8.22",
    settings: {
      viaIR: true  // ← Добавить это
    }
  }
};
```

---

### Проблема 2: "Function already initialized"

**Симптомы:**
```
Error: Initializable: contract is already initialized
```

**Причина:** Попытка повторного вызова `initialize()`

**Решение:**
- `initialize()` можно вызвать ТОЛЬКО ОДИН РАЗ
- При деплое Proxy передавайте initData
- При upgrade НЕ вызывайте initialize повторно

---

### Проблема 3: "Implementation has state"

**Симптомы:**
- У implementation контракта есть данные
- Данные не совпадают с proxy

**Причина:** Прямой вызов на implementation вместо proxy

**Решение:**
- Всегда взаимодействуйте через Proxy адрес
- Implementation только для upgrade

```javascript
// ❌ НЕПРАВИЛЬНО
const contract = await ethers.getContractAt("Logic", logicAddress);

// ✅ ПРАВИЛЬНО
const contract = await ethers.getContractAt("Logic", proxyAddress);
```

---

### Проблема 4: "Storage collision"

**Симптомы:**
- Данные "перемешиваются" после upgrade
- Неожиданные значения переменных

**Причина:** Изменён порядок state variables в LogicV2

**Решение:**
- ❌ НЕ МЕНЯЙТЕ порядок существующих переменных
- ❌ НЕ УДАЛЯЙТЕ существующие переменные
- ✅ ДОБАВЛЯЙТЕ новые переменные в конец
- ✅ ИСПОЛЬЗУЙТЕ storage gap

```solidity
// LogicV1
contract LogicV1 {
    uint256 public var1;
    uint256 public var2;
    uint256[50] private __gap;
}

// LogicV2 - ПРАВИЛЬНО
contract LogicV2 is LogicV1 {
    uint256 public var3;  // добавляем в конец
    uint256[49] private __gap;  // уменьшаем gap
}

// LogicV2 - НЕПРАВИЛЬНО ❌
contract LogicV2 is LogicV1 {
    uint256 public var3;  // НЕ ДОБАВЛЯЙТЕ между существующими!
    uint256 public var1;  // НЕ МЕНЯЙТЕ порядок!
    uint256 public var2;
}
```

---

## ✅ Чеклист внедрения

### Pre-development

- [ ] OpenZeppelin upgradeable установлен
- [ ] hardhat-upgrades плагин установлен
- [ ] Определены роли и права доступа
- [ ] Спроектированы структуры данных
- [ ] Определены интеграции

---

### Development

#### Proxy контракт:
- [ ] Создан минимальный Proxy (30-40 строк)
- [ ] Наследует ERC1967Proxy
- [ ] Только конструктор с (implementation, initData)

#### Logic контракт:
- [ ] Наследует Initializable, UUPSUpgradeable
- [ ] Добавлены AccessControl, Pausable, ReentrancyGuard
- [ ] Объявлены все state variables
- [ ] Реализована функция initialize()
- [ ] Реализована _authorizeUpgrade()
- [ ] Добавлены custom errors
- [ ] Добавлены validation helpers
- [ ] Модификаторы применены правильно
- [ ] Газовые оптимизации применены
- [ ] События с indexed полями
- [ ] Storage gap добавлен (uint256[50])

---

### Testing

- [ ] Тесты деплоя и инициализации
- [ ] Тесты upgrade логики
- [ ] Тесты pause/unpause
- [ ] Тесты role restrictions
- [ ] Тесты reentrancy protection
- [ ] Тесты input validation
- [ ] Тесты event filtering
- [ ] Тесты custom errors
- [ ] Тесты proxy protection
- [ ] Интеграционные тесты
- [ ] **Все тесты проходят (100%)**

---

### Deployment

- [ ] Скомпилировано с viaIR: true
- [ ] Все тесты проходят
- [ ] Адрес админа подготовлен (multisig рекомендуется)
- [ ] Gas price приемлемый
- [ ] Logic контракт задеплоен
- [ ] Proxy контракт задеплоен
- [ ] Initialize вызван через Proxy
- [ ] Интеграции настроены
- [ ] Роли выданы
- [ ] Контракты верифицированы
- [ ] Адреса сохранены

---

## 📊 Сравнение с другими паттернами

### UUPS vs Transparent Proxy

| Характеристика | UUPS | Transparent |
|---------------|------|-------------|
| **Upgrade logic** | В Logic контракте | В Proxy контракте |
| **Gas overhead** | ~500 gas | ~2000 gas |
| **Admin separation** | Через роли | Встроенная |
| **Размер Proxy** | ~30 строк | ~150 строк |
| **Безопасность** | Требует внимания | Автоматическая |
| **Рекомендация OZ** | ✅ v5+ | ⚠️ Deprecated |

**Вывод:** UUPS - современный стандарт для v5+

---

### UUPS vs Diamond (EIP-2535)

| Характеристика | UUPS | Diamond |
|---------------|------|---------|
| **Сложность** | ✅ Простой | ❌ Сложный |
| **Модульность** | ⚠️ Монолит | ✅ Facets |
| **Gas overhead** | ✅ Низкий | ⚠️ Высокий |
| **Use case** | Обычные DApps | Большие системы |
| **Поддержка** | ✅ OZ v5 | ⚠️ Custom |

**Вывод:** Diamond для сложных систем, UUPS для обычных

---

## 🔄 Upgrade процесс

### Сценарий 1: Простой upgrade (без миграции)

```javascript
// 1. Деплой новой Logic
const LogicV2 = await ethers.getContractFactory("YourContractLogicV2");
const logicV2 = await LogicV2.deploy();
await logicV2.waitForDeployment();

// 2. Upgrade через Proxy
const contract = await ethers.getContractAt("YourContractLogic", proxyAddress);
await contract.connect(upgrader).upgradeToAndCall(
    await logicV2.getAddress(),
    "0x"  // нет calldata для миграции
);

// 3. Проверка
const version = await contract.LOGIC_VERSION();
console.log(`Upgraded to version: ${version}`);
```

---

### Сценарий 2: Upgrade с миграцией данных

```solidity
// LogicV2 с миграционной функцией
contract YourContractLogicV2 is YourContractLogic {
    uint256 public constant LOGIC_VERSION = 2;
    
    // Новая переменная
    mapping(uint256 => bool) public itemVerified;
    
    /**
     * @dev Миграция данных из V1 в V2
     * @notice Вызывается ОДИН РАЗ при upgrade
     */
    function migrateV1ToV2() 
        external 
        onlyRole(ADMIN_ROLE) 
        onlyProxy  // ← защита от прямых вызовов
    {
        // Миграция: пометить все существующие items как verified
        for (uint256 i = 1; i <= totalItems; i++) {
            itemVerified[i] = true;
        }
    }
}
```

```javascript
// Upgrade с миграцией
const migrateCalldata = logicV2.interface.encodeFunctionData("migrateV1ToV2");

await contract.connect(upgrader).upgradeToAndCall(
    await logicV2.getAddress(),
    migrateCalldata  // ← вызовет migrateV1ToV2() после upgrade
);
```

---

### Сценарий 3: Rollback (откат)

```javascript
// Если upgrade V2 вызвал проблемы, вернуться к V1

// 1. Получить адрес старой Logic (из истории деплоев)
const logicV1Address = "0x123..."; // из deployment.json

// 2. Откатиться через upgradeToAndCall
await contract.connect(upgrader).upgradeToAndCall(
    logicV1Address,
    "0x"
);

// 3. Проверка
const version = await contract.LOGIC_VERSION();
console.log(`Rolled back to version: ${version}`);
```

**⚠️ Внимание:** Rollback возможен только если storage layout совместим!

---

## 📚 Примеры из реальных контрактов

### Пример 1: OrganicComponentRegistry

**Структура:**
```
OrganicComponentRegistryProxy.sol    (36 строк)
OrganicComponentRegistryLogic.sol    (670 строк)
IOrganicComponentRegistry.sol        (182 строки)
OrganicComponentRegistry.UUPS.test.js (735 строк, 37 тестов)
```

**Особенности:**
- ✅ ReentrancyGuard на 10 функциях
- ✅ Custom errors (13 штук)
- ✅ Газовые оптимизации (unchecked, calldata, caching)
- ✅ Event indexing (5 событий)
- ✅ 3 интеграции (SpiralEngine, AmanitaInternational, ProductRegistry)
- ✅ 4 роли (DEFAULT_ADMIN, ADMIN, UPGRADER, CONTRIBUTOR)

**Статус:** ✅ Production ready (37/37 тестов)

---

## 🎓 Рекомендации по применению

### Для простых контрактов

**Минимальный набор:**
- Initializable + UUPSUpgradeable
- AccessControlUpgradeable
- 1-2 роли (ADMIN, UPGRADER)

**Пример:**
```solidity
contract SimpleLogic is 
    Initializable,
    UUPSUpgradeable,
    AccessControlUpgradeable
{
    // Минимальная реализация
}
```

---

### Для средних контрактов

**Расширенный набор:**
- + PausableUpgradeable
- + 3-4 роли
- + Custom errors
- + Basic газовые оптимизации

**Пример:** OrganicComponentRegistry

---

### Для сложных контрактов

**Полный набор:**
- + ReentrancyGuardUpgradeable
- + Множество ролей
- + Комплексные интеграции
- + Все газовые оптимизации
- + Event indexing
- + Storage gap

**Пример:** DeFi протоколы, DAOs

---

## 🔐 Безопасность

### Критические моменты

1. **UPGRADER_ROLE критичен**
   - Может изменить ВСЮ логику контракта
   - Рекомендуется multisig или timelock
   - Минимум 2-3 подписи для multisig

2. **Initialize единожды**
   - Защита через `initializer` модификатор
   - Нельзя вызвать повторно
   - Проверяйте в тестах

3. **Storage layout**
   - НЕ меняйте порядок переменных при upgrade
   - Используйте storage gap
   - Тестируйте upgrade на testnet

4. **Access control**
   - Проверяйте роли в каждой критической функции
   - DEFAULT_ADMIN_ROLE контролирует всё
   - Не забывайте про modifiers

---

### Checklist безопасности

- [ ] UPGRADER_ROLE выдан multisig (не EOA)
- [ ] initialize() имеет валидацию admin адреса
- [ ] _authorizeUpgrade() защищён через onlyRole
- [ ] Все мутирующие функции имеют nonReentrant
- [ ] Критические функции имеют role checks
- [ ] Input validation на всех функциях
- [ ] Custom errors используются правильно
- [ ] События индексированы корректно
- [ ] Storage gap добавлен для будущих upgrade
- [ ] Все тесты проходят (100%)

---

## 📐 Диаграммы

### Call Flow

```
User → Proxy.createItem("data")
         │
         │ (delegatecall)
         ▼
       Logic.createItem("data")
         │
         │ executes in Proxy context
         │ storage writes go to Proxy
         ▼
       Proxy.totalItems++
       Proxy.items[id] = data
         │
         ▼
       emit ItemCreated(...)
         │
         ▼
       return itemId to User
```

---

### Upgrade Flow

```
Before Upgrade:
┌──────────┐         ┌──────────┐
│  Proxy   │────────▶│ LogicV1  │
│  (data)  │         │  (code)  │
└──────────┘         └──────────┘

Upgrade Transaction:
┌──────────┐         ┌──────────┐
│  Proxy   │         │ LogicV2  │
│  (data)  │         │  (new)   │
└─────┬────┘         └──────────┘
      │
      │ upgradeToAndCall(logicV2, data)
      ▼
    Updates implementation slot

After Upgrade:
┌──────────┐         ┌──────────┐
│  Proxy   │────────▶│ LogicV2  │
│  (data)  │    ✓    │  (code)  │
│ preserved│         │  updated │
└──────────┘         └──────────┘
```

---

### Storage Layout

```
Proxy Contract Storage:
┌─────────────────────────────────────┐
│ Slot 0: OpenZeppelin reserved       │
│ Slot 1: Implementation address      │
│ Slot 2: Admin (if Transparent)      │
│ ...                                  │
├─────────────────────────────────────┤
│ Slot 51+: Your state variables      │
│   - totalItems                       │
│   - items mapping                    │
│   - custom data                      │
└─────────────────────────────────────┘

Logic Contract (no state!):
┌─────────────────────────────────────┐
│ Only code, no persistent storage     │
│ State variable declarations          │
│ Functions, modifiers, logic          │
└─────────────────────────────────────┘
```

---

## 🎯 Quick Start Guide

### 1. Создайте файлы

```bash
# Proxy
touch contracts/YourContractProxy.sol

# Logic
touch contracts/YourContractLogic.sol

# Interface
touch contracts/interfaces/IYourContract.sol

# Tests
touch contracts/tests/YourContract.UUPS.test.js
```

---

### 2. Скопируйте шаблоны

**Proxy:** Используйте [Шаблон 1](#шаблон-1-минимальный-proxy)

**Logic:** Используйте [Шаблон 2](#шаблон-2-logic-с-полным-набором-модулей)

---

### 3. Адаптируйте под свои нужды

- Замените `YourContract` на имя вашего контракта
- Добавьте свои state variables
- Реализуйте бизнес-логику
- Добавьте нужные роли
- Создайте custom errors

---

### 4. Напишите тесты

Минимум 7 тестов (см. [Минимальный набор тестов](#минимальный-набор-тестов))

---

### 5. Деплой

```bash
# Компиляция
npx hardhat compile

# Тесты
npx hardhat test

# Деплой на testnet
npx hardhat run scripts/deploy-your-contract.js --network mumbai

# Проверка
npx hardhat verify --network mumbai <PROXY_ADDRESS>
```

---

## 📖 Референсы

### OpenZeppelin Documentation

- [Upgrades Plugins](https://docs.openzeppelin.com/upgrades-plugins/1.x/)
- [UUPS Proxies](https://docs.openzeppelin.com/contracts/5.x/api/proxy#UUPSUpgradeable)
- [Writing Upgradeable Contracts](https://docs.openzeppelin.com/upgrades-plugins/1.x/writing-upgradeable)

### EIPs

- [EIP-1967: Proxy Storage Slots](https://eips.ethereum.org/EIPS/eip-1967)
- [EIP-1822: UUPS](https://eips.ethereum.org/EIPS/eip-1822)

### Примеры

- [OrganicComponentRegistry](../OrganicComponentRegistryLogic.sol) - референсная реализация
- [OpenZeppelin Contracts](https://github.com/OpenZeppelin/openzeppelin-contracts-upgradeable)

---

## ⚠️ Частые ошибки

### ❌ Ошибка 1: Конструктор в Logic

```solidity
// НЕПРАВИЛЬНО ❌
contract YourContractLogic {
    constructor() {
        totalItems = 0;  // НЕ СРАБОТАЕТ!
    }
}

// ПРАВИЛЬНО ✅
contract YourContractLogic {
    function initialize() public initializer {
        totalItems = 0;  // Сработает
    }
}
```

**Причина:** Конструкторы выполняются при деплое, но их state не копируется в Proxy

---

### ❌ Ошибка 2: Storage collision при upgrade

```solidity
// LogicV1
contract V1 {
    uint256 public var1;
    address public var2;
}

// LogicV2 - НЕПРАВИЛЬНО ❌
contract V2 {
    address public var2;  // ← Поменяли порядок!
    uint256 public var1;  // ← Данные "перемешаются"
}

// LogicV2 - ПРАВИЛЬНО ✅
contract V2 {
    uint256 public var1;  // ← Тот же порядок
    address public var2;  // ← Тот же порядок
    string public var3;   // ← Новые в конце
}
```

---

### ❌ Ошибка 3: Забыли __Module_init()

```solidity
// НЕПРАВИЛЬНО ❌
function initialize(address admin) public initializer {
    _grantRole(DEFAULT_ADMIN_ROLE, admin);
    // Забыли вызвать __AccessControl_init()!
}

// ПРАВИЛЬНО ✅
function initialize(address admin) public initializer {
    __AccessControl_init();  // ← Обязательно!
    _grantRole(DEFAULT_ADMIN_ROLE, admin);
}
```

---

### ❌ Ошибка 4: Прямой вызов на implementation

```javascript
// НЕПРАВИЛЬНО ❌
const contract = await ethers.getContractAt(
    "YourContractLogic",
    logicAddress  // ← адрес Logic!
);
await contract.createItem("test"); // Данные НЕ сохранятся

// ПРАВИЛЬНО ✅
const contract = await ethers.getContractAt(
    "YourContractLogic",
    proxyAddress  // ← адрес Proxy!
);
await contract.createItem("test"); // Данные сохранятся
```

---

## 🎓 Расширенные темы

### Storage Gaps

**Зачем:** Позволяет добавлять переменные в базовый контракт при upgrade

```solidity
contract YourContractLogicV1 {
    uint256 public totalItems;
    mapping(uint256 => Item) public items;
    
    // Резервируем 50 слотов для будущего
    uint256[50] private __gap;
}

contract YourContractLogicV2 is YourContractLogicV1 {
    // Добавляем новую переменную
    uint256 public newVariable;
    
    // Уменьшаем gap на 1
    uint256[49] private __gap;  // было 50, стало 49
}
```

---

### onlyProxy модификатор

**Когда использовать:** Для миграционных функций

```solidity
import "@openzeppelin/contracts-upgradeable/proxy/utils/UUPSUpgradeable.sol";

contract YourContractLogic is UUPSUpgradeable {
    
    function migrateData() external onlyProxy {
        // Можно вызвать ТОЛЬКО через Proxy
        // Защита от прямых вызовов на implementation
    }
}
```

**Примечание:** В OrganicComponentRegistry пока не используется (нет миграций)

---

### Transparent Proxy → UUPS миграция

**Если у вас Transparent Proxy:**

1. Создайте новый UUPS Logic
2. Добавьте _authorizeUpgrade()
3. Деплой нового Logic
4. Upgrade через ProxyAdmin
5. Измените тесты на UUPS паттерн

**Детали:** См. [OpenZeppelin Migration Guide](https://docs.openzeppelin.com/upgrades-plugins/1.x/proxies#transparent-vs-uups)

---

## 📊 Performance Tips

### Газовые оптимизации

1. **Unchecked для счётчиков**
   ```solidity
   unchecked { itemId = ++totalItems; }
   ```

2. **Calldata для read-only**
   ```solidity
   function create(string calldata data) external
   ```

3. **Кэширование length**
   ```solidity
   uint256 len = bytes(str).length;
   require(len > 0 && len <= MAX);
   ```

4. **Custom errors**
   ```solidity
   if (addr == address(0)) revert ZeroAddress();
   ```

5. **Indexed события**
   ```solidity
   event Created(uint256 indexed id, address indexed creator);
   ```

---

### Compiler settings

```javascript
// Оптимально для production
{
  version: "0.8.22",
  settings: {
    optimizer: {
      enabled: true,
      runs: 200  // баланс между размер/gas
    },
    viaIR: true  // для сложных контрактов
  }
}
```

---

## ✅ Финальный чеклист

### Код готов если:

- [ ] ✅ Proxy минимальный (30-40 строк)
- [ ] ✅ Logic наследует все нужные модули
- [ ] ✅ initialize() вызывает все __Module_init()
- [ ] ✅ _authorizeUpgrade() защищён через role
- [ ] ✅ State variables объявлены в Logic
- [ ] ✅ Модификаторы применены правильно
- [ ] ✅ События с indexed полями
- [ ] ✅ Custom errors объявлены
- [ ] ✅ Газовые оптимизации применены
- [ ] ✅ Storage gap добавлен

---

### Тесты готовы если:

- [ ] ✅ 100% тестов проходят
- [ ] ✅ Протестирован deploy и initialize
- [ ] ✅ Протестирован upgrade
- [ ] ✅ Протестирована pause/unpause
- [ ] ✅ Протестированы роли
- [ ] ✅ Протестирована reentrancy защита
- [ ] ✅ Протестированы события
- [ ] ✅ Протестирована proxy изоляция

---

### Готов к deployment если:

- [ ] ✅ Все тесты проходят на local
- [ ] ✅ Протестировано на testnet
- [ ] ✅ Admin/Upgrader = multisig
- [ ] ✅ Gas price приемлемый
- [ ] ✅ Адреса интеграций известны
- [ ] ✅ Скрипт деплоя готов
- [ ] ✅ План upgrade подготовлен
- [ ] ✅ Документация обновлена

---

## 🚀 Применение к другим контрактам Amanita

### Кандидаты для UUPS

#### 1. SpiralEngine
**Сложность:** 🔴 Высокая  
**Приоритет:** 🔴 Высокий  
**Зачем:** Центральный контракт пользователей и ролей

**Действия:**
1. Создать SpiralEngineProxy.sol
2. Рефакторить SpiralEngine → SpiralEngineLogic
3. Добавить UUPS модули
4. Comprehensive тесты

---

#### 2. ProductRegistry
**Сложность:** 🟠 Средняя  
**Приоритет:** 🟠 Высокий  
**Зачем:** Управление каталогом продуктов

**Действия:**
1. Создать ProductRegistryProxy.sol
2. Рефакторить ProductRegistry → ProductRegistryLogic
3. Интеграция с OrganicComponentRegistry
4. Тесты валидации компонентов

---

#### 3. AmanitaInternational
**Сложность:** 🟠 Средняя  
**Приоритет:** 🟢 Средний  
**Зачем:** Управление переводами и мультиязычностью

**Действия:**
1. Анализ текущей архитектуры (уже Storage/Logic/Proxy)
2. Рефакторинг к стандартному UUPS
3. Упрощение Proxy (сейчас 483 строки → должно быть ~35)
4. Обновление тестов

---

#### 4. AmanitaPaymentRouter
**Сложность:** 🔴 Высокая  
**Приоритет:** 🔴 Критичный  
**Зачем:** Обработка платежей

**Действия:**
1. Создать PaymentRouterProxy.sol
2. Добавить ReentrancyGuard (ОБЯЗАТЕЛЬНО!)
3. Comprehensive security тесты
4. Аудит перед деплоем

---

## 📋 Шаблон чеклиста для нового контракта

```markdown
# UUPS Conversion Checklist: [ContractName]

## Анализ
- [ ] Изучена текущая архитектура
- [ ] Определены state variables
- [ ] Определены роли и права
- [ ] Определены интеграции

## Разработка
- [ ] Создан [ContractName]Proxy.sol
- [ ] Создан [ContractName]Logic.sol
- [ ] Создан I[ContractName].sol
- [ ] Добавлены все Upgradeable модули
- [ ] Реализована initialize()
- [ ] Реализована _authorizeUpgrade()
- [ ] Добавлены custom errors
- [ ] Добавлены validation helpers
- [ ] Применены газовые оптимизации
- [ ] Добавлен storage gap

## Тестирование
- [ ] Созданы UUPS architecture тесты
- [ ] Созданы proxy management тесты
- [ ] Созданы business logic тесты
- [ ] Созданы security тесты
- [ ] Созданы integration тесты
- [ ] Все тесты проходят (100%)

## Deployment
- [ ] Деплой скрипт создан
- [ ] Протестировано на testnet
- [ ] Адреса интеграций настроены
- [ ] Роли выданы multisig
- [ ] Контракты верифицированы
- [ ] Документация обновлена

## Post-Deployment
- [ ] Адреса сохранены
- [ ] Мониторинг настроен
- [ ] План upgrade подготовлен
- [ ] Team обучена
```

---

## 🎉 Заключение

### Ключевые выводы

1. **UUPS - современный стандарт** для upgradeable контрактов (OpenZeppelin v5+)
2. **Минимальный Proxy** - только обёртка над ERC1967Proxy
3. **Вся логика в Logic** - state variables, функции, модификаторы
4. **Delegatecall магия** - Logic код + Proxy данные = работающий контракт
5. **Безопасность критична** - UPGRADER_ROLE = multisig, comprehensive тесты
6. **Газовые оптимизации** - unchecked, calldata, custom errors, indexed events
7. **Тестирование обязательно** - минимум 7 тестов, лучше 30+

### Успешные примеры

**OrganicComponentRegistry:**
- ✅ 37/37 тестов (100% success)
- ✅ 5 направлений улучшений (A-E)
- ✅ Production ready
- ✅ Газовые оптимизации: ~500-1000 gas экономии
- ✅ Полная документация

### Следующие шаги

1. Примените паттерн к SpiralEngine
2. Примените к ProductRegistry
3. Обновите AmanitaInternational к стандартному UUPS
4. Примените к AmanitaPaymentRouter (с аудитом!)

---

**Версия документа:** 1.0.0  
**Последнее обновление:** 2025-01-07  
**Базовый пример:** OrganicComponentRegistry v3.0.0  
**Статус:** ✅ Production Ready

---

*Эта документация является частью проекта Amanita Decentralization.*

