# Архитектура решения: Синхронизация состояния в моках SpiralEngine

**Дата:** 2025-11-22  
**Метод:** `@analysis.mdc`  
**Цель:** Продумать архитектуру решения проблемы синхронизации состояния в моках SpiralEngine для интеграционного теста `core-invite-actions.integration.test.js`

---

## 📋 Текущая проблема

### Симптом
```
Error: AccessControl: Не могу назначить SELLER_ROLE для 0x70997970C51812dc3A010C7d01b50e0d17dc79C8 - 
пользователь не активирован. Активируйте пользователя через activateUser() сначала.
```

### Последовательность вызовов (реальный код)

**Файл:** `scripts/lib/actions/InviteActions.js:824-892`

1. **Step 1: Check status** (строка 831)
   ```javascript
   const usedInvite = await spiralEngine.usedInviteByUser(sellerAddress);
   const isActivated = usedInvite > 0; // false (initial state)
   ```

2. **Step 2: Activate user** (строка 843-856)
   ```javascript
   if (!isActivated) {
     activationResult = await this.activateUser(spiralEngine, inviteCode, sellerAddress);
   }
   ```

   Внутри `activateUser()` (строка 799):
   ```javascript
   const spiralEngineWithSigner = spiralEngine.connect(signer);
   const tx = await spiralEngineWithSigner.activateUser(inviteCode, userAddress, newInvites, 0);
   await tx.wait();
   ```

3. **Step 3: Grant role** (строка 875)
   ```javascript
   await this.accessControlActions.grantSellerRole(spiralEngine, sellerAddress);
   ```

   Внутри `grantSellerRole()` → `checkActivationStatus()` (строка 149):
   ```javascript
   const usedInvite = await spiralEngine.usedInviteByUser(userAddress);
   const isActivated = usedInvite > 0; // ❌ Все ещё false!
   ```

### Корневая причина

**Проблема:** Мок обновляет состояние в `activateUserFn` синхронно, но `checkActivationStatus` вызывается через **другой экземпляр** контракта:

- `activateUser` вызывается через `spiralEngine.connect(signer)` → `spiralEngineWithSigner.activateUser()`
- `checkActivationStatus` вызывается через `spiralEngine` (без `connect()`)

**Текущая реализация `setupContractMock`:**
```javascript
connect: function(signer) {
  return this; // Return self for chaining
}
```

`connect()` возвращает `this`, поэтому это **должен быть тот же объект**, но проблема в том, что:

1. **Состояние обновляется синхронно** в `activateUserFn` через замыкание
2. **Но проверка происходит асинхронно** после `await tx.wait()`
3. **Между обновлением и проверкой** может быть временной разрыв

### Проверка реального кода

**Вызов `activateUser` в `InviteActions.activateUser()`:**
```799:800:scripts/lib/actions/InviteActions.js
const tx = await spiralEngineWithSigner.activateUser(inviteCode, userAddress, newInvites, 0);
await tx.wait();
```

**Вызов `checkActivationStatus` в `AccessControlActions.grantSellerRole()`:**
```149:149:scripts/lib/actions/AccessControlActions.js
const usedInvite = await spiralEngine.usedInviteByUser(userAddress);
```

**Разница:**
- `activateUser` → через `spiralEngineWithSigner` (после `connect()`)
- `checkActivationStatus` → через `spiralEngine` (без `connect()`)

---

## 🔍 Анализ текущей реализации моков

### Текущий мок в `core-invite-actions.integration.test.js`

**Состояние через замыкание:**
```javascript
let activationState = {
  usedInvite: '0',
  isActivated: false,
  hasSellerRole: false,
  SELLER_ROLE: null
};

const usedInviteByUserFn = async (address) => {
  return activationState.usedInvite; // ✅ Использует замыкание
};

const activateUserFn = async (code, user, newInvites, expiry) => {
  activationState.usedInvite = '1'; // ✅ Обновляет состояние синхронно
  activationState.isActivated = true;
  return { hash: '0xdelegate', wait: async () => ({ status: 1 }) };
};
```

**Проблема:** Состояние обновляется **синхронно** в `activateUserFn`, но проверка `checkActivationStatus` происходит **после** `await tx.wait()`, и мок может не сохранять состояние правильно.

### Как работает `setupContractMock`

**Файл:** `scripts/tests/helpers/IntegrationHarness.js:192-232`

