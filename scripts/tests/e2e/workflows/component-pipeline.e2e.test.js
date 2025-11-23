/**
 * E2E: Component Pipeline (777 → 555)
 */

const { expect } = require('chai');
const E2EHarness = require('../../helpers/E2EHarness');
const { ethers } = require('hardhat');

// Import real actions (not mocked - this is E2E!)
const ComponentActions = require('../../../lib/actions/ComponentActions');
const InviteActions = require('../../../lib/actions/InviteActions');
const AccessControlActions = require('../../../lib/actions/AccessControlActions');
const ContractManager = require('../../../lib/services/ContractManager');
const EthersUtils = require('../../../lib/utils/EthersUtils');
const { MockArweaveManager } = require('../../helpers');

describe('E2E Workflow: Component Pipeline (777 → 555)', function() {
  this.timeout(300000); // 5 минут для полного pipeline

  let harness;
  let deployedContracts;
  let componentActions;
  let inviteActions;

  before(async function() {
    this.timeout(120000); // 2 min for setup

    harness = new E2EHarness();
    await harness.startHardhatNode();
    harness.loadTestEnv();
    await harness.resetNetwork();

    // Deploy all contracts
    console.log('\n📦 Prerequisite: Deploying contracts...');
    deployedContracts = await deployAllContractsForPipeline();
    registerContractsInMagicRegistry(harness, deployedContracts);

    // Initialize actions
    const provider = ethers.provider;
    const [deployer, seller] = await ethers.getSigners();

    const config = {
      get: (key) => {
        if (key === 'contracts.magicRegistry') return deployedContracts.magicRegistry;
        if (key === 'deployer.privateKey') return process.env.DEPLOYER_PRIVATE_KEY;
        if (key === 'seller.address') return seller.address;
        if (key === 'seller.businessId') return 'test-seller';
        if (key === 'network.name') return 'localhost';
        return null;
      }
    };

    const contractManager = new ContractManager(provider, config);
    const ethersUtils = new EthersUtils(provider, config);
    const accessControlActions = new AccessControlActions(contractManager, ethersUtils, config);
    inviteActions = new InviteActions(contractManager, ethersUtils, config, accessControlActions);
    
    const mockArweaveManager = new MockArweaveManager();
    componentActions = new ComponentActions(
      contractManager,
      mockArweaveManager,
      ethersUtils,
      config,
      inviteActions
    );

    console.log('✅ Actions initialized');
  });

  after(async () => {
    await harness.stopHardhatNode();
    harness.restoreEnv();
  });

  beforeEach(async () => {
    await harness.resetNetwork();
  });

  describe('Sequential Workflow', () => {
    it('должен выполнить полный component pipeline: 777 → 555 → Validate', async function() {
      this.timeout(300000); // 5 минут для полного pipeline
      
      const { ethers } = require('hardhat');
      const [deployer, seller] = await ethers.getSigners();
      
      // STEP 1: Deploy SpiralEngine (prerequisite for Action 777)
      const Logic = await ethers.getContractFactory('SpiralEngineLogic');
      const logic = await Logic.deploy();
      await logic.waitForDeployment();

      // Encode initialize(admin) call
      const spiralInterface = logic.interface;
      const initializeData = spiralInterface.encodeFunctionData('initialize', [deployer.address]);
      
      const Proxy = await ethers.getContractFactory('SpiralEngineProxy');
      const proxy = await Proxy.deploy(await logic.getAddress(), initializeData);
      await proxy.waitForDeployment();
      
      const spiralEngineAddress = await proxy.getAddress();
      console.log(`✅ SpiralEngine deployed: ${spiralEngineAddress}`);

      // STEP 2: Generate deployer invite (Action 777)
      const SpiralEngine = await ethers.getContractAt('SpiralEngineLogic', spiralEngineAddress);
      const spiralWithDeployer = SpiralEngine.connect(deployer);
      const deployerInvite = 'AMANITA-PIPELINE-TEST';
      const mintTx = await spiralWithDeployer.mintInvite(deployerInvite, 0); // Expiry = 0 (бессрочный)
      await mintTx.wait();
      console.log(`✅ Deployer invite created: ${deployerInvite}`);

      // STEP 3: Upload components (Action 555)
      process.env.DEPLOYER_INVITE = deployerInvite;
      process.env.SELLER_ADDRESS = seller.address;

      const uploadResult = await componentActions.action555();
      expect(uploadResult.success).to.be.true;
      expect(uploadResult.uploadResults).to.exist;
      expect(uploadResult.uploadResults.totalCount).to.be.greaterThan(0);
      console.log(`✅ Components uploaded: ${uploadResult.uploadResults.totalCount}`);

      // STEP 4: Validate complex fields uniqueness
      const AmanitaIntl = await ethers.getContractAt(
        'AmanitaInternationalLogic',
        deployedContracts.amanitaInternational
      );

      // Проверяем хотя бы 2 компонента
      if (uploadResult.uploadResults.totalCount >= 2 && uploadResult.uploadResults.results) {
        const successfulResults = uploadResult.uploadResults.results.filter(r => r.success && r.componentId);
        if (successfulResults.length >= 2) {
          const comp1 = successfulResults[0].componentId;
          const comp2 = successfulResults[1].componentId;

          const cid1 = await AmanitaIntl.getComplexFieldCID(`ComponentDescription.${comp1}`, 'ru');
          const cid2 = await AmanitaIntl.getComplexFieldCID(`ComponentDescription.${comp2}`, 'ru');

          expect(cid1).to.not.equal('');
          expect(cid1).to.not.equal(ethers.ZeroAddress);
          expect(cid2).to.not.equal('');
          expect(cid2).to.not.equal(ethers.ZeroAddress);
          expect(cid1).to.not.equal(cid2); // Уникальность

          console.log(`✅ Complex fields uniqueness verified: ${comp1} != ${comp2}`);
          console.log(`   CID1: ${cid1}`);
          console.log(`   CID2: ${cid2}`);
        }
      }

      console.log(`✅ Component pipeline validated: ${uploadResult.uploadResults.totalCount} components`);
    });
  });
});

