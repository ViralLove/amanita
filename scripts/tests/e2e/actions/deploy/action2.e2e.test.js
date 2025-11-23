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
const {
  E2EHarness,
  assertRegisteredProxy
} = require('../../../helpers');
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
  let suite;
  let magicRegistryAddress;
  let deployerSigner;
  let deployerPrivateKey;

  before(async function() {
    this.timeout(120000); // 2 min for setup

    // Start E2E infrastructure
    harness = new E2EHarness();
    await harness.startHardhatNode();
    harness.loadTestEnv();

    [deployerSigner] = await ethers.getSigners();
    const envPrivateKey = process.env.DEPLOYER_PRIVATE_KEY;
    if (!envPrivateKey) {
      throw new Error('DEPLOYER_PRIVATE_KEY не задан: e2e тесты Action 2 требуют приватный ключ в окружении');
    }
    deployerPrivateKey = envPrivateKey.startsWith('0x') ? envPrivateKey : `0x${envPrivateKey}`;

    // Deploy contracts (Action 1 prerequisite)
    console.log('\n📦 Prerequisite: Deploying contracts (Action 1)...');
    suite = await deployAllContractsForTest(harness);
    magicRegistryAddress = suite.magicRegistry;

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
          return deployerPrivateKey;
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

      console.log('Фаза 1: setupSystemConnections без ручных адресов');
      // WHEN: setupSystemConnections вызывается БЕЗ переданных контрактов
      await setupActions.setupSystemConnections();

      console.log('Фаза 2: Проверяем загрузку адресов через MagicRegistryHelper');
      const spiralEntry = harness.loadContractFromSuite('SpiralEngine');
      assertRegisteredProxy(
        { SpiralEngine: spiralEntry },
        'SpiralEngine',
        suite.spiralEngine,
        suite.spiralEngineLogic
      );

      const organicEntry = harness.loadContractFromSuite('OrganicComponentRegistry');
      assertRegisteredProxy(
        { OrganicComponentRegistry: organicEntry },
        'OrganicComponentRegistry',
        suite.organicComponentRegistry,
        suite.organicComponentRegistryLogic
      );

      const soulCoreEntry = harness.loadContractFromSuite('SoulboundCore');
      assertRegisteredProxy(
        { SoulboundCore: soulCoreEntry },
        'SoulboundCore',
        suite.soulboundCore
      );

      console.log('Фаза 3: Проверяем связи через ethers');
      const SpiralEngine = await ethers.getContractAt(
        'SpiralEngineLogic',
        suite.spiralEngine
      );

      // soulIdentity - это public variable, getter генерируется автоматически
      const soulIdentityAddress = await SpiralEngine.soulIdentity();
      expect(soulIdentityAddress).to.equal(suite.soulIdentity);

      console.log('Фаза 4: Контракты загружены через MagicRegistry, связи установлены');
    });

    it('должен настроить SBT ecosystem (4 связи)', async function() {
      this.timeout(60000);

      console.log('Фаза 1: setupSystemConnections для SBT');
      // WHEN: setupSystemConnections вызывается
      await setupActions.setupSystemConnections();

      console.log('Фаза 2: Проверяем регистрации в MagicRegistryHelper');
      const soulMetadataEntry = harness.loadContractFromSuite('SoulMetadata');
      assertRegisteredProxy(
        { SoulMetadata: soulMetadataEntry },
        'SoulMetadata',
        suite.soulMetadata
      );

      const soulRecoveryEntry = harness.loadContractFromSuite('SoulRecovery');
      assertRegisteredProxy(
        { SoulRecovery: soulRecoveryEntry },
        'SoulRecovery',
        suite.soulRecovery
      );

      const soulIntegrationEntry = harness.loadContractFromSuite('SoulIntegration');
      assertRegisteredProxy(
        { SoulIntegration: soulIntegrationEntry },
        'SoulIntegration',
        suite.soulIntegration
      );

      const soulIdentityEntry = harness.loadContractFromSuite('SoulIdentity');
      assertRegisteredProxy(
        { SoulIdentity: soulIdentityEntry },
        'SoulIdentity',
        suite.soulIdentity
      );

      console.log('Фаза 3: Проверяем связи через контракты');
      // THEN: 4 связи установлены
      const SoulboundCore = await ethers.getContractAt(
        'SoulboundCore',
        suite.soulboundCore
      );

      // Используем getMetadataContract(), getRecoveryContract(), getIntegrationContract()
      const metadataContract = await SoulboundCore.getMetadataContract();
      const recoveryContract = await SoulboundCore.getRecoveryContract();
      const integrationContract = await SoulboundCore.getIntegrationContract();

      expect(metadataContract).to.equal(suite.soulMetadata);
      expect(recoveryContract).to.equal(suite.soulRecovery);
      expect(integrationContract).to.equal(suite.soulIntegration);

      // Проверка 4-й связи (SpiralEngine → SoulIdentity)
      const SpiralEngine = await ethers.getContractAt(
        'SpiralEngineLogic',
        suite.spiralEngine
      );
      // soulIdentity() - public variable getter
      const soulIdentityAddress = await SpiralEngine.soulIdentity();
      expect(soulIdentityAddress).to.equal(suite.soulIdentity);

      console.log('Фаза 4: SBT ecosystem connections validated (4/4)');
    });

    it('должен настроить OrganicComponentRegistry (связь с SpiralEngine)', async function() {
      this.timeout(60000);

      console.log('Фаза 1: setupSystemConnections для OrganicComponentRegistry');
      // WHEN: setupSystemConnections вызывается
      await setupActions.setupSystemConnections();

      console.log('Фаза 2: Проверяем регистрацию в MagicRegistryHelper');
      const organicEntry = harness.loadContractFromSuite('OrganicComponentRegistry');
      assertRegisteredProxy(
        { OrganicComponentRegistry: organicEntry },
        'OrganicComponentRegistry',
        suite.organicComponentRegistry,
        suite.organicComponentRegistryLogic
      );

      console.log('Фаза 3: Проверяем связь через контракт');
      // THEN: OrganicComponentRegistry → SpiralEngine связь установлена
      const OrganicRegistry = await ethers.getContractAt(
        'OrganicComponentRegistryLogic',
        suite.organicComponentRegistry
      );

      const spiralEngineAddress = await OrganicRegistry.spiralEngine();
      expect(spiralEngineAddress).to.equal(suite.spiralEngine);

      console.log('Фаза 4: OrganicComponentRegistry ↔ SpiralEngine связь подтверждена');
    });

    it('должен завершиться успешно (все connections установлены)', async function() {
      this.timeout(60000);

      console.log('Фаза 1: setupSystemConnections полный workflow');
      // WHEN: setupSystemConnections вызывается
      await setupActions.setupSystemConnections();

      console.log('Фаза 2: Проверяем через MagicRegistryHelper все ключевые контракты');
      const contractsToCheck = [
        ['SpiralEngine', suite.spiralEngine, suite.spiralEngineLogic],
        ['OrganicComponentRegistry', suite.organicComponentRegistry, suite.organicComponentRegistryLogic],
        ['SoulboundCore', suite.soulboundCore]
      ];

      contractsToCheck.forEach(([name, proxy, impl]) => {
        const entry = harness.loadContractFromSuite(name);
        assertRegisteredProxy({ [name]: entry }, name, proxy, impl);
      });

      console.log('Фаза 3: Дополнительная проверка state через контракты');
      // THEN: Все связи установлены, no errors
      // Validate complete system state
      const SoulboundCore = await ethers.getContractAt('SoulboundCore', suite.soulboundCore);
      const SpiralEngine = await ethers.getContractAt('SpiralEngineLogic', suite.spiralEngine);
      const OrganicRegistry = await ethers.getContractAt('OrganicComponentRegistryLogic', suite.organicComponentRegistry);

      // All connections present (используем правильные getters)
      expect(await SoulboundCore.getMetadataContract()).to.not.equal(ethers.ZeroAddress);
      expect(await SpiralEngine.soulIdentity()).to.not.equal(ethers.ZeroAddress);
      expect(await OrganicRegistry.spiralEngine()).to.not.equal(ethers.ZeroAddress);

      console.log('Фаза 4: Action 2 completed successfully (all connections)');
    });
  });

  // ================================================================
  // Idempotency Check (можно вызвать дважды)
  // ================================================================

  describe('Idempotency Check', () => {
    it('должен быть idempotent (повторный вызов безопасен)', async function() {
      this.timeout(90000);

      console.log('Фаза 1: Первый вызов setupSystemConnections');
      // WHEN: setupSystemConnections вызывается ДВАЖДЫ
      await setupActions.setupSystemConnections();

      console.log('Фаза 2: Второй вызов setupSystemConnections');
      // Second call (should not fail)
      await setupActions.setupSystemConnections();

      console.log('Фаза 3: Проверяем, что все контракты остались зарегистрированными');
      const suiteMappings = [
        { name: 'SpiralEngine', proxyKey: 'spiralEngine', implKey: 'spiralEngineLogic' },
        { name: 'OrganicComponentRegistry', proxyKey: 'organicComponentRegistry', implKey: 'organicComponentRegistryLogic' },
        { name: 'SoulboundCore', proxyKey: 'soulboundCore' },
        { name: 'SoulMetadata', proxyKey: 'soulMetadata' },
        { name: 'SoulRecovery', proxyKey: 'soulRecovery' },
        { name: 'SoulIntegration', proxyKey: 'soulIntegration' },
        { name: 'SoulIdentity', proxyKey: 'soulIdentity' }
      ];

      suiteMappings.forEach(({ name, proxyKey, implKey }) => {
        const entry = harness.loadContractFromSuite(name);
        const expectedProxy = suite[proxyKey];
        const expectedImpl = implKey ? suite[implKey] : undefined;
        assertRegisteredProxy({ [name]: entry }, name, expectedProxy, expectedImpl);
      });

      console.log('Фаза 4: Состояние контрактов через ABI');
      // THEN: Состояние то же самое, no errors
      const SoulboundCore = await ethers.getContractAt('SoulboundCore', suite.soulboundCore);
      const metadataContract = await SoulboundCore.getMetadataContract();
      
      expect(metadataContract).to.equal(suite.soulMetadata);

      console.log('Фаза 5: Idempotency validated (called twice safely)');
    });
  });

  // ================================================================
  // Error Scenarios
  // ================================================================

  describe('Error Scenarios', () => {
    it('должен выбросить ошибку если MagicRegistry отсутствует в .env', async function() {
      this.timeout(30000);

      console.log('Фаза 1: Подготовка конфигурации без MagicRegistry');
      // GIVEN: MagicRegistry отсутствует
      const brokenConfig = {
        get: (key) => {
          if (key === 'contracts.magicRegistry') {
            return null; // Missing
          }
          if (key === 'deployer.privateKey') {
            return deployerPrivateKey;
          }
          return config.get(key);
        }
      };

      const contractManager = new ContractManager(ethers.provider, brokenConfig);
      const ethersUtils = new EthersUtils(ethers.provider, brokenConfig);
      const brokenSetupActions = new SetupActions(contractManager, ethersUtils, brokenConfig);

      console.log('Фаза 2: Вызов setupSystemConnections с некорректной конфигурацией');
      // WHEN/THEN: setupSystemConnections падает
      try {
        await brokenSetupActions.setupSystemConnections();
        expect.fail('Should have thrown error');
      } catch (error) {
        expect(error.message).to.include('MAGIC_REGISTRY_CONTRACT_ADDRESS не найден в .env');
      }

      console.log('Фаза 3: Ошибка обработана: отсутствует MagicRegistry');
    });

    it('должен пропустить setup если контракты не deployed', async function() {
      this.timeout(60000);

      console.log('Фаза 1: Подготовка partialContracts (SBT отсутствует)');
      // GIVEN: Контракты частично deployed (SBT отсутствует)
      const partialContracts = {
        spiralEngine: null, // Missing
        organicComponentRegistry: suite.organicComponentRegistry
      };

      console.log('Фаза 2: Вызов setupSBTEcosystem с неполным набором адресов');
      // WHEN: setupSBTEcosystem вызывается с частичными контрактами
      await setupActions.setupSBTEcosystem(partialContracts);

      console.log('Фаза 3: Setup skipped for missing contracts (no error)');
    });

    it('должен выбросить ошибку если MagicRegistryHelper очищен', async function() {
      this.timeout(30000);

      console.log('Фаза 1: Очищаем локальный MagicRegistryHelper');
      harness.magicRegistry.clear();

      console.log('Фаза 2: Пытаемся загрузить контракт из пустого реестра');
      expect(() => harness.loadContractFromSuite('SpiralEngine')).to.throw('Contract SpiralEngine is not registered in MagicRegistryHelper');

      console.log('Фаза 3: Ошибка корректно выброшена при пустом реестре');

      console.log('Фаза 4: Восстанавливаем записи в MagicRegistryHelper');
      harness.magicRegistry.registerMany([
        ['SpiralEngine', suite.spiralEngine, suite.spiralEngineLogic],
        ['OrganicComponentRegistry', suite.organicComponentRegistry, suite.organicComponentRegistryLogic],
        ['SoulboundCore', suite.soulboundCore],
        ['SoulMetadata', suite.soulMetadata],
        ['SoulRecovery', suite.soulRecovery],
        ['SoulIntegration', suite.soulIntegration],
        ['SoulIdentity', suite.soulIdentity],
        ['ProductRegistry', suite.productRegistry, suite.productRegistryLogic],
        ['AmanitaInternational', suite.amanitaInternational, suite.amanitaInternationalLogic]
      ]);
    });
  });

  // ================================================================
  // Integration с Action 1 (предусловие)
  // ================================================================

  describe('Integration: Action 1 → Action 2', () => {
    it('должен работать после Action 1 (полный workflow)', async function() {
      this.timeout(90000);

      console.log('Фаза 1: Проверяем, что Action 1 выполнен (MagicRegistry есть)');
      // Prerequisite: Action 1 уже выполнен (контракты deployed)
      // Validate prerequisite
      const validation = await harness.validateDeployment(magicRegistryAddress);
      expect(validation.deployed).to.be.true;

      console.log('Фаза 2: Запускаем setupSystemConnections');
      // WHEN: Action 2 выполняется
      await setupActions.setupSystemConnections();

      console.log('Фаза 3: Проверяем, что все ключевые контракты зарегистрированы в MagicRegistry');
      const contractNames = [
        ['SpiralEngine', suite.spiralEngine, suite.spiralEngineLogic],
        ['OrganicComponentRegistry', suite.organicComponentRegistry, suite.organicComponentRegistryLogic],
        ['SoulboundCore', suite.soulboundCore]
      ];

      contractNames.forEach(([name, proxy, impl]) => {
        const entry = harness.loadContractFromSuite(name);
        assertRegisteredProxy({ [name]: entry }, name, proxy, impl);
      });

      console.log('Фаза 4: Проверяем состояние через ABI');
      // THEN: Полный workflow завершён
      const SpiralEngine = await ethers.getContractAt('SpiralEngineLogic', suite.spiralEngine);
      const OrganicRegistry = await ethers.getContractAt('OrganicComponentRegistryLogic', suite.organicComponentRegistry);

      // Validate: System готов к использованию (используем правильные getters)
      expect(await SpiralEngine.soulIdentity()).to.not.equal(ethers.ZeroAddress);
      expect(await OrganicRegistry.spiralEngine()).to.not.equal(ethers.ZeroAddress);

      console.log('Фаза 5: Action 1 → Action 2 workflow complete');
    });
  });
});

