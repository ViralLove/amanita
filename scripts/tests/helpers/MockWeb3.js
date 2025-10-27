/**
 * Mock Web3
 * 
 * Provides a mock implementation of Web3 for testing.
 */

class MockWeb3 {
  constructor() {
    this.eth = new MockEth();
    this.utils = new MockUtils();
  }
}

class MockEth {
  constructor() {
    this.accounts = new MockAccounts();
    this.Contract = MockContract;
    this.mockNetworkId = 31337;
    this.mockBlockNumber = 100;
  }

  async net() {
    return {
      getId: async () => this.mockNetworkId
    };
  }

  async getBlockNumber() {
    return this.mockBlockNumber;
  }

  async getBalance(address) {
    return '1000000000000000000'; // 1 ETH
  }

  async sendTransaction(tx) {
    return {
      transactionHash: '0xmocktxhash' + Date.now(),
      blockNumber: this.mockBlockNumber++,
      status: true
    };
  }

  async getTransactionReceipt(txHash) {
    return {
      transactionHash: txHash,
      blockNumber: this.mockBlockNumber,
      status: true,
      logs: []
    };
  }
}

class MockAccounts {
  privateKeyToAccount(privateKey) {
    return {
      address: '0x' + privateKey.substring(2, 42),
      privateKey: privateKey
    };
  }

  create() {
    return {
      address: '0xMockGeneratedAddress' + Date.now(),
      privateKey: '0xMockGeneratedPrivateKey' + Date.now()
    };
  }
}

class MockContract {
  constructor(abi, address) {
    this.options = {
      address: address || '0xMockContractAddress',
      jsonInterface: abi || []
    };
    this.methods = this.createMockMethods();
  }

  createMockMethods() {
    return new Proxy({}, {
      get: (target, prop) => {
        return (...args) => ({
          send: async (options) => ({
            transactionHash: '0xmocktxhash' + Date.now(),
            status: true
          }),
          call: async () => 'MockCallResult',
          encodeABI: () => '0xmockencoded'
        });
      }
    });
  }
}

class MockUtils {
  toWei(value, unit = 'ether') {
    return String(value * Math.pow(10, 18));
  }

  fromWei(value, unit = 'ether') {
    return String(value / Math.pow(10, 18));
  }

  isAddress(address) {
    return /^0x[a-fA-F0-9]{40}$/.test(address);
  }

  keccak256(value) {
    return '0xmockhash' + value;
  }
}

module.exports = MockWeb3;

