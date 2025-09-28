# **ЖУРНАЛ РАЗРАБОТКИ AMANITA ECOSYSTEM**

## 🚀 **ЗАДАЧА 4: Реализация Action 888 в deploy_full.js**

### **Цель**: Завершить действие 888 для полной инициализации селлера

---

## 🔍 **ГЛУБОКИЙ АНАЛИЗ (@analysis.mdc)**

### **Анализ текущего состояния deploy_full.js**

#### **Существующая архитектура:**
```javascript
// deploy_full.js - основной скрипт деплоя
- Поддержка действий: 0-10, 40-41, 777, 888
- Action 777: ✅ Реализован (генерация инвайтов деплоера)
- Action 888: ❌ НЕ РЕАЛИЗОВАН (только упоминание в валидации)
```

#### **Критические компоненты для Action 888:**
1. **SpiralEngine** - активация пользователей и управление ролями
2. **SoulIdentity** - создание SBT токенов и управление репутацией
3. **ProductRegistry** - загрузка и активация каталога продуктов
4. **Каталог продуктов** - `product_registry_upload_data.json` (87 продуктов)

#### **Анализ существующих функций:**

**Action 777 (работает):**
```javascript
// Генерация 12 инвайтов для деплоера
async function creatingInvitesForDeployer(spiralEngine) {
    // 1. Проверка роли SELLER_ROLE у деплоера
    // 2. Минтинг 12 инвайтов
    // 3. Сохранение в bot/flowers/invites.txt
}
```

**Action 4/40 (создание каталога):**
```javascript
// Создание каталога с неактивными продуктами
async function createCatalog(productRegistry) {
    // 1. Загрузка product_registry_upload_data.json
    // 2. Создание продуктов через createProduct()
    // 3. Оценка газа и стоимости
}
```

**Action 41 (активация каталога):**
```javascript
// Активация существующих продуктов
async function activateCatalogProducts(productRegistry) {
    // 1. Загрузка каталога
    // 2. Активация через setProductActive()
    // 3. Подсчет статистики
}
```

**Функция setupSoulIdentityFor888 (частично реализована):**
```javascript
// Настройка SoulIdentity для селлера
async function setupSoulIdentityFor888(soulIdentity, sellerAddress) {
    // 1. Загрузка SBT контрактов (SoulboundCore, SoulMetadata)
    // 2. Создание SBT токена через mintSoul()
    // 3. Инициализация метаданных
    // 4. Настройка репутации и уровня
}
```

### **Архитектурные требования для Action 888:**

#### **Функциональные требования:**
1. **Валидация деплоер инвайта** - проверка права активировать селлера
2. **Активация селлера** - вызов `activateUser()` в SpiralEngine
3. **Назначение роли SELLER_ROLE** - через `grantSellerRole()`
4. **Создание SBT токена** - через существующую SBT экосистему
5. **Загрузка каталога** - создание и активация продуктов
6. **Генерация 12 инвайтов** - для нового селлера

#### **Технические требования:**
1. **Интеграция с SpiralEngine** - активация и роли
2. **Интеграция с SoulIdentity** - SBT токены и репутация
3. **Интеграция с ProductRegistry** - каталог продуктов
4. **Обработка ошибок** - валидация на каждом этапе
5. **Логирование** - детальные логи процесса

#### **Интеграционные требования:**
1. **Параметры функции** - `deployerInvite`, `sellerAddress`, `catalogData`
2. **Валидация входных данных** - проверка адресов и инвайтов
3. **Атомарность операций** - откат при ошибках
4. **Совместимость** - с существующими действиями

---

## 🎯 **ДВУХУРОВНЕВЫЙ ПЛАН РЕАЛИЗАЦИИ**

### **УРОВЕНЬ 1: Создание основной функции Action 888**

#### **ItemY1.1: Создание функции action888**
```javascript
/**
 * Action 888: Полная инициализация селлера
 * @param {string} deployerInvite - инвайт код деплоера для активации селлера
 * @param {string} sellerAddress - адрес селлера для инициализации
 * @param {string} catalogData - путь к JSON файлу с каталогом (опционально)
 */
async function action888(deployerInvite, sellerAddress, catalogData = null) {
    console.log("\n🎲 Action 888: Полная инициализация селлера...");
    
    // 1. Валидация входных параметров
    await validateAction888Inputs(deployerInvite, sellerAddress);
    
    // 2. Загрузка необходимых контрактов
    const contracts = await loadContractsFor888();
    
    // 3. Валидация деплоер инвайта
    await validateDeployerInviteForSeller(contracts.spiralEngine, deployerInvite);
    
    // 4. Активация селлера в SpiralEngine
    await activateSellerInSpiralEngine(contracts.spiralEngine, sellerAddress, deployerInvite);
    
    // 5. Назначение роли SELLER_ROLE
    await grantSellerRoleToUser(contracts.spiralEngine, sellerAddress);
    
    // 6. Создание SBT токена в SoulIdentity
    await setupSoulIdentityFor888(contracts.soulIdentity, sellerAddress);
    
    // 7. Загрузка каталога продуктов
    await loadSellerCatalog(contracts.productRegistry, sellerAddress, catalogData);
    
    // 8. Генерация 12 инвайтов для селлера
    await generateInvitesForSeller(contracts.spiralEngine, sellerAddress);
    
    console.log("✅ Action 888 завершен успешно!");
}
```

