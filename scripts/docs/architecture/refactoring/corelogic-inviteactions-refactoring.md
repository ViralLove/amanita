# Архитектура и план реализации рефакторинга: CoreLogic → InviteActions

**Дата:** 2025-11-22  
**Метод:** `@analysis.mdc`  
**Цель:** Продумать архитектуру и план реализации рефакторинга `CoreLogic.activateSellerBasic()` для делегирования в `InviteActions.activateSeller()`

---

## 📋 Текущее состояние

### CoreLogic.activateSellerBasic() (Текущая реализация)

**Файл:** `scripts/lib/core/CoreLogic.js:53-87`

**Реализация:**
```javascript
async activateSellerBasic(sellerAddress = null, inviteCodes = null) {
  // 1. Получает SpiralEngine через ContractManager
  const spiralEngine = await this.contractManager.getContract('SpiralEngine');
  
  // 2. Генерирует invite codes (12 кодов) если не предоставлены
  const codes = inviteCodes || this.ethersUtils.generateNewInviteCodes(12, 8);
  
  // 3. Прямой вызов activateUser через executeContractWrite
  const activateTx = await this.executeContractWrite(
    spiralEngine,
    'activateUser',
    ['ROOT_INVITE', targetSellerAddress, codes, 0],  // ⚠️ Жестко закодированный 'ROOT_INVITE'
    { gas: 500000 }
  );
  
  // 4. Возвращает только базовую информацию
  return {
    success: true,
    transactionHash: activateTx.transactionHash,
    inviteCodes: codes,
    sellerAddress: targetSellerAddress
  };
}
```

**Ограничения:**
- ❌ Использует жестко закодированный `'ROOT_INVITE'` (не проверяет существование)
- ❌ Нет валидации invite code
- ❌ Нет проверки текущего статуса (не idempotent)
- ❌ Нет назначения SELLER_ROLE
- ❌ Нет сохранения invites в файл
- ❌ Нет делегации в специализированный модуль

### InviteActions.activateSeller() (Целевая реализация)

**Файл:** `scripts/lib/actions/InviteActions.js:824-892`

**Реализация:**
```javascript
async activateSeller(spiralEngine, inviteCode, sellerAddress) {
  // 1. Проверка текущего статуса (idempotent)
  const usedInvite = await spiralEngine.usedInviteByUser(sellerAddress);
  const hasSellerRole = await spiralEngine.hasRole(SELLER_ROLE, sellerAddress);
  
  // 2. Условная активация (если не активирован)
  if (!isActivated) {
    // 2.1. Валидация invite code
    const inviteExists = await spiralEngine.inviteCodeExists(inviteCode);
    if (!inviteExists) {
      throw new Error(`Invite код "${inviteCode}" не существует.`);
    }
    
    // 2.2. Активация через activateUser()
    activationResult = await this.activateUser(spiralEngine, inviteCode, sellerAddress);
    
    // 2.3. Сохранение invites в файл
    await this.saveUserInvites(sellerAddress, newInvites, 'seller');
  }
  
  // 3. Условное назначение роли (если нет роли)
  if (!hasSellerRole) {
    await this.accessControlActions.grantSellerRole(spiralEngine, sellerAddress);
  }
  
  // 4. Возврат полной информации
  return {
    success: true,
    sellerAddress: sellerAddress,
    wasActivated: !isActivated,
    wasRoleGranted: !hasSellerRole,
    newInvites: newInvites,
    activationResult: activationResult
  };
}
```

**Преимущества:**
- ✅ Валидация invite code
- ✅ Idempotent (проверка состояния)
- ✅ Назначение SELLER_ROLE
- ✅ Сохранение invites в файл
- ✅ Обработка ошибок
- ✅ Полная информация о результате

---

## 🎯 Цель рефакторинга

**Основная цель:** Унифицировать логику активации seller, делегировав ее в специализированный модуль `InviteActions`.

