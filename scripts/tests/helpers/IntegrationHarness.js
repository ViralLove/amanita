/**
 * Integration Test Harness
 * 
 * Loads multiple REAL modules together for integration testing.
 * Minimal mocking strategy: Mock only external systems (Arweave API, Web3 RPC).
 */

const sinon = require('sinon');
const { ethers } = require('hardhat');
const MagicRegistryHelper = require('./MagicRegistryHelper');

class IntegrationHarness {
  constructor() {
    this.modules = {};
    this.externalMocks = {};
    this.originalEnv = { ...process.env };
    this.productSuite = null;
    this.magicRegistry = new MagicRegistryHelper();
  }

  /**
   * Setup integration environment
   * - Load REAL modules (ContractManager, ArweaveManager, CoreLogic, etc)
   * - Mock ONLY external APIs (Arweave, Web3 RPC)
   * - No database needed (modules use in-memory or mock)
   */
  async setupIntegrationEnvironment() {
    // 1. Load test environment
    const path = require('path');
    const testEnvPath = path.join(__dirname, '../fixtures/env/test.env');
    require('dotenv').config({ path: testEnvPath, override: true });
    
    // 2. Mock ONLY external APIs (not our modules!)
    this.setupExternalMocks();
    
    // 3. Load REAL modules
    const config = require('../../lib/config');
    const Logger = require('../../lib/utils/Logger');
    const EthersUtils = require('../../lib/utils/EthersUtils');
    const ContractManager = require('../../lib/services/ContractManager');
    const ArweaveManager = require('../../lib/services/ArweaveManager');
    const { CoreLogic, CoreManager } = require('../../lib/core');
    const { ActionsManager, AccessControlActions, InviteActions } = require('../../lib/actions');
    
    // Mock Provider instance (blockchain RPC)
    const mockProvider = this.createMockProvider();
    
    // Create REAL module instances
    this.modules.config = config;
    this.modules.logger = Logger;
    this.modules.ethersUtils = new EthersUtils(mockProvider, config);
    this.modules.contractManager = new ContractManager(mockProvider, config, this.modules.ethersUtils);
    this.modules.arweaveManager = new ArweaveManager(config);
    
    // ✅ НОВОЕ: Создаем InviteActions и передаем в CoreLogic и CoreManager
    // Создаем AccessControlActions для InviteActions
    const accessControlActions = new AccessControlActions(
      this.modules.contractManager,
      this.modules.ethersUtils,
      config
    );
    
    // Создаем InviteActions
    const inviteActions = new InviteActions(
      this.modules.contractManager,
      this.modules.ethersUtils,
      config,
      accessControlActions
    );
    
    // Обновляем CoreLogic с InviteActions
    this.modules.coreLogic = new CoreLogic(
      this.modules.contractManager,
      this.modules.ethersUtils,
      config,
      inviteActions  // ✅ НОВОЕ
    );
    
    // Обновляем CoreManager с InviteActions
    this.modules.coreManager = new CoreManager(
      this.modules.contractManager,
      this.modules.ethersUtils,
      config,
      inviteActions  // ✅ НОВОЕ
    );
    
    // Сохраняем inviteActions для использования в тестах
    this.modules.inviteActions = inviteActions;
    
    this.modules.actionsManager = new ActionsManager(
      this.modules.contractManager,
      this.modules.arweaveManager,
      this.modules.ethersUtils,
      config
    );
    
    return this.modules;
  }

  /**
   * Setup external API mocks (Arweave only)
   * Do NOT mock our own modules!
   */
  setupExternalMocks() {
    // Mock Arweave API client (external service)
    // We'll stub the actual Arweave methods when needed in tests
    // This is just placeholder for now
    this.externalMocks.arweaveReady = true;
  }