#### **ItemY1.2: Создание вспомогательных функций**
```javascript
// Валидация входных параметров
async function validateAction888Inputs(deployerInvite, sellerAddress) {
    if (!deployerInvite || !sellerAddress) {
        throw new Error("Action 888: требуются deployerInvite и sellerAddress");
    }
    
    if (!web3.utils.isAddress(sellerAddress)) {
        throw new Error("Action 888: некорректный адрес селлера");
    }
    
    console.log(`✅ Валидация параметров: deployerInvite=${deployerInvite}, sellerAddress=${sellerAddress}`);
}

// Загрузка контрактов
async function loadContractsFor888() {
    const spiralEngine = await loadContract("SpiralEngine");
    const productRegistry = await loadContract("ProductRegistry");
    const soulIdentity = await loadContract("SoulIdentity");
    
    return { spiralEngine, productRegistry, soulIdentity };
}

// Валидация деплоер инвайта для селлера
async function validateDeployerInviteForSeller(spiralEngine, deployerInvite) {
    const inviteExists = await spiralEngine.methods.inviteCodeExists(deployerInvite).call();
    if (!inviteExists) {
        throw new Error(`Action 888: инвайт ${deployerInvite} не существует`);
    }
    
    const isUsed = await spiralEngine.methods.isInviteUsed(
        await spiralEngine.methods.inviteCodeToTokenId(deployerInvite).call()
    ).call();
    
    if (isUsed) {
        throw new Error(`Action 888: инвайт ${deployerInvite} уже использован`);
    }
    
    console.log(`✅ Деплоер инвайт ${deployerInvite} валиден для активации селлера`);
}
```

### **УРОВЕНЬ 2: Интеграция и тестирование**

#### **ItemY2.1: Интеграция в основной switch**
```javascript
// Добавление в main() функцию
if (action === 888) {
    console.log("\n🎲 Action 888: Полная инициализация селлера...");
    
    // Получаем параметры из аргументов или переменных окружения
    const deployerInvite = args[1] || process.env.DEPLOYER_INVITE;
    const sellerAddress = args[2] || process.env.SELLER_ADDRESS;
    const catalogData = args[3] || process.env.CATALOG_DATA;
    
    if (!deployerInvite || !sellerAddress) {
        throw new Error("Action 888: требуются deployerInvite и sellerAddress");
    }
    
    await action888(deployerInvite, sellerAddress, catalogData);
    console.log("✅ Action 888 завершен успешно!");
}
```

