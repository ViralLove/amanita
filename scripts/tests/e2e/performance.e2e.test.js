/**
 * E2E: Performance Benchmarks
 * 
 * Tests performance across all workflows and operations
 */

const { expect } = require('chai');
const E2EHarness = require('../helpers/E2EHarness');
const fs = require('fs');
const path = require('path');

describe('E2E: Performance', function() {
  this.timeout(180000);

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

  describe('Deployment Performance', () => {
    it('should deploy MagicRegistry быстро (< 1s)', async () => {
      const { ethers } = require('hardhat');
      const timer = harness.measureExecutionTime('MagicRegistry Deploy');
      
      await (await ethers.getContractFactory('MagicRegistry')).deploy();
      
      const duration = timer.end();
      expect(duration).to.be.lessThan(1000);
    });

    it('should deploy UUPS contract быстро (< 2s)', async () => {
      const { ethers } = require('hardhat');
      const timer = harness.measureExecutionTime('UUPS Deploy');
      
      const Logic = await ethers.getContractFactory('SpiralEngineLogic');
      const logic = await Logic.deploy();
      await logic.waitForDeployment();
      
      const Proxy = await ethers.getContractFactory('SpiralEngineProxy');
      await Proxy.deploy(await logic.getAddress(), '0x');
      
      const duration = timer.end();
      expect(duration).to.be.lessThan(2000);
    });

    it('should deploy multiple contracts efficiently', async () => {
      const { ethers } = require('hardhat');
      const timer = harness.measureExecutionTime('Deploy 3 Contracts');
      
      await (await ethers.getContractFactory('MagicRegistry')).deploy();
      await (await ethers.getContractFactory('AmanitaRegistry')).deploy();
      
      const Logic = await ethers.getContractFactory('SpiralEngineLogic');
      const logic = await Logic.deploy();
      await logic.waitForDeployment();
      
      const duration = timer.end();
      expect(duration).to.be.lessThan(5000);
    });
  });

  describe('Snapshot Performance', () => {
    it('should create snapshot быстро (< 100ms)', async () => {
      const timer = harness.measureExecutionTime('Snapshot Creation');
      
      await harness.saveState('perf-test');
      
      const duration = timer.end();
      expect(duration).to.be.lessThan(100);
    });

    it('should reset network быстро (< 100ms)', async () => {
      await harness.saveState('reset-test');
      
      const timer = harness.measureExecutionTime('Network Reset');
      
      await harness.resetNetwork('reset-test');
      
      const duration = timer.end();
      expect(duration).to.be.lessThan(100);
    });
  });

  describe('Workflow Performance', () => {
    it('should execute catalog workflow быстро (< 5s)', async () => {
      const { ethers } = require('hardhat');
      const timer = harness.measureExecutionTime('Catalog Workflow');
      
      // CSV → JSON
      const csvPath = path.join(__dirname, '../fixtures/catalog/test_catalog.csv');
      const csvData = fs.readFileSync(csvPath, 'utf8');
      const lines = csvData.trim().split('\n');
      const products = lines.slice(1).map(line => {
        const values = line.split(',');
        return { id: values[0], name: values[1] };
      });
      
      // Generate CID
      const randomPart = Array(5).fill(0).map(() => Math.random().toString(36).substring(2, 11)).join('');
      const cid = `Qm${randomPart.substring(0, 44)}`;
      
      // Deploy registry
      await (await ethers.getContractFactory('ProductRegistryLogic')).deploy();
      
      const duration = timer.end();
      expect(duration).to.be.lessThan(5000);
    });

    it('should benchmark large catalog processing', async () => {
      const csvPath = path.join(__dirname, '../fixtures/catalog/large_catalog.csv');
      const timer = harness.measureExecutionTime('Large Catalog Processing');
      
      const csvData = fs.readFileSync(csvPath, 'utf8');
      const lines = csvData.trim().split('\n');
      const products = lines.slice(1).map(line => {
        const values = line.split(',');
        return {
          id: values[0],
          name: values[1],
          description: values[2],
          price: parseFloat(values[3])
        };
      });
      
      const json = JSON.stringify(products);
      
      const duration = timer.end();
      expect(duration).to.be.lessThan(100); // Should be very fast
      expect(products.length).to.equal(10);
    });
  });

  describe('Gas Usage Tracking', () => {
    it('should track deployment gas usage', async () => {
      const { ethers } = require('hardhat');
      
      const Registry = await ethers.getContractFactory('MagicRegistry');
      const registry = await Registry.deploy();
      await registry.waitForDeployment();
      
      const deployTx = registry.deploymentTransaction();
      
      if (deployTx && deployTx.hash) {
        const gasUsed = await harness.measureGasUsage(deployTx.hash);
        expect(parseInt(gasUsed)).to.be.greaterThan(0);
        console.log(`✓ Gas tracked: ${gasUsed}`);
      } else {
        console.log('ℹ️ Gas tracking skipped (no deployment tx hash)');
      }
    });

    it('should track transaction gas usage', async () => {
      const { ethers } = require('hardhat');
      
      const Registry = await ethers.getContractFactory('MagicRegistry');
      const registry = await Registry.deploy();
      await registry.waitForDeployment();
      
      const tx = await registry.set('TestContract', '0x1234567890123456789012345678901234567890');
      const receipt = await tx.wait();
      
      expect(receipt.gasUsed > 0n).to.be.true;
      console.log(`✓ Transaction gas: ${receipt.gasUsed.toString()}`);
    });
  });

  describe('Scalability Benchmarks', () => {
    it('should handle sequential deployments efficiently', async () => {
      const { ethers } = require('hardhat');
      const timer = harness.measureExecutionTime('Sequential 5 Deployments');
      
      const deployments = [];
      
      for (let i = 0; i < 5; i++) {
        const registry = await (await ethers.getContractFactory('MagicRegistry')).deploy();
        await registry.waitForDeployment();
        deployments.push(await registry.getAddress());
      }
      
      const duration = timer.end();
      
      expect(deployments).to.have.lengthOf(5);
      expect(duration).to.be.lessThan(10000);
      
      console.log(`✓ 5 deployments in ${(duration / 1000).toFixed(2)}s`);
    });
  });
});
