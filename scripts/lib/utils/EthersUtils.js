/**
 * Ethers Utilities
 * 
 * This module provides ethers.js equivalents for Web3Utils functionality,
 * centralizing common operations for account management, invite generation, and blockchain helpers.
 * 
 * Migrated from Web3Utils.js to support Hardhat Network compatibility.
 * 
 * @version 2.0.0 (ethers migration)
 * @date 2025-10-16
 */

const { ethers } = require('hardhat');
const { PROCESSING } = require('../config/constants');
const logger = require('./Logger');

class EthersUtils {
  constructor(provider, config) {
    this.provider = provider;
    this.config = config;
    
    // НЕ кэшируем deployerSigner - критично для правильного nonce управления!
    // Каждый getSigner() создаёт НОВЫЙ Wallet instance, который автоматически
    // запросит актуальный nonce из provider
  }

  /**
   * Get signer (always creates new wallet instance)
   * ВАЖНО: ВСЕГДА создаёт НОВЫЙ Wallet для правильного nonce управления!
   * Каждый новый Wallet instance запрашивает актуальный nonce из provider.
   * Кэширование приводит к "nonce has already been used" ошибкам!
   * @param {string} privateKey - Optional private key (uses deployer if not provided)
   * @returns {ethers.Wallet} - Signer instance
   */
  getSigner(privateKey = null) {
    const key = privateKey || this.config.get('deployer.privateKey');
    if (!key) {
      logger.error('[ERROR] No private key available!');
      logger.error('[ERROR] Sources checked:');
      logger.error(`  - privateKey parameter: ${privateKey ? 'provided' : 'null'}`);
      logger.error(`  - config.deployer.privateKey: ${this.config.get('deployer.privateKey') ? 'found' : 'undefined'}`);
      logger.error('[ERROR] Set DEPLOYER_PRIVATE_KEY in .env');
      throw new Error('No private key available. Set DEPLOYER_PRIVATE_KEY in .env');
    }
    
    // 🔍 DEBUG: Log signer creation (without exposing full key)
    logger.debug(`[DEBUG] Creating signer with private key: ${key.substring(0, 10)}...${key.substring(key.length - 4)}`);
    
    try {
      // КРИТИЧНО: Всегда создаём НОВЫЙ Wallet instance!
      // Это гарантирует что ethers.js запросит актуальный nonce из provider
      const wallet = new ethers.Wallet(key, this.provider);
      logger.debug(`[DEBUG] Signer created successfully. Address: ${wallet.address}`);
      return wallet;
    } catch (error) {
      logger.error(`[ERROR] Failed to create signer from private key: ${error.message}`);
      logger.error(`[ERROR] Private key format: ${key.substring(0, 10)}...${key.substring(key.length - 4)}`);
      throw error;
    }
  }

  /**
   * Create account from private key (ethers equivalent)
   * @param {string} privateKey - Private key
   * @returns {ethers.Wallet} - Wallet instance
   */
  accountFromPrivateKey(privateKey) {
    try {
      const wallet = new ethers.Wallet(privateKey, this.provider);
      logger.debug(`Created wallet: ${wallet.address}`);
      return wallet;
    } catch (error) {
      logger.error('Failed to create wallet from private key:', error.message);
      throw error;
    }
  }

  // ==================== PURE JS METHODS (NO CHANGES) ====================

  /**
   * Generate random alphanumeric string
   * @param {number} length - Length of the string
   * @returns {string} - Random alphanumeric string
   */
  generateRandomAlphanumeric(length = 8) {
    const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789';
    let result = '';
    
    for (let i = 0; i < length; i++) {
      result += chars.charAt(Math.floor(Math.random() * chars.length));
    }
    
    logger.debug(`Generated random string: ${result}`);
    return result;
  }

  /**
   * Generate new invite codes
   * @param {number} count - Number of codes to generate
   * @param {number} length - Length of each code
   * @returns {Array} - Array of invite codes
   */
  generateNewInviteCodes(count = 12, length = 8) {
    const codes = [];
    
    for (let i = 0; i < count; i++) {
      let code;
      let attempts = 0;
      const maxAttempts = 100;
      
      do {
        code = this.generateRandomAlphanumeric(length);
        attempts++;
      } while (codes.includes(code) && attempts < maxAttempts);
      
      if (attempts >= maxAttempts) {
        throw new Error(`Failed to generate unique invite code after ${maxAttempts} attempts`);
      }
      
      codes.push(code);
    }
    
    logger.info(`Generated ${count} unique invite codes`);
    return codes;
  }

