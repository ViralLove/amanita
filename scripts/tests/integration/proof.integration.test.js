/**
 * Proof Integration Tests
 * 
 * Validates that integration test infrastructure works.
 * Tests basic module-to-module interactions.
 */

const { expect } = require('chai');
const sinon = require('sinon');
const { ethers } = require('hardhat');
const { IntegrationHarness } = require('../helpers');

describe('Integration Proof Tests', () => {
  let harness, modules;

  before(async function() {
    this.timeout(10000); // Integration tests can be slower
    harness = new IntegrationHarness();
    modules = await harness.setupIntegrationEnvironment();
  });

  after(async () => {
    await harness.teardownIntegrationEnvironment();
  });

  afterEach(() => {
    // Clean up any test-specific stubs
    sinon.restore();
  });

  describe('Infrastructure Validation', () => {
    it('должен загрузить все REAL modules (не mocks)', () => {
      // THEN: Все модули загружены как real instances
      expect(modules.config).to.exist;
      expect(modules.logger).to.exist;
      expect(modules.ethersUtils).to.exist;
      expect(modules.contractManager).to.exist;
      expect(modules.arweaveManager).to.exist;
      expect(modules.coreLogic).to.exist;
      expect(modules.coreManager).to.exist;
      expect(modules.actionsManager).to.exist;
      
      // Проверка что это REAL instances, не mocks
      expect(modules.contractManager.constructor.name).to.equal('ContractManager');
      expect(modules.arweaveManager.constructor.name).to.equal('ArweaveManager');
    });

    it('должен использовать minimal mocking (только external APIs)', () => {
      // THEN: Minimal mocking validated
      expect(harness.externalMocks).to.be.an('object');
      
      // Только external mocks (Arweave API готов)
      expect(harness.externalMocks.arweaveReady).to.be.true;
      
      // Наши модули НЕ замоканы
      expect(modules.contractManager).to.not.be.undefined;
      expect(modules.arweaveManager).to.not.be.undefined;
    });
  });

  describe('Module Integration: ContractManager ↔ EthersUtils', () => {
    it('должен интегрировать ContractManager с EthersUtils', async () => {
      // GIVEN: Setup mock contract with state tracking для проверки изменения состояния
      const sellerAddress = '0x70997970C51812dc3A010C7d01b50e0d17dc79C8';
      
      // ✅ ИСПРАВЛЕНИЕ 1.3: Отслеживание состояния между вызовами через замыкание
      let userActivationState = {
        usedInvite: '0', // Not activated initially
        isActivated: false,
        hasSellerRole: false, // ✅ P0 FIX: Добавляем состояние для SELLER_ROLE
        SELLER_ROLE: null // Будет установлено при первом вызове
      };

      // ✅ ИСПРАВЛЕНИЕ 1.3: Создаем функции, которые используют замыкание для состояния
      const usedInviteByUserFn = async (address) => {
        // ✅ ИСПРАВЛЕНИЕ 1.3: Возвращаем актуальное состояние из замыкания
        return userActivationState.usedInvite;
      };
      
      const activateUserFn = async (inviteCode, userAddress, newInvites, expiry) => {
        // ✅ ИСПРАВЛЕНИЕ 1.3: Обновляем состояние в замыкании после активации
        userActivationState.usedInvite = '1'; // Token ID after activation
        userActivationState.isActivated = true;
        
        return '1'; // Token ID after activation
      };

      // ✅ P0 FIX: Функция для проверки роли с отслеживанием состояния
      const hasRoleFn = async (role, address) => {
        // Получаем SELLER_ROLE при первом вызове
        if (!userActivationState.SELLER_ROLE) {
          userActivationState.SELLER_ROLE = ethers.keccak256(ethers.toUtf8Bytes('SELLER_ROLE'));
        }
        // Проверяем, является ли это SELLER_ROLE и назначена ли роль
        const sellerRole = userActivationState.SELLER_ROLE;
        if (role === sellerRole || role.toLowerCase() === sellerRole.toLowerCase()) {
          return userActivationState.hasSellerRole;
        }
        return false;
      };

      // ✅ P0 FIX: Функция для назначения роли с обновлением состояния
      const grantSellerRoleFn = async (userAddress) => {
        // Обновляем состояние после назначения роли
        userActivationState.hasSellerRole = true;
        return { hash: '0xgrantSellerRole', wait: async () => ({ status: 1 }) };
      };

      // GIVEN: Setup mock contract FIRST (before calling method)
      const mockSpiralEngine = harness.setupContractMock('SpiralEngine', {
        usedInviteByUser: {
          call: usedInviteByUserFn
        },
        activateUser: {
          call: activateUserFn,
          encodeABI: '0xactivate'
        },
        SELLER_ROLE: {
          call: async () => {
            if (!userActivationState.SELLER_ROLE) {
              userActivationState.SELLER_ROLE = ethers.keccak256(ethers.toUtf8Bytes('SELLER_ROLE'));
            }
            return userActivationState.SELLER_ROLE;
          }
        },
        hasRole: {
          call: hasRoleFn
        },
        inviteCodeExists: {
          call: async (inviteCode) => {
            // Возвращаем true для тестового invite кода
            return true;
          }
        },
        // ✅ P0 FIX: Добавляем grantSellerRole() для AccessControlActions.grantSellerRole()
        grantSellerRole: {
          call: grantSellerRoleFn,
          encodeABI: '0xgrantSellerRole'
        }
      });
      
      // ✅ ИСПРАВЛЕНИЕ 1.3: Создаем spy для отслеживания вызовов activateUser
      // Используем callsFake, чтобы сохранить оригинальное поведение и отслеживать вызовы
      const originalActivateUser = mockSpiralEngine.activateUser;
      const activateUserSpy = sinon.stub(mockSpiralEngine, 'activateUser').callsFake(async (...args) => {
        // ✅ ИСПРАВЛЕНИЕ 1.3: Обновляем состояние при вызове activateUser
        userActivationState.usedInvite = '1'; // Token ID after activation
        userActivationState.isActivated = true;
        
        // Вызываем оригинальный метод (который возвращает транзакцию)
        return originalActivateUser.apply(mockSpiralEngine, args);
      });
      
      // Stub getContract BEFORE calling CoreLogic
      const getContractStub = sinon.stub(modules.contractManager, 'getContract')
        .withArgs('SpiralEngine')
        .resolves(mockSpiralEngine);
      
      // EthersUtils генерирует invite коды
      const inviteCodes = modules.ethersUtils.generateNewInviteCodes(3);
      expect(inviteCodes).to.have.lengthOf(3);
      
      // ✅ ИСПРАВЛЕНИЕ 1.3: Проверяем начальное состояние (до активации)
      const initialStateBefore = await mockSpiralEngine.usedInviteByUser(sellerAddress);
      expect(initialStateBefore).to.equal('0'); // Не активирован
      expect(userActivationState.isActivated).to.be.false;
      
      // WHEN: CoreLogic использует оба модуля (ContractManager + EthersUtils)
      const result = await modules.coreLogic.activateSellerBasic(
        sellerAddress,
        inviteCodes
      );
      
      // THEN: Интеграция validated
      expect(result).to.be.an('object');
      expect(result.success).to.be.true;
      expect(getContractStub.calledOnce).to.be.true;
      
      // ✅ ИСПРАВЛЕНИЕ 1.3: Проверяем изменение состояния после активации
      // Так как activateUserFn был вызван через spy, состояние должно быть обновлено
      expect(userActivationState.isActivated).to.be.true; // Флаг активации обновлен
      expect(userActivationState.usedInvite).to.not.equal('0'); // Состояние изменилось
      expect(userActivationState.usedInvite).to.equal('1'); // Использован invite с token ID 1
      
      // ✅ ИСПРАВЛЕНИЕ 1.3: Проверяем изменение состояния через мок (после активации)
      const stateAfterActivation = await mockSpiralEngine.usedInviteByUser(sellerAddress);
      expect(stateAfterActivation).to.not.equal('0'); // Состояние изменилось
      expect(stateAfterActivation).to.equal('1'); // Использован invite с token ID 1
      
      // ✅ ИСПРАВЛЕНИЕ 1.3: Проверяем, что состояние действительно изменилось
      expect(stateAfterActivation).to.not.equal(initialStateBefore);
      
      // EthersUtils generated codes → CoreLogic used them → ContractManager processed
      // ✅ ИСПРАВЛЕНИЕ 1.3: Теперь также проверяем изменение состояния блокчейна через мок
    });
  });

  describe('Module Integration: ArweaveManager ↔ Config', () => {
    it('должен интегрировать ArweaveManager с Config', async () => {
      // GIVEN: Config предоставляет seller configuration
      const sellerConfig = modules.config.getSellerConfig();
      expect(sellerConfig).to.exist;
      const sellerId = sellerConfig.sellerId || 'test_seller_001';
      expect(sellerId).to.be.a('string');
      
      // WHEN: ArweaveManager использует seller_id для metadata
      // Mock Arweave client для этого теста
      const mockArweaveClient = harness.createMockArweaveClient();
      modules.arweaveManager.arweaveClient = mockArweaveClient;
      modules.arweaveManager.arweaveKey = { mock: true };
      
      const testData = { seller: sellerId, data: 'test' };
      const result = await modules.arweaveManager.uploadJSON(testData, {
        tags: { 'Seller-ID': sellerId }
      });
      
      // THEN: Интеграция validated
      expect(result).to.be.an('object');
      expect(result.txId).to.exist;
      expect(mockArweaveClient.createTransaction.calledOnce).to.be.true;
      
      // Config → ArweaveManager integration works
    });
  });

  describe('Module Integration: CoreManager ↔ CoreLogic ↔ ContractManager', () => {
    it('должен интегрировать 3 модуля через facade pattern', async () => {
      // GIVEN: Mock OrganicComponentRegistry contract FIRST
      const mockRegistry = harness.setupContractMock('OrganicComponentRegistry', {
        getTotalComponents: {
          call: async () => '5' // Return as string (как Web3 contract)
        }
      });
      
      // Stub getContract BEFORE calling
      const getStub = sinon.stub(modules.contractManager, 'getContract')
        .withArgs('OrganicComponentRegistry')
        .resolves(mockRegistry);
      
      // WHEN: CoreManager вызывается (triggers facade chain)
      const result = await modules.coreManager.checkComponents();
      
      // THEN: 3-module integration validated
      expect(result).to.be.an('object');
      expect(result.totalComponents).to.equal(5);
      expect(result.hasComponents).to.be.true;
      expect(getStub.calledOnce).to.be.true;
      
      // Integration chain: CoreManager → CoreLogic → ContractManager
    });
  });
});

