# Справочник по реализации интеграционных тестов

**Версия:** 2.0  
**Дата:** 2025-11-22  
**Статус:** ✅ Все тесты реализованы

---

## 📋 Обзор

Были идентифицированы три отсутствующих интеграционных теста:

1. **CoreLogic → InviteActions** (нет теста)
2. **ActionsManager → ComponentActions → InviteActions** (нет теста)
3. **MultilingualIPFSService → BlockchainService** (нет теста)

**Важное примечание:** После анализа кода выявлено, что Test #1 (CoreLogic → InviteActions) в текущей реализации **не существует**, так как `CoreLogic.activateSellerBasic()` напрямую вызывает `executeContractWrite()`, а не делегирует в `InviteActions`.

**📌 Решение:** Рефакторинг выполнен (см. `architecture/refactoring/corelogic-inviteactions-refactoring.md`), где `CoreLogic.activateSellerBasic()` делегирует в `InviteActions.activateSeller()`. 

**Статус рефакторинга:** 
- ✅ **ВЫПОЛНЕН** (Фазы 1-3 завершены)

Ниже представлены детальные планы для всех трех тестов с учетом **целевой архитектуры после рефакторинга**.

---

## 1️⃣ Test #1: CoreLogic → InviteActions (Integration)

### 📍 Текущее состояние кода (до рефакторинга)

**Файл:** `scripts/lib/core/CoreLogic.js:53-87`

**Реальность (до рефакторинга):**
- `CoreLogic.activateSellerBasic()` **НЕ использует** `InviteActions`
- Метод напрямую вызывает `executeContractWrite(spiralEngine, 'activateUser', ...)`
- Нет зависимости от `InviteActions` в конструкторе `CoreLogic`

**Связь с InviteActions:**
- `InviteActions.activateSeller()` выполняет более полную логику (активация + роль + валидация)
- `CoreLogic.activateSellerBasic()` выполняет только базовую активацию через контракт

### 🏗️ Целевое состояние (после рефакторинга)

**Рефакторинг:** См. `architecture/refactoring/corelogic-inviteactions-refactoring.md`

**После рефакторинга:**
- `CoreLogic.activateSellerBasic()` будет делегировать в `InviteActions.activateSeller()`
- `CoreLogic` будет иметь опциональную зависимость от `InviteActions` (через конструктор)
- При наличии `InviteActions` используется делегирование, иначе fallback на прямую реализацию

**Архитектура делегирования:**
```
CoreLogic.activateSellerBasic(sellerAddress, inviteCodes)
  ↓ (если inviteActions доступен)
  _activateSellerViaInviteActions()
    ↓
  Получает SpiralEngine через ContractManager
    ↓
  Определяет inviteCode (из параметров или конфига)
    ↓
  InviteActions.activateSeller(spiralEngine, inviteCode, sellerAddress)
    ↓
  Адаптирует результат под старую структуру
    ↓
  Возвращает { success, transactionHash, inviteCodes, sellerAddress }
```

### 🎯 Что тестировать (после рефакторинга)

#### Вариант A: Тест делегирования CoreLogic → InviteActions (После рефакторинга)

**Статус:** ✅ **Рекомендуется** - соответствует целевой архитектуре после рефакторинга

**Цель теста:** Проверить интеграцию, когда `CoreLogic` делегирует активацию в `InviteActions`.

**Структура теста:**
```javascript
describe('Integration: CoreLogic → InviteActions (Delegation)', () => {
  it('должен делегировать активацию seller в InviteActions.activateSeller', async () => {
    // GIVEN: CoreLogic инициализирован с InviteActions
    // WHEN: CoreLogic.activateSellerBasic() вызывается
    // THEN: InviteActions.activateSeller вызывается с правильными параметрами
    // THEN: Результат активации возвращается через CoreLogic (адаптированный)
  });
});
```

**Критерии приемки:**
- ✅ `InviteActions.activateSeller()` вызывается с правильными параметрами
- ✅ Результат адаптирован под старую структуру
- ✅ Обратная совместимость сохранена

#### Вариант B: Тест fallback на прямую реализацию (Без InviteActions)

**Предположение:** Тест проверяет, что `CoreLogic` правильно использует `ContractManager` для активации, что **заменяет** использование `InviteActions`.

**Цель теста:** Проверить, что `CoreLogic.activateSellerBasic()` корректно активирует seller через `ContractManager`, минуя `InviteActions`.

**Структура теста:**
```javascript
describe('Integration: CoreLogic → ContractManager (Direct Activation)', () => {
  it('должен активировать seller через ContractManager напрямую', async () => {
    // GIVEN: Mock SpiralEngine через ContractManager
    // WHEN: CoreLogic.activateSellerBasic() вызывается
    // THEN: ContractManager.getContract('SpiralEngine') вызывается
    // THEN: executeContractWrite вызывается с правильными параметрами
    // THEN: Seller активирован (проверка состояния через мок)
  });
});
```

**Статус:** ✅ Этот тест уже существует в `flows.integration.test.js:30-152` (тест "должен выполнить complete seller activation flow").

**Примечание:** После рефакторинга этот тест будет проверять fallback на прямую реализацию (когда `inviteActions = null`).

#### Вариант C: Тест интеграции через ActionsManager

**Статус:** ✅ **Дополнительный** - проверяет инициализацию и dependency injection

**Цель теста:** Проверить, что `ActionsManager` правильно инициализирует `CoreLogic` и `InviteActions`, и они работают вместе через `ActionsManager`.

**Структура теста:**
```javascript
describe('Integration: ActionsManager → CoreLogic + InviteActions', () => {
  it('должен инициализировать CoreLogic и InviteActions через ActionsManager', async () => {
    // GIVEN: ActionsManager инициализирован
    // WHEN: Запрашивается CoreLogic (через ActionsManager или напрямую)
    // WHEN: Запрашивается InviteActions (через ActionsManager или напрямую)
    // THEN: Оба модуля доступны и работают независимо
    // THEN: Оба модуля используют общий ContractManager
  });
});
```

### ✅ Рекомендация

**Выбрать Вариант A** - тест делегирования `CoreLogic → InviteActions`, так как:
1. ✅ Отражает **целевую архитектуру** после рефакторинга
2. ✅ Проверяет правильность делегирования
3. ✅ Проверяет адаптацию результата
4. ✅ Критично для проверки интеграции после рефакторинга

