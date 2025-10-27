/**
 * Core Logic Module
 * 
 * This module centralizes common business logic functions from deploy_full.js,
 * providing shared functionality across multiple actions.
 */

const logger = require('../utils/Logger');

class CoreLogic {
  constructor(contractManager, ethersUtils, config) {
    this.contractManager = contractManager;
    this.ethersUtils = ethersUtils;
    this.config = config;
  }

  /**
   * Execute contract write operation with proper signer
   * @param {Object} contract - Contract instance
   * @param {string} methodName - Method name
   * @param {Array} args - Method arguments
   * @param {Object} options - Transaction options
   * @returns {Promise<Object>} - Transaction result
   */
  async executeContractWrite(contract, methodName, args = [], options = {}) {
    try {
      const signer = this.ethersUtils.getSigner();
      const connectedContract = contract.connect(signer);
      
      const gasLimit = options.gas || 500000;
      const tx = await connectedContract[methodName](...args, { gasLimit });
      
      logger.info(`Transaction sent: ${methodName}`, { txHash: tx.hash });
      const receipt = await tx.wait();
      
      return {
        transactionHash: tx.hash,
        receipt: receipt,
        success: receipt.status === 1
      };
    } catch (error) {
      logger.error(`Failed to execute ${methodName}:`, error.message);
      throw error;
    }
  }

  /**
   * Activate seller basic
   * @param {string} sellerAddress - Seller address to activate
   * @param {Array} inviteCodes - Invite codes for activation
   * @returns {Promise<Object>} - Activation result
   */
  async activateSellerBasic(sellerAddress = null, inviteCodes = null) {
    try {
      const spiralEngine = await this.contractManager.getContract('SpiralEngine');
      if (!spiralEngine) {
        throw new Error('SpiralEngine contract not found');
      }

      const targetSellerAddress = sellerAddress || this.config.get('seller.address');
      if (!targetSellerAddress) {
        throw new Error('Seller address not provided');
      }

      // Generate invite codes if not provided
      const codes = inviteCodes || this.ethersUtils.generateNewInviteCodes(12, 8);

      // Activate seller
      const activateTx = await this.executeContractWrite(
        spiralEngine,
        'activateUser',
        ['ROOT_INVITE', targetSellerAddress, codes, 0],
        { gas: 500000 }
      );

      logger.info(`Seller activated: ${targetSellerAddress}`);
      return {
        success: true,
        transactionHash: activateTx.transactionHash,
        inviteCodes: codes,
        sellerAddress: targetSellerAddress
      };
    } catch (error) {
      logger.error('Failed to activate seller:', error.message);
      throw error;
    }
  }

  /**
   * Setup seller role
   * @param {string} sellerAddress - Seller address
   * @returns {Promise<Object>} - Role setup result
   */
  async setupSellerRole(sellerAddress = null) {
    try {
      const spiralEngine = await this.contractManager.getContract('SpiralEngine');
      if (!spiralEngine) {
        throw new Error('SpiralEngine contract not found');
      }

      const targetSellerAddress = sellerAddress || this.config.get('seller.address');
      if (!targetSellerAddress) {
        throw new Error('Seller address not provided');
      }

      // Check if seller already has role
      const hasRole = await spiralEngine.hasRole(
        '0x9f2df0fed2c77648de5860a4cc508cd0818c85b8b8a1ab4ceeef8d981c8956a6', // SELLER_ROLE
        targetSellerAddress
      );

      if (hasRole) {
        logger.info(`Seller ${targetSellerAddress} already has SELLER_ROLE`);
        return {
          success: true,
          alreadyHadRole: true,
          sellerAddress: targetSellerAddress
        };
      }

      // Grant seller role
      const grantTx = await this.executeContractWrite(
        spiralEngine,
        'grantRole',
        ['0x9f2df0fed2c77648de5860a4cc508cd0818c85b8b8a1ab4ceeef8d981c8956a6', targetSellerAddress],
        { gas: 500000 }
      );

      logger.info(`SELLER_ROLE granted to: ${targetSellerAddress}`);
      return {
        success: true,
        transactionHash: grantTx.transactionHash,
        sellerAddress: targetSellerAddress
      };
    } catch (error) {
      logger.error('Failed to setup seller role:', error.message);
      throw error;
    }
  }

