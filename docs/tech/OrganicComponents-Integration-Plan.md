# 🔗 План интеграции OrganicComponentRegistry с AmanitaInternational и ProductRegistry

**Дата:** 2025-01-11  
**Статус:** 🟡 Планирование  
**Приоритет:** 🔴 Высокий

---

## 📊 Текущее состояние

### ❌ Проблемы:

1. **OrganicComponentRegistry НЕ использует AmanitaInternational** для переводов
   - Компоненты хранят `rootMetadataCID` - монолитный JSON на одном языке
   - `shareableData` (features, forms) - не мультиязычные JSON файлы
   - Адрес `amanitaInternational` сохранен, но НЕ используется

2. **ProductRegistry не связан с компонентами**
   - Нет поля `components` в структуре Product
   - Нет валидации компонентов при создании продукта
   - Нет мультиязычной поддержки

3. **Переводы разрознены**
   - Название компонента в IPFS JSON
   - Описание компонента в IPFS JSON
   - Features и Forms в отдельных IPFS файлах
   - Невозможно обновить перевод без смены CID

---

## 🎯 Цели интеграции

### **Главная цель:**
Сделать компоненты **полностью мультиязычными** с централизованным управлением переводами через `AmanitaInternational`.

### **Конкретные цели:**

1. ✅ **Мультиязычные названия компонентов** (EN, RU, DE, FR, ES, etc.)
2. ✅ **Мультиязычные описания** компонентов
3. ✅ **Мультиязычные features** (Organic, Wildcrafted, Lab-tested)
4. ✅ **Мультиязычные forms** (Powder, Tincture, Capsules)
5. ✅ **Валидация компонентов** в ProductRegistry
6. ✅ **Отслеживание использования** компонентов в продуктах

---

## 🏗️ Варианты решения

### **Вариант 1: Легковесная интеграция (Quick Win - 1-2 дня)**

**Что делаем:**
- Храним **названия и описания** компонентов в AmanitaInternational
- Технические данные остаются в IPFS (состав, сертификаты, изображения)
- Features и Forms переводим через AmanitaInternational
- Добавляем поле `components` в ProductRegistry

**Архитектура:**

```
OrganicComponentRegistry
├─ Component
│  ├─ blockchain_id
│  ├─ creator
│  ├─ business_id → "amanita_muscaria_powder"
│  ├─ technical_metadata_cid → IPFS CID (состав, сертификаты, изображения)
│  ├─ created_at
│  ├─ last_updated
│  ├─ status
│  └─ is_shared
│
└─ Переводы в AmanitaInternational:
   ├─ SimpleFields:
   │  ├─ "component.features" → CID (Organic, Wildcrafted, Lab-tested на всех языках)
   │  └─ "component.forms" → CID (Powder, Tincture, Capsules на всех языках)
   │
   └─ ComplexFields:
      ├─ "ComponentName.amanita_muscaria_powder.en" → "Amanita Muscaria Powder"
      ├─ "ComponentName.amanita_muscaria_powder.ru" → "Мухомор красный (порошок)"
      ├─ "ComponentDesc.amanita_muscaria_powder.en" → "Wildcrafted red fly agaric..."
      └─ "ComponentDesc.amanita_muscaria_powder.ru" → "Дикорастущий мухомор..."
```

**Преимущества:**
- ✅ Быстрая реализация (1-2 дня)
- ✅ Минимальные изменения в контрактах
- ✅ Обратная совместимость с существующими компонентами
- ✅ Централизованное управление переводами

**Недостатки:**
- ⚠️ Технические данные всё ещё в IPFS (но это OK для сертификатов, изображений)

---

### **Вариант 2: Полная миграция (2-3 недели)**

**Что делаем:**
- **ВСЕ данные** компонентов хранятся on-chain или через AmanitaInternational
- Только изображения и файлы сертификатов в IPFS
- Полная валидация данных на уровне смарт-контрактов

**Преимущества:**
- ✅ Максимальная децентрализация
- ✅ Полная валидация on-chain
- ✅ Быстрое чтение данных (без IPFS запросов)

