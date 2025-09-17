# SoulboundCore - Документация

## 📋 Обзор

**SoulboundCore** - это минимальная, газоэффективная реализация Soulbound Token (SBT) согласно стандарту EIP-5192. Контракт обеспечивает создание неотчуждаемых токенов, которые привязаны к конкретному кошельку и не могут быть переданы другим пользователям.

## 🎯 Основные характеристики

- **EIP-5192 Compliance**: Полная совместимость со стандартом Soulbound Tokens
- **ERC721 совместимость**: Реализует интерфейс ERC721 с блокировкой передачи
- **Газоэффективность**: Оптимизирован для минимального потребления газа
- **Безопасность**: Строгие проверки авторизации для всех операций
- **Модульность**: Готов к интеграции с другими контрактами экосистемы

## 🏗️ Архитектура

### Наследование
```solidity
contract SoulboundCore is IERC165, IERC721, IERC721Metadata, IERC5192, Ownable
```

### Основные интерфейсы
- **IERC165**: Поддержка интерфейсов
- **IERC721**: Стандарт NFT
- **IERC721Metadata**: Метаданные NFT
- **IERC5192**: Стандарт Soulbound Tokens
- **Ownable**: Управление владельцем контракта

## 🔧 Функциональность

### ✅ Реализованные функции

#### **1. Минтинг токенов**
```solidity
function mintSoul(address to, uint256 tokenId) external onlyOwner
function mintSoulBatch(address to, uint256 amount) external onlyOwner
```

**Описание**: Создание новых SBT токенов
- **mintSoul**: Минтинг одного токена с указанным ID
- **mintSoulBatch**: Минтинг нескольких токенов подряд
- **Авторизация**: Только владелец контракта
- **События**: `SoulMinted`, `Locked`, `Transfer`

#### **2. Сжигание токенов**
```solidity
function burnSoul(uint256 tokenId) external
```

**Описание**: Уничтожение SBT токена
- **Авторизация**: Владелец токена или владелец контракта
- **Обновление**: `_totalSupply` уменьшается на 1
- **События**: `SoulBurned`, `Transfer`

#### **3. EIP-5192 Compliance**
```solidity
function locked(uint256 tokenId) external pure returns (bool)
```

**Описание**: Всегда возвращает `true` - токены заблокированы навсегда
- **Pure функция**: Не требует газа
- **Событие**: `Locked` при минтинге

#### **4. Блокировка передачи**
```solidity
function transferFrom(...) public pure override
function safeTransferFrom(...) public pure override
function approve(...) public pure override
function setApprovalForAll(...) public pure override
```

**Описание**: Все функции передачи заблокированы
- **Revert**: Всегда возвращают ошибку "SBT: transfer not allowed"
- **Безопасность**: Предотвращает случайную передачу

#### **5. View функции**
```solidity
function name() public view returns (string memory)
function symbol() public view returns (string memory)
function tokenURI(uint256 tokenId) public view returns (string memory)
function balanceOf(address owner) public view returns (uint256)
function ownerOf(uint256 tokenId) public view returns (address)
function getTotalSupply() external view returns (uint256)
function getNextTokenId() external view returns (uint256)
function exists(uint256 tokenId) external view returns (bool)
function setMetadataContract(address metadataContract) external onlyOwner
function getMetadataContract() external view returns (address)
```

**Описание**: Получение информации о токенах и контракте
- **Метаданные**: Название, символ, динамический URI через SoulMetadata
- **Балансы**: Количество токенов у пользователя
- **Владельцы**: Кто владеет конкретным токеном
- **Статистика**: Общее количество, следующий ID
- **Интеграция**: Управление контрактом метаданных

## 🧪 Тестирование

### ✅ Покрытие тестами: 100% (34/34 тестов)

#### **Группы тестов**
1. **Deployment** (4 теста) - Развертывание контракта
2. **EIP-5192 Compliance** (2 теста) - Соответствие стандарту
3. **Non-transferability** (3 теста) - Блокировка передачи
4. **No Approval Delegation** (4 теста) - Блокировка делегирования
5. **Minting** (5 тестов) - Создание токенов
6. **Burning** (4 теста) - Уничтожение токенов
7. **View Functions** (3 теста) - Информационные функции
8. **Edge Cases** (5 тестов) - Граничные случаи
9. **Gas Profiling** (4 теста) - Измерение газа

