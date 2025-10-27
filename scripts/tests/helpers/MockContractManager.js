/**
 * Mock Contract Manager
 * 
 * Provides a mock implementation of ContractManager for testing.
 */

class MockContractManager {
  constructor() {
    this.contracts = new Map();
    this.deployments = [];
    this.artifacts = new Map();
  }

  /**
   * Load contract artifact (mocked)
   * @param {string} contractName - Contract name
   * @returns {Object} - Mock artifact
   */
  async loadContractArtifact(contractName) {
    if (this.artifacts.has(contractName)) {
      return this.artifacts.get(contractName);
    }

    const mockArtifact = {
      contractName,
      abi: [],
      bytecode: '0x608060405234801561001057600080fd5b50',
      deployedBytecode: '0x608060405234801561001057600080fd5b50'
    };

    this.artifacts.set(contractName, mockArtifact);
    return mockArtifact;
  }

  /**
   * Load contract (mocked)
   * @param {string} contractName - Contract name
   * @param {string} address - Contract address (optional)
   * @returns {Object} - Mock contract instance
   */
  async loadContract(contractName, address = null) {
    if (this.contracts.has(contractName)) {
      return this.contracts.get(contractName);
    }

    const mockContract = {
      options: {
        address: address || `0x${contractName}MockAddress`,
        jsonInterface: []
      },
      methods: this.createMockMethods(contractName)
    };

    this.contracts.set(contractName, mockContract);
    return mockContract;
  }

  /**
   * Deploy UUPS contract (mocked)
   * @param {string} contractName - Contract name
   * @param {Array} logicArgs - Logic constructor arguments
   * @param {Array} initArgs - Initialize arguments
   * @returns {Object} - Mock deployed contract
   */
  async deployUUPSContract(contractName, logicArgs = [], initArgs = []) {
    const mockAddress = `0x${contractName}ProxyMock`;
    const mockContract = {
      options: {
        address: mockAddress,
        jsonInterface: []
      },
      methods: this.createMockMethods(contractName)
    };

    this.deployments.push({
      contractName,
      type: 'UUPS',
      logicArgs,
      initArgs,
      address: mockAddress
    });

    this.contracts.set(contractName, mockContract);
    return mockContract;
  }

  /**
   * Deploy single contract (mocked)
   * @param {string} contractName - Contract name
   * @param {Object} options - Deployment options
   * @returns {Object} - Mock deployed contract
   */
  async deploySingleContract(contractName, options = {}) {
    const mockAddress = `0x${contractName}Mock`;
    const mockContract = {
      options: {
        address: mockAddress,
        jsonInterface: []
      },
      methods: this.createMockMethods(contractName)
    };

    this.deployments.push({
      contractName,
      type: 'Single',
      options,
      address: mockAddress
    });

    this.contracts.set(contractName, mockContract);
    return mockContract;
  }

  /**
   * Create mock methods for contract
   * @param {string} contractName - Contract name
   * @returns {Object} - Mock methods
   */
  createMockMethods(contractName) {
    return {
      registerContract: () => ({
        send: async () => ({ transactionHash: '0xmocktxhash' })
      }),
      getAddress: () => ({
        call: async () => `0x${contractName}Address`
      }),
      initialize: (...args) => ({
        encodeABI: () => '0xmockinitdata',
        send: async () => ({ transactionHash: '0xmocktxhash' })
      })
    };
  }

  /**
   * Get contract (from cache)
   * @param {string} contractName - Contract name
   * @returns {Object|undefined} - Contract instance or undefined
   */
  getContract(contractName) {
    return this.contracts.get(contractName);
  }

  /**
   * Get all deployments
   * @returns {Array} - Array of deployment records
   */
  getDeployments() {
    return this.deployments;
  }

  /**
   * Clear all contracts and deployments
   */
  clearAll() {
    this.contracts.clear();
    this.deployments = [];
    this.artifacts.clear();
  }
}

module.exports = MockContractManager;

