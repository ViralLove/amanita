# Инфраструктура тестирования контрактов Amanita

## 📋 Обзор

Данный документ описывает инфраструктурные решения для тестирования смарт-контрактов в экосистеме Amanita, основанные на анализе существующих тестовых файлов.

## 🏗️ Архитектура тестирования

### 1. Технологический стек

```yaml
testing_framework:
  primary: "Hardhat + Ethers.js"
  assertion_library: "Chai (expect, assert)"
  test_runner: "Mocha"
  environment: "Node.js"
  
blockchain_environment:
  local: "Hardhat Network"
  testnet: "Polygon Mumbai"
  mainnet: "Polygon"
```

### 2. Структура тестового окружения

```
test/
├── ProductRegistryClearCatalog.simple.test.js  # Интеграционные тесты
├── ProductRegistryClearCatalog.test.js         # Unit тесты
└── [другие тестовые файлы]
```

## 🔧 Инфраструктурные компоненты

### 1. Управление окружением

#### Переменные окружения (.env)
```bash
# Ключи доступа
DEPLOYER_PRIVATE_KEY=0x...                    # Приватный ключ деплоера
SELLER_PRIVATE_KEY=0x...                      # Приватный ключ селлера (опционально)

# Адреса контрактов
PRODUCT_REGISTRY_CONTRACT_ADDRESS=0x...       # Адрес ProductRegistry
INVITE_NFT_CONTRACT_ADDRESS=0x...             # Адрес InviteNFT
LOVECOIN_REGISTRY_CONTRACT_ADDRESS=0x...       # Адрес AmanitaRegistry

# Сеть
HARDHAT_NETWORK=localhost                     # Сеть для тестирования
```

#### Валидация окружения
```javascript
// Проверка обязательных переменных
const deployerPrivateKey = process.env.DEPLOYER_PRIVATE_KEY;
if (!deployerPrivateKey) {
    throw new Error("DEPLOYER_PRIVATE_KEY not found in environment variables");
}
```

### 2. Управление кошельками

#### Создание кошельков
```javascript
// Деплоер из .env
const deployer = new ethers.Wallet(deployerPrivateKey, ethers.provider);

// Тестовые аккаунты из Hardhat
const [seller, buyer, admin] = await ethers.getSigners();
```

#### Роли и права доступа
```javascript
// Определение ролей
const SELLER_ROLE = ethers.keccak256(ethers.toUtf8Bytes("SELLER_ROLE"));
const ACTIVATOR_ROLE = ethers.keccak256(ethers.toUtf8Bytes("ACTIVATOR_ROLE"));

// Проверка ролей
const hasRole = await contract.hasRole(SELLER_ROLE, address);
```

### 3. Подключение к контрактам

#### Attach к существующим контрактам
```javascript
// Получение адреса из окружения
const contractAddress = process.env.CONTRACT_ADDRESS;

// Создание фабрики контракта
const ContractFactory = await ethers.getContractFactory("ContractName");

// Подключение к существующему контракту
const contract = ContractFactory.attach(contractAddress);
```

#### Deploy новых контрактов (для unit тестов)
```javascript
// Деплой нового контракта
const contract = await ContractFactory.deploy();
await contract.waitForDeployment();
```

## 🧪 Паттерны тестирования

### 1. Интеграционное тестирование

#### Структура интеграционного теста
```javascript
describe("Contract Integration Test", function () {
    let contract;
    let deployer;
    let user;

    beforeEach(async function () {
        // 1. Настройка окружения
        // 2. Подключение к контрактам
        // 3. Инициализация пользователей
        // 4. Настройка ролей и прав
    });

    it("Should perform integration test", async function () {
        // 1. Подготовка данных
        // 2. Выполнение операции
        // 3. Валидация результата
        // 4. Проверка событий
    });
});
```

#### Активация пользователей
```javascript
// Активация через InviteNFT
const isActivated = await inviteNFT.isUserActivated(user.address);
if (!isActivated) {
    // Создание инвайта
    const testInviteCode = "TEST-INVITE-1234";
    await inviteNFT.connect(deployer).mintInvites([testInviteCode], 0);
    
    // Активация пользователя
    await inviteNFT.connect(deployer).activateAndMintInvites(
        testInviteCode,
        user.address,
        ["NEW-INVITE-1", "NEW-INVITE-2"],
        0
    );
}
```

### 2. Unit тестирование

#### Тестирование функций
```javascript
it("Should have correct function signature", async function () {
    const interface = contract.interface;
    const function = interface.getFunction("functionName");
    
    expect(function).to.not.be.undefined;
    expect(function.inputs.length).to.equal(expectedInputs);
    expect(function.inputs[0].type).to.equal("address");
});
```

#### Тестирование событий
```javascript
it("Should emit correct event", async function () {
    const interface = contract.interface;
    const event = interface.getEvent("EventName");
    
    expect(event).to.not.be.undefined;
    expect(event.inputs.length).to.equal(expectedInputs);
    expect(event.inputs[0].name).to.equal("paramName");
});
```

### 3. Тестирование безопасности

#### Access Control тестирование
```javascript
it("Should have proper access control", async function () {
    try {
        await contract.connect(unauthorizedUser).restrictedFunction();
        expect.fail("Function should require proper role");
    } catch (error) {
        expect(error.message).to.include("Not authorized");
    }
});
```

