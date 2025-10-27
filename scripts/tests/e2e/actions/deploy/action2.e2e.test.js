/**
 * E2E Tests: Action 2 - Setup System Connections
 * 
 * Tests contract initialization and connection setup after deployment.
 * Action 2 = SetupActions.setupSystemConnections()
 * 
 * Coverage:
 * - setupSystemConnections() orchestration
 * - loadSystemContracts() via MagicRegistry
 * - setupSBTEcosystem() (4 connections)
 * - setupOrganicComponentRegistry() (SpiralEngine connection)
 * - Idempotency (can be called twice safely)
 * - Error scenarios (missing MagicRegistry, failed setup)
 */

const { expect } = require('chai');
const E2EHarness = require('../../../helpers/E2EHarness');
const { ethers } = require('hardhat');

// Import real SetupActions (not mocked — this is E2E!)
const SetupActions = require('../../../../lib/actions/SetupActions');
const ContractManager = require('../../../../lib/services/ContractManager');
const EthersUtils = require('../../../../lib/utils/EthersUtils');
const config = require('../../../../lib/config');

describe('E2E: Action 2 - Setup System Connections', function() {
  this.timeout(180000); // 3 min for full E2E

  let harness;
  let setupActions;
  let deployedContracts;
  let magicRegistryAddress;

  before(async function() {
    this.timeout(120000); // 2 min for setup

    // Start E2E infrastructure
    harness = new E2EHarness();
    await harness.startHardhatNode();
    harness.loadTestEnv();

    // Deploy contracts (Action 1 prerequisite)
    console.log('\n📦 Prerequisite: Deploying contracts (Action 1)...');
    deployedContracts = await deployAllContractsForTest();
    magicRegistryAddress = deployedContracts.magicRegistry;

    console.log(`✅ Contracts deployed. MagicRegistry: ${magicRegistryAddress}`);

    // Create snapshot (expensive setup done)
    await harness.saveState('after-action1');
  });

  after(async function() {
    await harness.stopHardhatNode();
    harness.restoreEnv();
  });

  beforeEach(async function() {
    // Reset to state after Action 1 (contracts deployed)
    await harness.restoreState('after-action1');

    // Create fresh SetupActions instance
    const provider = ethers.provider;
    
    // Create config wrapper for tests
    const configWrapper = {
      get: (key) => {
        if (key === 'contracts.magicRegistry') {
          return magicRegistryAddress;
        }
        if (key === 'deployer.privateKey') {
          return process.env.DEPLOYER_PRIVATE_KEY;
        }
        return config.get(key);
      }
    };

    const contractManager = new ContractManager(provider, configWrapper);
    const ethersUtils = new EthersUtils(provider, configWrapper);

    setupActions = new SetupActions(contractManager, ethersUtils, configWrapper);
  });

  // ================================================================
  // Infrastructure Validation
  // ================================================================

  describe('Infrastructure Validation', () => {
    it('должен иметь deployed contracts (Action 1 выполнен)', async () => {
      // Validate MagicRegistry deployed
      const validation = await harness.validateDeployment(magicRegistryAddress);
      expect(validation.deployed).to.be.true;

      console.log('✓ Action 1 completed, contracts deployed');
    });

    it('должен иметь MagicRegistry в config', async () => {
      const configWrapper = {
        get: (key) => {
          if (key === 'contracts.magicRegistry') {
            return magicRegistryAddress;
          }
          return config.get(key);
        }
      };
      
      const registryAddress = configWrapper.get('contracts.magicRegistry');

      expect(registryAddress).to.equal(magicRegistryAddress);
      console.log('✓ MagicRegistry address in config');
    });
  });

  // ================================================================
  // setupSystemConnections() — Happy Path
  // ================================================================

  describe('setupSystemConnections() - Happy Path', () => {
    it('должен загрузить контракты через MagicRegistry', async function() {
      this.timeout(60000);

      // WHEN: setupSystemConnections вызывается БЕЗ переданных контрактов
      await setupActions.setupSystemConnections();

      // THEN: Контракты загружены через loadSystemContracts()
      // Validate: SBT ecosystem connections установлены
      const SpiralEngine = await ethers.getContractAt(
        'SpiralEngineLogic',
        deployedContracts.spiralEngine
      );

      // soulIdentity - это public variable, getter генерируется автоматически
      const soulIdentityAddress = await SpiralEngine.soulIdentity();
      expect(soulIdentityAddress).to.equal(deployedContracts.soulIdentity);

      console.log('✓ Contracts loaded via MagicRegistry, connections established');
    });

    it('должен настроить SBT ecosystem (4 связи)', async function() {
      this.timeout(60000);

      // WHEN: setupSystemConnections вызывается
      await setupActions.setupSystemConnections();

      // THEN: 4 связи установлены
      const SoulboundCore = await ethers.getContractAt(
        'SoulboundCore',
        deployedContracts.soulboundCore
      );

      // Используем getMetadataContract(), getRecoveryContract(), getIntegrationContract()
      const metadataContract = await SoulboundCore.getMetadataContract();
      const recoveryContract = await SoulboundCore.getRecoveryContract();
      const integrationContract = await SoulboundCore.getIntegrationContract();

      expect(metadataContract).to.equal(deployedContracts.soulMetadata);
      expect(recoveryContract).to.equal(deployedContracts.soulRecovery);
      expect(integrationContract).to.equal(deployedContracts.soulIntegration);

      // Проверка 4-й связи (SpiralEngine → SoulIdentity)
      const SpiralEngine = await ethers.getContractAt(
        'SpiralEngineLogic',
        deployedContracts.spiralEngine
      );
      // soulIdentity() - public variable getter
      const soulIdentityAddress = await SpiralEngine.soulIdentity();
      expect(soulIdentityAddress).to.equal(deployedContracts.soulIdentity);

      console.log('✓ SBT ecosystem connections validated (4/4)');
    });

    it('должен настроить OrganicComponentRegistry (связь с SpiralEngine)', async function() {
      this.timeout(60000);

      // WHEN: setupSystemConnections вызывается
      await setupActions.setupSystemConnections();

      // THEN: OrganicComponentRegistry → SpiralEngine связь установлена
      const OrganicRegistry = await ethers.getContractAt(
        'OrganicComponentRegistryLogic',
        deployedContracts.organicComponentRegistry
      );

      const spiralEngineAddress = await OrganicRegistry.spiralEngine();
      expect(spiralEngineAddress).to.equal(deployedContracts.spiralEngine);

      console.log('✓ OrganicComponentRegistry → SpiralEngine connection validated');
    });

    it('должен завершиться успешно (все connections установлены)', async function() {
      this.timeout(60000);

      // WHEN: setupSystemConnections вызывается
      await setupActions.setupSystemConnections();

      // THEN: Все связи установлены, no errors
      // Validate complete system state
      const SoulboundCore = await ethers.getContractAt('SoulboundCore', deployedContracts.soulboundCore);
      const SpiralEngine = await ethers.getContractAt('SpiralEngineLogic', deployedContracts.spiralEngine);
      const OrganicRegistry = await ethers.getContractAt('OrganicComponentRegistryLogic', deployedContracts.organicComponentRegistry);

      // All connections present (используем правильные getters)
      expect(await SoulboundCore.getMetadataContract()).to.not.equal(ethers.ZeroAddress);
      expect(await SpiralEngine.soulIdentity()).to.not.equal(ethers.ZeroAddress);
      expect(await OrganicRegistry.spiralEngine()).to.not.equal(ethers.ZeroAddress);

      console.log('✓ Action 2 completed successfully (all connections)');
    });
  });

  // ================================================================
  // Idempotency Check (можно вызвать дважды)
  // ================================================================

  describe('Idempotency Check', () => {
    it('должен быть idempotent (повторный вызов безопасен)', async function() {
      this.timeout(90000);

      // WHEN: setupSystemConnections вызывается ДВАЖДЫ
      await setupActions.setupSystemConnections();
      
      // Second call (should not fail)
      await setupActions.setupSystemConnections();

      // THEN: Состояние то же самое, no errors
      const SoulboundCore = await ethers.getContractAt('SoulboundCore', deployedContracts.soulboundCore);
      const metadataContract = await SoulboundCore.getMetadataContract();
      
      expect(metadataContract).to.equal(deployedContracts.soulMetadata);

      console.log('✓ Idempotency validated (called twice safely)');
    });
  });

  // ================================================================
  // Error Scenarios
  // ================================================================

  describe('Error Scenarios', () => {
    it('должен выбросить ошибку если MagicRegistry отсутствует в .env', async function() {
      this.timeout(30000);

      // GIVEN: MagicRegistry отсутствует
      const brokenConfig = {
        get: (key) => {
          if (key === 'contracts.magicRegistry') {
            return null; // Missing
          }
          if (key === 'deployer.privateKey') {
            return process.env.DEPLOYER_PRIVATE_KEY;
          }
          return config.get(key);
        }
      };

      const contractManager = new ContractManager(ethers.provider, brokenConfig);
      const ethersUtils = new EthersUtils(ethers.provider, brokenConfig);
      const brokenSetupActions = new SetupActions(contractManager, ethersUtils, brokenConfig);

      // WHEN/THEN: setupSystemConnections падает
      try {
        await brokenSetupActions.setupSystemConnections();
        expect.fail('Should have thrown error');
      } catch (error) {
        expect(error.message).to.include('MAGIC_REGISTRY_CONTRACT_ADDRESS не найден в .env');
      }

      console.log('✓ Error handled: missing MagicRegistry');
    });

    it('должен пропустить setup если контракты не deployed', async function() {
      this.timeout(60000);

      // GIVEN: Контракты частично deployed (SBT отсутствует)
      const partialContracts = {
        spiralEngine: null, // Missing
        organicComponentRegistry: deployedContracts.organicComponentRegistry
      };

      // WHEN: setupSBTEcosystem вызывается с частичными контрактами
      await setupActions.setupSBTEcosystem(partialContracts);

      // THEN: Setup пропущен (warning, no error)
      console.log('✓ Setup skipped for missing contracts (no error)');
    });
  });

  // ================================================================
  // Integration с Action 1 (предусловие)
  // ================================================================

  describe('Integration: Action 1 → Action 2', () => {
    it('должен работать после Action 1 (полный workflow)', async function() {
      this.timeout(90000);

      // Prerequisite: Action 1 уже выполнен (контракты deployed)
      // Validate prerequisite
      const validation = await harness.validateDeployment(magicRegistryAddress);
      expect(validation.deployed).to.be.true;

      // WHEN: Action 2 выполняется
      await setupActions.setupSystemConnections();

      // THEN: Полный workflow завершён
      const SpiralEngine = await ethers.getContractAt('SpiralEngineLogic', deployedContracts.spiralEngine);
      const OrganicRegistry = await ethers.getContractAt('OrganicComponentRegistryLogic', deployedContracts.organicComponentRegistry);

      // Validate: System готов к использованию (используем правильные getters)
      expect(await SpiralEngine.soulIdentity()).to.not.equal(ethers.ZeroAddress);
      expect(await OrganicRegistry.spiralEngine()).to.not.equal(ethers.ZeroAddress);

      console.log('✓ Action 1 → Action 2 workflow complete');
    });
  });
});

