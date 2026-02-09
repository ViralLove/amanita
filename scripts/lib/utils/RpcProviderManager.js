/**
 * RPC Provider Manager
 * 
 * Manages alternative RPC endpoints for Polygon mainnet with automatic
 * fallback switching on rate limit errors.
 * 
 * @version 1.0.0
 * @date 2026-01-26
 */

const { ethers } = require('hardhat');

class RpcProviderManager {
  constructor(networkName, chainId, logger, primaryEndpoint = null) {
    this.networkName = networkName;
    this.chainId = chainId;
    this.logger = logger;
    
    // Initialize endpoints list
    this.endpoints = this._buildEndpointsList(primaryEndpoint);
    
    // Round-robin state
    this.currentIndex = 0;
    this.switchCount = 0;
    this.maxSwitches = 10;
    
    // Switch history for debugging
    this.switchHistory = [];
  }
  
  /**
   * Build list of alternative RPC endpoints
   * @private
   * @param {string|null} primaryEndpoint - Primary endpoint from env/config
   * @returns {Array<string>} - List of endpoints
   */
  _buildEndpointsList(primaryEndpoint) {
    // Order: most reliable first. publicnode last — diagnostic showed it returns hash but does not broadcast tx.
    const alternativeEndpoints = [
      'https://polygon-rpc.com', // ✅ Official Polygon endpoint (primary)
      'https://1rpc.io/matic', // ✅ 1RPC (Automata)
      'https://polygon.drpc.org', // ✅ dRPC
      'https://rpc-mainnet.matic.network', // ✅ Official Polygon backup
      'https://polygon-bor-rpc.publicnode.com', // ⚠️ Last: returns hash but may not broadcast (A1/A2)
      // REMOVED endpoints (not valid or require API key):
      // 'https://rpc.ankr.com/polygon', // ❌ Requires API key
      // 'https://polygon.llamarpc.com', // ❌ DNS not resolving (ENOTFOUND)
      // 'https://polygon.blockpi.network/v1/rpc/public', // ⚠️ May require registration
      // 'https://polygon.chainstacklabs.com', // ⚠️ May require registration
    ];
    
    // If primary endpoint is provided, use it as first
    if (primaryEndpoint) {
      // Remove primaryEndpoint from alternatives if it's there
      const filtered = alternativeEndpoints.filter(e => e !== primaryEndpoint);
      return [primaryEndpoint, ...filtered];
    }
    
    // Otherwise, use default first (polygon-rpc.com)
    return alternativeEndpoints;
  }
  
  /**
   * Get list of all alternative endpoints
   * @returns {Array<string>} - Copy of endpoints list
   */
  getAlternativeEndpoints() {
    return [...this.endpoints];
  }
  
  /**
   * Get next endpoint in round-robin fashion
   * Skips current endpoint to ensure we switch to a different one
   * @returns {string} - Next endpoint URL
   */
  getNextEndpoint() {
    // Check if max switches reached
    if (this.switchCount >= this.maxSwitches) {
      this.logger.warn(`[RPC] Max switches (${this.maxSwitches}) reached, resetting to first endpoint`);
      this.currentIndex = 0;
      this.switchCount = 0;
    }
    
    // CRITICAL: Increment index BEFORE getting endpoint to ensure we switch to a different one
    // This prevents returning the same endpoint that just failed
    this.currentIndex = (this.currentIndex + 1) % this.endpoints.length;
    this.switchCount++;
    
    // Get next endpoint (after increment)
    const endpoint = this.endpoints[this.currentIndex];
    
    // Log selection
    this.logger.info(`[RPC] Selected endpoint ${this.switchCount}/${this.endpoints.length}: ${endpoint}`);
    
    // Save to history
    this.switchHistory.push({
      index: this.currentIndex,
      endpoint: endpoint,
      timestamp: Date.now(),
      switchCount: this.switchCount
    });
    
    return endpoint;
  }
  
  /**
   * Create new ethers.JsonRpcProvider for given endpoint
   * @param {string} endpoint - RPC endpoint URL
   * @returns {ethers.JsonRpcProvider} - New provider instance
   */
  createProvider(endpoint) {
    this.logger.debug(`[RPC] Creating provider for endpoint: ${endpoint}`);
    const provider = new ethers.JsonRpcProvider(endpoint);
    return provider;
  }
  
  /**
   * Check if fallback should be used for this network
   * @returns {boolean} - True if fallback is needed (Polygon mainnet)
   */
  shouldUseFallback() {
    return this.chainId === 137;
  }
  
  /**
   * Get current endpoint (without incrementing index)
   * @returns {string} - Current endpoint URL
   */
  getCurrentEndpoint() {
    return this.endpoints[this.currentIndex];
  }
  
  /**
   * Reset round-robin state
   */
  reset() {
    this.currentIndex = 0;
    this.switchCount = 0;
    this.logger.debug(`[RPC] Reset round-robin state`);
  }
  
  /**
   * Get switch history
   * @returns {Array<Object>} - History of endpoint switches
   */
  getSwitchHistory() {
    return [...this.switchHistory];
  }
}

module.exports = RpcProviderManager;
