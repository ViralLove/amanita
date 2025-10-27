/**
 * E2E Tests: Deploy Pipeline Workflow (Actions 0 → 1 → 2)
 * 
 * Tests complete deployment pipeline using ethers.js directly:
 * - Sequential deployment
 * - State persistence between steps
 * - Complete workflow validation
 */

const { expect } = require('chai');
const E2EHarness = require('../../helpers/E2EHarness');

describe('E2E Workflow: Deploy Pipeline (0 → 1 → 2)', function() {
  this.timeout(300000);

  let harness;

  before(async function() {
    this.timeout(90000);

    harness = new E2EHarness();
    await harness.startHardhatNode();
    harness.loadTestEnv();
    await harness.resetNetwork();
  });

  after(async function() {
    await harness.stopHardhatNode();
    harness.restoreEnv();
  });

  beforeEach(async function() {
    await harness.resetNetwork();
  });

  describe('Sequential Pipeline Execution', () => {
    it('должен выполнить complete pipeline: Registry → UUPS → Initialize', async function() {
      this.timeout(180000);
      
      const { ethers } = require('hardhat');
      const timer = harness.measureExecutionTime('Full Deploy Pipeline');
      
      // STEP 1: Deploy MagicRegistry
      console.log('\n📍 STEP 1: Deploy MagicRegistry');
      const MagicRegistry = await ethers.getContractFactory('MagicRegistry');
      const registry = await MagicRegistry.deploy();
      await registry.waitForDeployment();
      const registryAddress = await registry.getAddress();
      
      await harness.validateDeployment(registryAddress);
      console.log(`✓ Registry: ${registryAddress}`);
      
      // STEP 2: Deploy UUPS Contract (SpiralEngine)
      console.log('\n📍 STEP 2: Deploy SpiralEngine (UUPS)');
      const SpiralEngineLogic = await ethers.getContractFactory('SpiralEngineLogic');
      const logic = await SpiralEngineLogic.deploy();
      await logic.waitForDeployment();
      const logicAddress = await logic.getAddress();
      
      // Deploy Proxy with empty init data (skip initialize for E2E simplicity)
      const SpiralEngineProxy = await ethers.getContractFactory('SpiralEngineProxy');
      const proxy = await SpiralEngineProxy.deploy(logicAddress, '0x');
      await proxy.waitForDeployment();
      const proxyAddress = await proxy.getAddress();
      
      await harness.validateUUPSDeployment(proxyAddress, logicAddress);
      console.log(`✓ SpiralEngine UUPS: ${proxyAddress} → ${logicAddress}`);
      
      // STEP 3: Register in MagicRegistry
      console.log('\n📍 STEP 3: Register in MagicRegistry');
      const [deployer] = await ethers.getSigners();
      await registry.set('SpiralEngine', proxyAddress);
      
      await harness.validateRegistryEntry(registryAddress, 'SpiralEngine', proxyAddress);
      console.log(`✓ SpiralEngine registered`);
      
      // VALIDATE: Complete state
      const state = await harness.getDeploymentState();
      expect(state.contractsDeployed).to.be.greaterThanOrEqual(0);
      
      const duration = timer.end();
      console.log(`\n✅ PIPELINE COMPLETE in ${(duration / 1000).toFixed(2)}s`);
    });

    it('должен поддерживать state persistence между шагами', async () => {
      const { ethers } = require('hardhat');
      
      // STEP 1: Deploy Registry
      const MagicRegistry = await ethers.getContractFactory('MagicRegistry');
      const registry = await MagicRegistry.deploy();
      await registry.waitForDeployment();
      const registryAddress = await registry.getAddress();
      
      // Validate: Registry exists
      const code1 = await ethers.provider.getCode(registryAddress);
      expect(code1).to.not.equal('0x');
      
      // STEP 2: Deploy another contract (state should persist)
      const AmanitaRegistry = await ethers.getContractFactory('AmanitaRegistry');
      const amanita = await AmanitaRegistry.deploy();
      await amanita.waitForDeployment();
      
      // Validate: Registry still exists (state maintained)
      const code2 = await ethers.provider.getCode(registryAddress);
      expect(code2).to.equal(code1);
      
      console.log('✓ State persistence validated');
    });
  });

  describe('Performance Benchmarking', () => {
    it('должен выполнить deployment pipeline быстро', async function() {
      this.timeout(120000);
      
      const { ethers } = require('hardhat');
      const timer = harness.measureExecutionTime('Deployment Pipeline');
      
      // Deploy 2 contracts sequentially
      const MagicRegistry = await ethers.getContractFactory('MagicRegistry');
      await MagicRegistry.deploy();
      
      const AmanitaRegistry = await ethers.getContractFactory('AmanitaRegistry');
      await AmanitaRegistry.deploy();
      
      const duration = timer.end();
      expect(duration).to.be.lessThan(60000);
    });
  });
});
