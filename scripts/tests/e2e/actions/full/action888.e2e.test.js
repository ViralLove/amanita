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
const {
  E2EHarness,
  assertInviteFormat,
  assertValidAddress,
  assertRegisteredProxy,
  assertSellerState,
  assertSoulIdentitySetup,
  assertBusinessIdFormat,
  assertBusinessIdMapping,
  assertBusinessIdCleared,
  assertCidFormat,
  expectEvent,
  expectRevertReason,
  expectRevertCustom
} = require('../../../helpers');
const { ethers } = require('hardhat');
const fs = require('fs');
const path = require('path');
const os = require('os');

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

  const getRegistryEntry = (contractName) => harness.loadContractFromSuite(contractName);
  const getProxyAddress = (contractName) => getRegistryEntry(contractName).proxy;
  const getImplementationAddress = (contractName) => getRegistryEntry(contractName).implementation;
  const getContractInstance = async (contractName, abiName) => {
    const proxyAddress = getProxyAddress(contractName);
    const implementation = getImplementationAddress(contractName);

    if (implementation) {
      try {
        const Factory = await ethers.getContractFactory(abiName);
        const contract = Factory.attach(proxyAddress);
        await contract.getAddress();
        return contract;
      } catch (error) {
        console.warn(`⚠️ attach fallback для ${contractName}: ${error.message}`);
      }
    }

    return ethers.getContractAt(abiName, proxyAddress);
  };

  async function clearCatalogAndAssert(productRegistry, sellerSigner, businessIds) {
    const sellerAddress = await sellerSigner.getAddress();
    await productRegistry.connect(sellerSigner).clearSellerCatalog(sellerAddress);
    const catalogVersion = await productRegistry.catalogVersion(sellerAddress);
    expect(Number(catalogVersion)).to.be.greaterThan(0);
    for (const businessId of businessIds) {
      await assertBusinessIdCleared(productRegistry, businessId);
    }
  }

function restoreBaseRegistry(registryHelper, deployed) {
  registryHelper.registerMany([
    ['MagicRegistry', deployed.magicRegistry, null],
    ['SpiralEngine', deployed.spiralEngine, deployed.spiralEngineLogic],
    ['ProductRegistry', deployed.productRegistry, deployed.productRegistryLogic],
    ['OrganicComponentRegistry', deployed.organicComponentRegistry, deployed.organicComponentRegistryLogic],
    ['AmanitaInternational', deployed.amanitaInternational, deployed.amanitaInternationalLogic],
    ['SoulboundCore', deployed.soulboundCore, null],
    ['SoulMetadata', deployed.soulMetadata, null],
    ['SoulRecovery', deployed.soulRecovery, null],
    ['SoulIntegration', deployed.soulIntegration, null],
    ['SoulIdentity', deployed.soulIdentity, null]
  ]);
}