```javascript
setupContractMock(contractName, methods) {
  const mockContract = {
    getAddress: async () => `0x${contractName}Address123`,
    connect: function(signer) {
      return this; // Return self for chaining
    }
  };
  
  // Setup method stubs directly on contract (ethers pattern)
  Object.keys(methods).forEach(methodName => {
    const methodConfig = methods[methodName];
    
    const isWriteMethod = methodConfig.encodeABI || 
                         /^(activate|mint|grant|register|suspend|set|update)/.test(methodName);
    
    mockContract[methodName] = async (...args) => {
      // Write methods return transaction
      if (isWriteMethod) {
        return {
          hash: `0x${Math.random().toString(16).substr(2, 64)}`,
          wait: async () => ({ status: 1 })
        };
      }
      
      // Read methods return value
      if (methodConfig.call) {
        return methodConfig.call(...args);
      }
      
      // Default: return transaction
      return {
        hash: `0x${Math.random().toString(16).substr(2, 64)}`,
        wait: async () => ({ status: 1 })
      };
    };
  });
  
  return mockContract;
}
```

**Проблема:** Методы создаются **напрямую на объекте**, и `connect()` возвращает `this`, поэтому состояние должно сохраняться. Но проблема в том, что:

1. `activateUser` обновляет состояние **внутри функции `activateUserFn`**
2. Но `setupContractMock` **переопределяет** метод, создавая новую функцию
3. Новая функция **не вызывает** `activateUserFn` автоматически - она проверяет `isWriteMethod` и возвращает транзакцию

**Проблема:** `setupContractMock` **не использует** `call` функцию для write методов, он просто возвращает транзакцию!

---

## 🎯 Корневая причина (найдена)

### Проблема в `setupContractMock`

**Текущая логика:**
```javascript
mockContract[methodName] = async (...args) => {
  // Write methods return transaction
  if (isWriteMethod) {
    return {
      hash: `0x${Math.random().toString(16).substr(2, 64)}`,
      wait: async () => ({ status: 1 })
    };
  }
  
  // Read methods return value
  if (methodConfig.call) {
    return methodConfig.call(...args); // ✅ Вызывается для read методов
  }
};
```

**Проблема:** Для write методов (как `activateUser`) `setupContractMock` **не вызывает** `methodConfig.call`, он просто возвращает транзакцию! Это значит, что `activateUserFn` **никогда не вызывается**, и состояние **не обновляется**.

**Проверка:** В `core-invite-actions.integration.test.js` (строка 115):
```javascript
activateUser: { call: activateUserFn, encodeABI: '0xactivate' },
```

`encodeABI` присутствует, поэтому `isWriteMethod = true`, и метод возвращает транзакцию **без вызова** `activateUserFn`.

---

## 🏗️ Архитектура решения

### Вариант A: Исправить `setupContractMock` для вызова `call` функции для write методов

**Преимущества:**
- ✅ Централизованное решение
- ✅ Работает для всех тестов
- ✅ Сохраняет совместимость с существующими тестами

**Недостатки:**
- ⚠️ Требует изменений в `IntegrationHarness` (инфраструктура)
- ⚠️ Может повлиять на другие тесты

**Реализация:**
```javascript
mockContract[methodName] = async (...args) => {
  // ✅ FIX: Вызываем call функцию ДО возврата транзакции для write методов
  if (isWriteMethod) {
    // ✅ НОВОЕ: Вызываем call функцию для обновления состояния
    if (methodConfig.call) {
      await methodConfig.call(...args); // Обновляем состояние синхронно
    }
    
    return {
      hash: `0x${Math.random().toString(16).substr(2, 64)}`,
      wait: async () => ({ status: 1 })
    };
  }
  
  // Read methods return value
  if (methodConfig.call) {
    return methodConfig.call(...args);
  }
};
```

### Вариант B: Обновить состояние в `wait()` callback

**Преимущества:**
- ✅ Локальное решение в тесте
- ✅ Не требует изменений в инфраструктуре

**Недостатки:**
- ⚠️ Дублирование логики в каждом тесте
- ⚠️ Не масштабируется на другие тесты

**Реализация:**
```javascript
const activateUserFn = async (code, user, newInvites, expiry) => {
  // Обновляем состояние сразу
  activationState.usedInvite = '1';
  activationState.isActivated = true;
  
  return {
    hash: '0xdelegate',
    wait: async () => {
      // ✅ FIX: Обновляем состояние ещё раз после wait()
      // (хотя оно уже обновлено синхронно выше)
      activationState.usedInvite = '1';
      activationState.isActivated = true;
      return { status: 1 };
    }
  };
};
```

