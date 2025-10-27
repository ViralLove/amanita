/**
 * E2E: Component Pipeline (777 → 555)
 */

const { expect } = require('chai');
const E2EHarness = require('../../helpers/E2EHarness');

describe('E2E Workflow: Component Pipeline (777 → 555)', function() {
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

  describe('Sequential Workflow', () => {
    it('должен выполнить component workflow', async () => {
      const { ethers } = require('hardhat');
      
      // Deploy SpiralEngine (prerequisite)
      const Logic = await ethers.getContractFactory('SpiralEngineLogic');
      const logic = await Logic.deploy();
      await logic.waitForDeployment();
      
      const Proxy = await ethers.getContractFactory('SpiralEngineProxy');
      const proxy = await Proxy.deploy(await logic.getAddress(), '0x');
      await proxy.waitForDeployment();
      
      const spiralEngineAddress = await proxy.getAddress();
      
      await harness.validateDeployment(spiralEngineAddress);
      console.log(`✓ Component workflow infrastructure ready`);
    });
  });
});