#### **Критические пути покрыты**
- ✅ Минтинг одиночных и пакетных токенов
- ✅ Сжигание токенов с авторизацией
- ✅ Блокировка всех функций передачи
- ✅ EIP-5192 compliance проверки
- ✅ Edge cases и граничные условия
- ✅ Газовое профилирование

## ⛽ Газовое потребление

### **Измеренные показатели**
- **mintSoul**: 103,995 газа
- **mintSoulBatch** (5 токенов): 43,964 газа за токен
- **burnSoul**: 32,608 газа
- **locked()**: 0 газа (pure функция)

### **Стоимость в POL/USD** (1 POL = $0.20)
- **mintSoul**: ~$0.0000208
- **burnSoul**: ~$0.0000065
- **Полный цикл** (mint + burn): ~$0.0000274

## 🔒 Безопасность

### **Принципы безопасности**
1. **Неотчуждаемость**: Токены не могут быть переданы
2. **Авторизация**: Строгие проверки прав доступа
3. **Валидация**: Проверка всех входных параметров
4. **Изоляция**: Каждая операция независима

### **Защита от атак**
- ❌ **Передача токенов**: Полностью заблокирована
- ❌ **Делегирование прав**: Запрещено
- ❌ **Неавторизованное сжигание**: Только владелец токена
- ❌ **Дублирование токенов**: Проверка существования

## 🔄 Интеграция с экосистемой

### **Связь с другими контрактами**
- **SpiralEngine**: Делегирует SBT функции в SoulIdentity
- **SoulIdentity**: Основной контракт для SBT функциональности
- **AmanitaRegistry**: Регистрация в общей экосистеме

### **Архитектурная роль**
SoulboundCore служит базовым строительным блоком для:
- Создания цифровых идентичностей
- Привязки репутации к кошельку
- Реализации системы достижений
- Управления доступом в DAO

## 📊 Состояние контракта

### **Внутренние переменные**
```solidity
string private _name;           // Название токена
string private _symbol;         // Символ токена
uint256 private _nextTokenId;   // Следующий доступный ID
uint256 private _totalSupply;   // Общее количество токенов
mapping(uint256 => address) private _owners;     // Владельцы токенов
mapping(address => uint256) private _balances;   // Балансы пользователей
```

### **События**
```solidity
event SoulMinted(address indexed to, uint256 indexed tokenId);
event SoulBurned(uint256 indexed tokenId);
event Locked(uint256 indexed tokenId);
event Transfer(address indexed from, address indexed to, uint256 indexed tokenId);
```

## 🚀 Развертывание

### **Параметры конструктора**
```solidity
constructor(string memory name, string memory symbol)
```

**Пример**:
```solidity
SoulboundCore("Amanita Soul", "ASOUL")
```

### **Требования**
- Solidity ^0.8.20
- OpenZeppelin контракты
- Hardhat для тестирования

## 🎨 Система метаданных (SoulMetadata)

**SoulMetadata** - это газоэффективная система управления метаданными для SoulboundCore токенов. Обеспечивает динамические метаданные с поддержкой IPFS и версионирования.

#### **Архитектура интеграции**
```solidity
SoulboundCore → ISoulMetadata → SoulMetadata
```

- **SoulboundCore**: Базовый SBT контракт с fallback логикой
- **SoulMetadata**: Контракт управления метаданными
- **ISoulMetadata**: Интерфейс для cross-contract взаимодействия

#### **Основные функции SoulMetadata**

##### **1. Инициализация метаданных**
```solidity
function initializeMetadata(
    uint256 tokenId,
    string memory metadataType,
    string memory attributes,
    string memory ipfsHash
) external
```

**Описание**: Первичная инициализация метаданных токена
- **Авторизация**: Владелец токена или владелец контракта
- **Параметры**: Тип, атрибуты (JSON), IPFS хеш
- **События**: `MetadataUpdated`

##### **2. Обновление метаданных**
```solidity
function updateMetadata(
    uint256 tokenId,
    string memory attributes,
    string memory ipfsHash
) external
```

**Описание**: Обновление атрибутов и IPFS хеша
- **Версионирование**: Автоматическое увеличение версии
- **Авторизация**: Только владелец токена
- **События**: `MetadataUpdated`

