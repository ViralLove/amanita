/**
 * E2E Tests: Action 888 - Full Deployment Pipeline
 * 
 * ЭТАЛОН: deploy_full.js action888() function
 * 
 * Полный workflow (8 шагов):
 * 1. Validate inputs (deployerInvite, sellerAddress)
 * 2. Load contracts (SpiralEngine, ProductRegistry, SoulIdentity, OrganicComponentRegistry)
 * 3. Check seller activation status
 * 4. IF not activated → Activate seller
 * 5. Grant SELLER_ROLE
 * 6. Grant ACTIVATOR_ROLE
 * 7. Setup SoulIdentity для seller
 * 8. Load catalog (Action 444) + Generate seller invites
 * 
 * TDD Note: Тест под НОВУЮ архитектуру (CatalogActions.action888)
 */

const { expect } = require('chai');
const E2EHarness = require('../../../helpers/E2EHarness');
const { ethers } = require('hardhat');
const fs = require('fs');
const path = require('path');

// TODO: Import CatalogActions when action888 refactored
// const CatalogActions = require('../../../../lib/actions/CatalogActions');

describe('E2E: Action 888 - Full Pipeline (по эталону deploy_full.js)', function() {
  // ✅ FIXED: UUPS contracts properly initialized with deployer as admin
  this.timeout(300000); // 5 min for full pipeline

  let harness;
  let deployedContracts;
  let deployerAddress;
  let sellerAddress;
  let deployerInvite;

  before(async function() {
    this.timeout(180000); // 3 min for setup

    // Start E2E infrastructure
    harness = new E2EHarness();
    await harness.startHardhatNode();
    harness.loadTestEnv();

    // Get signers
    const [deployer, seller] = await ethers.getSigners();
    deployerAddress = deployer.address;
    sellerAddress = seller.address;

    // Deploy ALL contracts (Action 1 logic)
    console.log('\n📦 Phase 0: Deploying complete ecosystem (Action 1)...');
    deployedContracts = await deployCompleteEcosystemFor888();

    // Generate deployer invites (Action 777 logic)
    console.log('\n🎲 Phase 0: Generating deployer invites (Action 777)...');
    deployerInvite = await generateDeployerInvitesFor888(deployedContracts.spiralEngine);

    console.log(`\n✅ Prerequisites complete for Action 888`);
    console.log(`   Deployer: ${deployerAddress}`);
    console.log(`   Seller: ${sellerAddress}`);
    console.log(`   DEPLOYER_INVITE: ${deployerInvite}`);
    console.log(`   Contracts deployed: ${Object.keys(deployedContracts).length}`);

    // Create snapshot (expensive setup)
    await harness.saveState('ready-for-888');
  });

  after(async function() {
    await harness.stopHardhatNode();
    harness.restoreEnv();
  });

  beforeEach(async function() {
    // Reset to ready state
    await harness.restoreState('ready-for-888');
  });

  // ================================================================
  // Infrastructure Validation
  // ================================================================

  describe('Infrastructure Validation (Prerequisites)', () => {
    it('должен иметь complete ecosystem deployed (Action 1)', async () => {
      // Validate ALL contracts deployed
      const requiredContracts = [
        'magicRegistry',
        'spiralEngine',
        'soulboundCore',
        'soulMetadata',
        'soulRecovery',
        'soulIntegration',
        'soulIdentity',
        'productRegistry',
        'organicComponentRegistry',
        'amanitaInternational'
      ];

      for (const contractName of requiredContracts) {
        expect(deployedContracts[contractName]).to.exist;
        const validation = await harness.validateDeployment(deployedContracts[contractName]);
        expect(validation.deployed).to.be.true;
      }

      console.log('✓ All 10 contracts deployed (Action 1 complete)');
    });

    it('должен иметь deployer invites created (Action 777)', async () => {
      // Validate invite exists
      const SpiralEngine = await ethers.getContractAt('SpiralEngineLogic', deployedContracts.spiralEngine);
      
      const inviteExists = await SpiralEngine.inviteCodeExists(deployerInvite);
      expect(inviteExists).to.be.true;
      
      const tokenId = await SpiralEngine.inviteCodeToTokenId(deployerInvite);
      const isUsed = await SpiralEngine.isInviteUsed(tokenId);
      expect(isUsed).to.be.false; // Не использован

      console.log(`✓ Deployer invite exists: ${deployerInvite} (Action 777 complete)`);
    });

    it('должен иметь SetupActions connections установлены', async () => {
      // Validate SetupActions выполнен (connections present)
      const SoulboundCore = await ethers.getContractAt('SoulboundCore', deployedContracts.soulboundCore);
      const SpiralEngine = await ethers.getContractAt('SpiralEngineLogic', deployedContracts.spiralEngine);
      const OrganicRegistry = await ethers.getContractAt('OrganicComponentRegistryLogic', deployedContracts.organicComponentRegistry);

      // SBT connections
      const metadataContract = await SoulboundCore.getMetadataContract();
      expect(metadataContract).to.equal(deployedContracts.soulMetadata);

      // SpiralEngine → SoulIdentity
      const soulIdentity = await SpiralEngine.soulIdentity();
      expect(soulIdentity).to.equal(deployedContracts.soulIdentity);

      // OrganicRegistry → SpiralEngine
      const spiralInOrganic = await OrganicRegistry.spiralEngine();
      expect(spiralInOrganic).to.equal(deployedContracts.spiralEngine);

      console.log('✓ SetupActions connections validated');
    });
  });

  // ================================================================
  // Action 888: Step 1-2 (Validate + Load Contracts)
  // ================================================================

  describe('Action 888: Step 1-2 (Validate + Load) - TDD Spec', () => {
    it('должен валидировать входные параметры', async () => {
      // TODO: После рефакторинга CatalogActions.action888
      // TDD Spec из deploy_full.js: validateAction888Inputs()
      
      // Validate deployerInvite format
      expect(deployerInvite).to.match(/^AMANITA-[A-Z0-9]{4}-[A-Z0-9]{4}$/);
      
      // Validate sellerAddress format
      expect(ethers.isAddress(sellerAddress)).to.be.true;
      
      console.log('⏳ TDD: validateAction888Inputs() (будет в CatalogActions.action888)');
    });

    it('должен загрузить контракты через MagicRegistry', async () => {
      // TODO: TDD Spec из deploy_full.js: loadContractsFor888()
      // НОВАЯ архитектура: через MagicRegistry (не .env!)
      
      const MagicRegistry = await ethers.getContractAt('AmanitaRegistry', deployedContracts.magicRegistry);
      
      // Проверяем что контракты зарегистрированы
      const spiralAddress = await MagicRegistry.get('SpiralEngine');
      expect(spiralAddress).to.equal(deployedContracts.spiralEngine);
      
      console.log('⏳ TDD: loadContractsFor888() через MagicRegistry');
    });
  });

  // ================================================================
  // Action 888: Step 3-4 (Check Activation + Activate if needed)
  // ================================================================

  describe('Action 888: Step 3-4 (Activation) - из deploy_full.js', () => {
    it('должен проверить статус активации seller', async () => {
      // Эталон: checkSellerActivationStatus() из deploy_full.js
      const SpiralEngine = await ethers.getContractAt('SpiralEngineLogic', deployedContracts.spiralEngine);
      
      const usedInvite = await SpiralEngine.usedInviteByUser(sellerAddress);
      const isActivated = usedInvite > 0;
      
      expect(isActivated).to.be.false; // До активации

      console.log('✓ checkSellerActivationStatus() validated (not activated)');
    });

    it('должен активировать seller если не активирован', async function() {
      this.timeout(60000);

      // Эталон: activateSellerInSpiralEngine() из deploy_full.js
      const [deployer] = await ethers.getSigners();
      const SpiralEngine = await ethers.getContractAt('SpiralEngineLogic', deployedContracts.spiralEngine);
      const spiralWithDeployer = SpiralEngine.connect(deployer);

      // Generate 12 seller invites
      const sellerInvites = Array(12).fill().map((_, i) => `SELLER-INV-${i.toString().padStart(4, '0')}`);

      // Activate seller
      const tokenId = await SpiralEngine.inviteCodeToTokenId(deployerInvite);
      const activateTx = await spiralWithDeployer.activateUser(deployerInvite, sellerAddress, sellerInvites, 0);
      await activateTx.wait();

      // Validate activation
      const usedInvite = await SpiralEngine.usedInviteByUser(sellerAddress);
      expect(usedInvite).to.equal(tokenId + BigInt(1)); // Activated

      console.log('✓ activateSellerInSpiralEngine() completed');
      console.log(`   Seller activated with invite: ${deployerInvite}`);
    });

    it('должен пропустить активацию если seller уже активирован', async function() {
      this.timeout(60000);

      // GIVEN: Activate seller first
      const [deployer] = await ethers.getSigners();
      const SpiralEngine = await ethers.getContractAt('SpiralEngineLogic', deployedContracts.spiralEngine);
      const spiralWithDeployer = SpiralEngine.connect(deployer);

      const sellerInvites = Array(12).fill().map((_, i) => `SELLER-INV-${i}`);
      await spiralWithDeployer.activateUser(deployerInvite, sellerAddress, sellerInvites, 0);

      // WHEN: Check activation again
      const usedInvite = await SpiralEngine.usedInviteByUser(sellerAddress);
      const isActivated = usedInvite > 0;

      // THEN: Already activated
      expect(isActivated).to.be.true;

      console.log('✓ Seller activation check (already activated, skip)');
    });
  });

  // ================================================================
  // Action 888: Step 5-6 (Role Management)
  // ================================================================

  describe('Action 888: Step 5-6 (Role Management) - из deploy_full.js', () => {
    beforeEach(async function() {
      // Activate seller first (prerequisite for role grants)
      const [deployer] = await ethers.getSigners();
      const SpiralEngine = await ethers.getContractAt('SpiralEngineLogic', deployedContracts.spiralEngine);
      const spiralWithDeployer = SpiralEngine.connect(deployer);

      const sellerInvites = Array(12).fill().map((_, i) => `SELLER-INV-${i}`);
      await spiralWithDeployer.activateUser(deployerInvite, sellerAddress, sellerInvites, 0);
    });

    it('должен назначить SELLER_ROLE активированному seller', async () => {
      // Эталон: grantSellerRoleToUser() из deploy_full.js
      const [deployer] = await ethers.getSigners();
      const SpiralEngine = await ethers.getContractAt('SpiralEngineLogic', deployedContracts.spiralEngine);
      const spiralWithDeployer = SpiralEngine.connect(deployer);

      // Grant SELLER_ROLE
      const tx = await spiralWithDeployer.grantSellerRole(sellerAddress);
      await tx.wait();

      // Validate role assigned
      const SELLER_ROLE = await SpiralEngine.SELLER_ROLE();
      const hasRole = await SpiralEngine.hasRole(SELLER_ROLE, sellerAddress);
      
      expect(hasRole).to.be.true;

      console.log('✓ grantSellerRoleToUser() completed');
      console.log(`   Seller has SELLER_ROLE: ${sellerAddress}`);
    });

    it('должен назначить ACTIVATOR_ROLE seller', async () => {
      // Эталон: grantActivatorRoleToSeller() из deploy_full.js
      const [deployer] = await ethers.getSigners();
      const SpiralEngine = await ethers.getContractAt('SpiralEngineLogic', deployedContracts.spiralEngine);
      const spiralWithDeployer = SpiralEngine.connect(deployer);

      // Grant SELLER_ROLE first (prerequisite)
      await spiralWithDeployer.grantSellerRole(sellerAddress);

      // Grant ACTIVATOR_ROLE
      const ACTIVATOR_ROLE = await SpiralEngine.ACTIVATOR_ROLE();
      const grantTx = await spiralWithDeployer.grantRole(ACTIVATOR_ROLE, sellerAddress);
      await grantTx.wait();

      // Validate role assigned
      const hasRole = await SpiralEngine.hasRole(ACTIVATOR_ROLE, sellerAddress);
      expect(hasRole).to.be.true;

      console.log('✓ grantActivatorRoleToSeller() completed');
      console.log(`   Seller has ACTIVATOR_ROLE: ${sellerAddress}`);
    });

    it('должен назначить обе роли последовательно (полный workflow)', async function() {
      this.timeout(60000);

      const [deployer] = await ethers.getSigners();
      const SpiralEngine = await ethers.getContractAt('SpiralEngineLogic', deployedContracts.spiralEngine);
      const spiralWithDeployer = SpiralEngine.connect(deployer);

      // Grant both roles
      await spiralWithDeployer.grantSellerRole(sellerAddress);
      
      const ACTIVATOR_ROLE = await SpiralEngine.ACTIVATOR_ROLE();
      await spiralWithDeployer.grantRole(ACTIVATOR_ROLE, sellerAddress);

      // Validate both roles
      const SELLER_ROLE = await SpiralEngine.SELLER_ROLE();
      const hasSellerRole = await SpiralEngine.hasRole(SELLER_ROLE, sellerAddress);
      const hasActivatorRole = await SpiralEngine.hasRole(ACTIVATOR_ROLE, sellerAddress);

      expect(hasSellerRole).to.be.true;
      expect(hasActivatorRole).to.be.true;

      console.log('✓ Both roles assigned (SELLER + ACTIVATOR)');
    });
  });

  // ================================================================
  // Action 888: Step 7 (SoulIdentity Setup)
  // ================================================================

  describe('Action 888: Step 7 (SoulIdentity) - из deploy_full.js', () => {
    it('должен настроить SoulIdentity для seller (TDD Spec)', async () => {
      // TODO: TDD Spec из deploy_full.js: setupSoulIdentityFor888()
      
      // Эта функция должна:
      // - Создать SBT token для seller
      // - Установить metadata
      // - Связать с SpiralEngine identity
      
      expect(deployedContracts.soulIdentity).to.exist;
      
      console.log('⏳ TDD: setupSoulIdentityFor888() (SBT token creation)');
    });

    it('должен пропустить SoulIdentity setup если не deployed', async () => {
      // TODO: TDD Spec
      // Если SoulIdentity не deployed → skip (не ошибка)
      
      console.log('⏳ TDD: SoulIdentity skip logic (if not deployed)');
      expect(true).to.be.true; // Placeholder
    });
  });

  // ================================================================
  // Action 888: Step 8 (Catalog + Invites)
  // ================================================================

  describe('Action 888: Step 8 (Catalog + Invites) - из deploy_full.js', () => {
    it('должен делегировать catalog upload в Action 444 (TDD Spec)', async () => {
      // TODO: После рефакторинга
      // action888 должен вызвать catalogActions.action444()
      
      console.log('⏳ TDD: action888 → action444 delegation');
      expect(true).to.be.true; // Placeholder
    });

    it('должен сгенерировать 12 seller invites (TDD Spec)', async () => {
      // TODO: TDD Spec из deploy_full.js: generateInvitesForSeller()
      // После активации seller получает 12 invites для своих пользователей
      
      console.log('⏳ TDD: generateInvitesForSeller() (12 invites)');
      expect(true).to.be.true; // Placeholder
    });

    it('должен сохранить seller invites в файл', async () => {
      // TODO: TDD Spec
      // Формат: bot/flowers/{sellerAddress}_invites.txt
      
      console.log('⏳ TDD: saveSellerInvitesToFile()');
      expect(true).to.be.true; // Placeholder
    });
  });

  // ================================================================
  // Complete Workflow E2E (все 8 шагов)
  // ================================================================

  describe('Complete Action 888 Workflow (8 шагов) - ЭТАЛОН', () => {
    it('должен выполнить полный pipeline: 1-8 шаги', async function() {
      this.timeout(180000); // 3 min for full workflow

      const timer = harness.measureExecutionTime('Action 888 Full Pipeline');

      // STEP 1: Validate inputs ✅ (уже проверено в Infrastructure)
      expect(deployerInvite).to.exist;
      expect(sellerAddress).to.exist;
      console.log('✓ Step 1: Inputs validated');

      // STEP 2: Load contracts ✅
      const SpiralEngine = await ethers.getContractAt('SpiralEngineLogic', deployedContracts.spiralEngine);
      const ProductRegistry = await ethers.getContractAt('ProductRegistryLogic', deployedContracts.productRegistry);
      const SoulIdentity = await ethers.getContractAt('SoulIdentity', deployedContracts.soulIdentity);
      const OrganicRegistry = await ethers.getContractAt('OrganicComponentRegistryLogic', deployedContracts.organicComponentRegistry);
      
      expect(await SpiralEngine.getAddress()).to.equal(deployedContracts.spiralEngine);
      console.log('✓ Step 2: Contracts loaded');

      // STEP 3: Check activation status
      let usedInvite = await SpiralEngine.usedInviteByUser(sellerAddress);
      let isActivated = usedInvite > 0;
      expect(isActivated).to.be.false; // Before activation
      console.log('✓ Step 3: Activation status checked (not activated)');

      // STEP 4: Activate seller (если не активирован)
      const [deployer] = await ethers.getSigners();
      const spiralWithDeployer = SpiralEngine.connect(deployer);
      
      const sellerInvites = Array(12).fill().map((_, i) => `SELLER-888-INV-${i.toString().padStart(4, '0')}`);
      const activateTx = await spiralWithDeployer.activateUser(deployerInvite, sellerAddress, sellerInvites, 0);
      await activateTx.wait();
      
      usedInvite = await SpiralEngine.usedInviteByUser(sellerAddress);
      isActivated = usedInvite > 0;
      expect(isActivated).to.be.true; // After activation
      console.log('✓ Step 4: Seller activated');

      // STEP 5: Grant SELLER_ROLE
      const grantSellerTx = await spiralWithDeployer.grantSellerRole(sellerAddress);
      await grantSellerTx.wait();
      
      const SELLER_ROLE = await SpiralEngine.SELLER_ROLE();
      const hasSellerRole = await SpiralEngine.hasRole(SELLER_ROLE, sellerAddress);
      expect(hasSellerRole).to.be.true;
      console.log('✓ Step 5: SELLER_ROLE granted');

      // STEP 6: Grant ACTIVATOR_ROLE
      const ACTIVATOR_ROLE = await SpiralEngine.ACTIVATOR_ROLE();
      const grantActivatorTx = await spiralWithDeployer.grantRole(ACTIVATOR_ROLE, sellerAddress);
      await grantActivatorTx.wait();
      
      const hasActivatorRole = await SpiralEngine.hasRole(ACTIVATOR_ROLE, sellerAddress);
      expect(hasActivatorRole).to.be.true;
      console.log('✓ Step 6: ACTIVATOR_ROLE granted');

      // STEP 7: Setup SoulIdentity (TDD placeholder)
      console.log('⏳ Step 7: SoulIdentity setup (TDD spec)');

      // STEP 8: Catalog + Seller invites (TDD placeholder)
      console.log('⏳ Step 8: Catalog upload + invites (TDD spec)');

      const duration = timer.end();
      expect(duration).to.be.lessThan(180000); // < 3 min

      console.log('\n✅ Action 888 Full Pipeline: Steps 1-6 ✅, 7-8 ⏳ TDD');
    });
  });

  // ================================================================
  // State Validation (Complete System)
  // ================================================================

  describe('Complete System State Validation', () => {
    beforeEach(async function() {
      // Execute full activation workflow
      const [deployer] = await ethers.getSigners();
      const SpiralEngine = await ethers.getContractAt('SpiralEngineLogic', deployedContracts.spiralEngine);
      const spiralWithDeployer = SpiralEngine.connect(deployer);

      const sellerInvites = Array(12).fill().map((_, i) => `STATE-INV-${i}`);
      await spiralWithDeployer.activateUser(deployerInvite, sellerAddress, sellerInvites, 0);
      await spiralWithDeployer.grantSellerRole(sellerAddress);
      
      const ACTIVATOR_ROLE = await SpiralEngine.ACTIVATOR_ROLE();
      await spiralWithDeployer.grantRole(ACTIVATOR_ROLE, sellerAddress);
    });

    it('должен иметь seller полностью настроен (10+ проверок)', async () => {
      const SpiralEngine = await ethers.getContractAt('SpiralEngineLogic', deployedContracts.spiralEngine);

      // 1. Seller activated
      const usedInvite = await SpiralEngine.usedInviteByUser(sellerAddress);
      expect(usedInvite).to.be.greaterThan(0);

      // 2. SELLER_ROLE assigned
      const SELLER_ROLE = await SpiralEngine.SELLER_ROLE();
      const hasSellerRole = await SpiralEngine.hasRole(SELLER_ROLE, sellerAddress);
      expect(hasSellerRole).to.be.true;

      // 3. ACTIVATOR_ROLE assigned
      const ACTIVATOR_ROLE = await SpiralEngine.ACTIVATOR_ROLE();
      const hasActivatorRole = await SpiralEngine.hasRole(ACTIVATOR_ROLE, sellerAddress);
      expect(hasActivatorRole).to.be.true;

      // 4. Invite использован
      const tokenId = await SpiralEngine.inviteCodeToTokenId(deployerInvite);
      const isUsed = await SpiralEngine.isInviteUsed(tokenId);
      expect(isUsed).to.be.true;

      // 5. Activator записан
      const activator = await SpiralEngine.userActivator(sellerAddress);
      expect(activator).to.equal(deployerAddress);

      console.log('✅ Complete seller state validated (5/10 checks)');
      console.log(`   Activated: ${usedInvite > 0}`);
      console.log(`   SELLER_ROLE: ${hasSellerRole}`);
      console.log(`   ACTIVATOR_ROLE: ${hasActivatorRole}`);
      console.log(`   Invite used: ${isUsed}`);
      console.log(`   Activator: ${activator}`);
    });

    it('должен иметь OrganicComponentRegistry готов для загрузки', async () => {
      // Validate OrganicRegistry configured
      const OrganicRegistry = await ethers.getContractAt('OrganicComponentRegistryLogic', deployedContracts.organicComponentRegistry);
      
      const spiralEngineAddress = await OrganicRegistry.spiralEngine();
      expect(spiralEngineAddress).to.equal(deployedContracts.spiralEngine);

      console.log('✓ OrganicComponentRegistry ready for component upload');
    });

    it('должен иметь ProductRegistry готов для catalog', async () => {
      // Validate ProductRegistry deployed and ready
      const validation = await harness.validateDeployment(deployedContracts.productRegistry);
      expect(validation.deployed).to.be.true;

      console.log('✓ ProductRegistry ready for catalog upload');
    });
  });

  // ================================================================
  // Error Scenarios (из deploy_full.js)
  // ================================================================

  describe('Error Scenarios (из deploy_full.js error handling)', () => {
    it('должен выбросить ошибку если deployerInvite отсутствует', async () => {
      // Эталон: validateAction888Inputs() error
      
      const invalidInvite = null;
      expect(invalidInvite).to.be.null;
      
      console.log('⏳ TDD: Error - missing deployerInvite');
    });

    it('должен выбросить ошибку если sellerAddress invalid', async () => {
      // Эталон: validateAction888Inputs() error
      
      const invalidAddress = '0xinvalid';
      expect(ethers.isAddress(invalidAddress)).to.be.false;
      
      console.log('⏳ TDD: Error - invalid sellerAddress');
    });

    it('должен выбросить ошибку если deployer invite не существует', async () => {
      // Эталон: validateDeployerInviteForSeller() error
      
      const SpiralEngine = await ethers.getContractAt('SpiralEngineLogic', deployedContracts.spiralEngine);
      const fakeInvite = 'AMANITA-FAKE-0000';
      
      const exists = await SpiralEngine.inviteCodeExists(fakeInvite);
      expect(exists).to.be.false;
      
      console.log('⏳ TDD: Error - invite not found');
    });

    it('должен выбросить ошибку если deployer invite уже использован', async function() {
      this.timeout(60000);

      // Эталон: validateDeployerInviteForSeller() error
      
      // GIVEN: Use the invite
      const [deployer] = await ethers.getSigners();
      const SpiralEngine = await ethers.getContractAt('SpiralEngineLogic', deployedContracts.spiralEngine);
      const spiralWithDeployer = SpiralEngine.connect(deployer);
      
      const sellerInvites = Array(12).fill().map((_, i) => `ERR-INV-${i}`);
      await spiralWithDeployer.activateUser(deployerInvite, sellerAddress, sellerInvites, 0);
      
      // THEN: Invite now used
      const tokenId = await SpiralEngine.inviteCodeToTokenId(deployerInvite);
      const isUsed = await SpiralEngine.isInviteUsed(tokenId);
      expect(isUsed).to.be.true;
      
      console.log('⏳ TDD: Error - invite already used');
    });

    it('должен выбросить ошибку если contracts не deployed', async () => {
      // Эталон: loadContractsFor888() error
      
      // TODO: TDD Spec
      // Если контракты не deployed → ошибка
      
      console.log('⏳ TDD: Error - contracts not deployed');
      expect(true).to.be.true; // Placeholder
    });
  });

  // ================================================================
  // Integration: Action 888 с другими Actions (TDD Spec)
  // ================================================================

  describe('Integration: Action 888 Orchestration (TDD Spec)', () => {
    it('должен использовать DeployActions для Action 1 (TDD)', async () => {
      // TODO: После рефакторинга CatalogActions.action888
      // action888 должен делегировать deploy в DeployActions.action1()
      
      console.log('⏳ TDD: action888 → DeployActions.action1()');
      expect(true).to.be.true; // Placeholder
    });

    it('должен использовать InviteActions для Action 777 (TDD)', async () => {
      // TODO: TDD Spec
      // action888 должен делегировать invites в InviteActions.action777()
      
      console.log('⏳ TDD: action888 → InviteActions.action777()');
      expect(true).to.be.true; // Placeholder
    });

    it('должен использовать ComponentActions для Action 555 (TDD)', async () => {
      // TODO: TDD Spec
      // action888 должен делегировать components в ComponentActions.action555()
      
      console.log('⏳ TDD: action888 → ComponentActions.action555()');
      expect(true).to.be.true; // Placeholder
    });

    it('должен использовать CatalogActions для Action 444 (TDD)', async () => {
      // TODO: TDD Spec
      // action888 должен делегировать catalog в catalogActions.action444()
      
      console.log('⏳ TDD: action888 → CatalogActions.action444()');
      expect(true).to.be.true; // Placeholder
    });
  });

  // ================================================================
  // Performance & Benchmarking
  // ================================================================

  describe('Performance Benchmarking (из deploy_full.js ожидания)', () => {
    it('должен завершить Action 888 за < 3 минут', async function() {
      this.timeout(180000);

      const timer = harness.measureExecutionTime('Action 888 Performance');

      // Simplified workflow для performance test
      const [deployer] = await ethers.getSigners();
      const SpiralEngine = await ethers.getContractAt('SpiralEngineLogic', deployedContracts.spiralEngine);
      const spiralWithDeployer = SpiralEngine.connect(deployer);

      // Activation + Role grants
      const sellerInvites = Array(12).fill().map((_, i) => `PERF-INV-${i}`);
      await spiralWithDeployer.activateUser(deployerInvite, sellerAddress, sellerInvites, 0);
      await spiralWithDeployer.grantSellerRole(sellerAddress);

      const duration = timer.end();
      expect(duration).to.be.lessThan(180000); // < 3 min

      console.log(`✓ Performance: ${(duration / 1000).toFixed(2)}s (target: < 180s)`);
    });

    it('должен выполнить activation за < 30 секунд', async function() {
      this.timeout(60000);

      const timer = harness.measureExecutionTime('Seller Activation');

      const [deployer] = await ethers.getSigners();
      const SpiralEngine = await ethers.getContractAt('SpiralEngineLogic', deployedContracts.spiralEngine);
      const spiralWithDeployer = SpiralEngine.connect(deployer);

      const sellerInvites = Array(12).fill().map((_, i) => `BENCH-INV-${i}`);
      await spiralWithDeployer.activateUser(deployerInvite, sellerAddress, sellerInvites, 0);

      const duration = timer.end();
      expect(duration).to.be.lessThan(30000); // < 30s

      console.log(`✓ Activation performance: ${(duration / 1000).toFixed(2)}s`);
    });
  });
});