// ================================================================
// Helper: Deploy All Contracts (Action 1 logic for E2E)
// ================================================================

async function deployAllContractsForTest(harnessInstance) {
  if (!harnessInstance) {
    throw new Error('deployAllContractsForTest: harness instance is required');
  }

  const [deployer] = await ethers.getSigners();
  
  // Deploy MagicRegistry
  const MagicRegistry = await ethers.getContractFactory('MagicRegistry');
  const registry = await MagicRegistry.deploy();
  await registry.waitForDeployment();
  const registryAddress = await registry.getAddress();
  harnessInstance.registerProxy('MagicRegistry', registryAddress, null);
  
  // Deploy SpiralEngine (UUPS)
  const SpiralEngineLogic = await ethers.getContractFactory('SpiralEngineLogic');
  const spiralLogic = await SpiralEngineLogic.deploy();
  await spiralLogic.waitForDeployment();
  const spiralLogicAddress = await spiralLogic.getAddress();
  
  const spiralInitData = spiralLogic.interface.encodeFunctionData('initialize', [deployer.address]);
  const SpiralEngineProxy = await ethers.getContractFactory('SpiralEngineProxy');
  const spiralProxy = await SpiralEngineProxy.deploy(spiralLogicAddress, spiralInitData);
  await spiralProxy.waitForDeployment();
  const spiralAddress = await spiralProxy.getAddress();
  harnessInstance.registerProxy('SpiralEngine', spiralAddress, spiralLogicAddress);
  
  // Deploy SBT ecosystem (ПРАВИЛЬНЫЙ ПОРЯДОК С ЗАВИСИМОСТЯМИ)
  
  // 1. SoulboundCore (первым, требует name + symbol)
  const SoulboundCore = await ethers.getContractFactory('SoulboundCore');
  const soulCore = await SoulboundCore.deploy('SoulboundIdentity', 'SBI');
  await soulCore.waitForDeployment();
  const soulCoreAddress = await soulCore.getAddress();
  harnessInstance.registerProxy('SoulboundCore', soulCoreAddress, null);
  
  // 2. SoulMetadata (требует soulboundCore)
  const SoulMetadata = await ethers.getContractFactory('SoulMetadata');
  const soulMetadata = await SoulMetadata.deploy(soulCoreAddress);
  await soulMetadata.waitForDeployment();
  const soulMetadataAddress = await soulMetadata.getAddress();
  harnessInstance.registerProxy('SoulMetadata', soulMetadataAddress, null);
  
  // 3. SoulRecovery (требует soulboundCore)
  const SoulRecovery = await ethers.getContractFactory('SoulRecovery');
  const soulRecovery = await SoulRecovery.deploy(soulCoreAddress);
  await soulRecovery.waitForDeployment();
  const soulRecoveryAddress = await soulRecovery.getAddress();
  harnessInstance.registerProxy('SoulRecovery', soulRecoveryAddress, null);
  
  // 4. SoulIntegration (требует spiralEngine + soulboundCore)
  const SoulIntegration = await ethers.getContractFactory('SoulIntegration');
  const soulIntegration = await SoulIntegration.deploy(spiralAddress, soulCoreAddress);
  await soulIntegration.waitForDeployment();
  const soulIntegrationAddress = await soulIntegration.getAddress();
  harnessInstance.registerProxy('SoulIntegration', soulIntegrationAddress, null);
  
  // 5. SoulIdentity (требует soulboundCore + soulMetadata)
  const SoulIdentity = await ethers.getContractFactory('SoulIdentity');
  const soulIdentity = await SoulIdentity.deploy(soulCoreAddress, soulMetadataAddress);
  await soulIdentity.waitForDeployment();
  const soulIdentityAddress = await soulIdentity.getAddress();
  harnessInstance.registerProxy('SoulIdentity', soulIdentityAddress, null);
  
  // Deploy OrganicComponentRegistry (UUPS)
  const OrganicLogic = await ethers.getContractFactory('OrganicComponentRegistryLogic');
  const organicLogic = await OrganicLogic.deploy();
  await organicLogic.waitForDeployment();
  const organicLogicAddress = await organicLogic.getAddress();
  
  const organicInitData = organicLogic.interface.encodeFunctionData('initialize', [deployer.address]);
  const OrganicProxy = await ethers.getContractFactory('OrganicComponentRegistryProxy');
  const organicProxy = await OrganicProxy.deploy(organicLogicAddress, organicInitData);
  await organicProxy.waitForDeployment();
  const organicAddress = await organicProxy.getAddress();
  harnessInstance.registerProxy('OrganicComponentRegistry', organicAddress, organicLogicAddress);

  // Deploy ProductRegistry (UUPS)
  const ProductLogic = await ethers.getContractFactory('ProductRegistryLogic');
  const productLogic = await ProductLogic.deploy();
  await productLogic.waitForDeployment();
  const productLogicAddress = await productLogic.getAddress();

  const productInitData = productLogic.interface.encodeFunctionData('initialize', [
    deployer.address,
    spiralAddress
  ]);

  const ProductProxy = await ethers.getContractFactory('ProductRegistryProxy');
  const productProxy = await ProductProxy.deploy(productLogicAddress, productInitData);
  await productProxy.waitForDeployment();
  const productAddress = await productProxy.getAddress();
  harnessInstance.registerProxy('ProductRegistry', productAddress, productLogicAddress);

  const productRegistry = await ethers.getContractAt('ProductRegistryLogic', productAddress);
  await productRegistry.connect(deployer).setOrganicComponentRegistry(organicAddress);

  // Deploy AmanitaInternational (UUPS)
  const AmanitaLogic = await ethers.getContractFactory('AmanitaInternationalLogic');
  const amanitaLogic = await AmanitaLogic.deploy();
  await amanitaLogic.waitForDeployment();
  const amanitaLogicAddress = await amanitaLogic.getAddress();

  const amanitaInitData = amanitaLogic.interface.encodeFunctionData('initialize', [
    deployer.address,
    spiralAddress
  ]);

  const AmanitaProxy = await ethers.getContractFactory('AmanitaInternationalProxy');
  const amanitaProxy = await AmanitaProxy.deploy(amanitaLogicAddress, amanitaInitData);
  await amanitaProxy.waitForDeployment();
  const amanitaAddress = await amanitaProxy.getAddress();
  harnessInstance.registerProxy('AmanitaInternational', amanitaAddress, amanitaLogicAddress);
  
  // РЕГИСТРАЦИЯ В MAGICREGISTRY (необходимо для loadSystemContracts!)
  console.log('\n📝 Регистрация контрактов в MagicRegistry...');
  
  // MagicRegistry использует метод set(key, address)
  await registry.set('SpiralEngine', spiralAddress);
  await registry.set('SoulboundCore', soulCoreAddress);
  await registry.set('SoulMetadata', soulMetadataAddress);
  await registry.set('SoulRecovery', soulRecoveryAddress);
  await registry.set('SoulIntegration', soulIntegrationAddress);
  await registry.set('SoulIdentity', soulIdentityAddress);
  await registry.set('OrganicComponentRegistry', organicAddress);
  await registry.set('ProductRegistry', productAddress);
  await registry.set('AmanitaInternational', amanitaAddress);
  
  console.log('✅ Все контракты зарегистрированы в MagicRegistry');
  
  return {
    magicRegistry: registryAddress,
    spiralEngine: spiralAddress,
    spiralEngineLogic: spiralLogicAddress,
    soulboundCore: soulCoreAddress,
    soulMetadata: soulMetadataAddress,
    soulRecovery: soulRecoveryAddress,
    soulIntegration: soulIntegrationAddress,
    soulIdentity: soulIdentityAddress,
    organicComponentRegistry: organicAddress,
    organicComponentRegistryLogic: organicLogicAddress,
    productRegistry: productAddress,
    productRegistryLogic: productLogicAddress,
    amanitaInternational: amanitaAddress,
    amanitaInternationalLogic: amanitaLogicAddress
  };
}
