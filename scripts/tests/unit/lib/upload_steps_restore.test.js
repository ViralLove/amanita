/**
 * Unit Tests: upload_steps.js - Restoration Functions
 * 
 * Tests for restoration functions that restore CIDs from state to contract
 * 
 * Coverage:
 * - restoreSimpleFieldsToContract() - restore simple fields from state
 * - restoreComplexFieldsToContract() - restore complex fields from state
 * 
 * @version 1.0.0
 * @date 2025-11-24
 */

const { expect } = require('chai');
const sinon = require('sinon');
const uploadSteps = require('../../../lib/upload_steps');

describe('upload_steps - Restoration Functions', () => {
  let mockContext;
  let mockState;
  let mockAmanitaIntl;
  let mockSigner;
  let mockTx;
  
  beforeEach(() => {
    // Mock transaction with wait method
    mockTx = {
      wait: sinon.stub().resolves({ status: 1, blockNumber: 12345 })
    };
    
    // Mock signer
    mockSigner = {
      address: '0xSeller123'
    };
    
    // Mock AmanitaInternational contract
    mockAmanitaIntl = {
      connect: sinon.stub().returnsThis(),
      setSimpleFieldCID: sinon.stub().resolves(mockTx),
      setComplexFieldCID: sinon.stub().resolves(mockTx)
    };
    
    // Mock context
    mockContext = {
      contracts: {
        amanitaInternational: mockAmanitaIntl
      },
      seller: {
        signer: mockSigner,
        address: '0xSeller123'
      },
      biounit_id: 'amanita_muscaria',
      dryRun: false,
      arweaveOnly: false
    };
    
    // Mock state
    mockState = {
      simple_fields: {
        title: {
          cid: 'cid_title_123',
          url: 'https://arweave.net/cid_title_123',
          size: 100
        },
        dosage_types: {
          cid: 'cid_dosage_456',
          url: 'https://arweave.net/cid_dosage_456',
          size: 200
        }
      },
      complex_fields: {
        ru: {
          cid: 'cid_ru_123',
          url: 'https://arweave.net/cid_ru_123',
          size: 500
        },
        en: {
          cid: 'cid_en_456',
          url: 'https://arweave.net/cid_en_456',
          size: 600
        }
      }
    };
  });
  
  afterEach(() => {
    sinon.restore();
  });
  
  // ====================================================================
  // 🔹 restoreSimpleFieldsToContract
  // ====================================================================
  
  describe('restoreSimpleFieldsToContract', () => {
    it('should restore both fields successfully', async () => {
      const missingFields = ['title', 'dosage'];
      
      const result = await uploadSteps.restoreSimpleFieldsToContract(
        mockContext,
        mockState,
        missingFields
      );
      
      expect(result).to.deep.equal({
        title: 'cid_title_123',
        dosage: 'cid_dosage_456'
      });
      
      expect(mockAmanitaIntl.connect.calledWith(mockSigner)).to.be.true;
      expect(mockAmanitaIntl.setSimpleFieldCID.calledTwice).to.be.true;
      expect(mockAmanitaIntl.setSimpleFieldCID.calledWith(
        'ComponentDescription.title',
        'cid_title_123'
      )).to.be.true;
      expect(mockAmanitaIntl.setSimpleFieldCID.calledWith(
        'DosageInstruction.description',
        'cid_dosage_456'
      )).to.be.true;
      expect(mockTx.wait.calledTwice).to.be.true;
    });
    
    it('should restore only title when dosage is missing in state', async () => {
      const missingFields = ['title', 'dosage'];
      const stateWithOnlyTitle = {
        simple_fields: {
          title: {
            cid: 'cid_title_123'
          }
        }
      };
      
      const result = await uploadSteps.restoreSimpleFieldsToContract(
        mockContext,
        stateWithOnlyTitle,
        missingFields
      );
      
      expect(result).to.deep.equal({
        title: 'cid_title_123'
      });
      
      expect(mockAmanitaIntl.setSimpleFieldCID.calledOnce).to.be.true;
      expect(mockAmanitaIntl.setSimpleFieldCID.calledWith(
        'ComponentDescription.title',
        'cid_title_123'
      )).to.be.true;
    });
    
    it('should skip fields without CID in state', async () => {
      const missingFields = ['title', 'dosage'];
      const stateWithEmptyCid = {
        simple_fields: {
          title: {
            cid: 'cid_title_123'
          },
          dosage_types: {
            // No CID
          }
        }
      };
      
      const result = await uploadSteps.restoreSimpleFieldsToContract(
        mockContext,
        stateWithEmptyCid,
        missingFields
      );
      
      expect(result).to.deep.equal({
        title: 'cid_title_123'
      });
      
      expect(mockAmanitaIntl.setSimpleFieldCID.calledOnce).to.be.true;
    });
    
    it('should skip all operations in dry-run mode', async () => {
      mockContext.dryRun = true;
      
      const result = await uploadSteps.restoreSimpleFieldsToContract(
        mockContext,
        mockState,
        ['title', 'dosage']
      );
      
      expect(result).to.deep.equal({});
      expect(mockAmanitaIntl.setSimpleFieldCID.called).to.be.false;
    });
    
    it('should skip all operations in arweave-only mode', async () => {
      mockContext.arweaveOnly = true;
      
      const result = await uploadSteps.restoreSimpleFieldsToContract(
        mockContext,
        mockState,
        ['title', 'dosage']
      );
      
      expect(result).to.deep.equal({});
      expect(mockAmanitaIntl.setSimpleFieldCID.called).to.be.false;
    });
    
    it('should throw error for invalid context', async () => {
      try {
        await uploadSteps.restoreSimpleFieldsToContract({}, mockState, ['title']);
        expect.fail('Should have thrown error');
      } catch (error) {
        expect(error.message).to.equal('Invalid context: contracts.amanitaInternational is required');
      }
      
      try {
        await uploadSteps.restoreSimpleFieldsToContract(
          { contracts: { amanitaInternational: mockAmanitaIntl } },
          mockState,
          ['title']
        );
        expect.fail('Should have thrown error');
      } catch (error) {
        expect(error.message).to.equal('Invalid context: seller.signer is required');
      }
    });
    
    it('should throw error for missing state', async () => {
      try {
        await uploadSteps.restoreSimpleFieldsToContract(mockContext, null, ['title']);
        expect.fail('Should have thrown error');
      } catch (error) {
        expect(error.message).to.equal('State object is required');
      }
    });
    
    it('should throw error for invalid missingFields', async () => {
      try {
        await uploadSteps.restoreSimpleFieldsToContract(mockContext, mockState, 'not-an-array');
        expect.fail('Should have thrown error');
      } catch (error) {
        expect(error.message).to.equal('missingFields must be an array');
      }
    });
    
    it('should throw error if contract call fails', async () => {
      mockAmanitaIntl.setSimpleFieldCID.rejects(new Error('Contract error'));
      
      try {
        await uploadSteps.restoreSimpleFieldsToContract(mockContext, mockState, ['title']);
        expect.fail('Should have thrown error');
      } catch (error) {
        expect(error.message).to.equal('Contract error');
      }
    });
  });
  
  // ====================================================================
  // 🔹 restoreComplexFieldsToContract
  // ====================================================================
  
  describe('restoreComplexFieldsToContract', () => {
    it('should restore all languages successfully', async () => {
      const missingLanguages = ['ru', 'en'];
      
      const result = await uploadSteps.restoreComplexFieldsToContract(
        mockContext,
        mockState,
        missingLanguages
      );
      
      expect(result).to.deep.equal({
        ru: 'cid_ru_123',
        en: 'cid_en_456'
      });
      
      expect(mockAmanitaIntl.connect.calledWith(mockSigner)).to.be.true;
      expect(mockAmanitaIntl.setComplexFieldCID.calledTwice).to.be.true;
      expect(mockAmanitaIntl.setComplexFieldCID.calledWith(
        'ComponentDescription.amanita_muscaria',
        'ru',
        'cid_ru_123'
      )).to.be.true;
      expect(mockAmanitaIntl.setComplexFieldCID.calledWith(
        'ComponentDescription.amanita_muscaria',
        'en',
        'cid_en_456'
      )).to.be.true;
      expect(mockTx.wait.calledTwice).to.be.true;
    });
    
    it('should handle string CID format', async () => {
      const stateWithStringCid = {
        complex_fields: {
          ru: 'cid_ru_string'
        }
      };
      
      const result = await uploadSteps.restoreComplexFieldsToContract(
        mockContext,
        stateWithStringCid,
        ['ru']
      );
      
      expect(result).to.deep.equal({
        ru: 'cid_ru_string'
      });
      
      expect(mockAmanitaIntl.setComplexFieldCID.calledWith(
        'ComponentDescription.amanita_muscaria',
        'ru',
        'cid_ru_string'
      )).to.be.true;
    });
    
    it('should skip languages missing in state', async () => {
      const stateWithOnlyRu = {
        complex_fields: {
          ru: {
            cid: 'cid_ru_123'
          }
        }
      };
      
      const result = await uploadSteps.restoreComplexFieldsToContract(
        mockContext,
        stateWithOnlyRu,
        ['ru', 'en']
      );
      
      expect(result).to.deep.equal({
        ru: 'cid_ru_123'
      });
      
      expect(mockAmanitaIntl.setComplexFieldCID.calledOnce).to.be.true;
      expect(mockAmanitaIntl.setComplexFieldCID.calledWith(
        'ComponentDescription.amanita_muscaria',
        'ru',
        'cid_ru_123'
      )).to.be.true;
    });
    
    it('should skip languages with invalid CID', async () => {
      const stateWithInvalidCid = {
        complex_fields: {
          ru: {
            cid: 'cid_ru_123'
          },
          en: {
            // No CID
          }
        }
      };
      
      const result = await uploadSteps.restoreComplexFieldsToContract(
        mockContext,
        stateWithInvalidCid,
        ['ru', 'en']
      );
      
      expect(result).to.deep.equal({
        ru: 'cid_ru_123'
      });
      
      expect(mockAmanitaIntl.setComplexFieldCID.calledOnce).to.be.true;
    });
    
    it('should skip all operations in dry-run mode', async () => {
      mockContext.dryRun = true;
      
      const result = await uploadSteps.restoreComplexFieldsToContract(
        mockContext,
        mockState,
        ['ru', 'en']
      );
      
      expect(result).to.deep.equal({});
      expect(mockAmanitaIntl.setComplexFieldCID.called).to.be.false;
    });
    
    it('should skip all operations in arweave-only mode', async () => {
      mockContext.arweaveOnly = true;
      
      const result = await uploadSteps.restoreComplexFieldsToContract(
        mockContext,
        mockState,
        ['ru', 'en']
      );
      
      expect(result).to.deep.equal({});
      expect(mockAmanitaIntl.setComplexFieldCID.called).to.be.false;
    });
    
    it('should throw error for invalid context', async () => {
      try {
        await uploadSteps.restoreComplexFieldsToContract({}, mockState, ['ru']);
        expect.fail('Should have thrown error');
      } catch (error) {
        expect(error.message).to.equal('Invalid context: contracts.amanitaInternational is required');
      }
      
      try {
        await uploadSteps.restoreComplexFieldsToContract(
          { contracts: { amanitaInternational: mockAmanitaIntl } },
          mockState,
          ['ru']
        );
        expect.fail('Should have thrown error');
      } catch (error) {
        expect(error.message).to.equal('Invalid context: seller.signer is required');
      }
      
      try {
        await uploadSteps.restoreComplexFieldsToContract(
          {
            contracts: { amanitaInternational: mockAmanitaIntl },
            seller: { signer: mockSigner }
          },
          mockState,
          ['ru']
        );
        expect.fail('Should have thrown error');
      } catch (error) {
        expect(error.message).to.equal('Invalid context: biounit_id is required');
      }
    });
    
    it('should throw error for missing state', async () => {
      try {
        await uploadSteps.restoreComplexFieldsToContract(mockContext, null, ['ru']);
        expect.fail('Should have thrown error');
      } catch (error) {
        expect(error.message).to.equal('State object is required');
      }
    });
    
    it('should throw error for invalid missingLanguages', async () => {
      try {
        await uploadSteps.restoreComplexFieldsToContract(mockContext, mockState, 'not-an-array');
        expect.fail('Should have thrown error');
      } catch (error) {
        expect(error.message).to.equal('missingLanguages must be an array');
      }
    });
    
    it('should use biounit_id in className', async () => {
      mockContext.biounit_id = 'test_component';
      
      await uploadSteps.restoreComplexFieldsToContract(
        mockContext,
        mockState,
        ['ru']
      );
      
      expect(mockAmanitaIntl.setComplexFieldCID.calledWith(
        'ComponentDescription.test_component',
        'ru',
        'cid_ru_123'
      )).to.be.true;
    });
    
    it('should throw error if contract call fails', async () => {
      mockAmanitaIntl.setComplexFieldCID.rejects(new Error('Contract error'));
      
      try {
        await uploadSteps.restoreComplexFieldsToContract(mockContext, mockState, ['ru']);
        expect.fail('Should have thrown error');
      } catch (error) {
        expect(error.message).to.equal('Contract error');
      }
    });
  });
});