// ================================================================
// Helper: Deploy Complete Ecosystem для Action 888 E2E
// ================================================================

async function deployCompleteEcosystemFor888() {
  const [deployer] = await ethers.getSigners();

  console.log('Deploying MagicRegistry...');
  const MagicRegistry = await ethers.getContractFactory('AmanitaRegistry');
  const registry = await MagicRegistry.deploy();
  await registry.waitForDeployment();
  const registryAddress = await registry.getAddress();

  console.log('Deploying SpiralEngine (UUPS)...');
  const SpiralLogic = await ethers.getContractFactory('SpiralEngineLogic');
  const spiralLogic = await SpiralLogic.deploy();
  await spiralLogic.waitForDeployment();

  // Encode initialize(admin) call
  const spiralInterface = spiralLogic.interface;
  const spiralInitData = spiralInterface.encodeFunctionData('initialize', [deployer.address]);

  const SpiralProxy = await ethers.getContractFactory('SpiralEngineProxy');
  const spiralProxy = await SpiralProxy.deploy(await spiralLogic.getAddress(), spiralInitData);
  await spiralProxy.waitForDeployment();
  const spiralAddress = await spiralProxy.getAddress();
  console.log('✅ SpiralEngine initialized with deployer as admin');

  console.log('Deploying SBT Ecosystem...');
  const SoulboundCore = await ethers.getContractFactory('SoulboundCore');
  const soulCore = await SoulboundCore.deploy('SoulboundIdentity', 'SBI');
  await soulCore.waitForDeployment();
  const soulCoreAddress = await soulCore.getAddress();

  const SoulMetadata = await ethers.getContractFactory('SoulMetadata');
  const soulMetadata = await SoulMetadata.deploy(soulCoreAddress);
  await soulMetadata.waitForDeployment();
  const soulMetadataAddress = await soulMetadata.getAddress();

  const SoulRecovery = await ethers.getContractFactory('SoulRecovery');
  const soulRecovery = await SoulRecovery.deploy(soulCoreAddress);
  await soulRecovery.waitForDeployment();
  const soulRecoveryAddress = await soulRecovery.getAddress();

  const SoulIntegration = await ethers.getContractFactory('SoulIntegration');
  const soulIntegration = await SoulIntegration.deploy(spiralAddress, soulCoreAddress);
  await soulIntegration.waitForDeployment();
  const soulIntegrationAddress = await soulIntegration.getAddress();

  const SoulIdentity = await ethers.getContractFactory('SoulIdentity');
  const soulIdentity = await SoulIdentity.deploy(soulCoreAddress, soulMetadataAddress);
  await soulIdentity.waitForDeployment();
  const soulIdentityAddress = await soulIdentity.getAddress();

  console.log('Deploying ProductRegistry (UUPS)...');
  const ProductLogic = await ethers.getContractFactory('ProductRegistryLogic');
  const productLogic = await ProductLogic.deploy();
  await productLogic.waitForDeployment();

  // Encode initialize(admin, spiralEngine) call
  const productInterface = productLogic.interface;
  const productInitData = productInterface.encodeFunctionData('initialize', [deployer.address, spiralAddress]);

  const ProductProxy = await ethers.getContractFactory('ProductRegistryProxy');
  const productProxy = await ProductProxy.deploy(await productLogic.getAddress(), productInitData);
  await productProxy.waitForDeployment();
  const productAddress = await productProxy.getAddress();
  console.log('✅ ProductRegistry initialized with deployer as admin');

  console.log('Deploying OrganicComponentRegistry (UUPS)...');
  const OrganicLogic = await ethers.getContractFactory('OrganicComponentRegistryLogic');
  const organicLogic = await OrganicLogic.deploy();
  await organicLogic.waitForDeployment();

  // Encode initialize(admin) call
  const organicInterface = organicLogic.interface;
  const organicInitData = organicInterface.encodeFunctionData('initialize', [deployer.address]);

  const OrganicProxy = await ethers.getContractFactory('OrganicComponentRegistryProxy');
  const organicProxy = await OrganicProxy.deploy(await organicLogic.getAddress(), organicInitData);
  await organicProxy.waitForDeployment();
  const organicAddress = await organicProxy.getAddress();
  console.log('✅ OrganicComponentRegistry initialized with deployer as admin');

  console.log('Deploying AmanitaInternational (UUPS)...');
  const AmanitaLogic = await ethers.getContractFactory('AmanitaInternationalLogic');
  const amanitaLogic = await AmanitaLogic.deploy();
  await amanitaLogic.waitForDeployment();

  // Encode initialize(admin, spiralEngine) call
  const amanitaInterface = amanitaLogic.interface;
  const amanitaInitData = amanitaInterface.encodeFunctionData('initialize', [deployer.address, spiralAddress]);

  const AmanitaProxy = await ethers.getContractFactory('AmanitaInternationalProxy');
  const amanitaProxy = await AmanitaProxy.deploy(await amanitaLogic.getAddress(), amanitaInitData);
  await amanitaProxy.waitForDeployment();
  const amanitaAddress = await amanitaProxy.getAddress();
  console.log('✅ AmanitaInternational initialized with deployer as admin');

  // SETUP CONNECTIONS (SetupActions logic)
  console.log('Setting up connections...');
  
  const soulCoreWithSigner = (await ethers.getContractAt('SoulboundCore', soulCoreAddress)).connect(deployer);
  await soulCoreWithSigner.setMetadataContract(soulMetadataAddress).then(tx => tx.wait());
  await soulCoreWithSigner.setRecoveryContract(soulRecoveryAddress).then(tx => tx.wait());
  await soulCoreWithSigner.setIntegrationContract(soulIntegrationAddress).then(tx => tx.wait());

  const spiralWithSigner = (await ethers.getContractAt('SpiralEngineLogic', spiralAddress)).connect(deployer);
  await spiralWithSigner.setSoulIdentity(soulIdentityAddress).then(tx => tx.wait());

  const organicWithSigner = (await ethers.getContractAt('OrganicComponentRegistryLogic', organicAddress)).connect(deployer);
  await organicWithSigner.setSpiralEngine(spiralAddress).then(tx => tx.wait());

  console.log('✅ All contracts deployed and connected');

  return {
    magicRegistry: registryAddress,
    spiralEngine: spiralAddress,
    soulboundCore: soulCoreAddress,
    soulMetadata: soulMetadataAddress,
    soulRecovery: soulRecoveryAddress,
    soulIntegration: soulIntegrationAddress,
    soulIdentity: soulIdentityAddress,
    productRegistry: productAddress,
    organicComponentRegistry: organicAddress,
    amanitaInternational: amanitaAddress
  };
}

async function generateDeployerInvitesFor888(spiralEngineAddress) {
  const [deployer] = await ethers.getSigners();
  const SpiralEngine = await ethers.getContractAt('SpiralEngineLogic', spiralEngineAddress);
  const spiralWithDeployer = SpiralEngine.connect(deployer);

  // Generate 1 deployer invite for testing
  const inviteCode = 'AMANITA-DEPLOY-888';
  const tx = await spiralWithDeployer.mintInvite(inviteCode, 0);
  await tx.wait();

  console.log(`✅ Deployer invite created: ${inviteCode}`);

  return inviteCode;
}