##### **3. Пакетное обновление**
```solidity
function batchUpdateMetadata(
    uint256[] memory tokenIds,
    string[] memory attributesArray,
    string[] memory ipfsHashes
) external
```

**Описание**: Массовое обновление до 50 токенов
- **Оптимизация**: Экономия газа при множественных операциях
- **События**: `MetadataBatchUpdated`

##### **4. View функции**
```solidity
function getMetadata(uint256 tokenId) external view returns (SoulData memory)
function isInitialized(uint256 tokenId) external view returns (bool)
function getTokenURI(uint256 tokenId) external view returns (string memory)
function getMetadataVersion(uint256 tokenId) external view returns (uint256)
```

#### **Структура данных SoulData**
```solidity
struct SoulData {
    string metadataType;    // "identity", "achievement", "reputation"
    uint256 version;        // Версия метаданных
    string attributes;      // JSON строка с атрибутами
    string ipfsHash;        // IPFS хеш для дополнительных данных
}
```

**Storage optimization**: 4 storage slots для полной структуры

#### **Интеграция с tokenURI**

SoulboundCore автоматически использует SoulMetadata для генерации tokenURI:

```javascript
// Без метаданных (fallback)
{
  "name": "Soul #1",
  "description": "Soulbound Token from Amanita Ecosystem",
  "type": "basic",
  "version": 1,
  "attributes": []
}

// С метаданными
{
  "name": "Soul #1",
  "description": "Soulbound Token from Amanita Ecosystem", 
  "type": "identity",
  "version": 2,
  "attributes": {"level": 5, "experience": 1000},
  "ipfs": "QmDetailedMetadata"
}
```

#### **Тестирование системы метаданных**

### ✅ **Покрытие тестами: 100% (24/24 тестов)**

##### **Группы тестов**
1. **Deployment and Integration** (2 теста) - Развертывание и связывание
2. **Basic Metadata Operations** (6 тестов) - Основные операции с метаданными
3. **Access Control** (4 теста) - Контроль доступа
4. **Batch Operations** (3 теста) - Пакетные операции
5. **Edge Cases** (5 тестов) - Граничные случаи и error handling
6. **Gas Profiling** (4 теста) - Измерение газа

##### **Критические пути покрыты**
- ✅ Инициализация и обновление метаданных
- ✅ Пакетные операции (до 50 токенов)
- ✅ Версионирование и отслеживание изменений
- ✅ Fallback логика при ошибках
- ✅ Контроль доступа и авторизация
- ✅ Edge cases (пустые IPFS, сложные JSON)

#### **Газовое потребление метаданных**

##### **Измеренные показатели**
- **initializeMetadata**: 216,853 газа
- **updateMetadata**: 101,288 газа
- **batchUpdateMetadata** (5 токенов): 32,595 газа за токен
- **tokenURI** (view): 50,927 газа

##### **Стоимость в POL/USD** (1 POL = $0.20)
- **Инициализация метаданных**: ~$0.0000434
- **Обновление метаданных**: ~$0.0000203
- **Пакетное обновление (5 токенов)**: ~$0.0000326

#### **Примеры использования метаданных**

##### **Инициализация метаданных**
```javascript
// Создание токена и инициализация метаданных
await soulboundCore.mintSoul(userAddress);
await soulMetadata.connect(user).initializeMetadata(
    1,
    "identity",
    '{"level": 1, "experience": 0, "class": "beginner"}',
    "QmIdentityHash"
);

// Проверка инициализации
const isInit = await soulMetadata.isInitialized(1);
console.log("Initialized:", isInit); // true
```

##### **Обновление метаданных**
```javascript
// Прогресс пользователя
await soulMetadata.connect(user).updateMetadata(
    1,
    '{"level": 5, "experience": 1250, "class": "advanced"}',
    "QmUpdatedHash"
);

// Проверка версии
const version = await soulMetadata.getMetadataVersion(1);
console.log("Version:", version); // 2
```

##### **Получение полных метаданных**
```javascript
// Получение структуры метаданных
const metadata = await soulMetadata.getMetadata(1);
console.log("Type:", metadata.metadataType); // "identity"
console.log("Version:", metadata.version);    // 2
console.log("Attributes:", metadata.attributes); // JSON string
console.log("IPFS:", metadata.ipfsHash);      // "QmUpdatedHash"

// Получение JSON URI
const tokenURI = await soulboundCore.tokenURI(1);
console.log("Token URI:", tokenURI); // Full JSON metadata
```