**Преимущества:**
1. **Устранение дублирования:** Один источник истины для активации seller
2. **Полнота функциональности:** Все вызовы получают полную логику (валидация, роли, сохранение)
3. **Консистентность:** Все модули используют одинаковую логику активации
4. **Поддержка:** Изменения в логике активации делаются в одном месте
5. **Тестируемость:** Легче тестировать интеграцию между модулями

**Риски:**
- Изменение сигнатуры метода (потребуется обновление всех вызовов)
- Изменение структуры возвращаемого значения
- Возможная потребность в обратной совместимости

---

## 🏗️ Архитектура решения

### Вариант 1: Прямое делегирование (Рекомендуется)

**Концепция:** `CoreLogic.activateSellerBasic()` делегирует в `InviteActions.activateSeller()`.

**Архитектура:**
```
CoreLogic.activateSellerBasic(sellerAddress, inviteCodes)
  ↓
  Получает SpiralEngine через ContractManager
  ↓
  Определяет inviteCode (из параметров или конфига)
  ↓
  InviteActions.activateSeller(spiralEngine, inviteCode, sellerAddress)
    ↓
    - Валидация invite code
    - Активация через activateUser()
    - Назначение SELLER_ROLE
    - Сохранение invites в файл
    ↓
  Возвращает результат (адаптированный под старую структуру или новую)
```

**Изменения в CoreLogic:**
```javascript
class CoreLogic {
  constructor(contractManager, ethersUtils, config, inviteActions = null) {
    this.contractManager = contractManager;
    this.ethersUtils = ethersUtils;
    this.config = config;
    this.inviteActions = inviteActions; // ✅ Новая зависимость (опциональная)
  }

  async activateSellerBasic(sellerAddress = null, inviteCodes = null) {
    // ✅ НОВОЕ: Делегирование в InviteActions, если доступен
    if (this.inviteActions) {
      return await this._activateSellerViaInviteActions(sellerAddress, inviteCodes);
    }
    
    // ✅ СТАРОЕ: Fallback на прямую реализацию (для обратной совместимости)
    return await this._activateSellerDirect(sellerAddress, inviteCodes);
  }

  async _activateSellerViaInviteActions(sellerAddress, inviteCodes) {
    // 1. Получаем SpiralEngine
    const spiralEngine = await this.contractManager.getContract('SpiralEngine');
    if (!spiralEngine) {
      throw new Error('SpiralEngine contract not found');
    }

    // 2. Определяем inviteCode
    // Если inviteCodes предоставлены, используем первый как inviteCode
    // Иначе берем из конфига или используем 'ROOT_INVITE' как fallback
    const inviteCode = inviteCodes && inviteCodes.length > 0 
      ? inviteCodes[0] 
      : this.config.get('deployer.invite') || 'ROOT_INVITE';

    // 3. Определяем sellerAddress
    const targetSellerAddress = sellerAddress || this.config.get('seller.address');
    if (!targetSellerAddress) {
      throw new Error('Seller address not provided');
    }

    // 4. Делегируем в InviteActions
    const result = await this.inviteActions.activateSeller(
      spiralEngine,
      inviteCode,
      targetSellerAddress
    );

    // 5. Адаптируем результат под старую структуру (для обратной совместимости)
    return {
      success: result.success,
      transactionHash: result.activationResult?.txHash || null,
      inviteCodes: result.newInvites || [],
      sellerAddress: result.sellerAddress
    };
  }

  async _activateSellerDirect(sellerAddress, inviteCodes) {
    // ✅ СТАРАЯ реализация (для обратной совместимости, если InviteActions недоступен)
    // ... (текущая реализация)
  }
}
```

**Изменения в CoreManager:**
```javascript
class CoreManager {
  constructor(contractManager, ethersUtils, config, inviteActions = null) {
    this.contractManager = contractManager;
    this.ethersUtils = ethersUtils;
    this.config = config;
    
    // ✅ НОВОЕ: Передаем InviteActions в CoreLogic
    this.coreLogic = new CoreLogic(contractManager, ethersUtils, config, inviteActions);
  }
}
```

