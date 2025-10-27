/**
 * Unit Tests: ArweaveManager
 * 
 * Tests for the centralized Arweave management service.
 */

const { expect } = require('chai');
const sinon = require('sinon');
const { TestHarness } = require('../../helpers');

describe('ArweaveManager Service', () => {
  let ArweaveManager;
  let arweaveManager;
  let harness;

  before(async () => {
    harness = new TestHarness();
    await harness.setupTestEnvironment();
    
    // Load ArweaveManager module
    ArweaveManager = require('../../../lib/services/ArweaveManager');
  });

  after(async () => {
    await harness.teardownTestEnvironment();
  });

  beforeEach(() => {
    const mockConfig = harness.createMockConfig();
    arweaveManager = new ArweaveManager(mockConfig);
  });

  describe('Initialization', () => {
    it('должен инициализироваться с config', () => {
      // THEN: ArweaveManager инициализирован
      expect(arweaveManager).to.be.an('object');
      expect(arweaveManager.config).to.be.an('object');
    });

    it('должен иметь null arweaveClient до инициализации', () => {
      // THEN: arweaveClient null
      expect(arweaveManager.arweaveClient).to.be.null;
    });

    it('должен иметь null arweaveKey до инициализации', () => {
      // THEN: arweaveKey null
      expect(arweaveManager.arweaveKey).to.be.null;
    });
  });

  describe('Arweave Client Initialization', () => {
    it('должен иметь метод initialize', () => {
      // THEN: initialize метод существует
      expect(arweaveManager.initialize).to.be.a('function');
    });

    it('должен иметь метод loadArweaveKey', () => {
      // THEN: loadArweaveKey метод существует
      expect(arweaveManager.loadArweaveKey).to.be.a('function');
    });

    it('должен иметь метод checkWalletBalance', () => {
      // THEN: checkWalletBalance метод существует
      expect(arweaveManager.checkWalletBalance).to.be.a('function');
    });
  });

  describe('Upload Operations', () => {
    it('должен иметь метод uploadJSON', () => {
      // THEN: uploadJSON метод существует
      expect(arweaveManager.uploadJSON).to.be.a('function');
    });

    it('должен иметь метод uploadData', () => {
      // THEN: uploadData метод существует
      expect(arweaveManager.uploadData).to.be.a('function');
    });

    it('должен иметь метод uploadFile', () => {
      // THEN: uploadFile метод существует
      expect(arweaveManager.uploadFile).to.be.a('function');
    });
  });

  describe('Connection Testing', () => {
    it('должен иметь метод testConnection', () => {
      // THEN: testConnection метод существует
      expect(arweaveManager.testConnection).to.be.a('function');
    });
  });

  describe('Method Existence', () => {
    it('должен иметь все необходимые методы', () => {
      // THEN: Все методы существуют
      expect(arweaveManager.initialize).to.be.a('function');
      expect(arweaveManager.loadArweaveKey).to.be.a('function');
      expect(arweaveManager.checkWalletBalance).to.be.a('function');
      expect(arweaveManager.uploadJSON).to.be.a('function');
      expect(arweaveManager.uploadData).to.be.a('function');
      expect(arweaveManager.uploadFile).to.be.a('function');
      expect(arweaveManager.testConnection).to.be.a('function');
    });
  });

  describe('Upload Operations - Real Tests', () => {
    beforeEach(() => {
      // Setup mock Arweave client
      const mockTransaction = {
        id: 'QmMockCID' + Date.now(),
        tags: {},
        addTag: function(name, value) { 
          this.tags[name] = value;
          return this;
        }
      };

      arweaveManager.arweaveClient = {
        createTransaction: async (data, key) => mockTransaction,
        transactions: {
          sign: async (tx, key) => tx,
          post: async (tx) => ({ status: 200, statusText: 'OK' })
        }
      };
      
      arweaveManager.arweaveKey = { mock: true, kty: 'RSA' };
    });

    it('должен загружать JSON и возвращать result объект', async () => {
      // GIVEN: Valid JSON data
      const testData = { test: 'data', nested: { value: 123 } };
      
      // WHEN: uploadJSON() вызывается
      const result = await arweaveManager.uploadJSON(testData);
      
      // THEN: Result объект возвращается с txId
      expect(result).to.be.an('object');
      expect(result.success).to.be.true;
      expect(result.txId).to.be.a('string');
      expect(result.txId).to.match(/^QmMock/);
    });

    it('должен добавлять Content-Type tag для JSON', async () => {
      // GIVEN: JSON data
      const testData = { test: 'data' };
      let transaction;
      
      arweaveManager.arweaveClient.createTransaction = async (data, key) => {
        transaction = {
          id: 'QmTestCID',
          tags: {},
          addTag: function(name, value) {
            this.tags[name] = value;
            return this;
          }
        };
        return transaction;
      };
      
      // WHEN: uploadJSON() вызывается
      await arweaveManager.uploadJSON(testData);
      
      // THEN: Content-Type tag добавлен
      expect(transaction.tags['Content-Type']).to.equal('application/json');
    });

    it('должен добавлять custom tags', async () => {
      // GIVEN: Data с custom tags в options
      const customTags = {
        'Component-ID': 'amanita_muscaria',
        'Version': '1.0'
      };
      let transaction;
      
      arweaveManager.arweaveClient.createTransaction = async (data, key) => {
        transaction = {
          id: 'QmTestCID',
          tags: {},
          addTag: function(name, value) {
            this.tags[name] = value;
            return this;
          }
        };
        return transaction;
      };
      
      // WHEN: uploadJSON() с tags в options
      await arweaveManager.uploadJSON({ test: 'data' }, { tags: customTags });
      
      // THEN: Custom tags добавлены (через uploadData)
      expect(transaction.tags['Component-ID']).to.equal('amanita_muscaria');
      expect(transaction.tags['Version']).to.equal('1.0');
    });

    it('должен подписывать транзакцию с arweaveKey', async () => {
      // GIVEN: Mock для проверки sign
      let signCalled = false;
      let usedKey = null;
      
      arweaveManager.arweaveClient.transactions.sign = async (tx, key) => {
        signCalled = true;
        usedKey = key;
        return tx;
      };
      
      // WHEN: uploadJSON() вызывается
      await arweaveManager.uploadJSON({ test: 'data' });
      
      // THEN: Transaction подписана с ключом
      expect(signCalled).to.be.true;
      expect(usedKey).to.deep.equal(arweaveManager.arweaveKey);
    });

    it('должен отправлять транзакцию после подписи', async () => {
      // GIVEN: Mock для проверки post
      let postCalled = false;
      
      arweaveManager.arweaveClient.transactions.post = async (tx) => {
        postCalled = true;
        return { status: 200, statusText: 'OK' };
      };
      
      // WHEN: uploadJSON() вызывается
      await arweaveManager.uploadJSON({ test: 'data' });
      
      // THEN: Transaction отправлена
      expect(postCalled).to.be.true;
    });

    it('должен сериализовать JSON в string', async () => {
      // GIVEN: Object data
      let capturedData;
      
      arweaveManager.arweaveClient.createTransaction = async (data, key) => {
        capturedData = data;
        return {
          id: 'QmTest',
          addTag: () => {},
          tags: {}
        };
      };
      
      // WHEN: uploadJSON() с object
      const testObject = { key: 'value', number: 123 };
      await arweaveManager.uploadJSON(testObject);
      
      // THEN: Data сериализован в JSON string
      expect(capturedData.data).to.be.a('string');
      expect(JSON.parse(capturedData.data)).to.deep.equal(testObject);
    });
  });

  describe('Error Handling - Real Tests', () => {
    it('должен обрабатывать ошибки создания транзакции', async () => {
      // GIVEN: Arweave client с ошибкой
      arweaveManager.arweaveClient = {
        createTransaction: async () => {
          throw new Error('Failed to create transaction');
        }
      };
      arweaveManager.arweaveKey = { mock: true };
      
      // WHEN: uploadJSON() вызывается
      try {
        await arweaveManager.uploadJSON({ test: 'data' });
        expect.fail('Should have thrown error');
      } catch (error) {
        // THEN: Ошибка пробрасывается
        expect(error.message).to.include('Failed to create transaction');
      }
    });

    it('должен обрабатывать ошибки подписи', async () => {
      // GIVEN: Arweave client с ошибкой sign
      arweaveManager.arweaveClient = {
        createTransaction: async () => ({
          id: 'QmTest',
          addTag: () => {},
          tags: {}
        }),
        transactions: {
          sign: async () => {
            throw new Error('Failed to sign');
          }
        }
      };
      arweaveManager.arweaveKey = { mock: true };
      
      // WHEN: uploadJSON() вызывается
      try {
        await arweaveManager.uploadJSON({ test: 'data' });
        expect.fail('Should have thrown error');
      } catch (error) {
        // THEN: Ошибка пробрасывается
        expect(error.message).to.include('Failed to sign');
      }
    });
  });
});