### Вариант C: Использовать stub для методов вместо `setupContractMock`

**Преимущества:**
- ✅ Полный контроль над вызовами
- ✅ Легко отслеживать состояние

**Недостатки:**
- ⚠️ Требует больше кода в каждом тесте
- ⚠️ Не использует существующую инфраструктуру

**Реализация:**
```javascript
const mockSpiralEngine = harness.setupContractMock('SpiralEngine', { /* базовые методы */ });

// ✅ FIX: Заменяем activateUser на stub с полным контролем
sinon.stub(mockSpiralEngine, 'activateUser').callsFake(async (...args) => {
  activationState.usedInvite = '1';
  activationState.isActivated = true;
  return { hash: '0xdelegate', wait: async () => ({ status: 1 }) };
});
```

---

## ✅ Рекомендуемое решение: Вариант A (с улучшением)

### Архитектура

**Принцип:** `setupContractMock` должен вызывать `call` функцию для **всех методов** (read и write), но для write методов вызывать её **до возврата транзакции**.

**Логика:**
1. Для **read методов** (без `encodeABI`): вызывать `call` и возвращать результат
2. Для **write методов** (с `encodeABI`): вызывать `call` для обновления состояния, **затем** возвращать транзакцию

**Почему это правильно:**
- ✅ Соответствует реальному поведению: транзакция выполняется **до** возврата
- ✅ Сохраняет совместимость: если `call` не определён, метод работает как раньше
- ✅ Централизованное решение: работает для всех тестов автоматически

---

## 📝 План реализации

### Phase 1: Исправить `setupContractMock` (P0)

**Файл:** `scripts/tests/helpers/IntegrationHarness.js:192-232`

**Изменения:**
1. Обновить логику для write методов: вызывать `methodConfig.call()` **перед** возвратом транзакции
2. Обработать случай, когда `call` не определён (обратная совместимость)
3. Сохранить существующее поведение для read методов

**Детали реализации:**
```javascript
mockContract[methodName] = async (...args) => {
  // Write methods return transaction
  if (isWriteMethod) {
    // ✅ FIX: Вызываем call функцию для обновления состояния
    // Это критично для state tracking в интеграционных тестах
    if (methodConfig.call) {
      await methodConfig.call(...args); // Обновляем состояние синхронно
    }
    
    return {
      hash: methodConfig.hash || `0x${Math.random().toString(16).substr(2, 64)}`,
      wait: async () => {
        // ✅ FIX: После wait() состояние уже должно быть обновлено
        // (через call выше)
        return { status: 1 };
      }
    };
  }
  
  // Read methods return value
  if (methodConfig.call) {
    return methodConfig.call(...args);
  }
  
  // Default: return transaction (для обратной совместимости)
  return {
    hash: `0x${Math.random().toString(16).substr(2, 64)}`,
    wait: async () => ({ status: 1 })
  };
};
```

**Почему это работает:**
- `activateUser` вызывается через `spiralEngineWithSigner.activateUser()`
- Мок вызывает `activateUserFn(...args)`, который обновляет `activationState`
- `checkActivationStatus` вызывается через `spiralEngine.usedInviteByUser()`
- Мок вызывает `usedInviteByUserFn(address)`, который возвращает `activationState.usedInvite` ('1')
- Состояние синхронизировано через замыкание

### Phase 2: Упростить тест (P1)

**Файл:** `scripts/tests/integration/core-invite-actions.integration.test.js`

**Изменения:**
1. Убрать дублирование логики обновления состояния
2. Упростить `activateUserFn`: просто обновлять состояние, без сложной логики `wait()`
3. Проверить, что состояние корректно отслеживается

**Детали:**
```javascript
const activateUserFn = async (code, user, newInvites, expiry) => {
  // ✅ Упрощённая версия: просто обновляем состояние
  // setupContractMock теперь вызывает эту функцию автоматически
  activationState.usedInvite = '1';
  activationState.isActivated = true;
  
  // ✅ Возвращаем транзакцию (setupContractMock обработает wait())
  // Можно вернуть любое значение - setupContractMock заменит на транзакцию
  return { hash: '0xdelegate' };
};
```

### Phase 3: Валидация (P0)

