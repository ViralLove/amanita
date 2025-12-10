/**
 * Integration Test: ComponentActions → uploadSimpleFields → AmanitaInternational (Simple Fields Upload)
 * 
 * Phase 2: Contract Validation - Module boundary handshake for simple fields upload
 * Phase 3: Flow Testing - Contract verification and restoration flow
 * 
 * Goal: Verify that uploadSimpleFields correctly:
 * 1. Verifies contract state using verifyStepCompletion
 * 2. Restores missing fields from state when contract check fails
 * 3. Handles edge cases and format validation
 * 
 * Method: @integration-test-build.core.mdc
 * - Real modules: ComponentActions, uploadSteps (via IntegrationHarness)
 * - Minimal mocks: AmanitaInternational contract (external blockchain API), ArweaveManager (external storage API)
 * - State tracking: Simple fields state via closures
 */

const { expect } = require('chai');
const sinon = require('sinon');
const { ethers } = require('hardhat');
const { IntegrationHarness } = require('../helpers');

describe('Integration: ComponentActions → uploadSimpleFields → AmanitaInternational (Simple Fields)', () => {
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

  describe('Phase 2: Contract Verification - verifyStepCompletion Integration', () => {
    it('должен пропустить загрузку когда данные подтверждены в контракте', async () => {
      // GIVEN: State указывает, что шаг выполнен, и данные есть в контракте
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

      // Mock контракт с данными (все поля присутствуют)
      const mockAmanitaInternational = harness.setupContractMock('AmanitaInternational', {
        getSimpleFieldCID: {
          call: async (fieldKey) => {
            if (fieldKey === 'ComponentDescription.title') {
              return 'cid_title_123';
            }
            if (fieldKey === 'DosageInstruction.description') {
              return 'cid_dosage_456';
            }
            return ethers.ZeroAddress;
          }
        },
        setSimpleFieldCID: {
          call: async () => ({ hash: '0xsetSimple', wait: async () => ({ status: 1 }) }),
          encodeABI: '0xsetSimpleFieldCID'
        }
      });

      sinon.stub(modules.contractManager, 'loadUUPSContract')
        .callsFake((contractName) => {
          if (contractName === 'SpiralEngine') return Promise.resolve(mockSpiralEngine);
          if (contractName === 'AmanitaInternational') return Promise.resolve(mockAmanitaInternational);
          return Promise.resolve(null);
        });

      // WHEN: uploadSimpleFields вызывается с state, где шаг уже выполнен
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

      // THEN: Функция возвращает данные из state без повторной загрузки
      expect(result).to.deep.equal(state.simple_fields);
      expect(mockAmanitaInternational.getSimpleFieldCID.callCount).to.be.at.least(2);
      // setSimpleFieldCID НЕ должен вызываться, так как данные уже в контракте
      expect(mockAmanitaInternational.setSimpleFieldCID).to.not.have.been.called;
    });

    it('должен восстановить данные из state когда контракт пуст', async () => {
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
    });

    it('должен восстановить только отсутствующие поля', async () => {
      // GIVEN: State указывает, что шаг выполнен, но в контракте отсутствует только одно поле
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

      // Mock контракт: title есть, dosage отсутствует
      let setSimpleFieldCIDCalls = [];
      const mockAmanitaInternational = harness.setupContractMock('AmanitaInternational', {
        getSimpleFieldCID: {
          call: async (fieldKey) => {
            if (fieldKey === 'ComponentDescription.title') {
              return 'cid_title_123'; // ✅ Присутствует
            }
            if (fieldKey === 'DosageInstruction.description') {
              return ethers.ZeroAddress; // ❌ Отсутствует
            }
            return ethers.ZeroAddress;
          }
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

      // WHEN: uploadSimpleFields вызывается
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

      // THEN: Восстановлен только dosage (title уже был в контракте)
      expect(result).to.deep.equal(state.simple_fields);
      expect(setSimpleFieldCIDCalls.length).to.equal(1); // Только dosage восстановлен
      expect(setSimpleFieldCIDCalls[0].fieldKey).to.equal('DosageInstruction.description');
      expect(setSimpleFieldCIDCalls[0].cid).to.equal('cid_dosage_456');
    });
  });

  describe('Phase 3: Flow Testing - Full Upload Flow', () => {
    it('должен выполнить полную загрузку когда шаг не выполнен', async () => {
      // GIVEN: State не содержит выполненный шаг
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
      const mockAmanitaInternational = harness.setupContractMock('AmanitaInternational', {
        getSimpleFieldCID: {
          call: async () => ethers.ZeroAddress
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

      // Mock Arweave для полной загрузки
      const mockArweave = harness.createMockArweaveClient();
      modules.arweaveManager.arweaveClient = mockArweave;
      modules.arweaveManager.arweaveKey = { mock: true };

      // WHEN: uploadSimpleFields вызывается с пустым state
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
        arweave: {
          client: mockArweave,
          key: { mock: true }
        }
      };

      const state = {
        steps_completed: [],
        simple_fields: {}
      };

      const result = await uploadSteps.uploadSimpleFields(context, state);

      // THEN: Выполнена полная загрузка (title и dosage)
      expect(result).to.have.property('title');
      expect(result).to.have.property('dosage_types');
      expect(result.title).to.have.property('cid');
      expect(result.dosage_types).to.have.property('cid');
      expect(setSimpleFieldCIDCalls.length).to.equal(2); // Оба поля сохранены в контракт
    });
  });
});