  /**
   * Generate invite codes with validation
   * @param {number} count - Number of codes to generate
   * @param {number} length - Length of each code
   * @param {Array} existingCodes - Existing codes to avoid duplicates
   * @returns {Array} - Array of invite codes
   */
  generateInviteCodes(count = 12, length = 8, existingCodes = []) {
    const codes = [];
    const allCodes = [...existingCodes];
    
    for (let i = 0; i < count; i++) {
      let code;
      let attempts = 0;
      const maxAttempts = 100;
      
      do {
        code = this.generateRandomAlphanumeric(length);
        attempts++;
      } while (allCodes.includes(code) && attempts < maxAttempts);
      
      if (attempts >= maxAttempts) {
        throw new Error(`Failed to generate unique invite code after ${maxAttempts} attempts`);
      }
      
      codes.push(code);
      allCodes.push(code);
    }
    
    logger.info(`Generated ${count} unique invite codes (avoiding ${existingCodes.length} existing)`);
    return codes;
  }

  // ==================== ETHERS ACCOUNT OPERATIONS ====================

  /**
   * Create account from private key (alias for accountFromPrivateKey)
   * @param {string} privateKey - Private key
   * @returns {ethers.Wallet} - Wallet instance
   */
  createAccount(privateKey) {
    return this.accountFromPrivateKey(privateKey);
  }

  /**
   * Get account balance
   * @param {string} address - Account address
   * @returns {Promise<bigint>} - Account balance in wei
   */
  async getBalance(address) {
    try {
      const balance = await this.provider.getBalance(address);
      logger.debug(`Balance for ${address}: ${balance.toString()} wei`);
      return balance;
    } catch (error) {
      logger.error(`Failed to get balance for ${address}:`, error.message);
      throw error;
    }
  }

  /**
   * Get account balance in ETH
   * @param {string} address - Account address
   * @returns {Promise<number>} - Account balance in ETH
   */
  async getBalanceInETH(address) {
    try {
      const balanceWei = await this.getBalance(address);
      const balanceETH = ethers.formatEther(balanceWei);
      logger.debug(`Balance for ${address}: ${balanceETH} ETH`);
      return parseFloat(balanceETH);
    } catch (error) {
      logger.error(`Failed to get ETH balance for ${address}:`, error.message);
      throw error;
    }
  }

  // ==================== ETHERS TRANSACTION OPERATIONS ====================

  /**
   * Send transaction with retry logic
   * @param {Object} transaction - Transaction object (ethers format)
   * @param {Object} options - Transaction options
   * @returns {Promise<Object>} - Transaction receipt
   */
  async sendTransactionWithRetry(transaction, options = {}) {
    const maxRetries = options.maxRetries || PROCESSING.MAX_RETRIES;
    let lastError;

    for (let attempt = 1; attempt <= maxRetries; attempt++) {
      try {
        logger.debug(`Transaction attempt ${attempt}/${maxRetries}`);
        
        // Get signer
        const signer = this.getSigner(options.privateKey);
        
        // Send transaction
        const tx = await signer.sendTransaction(transaction);
        logger.transaction(tx.hash, `Transaction sent (attempt ${attempt})`);
        
        // Wait for confirmation
        const receipt = await tx.wait();
        logger.transaction(receipt.hash, 'Transaction successful');
        return receipt;
      } catch (error) {
        lastError = error;
        logger.warn(`Transaction attempt ${attempt} failed:`, error.message);
        
        if (attempt < maxRetries) {
          const delay = Math.pow(2, attempt) * 1000; // Exponential backoff
          logger.debug(`Retrying in ${delay}ms...`);
          await new Promise(resolve => setTimeout(resolve, delay));
        }
      }
    }

    logger.error(`Transaction failed after ${maxRetries} attempts`);
    throw lastError;
  }

  /**
   * Estimate gas for transaction
   * @param {Object} transaction - Transaction object
   * @returns {Promise<bigint>} - Estimated gas
   */
  async estimateGas(transaction) {
    try {
      const gasEstimate = await this.provider.estimateGas(transaction);
      logger.debug(`Gas estimate: ${gasEstimate.toString()}`);
      return gasEstimate;
    } catch (error) {
      logger.error('Failed to estimate gas:', error.message);
      throw error;
    }
  }

