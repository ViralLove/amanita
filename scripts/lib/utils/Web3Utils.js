/**
 * Web3 Utilities
 * 
 * This module centralizes all Web3 utility functions from deploy_full.js,
 * providing common operations for account management, invite generation, and Web3 helpers.
 * 
 * Based on analysis of 134 Web3 references in deploy_full.js
 */

const { Web3 } = require('web3');
const { PROCESSING } = require('../config/constants');
const logger = require('./Logger');

class Web3Utils {
  constructor(web3, config) {
    this.web3 = web3;
    this.config = config;
  }

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

  /**
   * Create account from private key
   * @param {string} privateKey - Private key
   * @returns {Object} - Account object
   */
  createAccount(privateKey) {
    try {
      const account = this.web3.eth.accounts.privateKeyToAccount(privateKey);
      logger.debug(`Created account: ${account.address}`);
      return account;
    } catch (error) {
      logger.error('Failed to create account from private key:', error.message);
      throw error;
    }
  }

  /**
   * Get account balance
   * @param {string} address - Account address
   * @returns {Promise<string>} - Account balance in wei
   */
  async getBalance(address) {
    try {
      const balance = await this.web3.eth.getBalance(address);
      logger.debug(`Balance for ${address}: ${balance} wei`);
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
      const balanceETH = this.web3.utils.fromWei(balanceWei, 'ether');
      logger.debug(`Balance for ${address}: ${balanceETH} ETH`);
      return parseFloat(balanceETH);
    } catch (error) {
      logger.error(`Failed to get ETH balance for ${address}:`, error.message);
      throw error;
    }
  }

  /**
   * Send transaction with retry logic
   * @param {Object} transaction - Transaction object
   * @param {Object} options - Transaction options
   * @returns {Promise<Object>} - Transaction receipt
   */
  async sendTransactionWithRetry(transaction, options = {}) {
    const maxRetries = options.maxRetries || PROCESSING.MAX_RETRIES;
    let lastError;

    for (let attempt = 1; attempt <= maxRetries; attempt++) {
      try {
        logger.debug(`Transaction attempt ${attempt}/${maxRetries}`);
        
        const receipt = await this.web3.eth.sendTransaction(transaction);
        logger.transaction(receipt.transactionHash, 'Transaction successful');
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
   * @returns {Promise<number>} - Estimated gas
   */
  async estimateGas(transaction) {
    try {
      const gasEstimate = await this.web3.eth.estimateGas(transaction);
      logger.debug(`Gas estimate: ${gasEstimate}`);
      return gasEstimate;
    } catch (error) {
      logger.error('Failed to estimate gas:', error.message);
      throw error;
    }
  }

  /**
   * Get current gas price
   * @returns {Promise<string>} - Current gas price in wei
   */
  async getGasPrice() {
    try {
      const gasPrice = await this.web3.eth.getGasPrice();
      logger.debug(`Current gas price: ${gasPrice} wei`);
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
      
      const receipt = await this.web3.eth.waitForTransactionReceipt(txHash, confirmations);
      logger.transaction(txHash, `Confirmed with ${confirmations} confirmations`);
      
      return receipt;
    } catch (error) {
      logger.error(`Failed to wait for transaction confirmation ${txHash}:`, error.message);
      throw error;
    }
  }

  /**
   * Check if address is valid
   * @param {string} address - Address to validate
   * @returns {boolean} - Whether address is valid
   */
  isValidAddress(address) {
    try {
      return this.web3.utils.isAddress(address);
    } catch (error) {
      return false;
    }
  }

  /**
   * Convert wei to ETH
   * @param {string} wei - Amount in wei
   * @returns {string} - Amount in ETH
   */
  weiToETH(wei) {
    return this.web3.utils.fromWei(wei, 'ether');
  }

  /**
   * Convert ETH to wei
   * @param {string} eth - Amount in ETH
   * @returns {string} - Amount in wei
   */
  ethToWei(eth) {
    return this.web3.utils.toWei(eth, 'ether');
  }

  /**
   * Get network ID
   * @returns {Promise<number>} - Network ID
   */
  async getNetworkId() {
    try {
      const networkId = await this.web3.eth.net.getId();
      logger.debug(`Network ID: ${networkId}`);
      return networkId;
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
      const blockNumber = await this.web3.eth.getBlockNumber();
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
   * @returns {Promise<number>} - Transaction count
   */
  async getTransactionCount(address) {
    try {
      const count = await this.web3.eth.getTransactionCount(address);
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

module.exports = Web3Utils;