**Недостатки:**
- ❌ Долгая реализация (2-3 недели)
- ❌ Высокие gas costs для записи данных
- ❌ Сложная миграция существующих компонентов

---

## ✅ **Рекомендация: Вариант 1 (Легковесная интеграция)**

**Обоснование:**
1. **Быстрая реализация** - можно сделать за 1-2 дня
2. **Низкие gas costs** - храним только переводы on-chain
3. **Гибкость** - технические данные в IPFS (состав, сертификаты, изображения)
4. **Обратная совместимость** - существующие компоненты работают

---

## 🔧 Техническая реализация (Вариант 1)

### **Шаг 1: Обновление OrganicComponentRegistryLogic**

#### **1.1. Обновить структуру Component:**

```solidity
struct Component {
    uint256 blockchain_id;
    address creator;
    uint256 created_at;
    uint256 last_updated;
    ComponentStatus status;
    bool is_shared;
    // УДАЛИТЬ: rootMetadataCID
    // ДОБАВИТЬ: technical_metadata_cid для технических данных (состав, сертификаты, изображения)
}

mapping(uint256 => string) public componentTechnicalMetadataCIDs; // Технические данные
```

#### **1.2. Добавить функции для работы с переводами:**

```solidity
/**
 * @dev Получить название компонента на языке
 * @param businessId ID компонента
 * @param language Код языка (en, ru, de, fr, es)
 * @return Название компонента
 */
function getComponentName(
    string calldata businessId,
    string calldata language
) external view returns (string memory) {
    // Проверяем что компонент существует
    require(_componentExists(businessId), "Component not found");
    
    // Получаем перевод из AmanitaInternational
    IAmanitaInternational intl = IAmanitaInternational(amanitaInternational);
    string memory className = string(abi.encodePacked("ComponentName.", businessId));
    return intl.getComplexFieldCID(className, language);
}

/**
 * @dev Установить название компонента на языке
 * @param businessId ID компонента
 * @param language Код языка
 * @param nameCID IPFS CID с названием
 */
function setComponentName(
    string calldata businessId,
    string calldata language,
    string calldata nameCID
) external onlyComponentCreatorByBusinessId(businessId) {
    IAmanitaInternational intl = IAmanitaInternational(amanitaInternational);
    string memory className = string(abi.encodePacked("ComponentName.", businessId));
    intl.setComplexFieldCID(className, language, nameCID);
}

/**
 * @dev Получить описание компонента на языке
 * @param businessId ID компонента
 * @param language Код языка
 * @return Описание компонента
 */
function getComponentDescription(
    string calldata businessId,
    string calldata language
) external view returns (string memory) {
    require(_componentExists(businessId), "Component not found");
    
    IAmanitaInternational intl = IAmanitaInternational(amanitaInternational);
    string memory className = string(abi.encodePacked("ComponentDesc.", businessId));
    return intl.getComplexFieldCID(className, language);
}

/**
 * @dev Установить описание компонента на языке
 * @param businessId ID компонента
 * @param language Код языка
 * @param descCID IPFS CID с описанием
 */
function setComponentDescription(
    string calldata businessId,
    string calldata language,
    string calldata descCID
) external onlyComponentCreatorByBusinessId(businessId) {
    IAmanitaInternational intl = IAmanitaInternational(amanitaInternational);
    string memory className = string(abi.encodePacked("ComponentDesc.", businessId));
    intl.setComplexFieldCID(className, language, descCID);
}
```

#### **1.3. Обновить createComponent:**