#### Валидация параметров
```javascript
it("Should validate input parameters", async function () {
    // Тестирование с невалидными параметрами
    await expect(contract.functionWithValidation("invalid"))
        .to.be.revertedWith("Invalid parameter");
});
```

## 🔄 Жизненный цикл тестов

### 1. Подготовка (beforeEach)
```javascript
beforeEach(async function () {
    // 1. Валидация окружения
    // 2. Создание кошельков
    // 3. Подключение к контрактам
    // 4. Настройка ролей
    // 5. Инициализация тестовых данных
});
```

### 2. Выполнение теста
```javascript
it("Should perform test", async function () {
    // 1. Подготовка тестовых данных
    // 2. Выполнение операции
    // 3. Ожидание подтверждения
    // 4. Валидация результата
    // 5. Проверка событий
});
```

### 3. Очистка (afterEach)
```javascript
afterEach(async function () {
    // 1. Очистка тестовых данных
    // 2. Сброс состояния
    // 3. Освобождение ресурсов
});
```

## 📊 Мониторинг и логирование

### 1. Структурированное логирование
```javascript
console.log("🔷 Активируем продавца...");
console.log("✅ Роль SELLER_ROLE назначена продавцу");
console.log("⚠️ Ошибка при активации:", error.message);
console.log("🎉 Тест завершен успешно!");
```

### 2. Детальная валидация
```javascript
// Проверка состояния до операции
const stateBefore = await contract.getState();
console.log(`Состояние до операции: ${stateBefore}`);

// Выполнение операции
await contract.performOperation();

// Проверка состояния после операции
const stateAfter = await contract.getState();
console.log(`Состояние после операции: ${stateAfter}`);

// Валидация изменений
assert(stateAfter !== stateBefore, "Состояние должно измениться");
```

## 🚀 Запуск тестов

### 1. Локальное тестирование
```bash
# Запуск всех тестов
npx hardhat test

# Запуск конкретного теста
npx hardhat test test/ProductRegistryClearCatalog.simple.test.js

# Запуск с детальным выводом
npx hardhat test --verbose
```

### 2. Тестирование на тестнете
```bash
# Настройка сети
export HARDHAT_NETWORK=mumbai

# Запуск тестов
npx hardhat test --network mumbai
```

### 3. CI/CD интеграция
```yaml
# .github/workflows/test.yml
name: Contract Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Setup Node.js
        uses: actions/setup-node@v2
        with:
          node-version: '18'
      - name: Install dependencies
        run: npm install
      - name: Run tests
        run: npx hardhat test
        env:
          DEPLOYER_PRIVATE_KEY: ${{ secrets.DEPLOYER_PRIVATE_KEY }}
          PRODUCT_REGISTRY_CONTRACT_ADDRESS: ${{ secrets.PRODUCT_REGISTRY_ADDRESS }}
```

## 🔧 Конфигурация Hardhat

### hardhat.config.js
```javascript
require("@nomicfoundation/hardhat-toolbox");
require("dotenv").config();

module.exports = {
  solidity: "0.8.20",
  networks: {
    localhost: {
      url: "http://127.0.0.1:8545"
    },
    mumbai: {
      url: process.env.MUMBAI_RPC_URL,
      accounts: [process.env.DEPLOYER_PRIVATE_KEY]
    }
  },
  mocha: {
    timeout: 40000
  }
};
```

## 📈 Метрики и отчеты

### 1. Покрытие кода
```bash
# Установка инструмента покрытия
npm install --save-dev solidity-coverage

# Запуск с покрытием
npx hardhat coverage
```

### 2. Gas оптимизация
```bash
# Анализ gas
npx hardhat test --gas-report
```

### 3. Производительность
```javascript
// Измерение времени выполнения
const startTime = Date.now();
await contract.operation();
const endTime = Date.now();
console.log(`Операция выполнена за ${endTime - startTime}ms`);
```

## 🛡️ Безопасность тестирования

### 1. Изоляция тестов
- Каждый тест должен быть независимым
- Использование beforeEach для сброса состояния
- Очистка данных после тестов

### 2. Управление ключами
- Использование переменных окружения
- Никогда не коммитить приватные ключи
- Использование тестовых кошельков

### 3. Валидация результатов
- Проверка всех аспектов операции
- Валидация событий
- Проверка состояния контракта

## 📚 Лучшие практики

### 1. Структура тестов
- Группировка по функциональности
- Понятные названия тестов
- Документация сложных тестов

### 2. Обработка ошибок
- Ожидание конкретных ошибок
- Валидация сообщений об ошибках
- Graceful handling неожиданных ошибок

### 3. Поддержка
- Регулярное обновление зависимостей
- Документирование изменений
- Версионирование тестов

## 🔮 Будущие улучшения

### 1. Автоматизация
- Автоматический деплой тестовых контрактов
- Параллельное выполнение тестов
- Интеграция с мониторингом

### 2. Расширенная аналитика
- Детальные отчеты по тестам
- Метрики производительности
- Анализ покрытия кода

### 3. Интеграция
- CI/CD пайплайны
- Уведомления о результатах
- Интеграция с системами мониторинга

---

**Версия документа:** 1.0  
**Дата обновления:** 2024-01-XX  
**Автор:** AI Assistant  
**Статус:** Активный