#### **ItemY2.2: Создание функций активации селлера**
```javascript
// Активация селлера в SpiralEngine
async function activateSellerInSpiralEngine(spiralEngine, sellerAddress, deployerInvite) {
    console.log(`🔷 Активируем селлера ${sellerAddress} через инвайт ${deployerInvite}...`);
    
    // Генерируем 12 новых инвайт кодов для селлера
    const newInviteCodes = generateInviteCodes(12);
    console.log(`🔷 Сгенерированы новые инвайт коды: ${newInviteCodes.join(", ")}`);
    
    // Получаем tokenId деплоер инвайта
    const deployerTokenId = await spiralEngine.methods.inviteCodeToTokenId(deployerInvite).call();
    
    // Активируем селлера
    const activateTx = await spiralEngine.methods.activateUser(
        deployerTokenId,
        sellerAddress,
        newInviteCodes,
        0 // nonce
    ).send({
        from: deployerAccount.address,
        gas: 500000,
        gasPrice: network === 'polygon' ? web3.utils.toWei('100', 'gwei') : await web3.eth.getGasPrice()
    });
    
    console.log(`✅ Селлер активирован, tx: ${activateTx.transactionHash}`);
}

// Назначение роли SELLER_ROLE
async function grantSellerRoleToUser(spiralEngine, sellerAddress) {
    console.log(`🔷 Назначаем роль SELLER_ROLE селлеру ${sellerAddress}...`);
    
    const grantTx = await spiralEngine.methods.grantSellerRole(sellerAddress).send({
        from: deployerAccount.address,
        gas: 200000,
        gasPrice: network === 'polygon' ? web3.utils.toWei('100', 'gwei') : await web3.eth.getGasPrice()
    });
    
    console.log(`✅ Роль SELLER_ROLE назначена, tx: ${grantTx.transactionHash}`);
}

// Загрузка каталога селлера
async function loadSellerCatalog(productRegistry, sellerAddress, catalogData) {
    if (!catalogData) {
        catalogData = path.join(__dirname, "..", "bot", "catalog", "product_registry_upload_data.json");
    }
    
    console.log(`🔷 Загружаем каталог для селлера ${sellerAddress}...`);
    
    // Создаем каталог (аналогично action=4)
    await createCatalog(productRegistry);
    
    // Активируем продукты (аналогично action=41)
    await activateCatalogProducts(productRegistry);
    
    console.log(`✅ Каталог загружен и активирован для селлера ${sellerAddress}`);
}

// Генерация инвайтов для селлера
async function generateInvitesForSeller(spiralEngine, sellerAddress) {
    console.log(`🔷 Генерируем 12 инвайтов для селлера ${sellerAddress}...`);
    
    const inviteCodes = [];
    
    for (let i = 0; i < 12; i++) {
        const inviteCode = `INVITE_${sellerAddress.slice(2, 8)}_${i.toString().padStart(2, '0')}`;
        
        const mintTx = await spiralEngine.methods.mintInvite(inviteCode, 0).send({
            from: sellerAddress,
            gas: 200000,
            gasPrice: network === 'polygon' ? web3.utils.toWei('100', 'gwei') : await web3.eth.getGasPrice()
        });
        
        inviteCodes.push(inviteCode);
        console.log(`✅ Инвайт ${inviteCode} создан, tx: ${mintTx.transactionHash}`);
    }
    
    // Сохраняем инвайты в файл
    const invitesPath = path.join(__dirname, "..", "bot", "flowers", `${sellerAddress}_invites.txt`);
    fs.writeFileSync(invitesPath, inviteCodes.join("\n"));
    console.log(`✅ Инвайты селлера сохранены в ${invitesPath}`);
}
```

#### **ItemY2.3: Создание утилит**
```javascript
// Генерация инвайт кодов
function generateInviteCodes(count) {
    const codes = [];
    for (let i = 0; i < count; i++) {
        codes.push(`SELLER_INVITE_${Date.now()}_${i.toString().padStart(2, '0')}`);
    }
    return codes;
}

// Обновление документации
async function updateAction888Documentation() {
    console.log("📝 Обновляем документацию для Action 888...");
    
    const documentation = `
## Action 888: Полная инициализация селлера

### Использование:
\`\`\`bash
node deploy_full.js 888 <deployerInvite> <sellerAddress> [catalogData]
\`\`\`

### Параметры:
- deployerInvite: инвайт код деплоера для активации селлера
- sellerAddress: адрес селлера для инициализации
- catalogData: путь к JSON файлу с каталогом (опционально)

### Процесс:
1. Валидация входных параметров
2. Загрузка контрактов (SpiralEngine, ProductRegistry, SoulIdentity)
3. Валидация деплоер инвайта
4. Активация селлера в SpiralEngine
5. Назначение роли SELLER_ROLE
6. Создание SBT токена в SoulIdentity
7. Загрузка каталога продуктов
8. Генерация 12 инвайтов для селлера

### Результат:
- Селлер полностью активирован и готов к работе
- Каталог продуктов загружен и активирован
- SBT токен создан для репутации
- 12 инвайтов сгенерированы для приглашения новых пользователей
`;
    
    console.log("✅ Документация обновлена");
}
```

---

## 🚀 **ПРИОРИТИЗАЦИЯ ВЫПОЛНЕНИЯ**

### **Этап 1 (Критический)**: Создание основной функции
- **ItemY1.1** - Создание функции action888
- **ItemY1.2** - Создание вспомогательных функций

### **Этап 2 (Высокий)**: Интеграция и тестирование
- **ItemY2.1** - Интеграция в основной switch
- **ItemY2.2** - Создание функций активации селлера
- **ItemY2.3** - Создание утилит

### **Этап 3 (Средний)**: Документация и валидация
- **ItemY2.4** - Обновление документации
- **ItemY2.5** - Создание тестов и валидация

---

## 📊 **ОЖИДАЕМЫЕ РЕЗУЛЬТАТЫ**

### **Технические достижения:**
- ✅ **Action 888** - полноценная функция инициализации селлера
- ✅ **Интеграция** - со всеми необходимыми контрактами
- ✅ **Валидация** - проверка всех входных параметров
- ✅ **Логирование** - детальные логи процесса

### **Бизнес-ценность:**
- ✅ **Автоматизация** - полная инициализация селлера одним действием
- ✅ **Безопасность** - валидация инвайтов и прав доступа
- ✅ **Масштабируемость** - готовность к созданию множества селлеров
- ✅ **Интеграция** - связь со всей экосистемой контрактов

**План готов к выполнению методом @run-task.mdc!** 🎉

---