```solidity
function createComponent(
    string calldata businessId,
    string calldata technicalMetadataCID, // Технические данные (состав, сертификаты)
    string[] calldata languages,          // Языки для которых предоставлены переводы
    string[] calldata namesCIDs,          // IPFS CID для названий
    string[] calldata descriptionsCIDs    // IPFS CID для описаний
) external whenNotPaused nonReentrant onlyActivatedUser onlySeller 
    validBusinessId(businessId) 
    validCID(technicalMetadataCID) 
    returns (uint256 componentId) 
{
    // Валидация
    require(languages.length == namesCIDs.length, "Languages and names length mismatch");
    require(languages.length == descriptionsCIDs.length, "Languages and descriptions length mismatch");
    require(languages.length > 0, "At least one language required");
    
    // Создание компонента (как раньше)
    componentId = _createComponentCore(businessId, technicalMetadataCID);
    
    // Загрузка переводов в AmanitaInternational
    IAmanitaInternational intl = IAmanitaInternational(amanitaInternational);
    
    for (uint256 i = 0; i < languages.length; i++) {
        // Названия
        string memory nameClassName = string(abi.encodePacked("ComponentName.", businessId));
        intl.setComplexFieldCID(nameClassName, languages[i], namesCIDs[i]);
        
        // Описания
        string memory descClassName = string(abi.encodePacked("ComponentDesc.", businessId));
        intl.setComplexFieldCID(descClassName, languages[i], descriptionsCIDs[i]);
    }
    
    emit ComponentCreated(componentId, businessId, msg.sender, technicalMetadataCID, block.timestamp);
}
```

#### **1.4. Обновить ShareableData:**

**УДАЛИТЬ:**
```solidity
struct ShareableData {
    string features_cid;           // УДАЛИТЬ
    string component_forms_cid;    // УДАЛИТЬ
    uint256 features_version;      // УДАЛИТЬ
    uint256 forms_version;         // УДАЛИТЬ
    uint256 last_updated;
}
```

**Вместо этого использовать AmanitaInternational:**
```solidity
// Features теперь хранятся в AmanitaInternational
// Ключ: "component.features.{featureId}.{language}"
// Пример: "component.features.organic.en" → "Organic"
// Пример: "component.features.organic.ru" → "Органический"

// Forms теперь хранятся в AmanitaInternational
// Ключ: "component.forms.{formId}.{language}"
// Пример: "component.forms.powder.en" → "Powder"
// Пример: "component.forms.powder.ru" → "Порошок"

/**
 * @dev Получить перевод feature на языке
 * @param featureId ID характеристики (organic, wildcrafted, lab-tested)
 * @param language Код языка
 * @return Перевод характеристики
 */
function getFeatureTranslation(
    string calldata featureId,
    string calldata language
) external view returns (string memory) {
    IAmanitaInternational intl = IAmanitaInternational(amanitaInternational);
    string memory className = string(abi.encodePacked("component.features.", featureId));
    return intl.getComplexFieldCID(className, language);
}

/**
 * @dev Получить перевод form на языке
 * @param formId ID формы (powder, tincture, capsules)
 * @param language Код языка
 * @return Перевод формы
 */
function getFormTranslation(
    string calldata formId,
    string calldata language
) external view returns (string memory) {
    IAmanitaInternational intl = IAmanitaInternational(amanitaInternational);
    string memory className = string(abi.encodePacked("component.forms.", formId));
    return intl.getComplexFieldCID(className, language);
}
```

---

### **Шаг 2: Обновление ProductRegistryLogic**

#### **2.1. Добавить поле components в структуру Product:**

```solidity
struct Product {
    uint256 id;
    address seller;
    string ipfsCID;              // Метаданные продукта (цена, описание продукта, изображения)
    bool active;
    string[] componentIds;       // ДОБАВИТЬ: Массив business_id компонентов
}

mapping(uint256 => string[]) public productComponents; // product_id => [component_business_ids]
```

#### **2.2. Добавить адрес OrganicComponentRegistry:**

```solidity
// === ИНТЕГРАЦИЯ С ЭКОСИСТЕМОЙ ===
ISpiralEngine public spiralEngine;
IOrganicComponentRegistry public organicComponentRegistry; // ДОБАВИТЬ

/**
 * @dev Установить адрес OrganicComponentRegistry
 * @param _organicComponentRegistry Адрес контракта
 */
function setOrganicComponentRegistry(address _organicComponentRegistry) 
    external 
    onlyRole(ADMIN_ROLE) 
    nonReentrant 
{
    if (_organicComponentRegistry == address(0)) revert ZeroAddress();
    organicComponentRegistry = IOrganicComponentRegistry(_organicComponentRegistry);
    emit OrganicComponentRegistryUpdated(address(organicComponentRegistry), _organicComponentRegistry);
}
```