  /**
   * Create mock Provider instance for blockchain RPC
   * This is external dependency (Hardhat node)
   */
  createMockProvider() {
    const mockProvider = {
      getNetwork: async () => ({ chainId: 31337n, name: 'localhost' }),
      getBlockNumber: async () => 100,
      getCode: async (address) => {
        // Return non-empty code for valid addresses
        if (address && address.startsWith('0x')) {
          return '0x608060405234801561001057600080fd5b50';
        }
        return '0x';
      },
      getBalance: async (address) => ethers.parseEther('1'), // 1 ETH as BigInt
      sendTransaction: async (tx) => ({
        hash: `0x${Math.random().toString(16).substr(2, 64)}`,
        wait: async () => ({
          status: 1,
          blockNumber: 101
        })
      }),
      getSigner: async () => ({
        getAddress: async () => '0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266',
        sendTransaction: async (tx) => ({
          hash: `0x${Math.random().toString(16).substr(2, 64)}`,
          wait: async () => ({ status: 1 })
        })
      })
    };
    
    return mockProvider;
  }

  /**
   * Teardown integration environment
   */
  async teardownIntegrationEnvironment() {
    // Restore environment
    process.env = { ...this.originalEnv };
    
    // Restore all stubs
    sinon.restore();
    
    // Clear module cache
    this.modules = {};
    this.externalMocks = {};
    this.productSuite = null;
    this.magicRegistry.clear();
  }

  /**
   * Helper: Create mock Arweave client for tests
   * Returns stub that can be configured per test
   */
  createMockArweaveClient() {
    const mockClient = {
      createTransaction: sinon.stub().callsFake(async (data, key) => {
        return {
          id: `QmMockCID${Date.now()}`,
          tags: [],
          addTag: function(name, value) {
            this.tags.push({ name, value });
          }
        };
      }),
      transactions: {
        sign: sinon.stub().resolves(),
        post: sinon.stub().resolves({ status: 200, data: 'OK' })
      }
    };
    
    return mockClient;
  }

  /**
   * Helper: Setup mock for specific module contract interaction
   * @param {string} contractName - Contract name to mock
   * @param {object} methods - Methods to stub
   */
  setupContractMock(contractName, methods) {
    const mockContract = {
      getAddress: async () => `0x${contractName}Address123`,
      connect: function(signer) {
        return this; // Return self for chaining
      }
    };
    
    // Setup method stubs directly on contract (ethers pattern)
    Object.keys(methods).forEach(methodName => {
      const methodConfig = methods[methodName];
      
      // Detect if this is a write method (has encodeABI or send, or write-like name)
      const isWriteMethod = methodConfig.encodeABI || 
                            methodConfig.send || 
                            /^(activate|mint|grant|register|suspend|set|update)/.test(methodName);
      
      mockContract[methodName] = async (...args) => {
        // Write methods return transaction
        if (isWriteMethod) {
          // ✅ FIX: Вызываем call функцию для обновления состояния
          // Это критично для state tracking в интеграционных тестах
          // Состояние обновляется ДО возврата транзакции (как в реальном блокчейне)
          if (methodConfig.call) {
            await methodConfig.call(...args);
          }
          
          // ✅ FIX: Используем hash из config если указан, иначе генерируем случайный
          const txHash = methodConfig.hash || `0x${Math.random().toString(16).substr(2, 64)}`;
          
          return {
            hash: txHash,
            wait: async () => {
              // ✅ FIX: После wait() состояние уже обновлено через call выше
              return { status: 1 };
            }
          };
        }
        
        // Read methods return value
        if (methodConfig.call) {
          return methodConfig.call(...args);
        }
        
        // Default: return transaction (для обратной совместимости)
        return {
          hash: `0x${Math.random().toString(16).substr(2, 64)}`,
          wait: async () => ({ status: 1 })
        };
      };
    });
    
    return mockContract;
  }

