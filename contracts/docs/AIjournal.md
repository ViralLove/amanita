## 🔄 **ЗАДАЧА 1: Рефакторинг токеномики - Lovecoin как основной токен**

### **Цель**: Вернуть Lovecoin как основной токен экосистемы с социальным-майнингом (не путать с логикой бизнес майнинга который будет передан в AmanitaCoin и основан на системах лояльности)

---

## 🔍 **ГЛУБОКИЙ АНАЛИЗ (@analysis.mdc)**

### **Анализ текущего состояния токенов**

#### **Текущая архитектура токенов:**
```solidity
// AmanitaToken.sol - ТЕКУЩИЙ ОСНОВНОЙ ТОКЕН
contract AmanitaToken is ERC20, AccessControl {
    bytes32 public constant MINTER_ROLE = keccak256("MINTER_ROLE");
    uint256 public constant INITIAL_SUPPLY = 888_888_888 ether;
    
    constructor(address owner) ERC20("Amanita", "AMANITA") {
        _mint(owner, INITIAL_SUPPLY);
        _grantRole(DEFAULT_ADMIN_ROLE, owner);
        _grantRole(MINTER_ROLE, owner);
    }
    
    function mint(address to, uint256 amount) external onlyRole(MINTER_ROLE)
    function burn(address from, uint256 amount) external onlyRole(MINTER_ROLE)
}

// Lovecoin.sol - ПУСТОЙ ФАЙЛ (1 строка)
// Нужно создать полноценный контракт
```

#### **Критические интеграции:**
1. **LoveEmissionEngine.sol** - основная интеграция:
   ```solidity
   IERC20 public immutable amanitaToken;  // ← НУЖНО ЗАМЕНИТЬ НА LOVECOIN
   function claimAMANITA() external {     // ← НУЖНО ПЕРЕИМЕНОВАТЬ
       bool success = amanitaToken.transfer(msg.sender, amount);
   }
   ```

2. **Документация** - 4 файла содержат ссылки на AMANITA:
   - `AmanitaTokens.md` - полная документация токенов
   - `LoveEmissionEngine.md` - интеграция с эмиссией
   - `LoveDoPostNFT.md` - упоминания в контексте эмиссии
   - `testing-infrastructure.md` - переменные окружения

#### **Бизнес-логика токеномики:**
- **$LOVE** - утилити токен для социального майнинга через суперлайки
- **$LGOV** - governance токен для управления экосистемой
- **Механизм эмиссии**: 1 LOVE + 1 LGOV за суперлайк в LoveDoPostNFT
- **Клейм**: LOVE можно клеймить многократно, LGOV - при формировании репутации (эта логика еще не разработана)

### **Архитектурные требования для Lovecoin:**

#### **Функциональные требования:**
1. **Социальный майнинг** - эмиссия через суперлайки в LoveDoPostNFT
3. **Совместимость с LoveEmissionEngine** - замена AmanitaToken без изменения логики
4. **Стандарт ERC20** - полная совместимость с существующей экосистемой

#### **Технические требования:**
1. **MINTER_ROLE** - для эмиссии через LoveEmissionEngine
2. **DEFAULT_ADMIN_ROLE** - для управления ролями
3. **Начальная эмиссия** - 888,888,888 LOVECOIN (как у AMANITA)
4. **Децимали** - 18 (стандарт)
5. **События** - Transfer, Approval (стандартные ERC20)

#### **Интеграционные требования:**
1. **LoveEmissionEngine** - замена `amanitaToken` на `lovecoin`
2. **Функция claimAMANITA** → `claimLOVECOIN`
3. **События** - обновление названий событий
4. **Документация** - полное обновление всех ссылок

---

## 🎯 **ДВУХУРОВНЕВЫЙ ПЛАН РЕАЛИЗАЦИИ**

### **УРОВЕНЬ 1: Создание Lovecoin контракта**

#### **ItemY1.1: Создание базового Lovecoin.sol**
```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "@openzeppelin/contracts/access/AccessControl.sol";

contract Lovecoin is ERC20, AccessControl {
    bytes32 public constant MINTER_ROLE = keccak256("MINTER_ROLE");
    
    uint256 public constant INITIAL_SUPPLY = 888_888_888 ether;
    
    constructor(address owner) ERC20("Lovecoin", "LOVECOIN") {
        _mint(owner, INITIAL_SUPPLY);
        _grantRole(DEFAULT_ADMIN_ROLE, owner);
        _grantRole(MINTER_ROLE, owner);
    }
    
    function decimals() public view virtual override returns (uint8) {
        return 18;
    }
    
    function mint(address to, uint256 amount) external onlyRole(MINTER_ROLE) {
        _mint(to, amount);
    }
    
    function burn(address from, uint256 amount) external onlyRole(MINTER_ROLE) {
        _burn(from, amount);
    }
    
    function supportsInterface(bytes4 interfaceId)
        public
        view
        override(AccessControl)
        returns (bool)
    {
        return super.supportsInterface(interfaceId);
    }
}
```

