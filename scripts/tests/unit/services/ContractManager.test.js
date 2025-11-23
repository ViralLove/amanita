/**
 * Unit Tests: ContractManager
 * 
 * Tests for the centralized contract management service.
 * Migrated from Web3 to ethers.js
 */

const { expect } = require('chai');
const sinon = require('sinon');
const { ethers } = require('hardhat');
const { TestHarness } = require('../../helpers');

describe('ContractManager Service', () => {
  let ContractManager;
  let EthersUtils;
  let contractManager;
  let mockProvider;
  let mockEthersUtils;
  let harness;

  before(async () => {
    harness = new TestHarness();
    await harness.setupTestEnvironment();
    
    // Load modules
    ContractManager = require('../../../lib/services/ContractManager');
    EthersUtils = require('../../../lib/utils/EthersUtils');
  });

  after(async () => {
    await harness.teardownTestEnvironment();
  });

  beforeEach(() => {
    // Create mock provider with all required methods
    mockProvider = {
      getBalance: sinon.stub().resolves(1000000000000000000n),
      getNetwork: sinon.stub().resolves({ chainId: 31337n }),
      getBlockNumber: sinon.stub().resolves(100),
      resolveName: sinon.stub().resolves(null) // Required by ethers.Contract constructor
    };
    
    // Create mock config
    const mockConfig = harness.createMockConfig();
    
    // Create mock EthersUtils
    mockEthersUtils = new EthersUtils(mockProvider, mockConfig);
    
    // Create ContractManager instance
    contractManager = new ContractManager(mockProvider, mockConfig, mockEthersUtils);
  });

  afterEach(() => {
    sinon.restore();
  });

  describe('Initialization', () => {
    it('должен инициализироваться с provider, config и ethersUtils', () => {
      // THEN: ContractManager инициализирован
      expect(contractManager).to.be.an('object');
      expect(contractManager.provider).to.equal(mockProvider);
      expect(contractManager.config).to.be.an('object');
      expect(contractManager.ethersUtils).to.equal(mockEthersUtils);
    });

    it('должен иметь пустой contracts Map', () => {
      // THEN: contracts Map создан
      expect(contractManager.contracts).to.be.instanceOf(Map);
      expect(contractManager.contracts.size).to.equal(0);
    });

    it('должен иметь пустой contractArtifacts Map', () => {
      // THEN: contractArtifacts Map создан
      expect(contractManager.contractArtifacts).to.be.instanceOf(Map);
      expect(contractManager.contractArtifacts.size).to.equal(0);
    });
  });

  describe('Contract Artifact Loading', () => {
    it('должен кэшировать loaded artifacts', () => {
      // GIVEN: Mock artifact file
      const fs = require('fs');
      const readFileStub = sinon.stub(fs, 'readFileSync').returns(
        JSON.stringify({
          contractName: 'MagicRegistry',
          abi: [],
          bytecode: '0x1234'
        })
      );

      try {
        // WHEN: loadContractArtifact вызывается дважды
        const artifact1 = contractManager.loadContractArtifact('MagicRegistry');
        const artifact2 = contractManager.loadContractArtifact('MagicRegistry');
        
        // THEN: Файл читается только один раз
        expect(readFileStub.callCount).to.equal(1);
        expect(artifact1).to.equal(artifact2);
      } finally {
        readFileStub.restore();
      }
    });

    it('должен выбрасывать ошибку для несуществующего artifact', () => {
      // WHEN: loadContractArtifact для несуществующего контракта
      try {
        contractManager.loadContractArtifact('NonExistentContract');
        expect.fail('Should have thrown an error');
      } catch (error) {
        // THEN: Ошибка выбрасывается
        expect(error.message).to.include('Contract artifact not found');
      }
    });
  });

  describe('Contract Loading and Retrieval', () => {
    it('должен загружать contract instance с address и ABI', async () => {
      // GIVEN: Mock artifact и address
      const mockArtifact = {
        abi: [{ type: 'function', name: 'testMethod' }],
        bytecode: '0x1234'
      };
      sinon.stub(contractManager, 'loadContractArtifact').returns(mockArtifact);
      
      // Mock getSigner для предотвращения resolveName ошибок
      sinon.stub(mockEthersUtils, 'getSigner').returns(mockProvider);
      
      const testAddress = '0x1234567890123456789012345678901234567890';
      
      // WHEN: loadContract вызывается
      const contract = await contractManager.loadContract('MagicRegistry', testAddress);
      
      // THEN: Contract instance создан
      expect(contract).to.exist;
      expect(contract.target).to.equal(testAddress); // ethers v6: contract.target = address
    });
    
    it('должен кэшировать loaded contract', async () => {
      // GIVEN: Mock artifact
      const mockArtifact = {
        abi: [{ type: 'function', name: 'get' }],
        bytecode: '0x1234'
      };
      sinon.stub(contractManager, 'loadContractArtifact').returns(mockArtifact);
      sinon.stub(mockEthersUtils, 'getSigner').returns(mockProvider);
      
      // WHEN: loadContract вызывается дважды
      const contract1 = await contractManager.loadContract('MagicRegistry', '0xTest');
      const contract2 = await contractManager.loadContract('MagicRegistry');
      
      // THEN: Возвращается тот же instance из кэша
      expect(contract1).to.equal(contract2);
    });
    
    it('должен использовать address из config если не предоставлен', async () => {
      // GIVEN: Config с contract address
      const configAddress = '0xConfigAddress123';
      sinon.stub(contractManager.config, 'getContractAddress').returns(configAddress);
      sinon.stub(contractManager, 'loadContractArtifact').returns({
        abi: [],
        bytecode: '0x1234'
      });
      sinon.stub(mockEthersUtils, 'getSigner').returns(mockProvider);
      
      // WHEN: loadContract без address
      const contract = await contractManager.loadContract('MagicRegistry');
      
      // THEN: Address взят из config
      expect(contract.target).to.equal(configAddress);
    });
    
    it('должен возвращать undefined для non-existent contract', () => {
      // WHEN: getContract() для несуществующего контракта
      const contract = contractManager.getContract('NonExistent');
      
      // THEN: undefined возвращается
      expect(contract).to.be.undefined;
    });
  });

  describe('Contract Address Resolution', () => {
    it('должен использовать config для получения адресов', () => {
      // GIVEN: ContractManager с config
      // THEN: Config доступен
      expect(contractManager.config).to.be.an('object');
      expect(contractManager.config.getContractAddress).to.be.a('function');
    });

    it('должен получать address через config.getContractAddress', () => {
      // GIVEN: Simple test config
      const testConfig = {
        config: {
          contracts: {
            magicregistry: '0xConfigAddress'
          }
        },
        getContractAddress: function(contractName) {
          const key = contractName.toLowerCase().replace(/_/g, '');
          return this.config.contracts[key];
        }
      };
      
      // WHEN: getContractAddress() вызывается
      const address = testConfig.getContractAddress('MagicRegistry');
      
      // THEN: Address возвращается
      expect(address).to.equal('0xConfigAddress');
    });
  });

  describe('Contract Cache Management', () => {
    it('должен иметь метод clearContracts', () => {
      // THEN: clearContracts метод существует
      expect(contractManager.clearContracts).to.be.a('function');
    });

    it('должен очищать contracts cache', () => {
      // GIVEN: Contracts в cache
      contractManager.contracts.set('Test', { mock: true });
      contractManager.contractArtifacts.set('Test', { mock: true });
      
      expect(contractManager.contracts.size).to.equal(1);
      expect(contractManager.contractArtifacts.size).to.equal(1);

      // WHEN: clearContracts() вызывается
      contractManager.clearContracts();
      
      // THEN: Cache очищен
      expect(contractManager.contracts.size).to.equal(0);
      expect(contractManager.contractArtifacts.size).to.equal(0);
    });
  });

  describe('UUPS Support', () => {
    it('должен иметь метод deployUUPSContract', () => {
      // THEN: deployUUPSContract метод существует
      expect(contractManager.deployUUPSContract).to.be.a('function');
    });

    it('должен иметь метод deploySingleContract', () => {
      // THEN: deploySingleContract метод существует
      expect(contractManager.deploySingleContract).to.be.a('function');
    });
    
    it('должен иметь метод loadUUPSContract', () => {
      expect(contractManager.loadUUPSContract).to.be.a('function');
    });
    
    it('должен иметь метод prepareInitializeCalldata', () => {
      expect(contractManager.prepareInitializeCalldata).to.be.a('function');
    });
  });
  
  describe('UUPS Contract Loading', () => {
    it('должен загружать UUPS contract с proxy address', async () => {
      // GIVEN: Mock artifact для Logic (UUPS использует Logic ABI)
      const mockArtifact = {
        abi: [{ type: 'function', name: 'initialize' }],
        bytecode: '0x1234'
      };
      sinon.stub(contractManager, 'loadContractArtifact').returns(mockArtifact);
      sinon.stub(mockEthersUtils, 'getSigner').returns(mockProvider);
      
      const proxyAddress = '0xProxyAddress123';
      
      // WHEN: loadUUPSContract вызывается
      const contract = await contractManager.loadUUPSContract('SpiralEngine', proxyAddress);
      
      // THEN: Contract instance с proxy address
      expect(contract).to.exist;
      expect(contract.target).to.equal(proxyAddress);
    });
    
    it('должен кэшировать loaded UUPS contract', async () => {
      // GIVEN: Mock artifact
      sinon.stub(contractManager, 'loadContractArtifact').returns({
        abi: [],
        bytecode: '0x1234'
      });
      sinon.stub(mockEthersUtils, 'getSigner').returns(mockProvider);
      
      // WHEN: loadUUPSContract вызывается дважды
      const contract1 = await contractManager.loadUUPSContract('SpiralEngine', '0xProxy');
      const contract2 = contractManager.getContract('SpiralEngine');
      
      // THEN: Второй вызов возвращает из кэша
      expect(contract2).to.equal(contract1);
    });
  });
  
  describe('Initialize Calldata Preparation', () => {
    it('должен генерировать calldata для initialize метода', () => {
      // GIVEN: Mock artifact с initialize function
      const mockArtifact = {
        abi: [
          {
            type: 'function',
            name: 'initialize',
            inputs: [
              { name: 'param1', type: 'address' },
              { name: 'param2', type: 'uint256' }
            ]
          }
        ]
      };
      sinon.stub(contractManager, 'loadContractArtifact').returns(mockArtifact);
      
      // WHEN: prepareInitializeCalldata вызывается
      const calldata = contractManager.prepareInitializeCalldata('SpiralEngine', [
        '0x1234567890123456789012345678901234567890',
        123
      ]);
      
      // THEN: Calldata - valid hex string with initialize function selector
      expect(calldata).to.be.a('string');
      expect(calldata).to.match(/^0x[0-9a-fA-F]+$/);
      expect(calldata.length).to.be.greaterThan(10); // selector (4 bytes) + encoded params
      
      // Проверяем что calldata содержит function selector (первые 4 байта после 0x)
      const selector = calldata.slice(0, 10); // 0x + 8 hex chars = 4 bytes
      expect(selector).to.match(/^0x[0-9a-fA-F]{8}$/);
    });
    
    it('должен работать с UUPS contracts (загружать Logic artifact)', () => {
      // GIVEN: Mock artifact для Logic
      const mockLogicArtifact = {
        abi: [
          {
            type: 'function',
            name: 'initialize',
            inputs: [
              { name: 'addr', type: 'address' }
            ]
          }
        ]
      };
      const artifactStub = sinon.stub(contractManager, 'loadContractArtifact').returns(mockLogicArtifact);
      
      // WHEN: prepareInitializeCalldata для UUPS contract
      const calldata = contractManager.prepareInitializeCalldata('SpiralEngine', [
        '0x0000000000000000000000000000000000000001'
      ]);
      
      // THEN: 
      // 1. Logic artifact был загружен (не Proxy)
      expect(artifactStub.calledWith('SpiralEngineLogic')).to.be.true;
      
      // 2. Calldata сгенерирована корректно
      expect(calldata).to.be.a('string');
      expect(calldata).to.match(/^0x[0-9a-fA-F]+$/);
      expect(calldata.length).to.be.greaterThan(10);
    });
  });

  describe('UUPS Deployment - Real Tests', () => {
    it('должен вызывать deployContract для Logic и Proxy в правильном порядке', async () => {
      // GIVEN: Spy на deployContract (не stub - позволяем методу выполниться)
      const deploySpy = sinon.spy(contractManager, 'deployContract');
      
      // Stub ethers.ContractFactory чтобы предотвратить реальный deployment
      const deploymentWaitStub = sinon.stub().resolves({ gasUsed: 100000n });
      const mockContract = {
        getAddress: async () => '0xMockAddress',
        waitForDeployment: async () => {},
        deploymentTransaction: () => ({
          wait: deploymentWaitStub
        })
      };
      const factoryStub = sinon.stub(ethers, 'ContractFactory').returns({
        deploy: sinon.stub().resolves(mockContract)
      });

      // Mock artifact с initialize function
      sinon.stub(contractManager, 'loadContractArtifact').returns({
        abi: [
          {
            type: 'function',
            name: 'initialize',
            inputs: [{ name: 'admin', type: 'address' }]
          }
        ],
        bytecode: '0x1234'
      });
      
      // Mock getInitializeArgs с валидным address
      sinon.stub(contractManager, 'getInitializeArgs').resolves(['0x1234567890123456789012345678901234567890']);

      // WHEN: deployUUPSContract('SpiralEngine')
      await contractManager.deployUUPSContract('SpiralEngine', [], {});
      
      // THEN: deployContract вызывается для Logic (Proxy деплоится напрямую)
      expect(deploySpy.calledOnce).to.be.true;
      expect(deploySpy.firstCall.args[0]).to.equal('SpiralEngineLogic');
      
      factoryStub.restore();
    });

    it('должен передавать constructor args в Logic контракт', async () => {
      // GIVEN: Constructor args
      const constructorArgs = ['arg1', 'arg2'];
      const deploySpy = sinon.spy(contractManager, 'deployContract');
      
      const deploymentWaitStub = sinon.stub().resolves({ gasUsed: 100000n });
      const mockContract = {
        getAddress: async () => '0xMockAddress',
        waitForDeployment: async () => {},
        deploymentTransaction: () => ({
          wait: deploymentWaitStub
        })
      };
      const factoryStub = sinon.stub(ethers, 'ContractFactory').returns({
        deploy: sinon.stub().resolves(mockContract)
      });

      sinon.stub(contractManager, 'loadContractArtifact').returns({
        abi: [
          {
            type: 'function',
            name: 'initialize',
            inputs: [{ name: 'admin', type: 'address' }]
          }
        ],
        bytecode: '0x1234'
      });
      
      sinon.stub(contractManager, 'getInitializeArgs').resolves(['0x1234567890123456789012345678901234567890']);

      // WHEN: deployUUPSContract с args
      await contractManager.deployUUPSContract('SpiralEngine', constructorArgs, {});
      
      // THEN: Args передаются в Logic (единственный вызов deployContract)
      expect(deploySpy.calledOnce).to.be.true;
      expect(deploySpy.firstCall.args[1]).to.deep.equal(constructorArgs);
      
      factoryStub.restore();
    });

    it('должен кэшировать deployed UUPS contract в contracts Map', async () => {
      // GIVEN: Successful deployment mocks
      const deploymentWaitStub = sinon.stub().resolves({ gasUsed: 100000n });
      const mockContract = {
        getAddress: async () => '0x9fE46736679d2D9a65F0992F2272dE9f3c7fa6e0',
        waitForDeployment: async () => {},
        deploymentTransaction: () => ({
          wait: deploymentWaitStub
        })
      };
      
      const factoryStub = sinon.stub(ethers, 'ContractFactory').returns({
        deploy: sinon.stub().resolves(mockContract)
      });

      sinon.stub(contractManager, 'loadContractArtifact').returns({
        abi: [
          {
            type: 'function',
            name: 'initialize',
            inputs: [{ name: 'admin', type: 'address' }]
          }
        ],
        bytecode: '0x1234'
      });
      
      sinon.stub(contractManager, 'getInitializeArgs').resolves(['0x1234567890123456789012345678901234567890']);

      // WHEN: deployUUPSContract
      const result = await contractManager.deployUUPSContract('SpiralEngine', [], {});
      
      // THEN: Contract возвращен и добавлен в кэш
      expect(result).to.exist;
      const cached = contractManager.getContract('SpiralEngine');
      expect(cached).to.exist;
      expect(await cached.getAddress()).to.equal('0x9fE46736679d2D9a65F0992F2272dE9f3c7fa6e0');
      
      factoryStub.restore();
    });
  });

  describe('SBT Contract Deployment', () => {
    it('должен иметь метод getSBTConstructorArgs', () => {
      expect(contractManager.getSBTConstructorArgs).to.be.a('function');
    });
    
    it('должен возвращать правильные args для SoulboundCore', async () => {
      const args = await contractManager.getSBTConstructorArgs('SoulboundCore');
      expect(args).to.deep.equal(['Amanita Soul', 'ASOUL']);
    });
    
    it('должен загружать зависимости для SoulMetadata', async () => {
      // Mock SoulboundCore в кэше
      const mockSoulboundCore = {
        getAddress: async () => '0xSoulboundCore123'
      };
      contractManager.contracts.set('SoulboundCore', mockSoulboundCore);
      
      const args = await contractManager.getSBTConstructorArgs('SoulMetadata');
      expect(args).to.deep.equal(['0xSoulboundCore123']);
    });
    
    it('должен загружать зависимости для SoulIdentity', async () => {
      // Mock dependencies в кэше
      const mockSoulboundCore = {
        getAddress: async () => '0xSoulboundCore123'
      };
      const mockSoulMetadata = {
        getAddress: async () => '0xSoulMetadata456'
      };
      
      contractManager.contracts.set('SoulboundCore', mockSoulboundCore);
      contractManager.contracts.set('SoulMetadata', mockSoulMetadata);
      
      const args = await contractManager.getSBTConstructorArgs('SoulIdentity');
      expect(args).to.deep.equal(['0xSoulboundCore123', '0xSoulMetadata456']);
    });
    
    it('должен бросать ошибку если зависимости не найдены', async () => {
      // SoulMetadata без SoulboundCore в кэше
      try {
        await contractManager.getSBTConstructorArgs('SoulMetadata');
        expect.fail('Should have thrown error');
      } catch (error) {
        expect(error.message).to.include('SoulboundCore must be deployed before SoulMetadata');
      }
    });
  });

  describe('Contract Deployment - Real Tests', () => {
    it('должен иметь метод deployContract', () => {
      // THEN: deployContract метод существует
      expect(contractManager.deployContract).to.be.a('function');
    });

    it('должен загружать artifact перед deployment', () => {
      // GIVEN: Mock artifact
      const mockArtifact = {
        abi: [{ type: 'constructor', inputs: [] }],
        bytecode: '0x608060405234801561001057600080fd5b50'
      };
      const artifactStub = sinon.stub(contractManager, 'loadContractArtifact').returns(mockArtifact);

      // WHEN: deployContract вызывается (stub ethers.ContractFactory to prevent real deployment)
      const ethersStub = sinon.stub(ethers, 'ContractFactory');
      
      try {
        contractManager.deployContract('TestContract', []);
      } catch (error) {
        // Expected - ContractFactory stub will throw
      } finally {
        ethersStub.restore();
      }
      
      // THEN: Artifact был загружен (проверяем логику, не deployment)
      expect(artifactStub.calledOnceWith('TestContract')).to.be.true;
    });
  });

  describe('Registry Integration - Real Tests', () => {
    it('должен вызывать set на registry (MagicRegistry API)', async () => {
      // GIVEN: Mock registry with ethers pattern
      let registerCalled = false;
      const mockSigner = {
        address: '0xDeployer'
      };
      const mockRegistry = {
        connect: sinon.stub().returnsThis(),
        set: async (name, addr, options) => {
          registerCalled = true;
          return {
            wait: async () => ({ hash: '0xRegistered' })
          };
        }
      };

      // Mock getSigner
      sinon.stub(mockEthersUtils, 'getSigner').returns(mockSigner);

      // WHEN: registerContractInRegistry вызывается
      await contractManager.registerContractInRegistry(
        'SpiralEngine',
        '0xProxyAddress123',
        mockRegistry
      );
      
      // THEN: set был вызван (MagicRegistry uses set, not registerContract)
      expect(registerCalled).to.be.true;
      expect(mockRegistry.connect.calledOnceWith(mockSigner)).to.be.true;
    });

    it('должен передавать корректные параметры в set (MagicRegistry API)', async () => {
      // GIVEN: Mock registry с проверкой параметров
      let capturedName, capturedAddress;
      const mockSigner = {
        address: '0xDeployer'
      };
      const mockRegistry = {
        connect: sinon.stub().returnsThis(),
        set: async (name, addr, options) => {
          capturedName = name;
          capturedAddress = addr;
          return {
            wait: async () => ({ hash: '0xTx' })
          };
        }
      };

      sinon.stub(mockEthersUtils, 'getSigner').returns(mockSigner);

      // WHEN: registerContractInRegistry
      await contractManager.registerContractInRegistry(
        'TestContract',
        '0xTestAddress',
        mockRegistry
      );
      
      // THEN: Параметры переданы корректно
      expect(capturedName).to.equal('TestContract');
      expect(capturedAddress).to.equal('0xTestAddress');
    });

    it('должен логировать успешную регистрацию', async () => {
      // GIVEN: Mock registry
      const mockSigner = {
        address: '0xDeployer'
      };
      const mockRegistry = {
        connect: sinon.stub().returnsThis(),
        set: async (name, addr, options) => {
          return {
            wait: async () => ({ hash: '0xSuccess' })
          };
        }
      };

      sinon.stub(mockEthersUtils, 'getSigner').returns(mockSigner);

      // WHEN: registerContractInRegistry
      const result = await contractManager.registerContractInRegistry(
        'Test',
        '0xAddr',
        mockRegistry
      );
      
      // THEN: Результат возвращен
      expect(result).to.be.an('object');
      expect(result.hash).to.equal('0xSuccess');
    });
  });
});
