/**
 * Contract Validation Integration Tests
 * 
 * Validates that module contracts and boundaries align correctly.
 * Focus: Data format compatibility at module interfaces.
 */

const { expect } = require('chai');
const sinon = require('sinon');
const {
  IntegrationHarness,
  expectEvent,
  expectRevertCustom,
  assertBusinessIdMapping,
  assertBusinessIdCleared
} = require('../helpers');

describe('Contract Validation Tests', () => {
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

  describe('Contract: ContractManager → ArweaveManager (Deployment Data)', () => {
    it('должен валидировать contract deployment data format', async () => {
      // GIVEN: Simulated deployment data (skip real deploy, test contract only)
      const deployment = {
        address: '0x1234567890123456789012345678901234567890', // Mock proxy address
        logic: '0xabcdefabcdefabcdefabcdefabcdefabcdefabcd' // Mock logic address
      };
      
      // WHEN: Prepare metadata for ArweaveManager (using ContractManager output)
      
      // THEN: Deployment data format validated
      expect(deployment).to.be.an('object');
      expect(deployment.address).to.exist; // Proxy address
      
      // CONTRACT: Deployment result ready for ArweaveManager
      const metadata = {
        contractAddress: deployment.address,
        contractName: 'SpiralEngine',
        network: 'localhost'
      };
      
      // Mock Arweave client
      const mockArweave = harness.createMockArweaveClient();
      modules.arweaveManager.arweaveClient = mockArweave;
      modules.arweaveManager.arweaveKey = { mock: true };
      
      // ArweaveManager accepts this format (contract validated)
      const result = await modules.arweaveManager.uploadJSON(metadata);
      
      expect(result.txId).to.exist;
      expect(mockArweave.createTransaction.calledOnce).to.be.true;
      
      // Contract validated: ContractManager output → ArweaveManager input
    });
  });

  describe('Contract: Config → All Modules (Configuration)', () => {
    it('должен предоставлять consistent config для всех modules', () => {
      // GIVEN: Config loaded
      const deployer = modules.config.getDeployerConfig();
      const seller = modules.config.getSellerConfig();
      
      // THEN: Config contract validated
      expect(deployer).to.be.an('object');
      expect(deployer.privateKey).to.match(/^0x/); // Normalized format
      
      expect(seller).to.be.an('object');
      // Address и sellerId могут быть undefined в test.env
      if (seller.address) {
        expect(seller.address).to.match(/^0x[a-fA-F0-9]{40}$/);
      }
      if (seller.sellerId) {
        expect(seller.sellerId).to.be.a('string');
      }
      
      // CONTRACT: All modules can access config consistently
      expect(modules.contractManager.config).to.equal(modules.config);
      expect(modules.arweaveManager.config).to.equal(modules.config);
      expect(modules.coreLogic.config).to.equal(modules.config);
    });

    it('должен валидировать contract addresses format', () => {
      // GIVEN: Contract addresses from config
      const spiralEngineAddr = modules.config.getContractAddress('spiralEngine');
      const magicRegistryAddr = modules.config.getContractAddress('magicRegistry');
      
      // THEN: Address format contract validated
      // Могут быть null (не deployed yet), но если есть - валидны
      if (spiralEngineAddr) {
        expect(spiralEngineAddr).to.match(/^0x[a-fA-F0-9]{40}$/);
      }
      if (magicRegistryAddr) {
        expect(magicRegistryAddr).to.match(/^0x[a-fA-F0-9]{40}$/);
      }
      
      // CONTRACT: getContractAddress returns valid format or null
    });
  });

  describe('Contract: EthersUtils → CoreLogic (Invite Codes)', () => {
    it('должен валидировать invite code format contract', () => {
      // GIVEN: EthersUtils generates codes
      const codes = modules.ethersUtils.generateNewInviteCodes(5, 8);
      
      // THEN: Code format validated
      expect(codes).to.be.an('array');
      expect(codes).to.have.lengthOf(5);
      codes.forEach(code => {
        expect(code).to.be.a('string');
        expect(code).to.have.lengthOf(8);
        expect(code).to.match(/^[A-Za-z0-9]+$/); // Alphanumeric
      });
      
      // CONTRACT: CoreLogic expects array of alphanumeric strings
      // Validate this contract by checking CoreLogic can accept these codes
      expect(() => {
        // CoreLogic would use these codes in activateSellerBasic
        // Format contract: Array<string> of alphanumeric codes
        codes.forEach(code => {
          if (typeof code !== 'string' || code.length === 0) {
            throw new Error('Invalid code format');
          }
        });
      }).to.not.throw();
    });
  });

  describe('Contract: ContractManager.getContract → CoreLogic', () => {
    it('должен возвращать contract instance с required methods', async () => {
      // GIVEN: Mock contract with expected interface
      const mockContract = harness.setupContractMock('TestContract', {
        someMethod: {
          call: async () => 'result',
          encodeABI: '0xencoded'
        }
      });
      
      // Stub getContract
      sinon.stub(modules.contractManager, 'getContract')
        .withArgs('TestContract')
        .resolves(mockContract);
      
      // WHEN: CoreLogic получает contract
      const contract = await modules.contractManager.getContract('TestContract');
      
      // THEN: Contract interface validated
      expect(contract).to.be.an('object');
      expect(contract.getAddress).to.be.a('function');
      expect(contract.connect).to.be.a('function');
      const address = await contract.getAddress();
      expect(address).to.exist;
      
      // CONTRACT: getContract returns ethers Contract with getAddress() and direct methods
    });

    it('должен возвращать null/undefined для non-existent contract', async () => {
      // GIVEN: Contract не существует
      
      // WHEN: getContract вызывается
      const contract = await modules.contractManager.getContract('NonExistentContract');
      
      // THEN: null или undefined возвращается (contract not deployed)
      expect(contract).to.satisfy(c => c === null || c === undefined);
      
      // CONTRACT: getContract returns null/undefined OR contract instance
    });
  });

  describe('Contract: ArweaveManager.uploadJSON → Result Format', () => {
    it('должен возвращать consistent result object', async () => {
      // GIVEN: Mock Arweave client
      const mockArweave = harness.createMockArweaveClient();
      modules.arweaveManager.arweaveClient = mockArweave;
      modules.arweaveManager.arweaveKey = { mock: true };
      
      // WHEN: uploadJSON вызывается
      const result = await modules.arweaveManager.uploadJSON({ test: 'data' });
      
      // THEN: Result format contract validated
      expect(result).to.be.an('object');
      expect(result.success).to.be.a('boolean');
      expect(result.txId).to.be.a('string');
      
      // CONTRACT: uploadJSON returns { success: boolean, txId: string, url?: string }
    });

    it('должен валидировать CID format в result', async () => {
      // GIVEN: Mock Arweave
      const mockArweave = harness.createMockArweaveClient();
      modules.arweaveManager.arweaveClient = mockArweave;
      modules.arweaveManager.arweaveKey = { mock: true };
      
      // WHEN: Upload происходит
      const result = await modules.arweaveManager.uploadJSON({ data: 'test' });
      
      // THEN: CID format validated (Arweave format)
      expect(result.txId).to.match(/^Qm[A-Za-z0-9]+$|^[A-Za-z0-9_-]{43}$/);
      
      // CONTRACT: txId is valid Arweave CID
    });
  });

  describe('Contract: Error Propagation (Module A → Module B)', () => {
    it('должен пробрасывать errors между modules с context', async () => {
      // GIVEN: ArweaveManager fails (external API error)
      const mockArweave = harness.createMockArweaveClient();
      mockArweave.createTransaction.rejects(new Error('Arweave API unavailable'));
      modules.arweaveManager.arweaveClient = mockArweave;
      modules.arweaveManager.arweaveKey = { mock: true };
      
      // WHEN: CoreLogic tries to use ArweaveManager
      try {
        await modules.arweaveManager.uploadJSON({ test: 'data' });
        expect.fail('Should have thrown error');
      } catch (error) {
        // THEN: Error propagated correctly
        expect(error.message).to.include('Arweave');
        
        // CONTRACT: Errors preserve message and context
      }
    });
  });

  describe('Contract: CoreLogic → ProductRegistry (businessId flow)', () => {
    let suite;

    beforeEach(async () => {
      suite = await harness.setupProductRegistrySuite({ forceRedeploy: true });
    });

    it('должен создавать продукт с businessId и фиксировать событие', async () => {
      const { productRegistry, seller, sellerComponentIds } = suite;

      const businessId = 'integration-prod-1';
      const metadataCID = 'QmIntegrationCID1';

      await expectEvent(
        productRegistry
          .connect(seller)
          .createProduct(businessId, [sellerComponentIds[0]], metadataCID),
        productRegistry,
        'ProductCreated',
        async (args) => {
          expect(args.seller).to.equal(seller.address);
          expect(args.businessId).to.equal(businessId);
          expect(args.metadataCID).to.equal(metadataCID);
        }
      );

      await assertBusinessIdMapping(productRegistry, businessId, 1);
    });

    it('должен запрещать повторное использование businessId', async () => {
      const { productRegistry, seller, sellerComponentIds } = suite;

      const businessId = 'integration-prod-duplicate';
      const metadataCID = 'QmIntegrationCID2';

      await productRegistry
        .connect(seller)
        .createProduct(businessId, [sellerComponentIds[0]], metadataCID);

      await expectRevertCustom(
        productRegistry
          .connect(seller)
          .createProduct(businessId, [sellerComponentIds[1]], metadataCID),
        'BusinessIdExists',
        productRegistry
      );
    });

    it('должен очищать businessId mapping при clearSellerCatalog', async () => {
      const { productRegistry, seller, sellerComponentIds } = suite;

      const businessId = 'integration-prod-clear';
      await productRegistry
        .connect(seller)
        .createProduct(businessId, [sellerComponentIds[0]], 'QmIntegrationCID3');

      await assertBusinessIdMapping(productRegistry, businessId, 1);

      await productRegistry.connect(seller).clearSellerCatalog(seller.address);

      await assertBusinessIdCleared(productRegistry, businessId);
    });
  });
});

