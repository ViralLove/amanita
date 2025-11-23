/**
 * E2E: Action 777 - Create Root Invites
 */

const { expect } = require('chai');
const {
  E2EHarness,
  expectRevertCustom,
  assertSellerState
} = require('../../../helpers');
const { ethers } = require('hardhat');

describe('E2E: Action 777 - Create Root Invites', function() {
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

  describe('Root Invite Generation (real SpiralEngine)', () => {
    let suite;
    let SpiralEngine;

    beforeEach(async () => {
      suite = await harness.deployProductSuite({
        forceRedeploy: true,
        invitesPrefix: 'ACTION777'
      });
      SpiralEngine = await ethers.getContractAt('SpiralEngineLogic', suite.spiralEngineAddress);
    });

    it('должен минтить root invite и сохранять mapping', async () => {
      const inviteCode = `AMANITA-ROOT-${Date.now()}`;
      const mintTx = await SpiralEngine.connect(suite.admin).mintInvite(inviteCode, 0);
      await mintTx.wait();

      const exists = await SpiralEngine.inviteCodeExists(inviteCode);
      expect(exists).to.be.true;

      const tokenId = await SpiralEngine.inviteCodeToTokenId(inviteCode);
      expect(Number(tokenId)).to.be.greaterThan(0);

      console.log(`✓ Root invite minted: ${inviteCode}, tokenId=${tokenId}`);
    });

    it('должен активировать seller через prepareSellerForE2E c reuse root invite', async function() {
      this.timeout(60000);

      const rootInvite = `AMANITA-ROOT-${Date.now()}`;
      await (await SpiralEngine.connect(suite.admin).mintInvite(rootInvite, 0)).wait();

      const result = await harness.prepareSellerForE2E({
        spiralEngine: SpiralEngine,
        deployerSigner: suite.admin,
        sellerSigner: suite.seller,
        invitesPrefix: 'ACTION777',
        useExistingInvite: rootInvite
      });

      expect(result.sellerInvites).to.have.lengthOf(12);

      const adminAddress = await suite.admin.getAddress();
      await assertSellerState(SpiralEngine, result.sellerAddress, {
        activated: true,
        sellerRole: true,
        activatorRole: true,
        activatorAddress: adminAddress
      });
      
      console.log(`✓ Seller prepared via helper, root invite=${rootInvite}`);
    });

    it('должен отклонять mintInvite без SELLER_ROLE', async () => {
      const [, , randomUser] = await ethers.getSigners();

      await expectRevertCustom(
        SpiralEngine.connect(randomUser).mintInvite('AMANITA-HACK-0001', 0),
        'AccessControlUnauthorizedAccount',
        SpiralEngine
      );

      console.log('✓ Unauthorized mintInvite rejected');
    });
  });
});

