# Amanita Tokens - Токены экосистемы Amanita

## Обзор

Экосистема Amanita использует **два токена** для реализации экономической модели **Loveconomy** (экономики любви):

- **$AMANITA** - утилити токен для внутренних операций и вознаграждений
- **$AGOV** - governance токен для управления экосистемой и принятия решений

## Архитектура токенов

### Двухуровневая система
```mermaid
graph TB
    A[Loveconomy] --> B[$AMANITA - Утилити]
    A --> C[$AGOV - Governance]
    
    B --> D[Внутренние операции]
    B --> E[Вознаграждения]
    B --> F[Клейм сразу]
    
    C --> G[Управление экосистемой]
    C --> H[Голосование]
    C --> I[Активация при репутации]
```

### Роли и функции
- **$AMANITA** - повседневные операции, вознаграждения, клейм
- **$AGOV** - стратегические решения, управление, голосование
- **Интеграция** - оба токена эмитируются через LoveEmissionEngine

## AmanitaToken ($AMANITA)

### Назначение
**$AMANITA** - это утилити токен для внутренних операций в экосистеме Amanita.

### Технические характеристики
- **Стандарт**: ERC20
- **Символ**: AMANITA
- **Децимали**: 18
- **Начальная эмиссия**: 888,888,888 AMANITA
- **Дополнительная эмиссия**: через MINTER_ROLE

### Основные функции

#### Конструктор
```solidity
constructor(address owner) ERC20("Amanita", "AMANITA") {
    _mint(owner, INITIAL_SUPPLY);
    _grantRole(DEFAULT_ADMIN_ROLE, owner);
    _grantRole(MINTER_ROLE, owner);
}
```

**Функциональность:**
- Создание токена с начальной эмиссией
- Назначение ролей владельцу
- Установка 18 децималей

#### Минтинг
```solidity
function mint(address to, uint256 amount) external onlyRole(MINTER_ROLE) {
    _mint(to, amount);
}
```

**Требования:**
- Вызывающий должен иметь `MINTER_ROLE`
- Используется LoveEmissionEngine для эмиссии

#### Сжигание
```solidity
function burn(address from, uint256 amount) external onlyRole(MINTER_ROLE) {
    _burn(from, amount);
}
```

**Требования:**
- Вызывающий должен иметь `MINTER_ROLE`
- Уменьшение общего предложения токенов

### Использование в экосистеме

#### LoveEmissionEngine
- **Эмиссия**: 1 AMANITA за суперлайк
- **Клейм**: продавцы клеймят накопленные токены
- **Накопление**: токены накапливаются до клейма

#### Экономическая модель
- **Утилити**: внутренние операции экосистемы
- **Вознаграждения**: за активность в LoveDo постах
- **Ликвидность**: доступны для клейма сразу

## AmanitaGovToken ($AGOV)

### Назначение
**$AGOV** - это governance токен для управления экосистемой Amanita.

### Технические характеристики
- **Стандарт**: ERC20Votes + ERC20Permit
- **Символ**: AGOV
- **Децимали**: 18
- **Начальная эмиссия**: 0 (только минтинг)
- **Дополнительная эмиссия**: через MINTER_ROLE

### Расширенные возможности

#### ERC20Votes
- **Делегирование**: передача голосов другим адресам
- **Snapshot**: снимки балансов для голосования
- **История**: отслеживание изменений делегирования

#### ERC20Permit
- **Gasless транзакции**: подписание без газа
- **Meta-transactions**: транзакции через релееры
- **Удобство**: улучшенный UX для пользователей

### Основные функции

#### Конструктор
```solidity
constructor(address admin)
    ERC20("Amanita Governance", "AGOV")
    ERC20Permit("Amanita Governance")
{
    require(admin != address(0), "Admin address required");
    _grantRole(DEFAULT_ADMIN_ROLE, admin);
    _grantRole(MINTER_ROLE, admin);
}
```

**Функциональность:**
- Создание governance токена
- Инициализация ERC20Permit
- Назначение ролей администратору

#### Минтинг
```solidity
function mint(address to, uint256 amount) external onlyRole(MINTER_ROLE) {
    _mint(to, amount);
}
```

**Требования:**
- Вызывающий должен иметь `MINTER_ROLE`
- Используется LoveEmissionEngine для активации

### Использование в экосистеме

#### LoveEmissionEngine
- **Накопление**: 1 AGOV за суперлайк
- **Активация**: только при достижении 8+ LoveDo постов
- **Одноразовая активация**: можно активировать только один раз

#### Governance функции
- **Голосование**: участие в управлении экосистемой
- **Делегирование**: передача голосов другим участникам
- **Предложения**: создание и голосование по предложениям

## Система ролей

### Роли токенов
```solidity
bytes32 public constant MINTER_ROLE = keccak256("MINTER_ROLE");
bytes32 public constant DEFAULT_ADMIN_ROLE = keccak256("DEFAULT_ADMIN_ROLE");
```

### Назначение ролей
- **DEFAULT_ADMIN_ROLE** - управление ролями и контрактом
- **MINTER_ROLE** - эмиссия и сжигание токенов
- **Владелец** - получает обе роли при создании