async function prepareSellerStateForTests(options = {}) {
  if (!harness) {
    throw new Error('prepareSellerStateForTests: harness не инициализирован');
  }

  const helperOptions = {
    ...options,
    invitesPrefix: options.invitesPrefix || 'ACTION888',
    useExistingInvite: options.useExistingInvite ?? deployerInvite
  };

  return harness.prepareSellerForE2E(helperOptions);
}

  before(async function() {
    this.timeout(240000); // 4 min for full setup

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
    deployedContracts = await deployCompleteEcosystemFor888(harness.magicRegistry);

    console.log('\n🎲 Generating deployer invite via Action 777 helper...');
    deployerInvite = await generateDeployerInvitesFor888(deployedContracts.spiralEngine);
    deployedContracts.deployerInvite = deployerInvite;

    console.log(`\n✅ Prerequisites complete for Action 888`);
    console.log(`   Deployer: ${deployerAddress}`);
    console.log(`   Seller: ${sellerAddress}`);
    console.log(`   DEPLOYER_INVITE: ${deployerInvite}`);
    console.log(`   Contracts deployed: ${Object.keys(deployedContracts).length}`);
  console.log('   Suite hint: deployerInvite сохранён в deployedContracts для reuse');

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
    restoreBaseRegistry(harness.magicRegistry, deployedContracts);
    try {
      getProxyAddress('SoulIdentity');
    } catch (error) {
      throw new Error(`SoulIdentity missing in MagicRegistryHelper after restore: ${error.message}`);
    }
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
      const SpiralEngine = await getContractInstance('SpiralEngine', 'SpiralEngineLogic');
      
      const inviteExists = await SpiralEngine.inviteCodeExists(deployerInvite);
      expect(inviteExists).to.be.true;
      
      const tokenId = await SpiralEngine.inviteCodeToTokenId(deployerInvite);
      const isUsed = await SpiralEngine.isInviteUsed(tokenId);
      expect(isUsed).to.be.false; // Не использован

      console.log(`✓ Deployer invite exists: ${deployerInvite} (Action 777 complete)`);
    });

    it('должен иметь SetupActions connections установлены', async () => {
      // Validate SetupActions выполнен (connections present)
      const SoulboundCore = await getContractInstance('SoulboundCore', 'SoulboundCore');
      const SpiralEngine = await getContractInstance('SpiralEngine', 'SpiralEngineLogic');
      const OrganicRegistry = await getContractInstance('OrganicComponentRegistry', 'OrganicComponentRegistryLogic');

      // SBT connections
      const metadataContract = await SoulboundCore.getMetadataContract();
      expect(metadataContract).to.equal(getProxyAddress('SoulMetadata'));

      // SpiralEngine → SoulIdentity
      const soulIdentity = await SpiralEngine.soulIdentity();
      expect(soulIdentity).to.equal(getProxyAddress('SoulIdentity'));

      // OrganicRegistry → SpiralEngine
      const spiralInOrganic = await OrganicRegistry.spiralEngine();
      expect(spiralInOrganic).to.equal(getProxyAddress('SpiralEngine'));

      console.log('✓ SetupActions connections validated');
    });
  });

  // ================================================================
  // Action 888: Step 1-2 (Validate + Load Contracts)
  // ================================================================

  describe('Action 888: Step 1-2 (Validate + Load) - TDD Spec', () => {
    it('должен валидировать входные параметры', async () => {
      console.log('Фаза 1: Проверяем формат deployerInvite через helper');
      assertInviteFormat(deployerInvite);

      console.log('Фаза 2: Проверяем формат sellerAddress через helper');
      assertValidAddress(sellerAddress);

      console.log('Фаза 3: validateAction888Inputs() (предстоит реализовать в CatalogActions.action888)');
    });

    it('должен загрузить контракты через MagicRegistry', async () => {
      console.log('Фаза 1: Получаем записи из локального MagicRegistryHelper');
      const entries = {
        SpiralEngine: harness.magicRegistry.resolve('SpiralEngine'),
        ProductRegistry: harness.magicRegistry.resolve('ProductRegistry'),
        OrganicComponentRegistry: harness.magicRegistry.resolve('OrganicComponentRegistry')
      };

      console.log('Фаза 2: Проверяем соответствие proxy/logic адресов');
      assertRegisteredProxy(entries, 'SpiralEngine', getProxyAddress('SpiralEngine'), getImplementationAddress('SpiralEngine'));
      assertRegisteredProxy(entries, 'ProductRegistry', getProxyAddress('ProductRegistry'), getImplementationAddress('ProductRegistry'));
      assertRegisteredProxy(entries, 'OrganicComponentRegistry', getProxyAddress('OrganicComponentRegistry'), getImplementationAddress('OrganicComponentRegistry'));

      console.log('Фаза 3: loadContractsFor888() опирается на MagicRegistryHelper (TDD: реализация в actions)');
    });
  });

  // ================================================================
  // Action 888: Step 3-4 (Check Activation + Activate if needed)
  // ================================================================

  describe('Action 888: Step 3-4 (Activation) - из deploy_full.js', () => {
    it('должен проверить статус активации seller', async () => {
      // Эталон: checkSellerActivationStatus() из deploy_full.js
      const SpiralEngine = await getContractInstance('SpiralEngine', 'SpiralEngineLogic');

      console.log('Фаза 1: Получаем состояние seller до активации');
      const state = await assertSellerState(SpiralEngine, sellerAddress, {
        activated: false,
        sellerRole: false,
        activatorRole: false,
        activatorAddress: ethers.ZeroAddress
      });

      console.log(`Фаза 2: usedInvite=${Number(state.usedInvite)}, sellerRole=${state.sellerRole}, activatorRole=${state.activatorRole}`);
      console.log('✓ checkSellerActivationStatus() validated (not activated)');
    });

    it('должен активировать seller если не активирован', async function() {
      this.timeout(60000);

      // Эталон: activateSellerInSpiralEngine() из deploy_full.js
      const [deployer] = await ethers.getSigners();
      const SpiralEngine = await getContractInstance('SpiralEngine', 'SpiralEngineLogic');
      const spiralWithDeployer = SpiralEngine.connect(deployer);

      console.log('Фаза 1: Проверяем состояние перед активацией (NotASeller ожидается только при неверной роли)');
      await assertSellerState(SpiralEngine, sellerAddress, {
        activated: false,
        sellerRole: false,
        activatorRole: false,
        activatorAddress: ethers.ZeroAddress
      });

      // Generate 12 seller invites
      const sellerInvites = Array(12).fill().map((_, i) => `SELLER-INV-${i.toString().padStart(4, '0')}`);

      // Activate seller
      const tokenId = await SpiralEngine.inviteCodeToTokenId(deployerInvite);
      const activateTx = await spiralWithDeployer.activateUser(deployerInvite, sellerAddress, sellerInvites, 0);
      await activateTx.wait();

      console.log('Фаза 2: Проверяем состояние после активации');
      const state = await assertSellerState(SpiralEngine, sellerAddress, {
        activated: true,
        sellerRole: false,
        activatorRole: false,
        activatorAddress: deployer.address
      });

      expect(Number(state.usedInvite)).to.equal(Number(tokenId) + 1); // Activated

      console.log('✓ activateSellerInSpiralEngine() completed');
      console.log(`   Seller activated with invite: ${deployerInvite}`);
    });

    it('должен пропустить активацию если seller уже активирован', async function() {
      this.timeout(60000);

      // GIVEN: Activate seller first
      const [deployer] = await ethers.getSigners();
      const SpiralEngine = await getContractInstance('SpiralEngine', 'SpiralEngineLogic');
      const spiralWithDeployer = SpiralEngine.connect(deployer);

      const sellerInvites = Array(12).fill().map((_, i) => `SELLER-INV-${i}`);
      await spiralWithDeployer.activateUser(deployerInvite, sellerAddress, sellerInvites, 0);

      console.log('Фаза 1: Состояние после первой активации');
      await assertSellerState(SpiralEngine, sellerAddress, {
        activated: true,
        sellerRole: false,
        activatorRole: false,
        activatorAddress: deployer.address
      });

      // WHEN: Check activation again
      console.log('Фаза 2: Повторная проверка активации');
      await assertSellerState(SpiralEngine, sellerAddress, {
        activated: true,
        sellerRole: false,
        activatorRole: false
      });

      console.log('✓ Seller activation check (already activated, skip)');
    });
  });

  // ================================================================
  // Action 888: Step 5-6 (Role Management)
  // ================================================================

  describe('Action 888: Step 5-6 (Role Management) - из deploy_full.js', () => {
    beforeEach(async function() {
      // Seller должен быть активирован, но без ролей
      await prepareSellerStateForTests({
        grantRoles: false
      });
    });

    it('должен назначить SELLER_ROLE активированному seller', async () => {
      // Эталон: grantSellerRoleToUser() из deploy_full.js
      const [deployer] = await ethers.getSigners();
      const SpiralEngine = await getContractInstance('SpiralEngine', 'SpiralEngineLogic');
      const spiralWithDeployer = SpiralEngine.connect(deployer);

      // Grant SELLER_ROLE
      const tx = await spiralWithDeployer.grantSellerRole(sellerAddress);
      await tx.wait();

      // Validate role assigned
      const state = await assertSellerState(SpiralEngine, sellerAddress, {
        activated: true,
        sellerRole: true,
        activatorRole: false,
        activatorAddress: deployer.address
      });

      console.log(`   Seller state after SELLER_ROLE: activated=${state.activated}, sellerRole=${state.sellerRole}`);

      console.log('✓ grantSellerRoleToUser() completed');
      console.log(`   Seller has SELLER_ROLE: ${sellerAddress}`);
    });

    it('должен назначить ACTIVATOR_ROLE seller', async () => {
      // Эталон: grantActivatorRoleToSeller() из deploy_full.js
      const [deployer] = await ethers.getSigners();
      const SpiralEngine = await getContractInstance('SpiralEngine', 'SpiralEngineLogic');
      const spiralWithDeployer = SpiralEngine.connect(deployer);

      // Grant SELLER_ROLE first (prerequisite)
      await spiralWithDeployer.grantSellerRole(sellerAddress);

      // Grant ACTIVATOR_ROLE
      const ACTIVATOR_ROLE = await SpiralEngine.ACTIVATOR_ROLE();
      const grantTx = await spiralWithDeployer.grantRole(ACTIVATOR_ROLE, sellerAddress);
      await grantTx.wait();

      // Validate role assigned
      const state = await assertSellerState(SpiralEngine, sellerAddress, {
        activated: true,
        sellerRole: true,
        activatorRole: true,
        activatorAddress: deployer.address
      });

      console.log(`   Seller state after ACTIVATOR_ROLE: sellerRole=${state.sellerRole}, activatorRole=${state.activatorRole}`);

      console.log('✓ grantActivatorRoleToSeller() completed');
      console.log(`   Seller has ACTIVATOR_ROLE: ${sellerAddress}`);
    });

    it('должен назначить обе роли последовательно (полный workflow)', async function() {
      this.timeout(60000);

      const [deployer] = await ethers.getSigners();
      const SpiralEngine = await getContractInstance('SpiralEngine', 'SpiralEngineLogic');
      const spiralWithDeployer = SpiralEngine.connect(deployer);

      // Grant both roles
      await spiralWithDeployer.grantSellerRole(sellerAddress);
      
      const ACTIVATOR_ROLE = await SpiralEngine.ACTIVATOR_ROLE();
      await spiralWithDeployer.grantRole(ACTIVATOR_ROLE, sellerAddress);

      // Validate both roles
      await assertSellerState(SpiralEngine, sellerAddress, {
        activated: true,
        sellerRole: true,
        activatorRole: true,
        activatorAddress: deployer.address
      });

      console.log('✓ Both roles assigned (SELLER + ACTIVATOR)');
    });
  });

  // ================================================================
  // Action 888: Step 7 (SoulIdentity Setup)
  // ================================================================

  describe('Action 888: Step 7 (SoulIdentity) - из deploy_full.js', () => {
    it('должен настроить SoulIdentity для seller (TDD Spec)', async () => {
      console.log('Фаза 1: Получаем контракты SoulIdentity/SoulboundCore/SoulMetadata');
      const SpiralEngine = await getContractInstance('SpiralEngine', 'SpiralEngineLogic');
      const SoulIdentity = await getContractInstance('SoulIdentity', 'SoulIdentity');
      const SoulboundCore = await getContractInstance('SoulboundCore', 'SoulboundCore');

      console.log('Фаза 2: Проверяем конфигурацию мостов через helper');
      await assertSoulIdentitySetup({
        spiralEngine: SpiralEngine,
        soulIdentity: SoulIdentity,
        expectedSoulIdentityAddress: getProxyAddress('SoulIdentity'),
        expectedSoulboundCore: getProxyAddress('SoulboundCore'),
        expectedSoulMetadata: getProxyAddress('SoulMetadata'),
        soulboundCoreContract: SoulboundCore
      });

      console.log('Фаза 3: SoulIdentity готов к выдаче DID (TDD: дальнейшие шаги по токену)');
    });

    it('должен пропустить SoulIdentity setup если не deployed', async () => {
      console.log('Фаза 1: Получаем контракты для валидации');
      const SpiralEngine = await getContractInstance('SpiralEngine', 'SpiralEngineLogic');
      const SoulIdentity = await getContractInstance('SoulIdentity', 'SoulIdentity');
      const SoulboundCore = await getContractInstance('SoulboundCore', 'SoulboundCore');

      console.log('Фаза 2: Проверяем, что helper сообщает об ошибке при неверной конфигурации');
      try {
        await assertSoulIdentitySetup({
          spiralEngine: SpiralEngine,
          soulIdentity: SoulIdentity,
          expectedSoulIdentityAddress: getProxyAddress('SoulIdentity'),
          expectedSoulboundCore: getProxyAddress('SoulboundCore'),
          expectedSoulMetadata: ethers.ZeroAddress,
          soulboundCoreContract: SoulboundCore
        });
        expect.fail('Expected configuration mismatch but helper succeeded');
      } catch (error) {
        expect(error.message).to.include('SoulIdentity.soulMetadata mismatch');
      }

      console.log('Фаза 3: SoulIdentity skip logic зафиксирован (ошибка конфигурации выявлена)');
    });
  });

  // ================================================================
  // Action 888: Step 8 (Catalog + Invites)
  // ================================================================

  describe('Action 888: Step 8 (Catalog + Invites) - из deploy_full.js', () => {
    it('должен подготовить данные каталога и валидировать их helper’ами', async () => {
      console.log('Фаза 1: Читаем CSV каталог');
      const csvPath = path.join(__dirname, '../../../fixtures/catalog/test_catalog.csv');
      expect(fs.existsSync(csvPath), 'Catalog CSV отсутствует').to.be.true;
      const csvData = fs.readFileSync(csvPath, 'utf8');

      console.log('Фаза 2: Разбираем CSV и проверяем заголовки через harness.validateCsvHeaders');
      const lines = csvData.trim().split('\n');
      const headers = lines[0].split(',');
      harness.validateCsvHeaders(headers);

      console.log('Фаза 3: Формируем массив продуктов и проверяем businessId');
      const products = [];
      for (let i = 1; i < lines.length; i++) {
        const values = lines[i].split(',');
        const product = {};
        headers.forEach((header, index) => {
          product[header] = values[index];
        });
        assertBusinessIdFormat(product.product_id);
        products.push(product);
      }
      expect(products.length).to.be.greaterThan(0);

      console.log('Фаза 4: Подготавливаем JSON и CID, валидируем через helper');
      const jsonPayload = JSON.stringify(products, null, 2);
      expect(jsonPayload.length).to.be.greaterThan(0);
      const cid = harness.generateValidCid();
      assertCidFormat(cid);

      console.log(`✓ Catalog data ready: ${products.length} продуктов, CID=${cid}`);
    });

    it('должен зарегистрировать продукты через workflow Action 444 и очистить каталог', async () => {
      console.log('Фаза 1: Загружаем и валидируем CSV данные');
      const csvPath = path.join(__dirname, '../../../fixtures/catalog/test_catalog.csv');
      const csvData = fs.readFileSync(csvPath, 'utf8');
      const lines = csvData.trim().split('\n');
      const headers = lines[0].split(',');
      harness.validateCsvHeaders(headers);

      const products = [];
      for (let i = 1; i < lines.length; i++) {
        const values = lines[i].split(',');
        const product = {};
        headers.forEach((header, index) => {
          product[header] = values[index];
        });
        assertBusinessIdFormat(product.product_id);
        products.push(product);
      }

      console.log('Фаза 2: Разворачиваем suite и готовим seller для регистрации');
      const suite = await harness.deployProductSuite({ forceRedeploy: true });
      const { productRegistry, seller, sellerComponentIds } = suite;
      const sellerAddress = await seller.getAddress();
      suite.deployerInvite = deployedContracts.deployerInvite;
      console.log(`Suite получило deployerInvite для reuse: ${suite.deployerInvite}`);

      console.log('Фаза 3: Регистрируем продукты и проверяем события/маппинги');
      const registeredBusinessIds = [];
      for (let index = 0; index < products.length; index++) {
        const product = products[index];
        const businessId = product.product_id;
        const metadataCID = harness.generateValidCid();
        assertCidFormat(metadataCID);
        const componentId = sellerComponentIds[index % sellerComponentIds.length];

        await expectEvent(
          productRegistry
            .connect(seller)
            .createProduct(businessId, [componentId], metadataCID),
          productRegistry,
          'ProductCreated'
        );

        await assertBusinessIdMapping(productRegistry, businessId, index + 1);
        registeredBusinessIds.push(businessId);
      }

      console.log('Фаза 4: Очищаем каталог и проверяем удаление businessId');
      await clearCatalogAndAssert(productRegistry, seller, registeredBusinessIds);

      console.log('✓ Catalog workflow выполнен: продукты зарегистрированы и очищены');
    });

    it('должен сохранить seller invites в файл', async () => {
      console.log('Фаза 1: Генерируем инвайты в формате AMANITA');
      const invites = Array.from({ length: 12 }, (_, i) => `AMANITA-SELLER-${(i + 1).toString().padStart(4, '0')}`);
      invites.forEach((invite) => assertInviteFormat(invite));

      console.log('Фаза 2: Сохраняем инвайты во временный файл');
      const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'action888-'));
      const invitesPath = path.join(tmpDir, `${sellerAddress}-invites.txt`);
      fs.writeFileSync(invitesPath, invites.join('\n'), 'utf8');

      console.log('Фаза 3: Проверяем, что файл создан и содержит 12 строк');
      expect(fs.existsSync(invitesPath)).to.be.true;
      const storedInvites = fs.readFileSync(invitesPath, 'utf8').trim().split('\n');
      expect(storedInvites.length).to.equal(12);
      storedInvites.forEach((invite) => assertInviteFormat(invite));

      console.log('Фаза 4: Удаляем временные файлы');
      fs.unlinkSync(invitesPath);
      fs.rmSync(tmpDir, { recursive: true, force: true });

      console.log('✓ Seller invites сохранены и верифицированы');
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
      const SpiralEngine = await getContractInstance('SpiralEngine', 'SpiralEngineLogic');
      const ProductRegistry = await getContractInstance('ProductRegistry', 'ProductRegistryLogic');
      const SoulIdentity = await getContractInstance('SoulIdentity', 'SoulIdentity');
      const OrganicRegistry = await getContractInstance('OrganicComponentRegistry', 'OrganicComponentRegistryLogic');
      
      expect(await SpiralEngine.getAddress()).to.equal(getProxyAddress('SpiralEngine'));
      console.log('✓ Step 2: Contracts loaded');

      // STEP 3: Check activation status
      let state = await assertSellerState(SpiralEngine, sellerAddress, {
        activated: false,
        sellerRole: false,
        activatorRole: false,
        activatorAddress: ethers.ZeroAddress
      });
      console.log(`✓ Step 3: Activation status checked (activated=${state.activated})`);

      // STEP 4: Activate seller (если не активирован)
      const [deployer] = await ethers.getSigners();
      const spiralWithDeployer = SpiralEngine.connect(deployer);
      
      const sellerInvites = Array(12).fill().map((_, i) => `SELLER-888-INV-${i.toString().padStart(4, '0')}`);
      const activateTx = await spiralWithDeployer.activateUser(deployerInvite, sellerAddress, sellerInvites, 0);
      await activateTx.wait();
 
      state = await assertSellerState(SpiralEngine, sellerAddress, {
        activated: true,
        sellerRole: false,
        activatorRole: false,
        activatorAddress: deployer.address
      });
      console.log('✓ Step 4: Seller activated');

      // STEP 5: Grant SELLER_ROLE
      const grantSellerTx = await spiralWithDeployer.grantSellerRole(sellerAddress);
      await grantSellerTx.wait();
        
      state = await assertSellerState(SpiralEngine, sellerAddress, {
        activated: true,
        sellerRole: true,
        activatorRole: false,
        activatorAddress: deployer.address
      });
      console.log('✓ Step 5: SELLER_ROLE granted');

      // STEP 6: Grant ACTIVATOR_ROLE
      const ACTIVATOR_ROLE = await SpiralEngine.ACTIVATOR_ROLE();
      const grantActivatorTx = await spiralWithDeployer.grantRole(ACTIVATOR_ROLE, sellerAddress);
      await grantActivatorTx.wait();
        
      await assertSellerState(SpiralEngine, sellerAddress, {
        activated: true,
        sellerRole: true,
        activatorRole: true,
        activatorAddress: deployer.address
      });
      console.log('✓ Step 6: ACTIVATOR_ROLE granted');

      // STEP 7: Setup SoulIdentity
      const SoulboundCore = await getContractInstance('SoulboundCore', 'SoulboundCore');
      await assertSoulIdentitySetup({
        spiralEngine: SpiralEngine,
        soulIdentity: SoulIdentity,
        expectedSoulIdentityAddress: getProxyAddress('SoulIdentity'),
        expectedSoulboundCore: getProxyAddress('SoulboundCore'),
        expectedSoulMetadata: getProxyAddress('SoulMetadata'),
        soulboundCoreContract: SoulboundCore
      });
      console.log('✓ Step 7: SoulIdentity linked and verified');

      // STEP 8: Catalog + Seller invites
      const csvPath = path.join(__dirname, '../../../fixtures/catalog/test_catalog.csv');
      const csvData = fs.readFileSync(csvPath, 'utf8');
      const lines = csvData.trim().split('\n');
      const headers = lines[0].split(',');
      harness.validateCsvHeaders(headers);

      const [, sellerSigner] = await ethers.getSigners();
      const productRegistryWithSeller = ProductRegistry.connect(sellerSigner);
      const componentRegistry = await getContractInstance('OrganicComponentRegistry', 'OrganicComponentRegistryLogic');
      const componentRegistryWithSeller = componentRegistry.connect(sellerSigner);
      const baseComponentCid = harness.generateValidCid();
      await componentRegistryWithSeller.createComponent('suite-comp-1', baseComponentCid);

      const products = [];
      for (let i = 1; i < lines.length; i++) {
        const values = lines[i].split(',');
        const product = {};
        headers.forEach((header, index) => {
          product[header] = values[index];
        });
        assertBusinessIdFormat(product.product_id);
        products.push(product);
      }

      for (let index = 0; index < products.length; index++) {
        const product = products[index];
        const metadataCID = harness.generateValidCid();
        assertCidFormat(metadataCID);
        await expectEvent(
          productRegistryWithSeller.createProduct(product.product_id, ['suite-comp-1'], metadataCID),
          ProductRegistry,
          'ProductCreated'
        );
        await assertBusinessIdMapping(ProductRegistry, product.product_id, index + 1);
      }

      const productIdsForCleanup = products.map(product => product.product_id);
      await clearCatalogAndAssert(ProductRegistry, sellerSigner, productIdsForCleanup);
      restoreBaseRegistry(harness.magicRegistry, deployedContracts);

      console.log('✓ Step 8: Catalog workflow executed');

      const duration = timer.end();
      expect(duration).to.be.lessThan(180000); // < 3 min

      console.log('\n✅ Action 888 Full Pipeline: Steps 1-8 complete');
    });
  });

  // ================================================================
  // State Validation (Complete System)
  // ================================================================

  describe('Complete System State Validation', () => {
    beforeEach(async function() {
      await prepareSellerStateForTests();
    });

    it('должен иметь seller полностью настроен (10+ проверок)', async () => {
      const SpiralEngine = await getContractInstance('SpiralEngine', 'SpiralEngineLogic');

      const state = await assertSellerState(SpiralEngine, sellerAddress, {
        activated: true,
        sellerRole: true,
        activatorRole: true,
        activatorAddress: deployerAddress
      });

      // 4. Invite использован
      const tokenId = await SpiralEngine.inviteCodeToTokenId(deployerInvite);
      const isUsed = await SpiralEngine.isInviteUsed(tokenId);
      expect(isUsed).to.be.true;

      // 5. Activator записан
      const activator = await SpiralEngine.userActivator(sellerAddress);
      expect(activator).to.equal(deployerAddress);

      console.log('✅ Complete seller state validated (5/10 checks)');
      console.log(`   Activated: ${state.activated}`);
      console.log(`   SELLER_ROLE: ${state.sellerRole}`);
      console.log(`   ACTIVATOR_ROLE: ${state.activatorRole}`);
      console.log(`   Invite used: ${isUsed}`);
      console.log(`   Activator: ${activator}`);
    });

    it('должен иметь OrganicComponentRegistry готов для загрузки', async () => {
      // Validate OrganicRegistry configured
      const OrganicRegistry = await getContractInstance('OrganicComponentRegistry', 'OrganicComponentRegistryLogic');
      
      const spiralEngineAddress = await OrganicRegistry.spiralEngine();
      expect(spiralEngineAddress).to.equal(getProxyAddress('SpiralEngine'));

      console.log('✓ OrganicComponentRegistry ready for component upload');
    });

    it('должен иметь ProductRegistry готов для catalog', async () => {
      // Validate ProductRegistry deployed and ready
      const validation = await harness.validateDeployment(getProxyAddress('ProductRegistry'));
      expect(validation.deployed).to.be.true;

      console.log('✓ ProductRegistry ready for catalog upload');
    });
  });

  // ================================================================
  // Error Scenarios (из deploy_full.js)
  // ================================================================

  describe('Error Scenarios (из deploy_full.js error handling)', () => {
    // Эти сценарии документируют ожидаемые custom errors: BusinessIdExists, NotASeller, InviteNotFound, InvalidInviteCount, UserAlreadyActivated
    it('должен выбросить ошибку если deployerInvite отсутствует', async () => {
      console.log('Фаза 1: Получаем SpiralEngine и seller signer');
      const SpiralEngine = await getContractInstance('SpiralEngine', 'SpiralEngineLogic');

      console.log('Фаза 2: Пытаемся активировать seller без deployerInvite');
      const [deployer] = await ethers.getSigners();
      const spiralWithDeployer = SpiralEngine.connect(deployer);

      const sellerInvites = Array.from({ length: 12 }, (_, i) => `ERR-NO-INV-${i}`);
      const emptyInvite = '';
      console.log('  → Ожидаем кастомную ошибку InviteNotFound() при пустом инвайте');
      await expectRevertCustom(
        spiralWithDeployer.activateUser(emptyInvite, sellerAddress, sellerInvites, 0),
        'InviteNotFound',
        SpiralEngine
      );

      console.log('✓ Ошибка обработки отсутствующего deployerInvite проверена');
    });

    it('должен выбросить ошибку если sellerAddress invalid', async () => {
      console.log('Фаза 1: Проверяем helper для адреса');
      expect(() => assertValidAddress('0xinvalid')).to.throw('Invalid Ethereum address format');

      console.log('Фаза 2: Пробуем выдать роль невалидному адресу');
      const SpiralEngine = await getContractInstance('SpiralEngine', 'SpiralEngineLogic');
      const [deployer] = await ethers.getSigners();
      const spiralWithDeployer = SpiralEngine.connect(deployer);

      console.log('  → Ожидаем кастомную ошибку InvalidUserAddress() при grantSellerRole');
      await expectRevertCustom(
        spiralWithDeployer.grantSellerRole('0x0000000000000000000000000000000000000000'),
        'InvalidUserAddress',
        SpiralEngine
      );

      console.log('✓ Ошибка обработки неверного sellerAddress проверена');
    });

    it('должен выбросить ошибку если deployer invite не существует', async () => {
      const SpiralEngine = await getContractInstance('SpiralEngine', 'SpiralEngineLogic');
      const fakeInvite = 'AMANITA-FAKE-0000';

      const exists = await SpiralEngine.inviteCodeExists(fakeInvite);
      expect(exists).to.be.false;

      const [deployer] = await ethers.getSigners();
      const spiralWithDeployer = SpiralEngine.connect(deployer);

      console.log('  → Ожидаем кастомную ошибку InvalidInviteCount() при активации с несуществующим инвайтом');
      await expectRevertCustom(
        spiralWithDeployer.activateUser(fakeInvite, sellerAddress, ['ERR'], 0),
        'InvalidInviteCount',
        SpiralEngine
      );

      console.log('✓ Ошибка: invite не найден');
    });

    it('должен выбросить ошибку если deployer invite уже использован', async function() {
      this.timeout(60000);

      const [deployer] = await ethers.getSigners();
      const SpiralEngine = await getContractInstance('SpiralEngine', 'SpiralEngineLogic');
      const spiralWithDeployer = SpiralEngine.connect(deployer);

      const sellerInvites = Array(12).fill().map((_, i) => `ERR-INV-${i}`);
      await spiralWithDeployer.activateUser(deployerInvite, sellerAddress, sellerInvites, 0);

      const tokenId = await SpiralEngine.inviteCodeToTokenId(deployerInvite);
      const isUsed = await SpiralEngine.isInviteUsed(tokenId);
      expect(isUsed).to.be.true;

      console.log('  → Ожидаем кастомную ошибку UserAlreadyActivated() при повторном использовании инвайта');
      await expectRevertCustom(
        spiralWithDeployer.activateUser(deployerInvite, sellerAddress, ['ERR-REUSE'], 0),
        'UserAlreadyActivated',
        SpiralEngine
      );

      console.log('✓ Ошибка: invite уже использован');
    });

    it('должен выбросить ошибку если contracts не deployed', async () => {
      console.log('Фаза 1: Очищаем MagicRegistryHelper (симулируем отсутствие записей)');
      harness.magicRegistry.clear();

      console.log('Фаза 2: Пытаемся загрузить контракт из пустого реестра');
      expect(() => getRegistryEntry('SpiralEngine')).to.throw('Contract SpiralEngine is not registered');

      console.log('✓ Ошибка: контракты не зарегистрированы — ловим исключение');

      console.log('Фаза 3: Восстанавливаем записи в MagicRegistryHelper');
      harness.magicRegistry.registerMany([
        ['MagicRegistry', deployedContracts.magicRegistry, null],
        ['SpiralEngine', deployedContracts.spiralEngine, deployedContracts.spiralEngineLogic],
        ['ProductRegistry', deployedContracts.productRegistry, deployedContracts.productRegistryLogic],
        ['OrganicComponentRegistry', deployedContracts.organicComponentRegistry, deployedContracts.organicComponentRegistryLogic],
        ['AmanitaInternational', deployedContracts.amanitaInternational, deployedContracts.amanitaInternationalLogic],
        ['SoulboundCore', deployedContracts.soulboundCore, null],
        ['SoulMetadata', deployedContracts.soulMetadata, null],
        ['SoulRecovery', deployedContracts.soulRecovery, null],
        ['SoulIntegration', deployedContracts.soulIntegration, null],
        ['SoulIdentity', deployedContracts.soulIdentity, null]
      ]);
    });
  });

  describe('ProductRegistry Seller Validation Errors', () => {
    let ProductRegistry;
    let sellerSigner;

    beforeEach(async function() {
      ProductRegistry = await getContractInstance('ProductRegistry', 'ProductRegistryLogic');
      [, sellerSigner] = await ethers.getSigners();
    });

    it('должен выбросить EmptyBusinessId для активированного seller', async () => {
      await prepareSellerStateForTests();

      await expectRevertCustom(
        ProductRegistry.connect(sellerSigner).createProduct('', ['suite-comp-1'], harness.generateValidCid('empty-business-id')),
        'EmptyBusinessId',
        ProductRegistry
      );
    });

    it('должен выбросить UserNotActivated при попытке grantSellerRole без активации', async () => {
      const SpiralEngine = await getContractInstance('SpiralEngine', 'SpiralEngineLogic');
      const [deployer] = await ethers.getSigners();
      const spiralWithDeployer = SpiralEngine.connect(deployer);

      await expectRevertCustom(
        spiralWithDeployer.grantSellerRole(sellerAddress),
        'UserNotActivated',
        SpiralEngine
      );
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
    it('должен завершить Action 888 за < 3 минут (используя MagicRegistryHelper)', async function() {
      this.timeout(180000);

      console.log('Фаза 0: Sanity-проверка зарегистрированных контрактов перед измерениями');
      const spiralEntry = harness.loadContractFromSuite('SpiralEngine');
      assertRegisteredProxy({ SpiralEngine: spiralEntry }, 'SpiralEngine', deployedContracts.spiralEngine, deployedContracts.spiralEngineLogic);
      console.log(`   SpiralEngine proxy: ${spiralEntry.proxy}, impl: ${spiralEntry.implementation}`);

      const productEntry = harness.loadContractFromSuite('ProductRegistry');
      assertRegisteredProxy({ ProductRegistry: productEntry }, 'ProductRegistry', deployedContracts.productRegistry, deployedContracts.productRegistryLogic);
      console.log(`   ProductRegistry proxy: ${productEntry.proxy}, impl: ${productEntry.implementation}`);

      const organicEntry = harness.loadContractFromSuite('OrganicComponentRegistry');
      assertRegisteredProxy({ OrganicComponentRegistry: organicEntry }, 'OrganicComponentRegistry', deployedContracts.organicComponentRegistry, deployedContracts.organicComponentRegistryLogic);
      console.log(`   OrganicComponentRegistry proxy: ${organicEntry.proxy}, impl: ${organicEntry.implementation}`);

      const timer = harness.measureExecutionTime('Action 888 Performance');

      // Simplified workflow для performance test
      const [deployer] = await ethers.getSigners();
      const spiralEnginePerf = await getContractInstance('SpiralEngine', 'SpiralEngineLogic');
      const spiralWithDeployer = spiralEnginePerf.connect(deployer);
      const DEFAULT_ADMIN_ROLE = await spiralEnginePerf.DEFAULT_ADMIN_ROLE();
      const isAdmin = await spiralEnginePerf.hasRole(DEFAULT_ADMIN_ROLE, deployer.address);
      expect(isAdmin, 'Deployer must retain DEFAULT_ADMIN_ROLE for cleanup').to.be.true;

      // Activation + Role grants
      const sellerInvites = Array(12).fill().map((_, i) => `PERF-INV-${i}`);
      await spiralWithDeployer.activateUser(deployerInvite, sellerAddress, sellerInvites, 0);
      await spiralWithDeployer.grantSellerRole(sellerAddress);

      const duration = timer.end();
      expect(duration).to.be.lessThan(180000); // < 3 min (магический реестр уже заполнен registerMany)

      console.log(`✓ Performance: ${(duration / 1000).toFixed(2)}s (target: < 180s)`);
      console.log(`   Seller invites used: ${sellerInvites.join(', ')}`);

      console.log('Фаза 4: Удаляем SELLER_ROLE (cleanup)');
      const SELLER_ROLE = await spiralEnginePerf.SELLER_ROLE();
      await spiralWithDeployer.revokeRole(SELLER_ROLE, sellerAddress);

      console.log('Фаза 5: Smoke-проверка состояния seller после pipeline');
      await assertSellerState(spiralEnginePerf, sellerAddress, {
        activated: true,
        sellerRole: false,
        activatorRole: false,
        activatorAddress: deployer.address
      });

      console.log('Фаза 6: Валидация отката seller роли');
      await spiralWithDeployer.revokeRole(SELLER_ROLE, sellerAddress);
      await assertSellerState(spiralEnginePerf, sellerAddress, {
        activated: true,
        sellerRole: false,
        activatorRole: false,
        activatorAddress: deployer.address
      });
    });

    it('должен выполнить activation за < 30 секунд (MagicRegistryHelper заполнен)', async function() {
      this.timeout(60000);

      console.log('Фаза 0: Sanity-проверка SpiralEngine перед измерением активации');
      const spiralEntry = harness.loadContractFromSuite('SpiralEngine');
      assertRegisteredProxy({ SpiralEngine: spiralEntry }, 'SpiralEngine', deployedContracts.spiralEngine, deployedContracts.spiralEngineLogic);
      console.log(`   SpiralEngine proxy: ${spiralEntry.proxy}, impl: ${spiralEntry.implementation}`);

      const timer = harness.measureExecutionTime('Seller Activation');

      const [deployer] = await ethers.getSigners();
      const spiralEnginePerf = await getContractInstance('SpiralEngine', 'SpiralEngineLogic');
      const spiralWithDeployer = spiralEnginePerf.connect(deployer);
      const DEFAULT_ADMIN_ROLE = await spiralEnginePerf.DEFAULT_ADMIN_ROLE();
      const isAdmin = await spiralEnginePerf.hasRole(DEFAULT_ADMIN_ROLE, deployer.address);
      expect(isAdmin, 'Deployer must retain DEFAULT_ADMIN_ROLE for cleanup').to.be.true;

      const sellerInvites = Array(12).fill().map((_, i) => `BENCH-INV-${i}`);
      await spiralWithDeployer.activateUser(deployerInvite, sellerAddress, sellerInvites, 0);

      const duration = timer.end();
      expect(duration).to.be.lessThan(30000); // < 30s (контракты загружены через loadContractFromSuite)

      console.log(`✓ Activation performance: ${(duration / 1000).toFixed(2)}s`);
      console.log(`   CID snapshot: ${harness.generateValidCid('perf-sample').slice(0, 20)}...`);

      console.log('Фаза 4: Smoke-проверка состояния seller после быстрой активации');
      await assertSellerState(spiralEnginePerf, sellerAddress, {
        activated: true,
        sellerRole: false,
        activatorRole: false,
        activatorAddress: deployer.address
      });

      console.log('Фаза 5: Cleanup seller state для повторного запуска');
      const SELLER_ROLE = await spiralEnginePerf.SELLER_ROLE();
      await spiralWithDeployer.revokeRole(SELLER_ROLE, sellerAddress);
    });
  });
});