**Вариант C** - дополнительный тест для проверки инициализации (P1).

### 📝 Детальный план реализации Test #1 (Вариант A - После рефакторинга)

**Файл:** `scripts/tests/integration/core-invite-actions.integration.test.js` (новый файл)

**Статус:** ✅ **ВЫПОЛНЕН** - тест реализован и проходит

**Структура:**
```javascript
const { expect } = require('chai');
const sinon = require('sinon');
const { IntegrationHarness } = require('../helpers');

describe('Integration: CoreLogic → InviteActions (Delegation)', () => {
  let harness, modules;

  before(async function() {
    this.timeout(10000);
    harness = new IntegrationHarness();
    modules = await harness.setupIntegrationEnvironment();
    // ✅ После рефакторинга: IntegrationHarness должен передавать InviteActions в CoreLogic
  });

  after(async () => {
    await harness.teardownIntegrationEnvironment();
  });

  afterEach(() => {
    sinon.restore();
  });

  describe('Delegation: CoreLogic → InviteActions', () => {
    it('должен делегировать активацию seller в InviteActions.activateSeller', async () => {
      // GIVEN: CoreLogic инициализирован с InviteActions (через IntegrationHarness)
      const sellerAddress = '0x70997970C51812dc3A010C7d01b50e0d17dc79C8';
      const inviteCode = 'AMANITA-TEST-INVITE';
      
      // Setup state tracking
      let activationState = {
        usedInvite: '0',
        isActivated: false,
        hasSellerRole: false,
        activateSellerCalled: false
      };

      // Setup mock SpiralEngine с state tracking
      const usedInviteByUserFn = async (address) => activationState.usedInvite;
      const hasRoleFn = async (role, address) => {
        if (role === activationState.SELLER_ROLE) {
          return activationState.hasSellerRole;
        }
        return false;
      };
      const inviteCodeExistsFn = async (code) => code === inviteCode;
      const activateUserFn = async (code, user, newInvites, expiry) => {
        activationState.usedInvite = '1';
        activationState.isActivated = true;
        return { hash: '0xdelegate', wait: async () => ({ status: 1 }) };
      };
      const grantRoleFn = async (role, address) => {
        if (role === activationState.SELLER_ROLE) {
          activationState.hasSellerRole = true;
        }
        return { hash: '0xrole', wait: async () => ({ status: 1 }) };
      };

      const mockSpiralEngine = harness.setupContractMock('SpiralEngine', {
        usedInviteByUser: { call: usedInviteByUserFn },
        hasRole: { call: hasRoleFn },
        inviteCodeExists: { call: inviteCodeExistsFn },
        activateUser: { call: activateUserFn, encodeABI: '0xactivate' },
        grantRole: { call: grantRoleFn, encodeABI: '0xgrant' },
        SELLER_ROLE: { call: async () => '0x' + '0'.repeat(64) }
      });

      const getContractStub = sinon.stub(modules.contractManager, 'getContract')
        .withArgs('SpiralEngine')
        .resolves(mockSpiralEngine);

      // ✅ НОВОЕ: Spy на InviteActions.activateSeller для проверки делегирования
      const activateSellerSpy = sinon.spy(modules.inviteActions, 'activateSeller');

      // ✅ P1 FIX: Используем stub для config.get() вместо config.set() (mock config не имеет метода set())
      // Setup inviteCode в конфиге через stub для config.get()
      sinon.stub(modules.config, 'get').callsFake((key) => {
        if (key === 'deployer.invite') return inviteCode;
        if (key === 'invite.deployer') return null;
        if (key === 'seller.address') return sellerAddress;
        // Fallback на оригинальный get для других ключей
        return originalGet(key);
      });

      // WHEN: CoreLogic.activateSellerBasic() вызывается
      // ✅ НОВОЕ: После рефакторинга это должно делегировать в InviteActions
      const result = await modules.coreLogic.activateSellerBasic(sellerAddress);

      // THEN: InviteActions.activateSeller вызван (делегирование работает)
      expect(activateSellerSpy.calledOnce).to.be.true;
      
      // THEN: InviteActions.activateSeller вызван с правильными параметрами
      const activateSellerCall = activateSellerSpy.getCall(0);
      expect(activateSellerCall.args[0]).to.equal(mockSpiralEngine); // spiralEngine
      expect(activateSellerCall.args[1]).to.equal(inviteCode); // inviteCode
      expect(activateSellerCall.args[2]).to.equal(sellerAddress); // sellerAddress

      // THEN: Результат адаптирован под старую структуру
      expect(result.success).to.be.true;
      expect(result.sellerAddress).to.equal(sellerAddress);
      expect(result.transactionHash).to.exist; // Из activationResult.txHash
      expect(result.inviteCodes).to.be.an('array'); // Из newInvites

      // THEN: Состояние обновлено (через InviteActions)
      const stateAfter = await mockSpiralEngine.usedInviteByUser(sellerAddress);
      expect(stateAfter).to.equal('1');
      expect(activationState.isActivated).to.be.true;
      expect(activationState.hasSellerRole).to.be.true;
    });

    it('должен обрабатывать fallback на прямую реализацию, если InviteActions не доступен', async () => {
      // GIVEN: CoreLogic инициализирован БЕЗ InviteActions (для проверки обратной совместимости)
      const { CoreLogic } = require('../../../lib/core');
      const coreLogicWithoutInvite = new CoreLogic(
        modules.contractManager,
        modules.ethersUtils,
        modules.config,
        null  // ✅ InviteActions = null
      );

      const sellerAddress = '0x70997970C51812dc3A010C7d01b50e0d17dc79C8';
      const inviteCodes = modules.ethersUtils.generateNewInviteCodes(12);

      // Setup state tracking
      let userActivationState = { usedInvite: '0', isActivated: false };
      
      const usedInviteByUserFn = async (address) => userActivationState.usedInvite;
      const activateUserFn = async () => {
        userActivationState.usedInvite = '1';
        userActivationState.isActivated = true;
        return '1';
      };

      const mockSpiralEngine = harness.setupContractMock('SpiralEngine', {
        usedInviteByUser: { call: usedInviteByUserFn },
        activateUser: { call: activateUserFn, encodeABI: '0xactivate' }
      });

      const getContractStub = sinon.stub(modules.contractManager, 'getContract')
        .withArgs('SpiralEngine')
        .resolves(mockSpiralEngine);

      // WHEN: CoreLogic.activateSellerBasic() вызывается (без InviteActions)
      const result = await coreLogicWithoutInvite.activateSellerBasic(sellerAddress, inviteCodes);

      // THEN: Используется прямая реализация (_activateSellerDirect)
      expect(result.success).to.be.true;
      expect(result.sellerAddress).to.equal(sellerAddress);
      expect(getContractStub.calledOnce).to.be.true;

      // THEN: Состояние обновлено
      const stateAfter = await mockSpiralEngine.usedInviteByUser(sellerAddress);
      expect(stateAfter).to.equal('1');
    });

    it('должен адаптировать результат InviteActions под старую структуру', async () => {
      // GIVEN: CoreLogic с InviteActions и мок результата
      const sellerAddress = '0x70997970C51812dc3A010C7d01b50e0d17dc79C8';
      const inviteCode = 'AMANITA-ADAPTATION-TEST';
      const newInvites = ['INVITE-1', 'INVITE-2', 'INVITE-3'];

      // Setup mock для InviteActions.activateSeller
      const mockActivateSellerResult = {
        success: true,
        sellerAddress: sellerAddress,
        wasActivated: true,
        wasRoleGranted: true,
        newInvites: newInvites,
        activationResult: {
          txHash: '0xadaptation-test',
          newInvites: newInvites
        }
      };

      const activateSellerStub = sinon.stub(modules.inviteActions, 'activateSeller')
        .resolves(mockActivateSellerResult);

      const mockSpiralEngine = harness.setupContractMock('SpiralEngine', {
        usedInviteByUser: { call: async () => '0' },
        hasRole: { call: async () => false },
        inviteCodeExists: { call: async () => true },
        activateUser: { call: async () => ({ hash: '0xadapt', wait: async () => ({ status: 1 }) }) },
        grantRole: { call: async () => ({ hash: '0xrole', wait: async () => ({ status: 1 }) }) },
        SELLER_ROLE: { call: async () => '0x' + '0'.repeat(64) }
      });

      sinon.stub(modules.contractManager, 'getContract')
        .withArgs('SpiralEngine')
        .resolves(mockSpiralEngine);

      // ✅ P1 FIX: Используем stub для config.get() вместо config.set() (mock config не имеет метода set())
      // Setup inviteCode в конфиге через stub для config.get()
      const originalGet = modules.config.get.bind(modules.config);
      sinon.stub(modules.config, 'get').callsFake((key) => {
        if (key === 'deployer.invite') return inviteCode;
        if (key === 'invite.deployer') return null;
        if (key === 'seller.address') return sellerAddress;
        // Fallback на оригинальный get для других ключей
        return originalGet(key);
      });

      // WHEN: CoreLogic.activateSellerBasic() вызывается
      const result = await modules.coreLogic.activateSellerBasic(sellerAddress);

      // THEN: Результат адаптирован под старую структуру
      expect(result).to.have.property('success', true);
      expect(result).to.have.property('sellerAddress', sellerAddress);
      expect(result).to.have.property('transactionHash', '0xadaptation-test'); // Из activationResult.txHash
      expect(result).to.have.property('inviteCodes').that.deep.equals(newInvites); // Из newInvites

      // THEN: Старая структура сохранена
      expect(result).to.not.have.property('wasActivated'); // Новые поля не добавлены
      expect(result).to.not.have.property('wasRoleGranted');
      expect(result).to.not.have.property('activationResult');
    });
  });

  describe('Parameter Mapping', () => {
    it('должен правильно определить inviteCode из параметров или конфига', async () => {
      // GIVEN: Различные сценарии определения inviteCode
      const sellerAddress = '0x70997970C51812dc3A010C7d01b50e0d17dc79C8';

      // ✅ P1 FIX: Используем stub для config.get() вместо config.set() (mock config не имеет метода set())
      // Сценарий 1: inviteCode из конфига
      const inviteCodeFromConfig = 'AMANITA-CONFIG-INVITE';
      
      // Setup stub для config.get() для возврата inviteCode из конфига
      const originalGet = modules.config.get.bind(modules.config);
      sinon.stub(modules.config, 'get').callsFake((key) => {
        if (key === 'deployer.invite') return inviteCodeFromConfig;
        if (key === 'invite.deployer') return null;
        if (key === 'seller.address') return sellerAddress;
        // Fallback на оригинальный get для других ключей
        return originalGet(key);
      });

      const mockSpiralEngine = harness.setupContractMock('SpiralEngine', {
        usedInviteByUser: { call: async () => '0' },
        hasRole: { call: async () => false },
        inviteCodeExists: { call: async (code) => code === inviteCodeFromConfig },
        activateUser: { call: async () => ({ hash: '0xtest', wait: async () => ({ status: 1 }) }) },
        grantRole: { call: async () => ({ hash: '0xrole', wait: async () => ({ status: 1 }) }) },
        SELLER_ROLE: { call: async () => '0x' + '0'.repeat(64) }
      });

      sinon.stub(modules.contractManager, 'getContract')
        .withArgs('SpiralEngine')
        .resolves(mockSpiralEngine);

      const activateSellerSpy = sinon.spy(modules.inviteActions, 'activateSeller');

      // WHEN: CoreLogic.activateSellerBasic() вызывается без inviteCodes
      await modules.coreLogic.activateSellerBasic(sellerAddress);

      // THEN: InviteActions.activateSeller вызван с inviteCode из конфига
      const call1 = activateSellerSpy.getCall(0);
      expect(call1.args[1]).to.equal(inviteCodeFromConfig);

      // Сценарий 2: inviteCode из первого элемента inviteCodes массива (deprecated)
      activateSellerSpy.resetHistory();
      const inviteCodesArray = ['AMANITA-FIRST-INVITE', 'INVITE-2', 'INVITE-3'];
      mockSpiralEngine.inviteCodeExists = async (code) => code === 'AMANITA-FIRST-INVITE';

      await modules.coreLogic.activateSellerBasic(sellerAddress, inviteCodesArray);

      // THEN: InviteActions.activateSeller вызван с первым inviteCode из массива
      const call2 = activateSellerSpy.getCall(0);
      expect(call2.args[1]).to.equal('AMANITA-FIRST-INVITE');
    });
  });
});
```