**Задачи:**
1. Запустить все интеграционные тесты
2. Проверить, что существующие тесты не сломались
3. Проверить, что новый тест проходит

**Ожидаемый результат:**
- ✅ `core-invite-actions.integration.test.js` - все тесты проходят
- ✅ `flows.integration.test.js` - все тесты проходят (не сломались)
- ✅ `proof.integration.test.js` - все тесты проходят (не сломались)

---

## ✅ Результаты выполнения Phase 1

### Статус выполнения (2025-11-22)

**Phase 1: ✅ ВЫПОЛНЕНА**

**Изменения:**
1. ✅ Исправлен `setupContractMock` в `IntegrationHarness.js` (строки 209-241)
   - Добавлен вызов `methodConfig.call()` для write методов перед возвратом транзакции
   - Добавлена поддержка кастомного `hash` из config
   - Сохранена обратная совместимость

2. ✅ Обновлен тест "Parameter Mapping" в `core-invite-actions.integration.test.js`
   - Добавлен state tracking через замыкание
   - Исправлено переопределение `inviteCodeExists` для второго сценария

**Результаты валидации:**
- ✅ Все 4 теста в `core-invite-actions.integration.test.js` проходят:
  - ✅ "должен делегировать активацию seller в InviteActions.activateSeller"
  - ✅ "должен обрабатывать fallback на прямую реализацию, если InviteActions не доступен"
  - ✅ "должен адаптировать результат InviteActions под старую структуру"
  - ✅ "должен правильно определить inviteCode из параметров или конфига"

**Проблема с state tracking: ✅ РЕШЕНА**
- Состояние корректно обновляется при вызове write методов
- `checkActivationStatus` корректно видит обновленное состояние после `activateUser`
- Моки работают синхронно и предсказуемо

---

## ⚠️ Выявленная проблема (не связана с изменениями Phase 1)

### Проблема: Несоответствие `inviteCodes` в `flows.integration.test.js`

**Файл:** `scripts/tests/integration/flows.integration.test.js:225`

**Симптом:**
```
AssertionError: expected [ 'AMANITA-6BE3-87YK', …(11) ] to deeply equal [ 'ea4VEWQZ', 'KoBuTUkV', …(10) ]
```

**Корневая причина:**
После рефакторинга `CoreLogic.activateSellerBasic()` для делегирования в `InviteActions.activateSeller()`:

1. **Старое поведение (`_activateSellerDirect`):**
   - Использует переданные `inviteCodes` напрямую
   - Возвращает те же `inviteCodes` в результате (строка 82)

2. **Новое поведение (`_activateSellerViaInviteActions`):**
   - Игнорирует переданные `inviteCodes` (использует только первый как `inviteCode` для активации)
   - `InviteActions.activateUser()` генерирует **новые** invite codes через `generateAmanitaInviteCodes(12)`
   - Возвращает `result.newInvites` как `inviteCodes` (строка 153)
   - Переданные `codes` игнорируются

**Последовательность вызовов:**
```
flows.integration.test.js:
  codes = modules.ethersUtils.generateNewInviteCodes(12)  // Генерирует коды (формат: 'ea4VEWQZ')
  result = await modules.coreLogic.activateSellerBasic(sellerAddress, codes)
  expect(result.inviteCodes).to.deep.equal(codes)  // ❌ FAIL: ожидает 'ea4VEWQZ', получает 'AMANITA-6BE3-87YK'

CoreLogic._activateSellerViaInviteActions():
  inviteCode = inviteCodes[0]  // Использует только первый
  result = await this.inviteActions.activateSeller(spiralEngine, inviteCode, sellerAddress)
  return { inviteCodes: result.newInvites }  // ✅ Возвращает новые коды из InviteActions

InviteActions.activateUser():
  newInvites = this.generateAmanitaInviteCodes(12)  // Генерирует новые коды (формат: 'AMANITA-XXXX-XXXX')
  // ...
  return { newInvites }
```

**Почему это проблема:**
- Тест `flows.integration.test.js` ожидает, что переданные `codes` будут возвращены в результате
- Это поведение соответствует старой реализации `_activateSellerDirect`
- Но после рефакторинга используется делегирование, которое генерирует новые коды
- Тест не обновлен для нового поведения

**Связано ли с изменениями Phase 1?**
- ❌ **НЕТ** - проблема не связана с изменениями в `setupContractMock`
- ✅ Это архитектурная проблема, связанная с рефакторингом `CoreLogic.activateSellerBasic()`