**Изменения в IntegrationHarness:**
```javascript
// В setupIntegrationEnvironment()
const { InviteActions } = require('../../lib/actions');
const { AccessControlActions } = require('../../lib/actions');

// Создаем InviteActions для передачи в CoreLogic
const accessControlActions = new AccessControlActions(
  this.modules.contractManager,
  this.modules.ethersUtils,
  this.modules.config
);

const inviteActions = new InviteActions(
  this.modules.contractManager,
  this.modules.ethersUtils,
  this.modules.config,
  accessControlActions
);

// Передаем InviteActions в CoreLogic
this.modules.coreLogic = new CoreLogic(
  this.modules.contractManager,
  this.modules.ethersUtils,
  this.modules.config,
  inviteActions  // ✅ НОВОЕ
);
```

### Вариант 2: Обертка через ActionsManager

**Концепция:** `CoreLogic` получает `ActionsManager` и использует его для доступа к `InviteActions`.

**Архитектура:**
```
CoreLogic.activateSellerBasic(sellerAddress, inviteCodes)
  ↓
  ActionsManager.getInviteActions()
    ↓
  InviteActions.activateSeller(...)
```

**Недостатки:**
- Более сильная связанность (CoreLogic зависит от ActionsManager)
- Более сложная инициализация

**Рекомендация:** ❌ Не рекомендуется

### Вариант 3: Полное удаление activateSellerBasic

**Концепция:** Удалить `CoreLogic.activateSellerBasic()` и использовать напрямую `InviteActions.activateSeller()`.

**Недостатки:**
- Breaking change для всех существующих вызовов
- Требуется обновление всех тестов
- Потеря абстракции на уровне CoreLogic

**Рекомендация:** ❌ Не рекомендуется (слишком радикально для MVP)

---

## ✅ Выбранная архитектура: Вариант 1 (Прямое делегирование)

**Причины:**
1. Минимальные изменения в существующем коде
2. Обратная совместимость (fallback на старую реализацию)
3. Постепенная миграция (можно обновлять вызовы поэтапно)
4. Четкое разделение ответственности (CoreLogic делегирует в специализированный модуль)
5. Легкость тестирования (можно мокировать InviteActions)

---

## 📝 План реализации

### Фаза 1: Добавление зависимости InviteActions в CoreLogic

**Цель:** Добавить опциональную зависимость `InviteActions` в `CoreLogic` без изменения поведения.

**Задачи:**

#### 1.1 Обновить конструктор CoreLogic

**Файл:** `scripts/lib/core/CoreLogic.js:10-15`

**Изменения:**
```javascript
class CoreLogic {
  constructor(contractManager, ethersUtils, config, inviteActions = null) {
    this.contractManager = contractManager;
    this.ethersUtils = ethersUtils;
    this.config = config;
    this.inviteActions = inviteActions; // ✅ НОВОЕ: Опциональная зависимость
  }
}
```

**Критерии приемки:**
- ✅ Конструктор принимает опциональный параметр `inviteActions`
- ✅ Обратная совместимость: все существующие вызовы работают (inviteActions = null)
- ✅ Нет изменений в существующем поведении (inviteActions = null → используется старая логика)

**Время:** 15 минут

**Тестирование:**
- ✅ Все существующие тесты проходят без изменений
- ✅ Новый параметр не ломает существующие вызовы

---

#### 1.2 Вынести текущую реализацию в отдельный метод

**Файл:** `scripts/lib/core/CoreLogic.js:53-87`