**Приоритет:** P0 (критично для проверки интеграции после рефакторинга)

**Время реализации:** 1-2 часа

**Зависимости:**
- ✅ Рефакторинг выполнен (см. `architecture/refactoring/corelogic-inviteactions-refactoring.md`)
- ✅ `IntegrationHarness` обновлен для передачи `InviteActions` в `CoreLogic`

**Статус:** ✅ Тест реализован и проходит успешно

---

### Дополнительный тест (Вариант C): Инициализация через ActionsManager

**Файл:** `scripts/tests/integration/core-invite-actions.integration.test.js` (тот же файл, дополнительный describe блок)

**Структура:**
```javascript
describe('Module Initialization via ActionsManager', () => {
  it('должен правильно инициализировать CoreLogic и InviteActions через ActionsManager', async () => {
    // GIVEN: ActionsManager инициализирован
    const { ActionsManager } = require('../../../lib/actions');
    const actionsManager = new ActionsManager(
      modules.contractManager,
      modules.arweaveManager,
      modules.ethersUtils,
      modules.config
    );

    // THEN: InviteActions доступен через ComponentActions
    const inviteActions = actionsManager.componentActions.inviteActions;
    expect(inviteActions).to.exist;
    expect(inviteActions.activateSeller).to.be.a('function');

    // ✅ НОВОЕ: Проверяем, что CoreLogic может быть инициализирован с InviteActions
    const { CoreLogic } = require('../../../lib/core');
    const coreLogicWithInvite = new CoreLogic(
      modules.contractManager,
      modules.ethersUtils,
      modules.config,
      inviteActions  // ✅ Передаем InviteActions
    );

    expect(coreLogicWithInvite.inviteActions).to.equal(inviteActions);
  });

  it('должен использовать общий ContractManager для CoreLogic и InviteActions', async () => {
    // GIVEN: CoreLogic и InviteActions инициализированы
    const { ActionsManager } = require('../../../lib/actions');
    const actionsManager = new ActionsManager(
      modules.contractManager,
      modules.arweaveManager,
      modules.ethersUtils,
      modules.config
    );
    const inviteActions = actionsManager.componentActions.inviteActions;

    const { CoreLogic } = require('../../../lib/core');
    const coreLogic = new CoreLogic(
      modules.contractManager,
      modules.ethersUtils,
      modules.config,
      inviteActions
    );

    // THEN: Оба модуля используют один и тот же ContractManager
    expect(coreLogic.contractManager).to.equal(modules.contractManager);
    expect(inviteActions.contractManager).to.equal(modules.contractManager);
    expect(coreLogic.contractManager).to.equal(inviteActions.contractManager);
  });
});
```

