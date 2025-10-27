/**
 * Core Index Module
 * 
 * This module provides a centralized interface for all core modules,
 * allowing easy access to all core functionality from a single entry point.
 */

const CoreLogic = require('./CoreLogic');

class CoreManager {
  constructor(contractManager, ethersUtils, config) {
    this.contractManager = contractManager;
    this.ethersUtils = ethersUtils;
    this.config = config;
    
    // Initialize core modules
    this.coreLogic = new CoreLogic(contractManager, ethersUtils, config);
  }

  /**
   * Get core logic instance
   * @returns {CoreLogic} - Core logic instance
   */
  getCoreLogic() {
    return this.coreLogic;
  }

  /**
   * Activate seller (convenience method)
   * @param {string} sellerAddress - Seller address
   * @param {Array} inviteCodes - Invite codes
   * @returns {Promise<Object>} - Activation result
   */
  async activateSeller(sellerAddress = null, inviteCodes = null) {
    return await this.coreLogic.activateSellerBasic(sellerAddress, inviteCodes);
  }

  /**
   * Setup seller role (convenience method)
   * @param {string} sellerAddress - Seller address
   * @returns {Promise<Object>} - Role setup result
   */
  async setupSeller(sellerAddress = null) {
    return await this.coreLogic.setupSellerRole(sellerAddress);
  }

  /**
   * Validate seller (convenience method)
   * @param {string} sellerAddress - Seller address
   * @returns {Promise<Object>} - Validation result
   */
  async validateSeller(sellerAddress = null) {
    return await this.coreLogic.validateSellerAccess(sellerAddress);
  }

  /**
   * Check components (convenience method)
   * @returns {Promise<Object>} - Components check result
   */
  async checkComponents() {
    return await this.coreLogic.checkComponentsLoaded();
  }

  /**
   * Create catalog (convenience method)
   * @returns {Promise<Object>} - Catalog creation result
   */
  async createCatalog() {
    return await this.coreLogic.createCatalogWithAction444();
  }

  /**
   * Load catalog (convenience method)
   * @param {string} sellerId - Seller ID
   * @returns {Promise<Object>} - Catalog data
   */
  async loadCatalog(sellerId = null) {
    return await this.coreLogic.loadSellerCatalog(sellerId);
  }

  /**
   * Generate invites (convenience method)
   * @param {string} sellerAddress - Seller address
   * @param {number} count - Number of invites
   * @returns {Promise<Object>} - Invite generation result
   */
  async generateInvites(sellerAddress = null, count = 12) {
    return await this.coreLogic.generateInvitesForSeller(sellerAddress, count);
  }

  /**
   * Get catalog data (convenience method)
   * @param {string} sellerId - Seller ID
   * @returns {Promise<Object>} - Full catalog data
   */
  async getCatalogData(sellerId = null) {
    return await this.coreLogic.getFullCatalogWithData(sellerId);
  }

  /**
   * Diagnose state (convenience method)
   * @param {string} sellerAddress - Seller address
   * @returns {Promise<Object>} - Diagnosis result
   */
  async diagnoseState(sellerAddress = null) {
    return await this.coreLogic.diagnoseSellerState(sellerAddress);
  }
}

module.exports = {
  CoreManager,
  CoreLogic
};