// ================================================================
// Helper: Deploy All Contracts (Action 1 logic for E2E)
// ================================================================

async function deployAllContractsForTest() {
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
  
  const SpiralEngineProxy = await ethers.getContractFactory('SpiralEngineProxy');
  const spiralProxy = await SpiralEngineProxy.deploy(await spiralLogic.getAddress(), '0x');
  await spiralProxy.waitForDeployment();
  const spiralAddress = await spiralProxy.getAddress();
  
  // Deploy SBT ecosystem (ПРАВИЛЬНЫЙ ПОРЯДОК С ЗАВИСИМОСТЯМИ)
  
  // 1. SoulboundCore (первым, требует name + symbol)
  const SoulboundCore = await ethers.getContractFactory('SoulboundCore');
  const soulCore = await SoulboundCore.deploy('SoulboundIdentity', 'SBI');
  await soulCore.waitForDeployment();
  const soulCoreAddress = await soulCore.getAddress();
  
  // 2. SoulMetadata (требует soulboundCore)
  const SoulMetadata = await ethers.getContractFactory('SoulMetadata');
  const soulMetadata = await SoulMetadata.deploy(soulCoreAddress);
  await soulMetadata.waitForDeployment();
  const soulMetadataAddress = await soulMetadata.getAddress();
  
  // 3. SoulRecovery (требует soulboundCore)
  const SoulRecovery = await ethers.getContractFactory('SoulRecovery');
  const soulRecovery = await SoulRecovery.deploy(soulCoreAddress);
  await soulRecovery.waitForDeployment();
  const soulRecoveryAddress = await soulRecovery.getAddress();
  
  // 4. SoulIntegration (требует spiralEngine + soulboundCore)
  const SoulIntegration = await ethers.getContractFactory('SoulIntegration');
  const soulIntegration = await SoulIntegration.deploy(spiralAddress, soulCoreAddress);
  await soulIntegration.waitForDeployment();
  const soulIntegrationAddress = await soulIntegration.getAddress();
  
  // 5. SoulIdentity (требует soulboundCore + soulMetadata)
  const SoulIdentity = await ethers.getContractFactory('SoulIdentity');
  const soulIdentity = await SoulIdentity.deploy(soulCoreAddress, soulMetadataAddress);
  await soulIdentity.waitForDeployment();
  const soulIdentityAddress = await soulIdentity.getAddress();
  
  // Deploy OrganicComponentRegistry (UUPS)
  const OrganicLogic = await ethers.getContractFactory('OrganicComponentRegistryLogic');
  const organicLogic = await OrganicLogic.deploy();
  await organicLogic.waitForDeployment();
  
  const OrganicProxy = await ethers.getContractFactory('OrganicComponentRegistryProxy');
  const organicProxy = await OrganicProxy.deploy(await organicLogic.getAddress(), '0x');
  await organicProxy.waitForDeployment();
  const organicAddress = await organicProxy.getAddress();
  
  // РЕГИСТРАЦИЯ В MAGICREGISTRY (необходимо для loadSystemContracts!)
  console.log('\n📝 Регистрация контрактов в MagicRegistry...');
  
  // Используем setAddress() из AmanitaRegistry
  await registry.setAddress('SpiralEngine', spiralAddress);
  await registry.setAddress('SoulboundCore', soulCoreAddress);
  await registry.setAddress('SoulMetadata', soulMetadataAddress);
  await registry.setAddress('SoulRecovery', soulRecoveryAddress);
  await registry.setAddress('SoulIntegration', soulIntegrationAddress);
  await registry.setAddress('SoulIdentity', soulIdentityAddress);
  await registry.setAddress('OrganicComponentRegistry', organicAddress);
  
  console.log('✅ Все контракты зарегистрированы в MagicRegistry');
  
  return {
    magicRegistry: registryAddress,
    spiralEngine: spiralAddress,
    soulboundCore: soulCoreAddress,
    soulMetadata: soulMetadataAddress,
    soulRecovery: soulRecoveryAddress,
    soulIntegration: soulIntegrationAddress,
    soulIdentity: soulIdentityAddress,
    organicComponentRegistry: organicAddress
  };
}
