/**
 * Centralized Logger
 * 
 * This module provides structured logging for the deploy_full.js script,
 * replacing 793 console.log statements with a centralized, configurable
 * logging system.
 * 
 * Based on analysis of logging patterns in deploy_full.js
 */

const { LOGGING } = require('../config/constants');

class Logger {
  constructor(level = 'info') {
    this.level = level;
    this.levels = LOGGING.LEVELS;
    this.colors = LOGGING.COLORS;
  }

  /**
   * Set the logging level
   * @param {string} level - debug, info, warn, error
   */
  setLevel(level) {
    if (this.levels.hasOwnProperty(level.toUpperCase())) {
      this.level = level.toLowerCase();
    }
  }

  /**
   * Check if a log level should be output
   * @param {string} level - The level to check
   * @returns {boolean} - Whether to output
   */
  shouldLog(level) {
    return this.levels[level.toUpperCase()] >= this.levels[this.level.toUpperCase()];
  }

  /**
   * Format a log message with color and timestamp
   * @param {string} level - The log level
   * @param {string} message - The message to log
   * @param {...any} args - Additional arguments
   */
  formatMessage(level, message, ...args) {
    const timestamp = new Date().toISOString();
    const color = this.colors[level.toUpperCase()] || this.colors.RESET;
    const reset = this.colors.RESET;
    
    return `${color}[${timestamp}] [${level.toUpperCase()}] ${message}${reset}`;
  }

  /**
   * Debug level logging
   * @param {string} message - The message to log
   * @param {...any} args - Additional arguments
   */
  debug(message, ...args) {
    if (this.shouldLog('debug')) {
      console.log(this.formatMessage('debug', message), ...args);
    }
  }

  /**
   * Info level logging
   * @param {string} message - The message to log
   * @param {...any} args - Additional arguments
   */
  info(message, ...args) {
    if (this.shouldLog('info')) {
      console.log(this.formatMessage('info', message), ...args);
    }
  }

  /**
   * Warning level logging
   * @param {string} message - The message to log
   * @param {...any} args - Additional arguments
   */
  warn(message, ...args) {
    if (this.shouldLog('warn')) {
      console.log(this.formatMessage('warn', message), ...args);
    }
  }

  /**
   * Error level logging
   * @param {string} message - The message to log
   * @param {...any} args - Additional arguments
   */
  error(message, ...args) {
    if (this.shouldLog('error')) {
      console.error(this.formatMessage('error', message), ...args);
    }
  }

  /**
   * Action start logging with special formatting
   * @param {number} actionNumber - The action number
   * @param {string} actionName - The action name
   */
  action(actionNumber, actionName) {
    console.log("\n" + "=".repeat(70));
    console.log(`🔷 Action ${actionNumber}: ${actionName}`);
    console.log("=".repeat(70));
  }

  /**
   * Action success logging with special formatting
   * @param {number} actionNumber - The action number
   */
  success(actionNumber) {
    console.log("\n" + "=".repeat(70));
    console.log(`✅ Action ${actionNumber} completed successfully!`);
    console.log("=".repeat(70));
  }

  /**
   * Action failure logging with special formatting
   * @param {number} actionNumber - The action number
   * @param {string} error - The error message
   */
  failure(actionNumber, error) {
    console.log("\n" + "=".repeat(70));
    console.log(`❌ Action ${actionNumber} failed: ${error}`);
    console.log("=".repeat(70));
  }

  /**
   * Contract interaction logging
   * @param {string} contractName - The contract name
   * @param {string} method - The method being called
   * @param {any} params - The parameters
   */
  contract(contractName, method, params = null) {
    this.debug(`Contract ${contractName}.${method}`, params ? `with params: ${JSON.stringify(params)}` : '');
  }

  /**
   * Transaction logging
   * @param {string} txHash - The transaction hash
   * @param {string} operation - The operation description
   */
  transaction(txHash, operation) {
    this.info(`Transaction ${txHash} for ${operation}`);
  }

  /**
   * Configuration logging
   * @param {string} key - The configuration key
   * @param {any} value - The configuration value
   */
  config(key, value) {
    this.debug(`Config ${key}:`, value);
  }

  /**
   * Progress logging for long operations
   * @param {number} current - Current progress
   * @param {number} total - Total items
   * @param {string} operation - Operation description
   */
  progress(current, total, operation) {
    const percentage = Math.round((current / total) * 100);
    this.info(`Progress: ${current}/${total} (${percentage}%) - ${operation}`);
  }

  /**
   * Section separator for better readability
   * @param {string} title - The section title
   */
  section(title) {
    console.log("\n" + "-".repeat(50));
    console.log(`📋 ${title}`);
    console.log("-".repeat(50));
  }

  /**
   * Legacy section separator (compatible with deploy_full.js format)
   * @param {string} contractName - The contract name being deployed
   */
  legacySection(contractName) {
    console.log("--------------------------------------------------");
    console.log(`📋 Deploying ${contractName}`);
    console.log("--------------------------------------------------");
  }

  /**
   * Deployment details logging (gas, balance, cost)
   * @param {Object} details - Deployment details
   * @param {number} details.gasUsed - Gas used for deployment
   * @param {string} details.balance - Current balance in ETH
   * @param {string} details.cost - Deployment cost in ETH
   * @param {string} details.contractName - Contract name
   */
  deploymentDetails({ gasUsed, balance, cost, contractName }) {
    console.log(`Gas used: ${gasUsed.toLocaleString()}`);
    console.log(`Balance: ${balance} ETH`);
    console.log(`Cost: ${cost} ETH`);
    if (contractName) {
      console.log(`Contract: ${contractName}`);
    }
  }

  /**
   * Simple log (backward compatibility)
   * @param {string} message - The message to log
   * @param {...any} args - Additional arguments
   */
  log(message, ...args) {
    this.info(message, ...args);
  }
}

// Create and export a singleton instance
const logger = new Logger();

module.exports = logger;
