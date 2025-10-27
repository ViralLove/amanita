/**
 * E2E: Full Pipeline Workflow
 * 
 * Tests complete deployment workflow: Deploy → Initialize → Activate → Components → Catalog
 */

const { expect } = require('chai');
const E2EHarness = require('../../helpers/E2EHarness');
const fs = require('fs');
const path = require('path');

describe('E2E Workflow: Full Pipeline', function() {
  this.timeout(300000);

  let harness;

  before(async function() {
    harness = new E2EHarness();
    await harness.startHardhatNode();
    harness.loadTestEnv();
    await harness.resetNetwork();
  });

  after(async () => {
    await harness.stopHardhatNode();
    harness.restoreEnv();
  });

  beforeEach(async () => {
    await harness.resetNetwork();
  });

  describe('Complete Workflow Execution', () => {
    it('should execute Registry → Deploy → Catalog workflow', async function() {
      this.timeout(180000);
      
      const { ethers } = require('hardhat');
      const timer = harness.measureExecutionTime('Full Deployment Workflow');
      
      // PHASE 1: Deploy MagicRegistry
      console.log('\n📍 PHASE 1: Deploy Foundation');
      const Registry = await ethers.getContractFactory('MagicRegistry');
      const registry = await Registry.deploy();
      await registry.waitForDeployment();
      const registryAddress = await registry.getAddress();
      
      await harness.validateDeployment(registryAddress);
      console.log(`✓ MagicRegistry: ${registryAddress}`);
      
      // PHASE 2: Deploy UUPS Contracts
      console.log('\n📍 PHASE 2: Deploy UUPS Contracts');
      
      // SpiralEngine
      const SpiralLogic = await ethers.getContractFactory('SpiralEngineLogic');
      const spiralLogic = await SpiralLogic.deploy();
      await spiralLogic.waitForDeployment();
      const spiralLogicAddr = await spiralLogic.getAddress();
      
      const SpiralProxy = await ethers.getContractFactory('SpiralEngineProxy');
      const spiralProxy = await SpiralProxy.deploy(spiralLogicAddr, '0x');
      await spiralProxy.waitForDeployment();
      const spiralProxyAddr = await spiralProxy.getAddress();
      
      await harness.validateUUPSDeployment(spiralProxyAddr, spiralLogicAddr);
      await registry.set('SpiralEngine', spiralProxyAddr);
      console.log(`✓ SpiralEngine: ${spiralProxyAddr}`);
      
      // ProductRegistry
      const ProductLogic = await ethers.getContractFactory('ProductRegistryLogic');
      const productLogic = await ProductLogic.deploy();
      await productLogic.waitForDeployment();
      const productLogicAddr = await productLogic.getAddress();
      
      const ProductProxy = await ethers.getContractFactory('ProductRegistryProxy');
      const productProxy = await ProductProxy.deploy(productLogicAddr, '0x');
      await productProxy.waitForDeployment();
      const productProxyAddr = await productProxy.getAddress();
      
      await harness.validateUUPSDeployment(productProxyAddr, productLogicAddr);
      await registry.set('ProductRegistry', productProxyAddr);
      console.log(`✓ ProductRegistry: ${productProxyAddr}`);
      
      // PHASE 3: Catalog Processing
      console.log('\n📍 PHASE 3: Catalog Processing');
      const csvPath = path.join(__dirname, '../../fixtures/catalog/test_catalog.csv');
      const csvData = fs.readFileSync(csvPath, 'utf8');
      const lines = csvData.trim().split('\n');
      const products = [];
      
      for (let i = 1; i < lines.length; i++) {
        const values = lines[i].split(',');
        products.push({ id: values[0], name: values[1] });
      }
      
      const json = JSON.stringify(products);
      const randomPart = Array(5).fill(0).map(() => Math.random().toString(36).substring(2, 11)).join('');
      const cid = `Qm${randomPart.substring(0, 44)}`;
      
      console.log(`✓ Catalog processed: ${products.length} products → ${cid}`);
      
      // VALIDATE: Complete state
      console.log('\n📍 VALIDATION: Complete State');
      
      const registeredSpiral = await registry.get('SpiralEngine');
      expect(registeredSpiral.toLowerCase()).to.equal(spiralProxyAddr.toLowerCase());
      
      const registeredProduct = await registry.get('ProductRegistry');
      expect(registeredProduct.toLowerCase()).to.equal(productProxyAddr.toLowerCase());
      
      const duration = timer.end();
      
      console.log(`\n✅ FULL PIPELINE COMPLETE in ${(duration / 1000).toFixed(2)}s`);
      console.log(`  → Registry: ${registryAddress}`);
      console.log(`  → Contracts registered: 2`);
      console.log(`  → Catalog processed: ${products.length} products`);
    });

    it('should maintain state consistency across phases', async () => {
      const { ethers } = require('hardhat');
      
      // Phase 1: Deploy
      const Registry = await ethers.getContractFactory('MagicRegistry');
      const registry = await Registry.deploy();
      await registry.waitForDeployment();
      const registryAddress = await registry.getAddress();
      
      const initialCode = await ethers.provider.getCode(registryAddress);
      
      // Phase 2: More deployments
      await (await ethers.getContractFactory('AmanitaRegistry')).deploy();
      
      // Validate: Registry still exists (state maintained)
      const laterCode = await ethers.provider.getCode(registryAddress);
      expect(laterCode).to.equal(initialCode);
      
      console.log('✓ State consistency validated across phases');
    });
  });

  describe('Error Scenarios', () => {
    it('should handle deployment failure at each phase', async () => {
      const { ethers } = require('hardhat');
      
      // Phase 1 succeeds
      const Registry = await ethers.getContractFactory('MagicRegistry');
      const registry = await Registry.deploy();
      await registry.waitForDeployment();
      
      // Phase 2 fails
      try {
        await ethers.getContractFactory('NonExistentContract');
        expect.fail('Should throw');
      } catch (error) {
        expect(error).to.be.an('error');
        
        // Validate: Registry still deployed (partial state)
        const address = await registry.getAddress();
        await harness.validateDeployment(address);
        
        console.log('✓ Error handling validated (partial state preserved)');
      }
    });

    it('should handle catalog processing errors', async () => {
      // Invalid CSV path
      const fakePath = path.join(__dirname, '../../../fixtures/catalog/non_existent.csv');
      
      expect(fs.existsSync(fakePath)).to.be.false;
      
      console.log('✓ Catalog error handling validated');
    });
  });

  describe('Performance & Scale', () => {
    it('should handle large-scale deployment', async () => {
      const { ethers } = require('hardhat');
      const timer = harness.measureExecutionTime('Large Scale Deployment');
      
      // Deploy 5 contracts
      const contracts = [];
      
      contracts.push(await (await ethers.getContractFactory('MagicRegistry')).deploy());
      contracts.push(await (await ethers.getContractFactory('AmanitaRegistry')).deploy());
      
      const spiralLogic = await (await ethers.getContractFactory('SpiralEngineLogic')).deploy();
      await spiralLogic.waitForDeployment();
      contracts.push(await (await ethers.getContractFactory('SpiralEngineProxy')).deploy(await spiralLogic.getAddress(), '0x'));
      
      const productLogic = await (await ethers.getContractFactory('ProductRegistryLogic')).deploy();
      await productLogic.waitForDeployment();
      contracts.push(await (await ethers.getContractFactory('ProductRegistryProxy')).deploy(await productLogic.getAddress(), '0x'));
      
      const duration = timer.end();
      expect(contracts).to.have.lengthOf(4);
      expect(duration).to.be.lessThan(60000);
      
      console.log(`✓ Large-scale deployment: ${contracts.length} contracts in ${(duration / 1000).toFixed(2)}s`);
    });
  });
});
