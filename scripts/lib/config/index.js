/**
 * Centralized Configuration Manager
 * 
 * This module provides a single source of truth for all environment variables
 * used in the deploy_full.js script, eliminating duplication and providing
 * validation with sensible defaults.
 * 
 * Based on analysis of 44 process.env usages in deploy_full.js
 */

require('dotenv').config();

const { ARWEAVE } = require('./constants');

// Simple validation function
const validateEnv = () => {
  const errors = [];
  
  // Required variables
  if (!process.env.DEPLOYER_PRIVATE_KEY) {
    errors.push('DEPLOYER_PRIVATE_KEY is required');
  }
  
  if (errors.length > 0) {
    console.error('❌ Configuration validation failed:');
    errors.forEach(error => console.error(`  - ${error}`));
    process.exit(1);
  }
  
  return process.env;
};

// Validate environment variables
const validatedEnv = validateEnv();

// Configuration object with validated values
const config = {
  // Deployment
  deployer: {
    privateKey: validatedEnv.DEPLOYER_PRIVATE_KEY.startsWith('0x') 
      ? validatedEnv.DEPLOYER_PRIVATE_KEY 
      : `0x${validatedEnv.DEPLOYER_PRIVATE_KEY}`,
    address: validatedEnv.DEPLOYER_ADDRESS || '0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266'  // ✅ FIX: Add deployer address
  },
  
  // Seller
  seller: {
    address: validatedEnv.SELLER_ADDRESS,
    privateKey: validatedEnv.SELLER_PRIVATE_KEY 
      ? (validatedEnv.SELLER_PRIVATE_KEY.startsWith('0x') 
          ? validatedEnv.SELLER_PRIVATE_KEY 
          : `0x${validatedEnv.SELLER_PRIVATE_KEY}`)
      : null,
    businessId: validatedEnv.SELLER_BUSINESS_ID || 'iveta',
    id: validatedEnv.SELLER_ID || 'iveta_zeya888'
  },
  
  // Contracts
  contracts: {
    magicRegistry: validatedEnv.MAGIC_REGISTRY_CONTRACT_ADDRESS,
    spiralEngine: validatedEnv.SPIRAL_ENGINE_CONTRACT_ADDRESS,
    productRegistry: validatedEnv.PRODUCT_REGISTRY_CONTRACT_ADDRESS,
    soulIdentity: validatedEnv.SOUL_IDENTITY_CONTRACT_ADDRESS,
    organicComponentRegistry: validatedEnv.ORGANIC_COMPONENT_REGISTRY_PROXY,
    amanitaInternational: validatedEnv.AMANITA_INTERNATIONAL_PROXY
  },
  
  // Paths
  paths: {
    csvBase: validatedEnv.CSV_BASE_PATH || 'data/sellers',
    outputBase: validatedEnv.OUTPUT_BASE_PATH || 'data/sellers',
    csvPath: `${validatedEnv.CSV_BASE_PATH || 'data/sellers'}/${validatedEnv.SELLER_BUSINESS_ID || 'iveta'}/catalog/${validatedEnv.CSV_FILENAME || 'Iveta_catalog.csv'}`,
    outputPath: `${validatedEnv.OUTPUT_BASE_PATH || 'data/sellers'}/${validatedEnv.SELLER_BUSINESS_ID || 'iveta'}/products`
  },
  
  // Features
  features: {
    arweave: validatedEnv.ARWEAVE,
    quick: validatedEnv.QUICK
  },
  
  // Network
  network: {
    name: validatedEnv.NETWORK,
    rpcUrl: validatedEnv.RPC_URL
  },
  
  // Arweave configuration (with comprehensive fallbacks)
  arweave: {
    // Gateway configuration
    gateway: validatedEnv.ARWEAVE_GATEWAY || ARWEAVE.GATEWAY.DEFAULT,
    port: parseInt(validatedEnv.ARWEAVE_PORT || ARWEAVE.GATEWAY.PORT),
    protocol: validatedEnv.ARWEAVE_PROTOCOL || ARWEAVE.GATEWAY.PROTOCOL,
    
    // Timeouts
    timeout: parseInt(validatedEnv.ARWEAVE_TIMEOUT || ARWEAVE.TIMEOUT),
    uploadTimeout: parseInt(validatedEnv.ARWEAVE_UPLOAD_TIMEOUT || ARWEAVE.UPLOAD_TIMEOUT),
    connectionTimeout: parseInt(validatedEnv.ARWEAVE_CONNECTION_TIMEOUT || ARWEAVE.CONNECTION_TIMEOUT),
    
    // Key path
    keyPath: validatedEnv.ARWEAVE_KEY_PATH || ARWEAVE.KEY_PATH.DEFAULT,
    
    // Feature flags
    enabled: validatedEnv.ARWEAVE !== 'false',  // default: true
    retries: parseInt(validatedEnv.ARWEAVE_RETRIES || ARWEAVE.RETRY.MAX_ATTEMPTS),
    
    // Logging
    verbose: validatedEnv.ARWEAVE_VERBOSE === 'true'  // default: false
  },
  
  // Processing
  processing: {
    batchSize: validatedEnv.BATCH_SIZE,
    maxRetries: validatedEnv.MAX_RETRIES
  },
  
  // Logging
  logging: {
    level: validatedEnv.LOG_LEVEL,
    verbose: validatedEnv.VERBOSE
  }
};

// Utility functions
const get = (key) => {
  const keys = key.split('.');
  let value = config;
  for (const k of keys) {
    value = value[k];
    if (value === undefined) return undefined;
  }
  return value;
};

const getWithDefault = (key, defaultValue) => {
  const value = get(key);
  return value !== undefined ? value : defaultValue;
};

const isSet = (key) => {
  return get(key) !== undefined && get(key) !== null;
};

const validateRequired = (key) => {
  const value = get(key);
  if (value === undefined || value === null) {
    throw new Error(`Required configuration key '${key}' is not set`);
  }
  return value;
};

module.exports = {
  config,
  get,
  getWithDefault,
  isSet,
  validateRequired,
  
  // Backward compatibility
  getContractAddress: (contractName) => {
    const contractKey = contractName.toLowerCase().replace(/_/g, '');
    return get(`contracts.${contractKey}`);
  },
  
  getSellerConfig: () => config.seller,
  getDeployerConfig: () => config.deployer,
  getPathsConfig: () => config.paths,
  getFeaturesConfig: () => config.features
};
