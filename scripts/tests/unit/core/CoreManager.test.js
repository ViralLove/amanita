/**
 * Unit Tests: CoreManager
 * 
 * Tests for the core manager interface.
 */

const { expect } = require('chai');
const sinon = require('sinon');
const { ethers } = require('hardhat');
const { MockContractManager, TestHarness } = require('../../helpers');

describe('CoreManager', () => {
  let CoreManager;
  let coreManager;
  let mockContractManager;
  let mockProvider;
  let mockEthersUtils;
  let mockConfig;
  let harness;

  before(async () => {
    harness = new TestHarness();
    await harness.setupTestEnvironment();
    
    // Load modules
    const { CoreManager: CM } = require('../../../lib/core/index');
    const EthersUtils = require('../../../lib/utils/EthersUtils');
    
    CoreManager = CM;
    
    // Create mock provider
    mockProvider = {
      getBalance: sinon.stub(),
      getNetwork: sinon.stub(),
      getBlockNumber: sinon.stub()
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
    
    coreManager = new CoreManager(
      mockContractManager,
      mockEthersUtils,
      mockConfig
    );
  });

  afterEach(() => {
    // Restore all stubs after each test
    sinon.restore();
  });

  describe('Initialization', () => {
    it('должен инициализироваться с dependencies', () => {
      // THEN: CoreManager инициализирован
      expect(coreManager).to.be.an('object');
      expect(coreManager.contractManager).to.equal(mockContractManager);
      expect(coreManager.ethersUtils).to.equal(mockEthersUtils);
      expect(coreManager.config).to.equal(mockConfig);
    });

    it('должен иметь coreLogic instance', () => {
      // THEN: coreLogic создан
      expect(coreManager.coreLogic).to.be.an('object');
    });
  });

  describe('Convenience Methods', () => {
    it('должен предоставлять доступ к CoreLogic методам', () => {
      // THEN: Методы доступны
      expect(coreManager.activateSeller).to.be.a('function');
      expect(coreManager.setupSeller).to.be.a('function');
      expect(coreManager.validateSeller).to.be.a('function');
      expect(coreManager.checkComponents).to.be.a('function');
      expect(coreManager.createCatalog).to.be.a('function');
    });
  });

  describe('getCoreLogic Method', () => {
    it('должен возвращать CoreLogic instance', () => {
      // WHEN: getCoreLogic() вызывается
      const logic = coreManager.getCoreLogic();
      
      // THEN: CoreLogic instance возвращается
      expect(logic).to.be.an('object');
      expect(logic.activateSellerBasic).to.be.a('function');
    });
  });

  describe('Delegation Tests - activateSeller', () => {
    it('должен делегировать activateSeller к CoreLogic.activateSellerBasic', async () => {
      // GIVEN: Spy на coreLogic.activateSellerBasic
      const activateSpy = sinon.stub(coreManager.coreLogic, 'activateSellerBasic')
        .resolves({ success: true, transactionHash: '0xActivated' });
      
      // WHEN: activateSeller() вызывается
      const result = await coreManager.activateSeller('0xSellerAddr', ['CODE1', 'CODE2']);
      
      // THEN: CoreLogic метод вызван
      expect(activateSpy.calledOnce).to.be.true;
      expect(activateSpy.calledWith('0xSellerAddr', ['CODE1', 'CODE2'])).to.be.true;
      expect(result.success).to.be.true;
    });

    it('должен передавать параметры корректно', async () => {
      // GIVEN: Stub для проверки параметров
      let capturedAddress, capturedCodes;
      sinon.stub(coreManager.coreLogic, 'activateSellerBasic')
        .callsFake(async (addr, codes) => {
          capturedAddress = addr;
          capturedCodes = codes;
          return { success: true };
        });
      
      // WHEN: activateSeller() с параметрами
      await coreManager.activateSeller('0xTestAddr', ['A', 'B', 'C']);
      
      // THEN: Параметры переданы корректно
      expect(capturedAddress).to.equal('0xTestAddr');
      expect(capturedCodes).to.deep.equal(['A', 'B', 'C']);
    });

    it('должен передавать null параметры', async () => {
      // GIVEN: Stub
      let capturedAddress, capturedCodes;
      sinon.stub(coreManager.coreLogic, 'activateSellerBasic')
        .callsFake(async (addr, codes) => {
          capturedAddress = addr;
          capturedCodes = codes;
          return { success: true };
        });
      
      // WHEN: activateSeller() без параметров
      await coreManager.activateSeller();
      
      // THEN: null параметры переданы
      expect(capturedAddress).to.be.null;
      expect(capturedCodes).to.be.null;
    });
  });

  describe('Delegation Tests - setupSeller', () => {
    it('должен делегировать setupSeller к CoreLogic.setupSellerRole', async () => {
      // GIVEN: Spy на setupSellerRole
      const setupSpy = sinon.stub(coreManager.coreLogic, 'setupSellerRole')
        .resolves({ success: true, role: 'SELLER_ROLE' });
      
      // WHEN: setupSeller() вызывается
      const result = await coreManager.setupSeller('0xSellerAddr');
      
      // THEN: CoreLogic метод вызван с правильными параметрами
      expect(setupSpy.calledOnce).to.be.true;
      expect(setupSpy.calledWith('0xSellerAddr')).to.be.true;
      expect(result.success).to.be.true;
    });
  });

  describe('Delegation Tests - validateSeller', () => {
    it('должен делегировать validateSeller к CoreLogic.validateSellerAccess', async () => {
      // GIVEN: Spy на validateSellerAccess
      const validateSpy = sinon.stub(coreManager.coreLogic, 'validateSellerAccess')
        .resolves({ isValid: true, hasRole: true });
      
      // WHEN: validateSeller() вызывается
      const result = await coreManager.validateSeller('0xSellerAddr');
      
      // THEN: CoreLogic метод вызван
      expect(validateSpy.calledOnce).to.be.true;
      expect(validateSpy.calledWith('0xSellerAddr')).to.be.true;
      expect(result.isValid).to.be.true;
    });
  });

  describe('Delegation Tests - checkComponents', () => {
    it('должен делегировать checkComponents к CoreLogic.checkComponentsLoaded', async () => {
      // GIVEN: Spy на checkComponentsLoaded
      const checkSpy = sinon.stub(coreManager.coreLogic, 'checkComponentsLoaded')
        .resolves({ totalComponents: 5, hasComponents: true });
      
      // WHEN: checkComponents() вызывается
      const result = await coreManager.checkComponents();
      
      // THEN: CoreLogic метод вызван
      expect(checkSpy.calledOnce).to.be.true;
      expect(result.totalComponents).to.equal(5);
    });
  });

  describe('Delegation Tests - generateInvites', () => {
    it('должен делегировать generateInvites к CoreLogic.generateInvitesForSeller', async () => {
      // GIVEN: Spy на generateInvitesForSeller
      const generateSpy = sinon.stub(coreManager.coreLogic, 'generateInvitesForSeller')
        .resolves({ codes: ['A', 'B', 'C'], count: 3 });
      
      // WHEN: generateInvites() вызывается
      const result = await coreManager.generateInvites('0xSellerAddr', 3);
      
      // THEN: CoreLogic метод вызван с параметрами
      expect(generateSpy.calledOnce).to.be.true;
      expect(generateSpy.calledWith('0xSellerAddr', 3)).to.be.true;
      expect(result.codes).to.have.lengthOf(3);
    });

    it('должен использовать default count=12', async () => {
      // GIVEN: Spy
      let capturedCount;
      sinon.stub(coreManager.coreLogic, 'generateInvitesForSeller')
        .callsFake(async (addr, count) => {
          capturedCount = count;
          return { codes: [], count };
        });
      
      // WHEN: generateInvites() без count
      await coreManager.generateInvites('0xAddr');
      
      // THEN: Default count=12 передан
      expect(capturedCount).to.equal(12);
    });
  });

  describe('Error Propagation', () => {
    it('должен пробрасывать ошибки из CoreLogic', async () => {
      // GIVEN: CoreLogic выбрасывает ошибку
      sinon.stub(coreManager.coreLogic, 'activateSellerBasic')
        .rejects(new Error('Activation failed'));
      
      // WHEN: activateSeller() вызывается
      try {
        await coreManager.activateSeller('0xAddr');
        expect.fail('Should have thrown error');
      } catch (error) {
        // THEN: Ошибка пробрасывается без изменений
        expect(error.message).to.equal('Activation failed');
      }
    });
  });
});