#### **2.3. Обновить createProduct с валидацией компонентов:**

```solidity
/**
 * @notice Создать новый продукт с компонентами
 * @param ipfsCID IPFS CID с метаданными продукта
 * @param componentBusinessIds Массив business_id компонентов
 * @return productId ID созданного продукта
 */
function createProduct(
    string calldata ipfsCID,
    string[] calldata componentBusinessIds
) external 
    whenNotPaused 
    nonReentrant 
    onlyActivatedSeller
    override 
    returns (uint256 productId) 
{
    if (bytes(ipfsCID).length == 0) revert EmptyCID();
    
    // ВАЛИДАЦИЯ КОМПОНЕНТОВ
    if (componentBusinessIds.length > 0) {
        _validateComponents(componentBusinessIds);
    }
    
    // Создание продукта
    unchecked {
        productId = ++_productIdCounter;
    }
    
    products[productId] = Product({
        id: productId,
        seller: msg.sender,
        ipfsCID: ipfsCID,
        active: false
    });
    
    // Сохранение компонентов
    if (componentBusinessIds.length > 0) {
        productComponents[productId] = componentBusinessIds;
        
        // Обновление статистики в OrganicComponentRegistry
        for (uint256 i = 0; i < componentBusinessIds.length; i++) {
            organicComponentRegistry.incrementUsageCount(componentBusinessIds[i]);
            organicComponentRegistry.addComponentUser(componentBusinessIds[i], msg.sender);
        }
    }
    
    productsBySeller[msg.sender].push(productId);
    
    unchecked {
        catalogVersion[msg.sender]++;
    }
    
    emit ProductCreated(msg.sender, productId, ipfsCID, 0);
    emit CatalogUpdated(msg.sender, catalogVersion[msg.sender]);
}

/**
 * @dev Валидация массива компонентов
 * @param componentBusinessIds Массив business_id компонентов
 */
function _validateComponents(string[] calldata componentBusinessIds) internal view {
    for (uint256 i = 0; i < componentBusinessIds.length; i++) {
        // Проверка существования компонента
        require(
            organicComponentRegistry.componentExists(componentBusinessIds[i]),
            "Component does not exist"
        );
        
        // Проверка статуса компонента
        require(
            organicComponentRegistry.getComponentStatus(componentBusinessIds[i]) == 
            IOrganicComponentRegistry.ComponentStatus.ACTIVE,
            "Component is not active"
        );
    }
}

/**
 * @dev Получить компоненты продукта
 * @param productId ID продукта
 * @return Массив business_id компонентов
 */
function getProductComponents(uint256 productId) 
    external 
    view 
    returns (string[] memory) 
{
    if (products[productId].id == 0) revert ProductDoesNotExist();
    return productComponents[productId];
}
```

---

### **Шаг 3: Обновление интерфейсов**

#### **3.1. IOrganicComponentRegistry.sol:**

```solidity
interface IOrganicComponentRegistry {
    // ДОБАВИТЬ:
    
    /**
     * @dev Получить название компонента на языке
     */
    function getComponentName(
        string memory businessId,
        string memory language
    ) external view returns (string memory);
    
    /**
     * @dev Установить название компонента
     */
    function setComponentName(
        string memory businessId,
        string memory language,
        string memory nameCID
    ) external;
    
    /**
     * @dev Получить описание компонента на языке
     */
    function getComponentDescription(
        string memory businessId,
        string memory language
    ) external view returns (string memory);
    
    /**
     * @dev Установить описание компонента
     */
    function setComponentDescription(
        string memory businessId,
        string memory language,
        string memory descCID
    ) external;
    
    /**
     * @dev Получить перевод feature
     */
    function getFeatureTranslation(
        string memory featureId,
        string memory language
    ) external view returns (string memory);
    
    /**
     * @dev Получить перевод form
     */
    function getFormTranslation(
        string memory formId,
        string memory language
    ) external view returns (string memory);
}
```

