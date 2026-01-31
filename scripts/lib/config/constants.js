/**
 * Constants and Configuration Mappings
 * 
 * This module contains all constant values and mappings used throughout
 * the deploy_full.js script, centralizing magic numbers and string constants.
 */

// Contract environment variable mapping
const CONTRACT_ENV_MAPPING = {
  'MagicRegistry': 'MAGIC_REGISTRY_CONTRACT_ADDRESS',
  'SpiralEngine': 'SPIRAL_ENGINE_CONTRACT_ADDRESS', 
  'ProductRegistry': 'PRODUCT_REGISTRY_CONTRACT_ADDRESS',
  'ActivityRegistry': 'ACTIVITY_REGISTRY_CONTRACT_ADDRESS',
  'SoulIdentity': 'SOUL_IDENTITY_CONTRACT_ADDRESS',
  'OrganicComponentRegistry': 'ORGANIC_COMPONENT_REGISTRY_PROXY',
  'AmanitaInternational': 'AMANITA_INTERNATIONAL_PROXY'
};

// Supported contract types
const SUPPORTED_CONTRACTS = [
  'MagicRegistry',
  'SpiralEngine', 
  'ProductRegistry',
  'ActivityRegistry',
  'SoulIdentity',
  'OrganicComponentRegistry',
  'AmanitaInternational'
];

// Role constants
const ROLES = {
  ADMIN_ROLE: '0x0000000000000000000000000000000000000000000000000000000000000000',
  UPGRADER_ROLE: '0x189ab7a9244df0848122154315af71fe140f3db0fe014031783b0946b8c9d2e3',
  SELLER_ROLE: '0x9f2df0fed2c77648de5860a4cc508cd0818c85b8b8a1ab4ceeef8d981c8956a6',
  ACTIVATOR_ROLE: '0x0000000000000000000000000000000000000000000000000000000000000001'
};

// Processing constants
const PROCESSING = {
  BATCH_SIZE: 5,
  MAX_RETRIES: 3,
  TIMEOUT_MS: 30000,
  GAS_LIMIT: 5000000,
  GAS_PRICE: '20000000000' // 20 gwei
};

// File and path constants
const PATHS = {
  ARTIFACTS_BASE: '../artifacts/contracts',
  DATA_BASE: 'data',
  SELLERS_BASE: 'data/sellers',
  COMPONENTS_BASE: 'data/components',
  LOGS_BASE: 'logs'
};

// Action constants
const ACTIONS = {
  DEPLOY: 1,
  INITIALIZE: 2,
  ACTIVATE_SELLER: 3,
  CREATE_CATALOG: 4,
  UPLOAD_COMPONENTS: 555,
  FULL_PIPELINE: 888
};

// Arweave constants
const ARWEAVE = {
  // Gateway configuration
  GATEWAY: {
    DEFAULT: 'arweave.net',           // Official gateway (no protocol)
    ALTERNATIVES: [
      'arweave.net',                  // Official
      'arweave.dev',                  // Development
      'ar-io.net',                    // AR.IO network
      'g8way.io'                      // Alternative gateway
    ],
    PORT: 443,
    PROTOCOL: 'https'
  },
  
  // Timeouts (milliseconds)
  TIMEOUT: 60000,                     // 60 seconds default
  UPLOAD_TIMEOUT: 120000,             // 2 minutes for large files
  CONNECTION_TIMEOUT: 10000,          // 10 seconds for health check
  
  // Retry configuration
  RETRY: {
    MAX_ATTEMPTS: 3,
    BACKOFF_MS: 1000,
    BACKOFF_MULTIPLIER: 2
  },
  
  // Key configuration
  KEY_PATH: {
    DEFAULT: '.arweave-key.json',
    ENV_VAR: 'ARWEAVE_KEY_PATH'
  }
};

// Logging constants
const LOGGING = {
  LEVELS: {
    DEBUG: 0,
    INFO: 1,
    WARN: 2,
    ERROR: 3
  },
  COLORS: {
    DEBUG: '\x1b[36m', // Cyan
    INFO: '\x1b[32m',  // Green
    WARN: '\x1b[33m',  // Yellow
    ERROR: '\x1b[31m', // Red
    RESET: '\x1b[0m'   // Reset
  }
};

// Error messages
const ERROR_MESSAGES = {
  CONTRACT_NOT_FOUND: 'Contract not found in environment variables',
  INVALID_PRIVATE_KEY: 'Invalid private key format',
  MISSING_REQUIRED_CONFIG: 'Missing required configuration',
  CONTRACT_LOAD_FAILED: 'Failed to load contract',
  TRANSACTION_FAILED: 'Transaction failed',
  VALIDATION_FAILED: 'Validation failed'
};

// Success messages
const SUCCESS_MESSAGES = {
  CONTRACT_LOADED: 'Contract loaded successfully',
  TRANSACTION_SUCCESS: 'Transaction completed successfully',
  VALIDATION_PASSED: 'Validation passed',
  CONFIG_LOADED: 'Configuration loaded successfully'
};

module.exports = {
  CONTRACT_ENV_MAPPING,
  SUPPORTED_CONTRACTS,
  ROLES,
  PROCESSING,
  PATHS,
  ACTIONS,
  ARWEAVE,
  LOGGING,
  ERROR_MESSAGES,
  SUCCESS_MESSAGES
};
