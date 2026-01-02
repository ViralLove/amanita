# Task: fix — Action 555 блокируется из-за логической несогласованности ролей

## Цель
Исправить критическую проблему, при которой **Seller не может загружать переводы компонентов** в Action 555 из-за неправильной архитектуры проверки SELLER_ROLE между разными доменами.

## Почему это важно (риск)
**Блокировка Action 555** - ключевого действия для загрузки компонентов в production. Без исправления невозможно запустить экосистему с реальными компонентами.

## Факты из кода

### 1) Action 555 вызывает setSimpleFieldCID от имени seller
- `scripts/lib/upload_steps.js:131-137`
  - `const tx = await amanitaIntlWithSigner.setSimpleFieldCID("ComponentDescription.title", titleCID);`
  - Вызывается от `context.seller.address` через `context.seller.signer`

### 2) AmanitaInternational проверяет SELLER_ROLE через _hasSellerRole()
- `contracts/AmanitaInternationalLogic.sol:340`
  - `if (!hasRole(ADMIN_ROLE, msg.sender) && !_hasSellerRole(msg.sender))`
  - `_hasSellerRole()` проверяет роль сначала локально, потом в SpiralEngine

### 3) SpiralEngine SELLER_ROLE ≠ AmanitaInternational SELLER_ROLE
- **SpiralEngine.SELLER_ROLE**: социальный статус участника сети (право создавать инвайты)
- **AmanitaInternational.SELLER_ROLE**: право загружать переводы компонентов
- **Это разные домены и разные права доступа**

### 4) Action 51 дает SELLER_ROLE только в SpiralEngine
- `scripts/lib/actions/ComponentActions.js:184-256`
  - Seller получает SELLER_ROLE только в SpiralEngine
  - AmanitaInternational не получает информацию об активации seller

### 5) _hasSellerRole() полагается на SpiralEngine как "основной источник истины"
- `contracts/AmanitaInternationalLogic.sol:300`
  - Комментарий: "Роль в SpiralEngine (основной источник истины)"
  - **Это архитектурная ошибка** - домены должны быть независимы

## Gap / Проблема

**Логическая несогласованность архитектуры:**
1. **SpiralEngine** - домен социальных ролей и инвайтов
2. **AmanitaInternational** - домен переводов и мультиязычных данных
3. **Неправильная связность**: переводы зависят от социальных ролей
4. **Отсутствие локального управления**: seller не получает SELLER_ROLE в AmanitaInternational
5. **Результат:** `UnauthorizedFieldAccess` при попытке загрузить переводы

## AC/DoD
- [ ] **Команда проверки:** `DEPLOY_ACTION=555 DEPLOYER_INVITE=XXXX node scripts/deploy_full.js 555`
- [ ] Action 555 завершается без ошибок `UnauthorizedFieldAccess`
- [ ] Все компоненты успешно регистрируются с переводами
- [ ] Seller имеет SELLER_ROLE локально в AmanitaInternational
- [ ] Логи показывают успешную загрузку всех компонентов
- [ ] Домены SpiralEngine и AmanitaInternational работают независимо

## Где менять код

### 1. Исправление _hasSellerRole() в AmanitaInternational
- `contracts/AmanitaInternationalLogic.sol`
  - Убрать зависимость от SpiralEngine (строки 300-309)
  - Оставить только локальную проверку роли
  - Обновить комментарии

### 2. Автоматическое назначение SELLER_ROLE в AmanitaInternational
- `scripts/lib/actions/ComponentActions.js` (Action 51)
  - После активации seller в SpiralEngine автоматически дать ему SELLER_ROLE в AmanitaInternational
  - Добавить функцию grantSellerRoleInAmanitaInternational()

### 3. Удаление ненужных связей
- Убрать setSpiralEngine() из контракта AmanitaInternational
- Упростить архитектуру

## План выполнения

### Шаг 1: Анализ и признание ошибки архитектуры
1. Признать, что SpiralEngine и AmanitaInternational - разные домены
2. Понять, что SELLER_ROLE в разных контекстах - разные права
3. Решить, что делать с существующей "интеграцией"

### Шаг 2: Выбор решения - локальное управление ролями
1. Убрать зависимость от SpiralEngine в _hasSellerRole()
2. Добавить автоматическое назначение SELLER_ROLE в AmanitaInternational при активации seller
3. Протестировать, что Action 555 работает

### Шаг 3: Очистка кода
1. Убрать setSpiralEngine() из AmanitaInternational
2. Удалить связанные переменные и функции
3. Обновить комментарии и документацию

### Шаг 4: Тестирование
1. Протестировать Action 555 на чистой ноде
2. Убедиться, что роли работают независимо
3. Проверить обратную совместимость

## Команды проверки

### До исправления (демонстрация проблемы):
```bash
# На чистой hardhat ноде
npx hardhat node

# В новом терминале
DEPLOY_ACTION=1 node scripts/deploy_full.js 1
DEPLOY_ACTION=555 DEPLOYER_INVITE=AMANITA-TEST-001 node scripts/deploy_full.js 555
# Ожидаем: ❌ 11/11 компонентов с UnauthorizedFieldAccess
```

