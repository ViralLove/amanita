/**
 * Centralized Configuration Manager
 * 
 * This module provides a single source of truth for all environment variables
 * used in the deploy_full.js script, eliminating duplication and providing
 * validation with sensible defaults.
 * 
 * Based on analysis of 44 process.env usages in deploy_full.js
 */

const path = require('path');
const { SCRIPTS_DOTENV_PATH } = require('../env-path');
require('dotenv').config({ path: SCRIPTS_DOTENV_PATH });

const { ARWEAVE, CONTRACT_ENV_MAPPING, CONTRACT_ENV_ALIASES } = require('./constants');

function firstEnvValue(env, keys) {
  for (const k of keys) {
    const v = env[k];
    if (v && v !== 'undefined') return v;
  }
  return undefined;
}

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
    address: validatedEnv.DEPLOYER_ADDRESS || '0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266',  // ✅ FIX: Add deployer address
    invite: validatedEnv.DEPLOYER_INVITE || null
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

  // Activity creator (wallet signer for ActivityRegistry.createActivity)
  activityCreator: {
    address: validatedEnv.ACTIVITY_CREATOR_ADDRESS || null
  },

  // Generic validated address for diagnostics actions (e.g. Action 13)
  validated: {
    address: validatedEnv.VALIDATED_ADDRESS || null
  },
  
  // Contracts (canonical + aliases для resume после Action 12 / старых .env)
  contracts: {
    magicRegistry: validatedEnv.MAGIC_REGISTRY_CONTRACT_ADDRESS,
    spiralEngine: firstEnvValue(validatedEnv, [
      'SPIRAL_ENGINE_CONTRACT_ADDRESS',
      'SPIRAL_ENGINE_PROXY_ADDRESS'
    ]),
    productRegistry: firstEnvValue(validatedEnv, [
      'PRODUCT_REGISTRY_CONTRACT_ADDRESS',
      'PRODUCT_REGISTRY_PROXY_ADDRESS'
    ]),
    activityRegistry: firstEnvValue(validatedEnv, [
      'ACTIVITY_REGISTRY_CONTRACT_ADDRESS',
      'ACTIVITY_REGISTRY_PROXY_ADDRESS'
    ]),
    soulIdentity: validatedEnv.SOUL_IDENTITY_CONTRACT_ADDRESS,
    organicComponentRegistry: firstEnvValue(validatedEnv, [
      'ORGANIC_COMPONENT_REGISTRY_CONTRACT_ADDRESS',
      'ORGANIC_COMPONENT_REGISTRY_PROXY_ADDRESS',
      'ORGANIC_COMPONENT_REGISTRY_PROXY'
    ]),
    amanitaInternational: firstEnvValue(validatedEnv, [
      'AMANITA_INTERNATIONAL_CONTRACT_ADDRESS',
      'AMANITA_INTERNATIONAL_PROXY_ADDRESS',
      'AMANITA_INTERNATIONAL_PROXY'
    ]),
    soulboundCore: validatedEnv.SOULBOUND_CORE_CONTRACT_ADDRESS,
    soulMetadata: validatedEnv.SOUL_METADATA_CONTRACT_ADDRESS,
    soulRecovery: validatedEnv.SOUL_RECOVERY_CONTRACT_ADDRESS,
    soulIntegration: validatedEnv.SOUL_INTEGRATION_CONTRACT_ADDRESS
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
    // Support both RPC_URL and WEB3_PROVIDER_URI for compatibility
    rpcUrl: validatedEnv.RPC_URL || validatedEnv.WEB3_PROVIDER_URI
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
  
  // camelCase ключ как в config.contracts.* (magicRegistry, spiralEngine, ...)
  getContractAddress: (contractName) => {
    const contractConfigKey = contractName.charAt(0).toLowerCase() + contractName.slice(1);
    const fromConfig = get(`contracts.${contractConfigKey}`);
    if (fromConfig && fromConfig !== 'undefined') return fromConfig;

    const primary = CONTRACT_ENV_MAPPING[contractName];
    const aliases = CONTRACT_ENV_ALIASES[contractName] || [];
    for (const key of [primary, ...aliases]) {
      if (!key) continue;
      const v = process.env[key];
      if (v && v !== 'undefined') return v;
    }
    return undefined;
  },
  
  getSellerConfig: () => config.seller,
  getDeployerConfig: () => config.deployer,
  getPathsConfig: () => config.paths,
  getFeaturesConfig: () => config.features
};
