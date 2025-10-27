/**
 * Unit Tests: SetupActions
 * Tests for contract setup and connections orchestration.
 * 
 * Coverage:
 * - loadSystemContracts() - загрузка через MagicRegistry
 * - setupSBTEcosystem() - связи SBT контрактов
 * - setupOrganicComponentRegistry() - связь с SpiralEngine
 * - setupSystemConnections() - orchestration
 */

const { expect } = require('chai');
const sinon = require('sinon');
const SetupActions = require('../../../lib/actions/SetupActions');

describe('SetupActions', () => {
  let setupActions;
  let mockContractManager;
  let mockEthersUtils;
  let mockConfig;
  let mockSigner;
  let mockMagicRegistry;
  let mockContracts;

  beforeEach(() => {
    // Mock dependencies
    mockContractManager = {
      loadContract: sinon.stub(),
      loadUUPSContract: sinon.stub()
    };

    mockSigner = {
      // Signer будет использоваться для contract.connect()
    };

    mockEthersUtils = {
      getSigner: sinon.stub().returns(mockSigner)
    };

    mockConfig = {
      get: sinon.stub()
    };

    // Mock MagicRegistry
    mockMagicRegistry = {
      get: sinon.stub()
    };

    // Mock contract instances с методами connect, getAddress, set*
    const createMockContract = (name, address) => ({
      _name: name,
      _address: address,
      getAddress: sinon.stub().resolves(address),
      connect: sinon.stub().returnsThis(),
      setMetadataContract: sinon.stub().resolves({ wait: sinon.stub().resolves() }),
      setRecoveryContract: sinon.stub().resolves({ wait: sinon.stub().resolves() }),
      setIntegrationContract: sinon.stub().resolves({ wait: sinon.stub().resolves() }),
      setSoulIdentity: sinon.stub().resolves({ wait: sinon.stub().resolves() }),
      setSpiralEngine: sinon.stub().resolves({ wait: sinon.stub().resolves() })
    });

    // Setup mock contracts
    mockContracts = {
      magicRegistry: mockMagicRegistry,
      spiralEngine: createMockContract('SpiralEngine', '0xSpiral'),
      soulboundCore: createMockContract('SoulboundCore', '0xCore'),
      soulMetadata: createMockContract('SoulMetadata', '0xMetadata'),
      soulRecovery: createMockContract('SoulRecovery', '0xRecovery'),
      soulIntegration: createMockContract('SoulIntegration', '0xIntegration'),
      soulIdentity: createMockContract('SoulIdentity', '0xIdentity'),
      organicComponentRegistry: createMockContract('OrganicComponentRegistry', '0xOrganic'),
      productRegistry: createMockContract('ProductRegistry', '0xProduct'),
      amanitaInternational: createMockContract('AmanitaInternational', '0xAmanita')
    };

    setupActions = new SetupActions(mockContractManager, mockEthersUtils, mockConfig);
  });

  afterEach(() => {
    sinon.restore();
  });

  // ================================================================
  // SMOKE TESTS: Existence & Structure
  // ================================================================

  describe('Initialization', () => {
    it('должен инициализироваться с dependencies', () => {
      expect(setupActions.contractManager).to.equal(mockContractManager);
      expect(setupActions.ethersUtils).to.equal(mockEthersUtils);
      expect(setupActions.config).to.equal(mockConfig);
    });

    it('должен иметь метод setupSystemConnections', () => {
      expect(setupActions.setupSystemConnections).to.be.a('function');
    });

    it('должен иметь метод loadSystemContracts', () => {
      expect(setupActions.loadSystemContracts).to.be.a('function');
    });

    it('должен иметь метод setupSBTEcosystem', () => {
      expect(setupActions.setupSBTEcosystem).to.be.a('function');
    });

    it('должен иметь метод setupOrganicComponentRegistry', () => {
      expect(setupActions.setupOrganicComponentRegistry).to.be.a('function');
    });
  });

  // ================================================================
  // REAL TESTS: loadSystemContracts
  // ================================================================

  describe('loadSystemContracts() - Real Tests', () => {
    beforeEach(() => {
      // Setup config для MAGIC_REGISTRY
      mockConfig.get.withArgs('contracts.magicRegistry').returns('0xMagicRegistry');
      
      // Setup MagicRegistry loading
      mockContractManager.loadContract
        .withArgs('MagicRegistry', '0xMagicRegistry')
        .resolves(mockMagicRegistry);
      
      // Setup MagicRegistry.get() для non-UUPS контрактов
      mockMagicRegistry.get.withArgs('SoulboundCore').resolves('0xCore');
      mockMagicRegistry.get.withArgs('SoulMetadata').resolves('0xMetadata');
      mockMagicRegistry.get.withArgs('SoulRecovery').resolves('0xRecovery');
      mockMagicRegistry.get.withArgs('SoulIntegration').resolves('0xIntegration');
      mockMagicRegistry.get.withArgs('SoulIdentity').resolves('0xIdentity');
      
      // Setup loadContract для non-UUPS
      mockContractManager.loadContract.withArgs('SoulboundCore', '0xCore').resolves(mockContracts.soulboundCore);
      mockContractManager.loadContract.withArgs('SoulMetadata', '0xMetadata').resolves(mockContracts.soulMetadata);
      mockContractManager.loadContract.withArgs('SoulRecovery', '0xRecovery').resolves(mockContracts.soulRecovery);
      mockContractManager.loadContract.withArgs('SoulIntegration', '0xIntegration').resolves(mockContracts.soulIntegration);
      mockContractManager.loadContract.withArgs('SoulIdentity', '0xIdentity').resolves(mockContracts.soulIdentity);
      
      // Setup loadUUPSContract для UUPS контрактов
      mockContractManager.loadUUPSContract.withArgs('SpiralEngine').resolves(mockContracts.spiralEngine);
      mockContractManager.loadUUPSContract.withArgs('ProductRegistry').resolves(mockContracts.productRegistry);
      mockContractManager.loadUUPSContract.withArgs('OrganicComponentRegistry').resolves(mockContracts.organicComponentRegistry);
      mockContractManager.loadUUPSContract.withArgs('AmanitaInternational').resolves(mockContracts.amanitaInternational);
    });

    it('должен загрузить все контракты через MagicRegistry', async () => {
      // WHEN
      const contracts = await setupActions.loadSystemContracts();
      
      // THEN: MagicRegistry загружен
      expect(mockContractManager.loadContract.calledWith('MagicRegistry', '0xMagicRegistry')).to.be.true;
      expect(contracts.magicRegistry).to.equal(mockMagicRegistry);
      
      // THEN: UUPS контракты загружены
      expect(mockContractManager.loadUUPSContract.calledWith('SpiralEngine')).to.be.true;
      expect(mockContractManager.loadUUPSContract.calledWith('ProductRegistry')).to.be.true;
      expect(mockContractManager.loadUUPSContract.calledWith('OrganicComponentRegistry')).to.be.true;
      expect(mockContractManager.loadUUPSContract.calledWith('AmanitaInternational')).to.be.true;
      
      // THEN: Non-UUPS контракты загружены через MagicRegistry
      expect(mockMagicRegistry.get.calledWith('SoulboundCore')).to.be.true;
      expect(mockContractManager.loadContract.calledWith('SoulboundCore', '0xCore')).to.be.true;
    });

    it('должен вернуть объект со всеми контрактами', async () => {
      // WHEN
      const contracts = await setupActions.loadSystemContracts();
      
      // THEN: Все контракты присутствуют
      expect(contracts).to.have.property('magicRegistry');
      expect(contracts).to.have.property('spiralEngine');
      expect(contracts).to.have.property('soulboundCore');
      expect(contracts).to.have.property('organicComponentRegistry');
    });

    it('должен выбросить ошибку если MAGIC_REGISTRY не в .env', async () => {
      // GIVEN: MAGIC_REGISTRY отсутствует
      mockConfig.get.withArgs('contracts.magicRegistry').returns(null);
      
      // WHEN/THEN
      try {
        await setupActions.loadSystemContracts();
        expect.fail('Should have thrown error');
      } catch (error) {
        expect(error.message).to.include('MAGIC_REGISTRY_CONTRACT_ADDRESS не найден в .env');
      }
    });

    it('должен продолжить если один контракт не загружается', async () => {
      // GIVEN: SoulIdentity не загружается
      mockContractManager.loadContract.withArgs('SoulIdentity', '0xIdentity').rejects(new Error('Contract not found'));
      
      // WHEN
      const contracts = await setupActions.loadSystemContracts();
      
      // THEN: Остальные контракты загружены
      expect(contracts).to.have.property('spiralEngine');
      expect(contracts).to.have.property('soulboundCore');
      expect(contracts).not.to.have.property('soulIdentity');
    });
  });

  // ================================================================
  // REAL TESTS: setupSBTEcosystem
  // ================================================================

  describe('setupSBTEcosystem() - Real Tests', () => {
    it('должен настроить 4 связи в SBT ecosystem', async () => {
      // GIVEN: Все SBT контракты доступны
      const contracts = {
        soulboundCore: mockContracts.soulboundCore,
        soulMetadata: mockContracts.soulMetadata,
        soulRecovery: mockContracts.soulRecovery,
        soulIntegration: mockContracts.soulIntegration,
        soulIdentity: mockContracts.soulIdentity,
        spiralEngine: mockContracts.spiralEngine
      };
      
      // WHEN
      await setupActions.setupSBTEcosystem(contracts);
      
      // THEN: Signer получен
      expect(mockEthersUtils.getSigner.calledOnce).to.be.true;
      
      // THEN: 4 связи установлены
      expect(mockContracts.soulboundCore.connect.calledWith(mockSigner)).to.be.true;
      expect(mockContracts.soulboundCore.setMetadataContract.calledOnce).to.be.true;
      expect(mockContracts.soulboundCore.setRecoveryContract.calledOnce).to.be.true;
      expect(mockContracts.soulboundCore.setIntegrationContract.calledOnce).to.be.true;
      expect(mockContracts.spiralEngine.setSoulIdentity.calledOnce).to.be.true;
    });

    it('должен передать правильные адреса в set методы', async () => {
      // GIVEN
      const contracts = {
        soulboundCore: mockContracts.soulboundCore,
        soulMetadata: mockContracts.soulMetadata,
        soulRecovery: mockContracts.soulRecovery,
        soulIntegration: mockContracts.soulIntegration,
        soulIdentity: mockContracts.soulIdentity,
        spiralEngine: mockContracts.spiralEngine
      };
      
      // WHEN
      await setupActions.setupSBTEcosystem(contracts);
      
      // THEN: getAddress() был вызван для каждого контракта
      expect(mockContracts.soulMetadata.getAddress.calledOnce).to.be.true;
      expect(mockContracts.soulRecovery.getAddress.calledOnce).to.be.true;
      expect(mockContracts.soulIntegration.getAddress.calledOnce).to.be.true;
      expect(mockContracts.soulIdentity.getAddress.calledOnce).to.be.true;
    });

    it('должен пропустить setup если soulboundCore отсутствует', async () => {
      // GIVEN: soulboundCore нет
      const contracts = {
        spiralEngine: mockContracts.spiralEngine
      };
      
      // WHEN
      await setupActions.setupSBTEcosystem(contracts);
      
      // THEN: Setup не выполнен
      expect(mockEthersUtils.getSigner.called).to.be.false;
      expect(mockContracts.soulboundCore.setMetadataContract.called).to.be.false;
    });

    it('должен выбросить ошибку при провале транзакции', async () => {
      // GIVEN: setMetadataContract падает
      mockContracts.soulboundCore.setMetadataContract.rejects(new Error('Transaction failed'));
      
      const contracts = {
        soulboundCore: mockContracts.soulboundCore,
        soulMetadata: mockContracts.soulMetadata,
        soulRecovery: mockContracts.soulRecovery,
        soulIntegration: mockContracts.soulIntegration,
        soulIdentity: mockContracts.soulIdentity,
        spiralEngine: mockContracts.spiralEngine
      };
      
      // WHEN/THEN
      try {
        await setupActions.setupSBTEcosystem(contracts);
        expect.fail('Should have thrown error');
      } catch (error) {
        expect(error.message).to.include('Transaction failed');
      }
    });
  });

  // ================================================================
  // REAL TESTS: setupOrganicComponentRegistry
  // ================================================================

  describe('setupOrganicComponentRegistry() - Real Tests', () => {
    it('должен настроить связь с SpiralEngine', async () => {
      // GIVEN
      const contracts = {
        organicComponentRegistry: mockContracts.organicComponentRegistry,
        spiralEngine: mockContracts.spiralEngine
      };
      
      // WHEN
      await setupActions.setupOrganicComponentRegistry(contracts);
      
      // THEN: Связь установлена
      expect(mockEthersUtils.getSigner.calledOnce).to.be.true;
      expect(mockContracts.organicComponentRegistry.connect.calledWith(mockSigner)).to.be.true;
      expect(mockContracts.organicComponentRegistry.setSpiralEngine.calledOnce).to.be.true;
    });

    it('должен пропустить setup если контракты отсутствуют', async () => {
      // GIVEN: Контракты не переданы
      const contracts = {};
      
      // WHEN
      await setupActions.setupOrganicComponentRegistry(contracts);
      
      // THEN: Setup не выполнен
      expect(mockEthersUtils.getSigner.called).to.be.false;
    });

    it('должен выбросить ошибку при провале транзакции', async () => {
      // GIVEN: setSpiralEngine падает
      mockContracts.organicComponentRegistry.setSpiralEngine.rejects(new Error('Transaction failed'));
      
      const contracts = {
        organicComponentRegistry: mockContracts.organicComponentRegistry,
        spiralEngine: mockContracts.spiralEngine
      };
      
      // WHEN/THEN
      try {
        await setupActions.setupOrganicComponentRegistry(contracts);
        expect.fail('Should have thrown error');
      } catch (error) {
        expect(error.message).to.include('Transaction failed');
      }
    });
  });

  // ================================================================
  // REAL TESTS: setupSystemConnections (Orchestration)
  // ================================================================

  describe('setupSystemConnections() - Orchestration', () => {
    it('должен загрузить контракты если не переданы', async () => {
      // GIVEN: Mock loadSystemContracts
      const loadStub = sinon.stub(setupActions, 'loadSystemContracts').resolves(mockContracts);
      const sbtStub = sinon.stub(setupActions, 'setupSBTEcosystem').resolves();
      const organicStub = sinon.stub(setupActions, 'setupOrganicComponentRegistry').resolves();
      
      // WHEN: Контракты не переданы
      await setupActions.setupSystemConnections();
      
      // THEN: loadSystemContracts вызван
      expect(loadStub.calledOnce).to.be.true;
      expect(sbtStub.calledWith(mockContracts)).to.be.true;
      expect(organicStub.calledWith(mockContracts)).to.be.true;
    });

    it('должен использовать переданные контракты', async () => {
      // GIVEN: Контракты уже есть
      const loadStub = sinon.stub(setupActions, 'loadSystemContracts');
      const sbtStub = sinon.stub(setupActions, 'setupSBTEcosystem').resolves();
      const organicStub = sinon.stub(setupActions, 'setupOrganicComponentRegistry').resolves();
      
      // WHEN: Контракты переданы
      await setupActions.setupSystemConnections(mockContracts);
      
      // THEN: loadSystemContracts НЕ вызван
      expect(loadStub.called).to.be.false;
      expect(sbtStub.calledWith(mockContracts)).to.be.true;
      expect(organicStub.calledWith(mockContracts)).to.be.true;
    });

    it('должен вызвать setup методы в правильном порядке', async () => {
      // GIVEN
      sinon.stub(setupActions, 'loadSystemContracts').resolves(mockContracts);
      const sbtStub = sinon.stub(setupActions, 'setupSBTEcosystem').resolves();
      const organicStub = sinon.stub(setupActions, 'setupOrganicComponentRegistry').resolves();
      
      // WHEN
      await setupActions.setupSystemConnections();
      
      // THEN: SBT setup перед Organic setup
      expect(sbtStub.calledBefore(organicStub)).to.be.true;
    });

    it('должен выбросить ошибку если setup падает', async () => {
      // GIVEN: setupSBTEcosystem падает
      sinon.stub(setupActions, 'loadSystemContracts').resolves(mockContracts);
      sinon.stub(setupActions, 'setupSBTEcosystem').rejects(new Error('SBT setup failed'));
      sinon.stub(setupActions, 'setupOrganicComponentRegistry').resolves();
      
      // WHEN/THEN
      try {
        await setupActions.setupSystemConnections();
        expect.fail('Should have thrown error');
      } catch (error) {
        expect(error.message).to.include('SBT setup failed');
      }
    });
  });
});

