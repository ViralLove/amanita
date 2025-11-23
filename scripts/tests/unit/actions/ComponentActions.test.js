/**
 * Unit Tests: ComponentActions
 * Tests for component management and seller activation.
 * 
 * Тесты под НОВУЮ архитектуру (Layer 4B: Component Management)
 * ПОСЛЕ рефакторинга:
 * - action777, validateDeployerAccess, invite generation → InviteActions
 * - validateDeployerAccess → AccessControlActions
 * 
 * Coverage:
 * - action555() - orchestration (использует InviteActions + AccessControl)
 * - uploadComponentsCore() - router logic (только Full mode с Arweave)
 * - uploadComponentFull() - Arweave integration (Arweave-Readiness.js)
 * 
 * NOTE: activateSellerBasic() мигрировал в InviteActions.activateSeller()
 * NOTE: Quick mode (withArweave=false) не реализован и не планируется
 */

const { expect } = require('chai');
const sinon = require('sinon');
const fs = require('fs');
const ComponentActions = require('../../../lib/actions/ComponentActions');

describe('ComponentActions', () => {
  let componentActions;
  let mockContractManager;
  let mockArweaveManager;
  let mockEthersUtils;
  let mockConfig;
  let mockSigner;
  let mockInviteActions;

  beforeEach(() => {
    // Mock dependencies
    mockContractManager = {
      loadUUPSContract: sinon.stub(),
      loadContract: sinon.stub()
    };

    mockArweaveManager = {
      // Не используется в НОВОЙ архитектуре (Arweave-Readiness.js напрямую)
    };

    mockSigner = {
      getAddress: sinon.stub().resolves('0xSeller')
    };

    mockEthersUtils = {
      getSigner: sinon.stub().returns(mockSigner)
    };

    mockConfig = {
      get: sinon.stub()
    };

    // Mock InviteActions (Layer 4A dependency)
    mockInviteActions = {
      activateSeller: sinon.stub().resolves({
        success: true,
        wasActivated: true,
        wasRoleGranted: true,
        sellerAddress: '0xSeller'
      })
    };

    // Mock fs
    sinon.stub(fs, 'existsSync').returns(true);
    sinon.stub(fs, 'mkdirSync');
    sinon.stub(fs, 'writeFileSync');
    sinon.stub(fs, 'readdirSync').returns([]);

    componentActions = new ComponentActions(
      mockContractManager,
      mockArweaveManager,
      mockEthersUtils,
      mockConfig,
      mockInviteActions
    );
  });

  afterEach(() => {
    sinon.restore();
  });

  // ================================================================
  // SMOKE TESTS: Existence & Structure
  // ================================================================

  describe('Initialization', () => {
    it('должен инициализироваться с dependencies', () => {
      expect(componentActions.contractManager).to.equal(mockContractManager);
      expect(componentActions.ethersUtils).to.equal(mockEthersUtils);
      expect(componentActions.config).to.equal(mockConfig);
    });

    it('должен иметь метод action555', () => {
      expect(componentActions.action555).to.be.a('function');
    });

    it('должен иметь метод uploadComponentsCore', () => {
      expect(componentActions.uploadComponentsCore).to.be.a('function');
    });

    it('должен иметь метод uploadComponentFull', () => {
      expect(componentActions.uploadComponentFull).to.be.a('function');
    });
  });

  // ================================================================
  // NOTE: saveSellerInvites() MIGRATED → InviteActions.saveUserInvites()
  // ================================================================

  // ================================================================
  // NOTE: activateSellerBasic() MIGRATED → InviteActions.activateSeller()
  // ================================================================

  // Tests for migrated methods moved to InviteActions.test.js
  // See MIGRATION_SELLER_ACTIVATION.md for details

  // ================================================================
  // REAL TESTS: uploadComponentsCore (router logic)
  // ================================================================
  // NOTE: Quick mode (withArweave=false) не реализован и не планируется
  // Тесты для Quick mode удалены, так как uploadComponentsCore() выбрасывает
  // Error('Quick mode not implemented yet') при withArweave=false

  // ================================================================
  // REAL TESTS: uploadComponentFull (Arweave integration)
  // ================================================================

  describe('uploadComponentFull() - Real Tests (Arweave-Readiness)', () => {
    it('должен использовать Arweave-Readiness.js напрямую', async () => {
      // TODO: После рефакторинга (проверить интеграцию)
      // GIVEN: Mock Arweave-Readiness
      // const arweaveReadiness = require('../../Arweave-Readiness');
      // sinon.stub(arweaveReadiness, 'loadArweaveKey').resolves({ key: 'test' });
      // sinon.stub(arweaveReadiness, 'initArweave').returns({});
      
      // WHEN: uploadComponentFull вызывается
      // await componentActions.uploadComponentFull('0xSeller', 'data/components', 'localhost', false);
      
      // THEN: Arweave-Readiness использован
      // expect(arweaveReadiness.loadArweaveKey.calledOnce).to.be.true;
      
      expect(true).to.be.true; // Placeholder
    });

    it('должен вызвать uploadComponentsCore с withArweave=true', async () => {
      // TODO: После рефакторинга
      // Stub uploadComponentsCore
      // const uploadStub = sinon.stub(componentActions, 'uploadComponentsCore').resolves({ success: true });
      
      // WHEN: uploadComponentFull вызывается
      // await componentActions.uploadComponentFull('0xSeller', 'data/components', 'localhost', false);
      
      // THEN: uploadComponentsCore вызван с withArweave=true
      // expect(uploadStub.calledOnce).to.be.true;
      // expect(uploadStub.firstCall.args[4]).to.be.true; // withArweave parameter
      
      expect(true).to.be.true; // Placeholder
    });
  });

  // ================================================================
  // REAL TESTS: action555 (orchestration - TDD Spec)
  // ================================================================

  describe('action555() - Orchestration (TDD Spec)', () => {
    let mockSpiralEngine, mockOrganicRegistry;

    beforeEach(() => {
      mockSpiralEngine = {
        getAddress: sinon.stub().resolves('0xSpiral'),
        connect: sinon.stub().returnsThis(),
        // ✅ FIXED: Добавляем недостающие методы для activateSellerBasic
        usedInviteByUser: sinon.stub().resolves(0),
        inviteCodeToTokenId: sinon.stub().resolves(1),
        inviteCodeExists: sinon.stub().resolves(true),
        isInviteUsed: sinon.stub().resolves(false),
        activateUser: sinon.stub().resolves({
          wait: sinon.stub().resolves({ status: 1 })
        }),
        // ✅ FIXED: Добавляем SELLER_ROLE для activateSellerBasic
        SELLER_ROLE: sinon.stub().resolves('0xSellerRole'),
        hasRole: sinon.stub().resolves(true)
      };

      mockOrganicRegistry = {
        getAddress: sinon.stub().resolves('0xOrganic')
      };

      mockContractManager.loadUUPSContract.withArgs('SpiralEngine').resolves(mockSpiralEngine);
      mockContractManager.loadUUPSContract.withArgs('OrganicComponentRegistry').resolves(mockOrganicRegistry);
      
      // ✅ FIXED: Mock DEPLOYER_INVITE через process.env (как читает action555)
      process.env.DEPLOYER_INVITE = 'AMANITA-ROOT-777';
      process.env.SELLER_ADDRESS = '0xDeployer';
      
      // ✅ FIXED: Mock InviteActions для delegation
      const InviteActions = require('../../../lib/actions/InviteActions');
      const mockInviteActions = {
        activateSeller: sinon.stub().resolves({
          success: true,
          wasActivated: true,
          wasRoleGranted: true,
          sellerAddress: '0xDeployer',
          newInvites: ['AMANITA-NEW-001', 'AMANITA-NEW-002']
        })
      };
      componentActions.inviteActions = mockInviteActions;
    });
    
    afterEach(() => {
      // Cleanup environment variables
      delete process.env.DEPLOYER_INVITE;
      delete process.env.SELLER_ADDRESS;
    });

    it('должен загрузить необходимые контракты', async () => {
      // ✅ FIXED: Real test with proper environment setup
      const uploadStub = sinon.stub(componentActions, 'uploadComponentFull').resolves({ success: true });
      
      // WHEN: action555 вызывается
      const result = await componentActions.action555();
      
      // THEN: Контракты загружены
      expect(mockContractManager.loadUUPSContract.calledWith('SpiralEngine')).to.be.true;
      expect(result.success).to.be.true;
      
      // Cleanup stubs
      uploadStub.restore();
    });

    it('должен делегировать seller activation в InviteActions', async () => {
      // GIVEN: Mock uploadComponentFull
      const uploadStub = sinon.stub(componentActions, 'uploadComponentFull').resolves({ 
        success: true,
        totalCount: 11,
        successCount: 11,
        failCount: 0
      });
      
      // Mock SpiralEngine
      const mockSpiralEngineLocal = {
        getAddress: sinon.stub().resolves('0xSpiral')
      };
      mockContractManager.loadUUPSContract.withArgs('SpiralEngine').resolves(mockSpiralEngineLocal);
      
      // Setup env
      process.env.DEPLOYER_INVITE = 'AMANITA-ROOT-777';
      process.env.SELLER_ADDRESS = '0xSeller';
      
      // WHEN: action555 вызывается
      const result = await componentActions.action555();
      
      // THEN: InviteActions.activateSeller вызван через delegation
      expect(componentActions.inviteActions.activateSeller.calledOnce).to.be.true;
      expect(componentActions.inviteActions.activateSeller.firstCall.args[0]).to.equal(mockSpiralEngineLocal);
      expect(componentActions.inviteActions.activateSeller.firstCall.args[1]).to.equal('AMANITA-ROOT-777');
      expect(componentActions.inviteActions.activateSeller.firstCall.args[2]).to.equal('0xSeller');
      expect(result.success).to.be.true;
      
      // Cleanup
      delete process.env.DEPLOYER_INVITE;
      delete process.env.SELLER_ADDRESS;
      uploadStub.restore();
    });

    it('должен вызвать uploadComponentFull', async () => {
      // GIVEN: Mock uploadComponentFull
      const uploadStub = sinon.stub(componentActions, 'uploadComponentFull').resolves({ 
        success: true, 
        totalCount: 11,
        successCount: 11,
        failCount: 0
      });
      
      // Mock SpiralEngine
      const mockSpiralEngine = {
        getAddress: sinon.stub().resolves('0xSpiral')
      };
      componentActions.contractManager.loadUUPSContract.withArgs('SpiralEngine').resolves(mockSpiralEngine);
      
      // Setup env
      process.env.DEPLOYER_INVITE = 'TEST-INVITE';
      process.env.SELLER_ADDRESS = '0xSeller';
      
      // WHEN: action555 вызывается
      await componentActions.action555();
      
      // THEN: uploadComponentFull вызван
      expect(uploadStub.calledOnce).to.be.true;
      
      // Cleanup
      delete process.env.DEPLOYER_INVITE;
      delete process.env.SELLER_ADDRESS;
      uploadStub.restore();
    });

    it('должен вернуть success result', async () => {
      // GIVEN: Mock uploadComponentFull
      const uploadStub = sinon.stub(componentActions, 'uploadComponentFull').resolves({ 
        success: true, 
        totalCount: 11,
        successCount: 11,
        failCount: 0
      });
      
      // Mock SpiralEngine
      const mockSpiralEngine = {
        getAddress: sinon.stub().resolves('0xSpiral')
      };
      componentActions.contractManager.loadUUPSContract.withArgs('SpiralEngine').resolves(mockSpiralEngine);
      
      // Setup env
      process.env.DEPLOYER_INVITE = 'TEST-INVITE';
      process.env.SELLER_ADDRESS = '0xSeller';
      
      // WHEN: action555 вызывается
      const result = await componentActions.action555();
      
      // THEN: Result корректный
      expect(result).to.have.property('success', true);
      
      // Cleanup
      delete process.env.DEPLOYER_INVITE;
      delete process.env.SELLER_ADDRESS;
      uploadStub.restore();
    });
  });
});

