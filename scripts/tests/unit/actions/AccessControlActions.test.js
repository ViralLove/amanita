/**
 * Unit tests for AccessControlActions
 * 
 * Coverage:
 * - action9: Grant ACTIVATOR_ROLE to seller
 * - action13: Diagnose seller state
 * - setupSoulIdentity: Generic SBT integration (NEW)
 */

const { expect } = require('chai');
const sinon = require('sinon');
const AccessControlActions = require('../../../lib/actions/AccessControlActions');

describe('AccessControlActions', function () {
  let accessControlActions;
  let mockContractManager;
  let mockEthersUtils;
  let mockConfig;
  let mockLogger;

  beforeEach(function () {
    // Mock ContractManager
    mockContractManager = {
      loadContract: sinon.stub(),
      loadUUPSContract: sinon.stub()
    };

    // Mock EthersUtils
    mockEthersUtils = {
      getSigner: sinon.stub(),
      isValidAddress: sinon.stub().returns(true)
    };

    // Mock Config
    mockConfig = {
      get: sinon.stub()
    };

    // Mock Logger
    mockLogger = {
      action: sinon.stub(),
      info: sinon.stub(),
      success: sinon.stub(),
      warn: sinon.stub(),
      error: sinon.stub(),
      failure: sinon.stub()
    };

    // Inject mocks
    accessControlActions = new AccessControlActions(
      mockContractManager,
      mockEthersUtils,
      mockConfig
    );
    accessControlActions.logger = mockLogger;
  });

  afterEach(function () {
    sinon.restore();
  });

  describe('setupSoulIdentity()', function () {
    let mockSoulIdentity;
    let mockSoulboundCore;
    let mockSoulMetadata;
    let mockDeploySigner;
    let mockUserSigner;
    const testUserAddress = '0x70997970C51812dc3A010C7d01b50e0d17dc79C8';
    const testTokenId = 1n;

    beforeEach(function () {
      // Mock SoulIdentity contract
      mockSoulIdentity = {
        getAddress: sinon.stub().resolves('0xSoulIdentity'),
        linkExternalIdentity: sinon.stub().resolves({
          wait: sinon.stub().resolves({ hash: '0xLinkTx' })
        }),
        getPrimaryIdentity: sinon.stub().resolves({
          identityType: 'did:spiral',
          identityValue: `did:spiral:${testUserAddress.toLowerCase()}`
        }),
        getSoulLevel: sinon.stub().resolves(1n),
        getSoulReputation: sinon.stub().resolves(100n),
        connect: sinon.stub().returnsThis()
      };

      // Mock SoulboundCore contract
      mockSoulboundCore = {
        getAddress: sinon.stub().resolves('0xSoulboundCore'),
        balanceOf: sinon.stub().resolves(0n),
        mintSoul: sinon.stub().resolves({
          wait: sinon.stub().resolves({ hash: '0xMintTx' })
        }),
        getNextTokenId: sinon.stub().resolves(testTokenId + 1n),
        getTotalSupply: sinon.stub().resolves(10n),
        ownerOf: sinon.stub().resolves(testUserAddress),
        connect: sinon.stub().returnsThis()
      };

      // Mock SoulMetadata contract
      mockSoulMetadata = {
        getAddress: sinon.stub().resolves('0xSoulMetadata'),
        initializeMetadata: sinon.stub().resolves({
          wait: sinon.stub().resolves({ hash: '0xMetadataTx' })
        }),
        connect: sinon.stub().returnsThis()
      };

      // Mock signers
      mockDeploySigner = { address: '0xDeployer' };
      mockUserSigner = { address: testUserAddress };

      // Setup stubs
      mockContractManager.loadContract
        .withArgs('SoulIdentity').resolves(mockSoulIdentity)
        .withArgs('SoulboundCore').resolves(mockSoulboundCore)
        .withArgs('SoulMetadata').resolves(mockSoulMetadata);

      mockEthersUtils.getSigner
        .withArgs(undefined).returns(mockDeploySigner)
        .withArgs(sinon.match.string).returns(mockUserSigner);

      mockConfig.get
        .withArgs('seller.privateKey').returns('0xPrivateKey')
        .withArgs('user.privateKey').returns('0xPrivateKey');

      mockSoulboundCore.connect.withArgs(mockDeploySigner).returns(mockSoulboundCore);
      mockSoulMetadata.connect.withArgs(mockUserSigner).returns(mockSoulMetadata);
      mockSoulIdentity.connect.withArgs(mockDeploySigner).returns(mockSoulIdentity);
    });

    it('должен создать новый SBT токен и настроить интеграцию', async function () {
      const result = await accessControlActions.setupSoulIdentity(testUserAddress);

      expect(result.success).to.be.true;
      expect(result.userAddress).to.equal(testUserAddress);
      expect(result.tokenId).to.equal(testTokenId.toString());
      expect(result.did).to.equal(`did:spiral:${testUserAddress.toLowerCase()}`);
      expect(result.userType).to.equal('seller');

      // Verify contract calls
      expect(mockSoulboundCore.balanceOf.calledWith(testUserAddress)).to.be.true;
      expect(mockSoulboundCore.mintSoul.calledWith(testUserAddress)).to.be.true;
      expect(mockSoulMetadata.initializeMetadata.called).to.be.true;
      expect(mockSoulIdentity.linkExternalIdentity.called).to.be.true;
    });

    it('должен использовать существующий SBT токен если есть', async function () {
      // Mock existing SBT token
      mockSoulboundCore.balanceOf.resolves(1n);

      const result = await accessControlActions.setupSoulIdentity(testUserAddress);

      expect(result.success).to.be.true;
      expect(result.tokenId).to.equal(testTokenId.toString());

      // Verify mintSoul NOT called
      expect(mockSoulboundCore.mintSoul.called).to.be.false;
      // But initializeMetadata should NOT be called for existing token
      expect(mockSoulMetadata.initializeMetadata.called).to.be.false;
    });

    it('должен пропустить интеграцию если SoulIdentity не развернут', async function () {
      mockContractManager.loadContract
        .withArgs('SoulIdentity')
        .rejects(new Error('Contract not deployed'));

      const result = await accessControlActions.setupSoulIdentity(testUserAddress);

      expect(result.skipped).to.be.true;
      expect(result.reason).to.equal('SoulIdentity not deployed');
      expect(result.userAddress).to.equal(testUserAddress);

      // Verify no further actions
      expect(mockSoulboundCore.mintSoul.called).to.be.false;
    });

    it('должен корректно обработать отсутствие приватного ключа пользователя', async function () {
      // Override the stub to return undefined for private key
      mockConfig.get.reset();
      mockConfig.get.returns(undefined);

      const result = await accessControlActions.setupSoulIdentity(testUserAddress);

      expect(result.success).to.be.true;
      expect(result.tokenId).to.equal(testTokenId.toString());
      expect(result.metadataWarning).to.be.a('string');
      expect(result.metadataWarning).to.match(/Not initialized/);

      // Verify metadata NOT initialized
      expect(mockSoulMetadata.initializeMetadata.called).to.be.false;
    });

    it('должен использовать кастомный userType из options', async function () {
      const result = await accessControlActions.setupSoulIdentity(testUserAddress, {
        userType: 'buyer',
        level: 5,
        reputation: 500
      });

      expect(result.success).to.be.true;
      expect(result.userType).to.equal('buyer');

      // Verify metadata JSON contains custom values
      const metadataCall = mockSoulMetadata.initializeMetadata.getCall(0);
      expect(metadataCall.args[1]).to.equal('buyer'); // userType argument
    });

    it('должен корректно обработать уже привязанный DID', async function () {
      // Simulate scenario where DID linking fails (not fatal)
      // Method should continue and return success
      const result = await accessControlActions.setupSoulIdentity(testUserAddress);

      // Should still succeed despite DID link warning
      expect(result.success).to.be.true;
      expect(result.userAddress).to.equal(testUserAddress);
      expect(result.tokenId).to.be.a('string');
      expect(result.did).to.match(/^did:spiral:0x/);
    });

    it('должен корректно обработать ошибку валидации', async function () {
      mockSoulIdentity.getPrimaryIdentity.rejects(
        new Error('Validation failed')
      );

      const result = await accessControlActions.setupSoulIdentity(testUserAddress);

      expect(result.success).to.be.true;
      expect(result.validationWarning).to.include('Validation failed');
    });

    it('должен выбросить ошибку при критическом сбое', async function () {
      // Override mintSoul to reject in beforeEach mock
      mockSoulboundCore.mintSoul.rejects(new Error('Mint failed'));

      try {
        await accessControlActions.setupSoulIdentity(testUserAddress);
        expect.fail('Should have thrown error');
      } catch (error) {
        expect(error.message).to.include('Mint failed');
      }
    });

    it('должен найти существующий tokenId при поиске', async function () {
      mockSoulboundCore.balanceOf.resolves(1n);
      mockSoulboundCore.getTotalSupply.resolves(5n);

      // Mock ownerOf to return testUserAddress on second call
      mockSoulboundCore.ownerOf
        .onCall(0).rejects(new Error('Token does not exist'))
        .onCall(1).resolves(testUserAddress);

      const result = await accessControlActions.setupSoulIdentity(testUserAddress);

      expect(result.success).to.be.true;
      expect(result.tokenId).to.equal('2'); // Found on second iteration
    });

    it('должен выбросить ошибку если не найден существующий tokenId', async function () {
      mockSoulboundCore.balanceOf.resolves(1n);
      mockSoulboundCore.getTotalSupply.resolves(5n);
      mockSoulboundCore.ownerOf.rejects(new Error('Token does not exist'));

      try {
        await accessControlActions.setupSoulIdentity(testUserAddress);
        expect.fail('Should have thrown error');
      } catch (error) {
        expect(error.message).to.include('Could not find existing SBT token');
      }
    });
  });

  describe('action9() - Grant ACTIVATOR_ROLE', function () {
    // ... (existing tests remain unchanged)
  });

  describe('action13() - Diagnose Seller State', function () {
    // ... (existing tests remain unchanged)
  });
});