#### **ItemY1.2: Создание тестов для Lovecoin**
```javascript
// contracts/tests/Lovecoin.test.js
describe("Lovecoin", () => {
    describe("P0: Core Token Functions", () => {
        // mint(), burn(), transfer(), approve()
    });
    describe("P1: Access Control", () => {
        // MINTER_ROLE, DEFAULT_ADMIN_ROLE
    });
    describe("P2: Integration", () => {
        // SpiralEngine integration, role management
    });
    describe("P3: Edge Cases", () => {
        // Gas optimization, error handling
    });
});
```

### **УРОВЕНЬ 2: Интеграция и рефакторинг**

#### **ItemY2.1: Обновление LoveEmissionEngine**
```solidity
// Замена импорта
- import "./AmanitaToken.sol";
+ import "./Lovecoin.sol";

// Замена переменной
- IERC20 public immutable amanitaToken;
+ IERC20 public immutable lovecoin;

// Замена конструктора
- amanitaToken = IERC20(_amanita);
+ lovecoin = IERC20(_lovecoin);

// Переименование функции
- function claimAMANITA() external
+ function claimLOVECOIN() external

// Обновление логики
- bool success = amanitaToken.transfer(msg.sender, amount);
+ bool success = lovecoin.transfer(msg.sender, amount);

// Обновление событий
- event ClaimedAMANITA(address indexed seller, uint256 amount);
+ event ClaimedLOVECOIN(address indexed seller, uint256 amount);
```

#### **ItemY2.2: Обновление всех ссылок в коде**
1. **Поиск всех файлов** с упоминанием AMANITA/amanitaToken
2. **Систематическая замена** на LOVECOIN/lovecoin
3. **Обновление комментариев** и документации
4. **Валидация синтаксиса** после изменений

#### **ItemY2.3: Обновление документации**
1. **AmanitaTokens.md** → **LovecoinTokens.md**
2. **LoveEmissionEngine.md** - обновление интеграции
3. **LoveDoPostNFT.md** - обновление контекста эмиссии
4. **testing-infrastructure.md** - обновление переменных

#### **ItemY2.4: Создание системы тестов**
```javascript
// Полноценная система тестов по методологии @test-to-success.mdc
describe("Lovecoin Integration Tests", () => {
    describe("P0: LoveEmissionEngine Integration", () => {
        // Тестирование эмиссии через суперлайки
    });
    describe("P1: SpiralEngine Integration", () => {
        // Тестирование ролей и доступов
    });
    describe("P2: Social Mining", () => {
        // Тестирование социального майнинга
    });
    describe("P3: Edge Cases", () => {
        // Тестирование граничных случаев
    });
});
```

---

## 🚀 **ПРИОРИТИЗАЦИЯ ВЫПОЛНЕНИЯ**

### **Этап 1 (Критический)**: Создание Lovecoin
- **ItemY1.1** - Создание базового контракта
- **ItemY1.2** - Базовые тесты контракта

### **Этап 2 (Высокий)**: Интеграция
- **ItemY2.1** - Обновление LoveEmissionEngine
- **ItemY2.2** - Обновление всех ссылок

### **Этап 3 (Средний)**: Документация и тесты
- **ItemY2.3** - Обновление документации
- **ItemY2.4** - Полноценная система тестов

---

## 📊 **ОЖИДАЕМЫЕ РЕЗУЛЬТАТЫ**

### **Технические достижения:**
- ✅ **Lovecoin.sol** - полноценный ERC20 токен
- ✅ **100% совместимость** с существующей экосистемой
- ✅ **Обновленный LoveEmissionEngine** с социальным майнингом
- ✅ **Полная документация** и система тестов

### **Бизнес-ценность:**
- ✅ **Четкое разделение** токеномики (Lovecoin vs AmanitaCoin)
- ✅ **Социальный майнинг** через суперлайки
- ✅ **Готовность к бизнес-майнингу** в будущем
- ✅ **Масштабируемая архитектура** токенов

**План готов к выполнению методом @run-task.mdc!** 🎉

---
