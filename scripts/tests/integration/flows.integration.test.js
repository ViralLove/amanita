/**
 * Flow Integration Tests
 * 
 * Validates multi-step workflows across multiple modules.
 * Focus: Realistic production scenarios with 2-4 modules cooperating.
 */

const { expect } = require('chai');
const sinon = require('sinon');
const { IntegrationHarness } = require('../helpers');

describe('Flow Integration Tests', () => {
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

  describe('Flow: Seller Activation (CoreLogic → ContractManager → EthersUtils)', () => {
    it('должен выполнить complete seller activation flow', async () => {
      // STEP 1: Setup mock contract
      const mockSpiralEngine = harness.setupContractMock('SpiralEngine', {
        usedInviteByUser: {
          call: async () => '0' // Not activated
        },
        activateUser: {
          call: async () => '1', // Token ID after activation
          encodeABI: '0xactivate'
        }
      });
      
      sinon.stub(modules.contractManager, 'getContract')
        .withArgs('SpiralEngine')
        .resolves(mockSpiralEngine);
      
      // STEP 2: Generate invite codes (EthersUtils)
      const codes = modules.ethersUtils.generateNewInviteCodes(12);
      expect(codes).to.have.lengthOf(12);
      
      // STEP 3: Activate seller (CoreLogic orchestrates)
      const result = await modules.coreLogic.activateSellerBasic(
        '0x70997970C51812dc3A010C7d01b50e0d17dc79C8',
        codes
      );
      
      // FLOW VALIDATED: 3 modules worked together
      expect(result.success).to.be.true;
      expect(result.inviteCodes).to.deep.equal(codes);
      expect(result.sellerAddress).to.match(/^0x[a-fA-F0-9]{40}$/);
      
      // EthersUtils (codes) → CoreLogic (orchestration) → ContractManager (execution)
    });

    it('должен обрабатывать error в mid-flow gracefully', async () => {
      // GIVEN: Contract fails during activation
      sinon.stub(modules.contractManager, 'getContract')
        .withArgs('SpiralEngine')
        .resolves(null); // Contract not found (error scenario)
      
      // WHEN: Try to activate
      try {
        await modules.coreLogic.activateSellerBasic('0xAddr', ['CODE']);
        expect.fail('Should have thrown error');
      } catch (error) {
        // THEN: Error handled correctly
        expect(error.message).to.include('SpiralEngine contract not found');
        
        // FLOW ERROR HANDLING: Error propagated with context
      }
    });
  });

  describe('Flow: Component Check (CoreManager → CoreLogic → ContractManager)', () => {
    it('должен выполнить facade delegation flow через 3 modules', async () => {
      // STEP 1: Mock component registry
      const mockRegistry = harness.setupContractMock('OrganicComponentRegistry', {
        getTotalComponents: {
          call: async () => '10' // 10 components registered
        }
      });
      
      sinon.stub(modules.contractManager, 'getContract')
        .withArgs('OrganicComponentRegistry')
        .resolves(mockRegistry);
      
      // STEP 2: CoreManager calls (facade)
      const result = await modules.coreManager.checkComponents();
      
      // FLOW VALIDATED: Facade → Business Logic → Contract Service
      expect(result.totalComponents).to.equal(10);
      expect(result.hasComponents).to.be.true;
      
      // CoreManager (API) → CoreLogic (business) → ContractManager (service)
    });
  });

  describe('Flow: Config → Module Initialization (Happy Path)', () => {
    it('должен инициализировать все modules из shared config', () => {
      // GIVEN: Config loaded once
      const config = modules.config;
      
      // WHEN: Multiple modules initialized with same config
      // (already done in setupIntegrationEnvironment)
      
      // THEN: All modules share same config instance
      expect(modules.contractManager.config).to.equal(config);
      expect(modules.arweaveManager.config).to.equal(config);
      expect(modules.coreLogic.config).to.equal(config);
      expect(modules.ethersUtils.config).to.equal(config);
      
      // FLOW: Config → ALL modules (single source of truth)
    });
  });

  describe('Flow: Arweave Upload (ArweaveManager Success Path)', () => {
    it('должен успешно загружать data в Arweave', async () => {
      // GIVEN: Mock Arweave API (success scenario)
      const mockArweave = harness.createMockArweaveClient();
      modules.arweaveManager.arweaveClient = mockArweave;
      modules.arweaveManager.arweaveKey = { mock: true };
      
      // WHEN: Upload происходит
      const result = await modules.arweaveManager.uploadJSON({ test: 'data' });
      
      // THEN: Upload succeeded
      expect(result.success).to.be.true;
      expect(result.txId).to.exist;
      expect(mockArweave.createTransaction.calledOnce).to.be.true;
      expect(mockArweave.transactions.sign.calledOnce).to.be.true;
      expect(mockArweave.transactions.post.calledOnce).to.be.true;
      
      // FLOW: Data → Transaction → Sign → Post → Success
    });
  });

  describe('Flow: Invite Generation → Activation (EthersUtils → CoreLogic)', () => {
    it('должен генерировать и использовать invites в one flow', async () => {
      // STEP 1: CoreLogic requests invites (no codes provided)
      const mockSpiralEngine = harness.setupContractMock('SpiralEngine', {
        usedInviteByUser: { call: async () => '0' },
        activateUser: { call: async () => '1', encodeABI: '0xactivate' }
      });
      
      sinon.stub(modules.contractManager, 'getContract')
        .withArgs('SpiralEngine')
        .resolves(mockSpiralEngine);
      
      // Spy на generateNewInviteCodes
      const generateSpy = sinon.spy(modules.ethersUtils, 'generateNewInviteCodes');
      
      // STEP 2: Activate WITHOUT providing codes (triggers generation)
      const result = await modules.coreLogic.activateSellerBasic('0xAddr', null);
      
      // FLOW VALIDATED: CoreLogic → EthersUtils (generate) → CoreLogic (use)
      expect(generateSpy.calledOnce).to.be.true;
      expect(result.inviteCodes).to.have.lengthOf(12); // Default count
      expect(result.success).to.be.true;
      
      // Internal flow: Request codes → Generate → Use in activation
    });
  });

  describe('Flow: Error Propagation Chain', () => {
    it('должен пробрасывать errors через module chain с context', async () => {
      // GIVEN: Mock Arweave failure
      const mockArweave = harness.createMockArweaveClient();
      mockArweave.createTransaction.rejects(new Error('Arweave service down'));
      modules.arweaveManager.arweaveClient = mockArweave;
      modules.arweaveManager.arweaveKey = { mock: true };
      
      // WHEN: Try to upload
      try {
        await modules.arweaveManager.uploadJSON({ data: 'test' });
        expect.fail('Should have thrown');
      } catch (error) {
        // THEN: Error chain validated
        expect(error.message).to.include('Arweave');
        
        // FLOW: External API error → ArweaveManager → Caller (with context)
      }
    });
  });
});