**Рекомендации по исправлению:**

**Вариант A: Обновить тест (рекомендуется)**
- Изменить тест, чтобы ожидать новые invite codes из `result.newInvites`
- Проверить формат invite codes (AMANITA-XXXX-XXXX), а не точное соответствие

**Вариант B: Исправить `CoreLogic._activateSellerViaInviteActions()` (не рекомендуется)**
- Передавать переданные `inviteCodes` в `InviteActions.activateUser()` вместо генерации новых
- Но это противоречит новой архитектуре, где `InviteActions` сам генерирует invite codes

**Приоритет:** P1 (не критично, тест не блокирует работу, но нужно исправить для честности теста)

---

## 🔄 Альтернативный подход (если Phase 1 не работает)

### Вариант: Использовать стаб для `activateUser` после создания мока

**Преимущества:**
- ✅ Не требует изменений в инфраструктуре
- ✅ Локальное решение в тесте
- ✅ Полный контроль над вызовом

**Недостатки:**
- ⚠️ Дублирование кода в каждом тесте

**Реализация:**
```javascript
const mockSpiralEngine = harness.setupContractMock('SpiralEngine', {
  usedInviteByUser: { call: usedInviteByUserFn },
  hasRole: { call: hasRoleFn },
  // ... другие методы
});

// ✅ FIX: Заменяем activateUser на стаб с полным контролем
const originalActivateUser = mockSpiralEngine.activateUser;
sinon.stub(mockSpiralEngine, 'activateUser').callsFake(async (...args) => {
  // Обновляем состояние синхронно
  activationState.usedInvite = '1';
  activationState.isActivated = true;
  
  // Вызываем оригинальный метод для получения транзакции
  const tx = await originalActivateUser.apply(mockSpiralEngine, args);
  return tx;
});
```

---

## 📊 Сравнение подходов

| Подход | Сложность | Масштабируемость | Обратная совместимость | Рекомендация |
|--------|-----------|------------------|------------------------|--------------|
| **Вариант A** (исправить `setupContractMock`) | Средняя | ✅ Высокая | ✅ Высокая | ✅ **Рекомендуется** |
| **Вариант B** (обновить в `wait()`) | Низкая | ❌ Низкая | ✅ Высокая | ❌ Не рекомендуется |
| **Вариант C** (stub в тесте) | Низкая | ⚠️ Средняя | ✅ Высокая | ⚠️ Альтернатива |
| **Альтернативный** (stub после мока) | Низкая | ⚠️ Средняя | ✅ Высокая | ⚠️ Резервный вариант |

---

## 🎯 Рекомендуемое решение

### Выбрать Вариант A: Исправить `setupContractMock`

**Почему:**
1. ✅ **Централизованное решение** - работает для всех тестов автоматически
2. ✅ **Соответствует реальному поведению** - транзакция выполняется до возврата
3. ✅ **Сохраняет совместимость** - существующие тесты не сломаются
4. ✅ **Масштабируемость** - будущие тесты автоматически получат правильное поведение

**Риски:**
- ⚠️ Может повлиять на другие тесты (требуется валидация)
- ⚠️ Требует изменений в инфраструктуре

**Митигация:**
- Тщательная валидация всех интеграционных тестов
- Проверка обратной совместимости с существующими тестами

---

## 📝 Детальный план реализации (Вариант A)

### Task 1.1: Обновить `setupContractMock` для вызова `call` функции для write методов

**Файл:** `scripts/tests/helpers/IntegrationHarness.js:209-228`

**Изменения:**
```javascript
mockContract[methodName] = async (...args) => {
  // Write methods return transaction
  if (isWriteMethod) {
    // ✅ FIX: Вызываем call функцию для обновления состояния
    // Это критично для state tracking в интеграционных тестах
    // Состояние обновляется ДО возврата транзакции (как в реальном блокчейне)
    if (methodConfig.call) {
      await methodConfig.call(...args);
    }
    
    // ✅ FIX: Используем hash из config если указан, иначе генерируем случайный
    const txHash = methodConfig.hash || `0x${Math.random().toString(16).substr(2, 64)}`;
    
    return {
      hash: txHash,
      wait: async () => {
        // ✅ FIX: После wait() состояние уже обновлено через call выше
        return { status: 1 };
      }
    };
  }
  
  // Read methods return value
  if (methodConfig.call) {
    return methodConfig.call(...args);
  }
  
  // Default: return transaction (для обратной совместимости)
  return {
    hash: `0x${Math.random().toString(16).substr(2, 64)}`,
    wait: async () => ({ status: 1 })
  };
};
```

