/**
 * E2E Tests: AccessControl Validation (Layer 3)
 * 
 * ⚠️ AccessControlActions.js НЕ СУЩЕСТВУЕТ - это TDD!
 * Тесты написаны под НОВУЮ архитектуру (Layer 3: Access Control)
 * 
 * Coverage:
 * - validateDeployerAccess() - SELLER_ROLE check
 * - validateSellerAccess() - activation check
 * - validateInviteCode() - invite validation on-chain
 * - checkActivationStatus() - user status
 * - grantSellerRole() - role management
 * - getUserDiagnostics() - user diagnostics
 * 
 * Security Layer: КРИТИЧНО для системы безопасности!
 */

const { expect } = require('chai');
const E2EHarness = require('../../../helpers/E2EHarness');
const { ethers } = require('hardhat');

// AccessControlActions теперь создан! (ItemY_CODE1 completed)
const AccessControlActions = require('../../../../lib/actions/AccessControlActions');
const ContractManager = require('../../../../lib/services/ContractManager');
const EthersUtils = require('../../../../lib/utils/EthersUtils');
const config = require('../../../../lib/config');

describe('E2E: AccessControl Validation (Layer 3 - TDD)', function() {
  this.timeout(180000); // 3 min for E2E

  let harness;
  let spiralEngine;
  let deployerAddress;
  let sellerAddress;
  let testInviteCode;
  let accessControl; // AccessControlActions instance

  before(async function() {
    this.timeout(120000); // 2 min for setup

    // Start E2E infrastructure
    harness = new E2EHarness();
    await harness.startHardhatNode();
    harness.loadTestEnv();
    
    // Initialize AccessControlActions
    const ethersUtils = new EthersUtils(ethers.provider, config);
    const contractManager = new ContractManager(ethers.provider, config, ethersUtils);
    accessControl = new AccessControlActions(contractManager, ethersUtils, config);

    // Get signers
    const [deployer, seller] = await ethers.getSigners();
    deployerAddress = deployer.address;
    sellerAddress = seller.address;

    // Deploy SpiralEngine (prerequisite for access control)
    console.log('\n📦 Prerequisite: Deploying SpiralEngine...');
    const SpiralEngineLogic = await ethers.getContractFactory('SpiralEngineLogic');
    const spiralLogic = await SpiralEngineLogic.deploy();
    await spiralLogic.waitForDeployment();

    const SpiralEngineProxy = await ethers.getContractFactory('SpiralEngineProxy');
    const spiralProxy = await SpiralEngineProxy.deploy(await spiralLogic.getAddress(), '0x');
    await spiralProxy.waitForDeployment();

    spiralEngine = await ethers.getContractAt('SpiralEngineLogic', await spiralProxy.getAddress());

    console.log(`✅ SpiralEngine deployed: ${await spiralEngine.getAddress()}`);

    // Initialize SpiralEngine (grants all roles to deployer)
    const spiralWithDeployer = spiralEngine.connect(deployer);
    const initTx = await spiralWithDeployer.initialize(deployer.address);
    await initTx.wait();
    
    console.log(`✅ SpiralEngine initialized (deployer has all roles)`);

    // Create test invite
    testInviteCode = 'AMANITA-TEST-ACC1';
    const tx = await spiralWithDeployer.mintInvite(testInviteCode, 0);
    await tx.wait();

    console.log(`✅ Test invite created: ${testInviteCode}`);

    // Create snapshot
    await harness.saveState('after-setup');
  });

  after(async function() {
    await harness.stopHardhatNode();
    harness.restoreEnv();
  });

  beforeEach(async function() {
    await harness.restoreState('after-setup');
  });

  // ================================================================
  // Infrastructure Validation
  // ================================================================

  describe('Infrastructure Validation', () => {
    it('должен иметь deployed SpiralEngine', async () => {
      const validation = await harness.validateDeployment(await spiralEngine.getAddress());
      expect(validation.deployed).to.be.true;

      console.log('✓ SpiralEngine deployed for access control tests');
    });

    it('должен иметь test invite created', async () => {
      // Validate invite exists on-chain
      const inviteExists = await spiralEngine.inviteCodeExists(testInviteCode);
      expect(inviteExists).to.be.true;

      console.log(`✓ Test invite exists: ${testInviteCode}`);
    });

    it('должен иметь deployer с SELLER_ROLE', async () => {
      const SELLER_ROLE = await spiralEngine.SELLER_ROLE();
      const hasRole = await spiralEngine.hasRole(SELLER_ROLE, deployerAddress);

      expect(hasRole).to.be.true;

      console.log(`✓ Deployer has SELLER_ROLE: ${deployerAddress}`);
    });
  });

  // ================================================================
  // validateDeployerAccess (TDD Spec)
  // ================================================================

  describe('validateDeployerAccess() - E2E (TDD Spec)', () => {
    it('должен проверить SELLER_ROLE у deployer on-chain', async () => {
      // GIVEN: AccessControl instance (created in before hook)
      
      // WHEN: validateDeployerAccess вызывается
      await accessControl.validateDeployerAccess(spiralEngine);
      
      // THEN: Проверка прошла (deployer имеет SELLER_ROLE)
      const SELLER_ROLE = await spiralEngine.SELLER_ROLE();
      const hasRole = await spiralEngine.hasRole(SELLER_ROLE, deployerAddress);
      
      expect(hasRole).to.be.true;
      
      console.log('✅ AccessControlActions.validateDeployerAccess() работает!');
    });

    it('должен выбросить ошибку если deployer не имеет SELLER_ROLE', async () => {
      // GIVEN: Random user БЕЗ SELLER_ROLE
      const [_, __, randomUser] = await ethers.getSigners();
      
      // Verify randomUser doesn't have SELLER_ROLE
      const SELLER_ROLE = await spiralEngine.SELLER_ROLE();
      const hasRole = await spiralEngine.hasRole(SELLER_ROLE, randomUser.address);
      expect(hasRole).to.be.false;
      
      // Create AccessControl instance with randomUser as "deployer"
      // (используем getSigner(privateKey) для override deployer)
      const randomEthersUtils = new EthersUtils(ethers.provider, config);
      const randomContractManager = new ContractManager(ethers.provider, config, randomEthersUtils);
      const randomAccessControl = new AccessControlActions(randomContractManager, randomEthersUtils, config);
      
      // WHEN/THEN: validateDeployerAccess() ДОЛЖЕН выбросить ошибку
      let errorThrown = false;
      let errorMessage = '';
      
      try {
        // Override deployer через getSigner(privateKey)
        // Но проблема: метод использует getSigner() без параметров
        // Нужно передать privateKey через config или модифицировать подход
        
        // ALTERNATIVE: Проверим что метод выбрасывает ошибку через mock
        // Создаём wallet для randomUser и подменяем getSigner
        const originalGetSigner = randomEthersUtils.getSigner.bind(randomEthersUtils);
        randomEthersUtils.getSigner = () => randomUser;
        
        await randomAccessControl.validateDeployerAccess(spiralEngine);
      } catch (error) {
        errorThrown = true;
        errorMessage = error.message;
      }
      
      // THEN: Ошибка ДОЛЖНА быть выброшена
      expect(errorThrown).to.be.true;
      expect(errorMessage).to.include('не имеет роли SELLER_ROLE');
      
      console.log('✅ AccessControl: validateDeployerAccess() correctly throws error for non-SELLER');
    });
  });

  // ================================================================
  // validateInviteCode (TDD Spec)
  // ================================================================

  describe('validateInviteCode() - E2E (TDD Spec)', () => {
    it('должен проверить что invite существует on-chain', async () => {
      // WHEN: validateInviteCode вызывается
      const result = await accessControl.validateInviteCode(spiralEngine, testInviteCode);
      
      // THEN: Validation прошла (invite exists)
      expect(result.exists).to.be.true;
      expect(result.used).to.be.false;
      expect(result.tokenId).to.be.a('string');
      
      console.log('✅ AccessControlActions.validateInviteCode() работает!');
    });

    it('должен выбросить ошибку для несуществующего invite', async () => {
      // GIVEN: Несуществующий invite code
      const invalidInvite = 'AMANITA-INVALID-CODE';
      
      // Verify invite doesn't exist on-chain
      const exists = await spiralEngine.inviteCodeExists(invalidInvite);
      expect(exists).to.be.false;
      
      // WHEN/THEN: validateInviteCode() ДОЛЖЕН выбросить ошибку
      let errorThrown = false;
      let errorMessage = '';
      
      try {
        await accessControl.validateInviteCode(spiralEngine, invalidInvite);
      } catch (error) {
        errorThrown = true;
        errorMessage = error.message;
      }
      
      // THEN: Проверяем что ошибка выброшена и содержит правильный текст
      expect(errorThrown).to.be.true;
      expect(errorMessage).to.include('не существует в системе');
      expect(errorMessage).to.include(invalidInvite);
      
      console.log('✅ AccessControl: validateInviteCode() correctly throws for invalid invite');
    });

    it('должен выбросить ошибку для уже использованного invite', async () => {
      // GIVEN: Activate user with invite (использовать invite)
      const [deployer] = await ethers.getSigners();
      const [_, seller] = await ethers.getSigners();
      
      // Create new invites for activation
      const newInvites = Array(12).fill().map((_, i) => `SELLER-INV-${i}`);
      
      // Activate seller (использует testInviteCode)
      const spiralWithDeployer = spiralEngine.connect(deployer);
      const tokenId = await spiralEngine.inviteCodeToTokenId(testInviteCode);
      const activateTx = await spiralWithDeployer.activateUser(testInviteCode, seller.address, newInvites, 0);
      await activateTx.wait();
      
      // Verify invite is now used
      const isUsed = await spiralEngine.isInviteUsed(tokenId);
      expect(isUsed).to.be.true;
      
      // WHEN/THEN: validateInviteCode() ДОЛЖЕН выбросить ошибку
      let errorThrown = false;
      let errorMessage = '';
      
      try {
        await accessControl.validateInviteCode(spiralEngine, testInviteCode);
      } catch (error) {
        errorThrown = true;
        errorMessage = error.message;
      }
      
      // THEN: Проверяем что ошибка выброшена и содержит правильный текст
      expect(errorThrown).to.be.true;
      expect(errorMessage).to.include('уже был использован');
      expect(errorMessage).to.include(testInviteCode);
      
      console.log('✅ AccessControl: validateInviteCode() correctly throws for used invite');
    });
  });

  // ================================================================
  // checkActivationStatus (TDD Spec)
  // ================================================================

  describe('checkActivationStatus() - E2E (TDD Spec)', () => {
    it('должен вернуть false для неактивированного пользователя', async () => {
      // WHEN: checkActivationStatus вызывается для seller (не активирован)
      const status = await accessControl.checkActivationStatus(spiralEngine, sellerAddress);
      
      // THEN: Status = false
      expect(status).to.be.false;
      
      console.log('✅ AccessControlActions.checkActivationStatus() работает!');
    });

    it('должен вернуть true для активированного пользователя', async () => {
      // GIVEN: Activate seller first
      const [deployer] = await ethers.getSigners();
      const [_, seller] = await ethers.getSigners();
      
      const newInvites = Array(12).fill().map((_, i) => `SELLER-INV-${i}`);
      const spiralWithDeployer = spiralEngine.connect(deployer);
      const activateTx = await spiralWithDeployer.activateUser(testInviteCode, seller.address, newInvites, 0);
      await activateTx.wait();
      
      // WHEN: checkActivationStatus вызывается через AccessControl
      const status = await accessControl.checkActivationStatus(spiralEngine, seller.address);
      
      // THEN: Status = true (активирован)
      expect(status).to.be.true;
      
      console.log('✅ AccessControlActions.checkActivationStatus() returns true for activated user');
    });
  });

  // ================================================================
  // validateSellerAccess (TDD Spec) - NEW!
  // ================================================================

  describe('validateSellerAccess() - E2E (TDD Spec)', () => {
    it('должен вернуть true для активированного seller', async () => {
      // GIVEN: Activate seller first
      const [deployer, seller] = await ethers.getSigners();
      
      const newInvites = Array(12).fill().map((_, i) => `SELLER-VAL-${i}`);
      const spiralWithDeployer = spiralEngine.connect(deployer);
      await spiralWithDeployer.activateUser(testInviteCode, seller.address, newInvites, 0);
      
      // WHEN: validateSellerAccess вызывается
      const result = await accessControl.validateSellerAccess(spiralEngine, seller.address);
      
      // THEN: Validation успешна, возвращает true
      expect(result).to.be.true;
      
      console.log('✅ AccessControlActions.validateSellerAccess() returns true for activated seller');
    });

    it('должен выбросить ошибку для неактивированного seller', async () => {
      // GIVEN: Seller НЕ активирован
      const [_, seller] = await ethers.getSigners();
      
      // Verify seller not activated
      const usedInvite = await spiralEngine.usedInviteByUser(seller.address);
      expect(Number(usedInvite)).to.equal(0);
      
      // WHEN/THEN: validateSellerAccess должен выбросить ошибку
      let errorThrown = false;
      let errorMessage = '';
      
      try {
        await accessControl.validateSellerAccess(spiralEngine, seller.address);
      } catch (error) {
        errorThrown = true;
        errorMessage = error.message;
      }
      
      // THEN: Ошибка выброшена с правильным текстом
      expect(errorThrown).to.be.true;
      expect(errorMessage).to.include('не активирован в системе');
      expect(errorMessage).to.include(seller.address);
      
      console.log('✅ AccessControl: validateSellerAccess() correctly throws for non-activated seller');
    });

    it('должен выбросить ошибку для zero address', async () => {
      // WHEN/THEN: validateSellerAccess для zero address
      let errorThrown = false;
      let errorMessage = '';
      
      try {
        await accessControl.validateSellerAccess(spiralEngine, ethers.ZeroAddress);
      } catch (error) {
        errorThrown = true;
        errorMessage = error.message;
      }
      
      // THEN: Ошибка выброшена
      expect(errorThrown).to.be.true;
      expect(errorMessage).to.include('не может быть zero address');
      
      console.log('✅ AccessControl: validateSellerAccess() correctly throws for zero address');
    });
  });

  // ================================================================
  // grantSellerRole (TDD Spec)
  // ================================================================

  describe('grantSellerRole() - E2E (TDD Spec)', () => {
    beforeEach(async function() {
      // Activate seller first (prerequisite for grantSellerRole)
      const [deployer] = await ethers.getSigners();
      const [_, seller] = await ethers.getSigners();
      
      const newInvites = Array(12).fill().map((_, i) => `SELLER-INV-${i}`);
      const spiralWithDeployer = spiralEngine.connect(deployer);
      const tx = await spiralWithDeployer.activateUser(testInviteCode, seller.address, newInvites, 0);
      await tx.wait();
    });

    it('должен назначить SELLER_ROLE активированному пользователю', async () => {
      // WHEN: grantSellerRole вызывается
      await accessControl.grantSellerRole(spiralEngine, sellerAddress);
      
      // THEN: SELLER_ROLE назначена
      const SELLER_ROLE = await spiralEngine.SELLER_ROLE();
      const hasRole = await spiralEngine.hasRole(SELLER_ROLE, sellerAddress);
      expect(hasRole).to.be.true;
      
      console.log('✅ AccessControlActions.grantSellerRole() работает!');
    });

    it('должен выбросить ошибку если пользователь не активирован', async () => {
      // GIVEN: Неактивированный пользователь
      const [deployer, _, randomUser] = await ethers.getSigners();
      
      const spiralWithDeployer = spiralEngine.connect(deployer);
      
      // WHEN/THEN: grantSellerRole падает
      let reverted = false;
      try {
        await spiralWithDeployer.grantSellerRole(randomUser.address);
      } catch (error) {
        reverted = true;
        expect(error.message).to.include('revert');
      }
      
      expect(reverted).to.be.true;
      console.log('✅ AccessControl: grantSellerRole correctly reverts for non-activated user');
    });
  });

  // ================================================================
  // grantActivatorRole (TDD Spec) - NEW!
  // ================================================================

  describe('grantActivatorRole() - E2E (TDD Spec)', () => {
    it('должен назначить ACTIVATOR_ROLE пользователю', async () => {
      // GIVEN: Seller активирован (from grantSellerRole beforeEach)
      const [deployer] = await ethers.getSigners();
      const [_, seller] = await ethers.getSigners();
      
      // Activate seller first
      const newInvites = Array(12).fill().map((_, i) => `ACT-INV-${i}`);
      const spiralWithDeployer = spiralEngine.connect(deployer);
      await spiralWithDeployer.activateUser(testInviteCode, seller.address, newInvites, 0);
      
      // WHEN: grantActivatorRole вызывается
      await accessControl.grantActivatorRole(spiralEngine, seller.address);
      
      // THEN: ACTIVATOR_ROLE назначена on-chain
      const ACTIVATOR_ROLE = await spiralEngine.ACTIVATOR_ROLE();
      const hasRole = await spiralEngine.hasRole(ACTIVATOR_ROLE, seller.address);
      
      expect(hasRole).to.be.true;
      
      console.log('✅ AccessControlActions.grantActivatorRole() успешно назначает роль');
    });

    it('должен выбросить ошибку для zero address', async () => {
      // WHEN/THEN: grantActivatorRole для zero address
      let errorThrown = false;
      let errorMessage = '';
      
      try {
        await accessControl.grantActivatorRole(spiralEngine, ethers.ZeroAddress);
      } catch (error) {
        errorThrown = true;
        errorMessage = error.message;
      }
      
      // THEN: Ошибка выброшена
      expect(errorThrown).to.be.true;
      expect(errorMessage).to.include('не может быть zero address');
      
      console.log('✅ AccessControl: grantActivatorRole() correctly throws for zero address');
    });

    it('должен требовать DEFAULT_ADMIN роль для назначения (security)', async () => {
      // GIVEN: Activate seller first
      const [deployer, seller, randomUser] = await ethers.getSigners();
      
      const newInvites = Array(12).fill().map((_, i) => `SEC-INV-${i}`);
      const spiralWithDeployer = spiralEngine.connect(deployer);
      await spiralWithDeployer.activateUser(testInviteCode, seller.address, newInvites, 0);
      
      // WHEN: Random user (НЕ admin) пытается назначить ACTIVATOR_ROLE
      const spiralWithRandom = spiralEngine.connect(randomUser);
      const ACTIVATOR_ROLE = await spiralEngine.ACTIVATOR_ROLE();
      
      let reverted = false;
      try {
        await spiralWithRandom.grantRole(ACTIVATOR_ROLE, seller.address);
      } catch (error) {
        reverted = true;
        expect(error.message).to.include('revert');
      }
      
      expect(reverted).to.be.true;
      
      console.log('✅ Security: только admin может назначать ACTIVATOR_ROLE');
    });

    it('должен проверить назначенную роль on-chain (verification)', async () => {
      // GIVEN: Назначаем роль seller
      const [deployer, seller] = await ethers.getSigners();
      
      const newInvites = Array(12).fill().map((_, i) => `VER-INV-${i}`);
      const spiralWithDeployer = spiralEngine.connect(deployer);
      await spiralWithDeployer.activateUser(testInviteCode, seller.address, newInvites, 0);
      
      await accessControl.grantActivatorRole(spiralEngine, seller.address);
      
      // WHEN: Проверяем роль on-chain
      const ACTIVATOR_ROLE = await spiralEngine.ACTIVATOR_ROLE();
      const hasRole = await spiralEngine.hasRole(ACTIVATOR_ROLE, seller.address);
      
      // THEN: Роль действительно назначена
      expect(hasRole).to.be.true;
      
      console.log('✅ Verification: ACTIVATOR_ROLE confirmed on-chain');
    });
  });

  // ================================================================
  // getUserDiagnostics (TDD Spec)
  // ================================================================

  describe('getUserDiagnostics() - E2E (TDD Spec)', () => {
    it('должен вернуть полную диагностику для пользователя', async () => {
      // WHEN: getUserDiagnostics вызывается
      const diagnostics = await accessControl.getUserDiagnostics(spiralEngine, sellerAddress);
      
      // THEN: Diagnostics содержат полную информацию
      expect(diagnostics).to.have.property('address', sellerAddress);
      expect(diagnostics).to.have.property('valid', true);
      expect(diagnostics).to.have.property('activation');
      expect(diagnostics).to.have.property('roles');
      expect(diagnostics.activation).to.have.property('activated');
      expect(diagnostics.roles).to.have.property('SELLER_ROLE');
      expect(diagnostics.roles).to.have.property('ACTIVATOR_ROLE');
      
      console.log('✅ AccessControlActions.getUserDiagnostics() работает!');
    });

    it('должен вернуть полную диагностику для activated user с ролями', async () => {
      // GIVEN: Activate seller + grant both roles
      const [deployer, seller] = await ethers.getSigners();
      
      // Step 1: Activate
      const newInvites = Array(12).fill().map((_, i) => `DIAG-INV-${i}`);
      const spiralWithDeployer = spiralEngine.connect(deployer);
      await spiralWithDeployer.activateUser(testInviteCode, seller.address, newInvites, 0);
      
      // Step 2: Grant SELLER_ROLE
      await accessControl.grantSellerRole(spiralEngine, seller.address);
      
      // Step 3: Grant ACTIVATOR_ROLE
      await accessControl.grantActivatorRole(spiralEngine, seller.address);
      
      // WHEN: getUserDiagnostics вызывается
      const diagnostics = await accessControl.getUserDiagnostics(spiralEngine, seller.address);
      
      // THEN: Полная диагностика с всеми полями
      expect(diagnostics.valid).to.be.true;
      expect(diagnostics.activation.activated).to.be.true;
      expect(Number(diagnostics.activation.usedInviteTokenId)).to.be.greaterThan(0);
      expect(diagnostics.activation.activatedBy).to.equal(deployer.address);
      expect(diagnostics.roles.SELLER_ROLE).to.be.true;
      expect(diagnostics.roles.ACTIVATOR_ROLE).to.be.true;
      
      console.log('✅ getUserDiagnostics(): полная диагностика activated user с ролями работает!');
    });

    it.skip('должен показать количество созданных invites пользователем', async () => {
      // SKIP: Контракт не хранит счётчик invites напрямую
      // Требует event-based counting или дополнительный mapping
      // TODO: Реализовать после добавления invitesMintedByUser mapping в контракт
      
      console.log('⏳ SKIPPED: getUserDiagnostics() invites count (requires contract update)');
      expect(true).to.be.true; // Placeholder
    });
  });

  // ================================================================
  // Security E2E Scenarios (критично!)
  // ================================================================

  describe('Security E2E Scenarios (критично!)', () => {
    it('должен блокировать mintInvite от пользователя без SELLER_ROLE', async () => {
      // GIVEN: Random user без SELLER_ROLE
      const [_, __, randomUser] = await ethers.getSigners();
      const spiralWithRandom = spiralEngine.connect(randomUser);
      
      // WHEN/THEN: mintInvite падает
      let reverted = false;
      try {
        await spiralWithRandom.mintInvite('AMANITA-HACK-0001', 0);
      } catch (error) {
        reverted = true;
        expect(error.message).to.include('revert');
      }
      
      expect(reverted).to.be.true;
      console.log('✓ Security: mintInvite защищен SELLER_ROLE');
    });

    it('должен блокировать activateUser от пользователя без ACTIVATOR_ROLE', async () => {
      // GIVEN: Random user без ACTIVATOR_ROLE
      const [_, __, randomUser] = await ethers.getSigners();
      const spiralWithRandom = spiralEngine.connect(randomUser);
      
      const newInvites = Array(12).fill('TEST-INV');
      
      // WHEN/THEN: activateUser падает
      let reverted = false;
      try {
        await spiralWithRandom.activateUser(testInviteCode, randomUser.address, newInvites, 0);
      } catch (error) {
        reverted = true;
        expect(error.message).to.include('revert');
      }
      
      expect(reverted).to.be.true;
      console.log('✓ Security: activateUser защищен ACTIVATOR_ROLE');
    });

    it('должен блокировать grantSellerRole от пользователя без ACTIVATOR_ROLE', async () => {
      // GIVEN: Activate seller first
      const [deployer, seller, randomUser] = await ethers.getSigners();
      
      const newInvites = Array(12).fill().map((_, i) => `SELLER-INV-${i}`);
      const spiralWithDeployer = spiralEngine.connect(deployer);
      await spiralWithDeployer.activateUser(testInviteCode, seller.address, newInvites, 0);
      
      // THEN: Random user не может назначить SELLER_ROLE
      const spiralWithRandom = spiralEngine.connect(randomUser);
      
      let reverted = false;
      try {
        await spiralWithRandom.grantSellerRole(seller.address);
      } catch (error) {
        reverted = true;
        expect(error.message).to.include('revert');
      }
      
      expect(reverted).to.be.true;
      console.log('✓ Security: grantSellerRole защищен ACTIVATOR_ROLE');
    });

    it('должен проверить что только deployer может создавать root invites', async () => {
      // SECURITY: Только deployer (SELLER_ROLE) может минтить invites
      
      // STEP 1: Verify roles
      const SELLER_ROLE = await spiralEngine.SELLER_ROLE();
      const deployerHasRole = await spiralEngine.hasRole(SELLER_ROLE, deployerAddress);
      const sellerHasRole = await spiralEngine.hasRole(SELLER_ROLE, sellerAddress);
      
      expect(deployerHasRole).to.be.true;
      expect(sellerHasRole).to.be.false;
      
      // STEP 2: Попытка mint от seller (БЕЗ SELLER_ROLE)
      const [_, seller] = await ethers.getSigners();
      const spiralWithSeller = spiralEngine.connect(seller);
      
      let reverted = false;
      try {
        await spiralWithSeller.mintInvite('AMANITA-UNAUTHORIZED-MINT', 0);
      } catch (error) {
        reverted = true;
        expect(error.message).to.include('revert');
      }
      
      expect(reverted).to.be.true;
      
      console.log('✅ Security: mintInvite реально блокируется для non-SELLER');
    });
  });

  // ================================================================
  // Error Scenarios (TDD Spec)
  // ================================================================

  describe('Error Scenarios (TDD Spec)', () => {
    it.skip('должен обработать несуществующий invite code', async () => {
      // SKIP: Уже покрыто в validateInviteCode() error path (lines 207-244)
      // Этот тест дублирует, но проверяет контракт напрямую (не через accessControl)
      // Оставляем skip для документации
      
      const invalidInvite = 'AMANITA-NOTEXIST-00';
      const exists = await spiralEngine.inviteCodeExists(invalidInvite);
      expect(exists).to.be.false;
      
      console.log('⏳ SKIPPED: уже покрыто в validateInviteCode() error tests');
    });

    it.skip('должен обработать уже использованный invite', async () => {
      // SKIP: Уже покрыто в validateInviteCode() error path (lines 246-281)
      // Этот тест дублирует, оставляем для документации
      
      const [deployer, seller] = await ethers.getSigners();
      const newInvites = Array(12).fill().map((_, i) => `USED-INV-${i}`);
      const spiralWithDeployer = spiralEngine.connect(deployer);
      await spiralWithDeployer.activateUser(testInviteCode, seller.address, newInvites, 0);
      
      const tokenId = await spiralEngine.inviteCodeToTokenId(testInviteCode);
      const isUsed = await spiralEngine.isInviteUsed(tokenId);
      expect(isUsed).to.be.true;
      
      console.log('⏳ SKIPPED: уже покрыто в validateInviteCode() error tests');
    });

    it('должен обработать zero address (getUserDiagnostics graceful handling)', async () => {
      // NOTE: validateSellerAccess() zero address уже покрыт в lines 356-373
      
      // WHEN: getUserDiagnostics вызывается с zero address
      const diagnostics = await accessControl.getUserDiagnostics(spiralEngine, ethers.ZeroAddress);
      
      // THEN: Graceful handling (не throw, возвращает error info)
      expect(diagnostics).to.have.property('address', ethers.ZeroAddress);
      expect(diagnostics).to.have.property('valid', false);
      expect(diagnostics).to.have.property('error', 'Zero address');
      
      console.log('✅ AccessControl: getUserDiagnostics() gracefully handles zero address');
    });
  });

  // ================================================================
  // Integration: AccessControl → InviteActions (TDD Spec)
  // ================================================================

  describe('Integration: AccessControl → InviteActions (TDD Spec)', () => {
    it.skip('должен работать в связке: validateInviteCode → activateUser', async () => {
      // SKIP: InviteActions.js ещё не создан (ItemY_CODE2)
      // Интеграционный тест будет активирован после рефакторинга
      // TODO: Раскомментировать после создания InviteActions.activateUser()
      
      // GIVEN: AccessControl проверяет invite
      // const isValid = await accessControl.validateInviteCode(spiralEngine, testInviteCode);
      // expect(isValid).to.be.true;
      
      // WHEN: InviteActions использует этот invite для активации
      // const activation = await inviteActions.activateUser(spiralEngine, testInviteCode, sellerAddress);
      
      // THEN: Activation успешна
      
      console.log('⏳ SKIPPED: AccessControl → InviteActions integration (InviteActions not created yet)');
    });

    it.skip('должен работать в связке: checkActivationStatus → grantSellerRole', async () => {
      // SKIP: Интеграционный тест уже покрыт в grantSellerRole() describe block
      // grantSellerRole() внутренне использует checkActivationStatus()
      // Этот тест избыточен, можно удалить или оставить skip для документации
      
      // GIVEN: Проверить что user активирован
      // const isActivated = await accessControl.checkActivationStatus(spiralEngine, sellerAddress);
      
      // IF activated:
      // WHEN: grantSellerRole можно вызвать
      // await accessControl.grantSellerRole(spiralEngine, sellerAddress);
      
      // THEN: Role назначена
      
      console.log('⏳ SKIPPED: checkActivation → grantRole integration (already tested in grantSellerRole)');
    });
  });

  // ================================================================
  // DAO Governance Foundation (TDD Spec)
  // ================================================================

  describe('DAO Governance Foundation (TDD Spec)', () => {
    it('должен подготовить структуру для DAO voting (future)', async () => {
      // TODO: AccessControl = фундамент для DAO governance
      // Проверяем что роли могут управляться on-chain
      
      const SELLER_ROLE = await spiralEngine.SELLER_ROLE();
      const ACTIVATOR_ROLE = await spiralEngine.ACTIVATOR_ROLE();
      
      expect(SELLER_ROLE).to.not.equal(ethers.ZeroHash);
      expect(ACTIVATOR_ROLE).to.not.equal(ethers.ZeroHash);
      
      console.log('⏳ TDD: DAO governance foundation (role structure)');
      console.log(`   SELLER_ROLE: ${SELLER_ROLE}`);
      console.log(`   ACTIVATOR_ROLE: ${ACTIVATOR_ROLE}`);
    });

    it.skip('должен поддерживать role-based permissions для будущего DAO', async () => {
      // SKIP: Future feature - DAO voting система
      // AccessControl создаёт foundation для DAO governance
      // TODO: Реализовать после внедрения DAO voting механизма
      // - Vote для назначения ролей
      // - Collective decision-making
      // - Proposal system
      
      console.log('⏳ SKIPPED: DAO extensibility (future feature - not yet implemented)');
    });
  });
});

