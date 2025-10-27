/**
 * Test Harness
 * 
 * Provides setup and teardown utilities for tests.
 */

const path = require('path');
const fs = require('fs');

class TestHarness {
  constructor() {
    this.originalEnv = { ...process.env };
  }

  /**
   * Setup test environment
   */
  async setupTestEnvironment() {
    // Load test environment variables
    const testEnvPath = path.join(__dirname, '../fixtures/env/test.env');
    if (fs.existsSync(testEnvPath)) {
      const envContent = fs.readFileSync(testEnvPath, 'utf8');
      envContent.split('\n').forEach(line => {
        if (line && !line.startsWith('#')) {
          const [key, value] = line.split('=');
          if (key && value) {
            process.env[key.trim()] = value.trim();
          }
        }
      });
    }
  }

  /**
   * Teardown test environment
   */
  async teardownTestEnvironment() {
    // Restore original environment
    process.env = { ...this.originalEnv };
  }

  /**
   * Create mock config with overrides
   * @param {Object} overrides - Configuration overrides
   * @returns {Object} - Mock config object
   */
  createMockConfig(overrides = {}) {
    const defaultConfig = {
      config: {
        deployer: {
          privateKey: '0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef'
        },
        seller: {
          address: '0x70997970C51812dc3A010C7d01b50e0d17dc79C8',
          privateKey: '0xabcdefabcdefabcdefabcdefabcdefabcdefabcdefabcdefabcdefabcdefabcd',
          businessId: 'test_seller',
          id: 'test_seller_001'
        },
        contracts: {
          magicRegistry: null,
          spiralEngine: null,
          productRegistry: null,
          organicComponentRegistry: null,
          amanitaInternational: null,
          soulIdentity: null
        },
        paths: {
          csvBase: 'scripts/tests/fixtures/csv',
          outputBase: 'scripts/tests/fixtures/output',
          csvPath: 'scripts/tests/fixtures/csv/test_seller/catalog',
          outputPath: 'scripts/tests/fixtures/output/test_seller/products'
        },
        features: {
          arweave: false,
          quick: true
        },
        network: {
          name: 'localhost',
          rpcUrl: 'http://localhost:8545'
        }
      },
      
      // Helper methods like real config
      get: function(key) {
        const keys = key.split('.');
        let value = this.config;
        for (const k of keys) {
          value = value?.[k];
        }
        return value;
      },
      
      getWithDefault: function(key, defaultValue) {
        const value = this.get(key);
        return value !== undefined ? value : defaultValue;
      },
      
      getContractAddress: function(contractName) {
        const contractKey = contractName.toLowerCase().replace(/_/g, '');
        return this.get(`contracts.${contractKey}`);
      },
      
      getSellerConfig: function() {
        return this.config.seller;
      },
      
      getDeployerConfig: function() {
        return this.config.deployer;
      }
    };

    return this.deepMerge(defaultConfig, overrides);
  }

  /**
   * Deep merge objects
   * @param {Object} target - Target object
   * @param {Object} source - Source object
   * @returns {Object} - Merged object
   */
  deepMerge(target, source) {
    const output = { ...target };
    for (const key in source) {
      if (source[key] && typeof source[key] === 'object' && !Array.isArray(source[key]) && key in target && typeof target[key] === 'object') {
        output[key] = this.deepMerge(target[key], source[key]);
      } else {
        output[key] = source[key];
      }
    }
    return output;
  }

  /**
   * Load fixture file
   * @param {string} fixturePath - Path to fixture file (relative to fixtures/)
   * @returns {Object|string} - Fixture data
   */
  loadFixture(fixturePath) {
    const fullPath = path.join(__dirname, '../fixtures', fixturePath);
    if (!fs.existsSync(fullPath)) {
      throw new Error(`Fixture not found: ${fixturePath}`);
    }

    const content = fs.readFileSync(fullPath, 'utf8');
    
    // Try to parse as JSON
    try {
      return JSON.parse(content);
    } catch {
      return content;
    }
  }

  /**
   * Create temporary directory for test
   * @param {string} dirName - Directory name
   * @returns {string} - Full path to created directory
   */
  createTempDir(dirName) {
    const tempPath = path.join(__dirname, '../fixtures/temp', dirName);
    if (!fs.existsSync(tempPath)) {
      fs.mkdirSync(tempPath, { recursive: true });
    }
    return tempPath;
  }

  /**
   * Clean up temporary directories
   */
  cleanupTempDirs() {
    const tempPath = path.join(__dirname, '../fixtures/temp');
    if (fs.existsSync(tempPath)) {
      fs.rmSync(tempPath, { recursive: true, force: true });
    }
  }
}

module.exports = TestHarness;