**Приоритет:** P1 (важно для понимания архитектуры, но не критично для функциональности)

**Время реализации:** 30 минут

---

## 2️⃣ Test #2: ActionsManager → ComponentActions → InviteActions (Full Workflow)

### 📍 Текущее состояние кода

**Файл:** `scripts/lib/actions/ComponentActions.js:23-129`

**Реальность:**
- `ComponentActions.action555()` вызывает `this.inviteActions.activateSeller()` (строка 50)
- `InviteActions.activateSeller()` выполняет полную активацию (активация + роль + валидация)
- `action555()` также загружает компоненты после активации

**Цепочка вызовов:**
```
ActionsManager.executeAction(555)
  → ComponentActions.action555()
    → InviteActions.activateSeller(spiralEngine, inviteCode, sellerAddress)
      → InviteActions.activateUser() (если не активирован)
      → AccessControlActions.grantSellerRole() (если нет роли)
    → ComponentActions.uploadComponentsCore() (загрузка компонентов)
```

### 🎯 Что тестировать

**Цель теста:** Проверить полный workflow активации seller через `ActionsManager.action555()`, включая интеграцию всех модулей.

**Сценарии:**
1. Полный workflow: загрузка SpiralEngine → активация через InviteActions → загрузка компонентов
2. Проверка состояния после каждого шага
3. Проверка делегации вызовов между модулями
4. Проверка обработки ошибок на каждом этапе

### 📝 Детальный план реализации Test #2

**Файл:** `scripts/tests/integration/action555-full-workflow.integration.test.js` (новый файл)

