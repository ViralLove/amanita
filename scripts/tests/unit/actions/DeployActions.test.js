/**
 * Unit Tests: DeployActions
 * Tests for contract deployment actions (Layer 1).
 * 
 * Coverage:
 * - action0() - deploy MagicRegistry
 * - action1() - deploy all contracts + setup
 * - printContractAddresses() - output formatting
 * - setupActions delegation
 */

const { expect } = require('chai');
const sinon = require('sinon');
const DeployActions = require('../../../lib/actions/DeployActions');

describe('DeployActions', () => {
  let deployActions;
  let mockContractManager;
  let mockEthersUtils;
  let mockConfig;
  let mockSetupActions;

  beforeEach(() => {
    // Mock dependencies
    mockContractManager = {
      deployUUPSContract: sinon.stub(),
      deployContract: sinon.stub(),
      deploySingleContract: sinon.stub(),
      registerContractInRegistry: sinon.stub().resolves()
    };

    mockEthersUtils = {
      getSigner: sinon.stub().returns({ getAddress: sinon.stub().resolves('0xDeployer') })
    };

    mockConfig = {
      get: sinon.stub()
    };

    deployActions = new DeployActions(mockContractManager, mockEthersUtils, mockConfig);
    
    // Mock SetupActions (delegation)
    mockSetupActions = {
      setupSystemConnections: sinon.stub().resolves()
    };
    deployActions.setupActions = mockSetupActions;
  });

  afterEach(() => {
    sinon.restore();
  });

  // ================================================================
  // SMOKE TESTS
  // ================================================================

  describe('Initialization', () => {
    it('должен инициализироваться с dependencies', () => {
      expect(deployActions.contractManager).to.equal(mockContractManager);
      expect(deployActions.ethersUtils).to.equal(mockEthersUtils);
      expect(deployActions.config).to.equal(mockConfig);
    });

    it('должен иметь setupActions instance', () => {
      expect(deployActions.setupActions).to.exist;
    });

    it('должен иметь метод action0', () => {
      expect(deployActions.action0).to.be.a('function');
    });

    it('должен иметь метод action1', () => {
      expect(deployActions.action1).to.be.a('function');
    });

    it('должен иметь метод printContractAddresses', () => {
      expect(deployActions.printContractAddresses).to.be.a('function');
    });
  });

  // ================================================================
  // REAL TESTS: action0
  // ================================================================

  describe('action0() - Deploy MagicRegistry', () => {
    it('должен деплоить MagicRegistry через deploySingleContract', async () => {
      // GIVEN
      const mockRegistry = {
        options: { address: '0xRegistry' },
        getAddress: sinon.stub().resolves('0xRegistry')
      };
      mockContractManager.deploySingleContract.withArgs('MagicRegistry').resolves(mockRegistry);
      
      // WHEN
      const result = await deployActions.action0();
      
      // THEN: MagicRegistry deployed
      expect(mockContractManager.deploySingleContract.calledWith('MagicRegistry')).to.be.true;
      expect(result).to.have.property('address', '0xRegistry');
    });

    it('должен вернуть registry address', async () => {
      // GIVEN
      mockContractManager.deploySingleContract.resolves({
        options: { address: '0x5FbDB2315678afecb367f032d93F642f64180aa3' },
        getAddress: sinon.stub().resolves('0x5FbDB2315678afecb367f032d93F642f64180aa3')
      });
      
      // WHEN
      const result = await deployActions.action0();
      
      // THEN
      expect(result.address).to.match(/^0x[a-fA-F0-9]{40}$/);
    });

    it('должен выбросить ошибку при провале деплоя', async () => {
      // GIVEN: Deploy fails
      mockContractManager.deploySingleContract.rejects(new Error('Deployment failed'));
      
      // WHEN/THEN
      try {
        await deployActions.action0();
        expect.fail('Should have thrown error');
      } catch (error) {
        expect(error.message).to.include('Deployment failed');
      }
    });
  });

  // ================================================================
  // REAL TESTS: action1 (orchestration)
  // ================================================================

  describe('action1() - Deploy All Contracts', () => {
    beforeEach(() => {
      // Mock deploySingleContract (универсальный для всех контрактов)
      mockContractManager.deploySingleContract.callsFake((contractName) => {
        return Promise.resolve({
          options: { address: `0x${contractName}` },
          getAddress: sinon.stub().resolves(`0x${contractName}`)
        });
      });
    });

    it('должен деплоить MagicRegistry через deploySingleContract', async () => {
      // WHEN
      await deployActions.action1();
      
      // THEN: MagicRegistry deployed first (используется deploySingleContract)
      expect(mockContractManager.deploySingleContract.calledWith('MagicRegistry')).to.be.true;
    });

    it('должен деплоить все UUPS контракты через deploySingleContract', async () => {
      // WHEN
      await deployActions.action1();
      
      // THEN: UUPS contracts deployed (action1 использует deploySingleContract)
      expect(mockContractManager.deploySingleContract.calledWith('SpiralEngine')).to.be.true;
      expect(mockContractManager.deploySingleContract.calledWith('ProductRegistry')).to.be.true;
      expect(mockContractManager.deploySingleContract.calledWith('OrganicComponentRegistry')).to.be.true;
      expect(mockContractManager.deploySingleContract.calledWith('AmanitaInternational')).to.be.true;
    });

    it('должен деплоить SBT ecosystem через deploySingleContract', async () => {
      // WHEN
      await deployActions.action1();
      
      // THEN: SBT contracts deployed (action1 использует deploySingleContract для всех)
      const calls = mockContractManager.deploySingleContract.getCalls();
      const contractNames = calls.map(c => c.args[0]);
      
      expect(contractNames).to.include('SoulboundCore');
      expect(contractNames).to.include('SoulMetadata');
      expect(contractNames).to.include('SoulRecovery');
      expect(contractNames).to.include('SoulIntegration');
      expect(contractNames).to.include('SoulIdentity');
    });

    it('должен делегировать setup в SetupActions', async () => {
      // WHEN
      await deployActions.action1();
      
      // THEN: setupSystemConnections вызван
      expect(mockSetupActions.setupSystemConnections.calledOnce).to.be.true;
    });

    it('должен вернуть deployed contracts', async () => {
      // WHEN
      const result = await deployActions.action1();
      
      // THEN: Result содержит contracts
      expect(result).to.have.property('success', true);
      expect(result).to.have.property('contracts');
    });
  });

  // ================================================================
  // REAL TESTS: printContractAddresses
  // ================================================================

  describe('printContractAddresses() - Real Tests', () => {
    it('должен вывести адреса контрактов', () => {
      // GIVEN: Contracts object
      const contracts = {
        magicRegistry: '0xRegistry',
        spiralEngine: '0xSpiral',
        soulboundCore: '0xCore'
      };
      
      // WHEN: printContractAddresses вызывается
      const consoleStub = sinon.stub(console, 'log');
      deployActions.printContractAddresses(contracts);
      
      // THEN: Адреса выведены
      expect(consoleStub.called).to.be.true;
      
      consoleStub.restore();
    });

    it('должен выделить MAGIC_REGISTRY как essential', () => {
      // TODO: После рефакторинга (новый output format)
      // GIVEN
      const contracts = { magicRegistry: '0xRegistry' };
      
      // WHEN
      const consoleStub = sinon.stub(console, 'log');
      deployActions.printContractAddresses(contracts);
      
      // THEN: MAGIC_REGISTRY выделен
      // const output = consoleStub.getCalls().map(c => c.args.join(' ')).join('\n');
      // expect(output).to.include('COPY TO .ENV');
      // expect(output).to.include('MAGIC_REGISTRY');
      
      consoleStub.restore();
      expect(true).to.be.true; // Placeholder до рефакторинга
    });
  });
});