##### **Пакетное обновление**
```javascript
// Обновление нескольких токенов одновременно
const tokenIds = [1, 2, 3];
const attributes = [
    '{"level": 6, "updated": true}',
    '{"level": 4, "updated": true}', 
    '{"level": 8, "updated": true}'
];
const ipfsHashes = ["QmNew1", "QmNew2", "QmNew3"];

await soulMetadata.connect(user).batchUpdateMetadata(
    tokenIds,
    attributes, 
    ipfsHashes
);
```

#### **Управление интеграцией**
```javascript
// Подключение контракта метаданных
await soulboundCore.setMetadataContract(soulMetadataAddress);

// Проверка подключения
const metadataContract = await soulboundCore.getMetadataContract();
console.log("Metadata contract:", metadataContract);
```

## 🔮 Планы развития

### ✅ **Этап 2: Система метаданных (ЗАВЕРШЕН)**
- ✅ Интеграция с IPFS для метаданных
- ✅ Динамические метаданные с версионированием
- ✅ Пакетные операции для оптимизации газа
- ✅ Fallback логика и error handling

### **Этап 3: DID интеграция**
- [ ] Поддержка Decentralized Identifiers
- [ ] Верификация личности
- [ ] Кросс-чейн совместимость
- [ ] Восстановление доступа

### **Этап 4: DAO функции**
- [ ] Голосование на основе SBT
- [ ] Репутационная система
- [ ] Система достижений
- [ ] Социальные графы

## 📝 Примеры использования

### **Создание SBT токена**
```javascript
// Минтинг токена пользователю
await soulboundCore.mintSoul(userAddress, 1);

// Проверка владения
const owner = await soulboundCore.ownerOf(1);
console.log("Owner:", owner); // userAddress

// Проверка блокировки
const isLocked = await soulboundCore.locked(1);
console.log("Is locked:", isLocked); // true
```

### **Пакетный минтинг**
```javascript
// Создание 5 токенов подряд
await soulboundCore.mintSoulBatch(userAddress, 5);

// Проверка общего количества
const totalSupply = await soulboundCore.getTotalSupply();
console.log("Total supply:", totalSupply); // 5
```

### **Сжигание токена**
```javascript
// Сжигание токена (только владелец)
await soulboundCore.connect(user).burnSoul(1);

// Проверка удаления
const exists = await soulboundCore.exists(1);
console.log("Token exists:", exists); // false
```

## 🐛 Известные ограничения

1. ✅ **URI метаданные**: ~~Возвращает пустую строку~~ → **РЕШЕНО**: Полная интеграция с SoulMetadata
2. **Газовое потребление**: 103,995 газа на минтинг SoulboundCore (выше целевых 50,000)
3. ✅ **Метаданные**: ~~Статические~~ → **РЕШЕНО**: Динамические с версионированием и IPFS
4. **Восстановление**: Нет механизма восстановления потерянных токенов (планируется в Этапе 3)
5. **Новые ограничения системы метаданных**:
   - Инициализация метаданных: 216,853 газа (высокое потребление из-за storage)
   - Максимум 50 токенов в пакетной операции
   - Необходимость отдельного контракта для метаданных

## 📚 Ссылки

- [EIP-5192: Soulbound Tokens](https://eips.ethereum.org/EIPS/eip-5192)
- [ERC-721: Non-Fungible Tokens](https://eips.ethereum.org/EIPS/eip-721)
- [OpenZeppelin Contracts](https://docs.openzeppelin.com/contracts/)
- [Amanita Ecosystem Architecture](../docs/sellers-safety-descentralization.md)

---

**Версия документации**: 2.0  
**Последнее обновление**: Декабрь 2024  
**Статус**: ✅ SoulboundCore + SoulMetadata протестированы и готовы к использованию

### **Версии контрактов**
- **SoulboundCore**: v1.0 - Базовый SBT контракт (34/34 тестов)
- **SoulMetadata**: v1.0 - Система метаданных (24/24 тестов)
- **Общее покрытие**: 58/58 тестов (100% успеха)
