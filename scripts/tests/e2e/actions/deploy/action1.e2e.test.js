/**
 * E2E Test: Action 1 - Full Deployment with SBT Ecosystem
 * Tests real deployment with Hardhat network
 */

const { expect } = require('chai');
const hre = require('hardhat');

describe('E2E: Action 1 - Full Deployment', function() {
  // Increase timeout for real deployment
  this.timeout(180000); // 3 minutes

  let deployer;
  let provider;
  let actionsManager;
  let result;

  before(async function() {
    // Get provider and signer
    const { ethers } = hre;
    provider = ethers.provider;
    [deployer] = await ethers.getSigners();
    
    console.log('\n🔷 E2E Test Setup');
    console.log(`   Deployer: ${deployer.address}`);
    console.log(`   Network: ${hre.network.name}`);
    console.log(`   Block: ${await provider.getBlockNumber()}`);
    
    // Import modular system
    const EthersUtils = require('../../../../lib/utils/EthersUtils');
    const ContractManager = require('../../../../lib/services/ContractManager');
    const { ActionsManager } = require('../../../../lib/actions');
    
    // Create config (mimic real Config class with deployer key)
    // Using Hardhat default account #0 private key
    const deployerPrivateKey = '0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80';
    
    const config = {
      get: (key) => {
        if (key === 'deployer.privateKey') return deployerPrivateKey;
        if (key === 'network') return 'hardhat';
        return null;
      },
      getContractAddress: () => null,
      getDefaultGasLimit: () => 5000000,
      getNetworkConfig: () => ({ gasLimit: 5000000 })
    };
    
    // Initialize modules
    const ethersUtils = new EthersUtils(provider, config);
    const contractManager = new ContractManager(provider, config, ethersUtils);
    actionsManager = new ActionsManager(contractManager, null, ethersUtils, config);
    
    console.log('✅ Modules initialized');
  });
  
  it('должен деплоить все контракты на hardhat network', async function() {
    console.log('\n🚀 Executing Action 1: Full Deployment');
    
    // WHEN: Execute Action 1
    result = await actionsManager.executeAction(1);
    
    // THEN: Action successful
    expect(result.success).to.be.true;
    expect(result.contracts).to.exist;
    
    console.log('✅ Action 1 completed successfully');
  });
  
  it('должен задеплоить MagicRegistry', async function() {
    expect(result.contracts.magicRegistry).to.exist;
    const address = await result.contracts.magicRegistry.getAddress();
    expect(address).to.match(/^0x[0-9a-fA-F]{40}$/);
    console.log(`✅ MagicRegistry: ${address}`);
  });
  
  it('должен задеплоить UUPS контракты', async function() {
    // SpiralEngine
    expect(result.contracts.spiralEngine).to.exist;
    const spiralEngineAddr = await result.contracts.spiralEngine.getAddress();
    expect(spiralEngineAddr).to.match(/^0x[0-9a-fA-F]{40}$/);
    console.log(`✅ SpiralEngine: ${spiralEngineAddr}`);
    
    // ProductRegistry
    expect(result.contracts.productRegistry).to.exist;
    const productRegistryAddr = await result.contracts.productRegistry.getAddress();
    expect(productRegistryAddr).to.match(/^0x[0-9a-fA-F]{40}$/);
    console.log(`✅ ProductRegistry: ${productRegistryAddr}`);
    
    // OrganicComponentRegistry
    expect(result.contracts.organicComponentRegistry).to.exist;
    const organicRegistryAddr = await result.contracts.organicComponentRegistry.getAddress();
    expect(organicRegistryAddr).to.match(/^0x[0-9a-fA-F]{40}$/);
    console.log(`✅ OrganicComponentRegistry: ${organicRegistryAddr}`);
    
    // AmanitaInternational
    expect(result.contracts.amanitaInternational).to.exist;
    const amanitaIntlAddr = await result.contracts.amanitaInternational.getAddress();
    expect(amanitaIntlAddr).to.match(/^0x[0-9a-fA-F]{40}$/);
    console.log(`✅ AmanitaInternational: ${amanitaIntlAddr}`);
  });
  
  it('должен задеплоить SBT экосистему', async function() {
    // SoulboundCore
    expect(result.contracts.soulboundCore).to.exist;
    const soulboundCoreAddr = await result.contracts.soulboundCore.getAddress();
    expect(soulboundCoreAddr).to.match(/^0x[0-9a-fA-F]{40}$/);
    console.log(`✅ SoulboundCore: ${soulboundCoreAddr}`);
    
    // SoulMetadata
    expect(result.contracts.soulMetadata).to.exist;
    const soulMetadataAddr = await result.contracts.soulMetadata.getAddress();
    expect(soulMetadataAddr).to.match(/^0x[0-9a-fA-F]{40}$/);
    console.log(`✅ SoulMetadata: ${soulMetadataAddr}`);
    
    // SoulRecovery
    expect(result.contracts.soulRecovery).to.exist;
    const soulRecoveryAddr = await result.contracts.soulRecovery.getAddress();
    expect(soulRecoveryAddr).to.match(/^0x[0-9a-fA-F]{40}$/);
    console.log(`✅ SoulRecovery: ${soulRecoveryAddr}`);
    
    // SoulIntegration
    expect(result.contracts.soulIntegration).to.exist;
    const soulIntegrationAddr = await result.contracts.soulIntegration.getAddress();
    expect(soulIntegrationAddr).to.match(/^0x[0-9a-fA-F]{40}$/);
    console.log(`✅ SoulIntegration: ${soulIntegrationAddr}`);
    
    // SoulIdentity
    expect(result.contracts.soulIdentity).to.exist;
    const soulIdentityAddr = await result.contracts.soulIdentity.getAddress();
    expect(soulIdentityAddr).to.match(/^0x[0-9a-fA-F]{40}$/);
    console.log(`✅ SoulIdentity: ${soulIdentityAddr}`);
  });
  
  it('должен правильно инициализировать SoulIdentity с зависимостями', async function() {
    const soulIdentity = result.contracts.soulIdentity;
    const soulboundCore = result.contracts.soulboundCore;
    const soulMetadata = result.contracts.soulMetadata;
    
    // Verify SoulIdentity constructor worked correctly
    const soulboundCoreAddr = await soulIdentity.soulboundCore();
    const soulMetadataAddr = await soulIdentity.soulMetadata();
    
    expect(soulboundCoreAddr).to.equal(await soulboundCore.getAddress());
    expect(soulMetadataAddr).to.equal(await soulMetadata.getAddress());
    
    console.log('✅ SoulIdentity dependencies verified');
    console.log(`   soulboundCore: ${soulboundCoreAddr}`);
    console.log(`   soulMetadata: ${soulMetadataAddr}`);
  });
  
  it('должен настроить SBT connections', async function() {
    // Ensure result is available from previous test
    if (!result || !result.contracts) {
      throw new Error('Action 1 must be executed first');
    }
    
    const { soulboundCore, soulMetadata, soulRecovery, soulIntegration, soulIdentity, spiralEngine } = result.contracts;
    
    // Verify SoulboundCore connections (using getter methods)
    const metadataContract = await soulboundCore.getMetadataContract();
    const recoveryContract = await soulboundCore.getRecoveryContract();
    const integrationContract = await soulboundCore.getIntegrationContract();
    
    expect(metadataContract).to.equal(await soulMetadata.getAddress());
    expect(recoveryContract).to.equal(await soulRecovery.getAddress());
    expect(integrationContract).to.equal(await soulIntegration.getAddress());
    
    console.log('✅ SoulboundCore connections verified');
    console.log(`   Metadata: ${metadataContract}`);
    console.log(`   Recovery: ${recoveryContract}`);
    console.log(`   Integration: ${integrationContract}`);
    
    // Verify SpiralEngine connection (public variable - auto getter)
    const soulIdentityInSpiral = await spiralEngine.soulIdentity();
    expect(soulIdentityInSpiral).to.equal(await soulIdentity.getAddress());
    
    console.log('✅ SpiralEngine → SoulIdentity connection verified');
    console.log(`   SoulIdentity: ${soulIdentityInSpiral}`);
  });
  
  it('должен зарегистрировать все контракты в MagicRegistry', async function() {
    const magicRegistry = result.contracts.magicRegistry;
    
    // Verify all contracts are registered
    const contracts = [
      'SpiralEngine',
      'ProductRegistry',
      'OrganicComponentRegistry',
      'AmanitaInternational',
      'SoulboundCore',
      'SoulMetadata',
      'SoulRecovery',
      'SoulIntegration',
      'SoulIdentity'
    ];
    
    for (const contractName of contracts) {
      const registeredAddress = await magicRegistry.get(contractName);
      expect(registeredAddress).to.not.equal('0x0000000000000000000000000000000000000000');
      
      const expectedAddress = await result.contracts[contractName.charAt(0).toLowerCase() + contractName.slice(1)].getAddress();
      expect(registeredAddress).to.equal(expectedAddress);
      
      console.log(`✅ ${contractName}: ${registeredAddress}`);
    }
  });

  // ================================================================
  // NEW: SetupActions Delegation Validation
  // ================================================================

  describe('SetupActions Delegation (NEW - проверка архитектуры)', () => {
    it('должен делегировать setup в SetupActions.setupSystemConnections()', async function() {
      // Ensure result is available
      if (!result || !result.contracts) {
        throw new Error('Action 1 must be executed first');
      }
      
      // VALIDATE: Setup был выполнен (не пропущен)
      // Проверяем что connections установлены (это означает что setupSystemConnections() был вызван)
      
      const { soulboundCore, spiralEngine, organicComponentRegistry } = result.contracts;
      
      // 1. SBT ecosystem connections (из SetupActions.setupSBTEcosystem)
      const metadataContract = await soulboundCore.getMetadataContract();
      expect(metadataContract).to.not.equal(hre.ethers.ZeroAddress);
      
      const soulIdentityInSpiral = await spiralEngine.soulIdentity();
      expect(soulIdentityInSpiral).to.not.equal(hre.ethers.ZeroAddress);
      
      console.log('✅ SetupActions.setupSBTEcosystem() executed (connections present)');
      
      // 2. OrganicComponentRegistry connection (из SetupActions.setupOrganicComponentRegistry)
      const spiralEngineInOrganic = await organicComponentRegistry.spiralEngine();
      expect(spiralEngineInOrganic).to.not.equal(hre.ethers.ZeroAddress);
      expect(spiralEngineInOrganic).to.equal(await spiralEngine.getAddress());
      
      console.log('✅ SetupActions.setupOrganicComponentRegistry() executed');
      console.log(`   OrganicComponentRegistry.spiralEngine = ${spiralEngineInOrganic}`);
    });

    it('должен установить OrganicComponentRegistry.spiralEngine (критично для action555)', async function() {
      // Ensure result is available
      if (!result || !result.contracts) {
        throw new Error('Action 1 must be executed first');
      }
      
      const { spiralEngine, organicComponentRegistry } = result.contracts;
      
      // VALIDATE: setSpiralEngine() был вызван
      const spiralEngineAddress = await organicComponentRegistry.spiralEngine();
      const expectedAddress = await spiralEngine.getAddress();
      
      expect(spiralEngineAddress).to.equal(expectedAddress);
      expect(spiralEngineAddress).to.not.equal(hre.ethers.ZeroAddress);
      
      console.log('✅ OrganicComponentRegistry.setSpiralEngine() validated');
      console.log(`   Expected: ${expectedAddress}`);
      console.log(`   Actual:   ${spiralEngineAddress}`);
      console.log('   🎯 КРИТИЧНО: Без этого Action 555 падает!');
    });

    it('должен установить все 4 SBT connections (SetupActions.setupSBTEcosystem)', async function() {
      // Ensure result is available
      if (!result || !result.contracts) {
        throw new Error('Action 1 must be executed first');
      }
      
      const { soulboundCore, soulMetadata, soulRecovery, soulIntegration, spiralEngine, soulIdentity } = result.contracts;
      
      // VALIDATE: 4 connections из SetupActions.setupSBTEcosystem()
      
      // Connection 1: SoulboundCore → SoulMetadata
      const metadataAddr = await soulboundCore.getMetadataContract();
      expect(metadataAddr).to.equal(await soulMetadata.getAddress());
      console.log('✅ Connection 1/4: SoulboundCore → SoulMetadata');
      
      // Connection 2: SoulboundCore → SoulRecovery
      const recoveryAddr = await soulboundCore.getRecoveryContract();
      expect(recoveryAddr).to.equal(await soulRecovery.getAddress());
      console.log('✅ Connection 2/4: SoulboundCore → SoulRecovery');
      
      // Connection 3: SoulboundCore → SoulIntegration
      const integrationAddr = await soulboundCore.getIntegrationContract();
      expect(integrationAddr).to.equal(await soulIntegration.getAddress());
      console.log('✅ Connection 3/4: SoulboundCore → SoulIntegration');
      
      // Connection 4: SpiralEngine → SoulIdentity
      const soulIdentityAddr = await spiralEngine.soulIdentity();
      expect(soulIdentityAddr).to.equal(await soulIdentity.getAddress());
      console.log('✅ Connection 4/4: SpiralEngine → SoulIdentity');
      
      console.log('\n🎯 Все 4 связи установлены через SetupActions.setupSBTEcosystem()');
    });
  });
});
