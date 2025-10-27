/**
 * Integration Test Harness
 * 
 * Loads multiple REAL modules together for integration testing.
 * Minimal mocking strategy: Mock only external systems (Arweave API, Web3 RPC).
 */

const sinon = require('sinon');
const { ethers } = require('hardhat');

class IntegrationHarness {
  constructor() {
    this.modules = {};
    this.externalMocks = {};
    this.originalEnv = { ...process.env };
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
    const { ActionsManager } = require('../../lib/actions');
    
    // Mock Provider instance (blockchain RPC)
    const mockProvider = this.createMockProvider();
    
    // Create REAL module instances
    this.modules.config = config;
    this.modules.logger = Logger;
    this.modules.ethersUtils = new EthersUtils(mockProvider, config);
    this.modules.contractManager = new ContractManager(mockProvider, config, this.modules.ethersUtils);
    this.modules.arweaveManager = new ArweaveManager(config);
    this.modules.coreLogic = new CoreLogic(
      this.modules.contractManager,
      this.modules.ethersUtils,
      config
    );
    this.modules.coreManager = new CoreManager(
      this.modules.contractManager,
      this.modules.ethersUtils,
      config
    );
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
          return {
            hash: `0x${Math.random().toString(16).substr(2, 64)}`,
            wait: async () => ({ status: 1 })
          };
        }
        
        // Read methods return value
        if (methodConfig.call) {
          return methodConfig.call(...args);
        }
        
        // Default: return transaction
        return {
          hash: `0x${Math.random().toString(16).substr(2, 64)}`,
          wait: async () => ({ status: 1 })
        };
      };
    });
    
    return mockContract;
  }
}

module.exports = IntegrationHarness;

