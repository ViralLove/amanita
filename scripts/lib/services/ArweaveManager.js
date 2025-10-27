/**
 * Arweave Manager
 * 
 * Centralized Arweave service with defensive initialization,
 * comprehensive fallbacks, and unified configuration management.
 * 
 * Features:
 * - Automatic gateway normalization
 * - Type-safe configuration with fallbacks
 * - Comprehensive error messages
 * - Wallet management and balance checking
 * - Upload operations for data, JSON, and files
 */

const Arweave = require('arweave');
const fs = require('fs');
const path = require('path');
const { ARWEAVE } = require('../config/constants');
const logger = require('../utils/Logger');

class ArweaveManager {
  constructor(config) {
    this.config = config;
    this.arweaveClient = null;
    this.arweaveKey = null;
    this.wallet = null;
  }

  /**
   * Initialize Arweave client and load wallet
   * @returns {Object} - Initialization result
   */
  async initialize() {
    try {
      logger.section('Initializing Arweave Manager');
      
      // DEFENSIVE: Get arweave config with type checking and fallbacks
      const arweaveConfig = this.config.get('arweave') || {};
      
      // DEFENSIVE: Ensure gateway is a string, apply fallback if not
      let gateway = arweaveConfig.gateway;
      if (typeof gateway !== 'string' || !gateway) {
        logger.warn(`⚠️ Arweave gateway not configured or invalid (got: ${typeof gateway})`);
        gateway = ARWEAVE.GATEWAY.DEFAULT;
        logger.info(`📌 Using default Arweave gateway: ${gateway}`);
      }
      
      // DEFENSIVE: Normalize gateway host (remove protocol if present)
      let normalizedHost = gateway;
      if (gateway.includes('://')) {
        normalizedHost = gateway.replace(/^https?:\/\//, '');
        logger.debug(`🔧 Normalized gateway: ${gateway} → ${normalizedHost}`);
      }
      
      // DEFENSIVE: Get port and protocol with fallbacks
      const port = arweaveConfig.port || ARWEAVE.GATEWAY.PORT;
      const protocol = arweaveConfig.protocol || ARWEAVE.GATEWAY.PROTOCOL;
      const timeout = arweaveConfig.timeout || ARWEAVE.TIMEOUT;
      
      logger.info(`🌐 Arweave Configuration:`);
      logger.info(`   Gateway: ${normalizedHost}`);
      logger.info(`   Port: ${port}`);
      logger.info(`   Protocol: ${protocol}`);
      logger.info(`   Timeout: ${timeout}ms`);
      
      // Initialize Arweave client with validated configuration
      this.arweaveClient = Arweave.init({
        host: normalizedHost,
        port: port,
        protocol: protocol,
        timeout: timeout,
        logging: false
      });

      logger.success('✅ Arweave client initialized');

      // Load Arweave key
      await this.loadArweaveKey();
      
      // Check wallet balance
      const balanceResult = await this.checkWalletBalance();
      
      logger.success('✅ Arweave Manager initialized successfully');
      return {
        success: true,
        client: this.arweaveClient,
        key: this.arweaveKey,
        wallet: this.wallet,
        balance: balanceResult,
        config: {
          gateway: normalizedHost,
          port,
          protocol,
          timeout
        }
      };
    } catch (error) {
      logger.error('❌ Failed to initialize Arweave Manager:', error.message);
      logger.error('💡 Check:');
      logger.error('   - ARWEAVE_GATEWAY in .env (or use default: arweave.net)');
      logger.error('   - ARWEAVE_KEY_PATH points to valid .arweave-key.json');
      logger.error('   - Network connectivity to Arweave gateway');
      throw error;
    }
  }

  /**
   * Load Arweave key from file
   * @returns {Object} - The loaded key
   */
  async loadArweaveKey() {
    try {
      const keyPath = this.config.get('arweave.keyPath');
      
      if (!fs.existsSync(keyPath)) {
        throw new Error(`Arweave key file not found: ${keyPath}`);
      }

      const keyData = fs.readFileSync(keyPath, 'utf8');
      this.arweaveKey = JSON.parse(keyData);
      
      // Create wallet from key
      this.wallet = await this.arweaveClient.wallets.jwkToAddress(this.arweaveKey);
      
      logger.info(`Arweave key loaded from ${keyPath}`);
      logger.info(`Wallet address: ${this.wallet}`);
      
      return this.arweaveKey;
    } catch (error) {
      logger.error('Failed to load Arweave key:', error.message);
      throw error;
    }
  }

  /**
   * Check wallet balance
   * @returns {Object} - Balance information
   */
  async checkWalletBalance() {
    try {
      if (!this.wallet) {
        throw new Error('Wallet not initialized');
      }

      const balance = await this.arweaveClient.wallets.getBalance(this.wallet);
      const balanceInAR = this.arweaveClient.ar.winstonToAr(balance);
      
      const result = {
        address: this.wallet,
        balance: balance,
        balanceInAR: parseFloat(balanceInAR),
        status: parseFloat(balanceInAR) > 0 ? 'has_balance' : 'zero_balance'
      };

      logger.info(`Wallet balance: ${result.balanceInAR} AR`);
      
      if (result.status === 'zero_balance') {
        logger.warn('Wallet has zero balance - uploads will fail');
      }

      return result;
    } catch (error) {
      logger.error('Failed to check wallet balance:', error.message);
      throw error;
    }
  }

  /**
   * Upload data to Arweave
   * @param {string|Buffer} data - Data to upload
   * @param {Object} options - Upload options
   * @returns {Object} - Upload result with transaction ID
   */
  async uploadData(data, options = {}) {
    try {
      if (!this.arweaveClient || !this.arweaveKey) {
        throw new Error('Arweave not initialized');
      }

      logger.debug('Starting Arweave upload', { dataSize: data.length });

      // Create transaction
      const transaction = await this.arweaveClient.createTransaction({
        data: data
      }, this.arweaveKey);

      // Add tags if provided
      if (options.tags) {
        for (const [key, value] of Object.entries(options.tags)) {
          transaction.addTag(key, value);
        }
      }

      // Sign transaction
      await this.arweaveClient.transactions.sign(transaction, this.arweaveKey);

      // Submit transaction
      const response = await this.arweaveClient.transactions.post(transaction);
      
      if (response.status === 200) {
        const txId = transaction.id;
        const arweaveUrl = `${this.config.get('arweave.gateway')}/${txId}`;
        
        logger.transaction(txId, 'Arweave upload');
        logger.info(`Upload successful: ${arweaveUrl}`);
        
        return {
          success: true,
          txId: txId,
          url: arweaveUrl,
          transaction: transaction
        };
      } else {
        throw new Error(`Upload failed with status: ${response.status}`);
      }
    } catch (error) {
      logger.error('Failed to upload to Arweave:', error.message);
      throw error;
    }
  }

  /**
   * Upload JSON data to Arweave
   * @param {Object} jsonData - JSON data to upload
   * @param {Object} options - Upload options
   * @returns {Object} - Upload result
   */
  async uploadJSON(jsonData, options = {}) {
    try {
      const jsonString = JSON.stringify(jsonData, null, 2);
      const tags = {
        'Content-Type': 'application/json',
        'App-Name': 'Amanita',
        'App-Version': '1.0.0',
        ...options.tags
      };

      return await this.uploadData(jsonString, { ...options, tags });
    } catch (error) {
      logger.error('Failed to upload JSON to Arweave:', error.message);
      throw error;
    }
  }

  /**
   * Upload file to Arweave
   * @param {string} filePath - Path to file
   * @param {Object} options - Upload options
   * @returns {Object} - Upload result
   */
  async uploadFile(filePath, options = {}) {
    try {
      if (!fs.existsSync(filePath)) {
        throw new Error(`File not found: ${filePath}`);
      }

      const fileData = fs.readFileSync(filePath);
      const fileName = path.basename(filePath);
      const fileExtension = path.extname(filePath);
      
      const tags = {
        'Content-Type': this.getContentType(fileExtension),
        'App-Name': 'Amanita',
        'App-Version': '1.0.0',
        'File-Name': fileName,
        ...options.tags
      };

      return await this.uploadData(fileData, { ...options, tags });
    } catch (error) {
      logger.error(`Failed to upload file ${filePath} to Arweave:`, error.message);
      throw error;
    }
  }

  /**
   * Get content type based on file extension
   * @param {string} extension - File extension
   * @returns {string} - Content type
   */
  getContentType(extension) {
    const contentTypes = {
      '.json': 'application/json',
      '.txt': 'text/plain',
      '.md': 'text/markdown',
      '.png': 'image/png',
      '.jpg': 'image/jpeg',
      '.jpeg': 'image/jpeg',
      '.gif': 'image/gif',
      '.svg': 'image/svg+xml',
      '.pdf': 'application/pdf'
    };
    
    return contentTypes[extension.toLowerCase()] || 'application/octet-stream';
  }

  /**
   * Test Arweave connection
   * @returns {Object} - Test result
   */
  async testConnection() {
    try {
      logger.section('Testing Arweave Connection');
      
      // Test message
      const testMessage = "HELLOATLASSWANFROMZEYA888CONNECTIONWORKS";
      
      // Upload test message
      const result = await this.uploadData(testMessage, {
        tags: {
          'Content-Type': 'text/plain',
          'App-Name': 'Amanita-Test',
          'Test-Message': 'true'
        }
      });

      logger.success('Arweave connection test successful');
      return {
        success: true,
        testUrl: result.url,
        message: 'Connection test successful'
      };
    } catch (error) {
      logger.error('Arweave connection test failed:', error.message);
      return {
        success: false,
        error: error.message
      };
    }
  }

  /**
   * Get Arweave client
   * @returns {Object} - Arweave client
   */
  getClient() {
    return this.arweaveClient;
  }

  /**
   * Get Arweave key
   * @returns {Object} - Arweave key
   */
  getKey() {
    return this.arweaveKey;
  }

  /**
   * Get wallet address
   * @returns {string} - Wallet address
   */
  getWalletAddress() {
    return this.wallet;
  }

  /**
   * Check if Arweave is ready for operations
   * @returns {boolean} - Ready status
   */
  isReady() {
    return this.arweaveClient !== null && this.arweaveKey !== null && this.wallet !== null;
  }
}

module.exports = ArweaveManager;