#### **3.2. IProductRegistry.sol:**

```solidity
interface IProductRegistry {
    // ОБНОВИТЬ:
    
    struct Product {
        uint256 id;
        address seller;
        string ipfsCID;
        bool active;
        // УДАЛИТЬ поле components отсюда
    }
    
    // ДОБАВИТЬ:
    
    /**
     * @notice Создать новый продукт с компонентами
     */
    function createProduct(
        string calldata ipfsCID,
        string[] calldata componentBusinessIds
    ) external returns (uint256 productId);
    
    /**
     * @notice Получить компоненты продукта
     */
    function getProductComponents(uint256 productId) 
        external 
        view 
        returns (string[] memory);
    
    /**
     * @notice Событие обновления OrganicComponentRegistry
     */
    event OrganicComponentRegistryUpdated(
        address indexed oldRegistry,
        address indexed newRegistry
    );
}
```

---

## 📦 Миграция существующих данных

### **Шаг 1: Snapshot текущих компонентов**

```bash
npx hardhat run scripts/migration/snapshot-components.js --network polygon

# Результат: data/components-snapshot.json
{
  "components": [
    {
      "blockchain_id": 1,
      "business_id": "amanita_muscaria_powder",
      "creator": "0x123...",
      "rootMetadataCID": "QmOldCID...",
      "created_at": 1704672000,
      "status": "ACTIVE"
    },
    ...
  ]
}
```

### **Шаг 2: Парсинг старых метаданных из IPFS**

```javascript
// scripts/migration/parse-old-metadata.js

async function parseComponentMetadata(oldCID) {
    // Скачать старый JSON из IPFS
    const oldMetadata = await fetchFromIPFS(oldCID);
    
    // Структура старого JSON:
    // {
    //   "name": "Amanita Muscaria Powder",
    //   "description": "Wildcrafted red fly agaric...",
    //   "species": "Amanita muscaria",
    //   "form": "powder",
    //   "features": ["organic", "wildcrafted"],
    //   "images": ["QmImg1...", "QmImg2..."],
    //   "certificates": ["QmCert1..."]
    // }
    
    // Разделить на:
    // 1. Переводы (название, описание)
    // 2. Технические данные (species, images, certificates)
    
    const translations = {
        name: {
            en: oldMetadata.name,  // Предполагаем что старые данные на английском
            ru: "", // Пока пусто, заполним вручную или через API перевода
        },
        description: {
            en: oldMetadata.description,
            ru: "",
        }
    };
    
    const technicalData = {
        species: oldMetadata.species,
        form: oldMetadata.form,
        features: oldMetadata.features,
        images: oldMetadata.images,
        certificates: oldMetadata.certificates
    };
    
    return { translations, technicalData };
}
```

### **Шаг 3: Загрузка переводов в AmanitaInternational**

```javascript
// scripts/migration/upload-translations.js

async function migrateComponentTranslations(component, translations) {
    const intl = await ethers.getContractAt(
        "AmanitaInternationalLogic",
        AMANITA_INTERNATIONAL_PROXY
    );
    
    // Загрузка названий
    for (const [lang, name] of Object.entries(translations.name)) {
        if (!name) continue; // Пропускаем пустые
        
        // Создаём простой JSON с переводом
        const nameJSON = { value: name };
        const nameCID = await uploadToIPFS(nameJSON);
        
        // Сохраняем в AmanitaInternational
        const className = `ComponentName.${component.business_id}`;
        await intl.setComplexFieldCID(className, lang, nameCID);
        
        console.log(`✅ Set ${className}.${lang} = ${nameCID}`);
    }
    
    // Загрузка описаний (аналогично)
    for (const [lang, desc] of Object.entries(translations.description)) {
        if (!desc) continue;
        
        const descJSON = { value: desc };
        const descCID = await uploadToIPFS(descJSON);
        
        const className = `ComponentDesc.${component.business_id}`;
        await intl.setComplexFieldCID(className, lang, descCID);
        
        console.log(`✅ Set ${className}.${lang} = ${descCID}`);
    }
}
```