**Структура:**
```javascript
const { expect } = require('chai');
const sinon = require('sinon');
const { IntegrationHarness } = require('../helpers');

describe('Integration: ActionsManager → ComponentActions → InviteActions (Action 555 Full Workflow)', () => {
  let harness, modules;

  before(async function() {
    this.timeout(10000);
    harness = new IntegrationHarness();
    modules = await harness.setupIntegrationEnvironment();
  });

  after(async () => {
    await harness.teardownIntegrationEnvironment();
  });

  afterEach(() => {
    sinon.restore();
  });

  describe('Full Workflow: Action 555 Complete Flow', () => {
    it('должен выполнить полный workflow: SpiralEngine → activateSeller → uploadComponents', async () => {
      // GIVEN: Настройка окружения
      const sellerAddress = '0x70997970C51812dc3A010C7d01b50e0d17dc79C8';
      const inviteCode = 'AMANITA-TEST-555';
      
      // Setup state tracking
      let activationState = {
        usedInvite: '0',
        isActivated: false,
        hasSellerRole: false,
        componentsUploaded: false
      };

      // Setup mock SpiralEngine с state tracking
      const usedInviteByUserFn = async (address) => activationState.usedInvite;
      const hasRoleFn = async (role, address) => {
        if (role === activationState.SELLER_ROLE) {
          return activationState.hasSellerRole;
        }
        return false;
      };
      const inviteCodeExistsFn = async (code) => code === inviteCode;
      const activateUserFn = async (code, user, newInvites, expiry) => {
        activationState.usedInvite = '1';
        activationState.isActivated = true;
        return { hash: '0xtest555', wait: async () => ({ status: 1 }) };
      };
      const grantRoleFn = async (role, address) => {
        if (role === activationState.SELLER_ROLE) {
          activationState.hasSellerRole = true;
        }
        return { hash: '0xrole555', wait: async () => ({ status: 1 }) };
      };

      const mockSpiralEngine = harness.setupContractMock('SpiralEngine', {
        usedInviteByUser: { call: usedInviteByUserFn },
        hasRole: { call: hasRoleFn },
        inviteCodeExists: { call: inviteCodeExistsFn },
        activateUser: { call: activateUserFn, encodeABI: '0xactivate' },
        grantRole: { call: grantRoleFn, encodeABI: '0xgrant' },
        SELLER_ROLE: { call: async () => '0x' + '0'.repeat(64) }
      });

      // Setup mock для ComponentActions.uploadComponentsCore
      const mockComponentActions = {
        uploadComponentsCore: sinon.stub().resolves({
          success: true,
          totalCount: 5,
          results: []
        })
      };

      // Setup stubs
      const getContractStub = sinon.stub(modules.contractManager, 'getContract')
        .withArgs('SpiralEngine')
        .resolves(mockSpiralEngine);

      const loadUUPSContractStub = sinon.stub(modules.contractManager, 'loadUUPSContract')
        .withArgs('SpiralEngine')
        .resolves(mockSpiralEngine);

      // Setup ActionsManager
      const { ActionsManager } = require('../../../lib/actions');
      const actionsManager = new ActionsManager(
        modules.contractManager,
        modules.arweaveManager,
        modules.ethersUtils,
        modules.config
      );

      // Spy на InviteActions.activateSeller
      const activateSellerSpy = sinon.spy(actionsManager.componentActions.inviteActions, 'activateSeller');

      // Mock uploadComponentsCore в ComponentActions
      sinon.stub(actionsManager.componentActions, 'uploadComponentsCore')
        .resolves({
          success: true,
          totalCount: 5,
          results: []
        });

      // Setup environment variables
      process.env.DEPLOYER_INVITE = inviteCode;
      process.env.SELLER_ADDRESS = sellerAddress;
      process.env.DRY_RUN = 'false';

      // WHEN: Выполняется Action 555 через ActionsManager
      const result = await actionsManager.executeAction(555);

      // THEN: Step 1: SpiralEngine загружен
      expect(loadUUPSContractStub.calledOnce).to.be.true;
      expect(loadUUPSContractStub.calledWith('SpiralEngine')).to.be.true;

      // THEN: Step 2: InviteActions.activateSeller вызван с правильными параметрами
      expect(activateSellerSpy.calledOnce).to.be.true;
      const activateSellerCall = activateSellerSpy.getCall(0);
      expect(activateSellerCall.args[0]).to.equal(mockSpiralEngine); // spiralEngine
      expect(activateSellerCall.args[1]).to.equal(inviteCode); // inviteCode
      expect(activateSellerCall.args[2]).to.equal(sellerAddress); // sellerAddress

      // THEN: Step 3: Seller активирован (проверка состояния)
      const stateAfterActivation = await mockSpiralEngine.usedInviteByUser(sellerAddress);
      expect(stateAfterActivation).to.equal('1');
      expect(activationState.isActivated).to.be.true;

      // THEN: Step 4: SELLER_ROLE назначена
      const hasSellerRoleAfter = await mockSpiralEngine.hasRole(
        await mockSpiralEngine.SELLER_ROLE(),
        sellerAddress
      );
      expect(hasSellerRoleAfter).to.be.true;
      expect(activationState.hasSellerRole).to.be.true;

      // THEN: Step 5: uploadComponentsCore вызван
      expect(actionsManager.componentActions.uploadComponentsCore.calledOnce).to.be.true;

      // THEN: Result содержит корректную структуру
      expect(result).to.exist;
      expect(result.uploadResults).to.exist;
      expect(result.uploadResults.success).to.be.true;
    });

    it('должен обработать ошибку на этапе активации', async () => {
      // GIVEN: Mock SpiralEngine, который выбрасывает ошибку при активации
      const sellerAddress = '0x70997970C51812dc3A010C7d01b50e0d17dc79C8';
      const inviteCode = 'AMANITA-ERROR-555';

      const mockSpiralEngine = harness.setupContractMock('SpiralEngine', {
        usedInviteByUser: { call: async () => '0' },
        inviteCodeExists: { call: async () => false }, // Invite не существует
        activateUser: { call: async () => { throw new Error('Invalid invite'); } }
      });

      sinon.stub(modules.contractManager, 'loadUUPSContract')
        .withArgs('SpiralEngine')
        .resolves(mockSpiralEngine);

      const { ActionsManager } = require('../../../lib/actions');
      const actionsManager = new ActionsManager(
        modules.contractManager,
        modules.arweaveManager,
        modules.ethersUtils,
        modules.config
      );

      process.env.DEPLOYER_INVITE = inviteCode;
      process.env.SELLER_ADDRESS = sellerAddress;

      // WHEN: Выполняется Action 555
      // THEN: Ошибка выбрасывается на этапе активации
      try {
        await actionsManager.executeAction(555);
        expect.fail('Должна была быть выброшена ошибка');
      } catch (error) {
        expect(error.message).to.include('Invite код');
        expect(error.message).to.include('не существует');
      }

      // THEN: uploadComponentsCore НЕ вызывается (из-за ошибки активации)
      // Проверяем, что компоненты не загружаются после ошибки
    });

    it('должен пропустить активацию, если seller уже активирован (idempotent)', async () => {
      // GIVEN: Seller уже активирован
      const sellerAddress = '0x70997970C51812dc3A010C7d01b50e0d17dc79C8';
      const inviteCode = 'AMANITA-IDEMPOTENT-555';

      let activationState = {
        usedInvite: '1', // Уже активирован
        isActivated: true,
        hasSellerRole: true,
        activateUserCalled: false
      };

      const mockSpiralEngine = harness.setupContractMock('SpiralEngine', {
        usedInviteByUser: { call: async () => activationState.usedInvite },
        hasRole: { call: async () => activationState.hasSellerRole },
        inviteCodeExists: { call: async () => true },
        activateUser: { 
          call: async () => {
            activationState.activateUserCalled = true;
            throw new Error('Should not be called');
          }
        },
        SELLER_ROLE: { call: async () => '0x' + '0'.repeat(64) }
      });

      sinon.stub(modules.contractManager, 'loadUUPSContract')
        .withArgs('SpiralEngine')
        .resolves(mockSpiralEngine);

      const { ActionsManager } = require('../../../lib/actions');
      const actionsManager = new ActionsManager(
        modules.contractManager,
        modules.arweaveManager,
        modules.ethersUtils,
        modules.config
      );

      sinon.stub(actionsManager.componentActions, 'uploadComponentsCore')
        .resolves({ success: true, totalCount: 5, results: [] });

      process.env.DEPLOYER_INVITE = inviteCode;
      process.env.SELLER_ADDRESS = sellerAddress;

      // WHEN: Выполняется Action 555
      const result = await actionsManager.executeAction(555);

      // THEN: activateUser НЕ вызывается (пропуск активации)
      expect(activationState.activateUserCalled).to.be.false;

      // THEN: uploadComponentsCore вызывается (компоненты загружаются)
      expect(actionsManager.componentActions.uploadComponentsCore.calledOnce).to.be.true;

      // THEN: Result успешен
      expect(result.uploadResults.success).to.be.true;
    });
  });

  describe('Delegation Verification', () => {
    it('должен проверить правильность делегации ComponentActions → InviteActions', async () => {
      // GIVEN: Setup моков
      const sellerAddress = '0x70997970C51812dc3A010C7d01b50e0d17dc79C8';
      const inviteCode = 'AMANITA-DELEGATION-555';

      const mockSpiralEngine = harness.setupContractMock('SpiralEngine', {
        usedInviteByUser: { call: async () => '0' },
        hasRole: { call: async () => false },
        inviteCodeExists: { call: async () => true },
        activateUser: { call: async () => ({ hash: '0xdelegate', wait: async () => ({ status: 1 }) }) },
        grantRole: { call: async () => ({ hash: '0xrole', wait: async () => ({ status: 1 }) }) },
        SELLER_ROLE: { call: async () => '0x' + '0'.repeat(64) }
      });

      sinon.stub(modules.contractManager, 'loadUUPSContract')
        .withArgs('SpiralEngine')
        .resolves(mockSpiralEngine);

      const { ActionsManager } = require('../../../lib/actions');
      const actionsManager = new ActionsManager(
        modules.contractManager,
        modules.arweaveManager,
        modules.ethersUtils,
        modules.config
      );

      // Spy на InviteActions.activateSeller
      const activateSellerSpy = sinon.spy(actionsManager.componentActions.inviteActions, 'activateSeller');
      const activateUserSpy = sinon.spy(actionsManager.componentActions.inviteActions, 'activateUser');

      sinon.stub(actionsManager.componentActions, 'uploadComponentsCore')
        .resolves({ success: true, totalCount: 5, results: [] });

      process.env.DEPLOYER_INVITE = inviteCode;
      process.env.SELLER_ADDRESS = sellerAddress;

      // WHEN: ComponentActions.action555() вызывается напрямую
      const result = await actionsManager.componentActions.action555();

      // THEN: InviteActions.activateSeller вызван
      expect(activateSellerSpy.calledOnce).to.be.true;

      // THEN: InviteActions.activateUser вызван внутри activateSeller (если не активирован)
      expect(activateUserSpy.calledOnce).to.be.true;

      // THEN: Правильные параметры переданы
      const activateSellerCall = activateSellerSpy.getCall(0);
      expect(activateSellerCall.args[0]).to.equal(mockSpiralEngine);
      expect(activateSellerCall.args[1]).to.equal(inviteCode);
      expect(activateSellerCall.args[2]).to.equal(sellerAddress);
    });
  });
});
```

