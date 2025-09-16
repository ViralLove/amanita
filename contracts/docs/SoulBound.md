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
```

**Описание**: Получение информации о токенах и контракте
- **Метаданные**: Название, символ, URI
- **Балансы**: Количество токенов у пользователя
- **Владельцы**: Кто владеет конкретным токеном
- **Статистика**: Общее количество, следующий ID

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

## 🔮 Планы развития

### **Этап 2: Расширенная функциональность**
- [ ] Интеграция с IPFS для метаданных
- [ ] Система ролей и разрешений
- [ ] Временные блокировки
- [ ] Делегирование функций

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

1. **URI метаданные**: Возвращает пустую строку (планируется интеграция с IPFS)
2. **Газовое потребление**: 103,995 газа на минтинг (выше целевых 50,000)
3. **Метаданные**: Статические, без динамического контента
4. **Восстановление**: Нет механизма восстановления потерянных токенов

## 📚 Ссылки

- [EIP-5192: Soulbound Tokens](https://eips.ethereum.org/EIPS/eip-5192)
- [ERC-721: Non-Fungible Tokens](https://eips.ethereum.org/EIPS/eip-721)
- [OpenZeppelin Contracts](https://docs.openzeppelin.com/contracts/)
- [Amanita Ecosystem Architecture](../docs/sellers-safety-descentralization.md)

---

**Версия документации**: 1.0  
**Последнее обновление**: Декабрь 2024  
**Статус**: ✅ Протестировано и готово к использованию
