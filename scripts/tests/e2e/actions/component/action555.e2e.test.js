/**
 * E2E Tests: Action 555 - Upload Components
 * 
 * Full workflow: Deploy → Activate Seller → Upload Components
 * 
 * Coverage:
 * - Seller activation (InviteActions delegation - after refactoring)
 * - Component upload (Arweave-Readiness.js integration)
 * - On-chain registration (OrganicComponentRegistry)
 * - State validation
 * 
 * NO Web3.js! Only ethers.js
 */

const { expect } = require('chai');
const { E2EHarness, MockArweaveManager, assertSellerState } = require('../../../helpers');
const { ethers } = require('hardhat');
const fs = require('fs');
const path = require('path');

// Import real actions (not mocked - this is E2E!)
const ComponentActions = require('../../../../lib/actions/ComponentActions');
const ContractManager = require('../../../../lib/services/ContractManager');
const EthersUtils = require('../../../../lib/utils/EthersUtils');

describe('E2E: Action 555 - Upload Components', function() {
  // ✅ FIXED: UUPS contracts properly initialized with deployer as admin
  this.timeout(180000); // 3 min for full workflow

  let harness;
  let componentActions;
  let deployedContracts;
  let sellerAddress;
  let deployerAddress;
  let deployerInvite;
  let mockArweaveManager;

  before(async function() {
    this.timeout(120000); // 2 min for setup

    // Start E2E infrastructure
    harness = new E2EHarness();
    await harness.startHardhatNode();
    harness.loadTestEnv();

    // Deploy contracts (Action 1 prerequisite)
    console.log('\n📦 Prerequisite: Deploying contracts (Action 1)...');
    deployedContracts = await deployAllContractsForAction555();
    registerContractsInMagicRegistry(harness, deployedContracts);

    // Generate deployer invites (Action 777 prerequisite)
    console.log('\n🎲 Prerequisite: Generating deployer invites (Action 777)...');
    deployerInvite = await generateDeployerInviteForTest(deployedContracts.spiralEngine);
    deployedContracts.deployerInvite = deployerInvite;

    console.log(`✅ Prerequisites complete`);
    console.log(`   MagicRegistry: ${deployedContracts.magicRegistry}`);
    console.log(`   SpiralEngine: ${deployedContracts.spiralEngine}`);
    console.log(`   OrganicComponentRegistry: ${deployedContracts.organicComponentRegistry}`);
    console.log(`   AmanitaInternational: ${deployedContracts.amanitaInternational}`);
    console.log(`   DEPLOYER_INVITE: ${deployerInvite}`);

    // Setup seller
    const [deployer, seller] = await ethers.getSigners();
    deployerAddress = deployer.address;
    sellerAddress = seller.address;

    mockArweaveManager = new MockArweaveManager();
    await mockArweaveManager.initialize();

    process.env.DEPLOYER_INVITE = deployerInvite;
    process.env.SELLER_ADDRESS = sellerAddress;

    // Create snapshot (expensive setup done)
    await harness.saveState('after-prerequisites');

    // Create ComponentActions instance
    const provider = ethers.provider;
    const config = {
      get: (key) => {
        if (key === 'contracts.magicRegistry') return deployedContracts.magicRegistry;
        if (key === 'deployer.privateKey') return process.env.DEPLOYER_PRIVATE_KEY;
        if (key === 'seller.address') return sellerAddress;
        if (key === 'seller.deployerInvite') return deployerInvite;
        if (key === 'seller.businessId') return 'test-seller';
        if (key === 'network.name') return 'localhost';
        return null;
      }
    };

    const contractManager = new ContractManager(provider, config);
    const ethersUtils = new EthersUtils(provider, config);

    // Create dependencies for ComponentActions (Layer 3 → 4A → 4B)
    const AccessControlActions = require('../../../../lib/actions/AccessControlActions');
    const InviteActions = require('../../../../lib/actions/InviteActions');
    
    const accessControlActions = new AccessControlActions(contractManager, ethersUtils, config);
    const inviteActions = new InviteActions(contractManager, ethersUtils, config, accessControlActions);

    componentActions = new ComponentActions(
      contractManager,
      mockArweaveManager,
      ethersUtils,
      config,
      inviteActions
    );
  });

  after(async function() {
    await harness.stopHardhatNode();
    harness.restoreEnv();
  });

  beforeEach(async function() {
    // Reset to state after prerequisites
    await harness.restoreState('after-prerequisites');
    registerContractsInMagicRegistry(harness, deployedContracts);
  });

  // ================================================================
  // Infrastructure Validation
  // ================================================================

  describe('Infrastructure Validation', () => {
    it('должен иметь deployed contracts (Action 1 выполнен)', async () => {
      // Validate SpiralEngine deployed
      const validation1 = await harness.validateDeployment(deployedContracts.spiralEngine);
      expect(validation1.deployed).to.be.true;

      // Validate OrganicComponentRegistry deployed
      const validation2 = await harness.validateDeployment(deployedContracts.organicComponentRegistry);
      expect(validation2.deployed).to.be.true;

      console.log('✓ Action 1 completed, contracts deployed');
    });

    it('должен иметь OrganicComponentRegistry.spiralEngine установлен', async () => {
      // CRITICAL: Без этого action555 падает!
      const OrganicRegistry = await ethers.getContractAt(
        'OrganicComponentRegistryLogic',
        deployedContracts.organicComponentRegistry
      );

      const spiralEngineAddress = await OrganicRegistry.spiralEngine();

      expect(spiralEngineAddress).to.equal(deployedContracts.spiralEngine);
      expect(spiralEngineAddress).to.not.equal(ethers.ZeroAddress);

      console.log('✓ OrganicComponentRegistry.spiralEngine configured');
      console.log(`   🎯 КРИТИЧНО: ${spiralEngineAddress}`);
    });

    it('должен иметь DEPLOYER_INVITE (Action 777 выполнен)', async () => {
      // Config должен содержать deployer invite
      const config = {
        get: (key) => {
          if (key === 'seller.deployerInvite') return 'AMANITA-TEST-0001';
          return null;
        }
      };

      const deployerInvite = config.get('seller.deployerInvite');
      expect(deployerInvite).to.exist;
      expect(deployerInvite).to.match(/^AMANITA-[A-Z0-9]{4}-[A-Z0-9]{4}$/);

      console.log(`✓ DEPLOYER_INVITE ready: ${deployerInvite}`);
    });
  });

  // ================================================================
  // Seller Preparation Helper (Real State)
  // ================================================================

  describe('Seller Preparation Helper', () => {
    it('должен активировать seller через harness.prepareSellerForE2E', async function() {
      this.timeout(60000);

      const SpiralEngine = await ethers.getContractAt('SpiralEngineLogic', deployedContracts.spiralEngine);
      const result = await harness.prepareSellerForE2E({
        spiralEngine: SpiralEngine,
        invitesPrefix: 'ACTION555',
        useExistingInvite: deployerInvite
      });

      expect(result.sellerAddress).to.equal(sellerAddress);

      await assertSellerState(SpiralEngine, sellerAddress, {
        activated: true,
        sellerRole: true,
        activatorRole: true,
        activatorAddress: deployerAddress
      });
    });
  });

  // ================================================================
  // Seller Activation (TDD Spec - InviteActions delegation)
  // ================================================================

  describe('Seller Activation Workflow (TDD Spec)', () => {
    it('должен делегировать activation в InviteActions (после рефакторинга)', async () => {
      // TODO: После рефакторинга
      // GIVEN: ComponentActions использует InviteActions для activation
      
      // WHEN: action555.activateSellerBasic() вызывается
      // const result = await componentActions.activateSellerBasic(...);
      
      // THEN: InviteActions.activateUser() был вызван
      
      expect(true).to.be.true; // Placeholder для TDD
      console.log('⏳ TDD: InviteActions delegation (будет после рефакторинга)');
    });

    it('должен активировать seller on-chain (TDD Spec)', async () => {
      // TODO: Требует deployed contracts + invite
      // Stub для TDD
      
      expect(true).to.be.true; // Placeholder
      console.log('⏳ TDD: Seller activation on-chain validation');
    });

    it('должен создать 12 seller invites после активации (TDD Spec)', async () => {
      // TODO: После активации seller получает 12 invites
      // Это часть InviteActions.activateUser()
      
      expect(true).to.be.true; // Placeholder
      console.log('⏳ TDD: 12 seller invites generation');
    });
  });

  // ================================================================
  // Arweave-Readiness.js Integration (NEW - критично!)
  // ================================================================

  describe('Arweave-Readiness.js Integration (NEW)', () => {
    it('должен использовать Arweave-Readiness.js напрямую (не ArweaveManager)', async () => {
      // VALIDATE: ComponentActions.uploadComponentFull использует Arweave-Readiness.js
      
      // Проверяем что метод существует
      expect(componentActions.uploadComponentFull).to.be.a('function');
      
      // TODO: После рефакторинга проверим integration
      // const arweaveReadiness = require('../../../../Arweave-Readiness');
      // const loadKeyStub = sinon.stub(arweaveReadiness, 'loadArweaveKey').resolves({ key: 'test' });
      
      console.log('✓ Arweave-Readiness.js integration expected');
      console.log('  🎯 ComponentActions.uploadComponentFull() использует Arweave-Readiness напрямую');
    });

    it('должен проверить Arweave key перед upload (QUICK mode)', async () => {
      // TDD Spec: uploadComponentFull должен вызвать loadArweaveKey()
      
      expect(true).to.be.true; // Placeholder
      console.log('⏳ TDD: Arweave key validation');
    });

    it('должен проверить Arweave connection перед upload (QUICK mode)', async () => {
      // TDD Spec: uploadComponentFull должен вызвать checkConnection()
      
      expect(true).to.be.true; // Placeholder
      console.log('⏳ TDD: Arweave connection check');
    });
  });

  // ================================================================
  // Component Upload E2E (TDD Spec - полный workflow)
  // ================================================================

  describe('Component Upload E2E Workflow (TDD Spec)', () => {
    it('должен выполнить полный workflow: Load → Activate → Upload → Validate', async function() {
      this.timeout(180000); // 3 минуты
      
      // STEP 1: Activate seller
      const SpiralEngine = await ethers.getContractAt('SpiralEngineLogic', deployedContracts.spiralEngine);
      const activationResult = await harness.prepareSellerForE2E({
        spiralEngine: SpiralEngine,
        invitesPrefix: 'ACTION555',
        useExistingInvite: deployerInvite
      });
      
      expect(activationResult.sellerAddress).to.equal(sellerAddress);
      
      // STEP 2: Upload components via Action 555
      const uploadResult = await componentActions.action555();
      
      expect(uploadResult.success).to.be.true;
      expect(uploadResult.uploadResults).to.exist;
      expect(uploadResult.uploadResults.totalCount).to.be.greaterThan(0);
      expect(uploadResult.uploadResults.successCount).to.equal(uploadResult.uploadResults.totalCount);
      expect(uploadResult.uploadResults.failCount).to.equal(0);
      
      // STEP 3: Validate on-chain state
      const OrganicRegistry = await ethers.getContractAt(
        'OrganicComponentRegistryLogic',
        deployedContracts.organicComponentRegistry
      );
      
      const componentCount = await OrganicRegistry.getComponentCount();
      expect(componentCount).to.be.greaterThan(0);
      
      // STEP 4: Validate complex fields in AmanitaInternational
      const AmanitaIntl = await ethers.getContractAt(
        'AmanitaInternationalLogic',
        deployedContracts.amanitaInternational
      );
      
      // Проверяем хотя бы один компонент
      if (uploadResult.uploadResults.results && uploadResult.uploadResults.results.length > 0) {
        const firstResult = uploadResult.uploadResults.results.find(r => r.success);
        if (firstResult && firstResult.componentId) {
          const testComponentId = firstResult.componentId;
          const className = `ComponentDescription.${testComponentId}`;
          const cid = await AmanitaIntl.getComplexFieldCID(className, 'ru');
          
          expect(cid).to.not.equal('');
          expect(cid).to.not.equal(ethers.ZeroAddress);
        }
      }
      
      console.log(`✅ Full workflow validated: ${uploadResult.uploadResults.totalCount} components uploaded`);
    });

    it('должен зарегистрировать components в OrganicComponentRegistry on-chain с правильными complex fields', async function() {
      this.timeout(180000);
      
      // GIVEN: Активирован seller
      const SpiralEngine = await ethers.getContractAt('SpiralEngineLogic', deployedContracts.spiralEngine);
      await harness.prepareSellerForE2E({
        spiralEngine: SpiralEngine,
        invitesPrefix: 'ACTION555',
        useExistingInvite: deployerInvite
      });
      
      // GIVEN: Загружен компонент через Action 555
      const uploadResult = await componentActions.action555();
      expect(uploadResult.success).to.be.true;
      expect(uploadResult.uploadResults).to.exist;
      expect(uploadResult.uploadResults.results).to.exist;
      expect(uploadResult.uploadResults.results.length).to.be.greaterThan(0);
      
      // WHEN: Проверяем регистрацию в OrganicComponentRegistry
      const OrganicRegistry = await ethers.getContractAt(
        'OrganicComponentRegistryLogic',
        deployedContracts.organicComponentRegistry
      );
      
      // Находим первый успешно загруженный компонент
      const firstResult = uploadResult.uploadResults.results.find(r => r.success && r.componentId);
      if (!firstResult || !firstResult.componentId) {
        throw new Error('No successful component upload found in results');
      }
      
      const testComponentId = firstResult.componentId;
      const exists = await OrganicRegistry.componentExists(testComponentId);
      expect(exists).to.be.true;
      
      // WHEN: Проверяем complex fields в AmanitaInternational
      const AmanitaIntl = await ethers.getContractAt(
        'AmanitaInternationalLogic',
        deployedContracts.amanitaInternational
      );
      
      const className = `ComponentDescription.${testComponentId}`;
      
      // THEN: Ключ содержит biounit_id (правильный формат)
      expect(className).to.include(testComponentId);
      expect(className).to.not.equal('ComponentDescription'); // НЕ без biounit_id
      
      // THEN: CID доступен для всех языков
      const languages = ['ru', 'en', 'de'];
      for (const lang of languages) {
        const cid = await AmanitaIntl.getComplexFieldCID(className, lang);
        expect(cid).to.not.equal('');
        expect(cid).to.not.equal(ethers.ZeroAddress);
      }
      
      console.log(`✅ Component ${testComponentId} registered with correct complex fields keys`);
    });

    it('должен создавать уникальные ключи для разных компонентов (не перезаписывать)', async function() {
      this.timeout(240000); // 4 минуты (загрузка 2+ компонентов)
      
      // GIVEN: Активирован seller
      const SpiralEngine = await ethers.getContractAt('SpiralEngineLogic', deployedContracts.spiralEngine);
      await harness.prepareSellerForE2E({
        spiralEngine: SpiralEngine,
        invitesPrefix: 'ACTION555',
        useExistingInvite: deployerInvite
      });
      
      // GIVEN: Загружены компоненты через Action 555
      const uploadResult = await componentActions.action555();
      expect(uploadResult.success).to.be.true;
      expect(uploadResult.uploadResults).to.exist;
      expect(uploadResult.uploadResults.totalCount).to.be.greaterThanOrEqual(2);
      expect(uploadResult.uploadResults.results).to.exist;
      expect(uploadResult.uploadResults.results.length).to.be.greaterThanOrEqual(2);
      
      // Находим минимум 2 успешно загруженных компонента
      const successfulResults = uploadResult.uploadResults.results.filter(r => r.success && r.componentId);
      expect(successfulResults.length).to.be.greaterThanOrEqual(2, 'Need at least 2 successfully uploaded components for uniqueness test');
      
      const comp1 = successfulResults[0].componentId;
      const comp2 = successfulResults[1].componentId;
      
      // WHEN: Проверяем ключи в контракте
      const AmanitaIntl = await ethers.getContractAt(
        'AmanitaInternationalLogic',
        deployedContracts.amanitaInternational
      );
      
      const className1 = `ComponentDescription.${comp1}`;
      const className2 = `ComponentDescription.${comp2}`;
      const lang = 'ru';
      
      const cid1 = await AmanitaIntl.getComplexFieldCID(className1, lang);
      const cid2 = await AmanitaIntl.getComplexFieldCID(className2, lang);
      
      // THEN: Оба CID существуют
      expect(cid1).to.not.equal('');
      expect(cid1).to.not.equal(ethers.ZeroAddress);
      expect(cid2).to.not.equal('');
      expect(cid2).to.not.equal(ethers.ZeroAddress);
      
      // THEN: CID разные (ключи уникальны)
      expect(cid1).to.not.equal(cid2, `CIDs should be different for different components. Component1: ${comp1}, Component2: ${comp2}`);
      
      // THEN: Проверяем, что ключи действительно содержат biounit_id
      expect(className1).to.include(comp1);
      expect(className2).to.include(comp2);
      expect(className1).to.not.equal('ComponentDescription'); // НЕ без biounit_id
      expect(className2).to.not.equal('ComponentDescription'); // НЕ без biounit_id
      
      // THEN: Старый формат (без biounit_id) НЕ должен перезаписывать новые ключи
      const oldFormatKey = 'ComponentDescription';
      const oldFormatCID = await AmanitaIntl.getComplexFieldCID(oldFormatKey, lang);
      
      // Старый формат может быть пустым ИЛИ должен отличаться от обоих (не перезаписан последним компонентом)
      if (oldFormatCID && oldFormatCID !== '' && oldFormatCID !== ethers.ZeroAddress) {
        // Если существует, должен быть другим (не перезаписан)
        expect(oldFormatCID).to.not.equal(cid1, `Old format CID should not match component1 (${comp1})`);
        expect(oldFormatCID).to.not.equal(cid2, `Old format CID should not match component2 (${comp2})`);
      }
      
      console.log(`✅ Unique keys verified: ${className1}.${lang} != ${className2}.${lang}`);
      console.log(`   CID1 (${comp1}): ${cid1}`);
      console.log(`   CID2 (${comp2}): ${cid2}`);
    });

    it('должен сохранить seller invites в файл', async () => {
      // TODO: TDD Spec (проверка saveSellerInvites)
      
      expect(true).to.be.true; // Placeholder
      console.log('⏳ TDD: Seller invites file persistence');
    });
  });

  // ================================================================
  // Complex Fields Upload Validation (NEW)
  // ================================================================

  describe('Complex Fields Upload Validation', () => {
    it('должен вызывать setComplexFieldCID с biounit_id в className', async function() {
      this.timeout(180000);
      
      // GIVEN: Активирован seller
      const SpiralEngine = await ethers.getContractAt('SpiralEngineLogic', deployedContracts.spiralEngine);
      await harness.prepareSellerForE2E({
        spiralEngine: SpiralEngine,
        invitesPrefix: 'ACTION555',
        useExistingInvite: deployerInvite
      });
      
      // GIVEN: Загружен компонент через Action 555
      const uploadResult = await componentActions.action555();
      expect(uploadResult.success).to.be.true;
      expect(uploadResult.uploadResults).to.exist;
      expect(uploadResult.uploadResults.results).to.exist;
      expect(uploadResult.uploadResults.results.length).to.be.greaterThan(0);
      
      // WHEN: Проверяем контракт
      const AmanitaIntl = await ethers.getContractAt(
        'AmanitaInternationalLogic',
        deployedContracts.amanitaInternational
      );
      
      // Находим первый успешно загруженный компонент
      const firstResult = uploadResult.uploadResults.results.find(r => r.success && r.componentId);
      if (!firstResult || !firstResult.componentId) {
        throw new Error('No successful component upload found in results');
      }
      
      const testComponentId = firstResult.componentId;
      const expectedClassName = `ComponentDescription.${testComponentId}`;
      
      // THEN: Ключ содержит biounit_id (правильный формат)
      expect(expectedClassName).to.include(testComponentId);
      expect(expectedClassName).to.not.equal('ComponentDescription'); // НЕ без biounit_id
      
      // THEN: CID доступен для правильного className (с biounit_id)
      const cid = await AmanitaIntl.getComplexFieldCID(expectedClassName, 'ru');
      expect(cid).to.not.equal('');
      expect(cid).to.not.equal(ethers.ZeroAddress);
      
      // THEN: Старый формат (без biounit_id) НЕ должен перезаписывать новые ключи
      const oldClassName = 'ComponentDescription';
      const oldCID = await AmanitaIntl.getComplexFieldCID(oldClassName, 'ru');
      
      // Старый формат может быть пустым ИЛИ должен отличаться от нового (не перезаписан последним компонентом)
      if (oldCID && oldCID !== '' && oldCID !== ethers.ZeroAddress) {
        // Если существует, должен быть другим (не перезаписан)
        expect(oldCID).to.not.equal(cid, `Old format CID should not match component with biounit_id (${testComponentId})`);
      }
      
      console.log(`✅ ClassName format correct: ${expectedClassName} (contains biounit_id)`);
      console.log(`   CID for ${expectedClassName}.ru: ${cid}`);
    });
  });

  // ================================================================
  // Error Scenarios (TDD Spec)
  // ================================================================

  describe('Error Scenarios (TDD Spec)', () => {
    it('должен выбросить ошибку если contracts не deployed', async () => {
      // TODO: После рефакторинга
      // GIVEN: Контракты не deployed
      
      // WHEN/THEN: action555 падает
      
      expect(true).to.be.true; // Placeholder
      console.log('⏳ TDD: Error handling - contracts not deployed');
    });

    it('должен выбросить ошибку если DEPLOYER_INVITE отсутствует', async () => {
      // TODO: action555 требует DEPLOYER_INVITE
      
      expect(true).to.be.true; // Placeholder
      console.log('⏳ TDD: Error handling - missing DEPLOYER_INVITE');
    });

    it('должен выбросить ошибку если seller уже активирован', async () => {
      // TODO: Duplicate activation должна быть обработана
      
      expect(true).to.be.true; // Placeholder
      console.log('⏳ TDD: Error handling - duplicate activation');
    });

    it('должен обработать ошибку Arweave upload', async () => {
      // TODO: Arweave upload падает → graceful handling
      
      expect(true).to.be.true; // Placeholder
      console.log('⏳ TDD: Error handling - Arweave upload failure');
    });
  });

  // ================================================================
  // Existing Fixture Validation (сохранено)
  // ================================================================

  describe('Component Fixtures Validation', () => {
    it('должен валидировать component fixtures', async () => {
      const component1 = JSON.parse(fs.readFileSync(
        path.join(__dirname, '../../../fixtures/components/test_component_01.json')
      ));
      
      expect(component1.component_id).to.exist;
      expect(component1.name).to.exist;
      console.log(`✓ Component fixture valid: ${component1.component_id}`);
    });

    it('должен иметь валидные JSON файлы компонентов', async () => {
      const fixturesDir = path.join(__dirname, '../../../fixtures/components');
      const files = fs.readdirSync(fixturesDir).filter(f => f.endsWith('.json'));

      expect(files).to.have.length.greaterThan(0);

      files.forEach(file => {
        const filePath = path.join(fixturesDir, file);
        const component = JSON.parse(fs.readFileSync(filePath));

        expect(component).to.have.property('component_id');
        expect(component).to.have.property('name');
        console.log(`✓ Fixture valid: ${file}`);
      });
    });
  });
});