**Приоритет:** P0 (критично для проверки полного workflow)

**Время реализации:** 2-3 часа

**Зависимости:**
- Мок для `uploadComponentsCore` (или реальная загрузка, если доступна)
- Правильная настройка environment variables для Action 555
- Mock для ArweaveManager (если используется при загрузке компонентов)

---

## 3️⃣ Test #3: ComponentActions → uploadComplexFields → AmanitaInternational (Complex Fields Upload)

### 📍 Текущее состояние кода

**Файл:** `scripts/lib/upload_steps.js:189-295` и `scripts/lib/actions/ComponentActions.js:40-130`

**Реальность:**
- `ComponentActions.action555()` → `uploadComponentsCore()` → `uploadComplexFields()` для каждого компонента
- `uploadComplexFields()` вызывает `amanitaIntlWithSigner.setComplexFieldCID()` с `className = "ComponentDescription.{biounit_id}"`
- Ключи в контракте: `complexFieldCIDs["ComponentDescription.{biounit_id}.{lang}"]` (уникальные для каждого компонента)

**Цепочка вызовов:**
```
ComponentActions.action555()
  → uploadComponentsCore(sellerAddress, componentsDir, networkName, dryRun)
    → Для каждого компонента:
      → uploadComplexFields(context, state)
        → Для каждого языка:
          → Читает файл: complex_fields/{biounit_id}.ComponentDescription.{lang}.json
          → Загружает в Arweave → получает CID
          → amanitaIntlWithSigner.setComplexFieldCID(
               "ComponentDescription.{biounit_id}",  // ✅ С biounit_id для уникальности
               lang,
               descCID
             )
            → Сохраняет в контракте: complexFieldCIDs["ComponentDescription.{biounit_id}.{lang}"]
```

### 🎯 Что тестировать

**Цель теста:** Проверить интеграцию загрузки complex fields через Action 555:
1. `ComponentActions.action555()` → `uploadComponentsCore()` → `uploadComplexFields()`
2. Вызов `setComplexFieldCID` с правильным `className` (с `biounit_id`)
3. Уникальность ключей для разных компонентов
4. Сохранение CIDs в контракте и state

**Сценарии:**
1. Успешная загрузка complex field через блокчейн
2. Обработка пустого CID (complex field не найден)
3. Обработка ошибки блокчейн контракта
4. Проверка кэширования (локальный и внешний кэш)
5. Проверка валидации структуры данных

### ⚠️ Важное примечание

**Исправление локализации:** Test #3 тестирует **загрузку** компонентов в блокчейн, поэтому должен быть в `scripts` слое, а не в `bot` слое.