### После исправления (ожидаемый результат):
```bash
# На чистой hardhat ноде
npx hardhat node

# В новом терминале
DEPLOY_ACTION=1 node scripts/deploy_full.js 1
DEPLOY_ACTION=555 DEPLOYER_INVITE=AMANITA-TEST-001 node scripts/deploy_full.js 555
# Ожидаем: ✅ Все компоненты загружены успешно
```

### Диагностика связей:
```bash
# Проверить настройку SpiralEngine в контрактах
node -e "
const { ethers } = require('ethers');
const provider = new ethers.JsonRpcProvider('http://127.0.0.1:8545');

async function check() {
  // Загрузить адреса из deploy.json или логов
  const amanitaIntl = new ethers.Contract(AMANITA_INTL_ADDRESS, abi, provider);
  const spiralAddr = await amanitaIntl.spiralEngine();
  console.log('SpiralEngine in AmanitaInternational:', spiralAddr);
  
  const spiral = new ethers.Contract(SPIRAL_ADDRESS, abi, provider);
  const sellerRole = await spiral.SELLER_ROLE();
  const hasRole = await spiral.hasRole(sellerRole, SELLER_ADDRESS);
  console.log('Seller has SELLER_ROLE in SpiralEngine:', hasRole);
}

check();
"
```

## Команды проверки

### До исправления (демонстрация проблемы):
```bash
# На чистой hardhat ноде
npx hardhat node

# В новом терминале - только деплой контрактов
DEPLOY_ACTION=1 node scripts/deploy_full.js 1

# Попытка Action 555 - должна упасть с UnauthorizedFieldAccess
DEPLOY_ACTION=555 DEPLOYER_INVITE=AMANITA-TEST-001 node scripts/deploy_full.js 555
# Ожидаем: ❌ 11/11 компонентов с UnauthorizedFieldAccess
```

### После исправления (ожидаемый результат):
```bash
# На чистой hardhat ноде
npx hardhat node

# В новом терминале - только деплой контрактов
DEPLOY_ACTION=1 node scripts/deploy_full.js 1

# Action 555 должен работать без настройки связей
DEPLOY_ACTION=555 DEPLOYER_INVITE=AMANITA-TEST-001 node scripts/deploy_full.js 555
# Ожидаем: ✅ Все компоненты загружены успешно
```

### Диагностика ролей:
```bash
# Проверить SELLER_ROLE в AmanitaInternational
node -e "
const { ethers } = require('ethers');
const provider = new ethers.JsonRpcProvider('http://127.0.0.1:8545');

async function check() {
  const amanitaIntl = new ethers.Contract(AMANITA_INTL_ADDRESS, ABI, provider);
  const SELLER_ROLE = await amanitaIntl.SELLER_ROLE();
  const hasRole = await amanitaIntl.hasRole(SELLER_ROLE, SELLER_ADDRESS);
  console.log('Seller has SELLER_ROLE in AmanitaInternational:', hasRole);

  if (!hasRole) {
    console.log('❌ Seller не имеет SELLER_ROLE в AmanitaInternational!');
  } else {
    console.log('✅ Seller имеет SELLER_ROLE в AmanitaInternational');
  }
}

check();
"
```

---

## Метаданные задачи
**Приоритет:** P0 (Критично - блокирует MVP)  
**Сложность:** M (Средняя - требует понимания доменов)  
**Оценка времени:** 3-4 часа (анализ архитектуры + refactoring + тестирование)  
**Зависимости:** Требует понимания разделения доменов  
**Тэги:** contracts, architecture, domain-separation, seller-role, amanita-international  
**Статус:** ready

---

## Решение (Архитектура)

### Корневая причина: Неправильная связность между доменами
SpiralEngine (социальные роли) и AmanitaInternational (переводы) были неправильно связаны.

### Правильная архитектура - разделение доменов:
```
SpiralEngine (Social Domain)
    ↓ (независимо)
SELLER_ROLE = право создавать инвайты

AmanitaInternational (Translation Domain)
    ↓ (независимо)
SELLER_ROLE = право загружать переводы
```

### Техническое решение:
1. **Убрать зависимость** - _hasSellerRole() проверяет только локальные роли
2. **Автоматическое назначение** - при активации seller дать ему SELLER_ROLE в обоих доменах
3. **Независимость** - домены не знают друг о друге

### Код изменения:
```javascript
// В ComponentActions.action51() добавить:
await this.grantSellerRoleInAmanitaInternational(sellerAddress);

// В AmanitaInternationalLogic._hasSellerRole() оставить только:
return hasRole(SELLER_ROLE, account);
```

---

## Риски/Подводные камни

### Риск 1: Нарушение обратной совместимости
**Симптом:** Существующие seller теряют доступ к переводам
**Решение:** Добавить миграцию для существующих seller

### Риск 2: Дублирование логики активации
**Симптом:** Нужно активировать seller в двух местах
**Решение:** Обернуть в единую функцию активации

### Риск 3: Несогласованность ролей
**Симптом:** Seller имеет роль в одном домене, но не в другом
**Решение:** Всегда назначать роли комплектом

---

## High-ROI доп. задачи

### Задача 1: Создать единый SellerRegistry (+25% надежности)
Централизованный реестр seller со всеми их ролями в разных доменах.

### Задача 2: Автоматическая синхронизация ролей (+15% UX)
При назначении роли в одном домене автоматически назначать в других.

### Задача 3: Доменная модель документации (+10% понимания)
Четко документировать границы доменов и их роли.
