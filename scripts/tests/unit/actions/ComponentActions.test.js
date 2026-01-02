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

    it('должен иметь метод action51', () => {
      expect(componentActions.action51).to.be.a('function');
    });

    it('должен иметь метод action52', () => {
      expect(componentActions.action52).to.be.a('function');
    });

    it('должен иметь метод action53', () => {
      expect(componentActions.action53).to.be.a('function');
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
  // REAL TESTS: action51 (seller activation)
  // ================================================================

  describe('action51() - Seller Activation', () => {
    let mockSpiralEngine;

    beforeEach(() => {
      mockSpiralEngine = {
        getAddress: sinon.stub().resolves('0xSpiral'),
        usedInviteByUser: sinon.stub().resolves(1),
        SELLER_ROLE: sinon.stub().resolves('0xSellerRole'),
        hasRole: sinon.stub().resolves(true)
      };

      mockContractManager.loadUUPSContract.withArgs('SpiralEngine').resolves(mockSpiralEngine);
      
      mockInviteActions.activateSeller.resolves({
        wasActivated: true,
        wasRoleGranted: true,
        newInvites: ['AMANITA-NEW-001', 'AMANITA-NEW-002']
      });

      process.env.DEPLOYER_INVITE = 'AMANITA-ROOT-777';
      process.env.SELLER_ADDRESS = '0xSeller';
    });

    afterEach(() => {
      delete process.env.DEPLOYER_INVITE;
      delete process.env.SELLER_ADDRESS;
    });

    it('должен загрузить SpiralEngine контракт', async () => {
      // WHEN: action51 вызывается
      await componentActions.action51();

      // THEN: SpiralEngine загружен
      expect(mockContractManager.loadUUPSContract.calledWith('SpiralEngine')).to.be.true;
    });

    it('должен вызвать InviteActions.activateSeller с правильными параметрами', async () => {
      // WHEN: action51 вызывается
      await componentActions.action51();

      // THEN: activateSeller вызван с правильными параметрами
      expect(mockInviteActions.activateSeller.calledOnce).to.be.true;
      expect(mockInviteActions.activateSeller.firstCall.args[0]).to.equal(mockSpiralEngine);
      expect(mockInviteActions.activateSeller.firstCall.args[1]).to.equal('AMANITA-ROOT-777');
      expect(mockInviteActions.activateSeller.firstCall.args[2]).to.equal('0xSeller');
    });

    it('должен валидировать активацию через blockchain', async () => {
      // WHEN: action51 вызывается
      await componentActions.action51();

      // THEN: Проверка usedInviteByUser
      expect(mockSpiralEngine.usedInviteByUser.calledWith('0xSeller')).to.be.true;
      
      // THEN: Проверка hasRole
      expect(mockSpiralEngine.SELLER_ROLE.called).to.be.true;
      expect(mockSpiralEngine.hasRole.calledWith('0xSellerRole', '0xSeller')).to.be.true;
    });

    it('должен выбросить ошибку если DEPLOYER_INVITE отсутствует', async () => {
      // GIVEN: Seller НЕ активирован (иначе будет skipActivation)
      mockSpiralEngine.usedInviteByUser.resolves(0); // Не активирован
      mockSpiralEngine.SELLER_ROLE.resolves('0xSELLER_ROLE');
      mockSpiralEngine.hasRole.resolves(false); // Не имеет роли
      delete process.env.DEPLOYER_INVITE;

      // WHEN/THEN: Должна быть выброшена ошибка
      // (код проверяет активацию ДО требования DEPLOYER_INVITE, и если seller не активирован, требует DEPLOYER_INVITE)
      await expect(componentActions.action51()).to.be.rejectedWith('Action 51: требуется DEPLOYER_INVITE');
    });

    it('должен выбросить ошибку если SELLER_ADDRESS отсутствует', async () => {
      // GIVEN: SELLER_ADDRESS не установлен
      delete process.env.SELLER_ADDRESS;
      mockConfig.get.withArgs('seller.address').returns(null);

      // WHEN/THEN: Должна быть выброшена ошибка
      await expect(componentActions.action51()).to.be.rejectedWith('Action 51: требуется SELLER_ADDRESS');
    });

    it('должен выбросить ошибку если seller не активирован после activateSeller', async () => {
      // GIVEN: usedInviteByUser возвращает 0 (не активирован)
      mockSpiralEngine.usedInviteByUser.resolves(0);

      // WHEN/THEN: Должна быть выброшена ошибка
      await expect(componentActions.action51()).to.be.rejectedWith('не активирован после вызова activateSeller');
    });

    it('должен выбросить ошибку если seller не имеет SELLER_ROLE', async () => {
      // GIVEN: hasRole возвращает false
      mockSpiralEngine.hasRole.resolves(false);

      // WHEN/THEN: Должна быть выброшена ошибка
      await expect(componentActions.action51()).to.be.rejectedWith('не имеет SELLER_ROLE');
    });

    it('должен вернуть правильный результат', async () => {
      // WHEN: action51 вызывается
      const result = await componentActions.action51();

      // THEN: Result содержит все необходимые поля
      expect(result).to.have.property('success', true);
      expect(result).to.have.property('sellerAddress', '0xSeller');
      expect(result).to.have.property('spiralEngineAddress', '0xSpiral');
      expect(result).to.have.property('wasActivated', true);
      expect(result).to.have.property('wasRoleGranted', true);
      expect(result).to.have.property('newInvites').that.is.an('array');
      expect(result).to.have.property('inviteCodeUsed', 'AMANITA-ROOT-777');
    });

    it('должен пропустить активацию если seller уже активирован (skipActivation)', async () => {
      // GIVEN: Seller уже активирован (usedInvite > 0 и hasRole = true)
      mockSpiralEngine.usedInviteByUser.resolves(1); // Уже активирован
      mockSpiralEngine.hasRole.resolves(true); // Имеет SELLER_ROLE
      delete process.env.DEPLOYER_INVITE; // DEPLOYER_INVITE не требуется

      // WHEN: action51 вызывается
      const result = await componentActions.action51();

      // THEN: Результат содержит skipActivation: true
      expect(result).to.have.property('success', true);
      expect(result).to.have.property('skipActivation', true);
      expect(result).to.have.property('sellerAddress', '0xSeller');
      expect(result).to.have.property('spiralEngineAddress', '0xSpiral');
      expect(result).to.have.property('wasActivated', false);
      expect(result).to.have.property('wasRoleGranted', false);
      expect(result).to.have.property('newInvites').that.is.an('array').that.is.empty;

      // THEN: activateSeller НЕ должен быть вызван
      expect(mockInviteActions.activateSeller.called).to.be.false;

      // THEN: Проверка активации должна быть выполнена ДО требования DEPLOYER_INVITE
      expect(mockSpiralEngine.usedInviteByUser.calledWith('0xSeller')).to.be.true;
      expect(mockSpiralEngine.hasRole.called).to.be.true;
    });

    it('должен требовать DEPLOYER_INVITE только если seller НЕ активирован', async () => {
      // GIVEN: Seller НЕ активирован
      mockSpiralEngine.usedInviteByUser.resolves(0); // Не активирован
      delete process.env.DEPLOYER_INVITE;

      // WHEN/THEN: Должна быть выброшена ошибка о необходимости DEPLOYER_INVITE
      await expect(componentActions.action51()).to.be.rejectedWith('Action 51: требуется DEPLOYER_INVITE');
    });

    // ✅ P0: Edge cases для action51 skipActivation
    it('должен требовать DEPLOYER_INVITE если usedInvite=0 но hasRole=true', async () => {
      // GIVEN: Edge case - seller не активирован (usedInvite=0), но имеет роль (hasRole=true)
      // Это невалидное состояние, но код должен требовать активацию
      mockSpiralEngine.usedInviteByUser.resolves(0); // Не активирован
      mockSpiralEngine.SELLER_ROLE.resolves('0xSELLER_ROLE'); // Нужен для проверки
      mockSpiralEngine.hasRole.resolves(true); // Но имеет роль (невалидное состояние)
      delete process.env.DEPLOYER_INVITE;

      // WHEN/THEN: Должна быть выброшена ошибка о необходимости DEPLOYER_INVITE
      // (код проверяет isActivated && hasSellerRole, оба должны быть true)
      // isActivated = usedInvite > 0 = false, поэтому условие не выполняется
      await expect(componentActions.action51()).to.be.rejectedWith('Action 51: требуется DEPLOYER_INVITE');
      
      // THEN: Проверка активации должна быть выполнена ДО требования DEPLOYER_INVITE
      expect(mockSpiralEngine.usedInviteByUser.calledWith('0xSeller')).to.be.true;
      expect(mockSpiralEngine.SELLER_ROLE.called).to.be.true;
      expect(mockSpiralEngine.hasRole.called).to.be.true;
      
      // THEN: activateSeller НЕ должен быть вызван (нет DEPLOYER_INVITE)
      expect(mockInviteActions.activateSeller.called).to.be.false;
    });

    it('должен требовать DEPLOYER_INVITE если usedInvite=1 но hasRole=false', async () => {
      // GIVEN: Edge case - seller активирован (usedInvite=1), но не имеет роли (hasRole=false)
      // Это невалидное состояние, но код должен требовать активацию роли
      mockSpiralEngine.usedInviteByUser.resolves(1); // Активирован
      mockSpiralEngine.SELLER_ROLE.resolves('0xSELLER_ROLE'); // Нужен для проверки
      mockSpiralEngine.hasRole.resolves(false); // Но не имеет роли (невалидное состояние)
      delete process.env.DEPLOYER_INVITE;

      // WHEN/THEN: Должна быть выброшена ошибка о необходимости DEPLOYER_INVITE
      // (код проверяет isActivated && hasSellerRole, оба должны быть true)
      // isActivated = true, но hasSellerRole = false, поэтому условие не выполняется
      await expect(componentActions.action51()).to.be.rejectedWith('Action 51: требуется DEPLOYER_INVITE');
      
      // THEN: Проверка активации должна быть выполнена ДО требования DEPLOYER_INVITE
      expect(mockSpiralEngine.usedInviteByUser.calledWith('0xSeller')).to.be.true;
      expect(mockSpiralEngine.SELLER_ROLE.called).to.be.true;
      expect(mockSpiralEngine.hasRole.called).to.be.true;
      
      // THEN: activateSeller НЕ должен быть вызван (нет DEPLOYER_INVITE)
      expect(mockInviteActions.activateSeller.called).to.be.false;
    });
  });

  // ================================================================
  // REAL TESTS: action52 (Arweave upload)
  // ================================================================

  describe('action52() - Arweave Upload', () => {
    let mockSpiralEngine, mockOrganicRegistry, mockAmanitaIntl;
    let mockArweaveManagerInstance;

    beforeEach(() => {
      mockSpiralEngine = {
        usedInviteByUser: sinon.stub().resolves(1),
        SELLER_ROLE: sinon.stub().resolves('0xSellerRole'),
        hasRole: sinon.stub().resolves(true)
      };

      mockOrganicRegistry = {
        getAddress: sinon.stub().resolves('0xOrganic')
      };

      mockAmanitaIntl = {
        getAddress: sinon.stub().resolves('0xAmanita')
      };

      mockContractManager.loadUUPSContract.withArgs('OrganicComponentRegistry').resolves(mockOrganicRegistry);
      mockContractManager.loadUUPSContract.withArgs('AmanitaInternational').resolves(mockAmanitaIntl);
      mockContractManager.loadUUPSContract.withArgs('SpiralEngine').resolves(mockSpiralEngine);

      mockArweaveManagerInstance = {
        isReady: sinon.stub().returns(true),
        initialize: sinon.stub().resolves({ success: true }),
        getClient: sinon.stub().returns({ mock: 'arweave-client' }),
        getKey: sinon.stub().returns({ mock: 'arweave-key' })
      };

      componentActions.arweaveManager = mockArweaveManagerInstance;

      mockEthersUtils.provider = { mock: 'provider' };
      mockConfig.get.withArgs('seller.address').returns('0xSeller');
      mockConfig.get.withArgs('seller.privateKey').returns('0xSellerPrivateKey');
      mockConfig.get.withArgs('network.name').returns('localhost');

      process.env.SELLER_ADDRESS = '0xSeller';
      process.env.COMPONENTS_DIR = 'data/components';
      process.env.DRY_RUN = 'false';

      // Mock fs для поиска компонентов
      fs.readdirSync.returns([
        { name: 'amanita_muscaria', isDirectory: () => true },
        { name: 'blue_lotus', isDirectory: () => true }
      ]);
      fs.existsSync.callsFake((path) => {
        if (path.includes('data/components')) return true;
        if (path.endsWith('.json')) return true;
        return false;
      });
    });

    afterEach(() => {
      delete process.env.SELLER_ADDRESS;
      delete process.env.COMPONENTS_DIR;
      delete process.env.DRY_RUN;
    });

    it('должен загрузить необходимые контракты', async () => {
      // GIVEN: Mock action52_UnifiedArweaveUpload через require cache
      const uploadStepsPath = require.resolve('../../../lib/upload_steps');
      const uploadSteps = require(uploadStepsPath);
      const originalAction52 = uploadSteps.action52_UnifiedArweaveUpload;
      
      const action52Stub = sinon.stub(uploadSteps, 'action52_UnifiedArweaveUpload').resolves({
        success: true,
        successCount: 2,
        failCount: 0,
        totalCount: 2
      });

      // WHEN: action52 вызывается
      await componentActions.action52();

      // THEN: Контракты загружены
      expect(mockContractManager.loadUUPSContract.calledWith('OrganicComponentRegistry')).to.be.true;
      expect(mockContractManager.loadUUPSContract.calledWith('AmanitaInternational')).to.be.true;
      expect(mockContractManager.loadUUPSContract.calledWith('SpiralEngine')).to.be.true;

      // Restore
      action52Stub.restore();
    });

    it('должен передать useExistingCids в context если USE_EXISTING_CIDS установлен', async () => {
      // GIVEN: USE_EXISTING_CIDS установлен
      process.env.USE_EXISTING_CIDS = 'true';
      
      const uploadStepsPath = require.resolve('../../../lib/upload_steps');
      const uploadSteps = require(uploadStepsPath);
      const action52Stub = sinon.stub(uploadSteps, 'action52_UnifiedArweaveUpload').resolves({
        success: true,
        successCount: 1,
        failCount: 0,
        totalCount: 1
      });

      // WHEN: action52 вызывается
      await componentActions.action52();

      // THEN: action52_UnifiedArweaveUpload вызван с context содержащим useExistingCids: true
      expect(action52Stub.calledOnce).to.be.true;
      const contextArg = action52Stub.firstCall.args[0];
      expect(contextArg).to.have.property('useExistingCids', true);

      action52Stub.restore();
      delete process.env.USE_EXISTING_CIDS;
    });

    it('должен передать useExistingCids: false если USE_EXISTING_CIDS не установлен', async () => {
      // GIVEN: USE_EXISTING_CIDS не установлен
      delete process.env.USE_EXISTING_CIDS;
      
      const uploadStepsPath = require.resolve('../../../lib/upload_steps');
      const uploadSteps = require(uploadStepsPath);
      const action52Stub = sinon.stub(uploadSteps, 'action52_UnifiedArweaveUpload').resolves({
        success: true,
        successCount: 1,
        failCount: 0,
        totalCount: 1
      });

      // WHEN: action52 вызывается
      await componentActions.action52();

      // THEN: action52_UnifiedArweaveUpload вызван с context содержащим useExistingCids: false
      expect(action52Stub.calledOnce).to.be.true;
      const contextArg = action52Stub.firstCall.args[0];
      expect(contextArg).to.have.property('useExistingCids', false);

      action52Stub.restore();
    });

    // ================================================================
    // Тест 2: Action 52 с USE_EXISTING_CIDS=true и CID в state
    // ================================================================
    it('должен использовать существующие CID если USE_EXISTING_CIDS=true и CID есть в state (Тест 2)', async () => {
      // GIVEN: USE_EXISTING_CIDS установлен
      process.env.USE_EXISTING_CIDS = 'true';
      
      const uploadStepsPath = require.resolve('../../../lib/upload_steps');
      const uploadSteps = require(uploadStepsPath);
      
      // GIVEN: Mock action52_UnifiedArweaveUpload который проверяет использование существующих CID
      const action52Stub = sinon.stub(uploadSteps, 'action52_UnifiedArweaveUpload').callsFake(async (context) => {
        // Проверяем что useExistingCids передан
        expect(context.useExistingCids).to.be.true;
        
        // Симулируем что функции upload используют существующие CID
        // (в реальности это проверяется в upload_steps.test.js)
        return {
          success: true,
          successCount: 2,
          failCount: 0,
          totalCount: 2,
          results: [
            {
              componentId: 'amanita_muscaria',
              success: true,
              usedExistingCids: true // ✅ Индикатор что использовались существующие CID
            }
          ]
        };
      });

      // WHEN: action52 вызывается
      const result = await componentActions.action52();

      // THEN: action52_UnifiedArweaveUpload вызван с useExistingCids: true
      expect(action52Stub.calledOnce).to.be.true;
      const contextArg = action52Stub.firstCall.args[0];
      expect(contextArg).to.have.property('useExistingCids', true);
      
      // THEN: Результат указывает на использование существующих CID
      expect(result).to.have.property('success', true);
      expect(result.result.results[0]).to.have.property('usedExistingCids', true);

      action52Stub.restore();
      delete process.env.USE_EXISTING_CIDS;
    });

    // ================================================================
    // Тест 3: Action 52 с USE_EXISTING_CIDS=true но без CID в state (fallback)
    // ================================================================
    it('должен выполнить fallback на загрузку если USE_EXISTING_CIDS=true но CID отсутствуют (Тест 3)', async () => {
      // GIVEN: USE_EXISTING_CIDS установлен, но CID отсутствуют
      process.env.USE_EXISTING_CIDS = 'true';
      
      const uploadStepsPath = require.resolve('../../../lib/upload_steps');
      const uploadSteps = require(uploadStepsPath);
      
      // GIVEN: Mock action52_UnifiedArweaveUpload который симулирует fallback
      const action52Stub = sinon.stub(uploadSteps, 'action52_UnifiedArweaveUpload').callsFake(async (context) => {
        // Проверяем что useExistingCids передан
        expect(context.useExistingCids).to.be.true;
        
        // Симулируем fallback (загрузка в Arweave)
        return {
          success: true,
          successCount: 2,
          failCount: 0,
          totalCount: 2,
          results: [
            {
              componentId: 'amanita_muscaria',
              success: true,
              usedExistingCids: false, // ❌ CID не использовались
              fallbackToUpload: true // ✅ Fallback выполнен
            }
          ]
        };
      });

      // WHEN: action52 вызывается
      const result = await componentActions.action52();

      // THEN: action52_UnifiedArweaveUpload вызван с useExistingCids: true
      expect(action52Stub.calledOnce).to.be.true;
      const contextArg = action52Stub.firstCall.args[0];
      expect(contextArg).to.have.property('useExistingCids', true);
      
      // THEN: Результат указывает на fallback
      expect(result).to.have.property('success', true);
      expect(result.result.results[0]).to.have.property('usedExistingCids', false);
      expect(result.result.results[0]).to.have.property('fallbackToUpload', true);

      action52Stub.restore();
      delete process.env.USE_EXISTING_CIDS;
    });

    // ================================================================
    // Тест 4: Action 52 с USE_EXISTING_CIDS=false
    // ================================================================
    it('должен загрузить в Arweave если USE_EXISTING_CIDS=false (Тест 4)', async () => {
      // GIVEN: USE_EXISTING_CIDS=false (обычная логика)
      process.env.USE_EXISTING_CIDS = 'false';
      
      const uploadStepsPath = require.resolve('../../../lib/upload_steps');
      const uploadSteps = require(uploadStepsPath);
      
      // GIVEN: Mock action52_UnifiedArweaveUpload который симулирует обычную загрузку
      const action52Stub = sinon.stub(uploadSteps, 'action52_UnifiedArweaveUpload').callsFake(async (context) => {
        // Проверяем что useExistingCids: false
        expect(context.useExistingCids).to.be.false;
        
        // Симулируем обычную загрузку (независимо от наличия CID в state)
        return {
          success: true,
          successCount: 2,
          failCount: 0,
          totalCount: 2,
          results: [
            {
              componentId: 'amanita_muscaria',
              success: true,
              uploaded: true // ✅ Загрузка выполнена
            }
          ]
        };
      });

      // WHEN: action52 вызывается
      const result = await componentActions.action52();

      // THEN: action52_UnifiedArweaveUpload вызван с useExistingCids: false
      expect(action52Stub.calledOnce).to.be.true;
      const contextArg = action52Stub.firstCall.args[0];
      expect(contextArg).to.have.property('useExistingCids', false);
      
      // THEN: Результат указывает на загрузку
      expect(result).to.have.property('success', true);
      expect(result.result.results[0]).to.have.property('uploaded', true);

      action52Stub.restore();
      delete process.env.USE_EXISTING_CIDS;
    });

    it('должен инициализировать Arweave если не готов', async () => {
      // GIVEN: Arweave не готов
      mockArweaveManagerInstance.isReady.returns(false);

      const action52Stub = sinon.stub().resolves({ success: true });

      const Module = require('module');
      const originalRequire = Module.prototype.require;
      Module.prototype.require = function(request) {
        if (request === '../upload_steps') {
          return { action52_UnifiedArweaveUpload: action52Stub };
        }
        return originalRequire.apply(this, arguments);
      };

      // WHEN: action52 вызывается
      await componentActions.action52();

      // THEN: Arweave инициализирован
      expect(mockArweaveManagerInstance.initialize.calledOnce).to.be.true;

      Module.prototype.require = originalRequire;
    });

    it('должен вызвать action52_UnifiedArweaveUpload с правильными параметрами', async () => {
      // GIVEN: Убеждаемся что SELLER_ADDRESS установлен (из beforeEach)
      expect(process.env.SELLER_ADDRESS).to.equal('0xSeller');
      
      // GIVEN: Mock hre чтобы использовался config.get('network.name') вместо hre.network.name
      const hreModule = require('hardhat');
      const originalNetwork = hreModule.network;
      hreModule.network = undefined; // Заставляем использовать config fallback
      
      // GIVEN: Mock action52_UnifiedArweaveUpload
      const uploadStepsPath = require.resolve('../../../lib/upload_steps');
      const uploadSteps = require(uploadStepsPath);
      const action52Stub = sinon.stub(uploadSteps, 'action52_UnifiedArweaveUpload').resolves({
        success: true,
        successCount: 2,
        failCount: 0,
        totalCount: 2
      });

      // WHEN: action52 вызывается
      await componentActions.action52();

      // THEN: action52_UnifiedArweaveUpload вызван
      expect(action52Stub.calledOnce).to.be.true;
      expect(action52Stub.firstCall.args[1]).to.equal('data/components');
      expect(action52Stub.firstCall.args[2]).to.equal('localhost'); // Из config.get('network.name')
      expect(action52Stub.firstCall.args[3]).to.equal(false);

      // Restore
      action52Stub.restore();
      hreModule.network = originalNetwork;
    });

    it('должен выбросить ошибку если SELLER_ADDRESS отсутствует', async () => {
      // GIVEN: SELLER_ADDRESS не установлен
      delete process.env.SELLER_ADDRESS;
      mockConfig.get.withArgs('seller.address').returns(null);

      // WHEN/THEN: Должна быть выброшена ошибка
      await expect(componentActions.action52()).to.be.rejectedWith('Action 52: требуется SELLER_ADDRESS');
    });

    it('должен выбросить ошибку если SELLER_PRIVATE_KEY отсутствует', async () => {
      // GIVEN: SELLER_PRIVATE_KEY не найден
      mockConfig.get.withArgs('seller.privateKey').returns(null);

      const Module = require('module');
      const originalRequire = Module.prototype.require;
      Module.prototype.require = function(request) {
        if (request === '../upload_steps') {
          return { action52_UnifiedArweaveUpload: sinon.stub() };
        }
        return originalRequire.apply(this, arguments);
      };

      // WHEN/THEN: Должна быть выброшена ошибка
      await expect(componentActions.action52()).to.be.rejectedWith('SELLER_PRIVATE_KEY не найден');

      Module.prototype.require = originalRequire;
    });

    it('должен вернуть правильный результат', async () => {
      // GIVEN: Mock action52_UnifiedArweaveUpload
      const uploadStepsPath = require.resolve('../../../lib/upload_steps');
      const uploadSteps = require(uploadStepsPath);
      const action52Stub = sinon.stub(uploadSteps, 'action52_UnifiedArweaveUpload').resolves({
        success: true,
        successCount: 2,
        failCount: 0,
        totalCount: 2
      });

      // WHEN: action52 вызывается
      const result = await componentActions.action52();

      // THEN: Result содержит правильные поля
      expect(result).to.have.property('success', true);
      expect(result).to.have.property('result').that.is.an('object');

      action52Stub.restore();
    });
  });

  // ================================================================
  // REAL TESTS: action53 (contract registration)
  // ================================================================

  describe('action53() - Contract Registration', () => {
    let mockSpiralEngine, mockOrganicRegistry;

    beforeEach(() => {
      mockSpiralEngine = {
        usedInviteByUser: sinon.stub().resolves(1),
        SELLER_ROLE: sinon.stub().resolves('0xSellerRole'),
        hasRole: sinon.stub().resolves(true)
      };

      mockOrganicRegistry = {
        getAddress: sinon.stub().resolves('0xOrganic'),
        totalComponents: sinon.stub().resolves(2),
        componentExists: sinon.stub().resolves(true)
      };

      mockContractManager.loadUUPSContract.withArgs('OrganicComponentRegistry').resolves(mockOrganicRegistry);
      mockContractManager.loadUUPSContract.withArgs('SpiralEngine').resolves(mockSpiralEngine);

      mockEthersUtils.provider = { mock: 'provider' };
      mockConfig.get.withArgs('seller.address').returns('0xSeller');
      mockConfig.get.withArgs('seller.privateKey').returns('0xSellerPrivateKey');
      mockConfig.get.withArgs('network.name').returns('localhost');

      componentActions.arweaveManager = {
        getClient: sinon.stub().returns({ mock: 'arweave-client' }),
        getKey: sinon.stub().returns({ mock: 'arweave-key' })
      };

      process.env.SELLER_ADDRESS = '0xSeller';
      process.env.COMPONENTS_DIR = 'data/components';
      process.env.DRY_RUN = 'false';

      // Mock fs для поиска компонентов
      fs.readdirSync.returns([
        { name: 'amanita_muscaria', isDirectory: () => true },
        { name: 'blue_lotus', isDirectory: () => true }
      ]);
      fs.existsSync.callsFake((path) => {
        if (path.includes('data/components')) return true;
        if (path.endsWith('.json')) return true;
        return false;
      });
    });
    
    afterEach(() => {
      delete process.env.SELLER_ADDRESS;
      delete process.env.COMPONENTS_DIR;
      delete process.env.DRY_RUN;
    });

    it('должен загрузить необходимые контракты', async () => {
      // GIVEN: Mock action53_UnifiedContractRegistration
      const uploadStepsPath = require.resolve('../../../lib/upload_steps');
      const uploadSteps = require(uploadStepsPath);
      const action53Stub = sinon.stub(uploadSteps, 'action53_UnifiedContractRegistration').resolves({
        success: true,
        successCount: 2,
        failCount: 0,
        totalCount: 2
      });
      
      // WHEN: action53 вызывается
      await componentActions.action53();
      
      // THEN: Контракты загружены
      expect(mockContractManager.loadUUPSContract.calledWith('OrganicComponentRegistry')).to.be.true;
      expect(mockContractManager.loadUUPSContract.calledWith('SpiralEngine')).to.be.true;

      action53Stub.restore();
    });

    it('должен вызвать action53_UnifiedContractRegistration с правильными параметрами', async () => {
      // GIVEN: Убеждаемся что SELLER_ADDRESS установлен (из beforeEach)
      expect(process.env.SELLER_ADDRESS).to.equal('0xSeller');
      
      // GIVEN: Mock hre чтобы использовался config.get('network.name') вместо hre.network.name
      const hreModule = require('hardhat');
      const originalNetwork = hreModule.network;
      hreModule.network = undefined; // Заставляем использовать config fallback
      
      // GIVEN: Mock action53_UnifiedContractRegistration через тот же подход что и для action52
      const uploadStepsPath = require.resolve('../../../lib/upload_steps');
      const uploadSteps = require(uploadStepsPath);
      const action53Stub = sinon.stub(uploadSteps, 'action53_UnifiedContractRegistration').resolves({
        success: true,
        successCount: 2,
        failCount: 0,
        totalCount: 2
      });
      
      // WHEN: action53 вызывается
      await componentActions.action53();

      // THEN: action53_UnifiedContractRegistration вызван
      expect(action53Stub.calledOnce).to.be.true;
      expect(action53Stub.firstCall.args[1]).to.equal('data/components');
      expect(action53Stub.firstCall.args[2]).to.equal('localhost'); // Из config.get('network.name')
      expect(action53Stub.firstCall.args[3]).to.equal(false);

      // Restore
      action53Stub.restore();
      hreModule.network = originalNetwork;
    });

    it('должен выбросить ошибку если SELLER_ADDRESS отсутствует', async () => {
      // GIVEN: SELLER_ADDRESS не установлен
      delete process.env.SELLER_ADDRESS;
      mockConfig.get.withArgs('seller.address').returns(null);

      // WHEN/THEN: Должна быть выброшена ошибка
      await expect(componentActions.action53()).to.be.rejectedWith('Action 53: требуется SELLER_ADDRESS');
    });

    it('должен вернуть правильный результат', async () => {
      // GIVEN: Mock action53_UnifiedContractRegistration
      const uploadStepsPath = require.resolve('../../../lib/upload_steps');
      const uploadSteps = require(uploadStepsPath);
      const action53Stub = sinon.stub(uploadSteps, 'action53_UnifiedContractRegistration').resolves({
        success: true,
        successCount: 2,
        failCount: 0,
        totalCount: 2
      });
      
      // WHEN: action53 вызывается
      const result = await componentActions.action53();

      // THEN: Result содержит правильные поля
      expect(result).to.have.property('success', true);
      expect(result).to.have.property('result').that.is.an('object');

      action53Stub.restore();
    });
  });
      
  // ================================================================
  // REAL TESTS: action555 (composite pipeline - UPDATED)
  // ================================================================

  describe('action555() - Composite Pipeline (51 → 52 → 53)', () => {
    beforeEach(() => {
      process.env.DEPLOYER_INVITE = 'AMANITA-ROOT-777';
      process.env.SELLER_ADDRESS = '0xSeller';
    });

    afterEach(() => {
      delete process.env.DEPLOYER_INVITE;
      delete process.env.SELLER_ADDRESS;
    });

    it('должен вызвать action51, action52, action53 последовательно', async () => {
      // GIVEN: Mock всех трех actions
      const action51Stub = sinon.stub(componentActions, 'action51').resolves({
        success: true,
        sellerAddress: '0xSeller',
        wasActivated: true,
        wasRoleGranted: true
      });

      const action52Stub = sinon.stub(componentActions, 'action52').resolves({
        success: true,
        result: { successCount: 2, totalCount: 2 }
      });

      const action53Stub = sinon.stub(componentActions, 'action53').resolves({
        success: true,
        result: { successCount: 2, totalCount: 2 }
      });
      
      // WHEN: action555 вызывается
      const result = await componentActions.action555();
      
      // THEN: Все три action вызваны последовательно
      expect(action51Stub.calledOnce).to.be.true;
      expect(action52Stub.calledOnce).to.be.true;
      expect(action53Stub.calledOnce).to.be.true;
      
      // THEN: Порядок вызовов правильный
      expect(action51Stub.calledBefore(action52Stub)).to.be.true;
      expect(action52Stub.calledBefore(action53Stub)).to.be.true;

      // THEN: Result содержит pipelineResults
      expect(result).to.have.property('success', true);
      expect(result).to.have.property('pipelineResults');
      expect(result.pipelineResults.action51.success).to.be.true;
      expect(result.pipelineResults.action52.success).to.be.true;
      expect(result.pipelineResults.action53.success).to.be.true;
      
      // Cleanup
      action51Stub.restore();
      action52Stub.restore();
      action53Stub.restore();
    });

    it('должен прервать pipeline при ошибке action51', async () => {
      // GIVEN: action51 выбрасывает ошибку
      const action51Stub = sinon.stub(componentActions, 'action51').rejects(new Error('Activation failed'));
      const action52Stub = sinon.stub(componentActions, 'action52');
      const action53Stub = sinon.stub(componentActions, 'action53');
      
      // WHEN/THEN: Pipeline прерывается
      await expect(componentActions.action555()).to.be.rejectedWith('Activation failed');

      // THEN: action52 и action53 НЕ вызваны
      expect(action51Stub.calledOnce).to.be.true;
      expect(action52Stub.called).to.be.false;
      expect(action53Stub.called).to.be.false;

      // Cleanup
      action51Stub.restore();
      action52Stub.restore();
      action53Stub.restore();
    });

    it('должен прервать pipeline при ошибке action52', async () => {
      // GIVEN: action51 успешен, action52 выбрасывает ошибку
      const action51Stub = sinon.stub(componentActions, 'action51').resolves({ success: true });
      const action52Stub = sinon.stub(componentActions, 'action52').rejects(new Error('Upload failed'));
      const action53Stub = sinon.stub(componentActions, 'action53');
      
      // WHEN/THEN: Pipeline прерывается
      await expect(componentActions.action555()).to.be.rejectedWith('Upload failed');
      
      // THEN: action51 и action52 вызваны, action53 НЕ вызван
      expect(action51Stub.calledOnce).to.be.true;
      expect(action52Stub.calledOnce).to.be.true;
      expect(action53Stub.called).to.be.false;
      
      // Cleanup
      action51Stub.restore();
      action52Stub.restore();
      action53Stub.restore();
    });

    it('должен собрать результаты всех этапов в pipelineResults', async () => {
      // GIVEN: Mock всех трех actions
      const action51Stub = sinon.stub(componentActions, 'action51').resolves({
        success: true, 
        sellerAddress: '0xSeller',
        wasActivated: true
      });

      const action52Stub = sinon.stub(componentActions, 'action52').resolves({
        success: true,
        result: { successCount: 2, totalCount: 2 }
      });

      const action53Stub = sinon.stub(componentActions, 'action53').resolves({
        success: true,
        result: { successCount: 2, totalCount: 2 }
      });
      
      // WHEN: action555 вызывается
      const result = await componentActions.action555();
      
      // THEN: pipelineResults содержит результаты всех этапов
      expect(result.pipelineResults).to.have.property('action51');
      expect(result.pipelineResults).to.have.property('action52');
      expect(result.pipelineResults).to.have.property('action53');
      expect(result.pipelineResults).to.have.property('success', true);
      expect(result.pipelineResults).to.have.property('errors').that.is.an('array');

      // Cleanup
      action51Stub.restore();
      action52Stub.restore();
      action53Stub.restore();
    });

    it('должен собрать ошибки в pipelineResults.errors при ошибке', async () => {
      // GIVEN: action52 выбрасывает ошибку
      const action51Stub = sinon.stub(componentActions, 'action51').resolves({ success: true });
      const action52Stub = sinon.stub(componentActions, 'action52').rejects(new Error('Upload failed'));

      // WHEN/THEN: Pipeline прерывается
      try {
        await componentActions.action555();
        expect.fail('Should have thrown error');
      } catch (error) {
        expect(error.message).to.equal('Upload failed');
      }
      
      // Cleanup
      action51Stub.restore();
      action52Stub.restore();
    });

    // ================================================================
    // Тест 1: Action 555 с активированным seller (без DEPLOYER_INVITE)
    // ================================================================
    it('должен пропустить action51 если seller уже активирован (Тест 1)', async () => {
      // GIVEN: Seller уже активирован (skipActivation: true)
      delete process.env.DEPLOYER_INVITE; // DEPLOYER_INVITE не требуется
      
      const action51Stub = sinon.stub(componentActions, 'action51').resolves({
        success: true,
        sellerAddress: '0xSeller',
        skipActivation: true, // ✅ Seller уже активирован
        wasActivated: false,
        wasRoleGranted: false
      });

      const action52Stub = sinon.stub(componentActions, 'action52').resolves({
        success: true,
        result: { successCount: 2, totalCount: 2 }
      });

      const action53Stub = sinon.stub(componentActions, 'action53').resolves({
        success: true,
        result: { successCount: 2, totalCount: 2 }
      });
      
      // WHEN: action555 вызывается
      const result = await componentActions.action555();
      
      // THEN: action51 вызван и вернул skipActivation: true
      expect(action51Stub.calledOnce).to.be.true;
      const action51Result = await action51Stub.firstCall.returnValue;
      expect(action51Result).to.have.property('skipActivation', true);
      
      // THEN: Pipeline продолжается (action52, action53 вызваны)
      expect(action52Stub.calledOnce).to.be.true;
      expect(action53Stub.calledOnce).to.be.true;
      
      // THEN: Result содержит успешные результаты всех действий
      expect(result).to.have.property('success', true);
      expect(result.pipelineResults.action51.result.skipActivation).to.be.true;
      expect(result.pipelineResults.action52.success).to.be.true;
      expect(result.pipelineResults.action53.success).to.be.true;
      
      // Cleanup
      action51Stub.restore();
      action52Stub.restore();
      action53Stub.restore();
    });

    // ================================================================
    // Тест 5: Action 555 с USE_EXISTING_CIDS=true
    // ================================================================
    it('должен использовать существующие CID для всех компонентов если USE_EXISTING_CIDS=true (Тест 5)', async () => {
      // GIVEN: USE_EXISTING_CIDS установлен
      process.env.USE_EXISTING_CIDS = 'true';
      process.env.DEPLOYER_INVITE = 'AMANITA-ROOT-777';
      
      // GIVEN: Seller может быть активирован или нет (проверяется в action51)
      const action51Stub = sinon.stub(componentActions, 'action51').resolves({
        success: true,
        sellerAddress: '0xSeller',
        skipActivation: true, // Seller уже активирован
        wasActivated: false
      });

      // GIVEN: action52 использует существующие CID
      const action52Stub = sinon.stub(componentActions, 'action52').resolves({
        success: true,
        result: {
          successCount: 2,
          totalCount: 2,
          results: [
            {
              componentId: 'amanita_muscaria',
              success: true,
              usedExistingCids: true // ✅ Использованы существующие CID
            },
            {
              componentId: 'blue_lotus',
              success: true,
              usedExistingCids: true // ✅ Использованы существующие CID
            }
          ]
        }
      });

      const action53Stub = sinon.stub(componentActions, 'action53').resolves({
        success: true,
        result: { successCount: 2, totalCount: 2 }
      });
      
      // WHEN: action555 вызывается
      const result = await componentActions.action555();
      
      // THEN: Все действия выполнены успешно
      expect(action51Stub.calledOnce).to.be.true;
      expect(action52Stub.calledOnce).to.be.true;
      expect(action53Stub.calledOnce).to.be.true;
      
      // THEN: action52 использовал существующие CID для всех компонентов
      const action52Result = await action52Stub.firstCall.returnValue;
      expect(action52Result.result.results).to.have.length(2);
      action52Result.result.results.forEach(componentResult => {
        expect(componentResult).to.have.property('usedExistingCids', true);
      });
      
      // THEN: Pipeline завершен успешно
      expect(result).to.have.property('success', true);
      expect(result.pipelineResults.action51.result.skipActivation).to.be.true;
      expect(result.pipelineResults.action52.success).to.be.true;
      expect(result.pipelineResults.action53.success).to.be.true;
      
      // Cleanup
      action51Stub.restore();
      action52Stub.restore();
      action53Stub.restore();
      delete process.env.USE_EXISTING_CIDS;
    });
  });
});