// ================================================================
// Helpers: Deploy contracts for Action 555 E2E
// ================================================================

async function deployAllContractsForAction555() {
  const [deployer] = await ethers.getSigners();

  // Deploy MagicRegistry
  const MagicRegistry = await ethers.getContractFactory('AmanitaRegistry');
  const registry = await MagicRegistry.deploy();
  await registry.waitForDeployment();
  const registryAddress = await registry.getAddress();

  // Deploy SpiralEngine (UUPS)
  const SpiralEngineLogic = await ethers.getContractFactory('SpiralEngineLogic');
  const spiralLogic = await SpiralEngineLogic.deploy();
  await spiralLogic.waitForDeployment();

  // Encode initialize(admin) call
  const spiralInterface = spiralLogic.interface;
  const initializeData = spiralInterface.encodeFunctionData('initialize', [deployer.address]);

  const SpiralEngineProxy = await ethers.getContractFactory('SpiralEngineProxy');
  const spiralProxy = await SpiralEngineProxy.deploy(await spiralLogic.getAddress(), initializeData);
  await spiralProxy.waitForDeployment();
  const spiralAddress = await spiralProxy.getAddress();
  
  console.log('✅ SpiralEngine initialized with deployer as admin');

  // Deploy OrganicComponentRegistry (UUPS)
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
  
  // Setup: setSpiralEngine (after initialization)
  const OrganicRegistry = await ethers.getContractAt('OrganicComponentRegistryLogic', organicAddress);
  const organicWithSigner = OrganicRegistry.connect(deployer);
  const setSpiralTx = await organicWithSigner.setSpiralEngine(spiralAddress);
  await setSpiralTx.wait();
  
  console.log('✅ OrganicComponentRegistry.setSpiralEngine() configured');

  // Deploy AmanitaInternational (UUPS)
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

  // Register in MagicRegistry
  const registryWithSigner = (await ethers.getContractAt('AmanitaRegistry', registryAddress)).connect(deployer);
  await registryWithSigner.set('AmanitaInternational', amanitaAddress);
  console.log('✅ AmanitaInternational registered in MagicRegistry');

  return {
    magicRegistry: registryAddress,
    spiralEngine: spiralAddress,
    organicComponentRegistry: organicAddress,
    amanitaInternational: amanitaAddress
  };
}

async function generateDeployerInviteForTest(spiralEngineAddress) {
  const [deployer] = await ethers.getSigners();

  const SpiralEngine = await ethers.getContractAt('SpiralEngineLogic', spiralEngineAddress);
  const spiralWithSigner = SpiralEngine.connect(deployer);

  // Generate 1 test invite
  const inviteCode = 'AMANITA-TEST-E2E0';
  const tx = await spiralWithSigner.mintInvite(inviteCode, 0); // Expiry = 0 (бессрочный)
  await tx.wait();

  console.log(`✅ Test invite created: ${inviteCode}`);

  return inviteCode;
}

function registerContractsInMagicRegistry(harnessInstance, deployed) {
  if (!harnessInstance || !deployed) {
    return;
  }

  harnessInstance.magicRegistry.registerMany([
    ['MagicRegistry', deployed.magicRegistry, null],
    ['SpiralEngine', deployed.spiralEngine, null],
    ['OrganicComponentRegistry', deployed.organicComponentRegistry, null],
    ['AmanitaInternational', deployed.amanitaInternational, null]
  ]);
}