**Изменения:**
```javascript
/**
 * Activate seller basic (legacy implementation)
 * @private
 */
async _activateSellerDirect(sellerAddress = null, inviteCodes = null) {
  try {
    const spiralEngine = await this.contractManager.getContract('SpiralEngine');
    if (!spiralEngine) {
      throw new Error('SpiralEngine contract not found');
    }

    const targetSellerAddress = sellerAddress || this.config.get('seller.address');
    if (!targetSellerAddress) {
      throw new Error('Seller address not provided');
    }

    // Generate invite codes if not provided
    const codes = inviteCodes || this.ethersUtils.generateNewInviteCodes(12, 8);

    // Activate seller
    const activateTx = await this.executeContractWrite(
      spiralEngine,
      'activateUser',
      ['ROOT_INVITE', targetSellerAddress, codes, 0],
      { gas: 500000 }
    );

    logger.info(`Seller activated: ${targetSellerAddress}`);
    return {
      success: true,
      transactionHash: activateTx.transactionHash,
      inviteCodes: codes,
      sellerAddress: targetSellerAddress
    };
  } catch (error) {
    logger.error('Failed to activate seller:', error.message);
    throw error;
  }
}

/**
 * Activate seller basic
 * @param {string} sellerAddress - Seller address to activate
 * @param {Array} inviteCodes - Invite codes for activation (deprecated: будет использован первый как inviteCode)
 * @returns {Promise<Object>} - Activation result
 */
async activateSellerBasic(sellerAddress = null, inviteCodes = null) {
  // ✅ НОВОЕ: Делегирование в InviteActions, если доступен
  if (this.inviteActions) {
    return await this._activateSellerViaInviteActions(sellerAddress, inviteCodes);
  }
  
  // ✅ СТАРОЕ: Fallback на прямую реализацию (для обратной совместимости)
  return await this._activateSellerDirect(sellerAddress, inviteCodes);
}
```

**Критерии приемки:**
- ✅ Текущая реализация вынесена в `_activateSellerDirect()`
- ✅ `activateSellerBasic()` вызывает `_activateSellerDirect()` при `inviteActions = null`
- ✅ Все существующие тесты проходят без изменений
- ✅ Поведение не изменилось

**Время:** 30 минут

**Тестирование:**
- ✅ Все существующие тесты проходят
- ✅ Нет регрессий в функциональности

---

### Фаза 2: Реализация делегирования в InviteActions

**Цель:** Добавить метод делегирования `_activateSellerViaInviteActions()`.

**Задачи:**

#### 2.1 Реализовать метод делегирования

**Файл:** `scripts/lib/core/CoreLogic.js` (новый метод после `_activateSellerDirect()`)