  /**
   * Deploy full ProductRegistry + OrganicComponentRegistry suite
   * Returns deployed contracts, configured sellers и компоненты
   *
    * @param {Object} options
    * @param {number} options.componentsPerSeller
    * @param {Array<string>} options.componentIds
    * @param {boolean} options.forceRedeploy
    */
  async setupProductRegistrySuite(options = {}) {
    const {
      componentsPerSeller = 3,
      componentIds = null,
      forceRedeploy = false
    } = options;

    if (this.productSuite && !forceRedeploy) {
      return this.productSuite;
    }

    const ids =
      componentIds ||
      Array.from({ length: componentsPerSeller }, (_, index) => `harness-comp-${index + 1}`);

    const [admin, seller, otherSeller] = await ethers.getSigners();

    // Deploy SpiralEngine mock
    const SpiralEngineMock = await ethers.getContractFactory(
      'contracts/mocks/MockSpiralEngine.sol:MockSpiralEngine'
    );
    const spiralEngine = await SpiralEngineMock.deploy();
    await spiralEngine.waitForDeployment();
    const spiralEngineAddress = await spiralEngine.getAddress();

    // Deploy OrganicComponentRegistry (logic + proxy)
    const OCRLogic = await ethers.getContractFactory('OrganicComponentRegistryLogic');
    const ocrLogic = await OCRLogic.deploy();
    await ocrLogic.waitForDeployment();
    const ocrLogicAddress = await ocrLogic.getAddress();

    const ocrInitCalldata = ocrLogic.interface.encodeFunctionData('initialize', [admin.address]);
    const OCRProxy = await ethers.getContractFactory('OrganicComponentRegistryProxy');
    const ocrProxy = await OCRProxy.deploy(ocrLogicAddress, ocrInitCalldata);
    await ocrProxy.waitForDeployment();
    const componentRegistryAddress = await ocrProxy.getAddress();

    const componentRegistry = ocrLogic.attach(componentRegistryAddress);
    await componentRegistry.connect(admin).setSpiralEngine(spiralEngineAddress);

    // Настраиваем роли продавцов в SpiralEngine
    const SELLER_ROLE = await spiralEngine.SELLER_ROLE();
    await spiralEngine.setUserActivated(seller.address, true);
    await spiralEngine.grantRole(SELLER_ROLE, seller.address);
    if (otherSeller) {
      await spiralEngine.setUserActivated(otherSeller.address, true);
      await spiralEngine.grantRole(SELLER_ROLE, otherSeller.address);
    }

    // Создаём компоненты для первого продавца
    for (const componentId of ids) {
      await componentRegistry.connect(seller).createComponent(componentId, `Qm${componentId}`);
    }

    // Deploy ProductRegistry (logic + proxy)
    const ProductLogic = await ethers.getContractFactory('ProductRegistryLogic');
    const productLogic = await ProductLogic.deploy();
    await productLogic.waitForDeployment();
    const productLogicAddress = await productLogic.getAddress();

    const initCalldata = productLogic.interface.encodeFunctionData('initialize', [
      admin.address,
      spiralEngineAddress
    ]);

    const ProductProxy = await ethers.getContractFactory('ProductRegistryProxy');
    const productProxy = await ProductProxy.deploy(productLogicAddress, initCalldata);
    await productProxy.waitForDeployment();
    const productProxyAddress = await productProxy.getAddress();

    const productRegistry = productLogic.attach(productProxyAddress);
    await productRegistry.connect(admin).setOrganicComponentRegistry(componentRegistryAddress);

    this.magicRegistry.clear();

    this.productSuite = {
      admin,
      seller,
      otherSeller,
      spiralEngine,
      spiralEngineAddress,
      componentRegistry,
      componentRegistryAddress,
      componentRegistryLogicAddress: ocrLogicAddress,
      productRegistry,
      productRegistryAddress: productProxyAddress,
      productRegistryLogicAddress: productLogicAddress,
      sellerComponentIds: ids,
      SELLER_ROLE
    };

    this.magicRegistry.register('SpiralEngine', spiralEngineAddress, spiralEngineAddress);
    this.magicRegistry.register('OrganicComponentRegistry', componentRegistryAddress, ocrLogicAddress);
    this.magicRegistry.register('ProductRegistry', productProxyAddress, productLogicAddress);

    return this.productSuite;
  }

  getProductRegistrySuite() {
    if (!this.productSuite) {
      throw new Error('ProductRegistry suite has not been initialized. Call setupProductRegistrySuite() first.');
    }
    return this.productSuite;
  }

