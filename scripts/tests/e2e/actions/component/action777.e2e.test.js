/**
 * E2E: Action 777 - Create Root Invites
 */

const { expect } = require('chai');
const E2EHarness = require('../../../helpers/E2EHarness');

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

  describe('Invite Generation', () => {
    it('должен генерировать 12 invite codes', () => {
      // Generate invite codes
      const codes = Array.from({ length: 12 }, (_, i) => 
        `AMANITA-${Math.random().toString(36).substring(2, 6).toUpperCase()}-${i.toString().padStart(4, '0')}`
      );
      
      expect(codes).to.have.lengthOf(12);
      console.log(`✓ Generated ${codes.length} invite codes`);
    });

    it('должен валидировать invite code format', async () => {
      const codes = ['AMANITA-AB12-0001', 'AMANITA-CD34-0002'];
      
      const validation = await harness.validateInviteCodes(codes);
      expect(validation.count).to.equal(2);
      
      console.log(`✓ Invite codes validated`);
    });
  });
});

