/**
 * Assertion Helpers
 * 
 * Custom assertion utilities for tests.
 */

const { expect } = require('chai');

const assertionHelpers = {
  /**
   * Assert valid Ethereum address
   * @param {string} address - Address to validate
   */
  assertValidAddress(address) {
    expect(address).to.match(/^0x[a-fA-F0-9]{40}$/, 'Invalid Ethereum address format');
  },

  /**
   * Assert valid IPFS CID
   * @param {string} cid - CID to validate
   */
  assertValidCID(cid) {
    expect(cid).to.match(/^Qm[a-zA-Z0-9]{44}$/, 'Invalid IPFS CID format');
  },

  /**
   * Assert valid transaction hash
   * @param {string} txHash - Transaction hash to validate
   */
  assertValidTxHash(txHash) {
    expect(txHash).to.match(/^0x[a-fA-F0-9]{64}$/, 'Invalid transaction hash format');
  },

  /**
   * Assert object has required properties
   * @param {Object} obj - Object to check
   * @param {Array<string>} properties - Required property names
   */
  assertHasProperties(obj, properties) {
    properties.forEach(prop => {
      expect(obj).to.have.property(prop, `Missing required property: ${prop}`);
    });
  },

  /**
   * Assert array has minimum length
   * @param {Array} arr - Array to check
   * @param {number} minLength - Minimum length
   */
  assertMinLength(arr, minLength) {
    expect(arr).to.be.an('array');
    expect(arr.length).to.be.at.least(minLength, `Array length ${arr.length} is less than minimum ${minLength}`);
  },

  /**
   * Assert execution time is within limit
   * @param {Function} fn - Function to execute
   * @param {number} maxMs - Maximum execution time in milliseconds
   */
  async assertExecutionTime(fn, maxMs) {
    const startTime = Date.now();
    await fn();
    const duration = Date.now() - startTime;
    expect(duration).to.be.lessThan(maxMs, `Execution time ${duration}ms exceeded limit ${maxMs}ms`);
  },

  /**
   * Assert function throws specific error
   * @param {Function} fn - Function to execute
   * @param {string|RegExp} errorMatch - Expected error message or pattern
   */
  async assertThrowsError(fn, errorMatch) {
    try {
      await fn();
      throw new Error('Expected function to throw an error, but it did not');
    } catch (error) {
      if (typeof errorMatch === 'string') {
        expect(error.message).to.include(errorMatch);
      } else {
        expect(error.message).to.match(errorMatch);
      }
    }
  },

  /**
   * Assert array contains item matching predicate
   * @param {Array} arr - Array to search
   * @param {Function} predicate - Predicate function
   */
  assertArrayContains(arr, predicate) {
    expect(arr).to.be.an('array');
    const found = arr.some(predicate);
    expect(found).to.be.true;
  },

  /**
   * Assert two objects are deeply equal
   * @param {Object} actual - Actual object
   * @param {Object} expected - Expected object
   */
  assertDeepEqual(actual, expected) {
    expect(actual).to.deep.equal(expected);
  },

  /**
   * Assert file exists
   * @param {string} filePath - Path to file
   */
  assertFileExists(filePath) {
    const fs = require('fs');
    expect(fs.existsSync(filePath)).to.be.true;
  },

  /**
   * Assert JSON file has valid structure
   * @param {string} filePath - Path to JSON file
   * @param {Object} expectedStructure - Expected structure (keys)
   */
  assertJSONStructure(filePath, expectedStructure) {
    const fs = require('fs');
    expect(fs.existsSync(filePath)).to.be.true;
    
    const content = JSON.parse(fs.readFileSync(filePath, 'utf8'));
    Object.keys(expectedStructure).forEach(key => {
      expect(content).to.have.property(key);
    });
  }
};

module.exports = assertionHelpers;