**Реализация:**
```javascript
/**
 * Activate seller via InviteActions (delegation)
 * @private
 */
async _activateSellerViaInviteActions(sellerAddress = null, inviteCodes = null) {
  try {
    // 1. Получаем SpiralEngine через ContractManager
    const spiralEngine = await this.contractManager.getContract('SpiralEngine');
    if (!spiralEngine) {
      throw new Error('SpiralEngine contract not found');
    }

    // 2. Определяем targetSellerAddress
    const targetSellerAddress = sellerAddress || this.config.get('seller.address');
    if (!targetSellerAddress) {
      throw new Error('Seller address not provided');
    }

    // 3. Определяем inviteCode
    // Логика: если inviteCodes предоставлены, используем первый как inviteCode
    // Иначе берем из конфига или используем 'ROOT_INVITE' как fallback
    let inviteCode;
    if (inviteCodes && inviteCodes.length > 0) {
      // ⚠️ DEPRECATED: inviteCodes параметр используется для обратной совместимости
      // В новой архитектуре используется только один inviteCode
      inviteCode = inviteCodes[0];
      logger.warn(
        `CoreLogic.activateSellerBasic: Параметр inviteCodes deprecated. ` +
        `Используется первый код "${inviteCode}" как inviteCode. ` +
        `Рекомендуется использовать InviteActions.activateSeller() напрямую.`
      );
    } else {
      // Пытаемся получить из конфига
      inviteCode = this.config.get('deployer.invite') || 
                   this.config.get('invite.deployer') ||
                   'ROOT_INVITE'; // Fallback на старый жестко закодированный invite
      
      if (inviteCode === 'ROOT_INVITE') {
        logger.warn(
          `CoreLogic.activateSellerBasic: Используется fallback inviteCode "ROOT_INVITE". ` +
          `Рекомендуется настроить deployer.invite в конфиге или использовать InviteActions.activateSeller() напрямую.`
        );
      }
    }

    // 4. Делегируем в InviteActions.activateSeller()
    logger.info(`CoreLogic.activateSellerBasic: Делегирование в InviteActions.activateSeller()`);
    const result = await this.inviteActions.activateSeller(
      spiralEngine,
      inviteCode,
      targetSellerAddress
    );

    // 5. Адаптируем результат под старую структуру (для обратной совместимости)
    // Старая структура: { success, transactionHash, inviteCodes, sellerAddress }
    // Новая структура: { success, sellerAddress, wasActivated, wasRoleGranted, newInvites, activationResult }
    return {
      success: result.success,
      transactionHash: result.activationResult?.txHash || null,
      inviteCodes: result.newInvites || [],
      sellerAddress: result.sellerAddress
    };
  } catch (error) {
    logger.error('CoreLogic.activateSellerBasic: Ошибка при делегировании в InviteActions:', error.message);
    throw error;
  }
}
```

**Критерии приемки:**
- ✅ Метод получает SpiralEngine через ContractManager
- ✅ Определяет inviteCode из параметров или конфига
- ✅ Делегирует в `InviteActions.activateSeller()`
- ✅ Адаптирует результат под старую структуру
- ✅ Обрабатывает ошибки с логированием

**Время:** 45 минут

**Тестирование:**
- ✅ Unit тесты для `_activateSellerViaInviteActions()`
- ✅ Интеграционные тесты с моком InviteActions
- ✅ Проверка адаптации результата

---

#### 2.2 Обработка edge cases

**Задачи:**
- Обработка случая, когда `inviteActions` = `null` (fallback на старую логику)
- Обработка случая, когда `inviteCode` не найден в конфиге
- Обработка случая, когда `InviteActions.activateSeller()` выбрасывает ошибку
- Адаптация результата при отсутствии `activationResult`

**Время:** 30 минут

---

### Фаза 3: Обновление инициализации CoreLogic

**Цель:** Передать `InviteActions` в `CoreLogic` при инициализации.

**Задачи:**

#### 3.1 Обновить CoreManager

**Файл:** `scripts/lib/core/index.js:10-18`

**Изменения:**
```javascript
class CoreManager {
  constructor(contractManager, ethersUtils, config, inviteActions = null) {
    this.contractManager = contractManager;
    this.ethersUtils = ethersUtils;
    this.config = config;
    
    // ✅ НОВОЕ: Передаем InviteActions в CoreLogic
    this.coreLogic = new CoreLogic(contractManager, ethersUtils, config, inviteActions);
  }
  
  // ... остальные методы
}
```

**Критерии приемки:**
- ✅ Конструктор принимает опциональный параметр `inviteActions`
- ✅ Передает `inviteActions` в `CoreLogic`
- ✅ Обратная совместимость: все существующие вызовы работают (inviteActions = null)

**Время:** 15 минут

**Тестирование:**
- ✅ Все существующие тесты проходят без изменений

---

#### 3.2 Обновить IntegrationHarness

**Файл:** `scripts/tests/helpers/IntegrationHarness.js:27-70` (примерно)