  /**
   * Validate seller access
   * @param {string} sellerAddress - Seller address to validate
   * @returns {Promise<Object>} - Validation result
   */
  async validateSellerAccess(sellerAddress = null) {
    try {
      const spiralEngine = await this.contractManager.getContract('SpiralEngine');
      if (!spiralEngine) {
        throw new Error('SpiralEngine contract not found');
      }

      const targetSellerAddress = sellerAddress || this.config.get('seller.address');
      if (!targetSellerAddress) {
        throw new Error('Seller address not provided');
      }

      // Check if seller is activated
      const isActivated = await spiralEngine.isUserActivated(targetSellerAddress);
      
      // Check if seller has SELLER_ROLE
      const hasSellerRole = await spiralEngine.hasRole(
        '0x9f2df0fed2c77648de5860a4cc508cd0818c85b8b8a1ab4ceeef8d981c8956a6', // SELLER_ROLE
        targetSellerAddress
      );

      const result = {
        sellerAddress: targetSellerAddress,
        isActivated: isActivated,
        hasSellerRole: hasSellerRole,
        isValid: isActivated && hasSellerRole
      };

      logger.info(`Seller validation for ${targetSellerAddress}:`, result);
      return result;
    } catch (error) {
      logger.error('Failed to validate seller access:', error.message);
      throw error;
    }
  }

  /**
   * Check if components are loaded
   * @returns {Promise<Object>} - Components check result
   */
  async checkComponentsLoaded() {
    try {
      const organicComponentRegistry = await this.contractManager.getContract('OrganicComponentRegistry');
      if (!organicComponentRegistry) {
        throw new Error('OrganicComponentRegistry contract not found');
      }

      // Get total components count
      const totalComponents = await organicComponentRegistry.getTotalComponents();
      
      const result = {
        totalComponents: parseInt(totalComponents),
        hasComponents: parseInt(totalComponents) > 0
      };

      logger.info(`Components check: ${result.totalComponents} components loaded`);
      return result;
    } catch (error) {
      logger.error('Failed to check components loaded:', error.message);
      throw error;
    }
  }

  /**
   * Create catalog with Action 444
   * @returns {Promise<Object>} - Catalog creation result
   */
  async createCatalogWithAction444() {
    try {
      // Import the upload steps module
      const { action444_AutomaticPipeline } = require('../product_upload_steps.js');
      
      const result = await action444_AutomaticPipeline({
        contractManager: this.contractManager,
        config: this.config,
        logger: logger
      });
      
      logger.info('Catalog created with Action 444');
      return result;
    } catch (error) {
      logger.error('Failed to create catalog with Action 444:', error.message);
      throw error;
    }
  }

  /**
   * Load seller catalog
   * @param {string} sellerId - Seller ID
   * @returns {Promise<Object>} - Catalog data
   */
  async loadSellerCatalog(sellerId = null) {
    try {
      const targetSellerId = sellerId || this.config.get('seller.businessId');
      if (!targetSellerId) {
        throw new Error('Seller ID not provided');
      }

      const catalogPath = `${this.config.get('paths.csvBase')}/${targetSellerId}/catalog`;
      const fs = require('fs');
      
      if (!fs.existsSync(catalogPath)) {
        throw new Error(`Catalog path not found: ${catalogPath}`);
      }

      // Load catalog files
      const files = fs.readdirSync(catalogPath);
      const catalogFiles = files.filter(file => file.endsWith('.csv'));
      
      const result = {
        sellerId: targetSellerId,
        catalogPath: catalogPath,
        catalogFiles: catalogFiles,
        hasCatalog: catalogFiles.length > 0
      };

      logger.info(`Seller catalog loaded for ${targetSellerId}:`, result);
      return result;
    } catch (error) {
      logger.error('Failed to load seller catalog:', error.message);
      throw error;
    }
  }

