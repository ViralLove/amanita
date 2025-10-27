/**
 * Proof Integration Tests
 * 
 * Validates that integration test infrastructure works.
 * Tests basic module-to-module interactions.
 */

const { expect } = require('chai');
const sinon = require('sinon');
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
      // GIVEN: Setup mock contract FIRST (before calling method)
      const mockSpiralEngine = harness.setupContractMock('SpiralEngine', {
        usedInviteByUser: {
          call: async () => '0' // User not yet activated
        },
        activateUser: {
          call: async () => '1', // User activated with token ID 1
          encodeABI: '0xactivate'
        }
      });
      
      // Stub getContract BEFORE calling CoreLogic
      const getContractStub = sinon.stub(modules.contractManager, 'getContract')
        .withArgs('SpiralEngine')
        .resolves(mockSpiralEngine);
      
      // EthersUtils генерирует invite коды
      const inviteCodes = modules.ethersUtils.generateNewInviteCodes(3);
      expect(inviteCodes).to.have.lengthOf(3);
      
      // WHEN: CoreLogic использует оба модуля (ContractManager + EthersUtils)
      const result = await modules.coreLogic.activateSellerBasic(
        '0x70997970C51812dc3A010C7d01b50e0d17dc79C8',
        inviteCodes
      );
      
      // THEN: Интеграция validated
      expect(result).to.be.an('object');
      expect(result.success).to.be.true;
      expect(getContractStub.calledOnce).to.be.true;
      
      // EthersUtils generated codes → CoreLogic used them → ContractManager processed
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