**Изменения:**
```javascript
async setupIntegrationEnvironment() {
  // ... существующая настройка ...
  
  // ✅ НОВОЕ: Создаем InviteActions и передаем в CoreLogic
  const { InviteActions } = require('../../lib/actions');
  const { AccessControlActions } = require('../../lib/actions');
  
  // Создаем AccessControlActions для InviteActions
  const accessControlActions = new AccessControlActions(
    this.modules.contractManager,
    this.modules.ethersUtils,
    this.modules.config
  );
  
  // Создаем InviteActions
  const inviteActions = new InviteActions(
    this.modules.contractManager,
    this.modules.ethersUtils,
    this.modules.config,
    accessControlActions
  );
  
  // Обновляем CoreLogic с InviteActions
  this.modules.coreLogic = new CoreLogic(
    this.modules.contractManager,
    this.modules.ethersUtils,
    this.modules.config,
    inviteActions  // ✅ НОВОЕ
  );
  
  // Обновляем CoreManager с InviteActions
  this.modules.coreManager = new CoreManager(
    this.modules.contractManager,
    this.modules.ethersUtils,
    this.modules.config,
    inviteActions  // ✅ НОВОЕ
  );
  
  // Сохраняем inviteActions для использования в тестах
  this.modules.inviteActions = inviteActions;
  
  return this.modules;
}
```

**Критерии приемки:**
- ✅ `InviteActions` создается с правильными зависимостями
- ✅ `InviteActions` передается в `CoreLogic`
- ✅ `InviteActions` передается в `CoreManager`
- ✅ Все существующие тесты проходят

**Время:** 30 минут

**Тестирование:**
- ✅ Все интеграционные тесты проходят
- ✅ `CoreLogic` использует делегирование в `InviteActions`

---

#### 3.3 Обновить ActionsManager (если используется для инициализации)

**Файл:** `scripts/lib/actions/index.js:15-50` (примерно)

**Анализ:** Проверить, используется ли `ActionsManager` для инициализации `CoreLogic`.

**Если используется:**
```javascript
class ActionsManager {
  constructor(contractManager, arweaveManager, ethersUtils, config) {
    // ... существующая инициализация ...
    
    // ✅ НОВОЕ: Создаем InviteActions перед CoreLogic
    this.inviteActions = new InviteActions(
      contractManager,
      ethersUtils,
      config,
      this.accessControlActions,
      this.catalogActions
    );
    
    // ✅ ОБНОВЛЕНО: Передаем InviteActions в CoreLogic
    // Если CoreLogic инициализируется здесь
    // ...
  }
}
```

**Время:** 30 минут (если требуется)

---

### Фаза 4: Обновление тестов

**Цель:** Обновить все тесты для работы с новой архитектурой.

**Задачи:**

#### 4.1 Обновить unit тесты CoreLogic

**Файл:** `scripts/tests/unit/core/CoreLogic.test.js`

**Изменения:**
- Добавить тесты для делегирования в `InviteActions`
- Добавить тесты для fallback на старую логику (когда `inviteActions = null`)
- Добавить тесты для адаптации результата
- Обновить существующие тесты (если необходимо)

**Время:** 1 час

---

#### 4.2 Обновить интеграционные тесты

**Файлы:**
- `scripts/tests/integration/flows.integration.test.js`
- `scripts/tests/integration/proof.integration.test.js`

**Изменения:**
- Убедиться, что `IntegrationHarness` передает `InviteActions` в `CoreLogic`
- Обновить тесты для проверки делегирования
- Добавить тесты для проверки интеграции `CoreLogic → InviteActions`

**Время:** 1 час

---

#### 4.3 Добавить новый интеграционный тест

**Файл:** `scripts/tests/integration/core-invite-actions.integration.test.js` (новый)

**Содержание:**
- Тест делегирования `CoreLogic.activateSellerBasic()` → `InviteActions.activateSeller()`
- Тест проверки правильности параметров делегирования
- Тест проверки результата (адаптация структуры)

**Время:** 1 час

---

### Фаза 5: Документация и миграция

**Цель:** Обновить документацию и подготовить миграционный план.

**Задачи:**

#### 5.1 Обновить JSDoc комментарии

