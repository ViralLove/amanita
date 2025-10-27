/**
 * Unit Tests: ActionsManager
 * 
 * Tests for the centralized actions management and routing.
 */

const { expect } = require('chai');
const sinon = require('sinon');
const { ethers } = require('hardhat');
const { MockContractManager, MockArweaveManager, TestHarness } = require('../../helpers');

describe('ActionsManager', () => {
  let ActionsManager;
  let actionsManager;
  let mockContractManager;
  let mockArweaveManager;
  let mockProvider;
  let mockEthersUtils;
  let mockConfig;
  let harness;

  before(async () => {
    harness = new TestHarness();
    await harness.setupTestEnvironment();
    
    // Load modules
    const { ActionsManager: AM } = require('../../../lib/actions/index');
    const EthersUtils = require('../../../lib/utils/EthersUtils');
    
    ActionsManager = AM;
    
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
    mockArweaveManager = new MockArweaveManager();
    mockConfig = harness.createMockConfig();
    
    // Create mock EthersUtils
    mockEthersUtils = {
      getSigner: sinon.stub().returns({
        connect: sinon.stub().returnsThis(),
        sendTransaction: sinon.stub().resolves({ hash: '0x123', wait: sinon.stub().resolves({ status: 1 }) })
      }),
      generateNewInviteCodes: sinon.stub().returns(Array(12).fill().map((_, i) => `INVITE${i + 1}`)),
      createAccount: sinon.stub().returns({ address: '0xDeployer' })
    };
    
    actionsManager = new ActionsManager(
      mockContractManager,
      mockArweaveManager,
      mockEthersUtils,
      mockConfig
    );
  });

  describe('Initialization', () => {
    it('должен инициализироваться с dependencies', () => {
      // THEN: ActionsManager инициализирован
      expect(actionsManager).to.be.an('object');
      expect(actionsManager.contractManager).to.equal(mockContractManager);
      expect(actionsManager.arweaveManager).to.equal(mockArweaveManager);
      expect(actionsManager.ethersUtils).to.equal(mockEthersUtils);
      expect(actionsManager.config).to.equal(mockConfig);
    });

    it('должен иметь action modules', () => {
      // THEN: Action modules созданы
      expect(actionsManager.deployActions).to.be.an('object');
      expect(actionsManager.catalogActions).to.be.an('object');
      expect(actionsManager.componentActions).to.be.an('object');
    });
  });

  describe('Available Actions', () => {
    it('должен возвращать список доступных actions', () => {
      // WHEN: getAvailableActions() вызывается
      const actions = actionsManager.getAvailableActions();
      
      // THEN: Список actions возвращается
      expect(actions).to.be.an('array');
      expect(actions).to.have.lengthOf.at.least(10);
    });

    it('должен включать все основные actions', () => {
      // WHEN: getAvailableActions() вызывается
      const actions = actionsManager.getAvailableActions();
      
      // THEN: Все основные actions присутствуют
      expect(actions).to.include(0);
      expect(actions).to.include(1);
      expect(actions).to.include(2);
      expect(actions).to.include(41);
      expect(actions).to.include(42);
      expect(actions).to.include(43);
      expect(actions).to.include(444);
      expect(actions).to.include(555);
      expect(actions).to.include(777);
      expect(actions).to.include(888);
    });
  });

  describe('Action Descriptions', () => {
    it('должен возвращать описание для action', () => {
      // WHEN: getActionDescription() вызывается
      const description = actionsManager.getActionDescription(555);
      
      // THEN: Описание возвращается
      expect(description).to.be.a('string');
      expect(description).to.have.lengthOf.greaterThan(0);
    });

    it('должен возвращать описания для всех actions', () => {
      // GIVEN: Список всех actions
      const actions = [0, 1, 2, 41, 42, 43, 444, 555, 777, 888];
      
      // WHEN: Получаем описания
      actions.forEach(action => {
        const description = actionsManager.getActionDescription(action);
        
        // THEN: Каждый action имеет описание
        expect(description).to.be.a('string');
        expect(description).to.have.lengthOf.greaterThan(0);
      });
    });
  });

  describe('Action Execution Routing', () => {
    it('должен иметь метод executeAction', () => {
      // THEN: executeAction метод существует
      expect(actionsManager.executeAction).to.be.a('function');
    });

    it('должен выбрасывать ошибку для неизвестного action', async () => {
      // WHEN: executeAction() с неизвестным action
      try {
        await actionsManager.executeAction(999);
        expect.fail('Should have thrown an error');
      } catch (error) {
        // THEN: Ошибка выбрасывается
        expect(error.message).to.include('Unknown action');
      }
    });
  });

  describe('Action Module Integration', () => {
    it('должен иметь deployActions module', () => {
      // THEN: deployActions существует
      expect(actionsManager.deployActions).to.be.an('object');
      expect(actionsManager.deployActions.action0).to.be.a('function');
      expect(actionsManager.deployActions.action1).to.be.a('function');
    });

    it('должен иметь catalogActions module', () => {
      // THEN: catalogActions существует
      expect(actionsManager.catalogActions).to.be.an('object');
      expect(actionsManager.catalogActions.action41).to.be.a('function');
      expect(actionsManager.catalogActions.action42).to.be.a('function');
      expect(actionsManager.catalogActions.action43).to.be.a('function');
      expect(actionsManager.catalogActions.action444).to.be.a('function');
    });

    it('должен иметь componentActions module', () => {
      // THEN: componentActions существует
      expect(actionsManager.componentActions).to.be.an('object');
      expect(actionsManager.componentActions.action555).to.be.a('function');
    });

    it('должен иметь inviteActions module', () => {
      // THEN: inviteActions существует (Layer 4A - NEW!)
      expect(actionsManager.inviteActions).to.be.an('object');
      expect(actionsManager.inviteActions.action777).to.be.a('function');
      expect(actionsManager.inviteActions.activateUser).to.be.a('function');
    });
  });
});

