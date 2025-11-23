/**
 * Unit Tests: CoreLogic
 * 
 * Tests for the shared business logic.
 */

const { expect } = require('chai');
const sinon = require('sinon');
const { ethers } = require('hardhat');
const { MockContractManager, TestHarness } = require('../../helpers');

describe('CoreLogic', () => {
  let CoreLogic;
  let coreLogic;
  let mockContractManager;
  let mockProvider;
  let mockEthersUtils;
  let mockConfig;
  let harness;

  before(async () => {
    harness = new TestHarness();
    await harness.setupTestEnvironment();
    
    // Load modules
    CoreLogic = require('../../../lib/core/CoreLogic');
    const EthersUtils = require('../../../lib/utils/EthersUtils');
    
    // Create mock provider
    mockProvider = {
      getBalance: sinon.stub(),
      getNetwork: sinon.stub(),
      getBlockNumber: sinon.stub(),
      getTransactionCount: sinon.stub(),
      estimateGas: sinon.stub(),
      call: sinon.stub(),
      sendTransaction: sinon.stub()
    };
  });

  after(async () => {
    await harness.teardownTestEnvironment();
  });

  beforeEach(() => {
    mockContractManager = new MockContractManager();
    mockConfig = harness.createMockConfig();
    
    // Create mock EthersUtils
    mockEthersUtils = {
      getSigner: sinon.stub().returns({
        connect: sinon.stub().returnsThis(),
        sendTransaction: sinon.stub().resolves({ hash: '0x123', wait: sinon.stub().resolves({ status: 1 }) })
      }),
      generateNewInviteCodes: sinon.stub().returns(Array(12).fill().map((_, i) => `INVITE${i + 1}`))
    };
    
    coreLogic = new CoreLogic(
      mockContractManager,
      mockEthersUtils,
      mockConfig
    );
  });

  describe('Initialization', () => {
    it('должен инициализироваться с dependencies', () => {
      // THEN: CoreLogic инициализирован
      expect(coreLogic).to.be.an('object');
      expect(coreLogic.contractManager).to.equal(mockContractManager);
      expect(coreLogic.ethersUtils).to.equal(mockEthersUtils);
      expect(coreLogic.config).to.equal(mockConfig);
    });
  });

  describe('Seller Management Methods', () => {
    it('должен иметь метод activateSellerBasic', () => {
      // THEN: activateSellerBasic метод существует
      expect(coreLogic.activateSellerBasic).to.be.a('function');
    });

    it('должен иметь метод setupSellerRole', () => {
      // THEN: setupSellerRole метод существует
      expect(coreLogic.setupSellerRole).to.be.a('function');
    });

    it('должен иметь метод validateSellerAccess', () => {
      // THEN: validateSellerAccess метод существует
      expect(coreLogic.validateSellerAccess).to.be.a('function');
    });

    it('должен иметь метод diagnoseSellerState', () => {
      // THEN: diagnoseSellerState метод существует
      expect(coreLogic.diagnoseSellerState).to.be.a('function');
    });
  });

  describe('Component Management Methods', () => {
    it('должен иметь метод checkComponentsLoaded', () => {
      // THEN: checkComponentsLoaded метод существует
      expect(coreLogic.checkComponentsLoaded).to.be.a('function');
    });
  });

  describe('Catalog Management Methods', () => {
    it('должен иметь метод createCatalogWithAction444', () => {
      // THEN: createCatalogWithAction444 метод существует
      expect(coreLogic.createCatalogWithAction444).to.be.a('function');
    });

    it('должен иметь метод loadSellerCatalog', () => {
      // THEN: loadSellerCatalog метод существует
      expect(coreLogic.loadSellerCatalog).to.be.a('function');
    });

    it('должен иметь метод getFullCatalogWithData', () => {
      // THEN: getFullCatalogWithData метод существует
      expect(coreLogic.getFullCatalogWithData).to.be.a('function');
    });
  });

  describe('Invite Management Methods', () => {
    it('должен иметь метод generateInvitesForSeller', () => {
      // THEN: generateInvitesForSeller метод существует
      expect(coreLogic.generateInvitesForSeller).to.be.a('function');
    });
  });

  describe('Method Count', () => {
    it('должен иметь минимум 9 core methods', () => {
      // GIVEN: CoreLogic instance
      const methods = Object.getOwnPropertyNames(Object.getPrototypeOf(coreLogic))
        .filter(name => name !== 'constructor' && typeof coreLogic[name] === 'function');
      
      // THEN: Минимум 9 методов
      expect(methods.length).to.be.at.least(9);
    });
  });

  describe('Seller Activation - Real Tests', () => {
    it('должен активировать seller через SpiralEngine', async () => {
      // GIVEN: Mock SpiralEngine contract
      const mockSpiralEngine = {
        connect: sinon.stub().returns({
          activateUser: sinon.stub().resolves({
            hash: '0xActivated123',
            wait: sinon.stub().resolves({ status: 1 })
          })
        })
      };
      
      sinon.stub(mockContractManager, 'getContract')
        .withArgs('SpiralEngine').returns(mockSpiralEngine);
      
      // WHEN: activateSellerBasic() вызывается
      const result = await coreLogic.activateSellerBasic('0xSellerAddress', ['CODE1', 'CODE2']);
      
      // THEN: Seller активирован
      expect(result).to.be.an('object');
      expect(result.success).to.be.true;
      expect(result.transactionHash).to.equal('0xActivated123');
      expect(result.sellerAddress).to.equal('0xSellerAddress');
    });

    it('должен использовать предоставленные invite коды', async () => {
      // GIVEN: Provided invite codes
      const providedCodes = ['CODE1', 'CODE2', 'CODE3'];
      const mockSpiralEngine = {
        connect: sinon.stub().returns({
          activateUser: sinon.stub().resolves({
            hash: '0xTx',
            wait: sinon.stub().resolves({ status: 1 })
          })
        })
      };
      
      sinon.stub(mockContractManager, 'getContract').returns(mockSpiralEngine);
      
      // WHEN: activateSellerBasic() с codes
      const result = await coreLogic.activateSellerBasic('0xSeller', providedCodes);
      
      // THEN: Provided codes используются
      expect(result.inviteCodes).to.deep.equal(providedCodes);
    });

    it('должен генерировать invite коды если не предоставлены', async () => {
      // GIVEN: No invite codes provided
      const mockSpiralEngine = {
        connect: sinon.stub().returns({
          activateUser: sinon.stub().resolves({
            hash: '0xTx',
            wait: sinon.stub().resolves({ status: 1 })
          })
        })
      };
      
      sinon.stub(mockContractManager, 'getContract').returns(mockSpiralEngine);
      
      // WHEN: activateSellerBasic() без codes
      const result = await coreLogic.activateSellerBasic('0xSeller');
      
      // THEN: Codes автогенерированы
      expect(result.inviteCodes).to.be.an('array');
      expect(result.inviteCodes).to.have.lengthOf(12);
    });

    it('должен выбрасывать ошибку если SpiralEngine не найден', async () => {
      // GIVEN: SpiralEngine не найден
      sinon.stub(mockContractManager, 'getContract').returns(null);
      
      // WHEN: activateSellerBasic()
      try {
        await coreLogic.activateSellerBasic('0xSeller');
        expect.fail('Should have thrown error');
      } catch (error) {
        // THEN: Ошибка выбрасывается
        expect(error.message).to.include('SpiralEngine contract not found');
      }
    });
  });

  describe('Seller Activation - Delegation Tests', () => {
    let mockInviteActions;
    let mockSpiralEngine;

    beforeEach(() => {
      // Mock InviteActions
      mockInviteActions = {
        activateSeller: sinon.stub()
      };

      // Mock SpiralEngine
      mockSpiralEngine = {
        usedInviteByUser: sinon.stub().resolves('0'),
        SELLER_ROLE: sinon.stub().resolves('0x' + '1'.repeat(64)),
        hasRole: sinon.stub().resolves(false),
        inviteCodeExists: sinon.stub().resolves(true),
        connect: sinon.stub().returnsThis()
      };

      // Create CoreLogic with InviteActions
      coreLogic = new CoreLogic(
        mockContractManager,
        mockEthersUtils,
        mockConfig,
        mockInviteActions
      );

      // Stub getContract to return mockSpiralEngine
      sinon.stub(mockContractManager, 'getContract')
        .withArgs('SpiralEngine')
        .resolves(mockSpiralEngine);
    });

    it('должен делегировать в InviteActions когда inviteActions доступен', async () => {
      // GIVEN: Mock InviteActions возвращает результат
      const mockInviteResult = {
        success: true,
        sellerAddress: '0xSellerAddr',
        wasActivated: true,
        wasRoleGranted: true,
        newInvites: ['INVITE1', 'INVITE2'],
        activationResult: {
          txHash: '0xTransactionHash123'
        }
      };

      mockInviteActions.activateSeller.resolves(mockInviteResult);

      // WHEN: activateSellerBasic() вызывается
      const result = await coreLogic.activateSellerBasic('0xSellerAddr', ['CODE1']);

      // THEN: InviteActions.activateSeller() вызван
      expect(mockInviteActions.activateSeller.calledOnce).to.be.true;
      expect(mockInviteActions.activateSeller.calledWith(
        mockSpiralEngine,
        'CODE1', // Первый inviteCode из массива
        '0xSellerAddr'
      )).to.be.true;

      // THEN: Результат адаптирован под старую структуру
      expect(result).to.be.an('object');
      expect(result.success).to.be.true;
      expect(result.transactionHash).to.equal('0xTransactionHash123');
      expect(result.inviteCodes).to.deep.equal(['INVITE1', 'INVITE2']);
      expect(result.sellerAddress).to.equal('0xSellerAddr');
    });

    it('должен использовать inviteCode из конфига если inviteCodes не предоставлены', async () => {
      // GIVEN: Stub mockConfig.get для возврата inviteCode из конфига
      const originalGet = mockConfig.get;
      mockConfig.get = sinon.stub().callsFake((key) => {
        if (key === 'deployer.invite') return 'ROOT_INVITE_FROM_CONFIG';
        if (key === 'invite.deployer') return null;
        if (key === 'seller.address') return '0xSellerAddr';
        // Fallback на оригинальный get для других ключей
        return originalGet.call(mockConfig, key);
      });
      
      const mockInviteResult = {
        success: true,
        sellerAddress: '0xSellerAddr',
        wasActivated: true,
        wasRoleGranted: true,
        newInvites: [],
        activationResult: {
          txHash: '0xTx'
        }
      };

      mockInviteActions.activateSeller.resolves(mockInviteResult);

      // WHEN: activateSellerBasic() вызывается без inviteCodes
      const result = await coreLogic.activateSellerBasic('0xSellerAddr', null);

      // THEN: InviteActions.activateSeller() вызван с inviteCode из конфига
      expect(mockInviteActions.activateSeller.calledOnce).to.be.true;
      expect(mockInviteActions.activateSeller.calledWith(
        mockSpiralEngine,
        'ROOT_INVITE_FROM_CONFIG',
        '0xSellerAddr'
      )).to.be.true;

      expect(result.success).to.be.true;
    });

    it('должен адаптировать результат когда activationResult отсутствует', async () => {
      // GIVEN: Mock InviteActions возвращает результат без activationResult (seller уже активирован)
      const mockInviteResult = {
        success: true,
        sellerAddress: '0xSellerAddr',
        wasActivated: false, // Уже был активирован
        wasRoleGranted: false, // Роль уже была назначена
        newInvites: [],
        activationResult: null
      };

      mockInviteActions.activateSeller.resolves(mockInviteResult);

      // WHEN: activateSellerBasic() вызывается
      const result = await coreLogic.activateSellerBasic('0xSellerAddr', ['CODE1']);

      // THEN: Результат адаптирован (transactionHash = null)
      expect(result).to.be.an('object');
      expect(result.success).to.be.true;
      expect(result.transactionHash).to.be.null;
      expect(result.inviteCodes).to.deep.equal([]);
      expect(result.sellerAddress).to.equal('0xSellerAddr');
    });

    it('должен обрабатывать ошибки из InviteActions', async () => {
      // GIVEN: InviteActions выбрасывает ошибку
      const errorMessage = 'Invite code not found';
      mockInviteActions.activateSeller.rejects(new Error(errorMessage));

      // WHEN: activateSellerBasic() вызывается
      try {
        await coreLogic.activateSellerBasic('0xSellerAddr', ['CODE1']);
        expect.fail('Should have thrown error');
      } catch (error) {
        // THEN: Ошибка проброшена
        expect(error.message).to.include(errorMessage);
      }
    });
  });

  describe('Seller Activation - Fallback Tests', () => {
    it('должен использовать fallback на _activateSellerDirect когда inviteActions = null', async () => {
      // GIVEN: CoreLogic создан без InviteActions (null)
      coreLogic = new CoreLogic(
        mockContractManager,
        mockEthersUtils,
        mockConfig,
        null // inviteActions = null
      );

      // GIVEN: Mock SpiralEngine для fallback
      const mockSpiralEngine = {
        connect: sinon.stub().returns({
          activateUser: sinon.stub().resolves({
            hash: '0xFallbackHash',
            wait: sinon.stub().resolves({ status: 1 })
          })
        })
      };

      sinon.stub(mockContractManager, 'getContract')
        .withArgs('SpiralEngine')
        .resolves(mockSpiralEngine);

      // WHEN: activateSellerBasic() вызывается
      const result = await coreLogic.activateSellerBasic('0xSellerAddr', ['CODE1']);

      // THEN: Fallback на старую логику работает
      expect(result).to.be.an('object');
      expect(result.success).to.be.true;
      expect(result.transactionHash).to.equal('0xFallbackHash');
      expect(result.sellerAddress).to.equal('0xSellerAddr');
    });

    it('должен использовать fallback когда inviteActions = undefined', async () => {
      // GIVEN: CoreLogic создан без InviteActions (undefined - по умолчанию)
      coreLogic = new CoreLogic(
        mockContractManager,
        mockEthersUtils,
        mockConfig
        // inviteActions не передан (undefined)
      );

      // GIVEN: Mock SpiralEngine для fallback
      const mockSpiralEngine = {
        connect: sinon.stub().returns({
          activateUser: sinon.stub().resolves({
            hash: '0xFallbackHash2',
            wait: sinon.stub().resolves({ status: 1 })
          })
        })
      };

      sinon.stub(mockContractManager, 'getContract')
        .withArgs('SpiralEngine')
        .resolves(mockSpiralEngine);

      // WHEN: activateSellerBasic() вызывается
      const result = await coreLogic.activateSellerBasic('0xSellerAddr2');

      // THEN: Fallback на старую логику работает
      expect(result).to.be.an('object');
      expect(result.success).to.be.true;
      expect(result.transactionHash).to.equal('0xFallbackHash2');
    });
  });

  describe('Component Check - Real Tests', () => {
    it('должен проверять наличие components в контракте', async () => {
      // GIVEN: Mock OrganicComponentRegistry
      const mockRegistry = {
        getTotalComponents: sinon.stub().resolves('5')
      };
      
      sinon.stub(mockContractManager, 'getContract')
        .withArgs('OrganicComponentRegistry').returns(mockRegistry);
      
      // WHEN: checkComponentsLoaded() вызывается
      const result = await coreLogic.checkComponentsLoaded();
      
      // THEN: Result объект возвращается
      expect(result).to.be.an('object');
      expect(result.totalComponents).to.equal(5);
      expect(result.hasComponents).to.be.true;
    });

    it('должен возвращать hasComponents=false если components не найдены', async () => {
      // GIVEN: No components
      const mockRegistry = {
        getTotalComponents: sinon.stub().resolves('0')
      };
      
      sinon.stub(mockContractManager, 'getContract').returns(mockRegistry);
      
      // WHEN: checkComponentsLoaded()
      const result = await coreLogic.checkComponentsLoaded();
      
      // THEN: hasComponents = false
      expect(result).to.be.an('object');
      expect(result.totalComponents).to.equal(0);
      expect(result.hasComponents).to.be.false;
    });

    it('должен выбрасывать ошибку если OrganicComponentRegistry не найден', async () => {
      // GIVEN: Registry не найден
      sinon.stub(mockContractManager, 'getContract').returns(null);
      
      // WHEN: checkComponentsLoaded()
      try {
        await coreLogic.checkComponentsLoaded();
        expect.fail('Should have thrown error');
      } catch (error) {
        // THEN: Ошибка выбрасывается
        expect(error.message).to.include('OrganicComponentRegistry contract not found');
      }
    });
  });
});