// Helper functions
async function deployAllContractsForPipeline() {
  const [deployer] = await ethers.getSigners();

  // Deploy MagicRegistry
  const MagicRegistry = await ethers.getContractFactory('AmanitaRegistry');
  const registry = await MagicRegistry.deploy();
  await registry.waitForDeployment();
  const registryAddress = await registry.getAddress();

  // Deploy SpiralEngine (UUPS)
  const SpiralEngineLogic = await ethers.getContractFactory('SpiralEngineLogic');
  const spiralLogic = await SpiralEngineLogic.deploy();
  await spiralLogic.waitForDeployment();

  const spiralInterface = spiralLogic.interface;
  const initializeData = spiralInterface.encodeFunctionData('initialize', [deployer.address]);

  const SpiralEngineProxy = await ethers.getContractFactory('SpiralEngineProxy');
  const spiralProxy = await SpiralEngineProxy.deploy(await spiralLogic.getAddress(), initializeData);
  await spiralProxy.waitForDeployment();
  const spiralAddress = await spiralProxy.getAddress();

  // Deploy OrganicComponentRegistry (UUPS)
  const OrganicLogic = await ethers.getContractFactory('OrganicComponentRegistryLogic');
  const organicLogic = await OrganicLogic.deploy();
  await organicLogic.waitForDeployment();

  const organicInterface = organicLogic.interface;
  const organicInitData = organicInterface.encodeFunctionData('initialize', [deployer.address]);

  const OrganicProxy = await ethers.getContractFactory('OrganicComponentRegistryProxy');
  const organicProxy = await OrganicProxy.deploy(await organicLogic.getAddress(), organicInitData);
  await organicProxy.waitForDeployment();
  const organicAddress = await organicProxy.getAddress();

  // Setup: setSpiralEngine
  const OrganicRegistry = await ethers.getContractAt('OrganicComponentRegistryLogic', organicAddress);
  const organicWithSigner = OrganicRegistry.connect(deployer);
  await (await organicWithSigner.setSpiralEngine(spiralAddress)).wait();

  // Deploy AmanitaInternational (UUPS)
  const AmanitaLogic = await ethers.getContractFactory('AmanitaInternationalLogic');
  const amanitaLogic = await AmanitaLogic.deploy();
  await amanitaLogic.waitForDeployment();
  const amanitaLogicAddress = await amanitaLogic.getAddress();

  const amanitaInterface = amanitaLogic.interface;
  const amanitaInitData = amanitaInterface.encodeFunctionData('initialize', [deployer.address, spiralAddress]);

  const AmanitaProxy = await ethers.getContractFactory('AmanitaInternationalProxy');
  const amanitaProxy = await AmanitaProxy.deploy(amanitaLogicAddress, amanitaInitData);
  await amanitaProxy.waitForDeployment();
  const amanitaAddress = await amanitaProxy.getAddress();

  // Register in MagicRegistry
  const registryWithSigner = (await ethers.getContractAt('AmanitaRegistry', registryAddress)).connect(deployer);
  await registryWithSigner.set('AmanitaInternational', amanitaAddress);

  return {
    magicRegistry: registryAddress,
    spiralEngine: spiralAddress,
    organicComponentRegistry: organicAddress,
    amanitaInternational: amanitaAddress
  };
}

function registerContractsInMagicRegistry(harnessInstance, deployed) {
  if (!harnessInstance || !deployed) {
    return;
  }
  // MagicRegistry registration is done in deployAllContractsForPipeline
  // This function can be extended if needed
}

