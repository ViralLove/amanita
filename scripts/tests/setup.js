/**
 * Global Test Setup
 * 
 * This file is executed before all tests to set up the global test environment.
 */

// Configure Chai plugins
const chai = require('chai');
let chaiAsPromised;
try {
  chaiAsPromised = require('chai-as-promised');
  // Handle both CommonJS and ES module exports
  if (typeof chaiAsPromised === 'function') {
chai.use(chaiAsPromised);
  } else if (chaiAsPromised && typeof chaiAsPromised.default === 'function') {
    chai.use(chaiAsPromised.default);
  } else if (chaiAsPromised && chaiAsPromised.default) {
    chai.use(chaiAsPromised.default);
  }
} catch (error) {
  // chai-as-promised not available, skip
  console.warn('chai-as-promised not available, skipping plugin setup');
}

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

