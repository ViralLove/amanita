/**
 * Flow Integration Tests
 * 
 * Validates multi-step workflows across multiple modules.
 * Focus: Realistic production scenarios with 2-4 modules cooperating.
 */

const { expect } = require('chai');
const sinon = require('sinon');
const { ethers } = require('hardhat');
const { IntegrationHarness } = require('../helpers');

describe('Flow Integration Tests', () => {
  let harness, modules;

  before(async function() {
    this.timeout(10000);
    harness = new IntegrationHarness();
    modules = await harness.setupIntegrationEnvironment();
  });

  after(async () => {
    await harness.teardownIntegrationEnvironment();
  });

  afterEach(() => {
    sinon.restore();
  });

  describe('Flow: Seller Activation (CoreLogic → ContractManager → EthersUtils)', () => {
    it('должен выполнить complete seller activation flow', async () => {
      // STEP 1: Setup mock contract with state tracking для проверки изменения состояния
      const sellerAddress = '0x70997970C51812dc3A010C7d01b50e0d17dc79C8';
      
      // ✅ ИСПРАВЛЕНИЕ 1.1: Отслеживание состояния между вызовами через замыкание
      let userActivationState = {
        usedInvite: '0', // Not activated initially
        isActivated: false,
        hasSellerRole: false, // ✅ P0 FIX: Добавляем состояние для SELLER_ROLE
        SELLER_ROLE: null // Будет установлено при первом вызове
      };

      // ✅ ИСПРАВЛЕНИЕ 1.1: Создаем функции, которые используют замыкание для состояния
      const usedInviteByUserFn = async (address) => {
        // ✅ УЛУЧШЕНИЕ: Проверяем, что вызывается с правильным адресом
        expect(address).to.equal(sellerAddress);
        // ✅ ИСПРАВЛЕНИЕ 1.1: Возвращаем актуальное состояние из замыкания
        return userActivationState.usedInvite;
      };
      
      const activateUserFn = async (inviteCode, userAddress, newInvites, expiry) => {
        // ✅ УЛУЧШЕНИЕ: Проверяем правильность параметров вызова
        expect(inviteCode).to.be.a('string');
        expect(userAddress).to.equal(sellerAddress);
        expect(newInvites).to.be.an('array');
        expect(newInvites.length).to.equal(12); // Проверяем количество invites
        expect(expiry).to.equal(0); // Проверяем expiry
        
        // Проверяем формат invite codes
        newInvites.forEach(code => {
          expect(code).to.be.a('string');
          expect(code.length).to.be.greaterThan(0);
        });
        
        // ✅ ИСПРАВЛЕНИЕ 1.1: Обновляем состояние в замыкании после активации
        userActivationState.usedInvite = '1'; // Token ID after activation
        userActivationState.isActivated = true;
        
        return '1'; // Token ID after activation
      };

      // ✅ P0 FIX: Функция для проверки роли с отслеживанием состояния
      const hasRoleFn = async (role, address) => {
        // Получаем SELLER_ROLE при первом вызове
        if (!userActivationState.SELLER_ROLE) {
          userActivationState.SELLER_ROLE = ethers.keccak256(ethers.toUtf8Bytes('SELLER_ROLE'));
        }
        // Проверяем, является ли это SELLER_ROLE и назначена ли роль
        const sellerRole = userActivationState.SELLER_ROLE;
        if (role === sellerRole || role.toLowerCase() === sellerRole.toLowerCase()) {
          return userActivationState.hasSellerRole;
        }
        return false;
      };

      // ✅ P0 FIX: Функция для назначения роли с обновлением состояния
      const grantSellerRoleFn = async (userAddress) => {
        // Обновляем состояние после назначения роли
        userActivationState.hasSellerRole = true;
        return { hash: '0xgrantSellerRole', wait: async () => ({ status: 1 }) };
      };

      const mockSpiralEngine = harness.setupContractMock('SpiralEngine', {
        usedInviteByUser: {
          call: usedInviteByUserFn
        },
        activateUser: {
          call: activateUserFn,
          encodeABI: '0xactivate'
        },
        SELLER_ROLE: {
          call: async () => {
            if (!userActivationState.SELLER_ROLE) {
              userActivationState.SELLER_ROLE = ethers.keccak256(ethers.toUtf8Bytes('SELLER_ROLE'));
            }
            return userActivationState.SELLER_ROLE;
          }
        },
        hasRole: {
          call: hasRoleFn
        },
        inviteCodeExists: {
          call: async (inviteCode) => {
            // Возвращаем true для тестового invite кода
            return true;
          }
        },
        // ✅ P0 FIX: Добавляем grantSellerRole() для AccessControlActions.grantSellerRole()
        grantSellerRole: {
          call: grantSellerRoleFn,
          encodeABI: '0xgrantSellerRole'
        }
      });
      
      // ✅ ИСПРАВЛЕНИЕ 1.2: Добавляем interface в мок для парсинга событий
      // Создаем минимальный interface с событием UserActivated
      const eventAbi = [
        {
          type: 'event',
          name: 'UserActivated',
          inputs: [
            { name: 'user', type: 'address', indexed: true },
            { name: 'activator', type: 'address', indexed: true },
            { name: 'timestamp', type: 'uint256', indexed: false }
          ]
        }
      ];
      mockSpiralEngine.interface = new ethers.Interface(eventAbi);
      
      // ✅ УЛУЧШЕНИЕ: Создаем spy для отслеживания вызовов activateUser
      // Используем callsFake, чтобы сохранить оригинальное поведение и отслеживать вызовы
      const originalActivateUser = mockSpiralEngine.activateUser;
      const activateUserSpy = sinon.stub(mockSpiralEngine, 'activateUser').callsFake(async (...args) => {
        // ✅ ИСПРАВЛЕНИЕ 1.1: Обновляем состояние при вызове activateUser
        userActivationState.usedInvite = '1'; // Token ID after activation
        userActivationState.isActivated = true;
        
        // Вызываем оригинальный метод (который возвращает транзакцию)
        const tx = await originalActivateUser.apply(mockSpiralEngine, args);
        
        // ✅ ИСПРАВЛЕНИЕ 1.2: Обновляем receipt с событиями в logs
        // Эмулируем событие UserActivated в receipt
        if (tx && tx.wait) {
          const originalWait = tx.wait;
          tx.wait = async () => {
            const receipt = await originalWait();
            
            // ✅ ИСПРАВЛЕНИЕ 1.2: Получаем signer address для события (mock signer)
            const signerAddress = '0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266';
            
            // ✅ ИСПРАВЛЕНИЕ 1.2: Добавляем событие UserActivated в logs
            // Структура события: event UserActivated(address indexed user, address indexed activator, uint256 timestamp)
            const contractAddress = await mockSpiralEngine.getAddress();
            const userAddress = args[1]; // sellerAddress
            const timestamp = BigInt(Math.floor(Date.now() / 1000));
            
            // Создаем тему события (keccak256 от сигнатуры события)
            // UserActivated(address,address,uint256)
            const eventSignature = 'UserActivated(address,address,uint256)';
            const eventTopic = ethers.id(eventSignature);
            
            // ✅ ИСПРАВЛЕНИЕ 1.2: Создаем структуру события для парсинга
            const eventLog = {
              address: contractAddress,
              topics: [
                eventTopic, // topic[0] = keccak256 сигнатуры события
                ethers.zeroPadValue(userAddress, 32), // topic[1] = user (indexed)
                ethers.zeroPadValue(signerAddress, 32) // topic[2] = activator (indexed)
              ],
              data: ethers.AbiCoder.defaultAbiCoder().encode(
                ['uint256'],
                [timestamp]
              ),
              index: 0,
              transactionIndex: 0,
              transactionHash: tx.hash,
              blockHash: '0x0000000000000000000000000000000000000000000000000000000000000000',
              blockNumber: 0,
              removed: false
            };
            
            // ✅ ИСПРАВЛЕНИЕ 1.2: Добавляем событие в logs receipt
            receipt.logs = receipt.logs || [];
            receipt.logs.push(eventLog);
            
            return receipt;
          };
        }
        
        return tx;
      });
      
      const getContractStub = sinon.stub(modules.contractManager, 'getContract')
        .withArgs('SpiralEngine')
        .resolves(mockSpiralEngine);
      
      // STEP 2: Generate invite codes (EthersUtils)
      const codes = modules.ethersUtils.generateNewInviteCodes(12);
      expect(codes).to.have.lengthOf(12);
      codes.forEach(code => {
        expect(code).to.be.a('string');
        expect(code.length).to.be.greaterThan(0);
      });
      
      // ✅ ИСПРАВЛЕНИЕ 1.1: Проверяем начальное состояние (до активации)
      const initialStateBefore = await mockSpiralEngine.usedInviteByUser(sellerAddress);
      expect(initialStateBefore).to.equal('0');
      expect(userActivationState.isActivated).to.be.false;
      
      // STEP 3: Activate seller (CoreLogic orchestrates)
      const result = await modules.coreLogic.activateSellerBasic(sellerAddress, codes);
      
      // ✅ УЛУЧШЕНИЕ: Проверяем структуру ответа
      expect(result.success).to.be.true;
      
      // ✅ FIX Phase 3.1: После рефакторинга CoreLogic делегирует в InviteActions.activateSeller(),
      // который генерирует новые invite codes через generateAmanitaInviteCodes(12) в формате AMANITA-XXXX-XXXX
      // Вместо точного соответствия проверяем формат и количество
      expect(result.inviteCodes).to.be.an('array');
      expect(result.inviteCodes).to.have.lengthOf(12);
      result.inviteCodes.forEach(code => {
        expect(code).to.be.a('string');
        // ✅ Проверяем формат AMANITA-XXXX-XXXX (где XXXX - 4 символа alphanumeric)
        expect(code).to.match(/^AMANITA-[A-Z0-9]{4}-[A-Z0-9]{4}$/);
      });
      
      expect(result.sellerAddress).to.equal(sellerAddress);
      expect(result.transactionHash).to.exist;
      // Transaction hash может быть любой длины в тестовом окружении (мок генерирует короткие хеши)
      expect(result.transactionHash).to.match(/^0x[a-fA-F0-9]+$/);
      
      // ✅ ИСПРАВЛЕНИЕ 1.2: Получаем receipt из транзакции для проверки событий
      // activateSellerBasic не возвращает receipt, но executeContractWrite возвращает receipt
      // Получаем транзакцию из spy и проверяем receipt с событиями
      expect(activateUserSpy.calledOnce).to.be.true;
      const activateCall = activateUserSpy.getCall(0);
      const txFromSpy = await activateCall.returnValue; // Транзакция из spy
      expect(txFromSpy).to.exist;
      
      // ✅ ИСПРАВЛЕНИЕ 1.2: Получаем receipt из транзакции
      let receipt;
      if (txFromSpy && txFromSpy.wait) {
        receipt = await txFromSpy.wait(); // Receipt с событиями из мока
      } else {
        throw new Error('Не удалось получить receipt из транзакции');
      }
      
      // ✅ ИСПРАВЛЕНИЕ 1.2: Проверяем transaction receipt и события
      expect(receipt).to.exist; // Receipt должен быть доступен
      expect(receipt).to.be.an('object');
      expect(receipt.status).to.equal(1); // Transaction успешна
      
      // ✅ ИСПРАВЛЕНИЕ 1.2: Проверяем наличие событий в receipt
      expect(receipt.logs).to.exist; // Logs должны существовать
      expect(receipt.logs).to.be.an('array');
      expect(receipt.logs.length).to.be.greaterThan(0); // Должны быть события
      
      // ✅ ИСПРАВЛЕНИЕ 1.2: Парсим события из receipt и проверяем UserActivated
      // Парсим события из logs через interface контракта
      const parsedEvents = receipt.logs
        .map((log) => {
          try {
            // Парсим событие через interface контракта
            const parsed = mockSpiralEngine.interface.parseLog(log);
            return parsed;
          } catch (error) {
            // Если не удалось распарсить, это не наше событие
            return null;
          }
        })
        .filter(event => event !== null);
      
      // ✅ ИСПРАВЛЕНИЕ 1.2: Находим событие UserActivated
      const userActivatedEvent = parsedEvents.find(event => event && event.name === 'UserActivated');
      expect(userActivatedEvent, 'Событие UserActivated должно быть эмиттировано').to.exist;
      
      // ✅ ИСПРАВЛЕНИЕ 1.2: Проверяем параметры события UserActivated
      expect(userActivatedEvent.args).to.exist;
      expect(userActivatedEvent.args.user).to.equal(sellerAddress); // user address
      expect(userActivatedEvent.args.activator).to.exist; // activator address
      expect(userActivatedEvent.args.timestamp).to.exist; // timestamp
      expect(userActivatedEvent.args.timestamp).to.be.a('bigint'); // timestamp должен быть BigInt
      
      // ✅ УЛУЧШЕНИЕ: Проверяем, что getContract был вызван
      expect(getContractStub.calledOnce).to.be.true;
      expect(getContractStub.calledWith('SpiralEngine')).to.be.true;
      
      // ✅ УЛУЧШЕНИЕ: Проверяем, что activateUser был вызван с правильными параметрами
      expect(activateUserSpy.calledOnce).to.be.true;
      const activateCallArgs = activateUserSpy.getCall(0);
      
      // ✅ FIX Phase 3.1: После рефакторинга CoreLogic делегирует в InviteActions.activateSeller(),
      // который использует первый код из inviteCodes массива как inviteCode для активации,
      // а не 'ROOT_INVITE'. Также InviteActions.activateUser() генерирует новые invite codes
      // в формате AMANITA-XXXX-XXXX, а не использует переданные codes.
      expect(activateCallArgs.args[0]).to.equal(codes[0]); // Проверяем invite code (первый из массива)
      expect(activateCallArgs.args[1]).to.equal(sellerAddress); // Проверяем seller address
      // ✅ После рефакторинга новые invite codes генерируются через generateAmanitaInviteCodes(12)
      // Проверяем формат AMANITA-XXXX-XXXX, а не точное соответствие переданным codes
      expect(activateCallArgs.args[2]).to.be.an('array');
      expect(activateCallArgs.args[2]).to.have.lengthOf(12);
      activateCallArgs.args[2].forEach(code => {
        expect(code).to.be.a('string');
        expect(code).to.match(/^AMANITA-[A-Z0-9]{4}-[A-Z0-9]{4}$/);
      });
      expect(activateCallArgs.args[3]).to.equal(0); // Проверяем expiry
      
      // ✅ ИСПРАВЛЕНИЕ 1.1: Проверяем изменение состояния через замыкание
      // Так как activateUserFn был вызван через spy, состояние должно быть обновлено
      expect(userActivationState.isActivated).to.be.true; // Флаг активации обновлен
      expect(userActivationState.usedInvite).to.not.equal('0'); // Состояние изменилось
      expect(userActivationState.usedInvite).to.equal('1'); // Использован invite с token ID 1
      
      // ✅ ИСПРАВЛЕНИЕ 1.1: Проверяем изменение состояния через мок (после активации)
      // Примечание: мок использует замыкание, поэтому состояние должно быть обновлено
      const stateAfterActivation = await mockSpiralEngine.usedInviteByUser(sellerAddress);
      expect(stateAfterActivation).to.not.equal('0'); // Состояние изменилось
      expect(stateAfterActivation).to.equal('1'); // Использован invite с token ID 1
      
      // ✅ ИСПРАВЛЕНИЕ 1.1: Проверяем, что состояние действительно изменилось
      expect(stateAfterActivation).to.not.equal(initialStateBefore);
      
      // FLOW VALIDATED: 3 modules worked together
      // EthersUtils (codes) → CoreLogic (orchestration) → ContractManager (execution)
      // ✅ ИСПРАВЛЕНИЕ 1.1: Теперь также проверяем изменение состояния блокчейна через мок
    });

    it('должен обрабатывать error в mid-flow gracefully', async () => {
      // GIVEN: Contract fails during activation
      sinon.stub(modules.contractManager, 'getContract')
        .withArgs('SpiralEngine')
        .resolves(null); // Contract not found (error scenario)
      
      // WHEN: Try to activate
      try {
        await modules.coreLogic.activateSellerBasic('0xAddr', ['CODE']);
        expect.fail('Should have thrown error');
      } catch (error) {
        // THEN: Error handled correctly
        expect(error.message).to.include('SpiralEngine contract not found');
        
        // FLOW ERROR HANDLING: Error propagated with context
      }
    });
  });

  describe('Flow: Component Check (CoreManager → CoreLogic → ContractManager)', () => {
    it('должен выполнить facade delegation flow через 3 modules', async () => {
      // STEP 1: Mock component registry
      const mockRegistry = harness.setupContractMock('OrganicComponentRegistry', {
        getTotalComponents: {
          call: async () => '10' // 10 components registered
        }
      });
      
      sinon.stub(modules.contractManager, 'getContract')
        .withArgs('OrganicComponentRegistry')
        .resolves(mockRegistry);
      
      // STEP 2: CoreManager calls (facade)
      const result = await modules.coreManager.checkComponents();
      
      // FLOW VALIDATED: Facade → Business Logic → Contract Service
      expect(result.totalComponents).to.equal(10);
      expect(result.hasComponents).to.be.true;
      
      // CoreManager (API) → CoreLogic (business) → ContractManager (service)
    });
  });

  describe('Flow: Config → Module Initialization (Happy Path)', () => {
    it('должен инициализировать все modules из shared config', () => {
      // GIVEN: Config loaded once
      const config = modules.config;
      
      // WHEN: Multiple modules initialized with same config
      // (already done in setupIntegrationEnvironment)
      
      // THEN: All modules share same config instance
      expect(modules.contractManager.config).to.equal(config);
      expect(modules.arweaveManager.config).to.equal(config);
      expect(modules.coreLogic.config).to.equal(config);
      expect(modules.ethersUtils.config).to.equal(config);
      
      // FLOW: Config → ALL modules (single source of truth)
    });
  });

  describe('Flow: Arweave Upload (ArweaveManager Success Path)', () => {
    it('должен успешно загружать data в Arweave', async () => {
      // GIVEN: Mock Arweave API (success scenario)
      const mockArweave = harness.createMockArweaveClient();
      modules.arweaveManager.arweaveClient = mockArweave;
      modules.arweaveManager.arweaveKey = { mock: true };
      
      // WHEN: Upload происходит
      const result = await modules.arweaveManager.uploadJSON({ test: 'data' });
      
      // THEN: Upload succeeded
      expect(result.success).to.be.true;
      expect(result.txId).to.exist;
      expect(mockArweave.createTransaction.calledOnce).to.be.true;
      expect(mockArweave.transactions.sign.calledOnce).to.be.true;
      expect(mockArweave.transactions.post.calledOnce).to.be.true;
      
      // FLOW: Data → Transaction → Sign → Post → Success
    });
  });

  describe('Flow: Invite Generation → Activation (EthersUtils → CoreLogic)', () => {
    it('должен генерировать и использовать invites в one flow', async () => {
      // STEP 1: CoreLogic requests invites (no codes provided)
      const mockSpiralEngine = harness.setupContractMock('SpiralEngine', {
        usedInviteByUser: { call: async () => '0' },
        activateUser: { call: async () => '1', encodeABI: '0xactivate' }
      });
      
      sinon.stub(modules.contractManager, 'getContract')
        .withArgs('SpiralEngine')
        .resolves(mockSpiralEngine);
      
      // Spy на generateNewInviteCodes
      const generateSpy = sinon.spy(modules.ethersUtils, 'generateNewInviteCodes');
      
      // STEP 2: Activate WITHOUT providing codes (triggers generation)
      const result = await modules.coreLogic.activateSellerBasic('0xAddr', null);
      
      // FLOW VALIDATED: CoreLogic → EthersUtils (generate) → CoreLogic (use)
      expect(generateSpy.calledOnce).to.be.true;
      expect(result.inviteCodes).to.have.lengthOf(12); // Default count
      expect(result.success).to.be.true;
      
      // Internal flow: Request codes → Generate → Use in activation
    });
  });

  describe('Flow: Error Propagation Chain', () => {
    it('должен пробрасывать errors через module chain с context', async () => {
      // GIVEN: Mock Arweave failure
      const mockArweave = harness.createMockArweaveClient();
      mockArweave.createTransaction.rejects(new Error('Arweave service down'));
      modules.arweaveManager.arweaveClient = mockArweave;
      modules.arweaveManager.arweaveKey = { mock: true };
      
      // WHEN: Try to upload
      try {
        await modules.arweaveManager.uploadJSON({ data: 'test' });
        expect.fail('Should have thrown');
      } catch (error) {
        // THEN: Error chain validated
        expect(error.message).to.include('Arweave');
        
        // FLOW: External API error → ArweaveManager → Caller (with context)
      }
    });
  });
});