  /**
   * Generate invites for seller
   * @param {string} sellerAddress - Seller address
   * @param {number} count - Number of invites to generate
   * @returns {Promise<Object>} - Invite generation result
   */
  async generateInvitesForSeller(sellerAddress = null, count = 12) {
    try {
      const spiralEngine = await this.contractManager.getContract('SpiralEngine');
      if (!spiralEngine) {
        throw new Error('SpiralEngine contract not found');
      }

      const targetSellerAddress = sellerAddress || this.config.get('seller.address');
      if (!targetSellerAddress) {
        throw new Error('Seller address not provided');
      }

      // Generate invite codes
      const inviteCodes = this.ethersUtils.generateNewInviteCodes(count, 8);
      
      // Mint invites for seller
      const mintResults = [];
      for (const inviteCode of inviteCodes) {
        const mintTx = await this.executeContractWrite(
          spiralEngine,
          'mintInvite',
          [inviteCode, 0],
          { gas: 500000 }
        );
        
        mintResults.push({
          inviteCode: inviteCode,
          transactionHash: mintTx.transactionHash
        });
      }

      logger.info(`Generated ${count} invites for seller: ${targetSellerAddress}`);
      return {
        success: true,
        sellerAddress: targetSellerAddress,
        inviteCodes: inviteCodes,
        mintResults: mintResults
      };
    } catch (error) {
      logger.error('Failed to generate invites for seller:', error.message);
      throw error;
    }
  }

  /**
   * Get full catalog with data
   * @param {string} sellerId - Seller ID
   * @returns {Promise<Object>} - Full catalog data
   */
  async getFullCatalogWithData(sellerId = null) {
    try {
      const targetSellerId = sellerId || this.config.get('seller.businessId');
      if (!targetSellerId) {
        throw new Error('Seller ID not provided');
      }

      const catalogPath = `${this.config.get('paths.csvBase')}/${targetSellerId}/catalog`;
      const productsPath = `${this.config.get('paths.outputBase')}/${targetSellerId}/products`;
      
      const fs = require('fs');
      const path = require('path');
      
      // Load catalog files
      const catalogFiles = fs.existsSync(catalogPath) 
        ? fs.readdirSync(catalogPath).filter(file => file.endsWith('.csv'))
        : [];
      
      // Load product files
      const productFiles = fs.existsSync(productsPath)
        ? fs.readdirSync(productsPath).filter(file => file.endsWith('.json'))
        : [];

      const result = {
        sellerId: targetSellerId,
        catalogPath: catalogPath,
        productsPath: productsPath,
        catalogFiles: catalogFiles,
        productFiles: productFiles,
        hasCatalog: catalogFiles.length > 0,
        hasProducts: productFiles.length > 0
      };

      logger.info(`Full catalog data for ${targetSellerId}:`, result);
      return result;
    } catch (error) {
      logger.error('Failed to get full catalog with data:', error.message);
      throw error;
    }
  }

  /**
   * Diagnose seller state
   * @param {string} sellerAddress - Seller address
   * @returns {Promise<Object>} - Diagnosis result
   */
  async diagnoseSellerState(sellerAddress = null) {
    try {
      const targetSellerAddress = sellerAddress || this.config.get('seller.address');
      if (!targetSellerAddress) {
        throw new Error('Seller address not provided');
      }

      // Validate seller access
      const validation = await this.validateSellerAccess(targetSellerAddress);
      
      // Check components
      const components = await this.checkComponentsLoaded();
      
      // Get catalog data
      const catalog = await this.getFullCatalogWithData();

      const result = {
        sellerAddress: targetSellerAddress,
        validation: validation,
        components: components,
        catalog: catalog,
        overallStatus: validation.isValid && components.hasComponents && catalog.hasCatalog ? 'ready' : 'needs_setup'
      };

      logger.info(`Seller state diagnosis for ${targetSellerAddress}:`, result);
      return result;
    } catch (error) {
      logger.error('Failed to diagnose seller state:', error.message);
      throw error;
    }
  }
}

module.exports = CoreLogic;
