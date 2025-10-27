/**
 * Actions Index Module
 * 
 * This module provides a centralized interface for all action modules,
 * allowing easy access to all actions from a single entry point.
 */

const DeployActions = require('./DeployActions');
const SetupActions = require('./SetupActions');
const AccessControlActions = require('./AccessControlActions');
const InviteActions = require('./InviteActions');
const CatalogActions = require('./CatalogActions');
const ComponentActions = require('./ComponentActions');

class ActionsManager {
  constructor(contractManager, arweaveManager, ethersUtils, config) {
    this.contractManager = contractManager;
    this.arweaveManager = arweaveManager;
    this.ethersUtils = ethersUtils;
    this.config = config;
    
    // Initialize action modules (with proper dependency injection)
    this.deployActions = new DeployActions(contractManager, ethersUtils, config);
    this.setupActions = new SetupActions(contractManager, ethersUtils, config);
    
    // Layer 3: Access Control (no dependencies on other Actions)
    this.accessControlActions = new AccessControlActions(contractManager, ethersUtils, config);
    
    // Layer 5: Catalog Management (initialize first, no Action dependencies)
    this.catalogActions = new CatalogActions(contractManager, arweaveManager, ethersUtils, config);
    
    // Layer 4A: Invite Management (depends on Layer 3 + Layer 5 for action888)
    this.inviteActions = new InviteActions(
      contractManager, 
      ethersUtils, 
      config, 
      this.accessControlActions,
      this.catalogActions // Layer 5 dependency for action888
    );
    
    // Layer 4B: Component Management (depends on Layer 4A)
    this.componentActions = new ComponentActions(
      contractManager, 
      arweaveManager, 
      ethersUtils, 
      config, 
      this.inviteActions
    );
  }

  /**
   * Execute action by number
   * @param {number} actionNumber - The action number to execute
   * @returns {Promise<Object>} - Action result
   */
  async executeAction(actionNumber) {
    const actionMap = {
      // Deploy actions
      0: () => this.deployActions.action0(),
      1: () => this.deployActions.action1(),
      5: (contractName) => this.deployActions.action5(contractName),

      // Setup actions (re-setup connections without re-deploy)
      2: () => this.setupActions.setupSystemConnections(),
      
      // Catalog actions (legacy format)
      4: () => this.catalogActions.action4(),
      6: () => this.catalogActions.action6(),
      40: () => this.catalogActions.action40(), // Alias for action4
      
      // Access Control actions
      9: () => this.accessControlActions.action9(),
      13: () => this.accessControlActions.action13(),
      
      // Invite actions
      7: (inviteCode) => this.inviteActions.action7(inviteCode),
      11: () => this.inviteActions.action11(),
      777: () => this.inviteActions.action777(),
      888: (inviteCode, sellerAddress, options) => this.inviteActions.action888(inviteCode, sellerAddress, options),
      
      // Component actions
      555: () => this.componentActions.action555(),
      
      // Catalog actions (new format)
      41: () => this.catalogActions.action41(),
      42: () => this.catalogActions.action42(),
      43: () => this.catalogActions.action43(),
      46: () => this.catalogActions.action46(),
      444: () => this.catalogActions.action444()
    };

    const action = actionMap[actionNumber];
    if (!action) {
      throw new Error(`Unknown action: ${actionNumber}`);
    }

    return await action();
  }

  /**
   * Get available actions
   * @returns {Array} - List of available action numbers
   */
  getAvailableActions() {
    return [0, 1, 2, 4, 5, 6, 7, 9, 11, 13, 40, 41, 42, 43, 46, 444, 555, 777, 888];
  }

  /**
   * Get action description
   * @param {number} actionNumber - The action number
   * @returns {string} - Action description
   */
  getActionDescription(actionNumber) {
    const descriptions = {
      0: "Deploy MagicRegistry",
      1: "Deploy all contracts + Setup connections",
      2: "Re-setup system connections (без редеплоя)",
      4: "Create catalog (inactive products) from legacy format",
      5: "Deploy single contract by name",
      6: "Clear seller catalog",
      7: "Create first seller (bootstrap with invite)",
      9: "Grant ACTIVATOR_ROLE to seller",
      11: "Generate invites for active seller",
      13: "Diagnose seller state (full diagnostics)",
      40: "Create catalog (inactive products) - alias for action 4",
      41: "Transform CSV → Product JSONs",
      42: "Unified Arweave Upload",
      43: "Contract Registration",
      46: "Activate existing products in catalog",
      444: "Automatic Pipeline (CSV → Arweave → Contract)",
      555: "Upload Components",
      777: "Create Root Invites",
      888: "Full Seller Initialization Pipeline (Complete Workflow)"
    };

    return descriptions[actionNumber] || `Unknown action: ${actionNumber}`;
  }
}

module.exports = {
  ActionsManager,
  DeployActions,
  SetupActions,
  AccessControlActions,
  InviteActions,
  CatalogActions,
  ComponentActions
};
