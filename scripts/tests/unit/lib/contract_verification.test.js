/**
 * Unit Tests: contract_verification.js
 * 
 * Tests for contract verification utilities
 * 
 * Coverage:
 * - verifyStepCompletion() - unified step verification
 * - checkSimpleFieldsInContract() - simple fields contract check
 * - checkComplexFieldsInContract() - complex fields contract check
 * - getStateDataForStep() - state data extraction
 * 
 * @version 1.0.0
 * @date 2025-11-24
 */

const { expect } = require('chai');
const sinon = require('sinon');
const { ethers } = require('hardhat');

describe('contract_verification', () => {
  let contractVerification;
  let stateManagerModule;
  let uploadUtilsModule;
  
  // Mocks
  let mockAmanitaIntl;
  let mockContext;
  
  before(() => {
    // Load module (will use actual dependencies)
    contractVerification = require('../../../lib/contract_verification');
    
    // Load dependencies for potential stubbing if needed
    stateManagerModule = require('../../../lib/state_manager');
    uploadUtilsModule = require('../../../lib/upload_utils');
  });
  
  beforeEach(() => {
    // Mock AmanitaInternational contract
    mockAmanitaIntl = {
      getSimpleFieldCID: sinon.stub(),
      getComplexFieldCID: sinon.stub()
    };
    
    mockContext = {
      contracts: {
        amanitaInternational: mockAmanitaIntl
      },
      biounit_id: 'amanita_muscaria',
      supportedLanguages: ['ru', 'en', 'de']
    };
  });
  
  afterEach(() => {
    sinon.restore();
  });
  
  // ====================================================================
  // 🔹 verifyStepCompletion
  // ====================================================================
  
  describe('verifyStepCompletion', () => {
    it('should return incomplete when step not completed in state', async () => {
      const result = await contractVerification.verifyStepCompletion({
        state: { steps_completed: [] },
        stepName: 'simple_fields_uploaded',
        contractCheckFn: async () => ({ allPresent: true, missing: [] })
      });
      
      expect(result).to.deep.equal({
        isComplete: false,
        isConsistent: true,
        missingItems: [],
        stateData: null
      });
    });
    
    it('should return complete and consistent when contract check passes', async () => {
      const mockState = {
        steps_completed: ['simple_fields_uploaded'],
        simple_fields: { title: { cid: 'cid123' }, dosage_types: { cid: 'cid456' } }
      };
      
      const result = await contractVerification.verifyStepCompletion({
        state: mockState,
        stepName: 'simple_fields_uploaded',
        contractCheckFn: async () => ({ allPresent: true, missing: [] })
      });
      
      expect(result).to.deep.equal({
        isComplete: true,
        isConsistent: true,
        missingItems: [],
        stateData: mockState.simple_fields
      });
    });
    
    it('should return complete but inconsistent when contract check finds missing items', async () => {
      const mockState = {
        steps_completed: ['simple_fields_uploaded'],
        simple_fields: { title: { cid: 'cid123' } }
      };
      
      const result = await contractVerification.verifyStepCompletion({
        state: mockState,
        stepName: 'simple_fields_uploaded',
        contractCheckFn: async () => ({ allPresent: false, missing: ['dosage'] })
      });
      
      expect(result).to.deep.equal({
        isComplete: true,
        isConsistent: false,
        missingItems: ['dosage'],
        stateData: mockState.simple_fields
      });
    });
    
    it('should handle contract check errors gracefully', async () => {
      const mockState = {
        steps_completed: ['simple_fields_uploaded'],
        simple_fields: { title: { cid: 'cid123' } }
      };
      
      const result = await contractVerification.verifyStepCompletion({
        state: mockState,
        stepName: 'simple_fields_uploaded',
        contractCheckFn: async () => {
          throw new Error('Contract error');
        }
      });
      
      expect(result).to.deep.equal({
        isComplete: true,
        isConsistent: false,
        missingItems: ['*'],
        stateData: mockState.simple_fields
      });
    });
    
    it('should throw error for invalid input', async () => {
      try {
        await contractVerification.verifyStepCompletion({});
        expect.fail('Should have thrown error');
      } catch (error) {
        expect(error.message).to.equal('State object is required');
      }
      
      try {
        await contractVerification.verifyStepCompletion({ state: {} });
        expect.fail('Should have thrown error');
      } catch (error) {
        expect(error.message).to.equal('Step name is required');
      }
      
      try {
        await contractVerification.verifyStepCompletion({ state: {}, stepName: 'test' });
        expect.fail('Should have thrown error');
      } catch (error) {
        expect(error.message).to.equal('contractCheckFn must be an async function');
      }
    });
  });
  
  // ====================================================================
  // 🔹 checkSimpleFieldsInContract
  // ====================================================================
  
  describe('checkSimpleFieldsInContract', () => {
    it('should return all present when both fields exist in contract', async () => {
      mockAmanitaIntl.getSimpleFieldCID
        .withArgs('ComponentDescription.title').resolves('cid_title_123')
        .withArgs('DosageInstruction.description').resolves('cid_dosage_456');
      
      const result = await contractVerification.checkSimpleFieldsInContract(mockContext);
      
      expect(result).to.deep.equal({
        allPresent: true,
        missing: [],
        present: {
          title: 'cid_title_123',
          dosage: 'cid_dosage_456'
        }
      });
    });
    
    it('should return missing when one field is absent', async () => {
      mockAmanitaIntl.getSimpleFieldCID
        .withArgs('ComponentDescription.title').resolves('cid_title_123')
        .withArgs('DosageInstruction.description').resolves('');
      
      const result = await contractVerification.checkSimpleFieldsInContract(mockContext);
      
      expect(result).to.deep.equal({
        allPresent: false,
        missing: ['dosage'],
        present: {
          title: 'cid_title_123'
        }
      });
    });
    
    it('should handle ZeroAddress as missing', async () => {
      mockAmanitaIntl.getSimpleFieldCID
        .withArgs('ComponentDescription.title').resolves(ethers.ZeroAddress)
        .withArgs('DosageInstruction.description').resolves('cid_dosage_456');
      
      const result = await contractVerification.checkSimpleFieldsInContract(mockContext);
      
      expect(result).to.deep.equal({
        allPresent: false,
        missing: ['title'],
        present: {
          dosage: 'cid_dosage_456'
        }
      });
    });
    
    it('should handle contract errors gracefully', async () => {
      mockAmanitaIntl.getSimpleFieldCID
        .withArgs('ComponentDescription.title').rejects(new Error('Network error'))
        .withArgs('DosageInstruction.description').resolves('cid_dosage_456');
      
      const result = await contractVerification.checkSimpleFieldsInContract(mockContext);
      
      expect(result).to.deep.equal({
        allPresent: false,
        missing: ['title'],
        present: {
          dosage: 'cid_dosage_456'
        }
      });
    });
    
    it('should throw error for invalid context', async () => {
      try {
        await contractVerification.checkSimpleFieldsInContract({});
        expect.fail('Should have thrown error');
      } catch (error) {
        expect(error.message).to.equal('Invalid context: contracts.amanitaInternational is required');
      }
      
      try {
        await contractVerification.checkSimpleFieldsInContract({ contracts: {} });
        expect.fail('Should have thrown error');
      } catch (error) {
        expect(error.message).to.equal('Invalid context: contracts.amanitaInternational is required');
      }
    });
  });
  
  // ====================================================================
  // 🔹 checkComplexFieldsInContract
  // ====================================================================
  
  describe('checkComplexFieldsInContract', () => {
    it('should return all present when all languages exist in contract', async () => {
      mockAmanitaIntl.getComplexFieldCID
        .withArgs('ComponentDescription.amanita_muscaria', 'ru').resolves('cid_ru_123')
        .withArgs('ComponentDescription.amanita_muscaria', 'en').resolves('cid_en_456')
        .withArgs('ComponentDescription.amanita_muscaria', 'de').resolves('cid_de_789');
      
      const result = await contractVerification.checkComplexFieldsInContract(mockContext);
      
      expect(result).to.deep.equal({
        allPresent: true,
        missing: [],
        present: {
          ru: 'cid_ru_123',
          en: 'cid_en_456',
          de: 'cid_de_789'
        }
      });
    });
    
    it('should use supportedLanguages from context', async () => {
      mockAmanitaIntl.getComplexFieldCID.resolves('cid123');
      
      await contractVerification.checkComplexFieldsInContract(mockContext);
      
      expect(mockAmanitaIntl.getComplexFieldCID.calledWith(
        'ComponentDescription.amanita_muscaria',
        'ru'
      )).to.be.true;
      expect(mockAmanitaIntl.getComplexFieldCID.calledWith(
        'ComponentDescription.amanita_muscaria',
        'en'
      )).to.be.true;
      expect(mockAmanitaIntl.getComplexFieldCID.calledWith(
        'ComponentDescription.amanita_muscaria',
        'de'
      )).to.be.true;
      expect(mockAmanitaIntl.getComplexFieldCID.callCount).to.equal(3);
    });
    
    it('should fallback to utils.getSupportedLanguages when supportedLanguages not provided', async () => {
      const contextWithoutLanguages = {
        contracts: { amanitaInternational: mockAmanitaIntl },
        biounit_id: 'amanita_muscaria'
      };
      
      // Mock getSupportedLanguages to return test languages
      sinon.stub(uploadUtilsModule, 'getSupportedLanguages').returns(['ru', 'en']);
      
      mockAmanitaIntl.getComplexFieldCID.resolves('cid123');
      
      await contractVerification.checkComplexFieldsInContract(contextWithoutLanguages);
      
      expect(uploadUtilsModule.getSupportedLanguages.called).to.be.true;
      expect(mockAmanitaIntl.getComplexFieldCID.calledWith(
        'ComponentDescription.amanita_muscaria',
        'ru'
      )).to.be.true;
      expect(mockAmanitaIntl.getComplexFieldCID.calledWith(
        'ComponentDescription.amanita_muscaria',
        'en'
      )).to.be.true;
      
      uploadUtilsModule.getSupportedLanguages.restore();
    });
    
    it('should return missing when some languages are absent', async () => {
      mockAmanitaIntl.getComplexFieldCID
        .withArgs('ComponentDescription.amanita_muscaria', 'ru').resolves('cid_ru_123')
        .withArgs('ComponentDescription.amanita_muscaria', 'en').resolves('')
        .withArgs('ComponentDescription.amanita_muscaria', 'de').resolves('cid_de_789');
      
      const result = await contractVerification.checkComplexFieldsInContract(mockContext);
      
      expect(result).to.deep.equal({
        allPresent: false,
        missing: ['en'],
        present: {
          ru: 'cid_ru_123',
          de: 'cid_de_789'
        }
      });
    });
    
    it('should include biounit_id in className', async () => {
      mockAmanitaIntl.getComplexFieldCID.resolves('cid123');
      
      await contractVerification.checkComplexFieldsInContract(mockContext);
      
      expect(mockAmanitaIntl.getComplexFieldCID.calledWith(
        'ComponentDescription.amanita_muscaria',
        sinon.match.string
      )).to.be.true;
    });
    
    it('should throw error for invalid context', async () => {
      try {
        await contractVerification.checkComplexFieldsInContract({});
        expect.fail('Should have thrown error');
      } catch (error) {
        expect(error.message).to.equal('Invalid context: contracts.amanitaInternational is required');
      }
      
      try {
        await contractVerification.checkComplexFieldsInContract({
          contracts: { amanitaInternational: mockAmanitaIntl }
        });
        expect.fail('Should have thrown error');
      } catch (error) {
        expect(error.message).to.equal('Invalid context: biounit_id is required');
      }
    });
  });
  
  // ====================================================================
  // 🔹 getStateDataForStep
  // ====================================================================
  
  describe('getStateDataForStep', () => {
    it('should return simple_fields for simple_fields_uploaded step', () => {
      const state = {
        simple_fields: {
          title: { cid: 'cid1' },
          dosage_types: { cid: 'cid2' }
        }
      };
      
      const result = contractVerification.getStateDataForStep(state, 'simple_fields_uploaded');
      
      expect(result).to.deep.equal(state.simple_fields);
    });
    
    it('should return complex_fields for complex_fields_uploaded step', () => {
      const state = {
        complex_fields: {
          ru: { cid: 'cid_ru' },
          en: { cid: 'cid_en' }
        }
      };
      
      const result = contractVerification.getStateDataForStep(state, 'complex_fields_uploaded');
      
      expect(result).to.deep.equal(state.complex_fields);
    });
    
    it('should return root_metadata.cid for root_metadata_uploaded step', () => {
      const state = {
        root_metadata: {
          cid: 'root_cid_123'
        }
      };
      
      const result = contractVerification.getStateDataForStep(state, 'root_metadata_uploaded');
      
      expect(result).to.equal('root_cid_123');
    });
    
    it('should return null for unknown step', () => {
      const state = {
        some_data: 'value'
      };
      
      const result = contractVerification.getStateDataForStep(state, 'unknown_step');
      
      expect(result).to.be.null;
    });
    
    it('should return null when state is null', () => {
      const result = contractVerification.getStateDataForStep(null, 'simple_fields_uploaded');
      
      expect(result).to.be.null;
    });
    
    it('should return null when field is missing in state', () => {
      const state = {};
      
      const result = contractVerification.getStateDataForStep(state, 'simple_fields_uploaded');
      
      expect(result).to.be.null;
    });
    
    it('should return null when root_metadata exists but cid is missing', () => {
      const state = {
        root_metadata: {}
      };
      
      const result = contractVerification.getStateDataForStep(state, 'root_metadata_uploaded');
      
      expect(result).to.be.null;
    });
  });
});