  /**
   * Get current gas price (legacy - ethers v6 uses FeeData)
   * @returns {Promise<bigint>} - Current gas price in wei
   */
  async getGasPrice() {
    try {
      const feeData = await this.provider.getFeeData();
      const gasPrice = feeData.gasPrice;
      logger.debug(`Current gas price: ${gasPrice.toString()} wei`);
      return gasPrice;
    } catch (error) {
      logger.error('Failed to get gas price:', error.message);
      throw error;
    }
  }

  /**
   * Wait for transaction confirmation
   * @param {string} txHash - Transaction hash
   * @param {number} confirmations - Number of confirmations to wait for
   * @returns {Promise<Object>} - Transaction receipt
   */
  async waitForTransactionConfirmation(txHash, confirmations = 1) {
    try {
      logger.info(`Waiting for transaction confirmation: ${txHash}`);
      
      const receipt = await this.provider.waitForTransaction(txHash, confirmations);
      logger.transaction(txHash, `Confirmed with ${confirmations} confirmations`);
      
      return receipt;
    } catch (error) {
      logger.error(`Failed to wait for transaction confirmation ${txHash}:`, error.message);
      throw error;
    }
  }

  // ==================== ETHERS UTILITY OPERATIONS ====================

  /**
   * Check if address is valid
   * @param {string} address - Address to validate
   * @returns {boolean} - Whether address is valid
   */
  isValidAddress(address) {
    try {
      return ethers.isAddress(address);
    } catch (error) {
      return false;
    }
  }

  /**
   * Convert wei to ETH
   * @param {bigint|string} wei - Amount in wei
   * @returns {string} - Amount in ETH
   */
  weiToETH(wei) {
    return ethers.formatEther(wei);
  }

  /**
   * Convert ETH to wei
   * @param {string} eth - Amount in ETH
   * @returns {bigint} - Amount in wei
   */
  ethToWei(eth) {
    return ethers.parseEther(eth);
  }

  /**
   * Get network ID (ethers uses chainId)
   * @returns {Promise<bigint>} - Network chain ID
   */
  async getNetworkId() {
    try {
      const network = await this.provider.getNetwork();
      const chainId = network.chainId;
      logger.debug(`Network chain ID: ${chainId.toString()}`);
      return chainId;
    } catch (error) {
      logger.error('Failed to get network ID:', error.message);
      throw error;
    }
  }

  /**
   * Get block number
   * @returns {Promise<number>} - Current block number
   */
  async getBlockNumber() {
    try {
      const blockNumber = await this.provider.getBlockNumber();
      logger.debug(`Current block number: ${blockNumber}`);
      return blockNumber;
    } catch (error) {
      logger.error('Failed to get block number:', error.message);
      throw error;
    }
  }

  /**
   * Get transaction count for address
   * @param {string} address - Address to check
   * @returns {Promise<number>} - Transaction count (nonce)
   */
  async getTransactionCount(address) {
    try {
      const count = await this.provider.getTransactionCount(address);
      logger.debug(`Transaction count for ${address}: ${count}`);
      return count;
    } catch (error) {
      logger.error(`Failed to get transaction count for ${address}:`, error.message);
      throw error;
    }
  }

  /**
   * Batch process transactions
   * @param {Array} transactions - Array of transaction objects
   * @param {Object} options - Batch options
   * @returns {Promise<Array>} - Array of transaction receipts
   */
  async batchProcessTransactions(transactions, options = {}) {
    const batchSize = options.batchSize || PROCESSING.BATCH_SIZE;
    const results = [];
    
    logger.info(`Processing ${transactions.length} transactions in batches of ${batchSize}`);
    
    for (let i = 0; i < transactions.length; i += batchSize) {
      const batch = transactions.slice(i, i + batchSize);
      logger.progress(i + batch.length, transactions.length, 'Processing transaction batch');
      
      const batchPromises = batch.map(tx => this.sendTransactionWithRetry(tx, options));
      const batchResults = await Promise.allSettled(batchPromises);
      
      results.push(...batchResults);
    }
    
    const successful = results.filter(r => r.status === 'fulfilled').length;
    const failed = results.filter(r => r.status === 'rejected').length;
    
    logger.info(`Batch processing complete: ${successful} successful, ${failed} failed`);
    return results;
  }
}

module.exports = EthersUtils;