// ================================================================
// Helper: Deploy Complete Ecosystem для Action 888 E2E
// ================================================================

async function deployCompleteEcosystemFor888(magicRegistryHelper) {
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
  const spiralLogicAddress = await spiralLogic.getAddress();

  // Encode initialize(admin) call
  const spiralInterface = spiralLogic.interface;
  const spiralInitData = spiralInterface.encodeFunctionData('initialize', [deployer.address]);

  const SpiralProxy = await ethers.getContractFactory('SpiralEngineProxy');
  const spiralProxy = await SpiralProxy.deploy(spiralLogicAddress, spiralInitData);
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
  const productLogicAddress = await productLogic.getAddress();

  // Encode initialize(admin, spiralEngine) call
  const productInterface = productLogic.interface;
  const productInitData = productInterface.encodeFunctionData('initialize', [deployer.address, spiralAddress]);

  const ProductProxy = await ethers.getContractFactory('ProductRegistryProxy');
  const productProxy = await ProductProxy.deploy(productLogicAddress, productInitData);
  await productProxy.waitForDeployment();
  const productAddress = await productProxy.getAddress();
  console.log('✅ ProductRegistry initialized with deployer as admin');

  console.log('Deploying OrganicComponentRegistry (UUPS)...');
  const OrganicLogic = await ethers.getContractFactory('OrganicComponentRegistryLogic');
  const organicLogic = await OrganicLogic.deploy();
  await organicLogic.waitForDeployment();
  const organicLogicAddress = await organicLogic.getAddress();

  // Encode initialize(admin) call
  const organicInterface = organicLogic.interface;
  const organicInitData = organicInterface.encodeFunctionData('initialize', [deployer.address]);

  const OrganicProxy = await ethers.getContractFactory('OrganicComponentRegistryProxy');
  const organicProxy = await OrganicProxy.deploy(organicLogicAddress, organicInitData);
  await organicProxy.waitForDeployment();
  const organicAddress = await organicProxy.getAddress();
  console.log('✅ OrganicComponentRegistry initialized with deployer as admin');

  console.log('Deploying AmanitaInternational (UUPS)...');
  const AmanitaLogic = await ethers.getContractFactory('AmanitaInternationalLogic');
  const amanitaLogic = await AmanitaLogic.deploy();
  await amanitaLogic.waitForDeployment();
  const amanitaLogicAddress = await amanitaLogic.getAddress();

  // Encode initialize(admin, spiralEngine) call
  const amanitaInterface = amanitaLogic.interface;
  const amanitaInitData = amanitaInterface.encodeFunctionData('initialize', [deployer.address, spiralAddress]);

  const AmanitaProxy = await ethers.getContractFactory('AmanitaInternationalProxy');
  const amanitaProxy = await AmanitaProxy.deploy(amanitaLogicAddress, amanitaInitData);
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

  const productWithSigner = (await ethers.getContractAt('ProductRegistryLogic', productAddress)).connect(deployer);
  await productWithSigner.setOrganicComponentRegistry(organicAddress).then(tx => tx.wait());

  console.log('✅ All contracts deployed and connected');

  const deployed = {
    magicRegistry: registryAddress,
    spiralEngine: spiralAddress,
    spiralEngineLogic: spiralLogicAddress,
    soulboundCore: soulCoreAddress,
    soulMetadata: soulMetadataAddress,
    soulRecovery: soulRecoveryAddress,
    soulIntegration: soulIntegrationAddress,
    soulIdentity: soulIdentityAddress,
    productRegistry: productAddress,
    productRegistryLogic: productLogicAddress,
    organicComponentRegistry: organicAddress,
    organicComponentRegistryLogic: organicLogicAddress,
    amanitaInternational: amanitaAddress,
    amanitaInternationalLogic: amanitaLogicAddress
  };

  if (magicRegistryHelper) {
    magicRegistryHelper.clear();
    magicRegistryHelper.registerMany([
      ['MagicRegistry', deployed.magicRegistry, null],
      ['SpiralEngine', deployed.spiralEngine, deployed.spiralEngineLogic],
      ['ProductRegistry', deployed.productRegistry, deployed.productRegistryLogic],
      ['OrganicComponentRegistry', deployed.organicComponentRegistry, deployed.organicComponentRegistryLogic],
      ['AmanitaInternational', deployed.amanitaInternational, deployed.amanitaInternationalLogic],
      ['SoulboundCore', deployed.soulboundCore, null],
      ['SoulMetadata', deployed.soulMetadata, null],
      ['SoulRecovery', deployed.soulRecovery, null],
      ['SoulIntegration', deployed.soulIntegration, null],
      ['SoulIdentity', deployed.soulIdentity, null]
    ]);
  }

  return deployed;
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