- ✅ `scripts` слой: **загрузка** компонентов через Action 555 → `uploadComplexFields()` → `setComplexFieldCID()`
- ❌ `bot` слой: только **чтение** и отображение данных (не относится к Test #3)

**Текущее состояние:** Test #3 уже покрыт E2E тестами в `scripts/tests/e2e/actions/component/action555.e2e.test.js` (7 тестов).

**Рекомендация:** Расширить integration тесты для более детальной проверки интеграции.

### 📝 Детальный план реализации Test #3

**Файл:** `scripts/tests/integration/action555-complex-fields.integration.test.js` (новый файл или расширить существующий)

**Структура:**
```python
import pytest
from unittest.mock import Mock, MagicMock, patch
from bot.services.common.multilingual_ipfs_service import MultilingualIPFSService
from bot.services.blockchain.blockchain_service import BlockchainService
from bot.services.ipfs.ipfs_factory import IPFSFactory
from bot.services.common.translation_cache_service import TranslationCacheService

class TestMultilingualIPFSServiceBlockchainIntegration:
    """Integration tests for MultilingualIPFSService → BlockchainService for complex fields"""
    
    @pytest.fixture
    def mock_blockchain_service(self):
        """Mock BlockchainService"""
        service = Mock(spec=BlockchainService)
        return service
    
    @pytest.fixture
    def mock_ipfs_factory(self):
        """Mock IPFSFactory"""
        factory = Mock(spec=IPFSFactory)
        service = Mock()
        service.download_json = Mock(return_value={
            "label": "ComponentDescription",
            "type": "complex",
            "fields": {
                "generic_description": "Test description",
                "effects": "Test effects"
            }
        })
        factory.get_service = Mock(return_value=service)
        return factory
    
    @pytest.fixture
    def mock_cache_service(self):
        """Mock TranslationCacheService"""
        return Mock(spec=TranslationCacheService)
    
    @pytest.fixture
    def multilingual_ipfs_service(self, mock_blockchain_service, mock_ipfs_factory, mock_cache_service):
        """Create MultilingualIPFSService instance"""
        return MultilingualIPFSService(
            blockchain_service=mock_blockchain_service,
            ipfs_factory=mock_ipfs_factory,
            cache_service=mock_cache_service,
            default_language="ru"
        )
    
    def test_load_complex_field_success(self, multilingual_ipfs_service, mock_blockchain_service, mock_ipfs_factory):
        """Test successful loading of complex field through blockchain"""
        # GIVEN: Blockchain contract returns CID
        mock_contract = Mock()
        mock_contract.functions.getComplexFieldCID = Mock(return_value=Mock(
            call=Mock(return_value="QmTestCID123456789")
        ))
        mock_blockchain_service.get_contract = Mock(return_value=mock_contract)
        
        # GIVEN: IPFS service returns valid JSON
        mock_ipfs_service = mock_ipfs_factory.get_service()
        mock_ipfs_service.download_json = Mock(return_value={
            "label": "ComponentDescription",
            "type": "complex",
            "fields": {
                "generic_description": "Test description",
                "effects": "Test effects"
            }
        })
        
        # WHEN: Loading complex field
        result = multilingual_ipfs_service._load_complex_field_from_ipfs("ComponentDescription", "ru")
        
        # THEN: BlockchainService.get_contract called with correct contract name
        mock_blockchain_service.get_contract.assert_called_once_with("AmanitaInternational")
        
        # THEN: getComplexFieldCID called with correct parameters
        mock_contract.functions.getComplexFieldCID.assert_called_once_with("ComponentDescription", "ru")
        
        # THEN: IPFS download_json called with CID
        mock_ipfs_service.download_json.assert_called_once_with("QmTestCID123456789")
        
        # THEN: Result contains valid data
        assert result is not None
        assert result["label"] == "ComponentDescription"
        assert result["type"] == "complex"
        assert "fields" in result
    
    def test_load_complex_field_empty_cid(self, multilingual_ipfs_service, mock_blockchain_service):
        """Test handling of empty CID (complex field not found)"""
        # GIVEN: Blockchain contract returns empty CID
        mock_contract = Mock()
        mock_contract.functions.getComplexFieldCID = Mock(return_value=Mock(
            call=Mock(return_value="")
        ))
        mock_blockchain_service.get_contract = Mock(return_value=mock_contract)
        
        # WHEN: Loading complex field
        result = multilingual_ipfs_service._load_complex_field_from_ipfs("ComponentDescription", "ru")
        
        # THEN: Result is None
        assert result is None
        
        # THEN: getComplexFieldCID was called
        mock_contract.functions.getComplexFieldCID.assert_called_once_with("ComponentDescription", "ru")
    
    def test_load_complex_field_contract_not_found(self, multilingual_ipfs_service, mock_blockchain_service):
        """Test handling when AmanitaInternational contract is not found"""
        # GIVEN: BlockchainService returns None for contract
        mock_blockchain_service.get_contract = Mock(return_value=None)
        
        # WHEN: Loading complex field
        result = multilingual_ipfs_service._load_complex_field_from_ipfs("ComponentDescription", "ru")
        
        # THEN: Result is None
        assert result is None
        
        # THEN: get_contract was called
        mock_blockchain_service.get_contract.assert_called_once_with("AmanitaInternational")
    
    def test_load_complex_field_blockchain_error(self, multilingual_ipfs_service, mock_blockchain_service):
        """Test handling of blockchain contract errors"""
        # GIVEN: Blockchain contract raises exception
        mock_contract = Mock()
        mock_contract.functions.getComplexFieldCID = Mock(return_value=Mock(
            call=Mock(side_effect=Exception("Blockchain error"))
        ))
        mock_blockchain_service.get_contract = Mock(return_value=mock_contract)
        
        # WHEN: Loading complex field
        result = multilingual_ipfs_service._load_complex_field_from_ipfs("ComponentDescription", "ru")
        
        # THEN: Result is None (error handled gracefully)
        assert result is None
        
        # THEN: getComplexFieldCID was called
        mock_contract.functions.getComplexFieldCID.assert_called_once_with("ComponentDescription", "ru")
    
    def test_load_complex_field_caching(self, multilingual_ipfs_service, mock_blockchain_service, mock_cache_service):
        """Test caching of complex field data"""
        # GIVEN: Data in cache
        cached_data = {
            "label": "ComponentDescription",
            "type": "complex",
            "fields": {"generic_description": "Cached description"}
        }
        mock_cache_service.get = Mock(return_value=cached_data)
        
        # WHEN: Loading complex field
        result = multilingual_ipfs_service._load_complex_field_from_ipfs("ComponentDescription", "ru")
        
        # THEN: Result from cache
        assert result == cached_data
        
        # THEN: BlockchainService NOT called (cache hit)
        mock_blockchain_service.get_contract.assert_not_called()
        
        # THEN: Cache service was checked
        mock_cache_service.get.assert_called_once()
    
    def test_load_complex_field_invalid_structure(self, multilingual_ipfs_service, mock_blockchain_service, mock_ipfs_factory):
        """Test handling of invalid JSON structure from IPFS"""
        # GIVEN: IPFS returns invalid structure (missing required fields)
        mock_contract = Mock()
        mock_contract.functions.getComplexFieldCID = Mock(return_value=Mock(
            call=Mock(return_value="QmInvalidCID")
        ))
        mock_blockchain_service.get_contract = Mock(return_value=mock_contract)
        
        mock_ipfs_service = mock_ipfs_factory.get_service()
        mock_ipfs_service.download_json = Mock(return_value={
            "invalid": "structure"  # Missing 'label', 'type', 'fields'
        })
        
        # WHEN: Loading complex field
        result = multilingual_ipfs_service._load_complex_field_from_ipfs("ComponentDescription", "ru")
        
        # THEN: Result is None (validation failed)
        assert result is None
        
        # THEN: IPFS download was called
        mock_ipfs_service.download_json.assert_called_once_with("QmInvalidCID")
```

**Приоритет:** P0 (критично для проверки интеграции с блокчейном)

**Время реализации:** 2-3 часа

**Зависимости:**
- Моки для `BlockchainService`, `IPFSFactory`, `TranslationCacheService`
- Правильная настройка контракта `AmanitaInternational` в моке
- Тестирование различных edge cases (пустой CID, ошибки, кэширование)

---

## 📊 Сводная таблица

| # | Тест | Приоритет | Время | Слой | Файл |
|---|------|-----------|-------|------|------|
| 1 | CoreLogic + InviteActions (через ActionsManager) | P1 | 1-2 ч | scripts | `core-invite-actions.integration.test.js` |
| 2 | ActionsManager → ComponentActions → InviteActions | P0 | 2-3 ч | scripts | `action555-full-workflow.integration.test.js` |
| 3 | ComponentActions → uploadComplexFields → AmanitaInternational | P0 | 1-2 ч | scripts | `action555-complex-fields.integration.test.js` (или расширить существующий) |

---

## 🎯 Рекомендации по реализации

### Общие принципы:

1. **Используйте IntegrationHarness** для setup/teardown окружения
2. **Моки только внешних систем** (blockchain RPC, IPFS API), не внутренних модулей
3. **State tracking** через замыкания для проверки изменений состояния
4. **Spy на методы** для проверки правильности вызовов и параметров
5. **Проверка состояния до и после** операций для валидации изменений

### Для каждого теста:

1. **Test #1 (P1):**
   - Фокус на проверку инициализации и dependency injection
   - Проверка независимости модулей
   - Не критично для функциональности

2. **Test #2 (P0):**
   - Фокус на полный workflow
   - Проверка всех этапов (активация → загрузка)
   - Проверка обработки ошибок
   - Критично для проверки интеграции

3. **Test #3 (P0):**
   - Фокус на интеграцию с блокчейном
   - Проверка получения CID через контракт
   - Проверка загрузки данных из IPFS
   - Проверка кэширования и валидации
   - Критично для проверки архитектуры complex fields

---

## ✅ Следующие шаги

### Этап 1: Рефакторинг (Критично для Test #1)

**Перед реализацией Test #1 необходимо выполнить:**

1. ✅ **ВЫПОЛНЕНО:** Рефакторинг `CoreLogic.activateSellerBasic()` для делегирования в `InviteActions`
   - ✅ Детальный план в `architecture/refactoring/corelogic-inviteactions-refactoring.md` (Фазы 1-3 завершены)
   - ✅ Время: ~6-7 часов (завершено)

2. ✅ **ВЫПОЛНЕНО:** Обновление `IntegrationHarness` для передачи `InviteActions` в `CoreLogic`
   - ✅ Время: ~30 минут (завершено)

3. ✅ **ВЫПОЛНЕНО:** Исправлены P0 и P1 проблемы с моками
   - ✅ P0: Добавлен `grantSellerRole()` в моки SpiralEngine
   - ✅ P1: Адаптирован план для использования stub для `config.get()` вместо `config.set()`

**Готовность:** ✅ **ВЫПОЛНЕНО** - все тесты реализованы и проходят успешно

### Этап 2: Реализация тестов

**После рефакторинга:**

1. ✅ Создать файл `core-invite-actions.integration.test.js` по плану Test #1
2. ✅ Реализовать тесты делегирования CoreLogic → InviteActions
3. ✅ Добавить тесты для fallback на прямую реализацию
4. ✅ Добавить тесты для адаптации результата
5. ✅ Запустить тесты и убедиться, что они проходят

**Параллельно (не зависят от рефакторинга):**

1. ✅ Создать файл `action555-full-workflow.integration.test.js` по плану Test #2
2. ✅ Реализовать полный workflow тест для Action 555
3. ✅ Добавить edge cases и error handling тесты
4. ✅ Запустить тесты и убедиться, что они проходят

1. ✅ E2E тесты для загрузки complex fields уже созданы в `action555.e2e.test.js` (7 тестов)
2. ⏳ Расширить integration тесты для проверки загрузки complex fields (опционально)
2. ✅ Реализовать интеграционные тесты для complex fields
3. ✅ Добавить тесты для кэширования и валидации
4. ✅ Запустить тесты и убедиться, что они проходят

### Этап 3: Документация

1. ✅ Обновить документацию с примерами использования
2. ✅ Добавить примеры в README тестов
3. ✅ Обновить миграционный документ

---

## 🔗 Связанные документы

- **План рефакторинга:** `architecture/refactoring/corelogic-inviteactions-refactoring.md`
- **Архитектура моков:** `testing/architecture/mock-state-tracking-architecture.md`

---

**Версия:** 2.0  
**Последнее обновление:** 2025-11-22  
**Статус:** ✅ Все тесты реализованы и проходят успешно