  clearProductRegistrySuite() {
    this.productSuite = null;
    this.magicRegistry.clear();
  }

  getProductRegistryAddresses() {
    if (!this.productSuite) {
      throw new Error('ProductRegistry suite has not been initialized. Call setupProductRegistrySuite() first.');
    }

    const suite = this.productSuite;

    return {
      spiralEngine: suite.spiralEngineAddress,
      productRegistryProxy: suite.productRegistryAddress,
      productRegistryLogic: suite.productRegistryLogicAddress,
      componentRegistryProxy: suite.componentRegistryAddress,
      componentRegistryLogic: suite.componentRegistryLogicAddress
    };
  }

  getProductRegistrySigners() {
    if (!this.productSuite) {
      throw new Error('ProductRegistry suite has not been initialized. Call setupProductRegistrySuite() first.');
    }

    const { admin, seller, otherSeller } = this.productSuite;

    return { admin, seller, otherSeller };
  }

  async clearSellerCatalog(options = {}) {
    const suite = options.suite || this.productSuite;
    if (!suite) {
      throw new Error('ProductRegistry suite has not been initialized. Call setupProductRegistrySuite() first.');
    }

    const sellerSigner = await this.#resolveSigner(suite, options.seller || suite.seller);
    const sellerAddress = options.sellerAddress || (await sellerSigner.getAddress());

    return suite.productRegistry.connect(sellerSigner).clearSellerCatalog(sellerAddress);
  }

  async grantSellerRole(target, options = {}) {
    const suite = options.suite || this.productSuite;
    if (!suite) {
      throw new Error('ProductRegistry suite has not been initialized. Call setupProductRegistrySuite() first.');
    }

    const adminSigner = await this.#resolveSigner(suite, options.admin || suite.admin);
    const targetAddress = await this.#resolveAddress(target || suite.seller);

    return suite.spiralEngine.connect(adminSigner).grantRole(suite.SELLER_ROLE, targetAddress);
  }

  async revokeSellerRole(target, options = {}) {
    const suite = options.suite || this.productSuite;
    if (!suite) {
      throw new Error('ProductRegistry suite has not been initialized. Call setupProductRegistrySuite() first.');
    }

    const adminSigner = await this.#resolveSigner(suite, options.admin || suite.admin);
    const targetAddress = await this.#resolveAddress(target || suite.seller);

    return suite.spiralEngine.connect(adminSigner).revokeRole(suite.SELLER_ROLE, targetAddress);
  }

  async setSellerActivation(target, isActive = true, options = {}) {
    const suite = options.suite || this.productSuite;
    if (!suite) {
      throw new Error('ProductRegistry suite has not been initialized. Call setupProductRegistrySuite() first.');
    }

    const adminSigner = await this.#resolveSigner(suite, options.admin || suite.admin);
    const targetAddress = await this.#resolveAddress(target || suite.seller);

    return suite.spiralEngine
      .connect(adminSigner)
      .setUserActivated(targetAddress, isActive);
  }

  async #resolveAddress(signerOrAddress) {
    if (typeof signerOrAddress === 'string') {
      return signerOrAddress;
    }
    if (signerOrAddress && typeof signerOrAddress.getAddress === 'function') {
      return signerOrAddress.getAddress();
    }
    throw new Error('Unable to resolve address from provided value');
  }

  async #resolveSigner(suite, signerOrAddress) {
    if (signerOrAddress && typeof signerOrAddress.getAddress === 'function') {
      return signerOrAddress;
    }

    const address = await this.#resolveAddress(signerOrAddress);
    const candidates = [suite.admin, suite.seller, suite.otherSeller].filter(Boolean);

    for (const signer of candidates) {
      if ((await signer.getAddress()).toLowerCase() === address.toLowerCase()) {
        return signer;
      }
    }

    throw new Error(`Signer for address ${address} is not tracked in IntegrationHarness suite`);
  }

  getMagicRegistryHelper() {
    return this.magicRegistry;
  }
}

module.exports = IntegrationHarness;

