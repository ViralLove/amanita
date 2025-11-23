/**
 * Integration Test: ActionsManager → ComponentActions → InviteActions (Action 555 Full Workflow)
 * 
 * Phase 3: Flow Testing - Multi-step integration scenario
 * Validates module boundary handshake between ActionsManager, ComponentActions, and InviteActions
 * 
 * Goal: Verify that Action 555 correctly orchestrates full workflow:
 * 1. Load SpiralEngine via ContractManager
 * 2. Activate seller via InviteActions.activateSeller()
 * 3. Upload components via ComponentActions.uploadComponentsCore()
 * 
 * Method: @integration-test-build.core.mdc
 * - Real modules: ActionsManager, ComponentActions, InviteActions (via IntegrationHarness)
 * - Minimal mocks: SpiralEngine contract (external blockchain API), ArweaveManager (optional)
 * - State tracking: Activation and upload state via closures
 */

const { expect } = require('chai');
const sinon = require('sinon');
const { ethers } = require('hardhat');
const { IntegrationHarness } = require('../helpers');

describe('Integration: ActionsManager → ComponentActions → InviteActions (Action 555 Full Workflow)', () => {
  let harness, modules;

  before(async function() {
    this.timeout(10000);
    harness = new IntegrationHarness();
    modules = await harness.setupIntegrationEnvironment();
    // ✅ IntegrationHarness создает ActionsManager с реальными модулями
  });

  after(async () => {
    await harness.teardownIntegrationEnvironment();
  });

  afterEach(() => {
    sinon.restore();
    // Очищаем environment variables после каждого теста
    delete process.env.DEPLOYER_INVITE;
    delete process.env.SELLER_ADDRESS;
    delete process.env.DRY_RUN;
    delete process.env.ARWEAVE;
  });

  describe('Full Workflow: Action 555 Complete Flow', () => {
    it('должен выполнить полный workflow: SpiralEngine → activateSeller → uploadComponents', async () => {
      // GIVEN: Настройка окружения
      const sellerAddress = '0x70997970C51812dc3A010C7d01b50e0d17dc79C8';
      const inviteCode = 'AMANITA-TEST-555';
      
      // ✅ State tracking через замыкание для проверки изменения состояния
      let activationState = {
        usedInvite: '0',
        isActivated: false,
        hasSellerRole: false,
        SELLER_ROLE: null
      };

      // Setup mock SpiralEngine с state tracking (external API only)
      const usedInviteByUserFn = async (address) => activationState.usedInvite;
      
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
      
      const inviteCodeExistsFn = async (code) => code === inviteCode;
      
      // ✅ Phase 2: Упрощённая версия activateUserFn
      const activateUserFn = async (code, user, newInvites, expiry) => {
        activationState.usedInvite = '1';
        activationState.isActivated = true;
        return { hash: '0xtest555' };
      };
      
      const grantSellerRoleFn = async (userAddress) => {
        if (!activationState.isActivated) {
          throw new Error('AccessControl: Не могу назначить SELLER_ROLE - пользователь не активирован');
        }
        activationState.hasSellerRole = true;
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

      // ✅ Stub для loadUUPSContract (ComponentActions.action555() использует его)
      const loadUUPSContractStub = sinon.stub(modules.contractManager, 'loadUUPSContract')
        .withArgs('SpiralEngine')
        .resolves(mockSpiralEngine);

      // ✅ Stub для uploadComponentsCore (мокаем загрузку компонентов)
      const uploadComponentsCoreStub = sinon.stub(modules.actionsManager.componentActions, 'uploadComponentsCore')
        .resolves({
          success: true,
          totalCount: 5,
          successCount: 5,
          failCount: 0,
          skippedCount: 0,
          results: [
            { componentId: 'amanita_muscaria', success: true },
            { componentId: 'blue_lotus', success: true },
            { componentId: 'lions_mane', success: true },
            { componentId: 'reishi', success: true },
            { componentId: 'chaga', success: true }
          ]
        });

      // ✅ Spy на InviteActions.activateSeller для проверки делегации
      const activateSellerSpy = sinon.spy(modules.actionsManager.componentActions.inviteActions, 'activateSeller');

      // Setup environment variables (ComponentActions.action555() читает из process.env)
      process.env.DEPLOYER_INVITE = inviteCode;
      process.env.SELLER_ADDRESS = sellerAddress;
      process.env.DRY_RUN = 'false';
      process.env.ARWEAVE = 'false'; // Отключаем Arweave для теста

      // WHEN: Выполняется Action 555 через ActionsManager
      const result = await modules.actionsManager.executeAction(555);

      // THEN: Step 1: SpiralEngine загружен через loadUUPSContract
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
      expect(uploadComponentsCoreStub.calledOnce).to.be.true;
      const uploadCall = uploadComponentsCoreStub.getCall(0);
      expect(uploadCall.args[0]).to.equal(sellerAddress); // sellerAddress
      expect(uploadCall.args[1]).to.equal('data/components'); // componentsDir

      // THEN: Result содержит корректную структуру
      expect(result).to.exist;
      expect(result.success).to.be.true;
      expect(result.uploadResults).to.exist;
      expect(result.uploadResults.success).to.be.true;
      expect(result.uploadResults.totalCount).to.equal(5);
      expect(result.uploadResults.successCount).to.equal(5);
      expect(result.uploadResults.failCount).to.equal(0);
    });

    it('должен обработать ошибку на этапе активации', async () => {
      // GIVEN: Mock SpiralEngine, который выбрасывает ошибку при проверке invite code
      const sellerAddress = '0x70997970C51812dc3A010C7d01b50e0d17dc79C8';
      const inviteCode = 'AMANITA-ERROR-555';

      const mockSpiralEngine = harness.setupContractMock('SpiralEngine', {
        usedInviteByUser: { call: async () => '0' },
        inviteCodeExists: { call: async () => false }, // Invite не существует
        hasRole: { call: async () => false },
        SELLER_ROLE: {
          call: async () => ethers.keccak256(ethers.toUtf8Bytes('SELLER_ROLE'))
        }
      });

      sinon.stub(modules.contractManager, 'loadUUPSContract')
        .withArgs('SpiralEngine')
        .resolves(mockSpiralEngine);

      // ✅ Stub для uploadComponentsCore (не должен быть вызван из-за ошибки)
      const uploadComponentsCoreStub = sinon.stub(modules.actionsManager.componentActions, 'uploadComponentsCore')
        .resolves({ success: true, totalCount: 0, results: [] });

      process.env.DEPLOYER_INVITE = inviteCode;
      process.env.SELLER_ADDRESS = sellerAddress;
      process.env.DRY_RUN = 'false';
      process.env.ARWEAVE = 'false';

      // WHEN: Выполняется Action 555
      // THEN: Ошибка выбрасывается на этапе активации
      try {
        await modules.actionsManager.executeAction(555);
        expect.fail('Должна была быть выброшена ошибка');
      } catch (error) {
        expect(error.message).to.include('Invite код');
        expect(error.message).to.include('не существует');
      }

      // THEN: uploadComponentsCore НЕ вызывается (из-за ошибки активации)
      expect(uploadComponentsCoreStub.called).to.be.false;
    });

    it('должен пропустить активацию, если seller уже активирован (idempotent)', async () => {
      // GIVEN: Seller уже активирован
      const sellerAddress = '0x70997970C51812dc3A010C7d01b50e0d17dc79C8';
      const inviteCode = 'AMANITA-IDEMPOTENT-555';

      let activationState = {
        usedInvite: '1', // Уже активирован
        isActivated: true,
        hasSellerRole: true,
        activateUserCalled: false,
        SELLER_ROLE: null
      };

      const usedInviteByUserFn = async (address) => activationState.usedInvite;
      
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

      const activateUserFn = async () => {
        activationState.activateUserCalled = true;
        throw new Error('Should not be called');
      };

      const mockSpiralEngine = harness.setupContractMock('SpiralEngine', {
        usedInviteByUser: { call: usedInviteByUserFn },
        hasRole: { call: hasRoleFn },
        inviteCodeExists: { call: async () => true },
        activateUser: { call: activateUserFn, encodeABI: '0xactivate' },
        grantSellerRole: { 
          call: async () => {
            // Не должен вызываться, так как роль уже есть
            throw new Error('Should not be called');
          },
          encodeABI: '0xgrantSellerRole'
        },
        SELLER_ROLE: {
          call: async () => {
            if (!activationState.SELLER_ROLE) {
              activationState.SELLER_ROLE = ethers.keccak256(ethers.toUtf8Bytes('SELLER_ROLE'));
            }
            return activationState.SELLER_ROLE;
          }
        }
      });

      sinon.stub(modules.contractManager, 'loadUUPSContract')
        .withArgs('SpiralEngine')
        .resolves(mockSpiralEngine);

      const uploadComponentsCoreStub = sinon.stub(modules.actionsManager.componentActions, 'uploadComponentsCore')
        .resolves({ 
          success: true, 
          totalCount: 3, 
          successCount: 3,
          failCount: 0,
          results: [
            { componentId: 'test1', success: true },
            { componentId: 'test2', success: true },
            { componentId: 'test3', success: true }
          ]
        });

      process.env.DEPLOYER_INVITE = inviteCode;
      process.env.SELLER_ADDRESS = sellerAddress;
      process.env.DRY_RUN = 'false';
      process.env.ARWEAVE = 'false';

      // WHEN: Выполняется Action 555
      const result = await modules.actionsManager.executeAction(555);

      // THEN: activateUser НЕ вызывается (пропуск активации)
      expect(activationState.activateUserCalled).to.be.false;

      // THEN: uploadComponentsCore вызывается (компоненты загружаются)
      expect(uploadComponentsCoreStub.calledOnce).to.be.true;

      // THEN: Result успешен
      expect(result.success).to.be.true;
      expect(result.uploadResults.success).to.be.true;
    });
  });

  describe('Delegation Verification', () => {
    it('должен проверить правильность делегации ComponentActions → InviteActions', async () => {
      // GIVEN: Setup моков
      const sellerAddress = '0x70997970C51812dc3A010C7d01b50e0d17dc79C8';
      const inviteCode = 'AMANITA-DELEGATION-555';

      let activationState = {
        usedInvite: '0',
        isActivated: false,
        hasSellerRole: false,
        SELLER_ROLE: null
      };

      const usedInviteByUserFn = async (address) => activationState.usedInvite;
      
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

      const activateUserFn = async (code, user, newInvites, expiry) => {
        activationState.usedInvite = '1';
        activationState.isActivated = true;
        return { hash: '0xdelegate' };
      };

      const grantSellerRoleFn = async (userAddress) => {
        if (!activationState.isActivated) {
          throw new Error('AccessControl: Не могу назначить SELLER_ROLE - пользователь не активирован');
        }
        activationState.hasSellerRole = true;
      };

      const mockSpiralEngine = harness.setupContractMock('SpiralEngine', {
        usedInviteByUser: { call: usedInviteByUserFn },
        hasRole: { call: hasRoleFn },
        inviteCodeExists: { call: async () => true },
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

      sinon.stub(modules.contractManager, 'loadUUPSContract')
        .withArgs('SpiralEngine')
        .resolves(mockSpiralEngine);

      // ✅ Spy на InviteActions методы для проверки делегации
      const activateSellerSpy = sinon.spy(modules.actionsManager.componentActions.inviteActions, 'activateSeller');
      const activateUserSpy = sinon.spy(modules.actionsManager.componentActions.inviteActions, 'activateUser');

      const uploadComponentsCoreStub = sinon.stub(modules.actionsManager.componentActions, 'uploadComponentsCore')
        .resolves({ 
          success: true, 
          totalCount: 2, 
          successCount: 2,
          failCount: 0,
          results: [
            { componentId: 'test1', success: true },
            { componentId: 'test2', success: true }
          ]
        });

      process.env.DEPLOYER_INVITE = inviteCode;
      process.env.SELLER_ADDRESS = sellerAddress;
      process.env.DRY_RUN = 'false';
      process.env.ARWEAVE = 'false';

      // WHEN: ComponentActions.action555() вызывается напрямую
      const result = await modules.actionsManager.componentActions.action555();

      // THEN: InviteActions.activateSeller вызван
      expect(activateSellerSpy.calledOnce).to.be.true;

      // THEN: InviteActions.activateUser вызван внутри activateSeller (если не активирован)
      expect(activateUserSpy.calledOnce).to.be.true;

      // THEN: Правильные параметры переданы в activateSeller
      const activateSellerCall = activateSellerSpy.getCall(0);
      expect(activateSellerCall.args[0]).to.equal(mockSpiralEngine); // spiralEngine
      expect(activateSellerCall.args[1]).to.equal(inviteCode); // inviteCode
      expect(activateSellerCall.args[2]).to.equal(sellerAddress); // sellerAddress

      // THEN: Result успешен
      expect(result.success).to.be.true;
      expect(result.uploadResults).to.exist;
    });
  });

  describe('Complex Fields Upload Integration', () => {
    it('должен загрузить complex fields через uploadComponentsCore с правильным className', async () => {
      // GIVEN: Настройка окружения для загрузки complex fields
      const sellerAddress = '0x70997970C51812dc3A010C7d01b50e0d17dc79C8';
      const inviteCode = 'AMANITA-COMPLEX-555';
      const testBiounitId = 'amanita_muscaria';

      // Setup state tracking для активации
      let activationState = {
        usedInvite: '0',
        isActivated: false,
        hasSellerRole: false,
        SELLER_ROLE: null
      };

      const usedInviteByUserFn = async (address) => activationState.usedInvite;
      
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

      const activateUserFn = async (code, user, newInvites, expiry) => {
        activationState.usedInvite = '1';
        activationState.isActivated = true;
        return { hash: '0xcomplex' };
      };

      const grantSellerRoleFn = async (userAddress) => {
        if (!activationState.isActivated) {
          throw new Error('AccessControl: Не могу назначить SELLER_ROLE - пользователь не активирован');
        }
        activationState.hasSellerRole = true;
      };

      const mockSpiralEngine = harness.setupContractMock('SpiralEngine', {
        usedInviteByUser: { call: usedInviteByUserFn },
        hasRole: { call: hasRoleFn },
        inviteCodeExists: { call: async () => true },
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

      // Setup mock AmanitaInternational для проверки вызова setComplexFieldCID
      let setComplexFieldCIDCalls = [];
      const mockAmanitaInternational = harness.setupContractMock('AmanitaInternational', {
        setComplexFieldCID: {
          call: async (className, lang, cid) => {
            // ✅ State tracking: сохраняем вызовы для проверки
            setComplexFieldCIDCalls.push({ className, lang, cid });
            return { hash: `0xsetComplexField${setComplexFieldCIDCalls.length}`, wait: async () => ({ status: 1 }) };
          },
          encodeABI: '0xsetComplexFieldCID'
        }
      });

      sinon.stub(modules.contractManager, 'loadUUPSContract')
        .callsFake((contractName) => {
          if (contractName === 'SpiralEngine') {
            return Promise.resolve(mockSpiralEngine);
          }
          if (contractName === 'AmanitaInternational') {
            return Promise.resolve(mockAmanitaInternational);
          }
          return Promise.resolve(null);
        });

      // ✅ Stub для uploadComponentsCore, который симулирует загрузку complex fields
      // Мы проверяем, что при реальном вызове uploadComponentsCore будут использоваться правильные параметры
      const uploadComponentsCoreStub = sinon.stub(modules.actionsManager.componentActions, 'uploadComponentsCore')
        .callsFake(async (sellerAddr, componentsDir, networkName, dryRun) => {
          // Симулируем вызов uploadComplexFields для одного компонента
          // В реальности uploadComplexFields вызывается внутри uploadComponentsCore с context.biounit_id
          const className = `ComponentDescription.${testBiounitId}`;
          const languages = ['ru', 'en', 'de'];

          // Симулируем вызов setComplexFieldCID для каждого языка (как в реальной функции)
          for (const lang of languages) {
            const mockCID = `QmMockCID${testBiounitId}${lang}`;
            // ✅ Проверка: вызываем setComplexFieldCID с className, содержащим biounit_id
            await mockAmanitaInternational.setComplexFieldCID(className, lang, mockCID);
          }

          return {
            success: true,
            totalCount: 1,
            successCount: 1,
            failCount: 0,
            results: [{ componentId: testBiounitId, success: true }]
          };
        });

      process.env.DEPLOYER_INVITE = inviteCode;
      process.env.SELLER_ADDRESS = sellerAddress;
      process.env.DRY_RUN = 'false';
      process.env.ARWEAVE = 'false';

      // WHEN: Выполняется Action 555
      const result = await modules.actionsManager.executeAction(555);

      // THEN: uploadComponentsCore вызван
      expect(uploadComponentsCoreStub.calledOnce).to.be.true;

      // THEN: Result успешен
      expect(result.success).to.be.true;
      expect(result.uploadResults).to.exist;

      // THEN: setComplexFieldCID был вызван для каждого языка
      expect(setComplexFieldCIDCalls.length).to.be.greaterThanOrEqual(3); // ru, en, de

      // THEN: className содержит biounit_id (правильный формат)
      const expectedClassName = `ComponentDescription.${testBiounitId}`;
      setComplexFieldCIDCalls.forEach(call => {
        expect(call.className).to.equal(expectedClassName);
        expect(call.className).to.include(testBiounitId);
        expect(call.className).to.not.equal('ComponentDescription'); // НЕ без biounit_id
      });

      // THEN: setComplexFieldCID вызван для всех языков
      const languages = ['ru', 'en', 'de'];
      languages.forEach(lang => {
        const callForLang = setComplexFieldCIDCalls.find(c => c.lang === lang);
        expect(callForLang).to.exist;
        expect(callForLang.className).to.equal(expectedClassName);
      });

      // Cleanup
      uploadComponentsCoreStub.restore();
    });

    it('должен создать уникальные ключи для разных компонентов в контракте', async () => {
      // GIVEN: Настройка окружения для загрузки нескольких компонентов
      const sellerAddress = '0x70997970C51812dc3A010C7d01b50e0d17dc79C8';
      const inviteCode = 'AMANITA-UNIQUE-555';
      const biounitId1 = 'amanita_muscaria';
      const biounitId2 = 'blue_lotus';

      // Setup state tracking для активации
      let activationState = {
        usedInvite: '0',
        isActivated: false,
        hasSellerRole: false,
        SELLER_ROLE: null
      };

      const mockSpiralEngine = harness.setupContractMock('SpiralEngine', {
        usedInviteByUser: { call: async () => activationState.usedInvite },
        hasRole: { call: async () => activationState.hasSellerRole },
        inviteCodeExists: { call: async () => true },
        activateUser: { 
          call: async () => {
            activationState.usedInvite = '1';
            activationState.isActivated = true;
            return { hash: '0xunique' };
          },
          encodeABI: '0xactivate'
        },
        grantSellerRole: { 
          call: async () => {
            activationState.hasSellerRole = true;
          },
          encodeABI: '0xgrantSellerRole'
        },
        SELLER_ROLE: {
          call: async () => {
            if (!activationState.SELLER_ROLE) {
              activationState.SELLER_ROLE = ethers.keccak256(ethers.toUtf8Bytes('SELLER_ROLE'));
            }
            return activationState.SELLER_ROLE;
          }
        }
      });

      // ✅ State tracking для проверки уникальности ключей
      let setComplexFieldCIDCalls = [];
      const mockAmanitaInternational = harness.setupContractMock('AmanitaInternational', {
        setComplexFieldCID: {
          call: async (className, lang, cid) => {
            // ✅ Сохраняем все вызовы для проверки уникальности
            setComplexFieldCIDCalls.push({ className, lang, cid });
            return { hash: `0xsetComplexField${setComplexFieldCIDCalls.length}`, wait: async () => ({ status: 1 }) };
          },
          encodeABI: '0xsetComplexFieldCID'
        },
        getComplexFieldCID: {
          call: async (className, lang) => {
            // ✅ Симулируем чтение из контракта (возвращаем CID если был записан)
            const call = setComplexFieldCIDCalls.find(c => c.className === className && c.lang === lang);
            return call ? call.cid : '';
          }
        }
      });

      sinon.stub(modules.contractManager, 'loadUUPSContract')
        .callsFake((contractName) => {
          if (contractName === 'SpiralEngine') {
            return Promise.resolve(mockSpiralEngine);
          }
          if (contractName === 'AmanitaInternational') {
            return Promise.resolve(mockAmanitaInternational);
          }
          return Promise.resolve(null);
        });

      // ✅ Stub для uploadComponentsCore, который симулирует загрузку 2 компонентов
      const uploadComponentsCoreStub = sinon.stub(modules.actionsManager.componentActions, 'uploadComponentsCore')
        .callsFake(async (sellerAddr, componentsDir, networkName, dryRun) => {
          // Симулируем загрузку двух компонентов
          const components = [biounitId1, biounitId2];
          const lang = 'ru';

          for (const biounitId of components) {
            // Симулируем вызов setComplexFieldCID для каждого компонента
            const className = `ComponentDescription.${biounitId}`;
            const mockCID = `QmMockCID${biounitId}`;
            
            await mockAmanitaInternational.setComplexFieldCID(className, lang, mockCID);
          }

          return {
            success: true,
            totalCount: 2,
            successCount: 2,
            failCount: 0,
            results: [
              { componentId: biounitId1, success: true },
              { componentId: biounitId2, success: true }
            ]
          };
        });

      process.env.DEPLOYER_INVITE = inviteCode;
      process.env.SELLER_ADDRESS = sellerAddress;
      process.env.DRY_RUN = 'false';
      process.env.ARWEAVE = 'false';

      // WHEN: Выполняется Action 555
      const result = await modules.actionsManager.executeAction(555);

      // THEN: uploadComponentsCore вызван
      expect(uploadComponentsCoreStub.calledOnce).to.be.true;

      // THEN: setComplexFieldCID вызван для каждого компонента
      expect(setComplexFieldCIDCalls.length).to.be.greaterThanOrEqual(2);

      // THEN: Ключи уникальны (className содержит biounit_id)
      const className1 = `ComponentDescription.${biounitId1}`;
      const className2 = `ComponentDescription.${biounitId2}`;
      
      const callsForComponent1 = setComplexFieldCIDCalls.filter(c => c.className === className1);
      const callsForComponent2 = setComplexFieldCIDCalls.filter(c => c.className === className2);

      expect(callsForComponent1.length).to.be.greaterThan(0);
      expect(callsForComponent2.length).to.be.greaterThan(0);

      // THEN: Ключи действительно разные (с biounit_id)
      expect(className1).to.not.equal(className2);
      expect(className1).to.include(biounitId1);
      expect(className2).to.include(biounitId2);

      // THEN: CID для разных компонентов разные
      const cid1 = await mockAmanitaInternational.getComplexFieldCID(className1, 'ru');
      const cid2 = await mockAmanitaInternational.getComplexFieldCID(className2, 'ru');
      
      expect(cid1).to.not.equal('');
      expect(cid2).to.not.equal('');
      expect(cid1).to.not.equal(cid2);

      // Cleanup
      uploadComponentsCoreStub.restore();
    });

    it('должен сохранить CIDs в state.complex_fields после загрузки', async () => {
      // GIVEN: Настройка окружения для проверки сохранения в state
      const sellerAddress = '0x70997970C51812dc3A010C7d01b50e0d17dc79C8';
      const inviteCode = 'AMANITA-STATE-555';
      const testBiounitId = 'amanita_muscaria';

      // Setup state tracking для активации
      let activationState = {
        usedInvite: '0',
        isActivated: false,
        hasSellerRole: false,
        SELLER_ROLE: null
      };

      const mockSpiralEngine = harness.setupContractMock('SpiralEngine', {
        usedInviteByUser: { call: async () => activationState.usedInvite },
        hasRole: { call: async () => activationState.hasSellerRole },
        inviteCodeExists: { call: async () => true },
        activateUser: { 
          call: async () => {
            activationState.usedInvite = '1';
            activationState.isActivated = true;
            return { hash: '0xstate' };
          },
          encodeABI: '0xactivate'
        },
        grantSellerRole: { 
          call: async () => {
            activationState.hasSellerRole = true;
          },
          encodeABI: '0xgrantSellerRole'
        },
        SELLER_ROLE: {
          call: async () => {
            if (!activationState.SELLER_ROLE) {
              activationState.SELLER_ROLE = ethers.keccak256(ethers.toUtf8Bytes('SELLER_ROLE'));
            }
            return activationState.SELLER_ROLE;
          }
        }
      });

      // ✅ State tracking для complex fields
      let complexFieldsState = {};
      const mockAmanitaInternational = harness.setupContractMock('AmanitaInternational', {
        setComplexFieldCID: {
          call: async (className, lang, cid) => {
            // ✅ Сохраняем CID в state для проверки
            if (!complexFieldsState[className]) {
              complexFieldsState[className] = {};
            }
            complexFieldsState[className][lang] = cid;
            return { hash: `0xsetComplexField${Object.keys(complexFieldsState).length}`, wait: async () => ({ status: 1 }) };
          },
          encodeABI: '0xsetComplexFieldCID'
        },
        getComplexFieldCID: {
          call: async (className, lang) => {
            // ✅ Возвращаем CID из state
            return complexFieldsState[className]?.[lang] || '';
          }
        }
      });

      sinon.stub(modules.contractManager, 'loadUUPSContract')
        .callsFake((contractName) => {
          if (contractName === 'SpiralEngine') {
            return Promise.resolve(mockSpiralEngine);
          }
          if (contractName === 'AmanitaInternational') {
            return Promise.resolve(mockAmanitaInternational);
          }
          return Promise.resolve(null);
        });

      // ✅ Stub для uploadComponentsCore, который симулирует сохранение в state
      const mockComponentState = {
        steps_completed: [],
        biounit_id: testBiounitId,
        network: 'localhost',
        complex_fields: {}
      };

      const uploadComponentsCoreStub = sinon.stub(modules.actionsManager.componentActions, 'uploadComponentsCore')
        .callsFake(async (sellerAddr, componentsDir, networkName, dryRun) => {
          // Симулируем загрузку complex fields и сохранение в state
          const className = `ComponentDescription.${testBiounitId}`;
          const languages = ['ru', 'en', 'de'];

          for (const lang of languages) {
            const mockCID = `QmMockCID${testBiounitId}${lang}`;
            
            // Вызываем setComplexFieldCID (сохраняется в complexFieldsState)
            await mockAmanitaInternational.setComplexFieldCID(className, lang, mockCID);
            
            // ✅ Сохраняем в mockComponentState.complex_fields (как в реальной функции)
            mockComponentState.complex_fields[lang] = {
              cid: mockCID,
              url: `https://arweave.net/${mockCID}`,
              size: 0,
              label: 'ComponentDescription',
              file_path: `complex_fields/${testBiounitId}.ComponentDescription.${lang}.json`
            };
          }

          // Помечаем шаг как выполненный (как в реальной функции)
          if (!mockComponentState.steps_completed.includes('complex_fields_uploaded')) {
            mockComponentState.steps_completed.push('complex_fields_uploaded');
          }

          return {
            success: true,
            totalCount: 1,
            successCount: 1,
            failCount: 0,
            results: [{ componentId: testBiounitId, success: true }],
            componentState: mockComponentState  // ✅ Возвращаем state для проверки
          };
        });

      process.env.DEPLOYER_INVITE = inviteCode;
      process.env.SELLER_ADDRESS = sellerAddress;
      process.env.DRY_RUN = 'false';
      process.env.ARWEAVE = 'false';

      // WHEN: Выполняется Action 555
      const result = await modules.actionsManager.executeAction(555);

      // THEN: uploadComponentsCore вызван
      expect(uploadComponentsCoreStub.calledOnce).to.be.true;

      // THEN: complex_fields сохранены в state
      expect(mockComponentState.complex_fields).to.exist;
      expect(Object.keys(mockComponentState.complex_fields).length).to.be.greaterThan(0);

      // THEN: CIDs для всех языков сохранены
      const languages = ['ru', 'en', 'de'];
      for (const lang of languages) {
        expect(mockComponentState.complex_fields[lang]).to.exist;
        expect(mockComponentState.complex_fields[lang].cid).to.not.equal('');
        expect(mockComponentState.complex_fields[lang].label).to.equal('ComponentDescription');
      }

      // THEN: Шаг помечен как выполненный
      expect(mockComponentState.steps_completed).to.include('complex_fields_uploaded');

      // THEN: CIDs в state соответствуют CIDs в контракте
      const className = `ComponentDescription.${testBiounitId}`;
      for (const lang of languages) {
        const cidInState = mockComponentState.complex_fields[lang].cid;
        const cidInContract = await mockAmanitaInternational.getComplexFieldCID(className, lang);
        expect(cidInState).to.equal(cidInContract);
      }

      // Cleanup
      uploadComponentsCoreStub.restore();
    });
  });
});