### Безопасность
- **Контроль доступа**: только авторизованные адреса
- **Проверка ролей**: через модификаторы OpenZeppelin
- **Администрирование**: централизованное управление ролями

## Интеграция с LoveEmissionEngine

### Эмиссия токенов
```solidity
// В LoveEmissionEngine
amanitaAccrued[sellerTo] += EMISSION_RATE;  // 1 ether AMANITA
agovAccrued[sellerTo] += EMISSION_RATE;     // 1 ether AGOV
```

### Клейм $AMANITA
```solidity
// Немедленный клейм утилити токенов
function claimAMANITA() external {
    uint256 amount = amanitaAccrued[msg.sender];
    amanitaAccrued[msg.sender] = 0;
    amanitaToken.transfer(msg.sender, amount);
}
```

### Активация $AGOV
```solidity
// Активация при достижении репутации
function claimAGOV() external {
    require(loveDo.getLoveDoCount(msg.sender) >= 8, "Not enough reputation");
    uint256 amount = agovAccrued[msg.sender];
    agovToken.mint(msg.sender, amount);
}
```

## Экономическая модель

### Распределение токенов
- **$AMANITA**: 888,888,888 (начальная эмиссия) + эмиссия за активность
- **$AGOV**: только эмиссия за активность (без начальной эмиссии)

### Механизм эмиссии
- **Суперлайки**: 1 AMANITA + 1 AGOV за суперлайк
- **Социальная проверка**: только от участников одного круга
- **Репутация**: AGOV активируются при 8+ LoveDo постах

### Стимулы
- **Активность**: создание качественного контента
- **Социальные связи**: участие в кругах доверия
- **Репутация**: долгосрочное участие в экосистеме

## Использование

### Работа с $AMANITA
```javascript
const amanitaToken = new ethers.Contract(address, abi, signer);

// Проверка баланса
const balance = await amanitaToken.balanceOf(userAddress);

// Перевод токенов
await amanitaToken.transfer(recipient, amount);

// Клейм через LoveEmissionEngine
await loveEmission.claimAMANITA();
```

### Работа с $AGOV
```javascript
const agovToken = new ethers.Contract(address, abi, signer);

// Проверка баланса
const balance = await agovToken.balanceOf(userAddress);

// Делегирование голосов
await agovToken.delegate(delegateAddress);

// Активация через LoveEmissionEngine
await loveEmission.claimAGOV();
```

### Governance функции
```javascript
// Получение текущих голосов
const votes = await agovToken.getVotes(userAddress);

// Получение голосов на определенный блок
const votesAtBlock = await agovToken.getPastVotes(userAddress, blockNumber);

// Получение делегата
const delegate = await agovToken.delegates(userAddress);
```

## События

### AmanitaToken события
```solidity
event Transfer(address indexed from, address indexed to, uint256 value);
event Approval(address indexed owner, address indexed spender, uint256 value);
```

### AmanitaGovToken события
```solidity
event Transfer(address indexed from, address indexed to, uint256 value);
event Approval(address indexed owner, address indexed spender, uint256 value);
event DelegateChanged(address indexed delegator, address indexed fromDelegate, address indexed toDelegate);
event DelegateVotesChanged(address indexed delegate, uint256 previousVotes, uint256 newVotes);
```

## Безопасность

### Защита от манипуляций
- **Контроль ролей**: только авторизованные адреса могут минтить
- **Проверка адресов**: валидация адресов при создании
- **Стандарты OpenZeppelin**: проверенные реализации

### Governance безопасность
- **Делегирование**: защита от централизации власти
- **Snapshot**: защита от манипуляций во время голосования
- **Permit**: безопасные gasless транзакции

## Мониторинг и аналитика

### Метрики $AMANITA
- Общее предложение
- Распределение между пользователями
- Активность клейма

### Метрики $AGOV
- Количество активированных токенов
- Распределение голосов
- Активность делегирования

### Интеграция с экосистемой
- Связь с LoveDoPostNFT через LoveEmissionEngine
- Отслеживание эмиссии по суперлайкам
- Мониторинг репутации для активации AGOV

## Ограничения и особенности

### $AMANITA
- ✅ Можно клеймить многократно
- ✅ Доступны сразу после накопления
- ❌ Нет governance функций
- 🔄 Постоянная эмиссия за активность

### $AGOV
- ✅ Governance функции и делегирование
- ✅ Gasless транзакции через Permit
- ❌ Активация только при репутации
- 🔒 Одноразовая активация

## Заключение

Токены Amanita реализуют **двухуровневую экономическую модель**:

- **$AMANITA** - обеспечивает **повседневную активность** и **немедленные вознаграждения**
- **$AGOV** - обеспечивает **стратегическое управление** и **долгосрочную репутацию**

Эта модель создает **сбалансированную экосистему**, где:
- 🎯 **Активность поощряется** через $AMANITA
- 🏛️ **Управление децентрализовано** через $AGOV
- 🔗 **Социальные связи важны** для эмиссии
- 📈 **Репутация определяет** доступ к governance

Токены являются **фундаментом Loveconomy**, обеспечивая справедливое распределение власти и вознаграждений в децентрализованной экосистеме Amanita.
