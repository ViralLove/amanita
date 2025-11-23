/**
 * Integration Test: CoreLogic → InviteActions (Delegation)
 * 
 * Phase 3: Flow Testing - Multi-step integration scenario
 * Validates module boundary handshake between CoreLogic and InviteActions
 * 
 * Goal: Verify that CoreLogic correctly delegates seller activation to InviteActions
 * after refactoring, maintaining backward compatibility through result adaptation.
 * 
 * Method: @integration-test-build.core.mdc
 * - Real modules: CoreLogic, InviteActions (via IntegrationHarness)
 * - Minimal mocks: SpiralEngine contract (external blockchain API)
 * - State tracking: Activation state via closures
 */

const { expect } = require('chai');
const sinon = require('sinon');
const { ethers } = require('hardhat');
const { IntegrationHarness } = require('../helpers');

describe('Integration: CoreLogic → InviteActions (Delegation)', () => {
  let harness, modules;

  before(async function() {
    this.timeout(10000);
    harness = new IntegrationHarness();
    modules = await harness.setupIntegrationEnvironment();
    // ✅ IntegrationHarness передает InviteActions в CoreLogic после рефакторинга
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
      
      // ✅ State tracking через замыкание для проверки изменения состояния
      let activationState = {
        usedInvite: '0',
        isActivated: false,
        hasSellerRole: false,
        SELLER_ROLE: null // Будет установлено при первом вызове
      };

      // ✅ Setup mock SpiralEngine с state tracking (external API only)
      // ✅ FIX: Используем usedInvite напрямую для проверки состояния
      // checkActivationStatus проверяет: usedInvite > 0, где usedInvite = await spiralEngine.usedInviteByUser(address)
      const usedInviteByUserFn = async (address) => {
        // ✅ FIX: Возвращаем usedInvite (token ID) из состояния
        // '1' означает активирован, '0' - не активирован
        // Проверка usedInvite > 0 работает для строк ('1' > 0 = true)
        return activationState.usedInvite;
      };
      
      const hasRoleFn = async (role, address) => {
        // Получаем SELLER_ROLE при первом вызове
        if (!activationState.SELLER_ROLE) {
          activationState.SELLER_ROLE = ethers.keccak256(ethers.toUtf8Bytes('SELLER_ROLE'));
        }
        // Проверяем, является ли это SELLER_ROLE и назначена ли роль
        const sellerRole = activationState.SELLER_ROLE;
        if (role === sellerRole || (role && sellerRole && role.toLowerCase() === sellerRole.toLowerCase())) {
          return activationState.hasSellerRole;
        }
        return false;
      };

      const inviteCodeExistsFn = async (code) => code === inviteCode;
      
      // ✅ Phase 2: Упрощённая версия - просто обновляем состояние
      // setupContractMock теперь вызывает эту функцию автоматически для write методов
      // и обрабатывает wait() сам, поэтому не нужно возвращать сложный объект
      const activateUserFn = async (code, user, newInvites, expiry) => {
        // ✅ Обновляем состояние активации СИНХРОННО
        // setupContractMock вызовет эту функцию перед возвратом транзакции,
        // поэтому состояние обновлено ДО возврата (как в реальном блокчейне)
        activationState.usedInvite = '1';
        activationState.isActivated = true;
        
        // ✅ Возвращаем простое значение (setupContractMock обработает wait() автоматически)
        // Можно вернуть любое значение - setupContractMock заменит на транзакцию
        return { hash: '0xdelegate' };
      };

      // ✅ P0 FIX: grantSellerRole с обновлением состояния
      const grantSellerRoleFn = async (userAddress) => {
        // ✅ FIX: Проверяем, что пользователь активирован перед назначением роли
        // Это соответствует реальной логике AccessControlActions.grantSellerRole()
        if (!activationState.isActivated) {
          throw new Error('AccessControl: Не могу назначить SELLER_ROLE - пользователь не активирован');
        }
        activationState.hasSellerRole = true;
        return { hash: '0xgrantSellerRole', wait: async () => ({ status: 1 }) };
      };

      const mockSpiralEngine = harness.setupContractMock('SpiralEngine', {
        usedInviteByUser: { call: usedInviteByUserFn },
        hasRole: { call: hasRoleFn },
        inviteCodeExists: { call: inviteCodeExistsFn },
        activateUser: { call: activateUserFn, encodeABI: '0xactivate' },
        grantSellerRole: { call: grantSellerRoleFn, encodeABI: '0xgrantSellerRole' },
        SELLER_ROLE: {
          call: async () => {
            if (!activationState.SELLER_ROLE) {
              activationState.SELLER_ROLE = ethers.keccak256(ethers.toUtf8Bytes('SELLER_ROLE'));
            }
            return activationState.SELLER_ROLE;
          }
        }
      });

      // Stub ContractManager.getContract для возврата мока SpiralEngine
      const getContractStub = sinon.stub(modules.contractManager, 'getContract')
        .withArgs('SpiralEngine')
        .resolves(mockSpiralEngine);

      // ✅ Spy на InviteActions.activateSeller для проверки делегирования
      const activateSellerSpy = sinon.spy(modules.inviteActions, 'activateSeller');

      // ✅ P1 FIX: Используем stub для config.get() вместо config.set()
      const originalGet = modules.config.get.bind(modules.config);
      sinon.stub(modules.config, 'get').callsFake((key) => {
        if (key === 'deployer.invite') return inviteCode;
        if (key === 'invite.deployer') return null;
        if (key === 'seller.address') return sellerAddress;
        // Fallback на оригинальный get для других ключей
        return originalGet(key);
      });

      // WHEN: CoreLogic.activateSellerBasic() вызывается
      // ✅ После рефакторинга это должно делегировать в InviteActions
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
      const { CoreLogic } = require('../../lib/core');
      const coreLogicWithoutInvite = new CoreLogic(
        modules.contractManager,
        modules.ethersUtils,
        modules.config,
        null  // ✅ InviteActions = null
      );

      const sellerAddress = '0x70997970C51812dc3A010C7d01b50e0d17dc79C8';
      const inviteCodes = modules.ethersUtils.generateNewInviteCodes(12);

      // ✅ State tracking для проверки состояния
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

      // ✅ Setup mock для InviteActions.activateSeller
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
        grantSellerRole: { call: async () => ({ hash: '0xrole', wait: async () => ({ status: 1 }) }) },
        SELLER_ROLE: { call: async () => ethers.keccak256(ethers.toUtf8Bytes('SELLER_ROLE')) }
      });

      sinon.stub(modules.contractManager, 'getContract')
        .withArgs('SpiralEngine')
        .resolves(mockSpiralEngine);

      // ✅ P1 FIX: Используем stub для config.get()
      const originalGet = modules.config.get.bind(modules.config);
      sinon.stub(modules.config, 'get').callsFake((key) => {
        if (key === 'deployer.invite') return inviteCode;
        if (key === 'invite.deployer') return null;
        if (key === 'seller.address') return sellerAddress;
        return originalGet(key);
      });

      // WHEN: CoreLogic.activateSellerBasic() вызывается
      const result = await modules.coreLogic.activateSellerBasic(sellerAddress);

      // THEN: Результат адаптирован под старую структуру
      expect(result).to.have.property('success', true);
      expect(result).to.have.property('sellerAddress', sellerAddress);
      expect(result).to.have.property('transactionHash', '0xadaptation-test'); // Из activationResult.txHash
      expect(result).to.have.property('inviteCodes').that.deep.equals(newInvites); // Из newInvites

      // THEN: Старая структура сохранена (новые поля не добавлены)
      expect(result).to.not.have.property('wasActivated');
      expect(result).to.not.have.property('wasRoleGranted');
      expect(result).to.not.have.property('activationResult');
    });
  });

  describe('Parameter Mapping', () => {
    it('должен правильно определить inviteCode из параметров или конфига', async () => {
      // GIVEN: Различные сценарии определения inviteCode
      const sellerAddress = '0x70997970C51812dc3A010C7d01b50e0d17dc79C8';

      // ✅ Сценарий 1: inviteCode из конфига
      const inviteCodeFromConfig = 'AMANITA-CONFIG-INVITE';
      
      // ✅ FIX: State tracking для проверки изменения состояния
      let activationState = {
        usedInvite: '0',
        isActivated: false,
        hasSellerRole: false,
        SELLER_ROLE: null
      };

      // Setup stub для config.get() для возврата inviteCode из конфига
      const originalGet = modules.config.get.bind(modules.config);
      sinon.stub(modules.config, 'get').callsFake((key) => {
        if (key === 'deployer.invite') return inviteCodeFromConfig;
        if (key === 'invite.deployer') return null;
        if (key === 'seller.address') return sellerAddress;
        return originalGet(key);
      });

      // ✅ FIX: Используем state tracking для моков
      // ✅ FIX: Создаём переменную для текущего invite code (будет изменяться во втором сценарии)
      let currentInviteCode = inviteCodeFromConfig;
      
      const usedInviteByUserFn = async (address) => activationState.usedInvite;
      const activateUserFn = async (code, user, newInvites, expiry) => {
        activationState.usedInvite = '1';
        activationState.isActivated = true;
      };
      const hasRoleFn = async (role, address) => {
        if (!activationState.SELLER_ROLE) {
          activationState.SELLER_ROLE = ethers.keccak256(ethers.toUtf8Bytes('SELLER_ROLE'));
        }
        const sellerRole = activationState.SELLER_ROLE;
        if (role === sellerRole || (role && sellerRole && role.toLowerCase() === sellerRole.toLowerCase())) {
          return activationState.hasSellerRole;
        }
        return false;
      };
      const grantSellerRoleFn = async (userAddress) => {
        if (!activationState.isActivated) {
          throw new Error('AccessControl: Не могу назначить SELLER_ROLE - пользователь не активирован');
        }
        activationState.hasSellerRole = true;
      };
      // ✅ FIX: Используем функцию, которая проверяет текущий invite code
      const inviteCodeExistsFn = async (code) => code === currentInviteCode;

      const mockSpiralEngine = harness.setupContractMock('SpiralEngine', {
        usedInviteByUser: { call: usedInviteByUserFn },
        hasRole: { call: hasRoleFn },
        inviteCodeExists: { call: inviteCodeExistsFn },
        activateUser: { call: activateUserFn, encodeABI: '0xactivate' },
        grantSellerRole: { call: grantSellerRoleFn, encodeABI: '0xgrantSellerRole' },
        SELLER_ROLE: {
          call: async () => {
            if (!activationState.SELLER_ROLE) {
              activationState.SELLER_ROLE = ethers.keccak256(ethers.toUtf8Bytes('SELLER_ROLE'));
            }
            return activationState.SELLER_ROLE;
          }
        }
      });

      sinon.stub(modules.contractManager, 'getContract')
        .withArgs('SpiralEngine')
        .resolves(mockSpiralEngine);

      const activateSellerSpy = sinon.spy(modules.inviteActions, 'activateSeller');

      // WHEN: CoreLogic.activateSellerBasic() вызывается без inviteCodes
      await modules.coreLogic.activateSellerBasic(sellerAddress);

      // THEN: InviteActions.activateSeller вызван с inviteCode из конфига
      expect(activateSellerSpy.calledOnce).to.be.true;
      const call1 = activateSellerSpy.getCall(0);
      expect(call1.args[1]).to.equal(inviteCodeFromConfig);

      // ✅ Сценарий 2: inviteCode из первого элемента inviteCodes массива (deprecated)
      activateSellerSpy.resetHistory();
      const inviteCodesArray = ['AMANITA-FIRST-INVITE', 'INVITE-2', 'INVITE-3'];
      
      // ✅ FIX: Сбрасываем состояние для второго сценария
      activationState.usedInvite = '0';
      activationState.isActivated = false;
      activationState.hasSellerRole = false;
      
      // ✅ FIX: Обновляем текущий invite code для проверки во втором сценарии
      currentInviteCode = 'AMANITA-FIRST-INVITE';

      await modules.coreLogic.activateSellerBasic(sellerAddress, inviteCodesArray);

      // THEN: InviteActions.activateSeller вызван с первым inviteCode из массива
      expect(activateSellerSpy.calledOnce).to.be.true;
      const call2 = activateSellerSpy.getCall(0);
      expect(call2.args[1]).to.equal('AMANITA-FIRST-INVITE');
    });
  });
});

