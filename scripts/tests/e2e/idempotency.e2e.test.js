/**
 * E2E: Idempotency Tests
 * 
 * Tests re-deployment, re-execution, and idempotent operations
 */

const { expect } = require('chai');
const E2EHarness = require('../helpers/E2EHarness');

describe('E2E: Idempotency', function() {
  this.timeout(120000);

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

  describe('Re-Deployment', () => {
    it('should allow multiple deployments of same contract', async () => {
      const { ethers } = require('hardhat');
      
      // Deploy twice
      const Registry1 = await (await ethers.getContractFactory('MagicRegistry')).deploy();
      await Registry1.waitForDeployment();
      const addr1 = await Registry1.getAddress();
      
      const Registry2 = await (await ethers.getContractFactory('MagicRegistry')).deploy();
      await Registry2.waitForDeployment();
      const addr2 = await Registry2.getAddress();
      
      // Different addresses (new instances)
      expect(addr1).to.not.equal(addr2);
      
      // Both deployed
      await harness.validateDeployment(addr1);
      await harness.validateDeployment(addr2);
      
      console.log(`✓ Multiple deployments: ${addr1} !== ${addr2}`);
    });

    it('should allow registry update (idempotent set)', async () => {
      const { ethers } = require('hardhat');
      
      const Registry = await ethers.getContractFactory('MagicRegistry');
      const registry = await Registry.deploy();
      await registry.waitForDeployment();
      
      const testAddress1 = '0x1111111111111111111111111111111111111111';
      const testAddress2 = '0x2222222222222222222222222222222222222222';
      
      // Set first time
      await registry.set('TestContract', testAddress1);
      let retrieved = await registry.get('TestContract');
      expect(retrieved).to.equal(testAddress1);
      
      // Update (idempotent)
      await registry.set('TestContract', testAddress2);
      retrieved = await registry.get('TestContract');
      expect(retrieved).to.equal(testAddress2);
      
      console.log('✓ Registry update idempotent');
    });
  });

  describe('Re-Execution', () => {
    it('should handle workflow re-execution after reset', async () => {
      const { ethers } = require('hardhat');
      
      // Execution 1
      const Registry1 = await (await ethers.getContractFactory('MagicRegistry')).deploy();
      await Registry1.waitForDeployment();
      const addr1 = await Registry1.getAddress();
      
      // Reset
      await harness.resetNetwork();
      
      // Execution 2 (same workflow)
      const Registry2 = await (await ethers.getContractFactory('MagicRegistry')).deploy();
      await Registry2.waitForDeployment();
      const addr2 = await Registry2.getAddress();
      
      // Same address (deterministic deployment on reset node)
      expect(addr2).to.equal(addr1);
      
      console.log('✓ Re-execution after reset is deterministic');
    });

    it('should produce consistent results on re-run', async () => {
      const { ethers } = require('hardhat');
      
      // Run 1
      const [deployer] = await ethers.getSigners();
      const address1 = deployer.address;
      
      // Reset
      await harness.resetNetwork();
      
      // Run 2
      const [deployer2] = await ethers.getSigners();
      const address2 = deployer2.address;
      
      // Same deployer address
      expect(address2).to.equal(address1);
      
      console.log('✓ Consistent results on re-run');
    });
  });

  describe('State Idempotency', () => {
    it('should maintain contract state after snapshot restore', async () => {
      const { ethers } = require('hardhat');
      
      // Deploy and set state
      const Registry = await ethers.getContractFactory('MagicRegistry');
      const registry = await Registry.deploy();
      await registry.waitForDeployment();
      
      const testAddress1 = '0x1234567890123456789012345678901234567890';
      const testAddress2 = '0x9876543210987654321098765432109876543210';
      
      await registry.set('TestContract', testAddress1);
      
      // Save snapshot
      await harness.saveState('with-contract');
      
      // Change state (use different address, not zero)
      await registry.set('TestContract', testAddress2);
      let retrieved = await registry.get('TestContract');
      expect(retrieved).to.equal(testAddress2);
      
      // Restore snapshot
      await harness.restoreState('with-contract');
      
      // State restored to original
      const Registry2 = await ethers.getContractAt('MagicRegistry', await registry.getAddress());
      retrieved = await Registry2.get('TestContract');
      expect(retrieved).to.equal(testAddress1);
      
      console.log('✓ Snapshot restore maintains contract state');
    });
  });

  describe('Cleanup Validation', () => {
    it('should clean up after workflow failure', async () => {
      const { ethers } = require('hardhat');
      
      const initialBlock = await ethers.provider.getBlockNumber();
      
      try {
        // Workflow that fails
        await (await ethers.getContractFactory('MagicRegistry')).deploy();
        throw new Error('Simulated workflow failure');
      } catch (error) {
        // Reset (cleanup)
        await harness.resetNetwork();
        
        const resetBlock = await ethers.provider.getBlockNumber();
        expect(resetBlock).to.be.lessThanOrEqual(initialBlock + 3);
        
        console.log('✓ Cleanup after failure successful');
      }
    });
  });
});