**Файл:** `scripts/lib/core/CoreLogic.js`

**Изменения:**
- Обновить JSDoc для `activateSellerBasic()` с указанием делегирования
- Добавить `@deprecated` для параметра `inviteCodes` (если применимо)
- Добавить примеры использования

**Время:** 30 минут

---

#### 5.2 Создать миграционный документ

**Файл:** `scripts/docs/migrations/corelogic-inviteactions-migration.md` (новый)

**Содержание:**
- Описание изменений
- Миграционный путь для существующих вызовов
- Примеры обновления кода
- Breaking changes (если есть)

**Время:** 30 минут

---

#### 5.3 Обновить документацию (выполнено)

**Файл:** `scripts/docs/testing/reference/integration-tests-implementation-reference.md`

**Изменения:**
- Обновить Test #1 с учетом новой архитектуры
- Добавить информацию о делегировании
- Обновить примеры кода

**Время:** 30 минут

---

## 📊 Сводная таблица плана реализации

| Фаза | Задача | Приоритет | Время | Зависимости |
|------|--------|-----------|-------|-------------|
| 1.1 | Обновить конструктор CoreLogic | P0 | 15 мин | - |
| 1.2 | Вынести текущую реализацию в метод | P0 | 30 мин | 1.1 |
| 2.1 | Реализовать делегирование | P0 | 45 мин | 1.2 |
| 2.2 | Обработка edge cases | P0 | 30 мин | 2.1 |
| 3.1 | Обновить CoreManager | P0 | 15 мин | 2.1 |
| 3.2 | Обновить IntegrationHarness | P0 | 30 мин | 3.1 |
| 3.3 | Обновить ActionsManager (если нужно) | P1 | 30 мин | 3.1 |
| 4.1 | Обновить unit тесты | P0 | 1 ч | 2.2 |
| 4.2 | Обновить интеграционные тесты | P0 | 1 ч | 3.2 |
| 4.3 | Добавить новый интеграционный тест | P0 | 1 ч | 4.2 |
| 5.1 | Обновить JSDoc | P1 | 30 мин | 4.1 |
| 5.2 | Создать миграционный документ | P1 | 30 мин | 5.1 |
| 5.3 | Обновить документацию | ✅ Выполнено | - | - |

**Общее время:** ~6-7 часов

---

## ⚠️ Риски и митигации

### Риск 1: Breaking changes в сигнатуре метода

**Митигация:**
- Сохранить старую сигнатуру метода `activateSellerBasic(sellerAddress, inviteCodes)`
- Адаптировать результат под старую структуру
- Добавить предупреждения (warnings) для deprecated параметров

### Риск 2: Изменение структуры результата

**Митигация:**
- Адаптировать результат `InviteActions.activateSeller()` под старую структуру
- Сохранить поля: `success`, `transactionHash`, `inviteCodes`, `sellerAddress`
- Добавить новые поля только если не ломает существующие проверки

### Риск 3: Циклические зависимости

**Митигация:**
- `InviteActions` не зависит от `CoreLogic` (односторонняя зависимость)
- `CoreLogic` имеет опциональную зависимость от `InviteActions` (можно = null)

### Риск 4: Проблемы с тестами

**Митигация:**
- Сохранить fallback на старую логику (для обратной совместимости)
- Обновлять тесты поэтапно
- Добавить новые тесты параллельно со старыми

---

## ✅ Критерии успеха

1. ✅ `CoreLogic.activateSellerBasic()` делегирует в `InviteActions.activateSeller()` при наличии зависимости
2. ✅ Обратная совместимость: все существующие вызовы работают без изменений
3. ✅ Все существующие тесты проходят
4. ✅ Новый интеграционный тест `CoreLogic → InviteActions` проходит
5. ✅ Документация обновлена
6. ✅ Нет регрессий в функциональности

---

**Версия:** 1.0  
**Последнее обновление:** 2025-11-22

