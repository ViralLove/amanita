/**
 * Integration Test: Node Reset Scenario - Component Upload Restoration
 * 
 * Phase 3: Flow Testing - Node reset scenario with state restoration
 * 
 * Goal: Verify that the system correctly handles node reset scenarios:
 * 1. Test node reset scenario (state exists, contract is empty)
 * 2. Test simple fields restoration after node reset
 * 3. Test complex fields restoration after node reset
 * 4. Test full upload from scratch (no state, no contract)
 * 
 * Method: @integration-test-build.core.mdc
 * - Real modules: ComponentActions, uploadSteps (via IntegrationHarness)
 * - Minimal mocks: AmanitaInternational contract (external blockchain API), ArweaveManager (external storage API)
 * - State tracking: Component state via closures
 * 
 * @version 1.0.0
 * @date 2025-11-25
 */

const { expect } = require('chai');
const sinon = require('sinon');
const { ethers } = require('hardhat');
const { IntegrationHarness } = require('../helpers');

describe('Integration: Node Reset Scenario - Component Upload Restoration', () => {
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
    delete process.env.DEPLOYER_INVITE;
    delete process.env.SELLER_ADDRESS;
    delete process.env.DRY_RUN;
    delete process.env.ARWEAVE;
  });

  // ====================================================================
  // 🔹 TEST 1: Node Reset Scenario (General)
  // ====================================================================

  describe('Test 1: Node Reset Scenario', () => {
    it('должен обнаружить несоответствие между state и контрактом при перезапуске ноды', async () => {
      // GIVEN: State указывает, что шаги выполнены, но контракт пуст (нода перезапущена)
      const sellerAddress = '0x70997970C51812dc3A010C7d01b50e0d17dc79C8';
      const testBiounitId = 'amanita_muscaria';

      let activationState = {
        usedInvite: '1',
        isActivated: true,
        hasSellerRole: true,
        SELLER_ROLE: ethers.keccak256(ethers.toUtf8Bytes('SELLER_ROLE'))
      };

      const mockSpiralEngine = harness.setupContractMock('SpiralEngine', {
        usedInviteByUser: { call: async () => activationState.usedInvite },
        hasRole: { call: async () => activationState.hasSellerRole },
        SELLER_ROLE: { call: async () => activationState.SELLER_ROLE }
      });

      // Mock контракт пуст (все поля отсутствуют - нода перезапущена)
      const mockAmanitaInternational = harness.setupContractMock('AmanitaInternational', {
        getSimpleFieldCID: {
          call: async () => ethers.ZeroAddress // Все поля отсутствуют
        },
        getComplexFieldCID: {
          call: async () => ethers.ZeroAddress // Все поля отсутствуют
        },
        setSimpleFieldCID: {
          call: async () => ({ hash: '0xrestoreSimple', wait: async () => ({ status: 1 }) }),
          encodeABI: '0xsetSimpleFieldCID'
        },
        setComplexFieldCID: {
          call: async () => ({ hash: '0xrestoreComplex', wait: async () => ({ status: 1 }) }),
          encodeABI: '0xsetComplexFieldCID'
        },
        connect: sinon.stub().returnsThis()
      });

      sinon.stub(modules.contractManager, 'loadUUPSContract')
        .callsFake((contractName) => {
          if (contractName === 'SpiralEngine') return Promise.resolve(mockSpiralEngine);
          if (contractName === 'AmanitaInternational') return Promise.resolve(mockAmanitaInternational);
          return Promise.resolve(null);
        });

      // WHEN: Проверяем состояние через contractVerification
      const contractVerification = require('../../lib/contract_verification');
      const state = {
        steps_completed: ['simple_fields_uploaded', 'complex_fields_uploaded'],
        simple_fields: {
          title: { cid: 'cid_title_123' },
          dosage_types: { cid: 'cid_dosage_456' }
        },
        complex_fields: {
          ru: { cid: 'cid_ru_123' },
          en: { cid: 'cid_en_456' }
        }
      };

      // Проверяем simple fields
      const simpleVerification = await contractVerification.verifyStepCompletion({
        state,
        stepName: 'simple_fields_uploaded',
        contractCheckFn: () => contractVerification.checkSimpleFieldsInContract({
          contracts: { amanitaInternational: mockAmanitaInternational },
          seller: { address: sellerAddress },
          biounit_id: testBiounitId
        })
      });

      // Проверяем complex fields
      const complexVerification = await contractVerification.verifyStepCompletion({
        state,
        stepName: 'complex_fields_uploaded',
        contractCheckFn: () => contractVerification.checkComplexFieldsInContract({
          contracts: { amanitaInternational: mockAmanitaInternational },
          biounit_id: testBiounitId,
          supportedLanguages: ['ru', 'en']
        })
      });

      // THEN: Обнаружено несоответствие (state говорит "выполнено", контракт пуст)
      expect(simpleVerification.isComplete).to.be.true; // Шаг выполнен в state
      expect(simpleVerification.isConsistent).to.be.false; // Но данных нет в контракте
      expect(simpleVerification.missingItems).to.have.lengthOf(2); // title и dosage отсутствуют

      expect(complexVerification.isComplete).to.be.true; // Шаг выполнен в state
      expect(complexVerification.isConsistent).to.be.false; // Но данных нет в контракте
      expect(complexVerification.missingItems.length).to.be.greaterThan(0); // Языки отсутствуют
    });
  });

  // ====================================================================
  // 🔹 TEST 2: Simple Fields Restoration
  // ====================================================================

  describe('Test 2: Simple Fields Restoration After Node Reset', () => {
    it('должен восстановить simple fields из state в контракт после перезапуска ноды', async () => {
      // GIVEN: State указывает, что шаг выполнен, но контракт пуст (нода перезапущена)
      const sellerAddress = '0x70997970C51812dc3A010C7d01b50e0d17dc79C8';
      const testBiounitId = 'amanita_muscaria';

      let activationState = {
        usedInvite: '1',
        isActivated: true,
        hasSellerRole: true,
        SELLER_ROLE: ethers.keccak256(ethers.toUtf8Bytes('SELLER_ROLE'))
      };

      const mockSpiralEngine = harness.setupContractMock('SpiralEngine', {
        usedInviteByUser: { call: async () => activationState.usedInvite },
        hasRole: { call: async () => activationState.hasSellerRole },
        SELLER_ROLE: { call: async () => activationState.SELLER_ROLE }
      });

      // Mock контракт без данных (все поля отсутствуют)
      let setSimpleFieldCIDCalls = [];
      const mockAmanitaInternational = harness.setupContractMock('AmanitaInternational', {
        getSimpleFieldCID: {
          call: async () => ethers.ZeroAddress // Все поля отсутствуют
        },
        setSimpleFieldCID: {
          call: async (fieldKey, cid) => {
            setSimpleFieldCIDCalls.push({ fieldKey, cid });
            return { 
              hash: `0xsetSimple${setSimpleFieldCIDCalls.length}`, 
              wait: async () => ({ status: 1 }) 
            };
          },
          encodeABI: '0xsetSimpleFieldCID'
        },
        connect: sinon.stub().returnsThis()
      });

      sinon.stub(modules.contractManager, 'loadUUPSContract')
        .callsFake((contractName) => {
          if (contractName === 'SpiralEngine') return Promise.resolve(mockSpiralEngine);
          if (contractName === 'AmanitaInternational') return Promise.resolve(mockAmanitaInternational);
          return Promise.resolve(null);
        });

      // WHEN: uploadSimpleFields вызывается с state, где шаг выполнен, но контракт пуст
      const uploadSteps = require('../../lib/upload_steps');
      const context = {
        contracts: {
          amanitaInternational: mockAmanitaInternational
        },
        seller: {
          address: sellerAddress,
          signer: await modules.ethersUtils.getSigner(sellerAddress)
        },
        biounit_id: testBiounitId,
        componentDir: require('path').resolve(__dirname, '../../../../data/components', testBiounitId),
        network: 'localhost',
        dryRun: false,
        arweaveOnly: false
      };

      const state = {
        steps_completed: ['simple_fields_uploaded'],
        simple_fields: {
          title: { cid: 'cid_title_123' },
          dosage_types: { cid: 'cid_dosage_456' }
        }
      };

      const result = await uploadSteps.uploadSimpleFields(context, state);

      // THEN: Функция восстановила данные в контракт
      expect(result).to.deep.equal(state.simple_fields);
      expect(setSimpleFieldCIDCalls.length).to.equal(2); // title и dosage восстановлены
      expect(setSimpleFieldCIDCalls.find(c => c.fieldKey === 'ComponentDescription.title')).to.exist;
      expect(setSimpleFieldCIDCalls.find(c => c.fieldKey === 'DosageInstruction.description')).to.exist;
      
      // THEN: CIDs восстановлены из state
      const titleCall = setSimpleFieldCIDCalls.find(c => c.fieldKey === 'ComponentDescription.title');
      expect(titleCall.cid).to.equal('cid_title_123');
      const dosageCall = setSimpleFieldCIDCalls.find(c => c.fieldKey === 'DosageInstruction.description');
      expect(dosageCall.cid).to.equal('cid_dosage_456');
    });
  });

  // ====================================================================
  // 🔹 TEST 3: Complex Fields Restoration
  // ====================================================================

  describe('Test 3: Complex Fields Restoration After Node Reset', () => {
    it('должен восстановить complex fields из state в контракт после перезапуска ноды', async () => {
      // GIVEN: State указывает, что шаг выполнен, но контракт пуст (нода перезапущена)
      const sellerAddress = '0x70997970C51812dc3A010C7d01b50e0d17dc79C8';
      const testBiounitId = 'amanita_muscaria';

      let activationState = {
        usedInvite: '1',
        isActivated: true,
        hasSellerRole: true,
        SELLER_ROLE: ethers.keccak256(ethers.toUtf8Bytes('SELLER_ROLE'))
      };

      const mockSpiralEngine = harness.setupContractMock('SpiralEngine', {
        usedInviteByUser: { call: async () => activationState.usedInvite },
        hasRole: { call: async () => activationState.hasSellerRole },
        SELLER_ROLE: { call: async () => activationState.SELLER_ROLE }
      });

      // Mock контракт без данных (все поля отсутствуют)
      let setComplexFieldCIDCalls = [];
      const mockAmanitaInternational = harness.setupContractMock('AmanitaInternational', {
        getComplexFieldCID: {
          call: async () => ethers.ZeroAddress // Все поля отсутствуют
        },
        setComplexFieldCID: {
          call: async (className, lang, cid) => {
            setComplexFieldCIDCalls.push({ className, lang, cid });
            return { 
              hash: `0xsetComplex${setComplexFieldCIDCalls.length}`, 
              wait: async () => ({ status: 1 }) 
            };
          },
          encodeABI: '0xsetComplexFieldCID'
        },
        connect: sinon.stub().returnsThis()
      });

      sinon.stub(modules.contractManager, 'loadUUPSContract')
        .callsFake((contractName) => {
          if (contractName === 'SpiralEngine') return Promise.resolve(mockSpiralEngine);
          if (contractName === 'AmanitaInternational') return Promise.resolve(mockAmanitaInternational);
          return Promise.resolve(null);
        });

      // WHEN: uploadComplexFields вызывается с state, где шаг выполнен, но контракт пуст
      const uploadSteps = require('../../lib/upload_steps');
      const context = {
        contracts: {
          amanitaInternational: mockAmanitaInternational
        },
        seller: {
          address: sellerAddress,
          signer: await modules.ethersUtils.getSigner(sellerAddress)
        },
        biounit_id: testBiounitId,
        componentDir: require('path').resolve(__dirname, '../../../../data/components', testBiounitId),
        network: 'localhost',
        dryRun: false,
        arweaveOnly: false,
        supportedLanguages: ['ru', 'en', 'de']
      };

      const state = {
        steps_completed: ['complex_fields_uploaded'],
        complex_fields: {
          ru: { cid: 'cid_ru_123' },
          en: { cid: 'cid_en_456' },
          de: { cid: 'cid_de_789' }
        }
      };

      const result = await uploadSteps.uploadComplexFields(context, state);

      // THEN: Функция восстановила данные в контракт
      expect(result).to.deep.equal(state.complex_fields);
      expect(setComplexFieldCIDCalls.length).to.equal(3); // ru, en, de восстановлены
      
      // THEN: className содержит biounit_id
      const expectedClassName = `ComponentDescription.${testBiounitId}`;
      setComplexFieldCIDCalls.forEach(call => {
        expect(call.className).to.equal(expectedClassName);
      });
      
      // THEN: CIDs восстановлены из state
      const ruCall = setComplexFieldCIDCalls.find(c => c.lang === 'ru');
      expect(ruCall.cid).to.equal('cid_ru_123');
      const enCall = setComplexFieldCIDCalls.find(c => c.lang === 'en');
      expect(enCall.cid).to.equal('cid_en_456');
      const deCall = setComplexFieldCIDCalls.find(c => c.lang === 'de');
      expect(deCall.cid).to.equal('cid_de_789');
    });
  });

  // ====================================================================
  // 🔹 TEST 4: Full Upload From Scratch
  // ====================================================================

  describe('Test 4: Full Upload From Scratch (No State, No Contract)', () => {
    it('должен выполнить полную загрузку когда нет state и нет данных в контракте', async () => {
      // GIVEN: Нет state (шаг не выполнен) и нет данных в контракте
      const sellerAddress = '0x70997970C51812dc3A010C7d01b50e0d17dc79C8';
      const testBiounitId = 'amanita_muscaria';

      let activationState = {
        usedInvite: '1',
        isActivated: true,
        hasSellerRole: true,
        SELLER_ROLE: ethers.keccak256(ethers.toUtf8Bytes('SELLER_ROLE'))
      };

      const mockSpiralEngine = harness.setupContractMock('SpiralEngine', {
        usedInviteByUser: { call: async () => activationState.usedInvite },
        hasRole: { call: async () => activationState.hasSellerRole },
        SELLER_ROLE: { call: async () => activationState.SELLER_ROLE }
      });

      let setSimpleFieldCIDCalls = [];
      let setComplexFieldCIDCalls = [];
      const mockAmanitaInternational = harness.setupContractMock('AmanitaInternational', {
        getSimpleFieldCID: {
          call: async () => ethers.ZeroAddress // Все поля отсутствуют
        },
        getComplexFieldCID: {
          call: async () => ethers.ZeroAddress // Все поля отсутствуют
        },
        setSimpleFieldCID: {
          call: async (fieldKey, cid) => {
            setSimpleFieldCIDCalls.push({ fieldKey, cid });
            return { 
              hash: `0xsetSimple${setSimpleFieldCIDCalls.length}`, 
              wait: async () => ({ status: 1 }) 
            };
          },
          encodeABI: '0xsetSimpleFieldCID'
        },
        setComplexFieldCID: {
          call: async (className, lang, cid) => {
            setComplexFieldCIDCalls.push({ className, lang, cid });
            return { 
              hash: `0xsetComplex${setComplexFieldCIDCalls.length}`, 
              wait: async () => ({ status: 1 }) 
            };
          },
          encodeABI: '0xsetComplexFieldCID'
        },
        connect: sinon.stub().returnsThis()
      });

      sinon.stub(modules.contractManager, 'loadUUPSContract')
        .callsFake((contractName) => {
          if (contractName === 'SpiralEngine') return Promise.resolve(mockSpiralEngine);
          if (contractName === 'AmanitaInternational') return Promise.resolve(mockAmanitaInternational);
          return Promise.resolve(null);
        });

      // Mock Arweave для полной загрузки
      const mockArweave = harness.createMockArweaveClient();
      modules.arweaveManager.arweaveClient = mockArweave;
      modules.arweaveManager.arweaveKey = { mock: true };

      // WHEN: uploadSimpleFields и uploadComplexFields вызываются с пустым state
      const uploadSteps = require('../../lib/upload_steps');
      const componentDir = require('path').resolve(__dirname, '../../../../data/components', testBiounitId);
      const context = {
        contracts: {
          amanitaInternational: mockAmanitaInternational
        },
        seller: {
          address: sellerAddress,
          signer: await modules.ethersUtils.getSigner(sellerAddress)
        },
        biounit_id: testBiounitId,
        componentDir: componentDir,
        network: 'localhost',
        dryRun: false,
        arweaveOnly: false,
        supportedLanguages: ['ru', 'en'],
        arweave: {
          client: mockArweave,
          key: { mock: true }
        }
      };

      const state = {
        steps_completed: [],
        simple_fields: {},
        complex_fields: {}
      };

      const simpleResult = await uploadSteps.uploadSimpleFields(context, state);
      const complexResult = await uploadSteps.uploadComplexFields(context, state);

      // THEN: Выполнена полная загрузка (simple fields)
      expect(simpleResult).to.have.property('title');
      expect(simpleResult).to.have.property('dosage_types');
      expect(simpleResult.title).to.have.property('cid');
      expect(simpleResult.dosage_types).to.have.property('cid');
      expect(setSimpleFieldCIDCalls.length).to.equal(2); // Оба поля сохранены в контракт

      // THEN: Выполнена полная загрузка (complex fields)
      expect(complexResult).to.be.an('object');
      expect(Object.keys(complexResult).length).to.be.greaterThan(0);
      expect(setComplexFieldCIDCalls.length).to.be.greaterThan(0); // Языки сохранены в контракт

      // THEN: className содержит biounit_id
      const expectedClassName = `ComponentDescription.${testBiounitId}`;
      setComplexFieldCIDCalls.forEach(call => {
        expect(call.className).to.equal(expectedClassName);
      });
    });
  });
});

