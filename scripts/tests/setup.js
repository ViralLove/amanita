/**
 * Global Test Setup
 * 
 * This file is executed before all tests to set up the global test environment.
 */

// Configure Chai plugins
const chai = require('chai');
const chaiAsPromised = require('chai-as-promised');

chai.use(chaiAsPromised);

// Suppress console output during tests (optional)
if (process.env.SUPPRESS_LOGS === 'true') {
  global.console = {
    ...console,
    log: jest.fn(),
    debug: jest.fn(),
    info: jest.fn(),
    warn: jest.fn(),
    // Keep error for debugging
    error: console.error,
  };
}

// Set test environment variables
process.env.NODE_ENV = 'test';

// Increase timeout for async tests
if (typeof jest !== 'undefined') {
  jest.setTimeout(30000); // 30 seconds
}

console.log('✅ Test environment initialized');