### **Шаг 4: Обновление технических метаданных**

```javascript
// scripts/migration/update-technical-metadata.js

async function updateTechnicalMetadata(component, technicalData) {
    const registry = await ethers.getContractAt(
        "OrganicComponentRegistryLogic",
        ORGANIC_COMPONENT_REGISTRY_PROXY
    );
    
    // Загружаем технические данные в IPFS
    const techCID = await uploadToIPFS(technicalData);
    
    // Обновляем компонент
    await registry.updateComponent(component.blockchain_id, techCID);
    
    console.log(`✅ Updated component ${component.business_id} technical metadata: ${techCID}`);
}
```

### **Шаг 5: Запуск миграции**

```bash
# 1. Snapshot
npx hardhat run scripts/migration/snapshot-components.js --network polygon

# 2. Парсинг
npx hardhat run scripts/migration/parse-old-metadata.js --network polygon

# 3. Загрузка переводов
npx hardhat run scripts/migration/upload-translations.js --network polygon

# 4. Обновление технических данных
npx hardhat run scripts/migration/update-technical-metadata.js --network polygon

# 5. Верификация
npx hardhat run scripts/migration/verify-migration.js --network polygon
```

---

## 📊 Оценка работ

### **Вариант 1 (Легковесная интеграция):**

| Задача | Время | Сложность |
|--------|-------|-----------|
| Обновление OrganicComponentRegistryLogic | 6 часов | Средняя |
| Обновление ProductRegistryLogic | 4 часа | Средняя |
| Обновление интерфейсов | 2 часа | Низкая |
| Написание тестов | 4 часа | Средняя |
| Миграция существующих данных | 8 часов | Высокая |
| **ИТОГО** | **24 часа (3 дня)** | |

### **Риски:**

1. **Миграция данных** - самая трудоемкая часть
2. **Обратная совместимость** - нужно сохранить работу старых компонентов
3. **Gas costs** - нужно оптимизировать batch операции

---

## 🧪 План тестирования

### **Unit тесты:**

1. ✅ Создание компонента с переводами
2. ✅ Обновление переводов компонента
3. ✅ Получение переводов на разных языках
4. ✅ Валидация компонентов в ProductRegistry
5. ✅ Отслеживание использования компонентов

### **Integration тесты:**

1. ✅ OrganicComponentRegistry ↔ AmanitaInternational
2. ✅ ProductRegistry ↔ OrganicComponentRegistry
3. ✅ Полный flow создания продукта с компонентами

### **Migration тесты:**

1. ✅ Миграция старых компонентов
2. ✅ Совместимость старого и нового форматов
3. ✅ Верификация данных после миграции

---

## 📚 Следующие шаги

### **Immediate (сейчас):**
1. ✅ Согласовать архитектурное решение (Вариант 1 или 2)
2. ✅ Утвердить структуру данных
3. ✅ Начать разработку OrganicComponentRegistry

### **Short-term (1-2 дня):**
1. Обновить OrganicComponentRegistryLogic
2. Обновить ProductRegistryLogic
3. Написать unit тесты

### **Medium-term (3-5 дней):**
1. Написать migration скрипты
2. Провести миграцию на testnet (Mumbai)
3. Интеграционное тестирование

### **Long-term (1-2 недели):**
1. Деплой на mainnet (Polygon)
2. Миграция production данных
3. Обновление frontend для работы с новыми API

---

## 📞 Вопросы для обсуждения

1. **Какой вариант выбираем: Легковесную интеграцию (1) или Полную миграцию (2)?**
2. **Нужно ли мигрировать существующие компоненты или создать новые?**
3. **Какие языки поддерживаем в первой версии? (EN, RU обязательно, остальные?)**
4. **Как быть с техническими данными (состав, сертификаты) - в IPFS или on-chain?**
5. **Нужна ли валидация компонентов при создании продукта или просто ссылки?**

---

**Документ подготовлен:** 2025-01-11  
**Автор:** AI Analysis  
**Статус:** 🟡 Ожидает согласования

