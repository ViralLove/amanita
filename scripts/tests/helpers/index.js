/**
 * Test Helpers Index
 * 
 * Centralized export of all test helpers.
 */

const TestHarness = require('./TestHarness');
const MockContractManager = require('./MockContractManager');
const MockArweaveManager = require('./MockArweaveManager');
const MockWeb3 = require('./MockWeb3');
const assertionHelpers = require('./AssertionHelpers');
const IntegrationHarness = require('./IntegrationHarness');
const E2EHarness = require('./E2EHarness'); // NEW

module.exports = {
  TestHarness,
  MockContractManager,
  MockArweaveManager,
  MockWeb3,
  IntegrationHarness,
  E2EHarness, // NEW
  ...assertionHelpers
};