**Время:** 30 минут  
**Приоритет:** P0

### Task 1.2: Упростить `activateUserFn` в тесте

**Файл:** `scripts/tests/integration/core-invite-actions.integration.test.js:78-98`

**Изменения:**
```javascript
const activateUserFn = async (code, user, newInvites, expiry) => {
  // ✅ Упрощённая версия: просто обновляем состояние
  // setupContractMock теперь вызывает эту функцию автоматически для write методов
  activationState.usedInvite = '1';
  activationState.isActivated = true;
  
  // ✅ Возвращаем транзакцию (setupContractMock обработает wait())
  // Hash можно указать в config, иначе будет сгенерирован случайный
  return { hash: '0xdelegate' };
};
```

**Время:** 15 минут  
**Приоритет:** P1

### Task 1.3: Валидация изменений

**Задачи:**
1. Запустить `core-invite-actions.integration.test.js`
2. Запустить `flows.integration.test.js`
3. Запустить `proof.integration.test.js`
4. Проверить, что все тесты проходят

**Время:** 15 минут  
**Приоритет:** P0

---

## 🧪 Критерии приемки

### AC1: Тест делегирования проходит
- ✅ `core-invite-actions.integration.test.js:40` - "должен делегировать активацию seller в InviteActions.activateSeller"
- ✅ `checkActivationStatus` возвращает `true` после `activateUser`
- ✅ `grantSellerRole` вызывается успешно
- ✅ Состояние отслеживается корректно

### AC2: Обратная совместимость
- ✅ Все существующие интеграционные тесты проходят
- ✅ `flows.integration.test.js` - все тесты проходят
- ✅ `proof.integration.test.js` - все тесты проходят

### AC3: Корректность моков
- ✅ Состояние обновляется синхронно при вызове write методов
- ✅ Состояние доступно через все экземпляры контракта (с `connect()` и без)
- ✅ Read методы возвращают актуальное состояние

---

## 🔍 Дополнительные улучшения (опционально)

### Improvement 1: Поддержка кастомного hash в моках

**Цель:** Позволить тестам указывать кастомный hash для транзакций

**Реализация:**
```javascript
activateUser: { 
  call: activateUserFn, 
  encodeABI: '0xactivate',
  hash: '0xdelegate' // ✅ Опционально: кастомный hash
}
```

### Improvement 2: Логирование вызовов методов в моках

**Цель:** Упростить отладку интеграционных тестов

**Реализация:**
```javascript
mockContract[methodName] = async (...args) => {
  if (process.env.DEBUG_MOCKS) {
    console.log(`[MOCK] ${contractName}.${methodName}(${args.join(', ')})`);
  }
  // ... остальная логика
};
```

---

## 📚 Связанная документация

- **[reference/integration-tests-implementation-reference.md](../reference/integration-tests-implementation-reference.md)** - Справочник по реализации интеграционных тестов
- **[refactoring/corelogic-inviteactions-refactoring.md](../../architecture/refactoring/corelogic-inviteactions-refactoring.md)** - Рефакторинг CoreLogic → InviteActions
- **[Testing-Architecture.md](../../Testing-Architecture.md)** - Архитектура тестирования

---

---

## 📋 Следующие шаги

### Phase 2: Упростить тест (P1) - ОПЦИОНАЛЬНО

**Статус:** ⏸️ Отложено (Phase 1 решила основную проблему)

**Примечание:** После выполнения Phase 1 тесты работают корректно, упрощение не критично.

### Phase 3.1: Исправить проблему с `inviteCodes` в `flows.integration.test.js` (P1)

**Задачи:**
1. Обновить тест "должен выполнить complete seller activation flow" в `flows.integration.test.js`
2. Изменить проверку `result.inviteCodes` на проверку формата (AMANITA-XXXX-XXXX) или убрать точное соответствие
3. Проверить, что тест проходит с новым поведением

**Время:** 15 минут  
**Приоритет:** P1

---

**Версия:** 1.1  
**Последнее обновление:** 2025-11-22  
**Статус:** ✅ Phase 1 выполнена, Phase 3.1 ожидает реализации

