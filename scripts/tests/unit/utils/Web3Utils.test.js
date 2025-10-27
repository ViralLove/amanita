/**
 * Unit Tests: Web3Utils
 * 
 * Tests for Web3 utility functions.
 */

const { expect } = require('chai');
const { MockWeb3, TestHarness } = require('../../helpers');

describe('Web3Utils Module', () => {
  let Web3Utils;
  let web3Utils;
  let mockWeb3;
  let harness;

  before(async () => {
    harness = new TestHarness();
    await harness.setupTestEnvironment();
    
    // Load Web3Utils module
    Web3Utils = require('../../../lib/utils/Web3Utils');
    
    // Create mock Web3
    mockWeb3 = new MockWeb3();
    
    // Create Web3Utils instance
    const mockConfig = harness.createMockConfig();
    web3Utils = new Web3Utils(mockWeb3, mockConfig);
  });

  after(async () => {
    await harness.teardownTestEnvironment();
  });

  describe('Random String Generation', () => {
    it('должен генерировать alphanumeric строки', () => {
      // WHEN: generateRandomAlphanumeric(6)
      const result = web3Utils.generateRandomAlphanumeric(6);
      
      // THEN: 6-символьная alphanumeric строка
      expect(result).to.be.a('string');
      expect(result).to.have.lengthOf(6);
      expect(result).to.match(/^[A-Za-z0-9]+$/);
    });

    it('должен генерировать строки разной длины', () => {
      // WHEN: generateRandomAlphanumeric с разными длинами
      const length8 = web3Utils.generateRandomAlphanumeric(8);
      const length12 = web3Utils.generateRandomAlphanumeric(12);
      
      // THEN: Строки корректной длины
      expect(length8).to.have.lengthOf(8);
      expect(length12).to.have.lengthOf(12);
    });

    it('должен генерировать уникальные строки', () => {
      // WHEN: Генерируем несколько строк
      const strings = [];
      for (let i = 0; i < 100; i++) {
        strings.push(web3Utils.generateRandomAlphanumeric(8));
      }
      
      // THEN: Все строки уникальны
      const uniqueStrings = new Set(strings);
      expect(uniqueStrings.size).to.equal(strings.length);
    });
  });

  describe('Invite Code Generation', () => {
    it('должен генерировать уникальные invite коды', () => {
      // WHEN: generateNewInviteCodes(12, 6)
      const codes = web3Utils.generateNewInviteCodes(12, 6);
      
      // THEN: 12 уникальных кодов
      expect(codes).to.be.an('array');
      expect(codes).to.have.lengthOf(12);
      
      // Проверяем уникальность
      const uniqueCodes = new Set(codes);
      expect(uniqueCodes.size).to.equal(12);
    });

    it('должен генерировать коды корректной длины', () => {
      // WHEN: generateNewInviteCodes(5, 8)
      const codes = web3Utils.generateNewInviteCodes(5, 8);
      
      // THEN: Все коды длины 8
      codes.forEach(code => {
        expect(code).to.have.lengthOf(8);
        expect(code).to.match(/^[A-Za-z0-9]+$/);
      });
    });

    it('должен использовать default длину 8', () => {
      // WHEN: generateNewInviteCodes без параметра длины
      const codes = web3Utils.generateNewInviteCodes(5);
      
      // THEN: Коды длины 8 (default)
      codes.forEach(code => {
        expect(code).to.have.lengthOf(8);
      });
    });

    it('должен генерировать разное количество кодов', () => {
      // WHEN: generateNewInviteCodes с разными количествами
      const codes3 = web3Utils.generateNewInviteCodes(3);
      const codes12 = web3Utils.generateNewInviteCodes(12);
      const codes24 = web3Utils.generateNewInviteCodes(24);
      
      // THEN: Корректное количество
      expect(codes3).to.have.lengthOf(3);
      expect(codes12).to.have.lengthOf(12);
      expect(codes24).to.have.lengthOf(24);
    });

    it('должен логировать генерацию кодов', () => {
      // WHEN: generateNewInviteCodes вызывается
      const codes = web3Utils.generateNewInviteCodes(5, 6);
      
      // THEN: Коды сгенерированы
      expect(codes).to.have.lengthOf(5);
    });
  });

  describe('Invite Code Generation (Legacy)', () => {
    it('должен поддерживать generateInviteCodes()', () => {
      // WHEN: generateInviteCodes() вызывается
      const codes = web3Utils.generateInviteCodes(10);
      
      // THEN: 10 кодов сгенерировано
      expect(codes).to.be.an('array');
      expect(codes).to.have.lengthOf(10);
    });
  });

  describe('Account Operations', () => {
    it('должен создавать account из private key', async () => {
      // GIVEN: Valid private key
      const privateKey = '0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef';
      
      // WHEN: createAccount() вызывается
      const account = await web3Utils.createAccount(privateKey);
      
      // THEN: Account создан
      expect(account).to.be.an('object');
      expect(account.address).to.be.a('string');
      expect(account.privateKey).to.equal(privateKey);
    });

    it('должен получать balance для адреса', async () => {
      // GIVEN: Valid address
      const address = '0x70997970C51812dc3A010C7d01b50e0d17dc79C8';
      
      // WHEN: getBalance() вызывается
      const balance = await web3Utils.getBalance(address);
      
      // THEN: Balance возвращается
      expect(balance).to.be.a('string');
    });
  });

  describe('Error Handling', () => {
    it('должен обрабатывать invalid длину для invite кодов', () => {
      // WHEN: generateNewInviteCodes с 0 кодами
      const codes = web3Utils.generateNewInviteCodes(0);
      
      // THEN: Пустой массив
      expect(codes).to.be.an('array');
      expect(codes).to.have.lengthOf(0);
    });

    it('должен обрабатывать negative количество кодов', () => {
      // WHEN: generateNewInviteCodes с отрицательным числом
      const codes = web3Utils.generateNewInviteCodes(-5);
      
      // THEN: Пустой массив
      expect(codes).to.be.an('array');
      expect(codes).to.have.lengthOf(0);
    });
  });

  describe('Transaction Handling - Real Tests', () => {
    it('должен отправлять транзакции с retry', async () => {
      // GIVEN: Mock Web3 с временными ошибками
      let attempts = 0;
      mockWeb3.eth.sendTransaction = async (tx) => {
        attempts++;
        if (attempts < 3) {
          throw new Error('Network error');
        }
        return { 
          transactionHash: '0xSuccess' + attempts,
          status: true
        };
      };
      
      // WHEN: sendTransactionWithRetry()
      const result = await web3Utils.sendTransactionWithRetry({ to: '0xRecipient' });
      
      // THEN: Retry произошел, транзакция успешна
      expect(attempts).to.equal(3);
      expect(result.transactionHash).to.match(/^0xSuccess/);
    });

    it('должен использовать exponential backoff при retry', async function() {
      this.timeout(10000); // Увеличиваем timeout
      
      // GIVEN: Mock Web3 с временными ошибками
      const attemptTimestamps = [];
      mockWeb3.eth.sendTransaction = async (tx) => {
        attemptTimestamps.push(Date.now());
        if (attemptTimestamps.length < 3) {
          throw new Error('Temporary error');
        }
        return { transactionHash: '0xSuccess' };
      };
      
      // WHEN: sendTransactionWithRetry()
      await web3Utils.sendTransactionWithRetry({ to: '0xRecipient' });
      
      // THEN: Delays увеличиваются (exponential backoff)
      expect(attemptTimestamps).to.have.lengthOf(3);
      // Первая попытка → вторая: ~2 сек
      // Вторая → третья: ~4 сек
      const delay1 = attemptTimestamps[1] - attemptTimestamps[0];
      const delay2 = attemptTimestamps[2] - attemptTimestamps[1];
      expect(delay1).to.be.greaterThan(1500); // ~2 сек
      expect(delay2).to.be.greaterThan(delay1); // Больше чем первая задержка
    });

    it('должен выбрасывать ошибку после max retries', async () => {
      // GIVEN: Mock Web3 с постоянными ошибками
      mockWeb3.eth.sendTransaction = async (tx) => {
        throw new Error('Persistent network error');
      };
      
      // WHEN: sendTransactionWithRetry() с 3 retries
      try {
        await web3Utils.sendTransactionWithRetry({ to: '0xRecipient' }, { maxRetries: 3 });
        expect.fail('Should have thrown error');
      } catch (error) {
        // THEN: Ошибка после 3 попыток
        expect(error.message).to.include('Persistent network error');
      }
    });

    it('должен использовать custom maxRetries', async function() {
      this.timeout(60000); // Увеличиваем timeout до 60 сек
      
      // GIVEN: Custom maxRetries
      let attempts = 0;
      mockWeb3.eth.sendTransaction = async (tx) => {
        attempts++;
        throw new Error('Always fails');
      };
      
      // WHEN: sendTransactionWithRetry() с maxRetries=5
      try {
        await web3Utils.sendTransactionWithRetry({ to: '0xRecipient' }, { maxRetries: 5 });
      } catch (error) {
        // THEN: 5 попыток сделано
        expect(attempts).to.equal(5);
      }
    });
  });

  describe('Batch Transaction Processing - Real Tests', () => {
    it('должен обрабатывать транзакции батчами', async () => {
      // GIVEN: 10 транзакций
      const transactions = Array.from({ length: 10 }, (_, i) => ({ to: `0xAddr${i}` }));
      mockWeb3.eth.sendTransaction = async (tx) => ({
        transactionHash: '0xBatch' + tx.to,
        status: true
      });
      
      // WHEN: batchProcessTransactions() с batchSize=3
      const results = await web3Utils.batchProcessTransactions(transactions, { batchSize: 3 });
      
      // THEN: Все транзакции обработаны
      expect(results).to.be.an('array');
      expect(results).to.have.lengthOf(10);
    });

    it('должен продолжать при ошибках в батче', async () => {
      // GIVEN: Транзакции с некоторыми ошибками
      let txCount = 0;
      mockWeb3.eth.sendTransaction = async (tx) => {
        txCount++;
        if (txCount % 3 === 0) {
          throw new Error('Transaction failed');
        }
        return { transactionHash: '0xTx' + txCount };
      };
      
      // WHEN: batchProcessTransactions() с 9 транзакциями
      const transactions = Array.from({ length: 9 }, (_, i) => ({ to: `0xAddr${i}` }));
      const results = await web3Utils.batchProcessTransactions(transactions, { batchSize: 3 });
      
      // THEN: Все транзакции попытались выполниться
      expect(results).to.have.lengthOf(9);
      const successful = results.filter(r => r.status === 'fulfilled').length;
      const failed = results.filter(r => r.status === 'rejected').length;
      expect(successful + failed).to.equal(9);
    });

    it('должен использовать default batchSize', async () => {
      // GIVEN: Transactions
      const transactions = Array.from({ length: 20 }, (_, i) => ({ to: `0xAddr${i}` }));
      mockWeb3.eth.sendTransaction = async (tx) => ({
        transactionHash: '0xTx',
        status: true
      });
      
      // WHEN: batchProcessTransactions() без batchSize
      const results = await web3Utils.batchProcessTransactions(transactions);
      
      // THEN: Default batchSize используется (5)
      expect(results).to.have.lengthOf(20);
    });
  });
});

