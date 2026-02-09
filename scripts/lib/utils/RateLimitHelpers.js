/**
 * Rate Limit Helpers
 * 
 * Centralized utilities for handling RPC rate limit errors with retry logic and endpoint switching.
 * 
 * @version 1.0.0
 * @date 2026-01-27
 */

const logger = require('./Logger');

/**
 * Check if error is nonce-related (nonce already used / too low).
 * Such errors should NOT trigger RPC switch; caller should refresh nonce and retry.
 * @param {Error} error - The error to check
 * @returns {boolean} - True if error is nonce-related
 */
function isNonceError(error) {
  if (!error) return false;
  const errorMessage = error.message || error.reason || String(error);
  const errorString = String(error);
  const errorCode = error.code || error.error?.code;
  const hasNonceMessage = (errorMessage.includes('nonce') && (errorMessage.includes('already been used') || errorMessage.includes('too low'))) ||
    (errorString.includes('nonce') && (errorString.includes('already been used') || errorString.includes('too low')));
  if (hasNonceMessage || errorCode === 'NONCE_EXPIRED') return true;
  // Nested format (e.g. "could not coalesce error" with nonce message)
  if (errorString.includes('nonce') && (errorString.includes('already been used') || errorString.includes('too low'))) return true;
  return false;
}

/**
 * Check if error requires endpoint switching (rate limit or authentication errors)
 * @param {Error} error - The error to check
 * @returns {boolean} - True if error requires switching to another endpoint
 */
function isEndpointSwitchError(error) {
  if (!error) return false;
  
  // Check error message (including nested error messages)
  const errorMessage = error.message || error.reason || String(error);
  const errorString = String(error);
  
  // Check for "could not coalesce error" format (ethers.js wraps RPC errors)
  const isCoalesceError = errorMessage.includes('could not coalesce error');
  // Check for "missing response for request" format (ethers.js wraps RPC errors differently)
  const isMissingResponseError = errorMessage.includes('missing response for request');
  let nestedRateLimit = false;
  let nestedAuthError = false;
  
  let nestedNonceError = false;
  if (isCoalesceError) {
    // Extract nested error message from "could not coalesce error" format
    const nestedErrorMatch = errorString.match(/"message":\s*"([^"]+)"/);
    if (nestedErrorMatch) {
      const nestedMessage = nestedErrorMatch[1];
      nestedRateLimit = nestedMessage.includes('rate limit') || 
                       nestedMessage.includes('Too many requests') ||
                       nestedMessage.includes('call rate limit exhausted');
      nestedNonceError = nestedMessage.includes('nonce') &&
        (nestedMessage.includes('already been used') || nestedMessage.includes('too low'));
      if (!nestedNonceError) {
        nestedAuthError = nestedMessage.includes('Unauthorized') ||
                         nestedMessage.includes('authenticate') ||
                         nestedMessage.includes('API key') ||
                         nestedMessage.includes('authentication');
      }
    }
  }
  
  if (isMissingResponseError) {
    // Extract nested error from "missing response for request" format
    // Format: missing response for request (value=[ { "error": { "code": -32000, "message": "Unauthorized: ..." } } ])
    const nestedErrorMatch = errorString.match(/"error":\s*\{[^}]*"code":\s*(-?\d+)[^}]*"message":\s*"([^"]+)"/);
    if (nestedErrorMatch) {
      const nestedCode = parseInt(nestedErrorMatch[1]);
      const nestedMessage = nestedErrorMatch[2];
      // Nonce errors (e.g. -32000 "nonce has already been used") must NOT be treated as auth
      nestedNonceError = nestedNonceError || (nestedMessage.includes('nonce') &&
        (nestedMessage.includes('already been used') || nestedMessage.includes('too low')));
      if (!nestedNonceError) {
        if (nestedCode === -32000 || nestedMessage.includes('Unauthorized') ||
            nestedMessage.includes('authenticate') || nestedMessage.includes('API key')) {
          nestedAuthError = true;
        }
      }
      if (nestedMessage.includes('rate limit') ||
          nestedMessage.includes('Too many requests') ||
          nestedMessage.includes('call rate limit exhausted')) {
        nestedRateLimit = true;
      }
    }
  }
  
  // Check for rate limit patterns
  const isRateLimit = errorMessage.includes('rate limit') || 
                     errorMessage.includes('Too many requests') ||
                     errorMessage.includes('call rate limit exhausted') ||
                     errorString.includes('rate limit') ||
                     errorString.includes('Too many requests') ||
                     errorString.includes('call rate limit exhausted') ||
                     nestedRateLimit;
  
  // Check for authentication/authorization errors (endpoints requiring API keys)
  // Check both errorMessage and errorString for various formats
  const isAuthError = errorMessage.includes('Unauthorized') ||
                      errorMessage.includes('authenticate') ||
                      errorMessage.includes('API key') ||
                      errorMessage.includes('authentication') ||
                      errorMessage.includes('authorization') ||
                      errorString.includes('Unauthorized') ||
                      errorString.includes('authenticate') ||
                      errorString.includes('API key') ||
                      errorString.includes('authentication') ||
                      errorString.includes('authorization') ||
                      nestedAuthError;
  
  // Also check error.info structure for nested errors (ethers.js format)
  let infoAuthError = false;
  if (error.info && typeof error.info === 'object') {
    const infoString = JSON.stringify(error.info);
    infoAuthError = infoString.includes('Unauthorized') ||
                   infoString.includes('authenticate') ||
                   infoString.includes('API key');
  }
  
  // Check for Gas Station API errors (should use fallback gas price, not switch endpoint)
  const isGasStationError = errorMessage.includes('gas station') ||
                            errorMessage.includes('Batch size too large') ||
                            errorString.includes('gas station') ||
                            errorString.includes('Batch size too large');
  
  // Check error type/name
  const errorType = error.constructor?.name || error.name || '';
  const isProviderError = errorType === 'ProviderError';
  
  // Check error code
  const errorCode = error.code || error.error?.code;
  const isRateLimitCode = errorCode === -32090 || errorCode === 'RATE_LIMIT' || errorCode === 'TOO_MANY_REQUESTS';
  const isAuthCode = errorCode === -32000 || errorCode === 'UNAUTHORIZED' || errorCode === 'AUTH_ERROR';
  const isGasStationCode = errorCode === -32062 || errorCode === 'SERVER_ERROR';
  
  // Check for RPC endpoint errors that require switching
  // "response body is not valid JSON" - RPC endpoint returned invalid response
  const isInvalidJsonError = errorMessage.includes('response body is not valid JSON') ||
                            errorMessage.includes('not valid JSON') ||
                            errorCode === 'UNSUPPORTED_OPERATION';
  
  // Check for network/connection errors
  const isNetworkError = errorMessage.includes('ECONNREFUSED') ||
                        errorMessage.includes('ETIMEDOUT') ||
                        errorMessage.includes('ENOTFOUND') ||
                        errorMessage.includes('network error') ||
                        errorMessage.includes('connection error');
  
  // Check for HTTP errors (404, 5xx) - these indicate endpoint is unavailable
  let isHttpError = false;
  let httpStatusCode = null;
  if (error.info && typeof error.info === 'object') {
    const responseStatus = error.info.responseStatus || error.info.status;
    if (responseStatus) {
      httpStatusCode = parseInt(responseStatus);
      // 404, 500, 502, 503, 504 indicate endpoint problems
      isHttpError = httpStatusCode === 404 || 
                   (httpStatusCode >= 500 && httpStatusCode < 600);
    }
  }
  // Also check error message for HTTP status codes
  if (!isHttpError && (errorMessage.includes('404') || errorMessage.includes('Not Found') ||
      errorMessage.includes('500') || errorMessage.includes('502') || 
      errorMessage.includes('503') || errorMessage.includes('504') ||
      errorMessage.includes('server response'))) {
    isHttpError = true;
    // Try to extract status code from message
    const statusMatch = errorMessage.match(/(\d{3})\s+(Not Found|Internal Server Error|Bad Gateway|Service Unavailable|Gateway Timeout)/i);
    if (statusMatch) {
      httpStatusCode = parseInt(statusMatch[1]);
    }
  }
  
  // ProviderError with rate limit or auth message requires switching
  const isProviderSwitchError = isProviderError && (isRateLimit || isAuthError);
  
  // Check for "replacement fee too low" - this is NOT an endpoint switch error (must be before use in if/return)
  const isReplacementFeeError = errorMessage.includes('replacement fee too low') ||
                                errorMessage.includes('replacement transaction underpriced') ||
                                errorCode === 'REPLACEMENT_UNDERPRICED';
  
  // Nonce errors (already used / too low) must NOT trigger endpoint switch; use standalone check
  const isNonceErrorResult = isNonceError(error) || nestedNonceError;
  
  // Log for debugging
  if (isRateLimit || isAuthError || isGasStationError || isHttpError || isProviderError || isCoalesceError || isMissingResponseError || isRateLimitCode || isAuthCode || isGasStationCode || isInvalidJsonError || isNetworkError || isReplacementFeeError || isNonceErrorResult) {
    logger.debug(`[ENDPOINT SWITCH CHECK] Checking error:`);
    logger.debug(`  - Error type: ${errorType}`);
    logger.debug(`  - Error code: ${errorCode || 'N/A'}`);
    logger.debug(`  - HTTP status: ${httpStatusCode || 'N/A'}`);
    logger.debug(`  - Error message: ${errorMessage.substring(0, 200)}`);
    logger.debug(`  - isCoalesceError: ${isCoalesceError}, isMissingResponseError: ${isMissingResponseError}`);
    logger.debug(`  - isRateLimit: ${isRateLimit}, isAuthError: ${isAuthError}, isHttpError: ${isHttpError}, isGasStationError: ${isGasStationError}`);
    logger.debug(`  - isInvalidJsonError: ${isInvalidJsonError}, isNetworkError: ${isNetworkError}, isReplacementFeeError: ${isReplacementFeeError}, isNonceError: ${isNonceErrorResult}`);
    logger.debug(`  - nestedRateLimit: ${nestedRateLimit}, nestedAuthError: ${nestedAuthError}, nestedNonceError: ${nestedNonceError}`);
    const requiresSwitch = (isRateLimit || isAuthError || isHttpError || isProviderSwitchError || nestedRateLimit || nestedAuthError || isRateLimitCode || isAuthCode || isInvalidJsonError || isNetworkError) && !isReplacementFeeError && !isNonceErrorResult;
    logger.debug(`  - Requires switch: ${requiresSwitch}`);
    logger.debug(`  - Note: Gas Station errors should use fallback gas price, not switch endpoint`);
    logger.debug(`  - Note: Replacement fee and nonce errors are nonce/gas issues, not endpoint problems`);
  }
  
  // Gas Station errors should NOT trigger endpoint switch (they're external API errors)
  // Replacement fee and nonce errors should NOT trigger endpoint switch (caller should refresh nonce / gas and retry)
  
  // Endpoint switch is required for: rate limits, auth errors, HTTP errors, invalid JSON responses, network errors
  return (isRateLimit || isAuthError || isHttpError || infoAuthError || isProviderSwitchError ||
          nestedRateLimit || nestedAuthError || isRateLimitCode || isAuthCode ||
          isInvalidJsonError || isNetworkError) && !isReplacementFeeError && !isNonceErrorResult;
}

/**
 * Check if error is "receipt not found after N polling attempts" (pollForReceipt timeout).
 * Used in waitForTransactionReceipt to trigger RPC switch when current endpoint
 * does not return receipt within maxAttempts (e.g. slow index or hidden rate limit).
 * @param {Error} error - The error to check
 * @returns {boolean} - True if error is receipt-not-found-after-polling
 */
function isReceiptNotFoundError(error) {
  if (!error) return false;
  const msg = error.message || error.reason || String(error);
  return msg.includes('Transaction receipt not found') && msg.includes('polling attempts');
}

/**
 * Check if error is a rate limit error (backward compatibility)
 * @param {Error} error - The error to check
 * @returns {boolean} - True if error is rate limit related
 */
function isRateLimitError(error) {
  if (!error) return false;
  
  // Check error message (including nested error messages)
  const errorMessage = error.message || error.reason || String(error);
  const errorString = String(error);
  
  // Check for "could not coalesce error" format (ethers.js wraps RPC errors)
  const isCoalesceError = errorMessage.includes('could not coalesce error');
  let nestedRateLimit = false;
  if (isCoalesceError) {
    const nestedErrorMatch = errorString.match(/"message":\s*"([^"]+)"/);
    if (nestedErrorMatch) {
      const nestedMessage = nestedErrorMatch[1];
      nestedRateLimit = nestedMessage.includes('rate limit') || 
                       nestedMessage.includes('Too many requests') ||
                       nestedMessage.includes('call rate limit exhausted');
    }
  }
  
  const isRateLimit = errorMessage.includes('rate limit') || 
                     errorMessage.includes('Too many requests') ||
                     errorMessage.includes('call rate limit exhausted') ||
                     errorString.includes('rate limit') ||
                     errorString.includes('Too many requests') ||
                     errorString.includes('call rate limit exhausted') ||
                     nestedRateLimit;
  
  const errorType = error.constructor?.name || error.name || '';
  const isProviderError = errorType === 'ProviderError';
  
  const errorCode = error.code || error.error?.code;
  const isRateLimitCode = errorCode === -32090 || errorCode === 'RATE_LIMIT' || errorCode === 'TOO_MANY_REQUESTS';
  
  const isProviderRateLimit = isProviderError && isRateLimit;
  
  return isRateLimit || isProviderRateLimit || nestedRateLimit || isRateLimitCode;
}

/**
 * Switch to alternative RPC endpoint if available
 * @param {Object} rpcManager - RpcProviderManager instance
 * @param {Object} ethersUtils - EthersUtils instance (will be updated)
 * @param {Object} contractManager - ContractManager instance (will be updated)
 * @returns {boolean} - True if switch was performed
 */
function switchToAlternativeEndpoint(rpcManager, ethersUtils, contractManager) {
  if (!rpcManager || !rpcManager.shouldUseFallback()) {
    return false;
  }
  
  const nextEndpoint = rpcManager.getNextEndpoint();
  logger.warn(`[RPC SWITCH] Switching to alternative endpoint: ${nextEndpoint}`);
  
  // Create new provider with alternative endpoint
  const newProvider = rpcManager.createProvider(nextEndpoint);
  
  // Update provider in EthersUtils (critical - ContractManager uses this)
  ethersUtils.provider = newProvider;
  
  // Update provider in ContractManager (for compatibility)
  if (contractManager) {
    contractManager.provider = newProvider;
  }
  
  logger.info(`[RPC SWITCH] Provider updated`);
  return true;
}

/**
 * Execute operation with rate limit retry and RPC switching
 * @param {Function} operation - Async function to execute
 * @param {Object} options - Retry options
 * @param {number} options.maxRetries - Maximum number of retries (default: 3)
 * @param {number} options.initialDelayMs - Initial delay in milliseconds (default: 10000)
 * @param {Object} options.rpcManager - RpcProviderManager instance (optional)
 * @param {Object} options.ethersUtils - EthersUtils instance (optional, for RPC switching)
 * @param {Object} options.contractManager - ContractManager instance (optional, for RPC switching)
 * @param {string} options.operationName - Name of operation for logging (optional)
 * @returns {Promise<any>} - Result of operation
 */
async function executeWithRateLimitRetry(operation, options = {}) {
  const {
    maxRetries = 3,
    initialDelayMs = 10000,
    rpcManager = null,
    ethersUtils = null,
    contractManager = null,
    operationName = 'operation'
  } = options;
  
  let lastError;
  
  logger.info(`[RETRY] Starting ${operationName} with maxRetries=${maxRetries}, initialDelayMs=${initialDelayMs}`);
  
  for (let attempt = 1; attempt <= maxRetries; attempt++) {
    try {
      logger.info(`[RETRY] Attempt ${attempt}/${maxRetries} for ${operationName}...`);
      const result = await operation();
      logger.info(`[RETRY] ✅ Success on attempt ${attempt}/${maxRetries} for ${operationName}`);
      return result;
    } catch (error) {
      lastError = error;
      
      // Check if error requires endpoint switching (rate limit, auth, or HTTP errors)
      const requiresSwitch = isEndpointSwitchError(error);
      const canRetry = attempt < maxRetries;
      
      logger.warn(`[RETRY] ❌ Attempt ${attempt}/${maxRetries} failed for ${operationName}`);
      logger.warn(`[RETRY]   - Error: ${error.message || String(error).substring(0, 200)}`);
      logger.warn(`[RETRY]   - Requires switch: ${requiresSwitch}, Can retry: ${canRetry}`);
      
      // Log full error details for debugging
      logger.debug(`[RETRY] Full error details:`, error);
      
      if (requiresSwitch && canRetry) {
        const waitTime = initialDelayMs * attempt;
        
        // Determine error type for logging
        const errorMessage = error.message || String(error);
        const isAuthError = errorMessage.includes('Unauthorized') ||
                           errorMessage.includes('authenticate') ||
                           errorMessage.includes('API key');
        const isHttpError = errorMessage.includes('404') || 
                           errorMessage.includes('Not Found') ||
                           errorMessage.includes('server response') ||
                           (error.info && error.info.responseStatus);
        
        if (isAuthError) {
          logger.warn(`[AUTH ERROR] Endpoint requires authentication during ${operationName} (attempt ${attempt}/${maxRetries})`);
          logger.warn(`[AUTH ERROR] Switching to next endpoint...`);
        } else if (isHttpError) {
          const status = error.info?.responseStatus || 'unknown';
          logger.warn(`[HTTP ERROR] Endpoint returned HTTP ${status} during ${operationName} (attempt ${attempt}/${maxRetries})`);
          logger.warn(`[HTTP ERROR] Switching to next endpoint...`);
        } else {
          logger.warn(`[RATE LIMIT] Rate limit hit during ${operationName} (attempt ${attempt}/${maxRetries})`);
        }
        
        // Switch to alternative endpoint if available
        const switched = switchToAlternativeEndpoint(rpcManager, ethersUtils, contractManager);
        
        if (!switched) {
          logger.warn(`[RETRY] No alternative endpoint available, waiting ${waitTime/1000}s before retry...`);
        } else {
          logger.info(`[RPC SWITCH] Switched to alternative endpoint, waiting ${waitTime/1000}s before retry...`);
        }
        
        logger.debug(`[RETRY] Waiting ${waitTime/1000}s before retry (attempt ${attempt}/${maxRetries})...`);
        await new Promise(resolve => setTimeout(resolve, waitTime));
        logger.info(`[RETRY] Wait completed, retrying operation with ${switched ? 'new' : 'same'} endpoint...`);
        continue; // Retry operation with new endpoint
      }
      
      // Not an endpoint switch error, or max retries reached
      if (!requiresSwitch) {
        logger.error(`[RETRY] ❌ Error does not require endpoint switch: ${error.message || String(error).substring(0, 200)}`);
        logger.error(`[RETRY] This error type is not handled by RPC switching. Check error details above.`);
      } else {
        logger.error(`[RETRY] ❌ Max retries (${maxRetries}) reached for ${operationName}. Last error: ${error.message || String(error).substring(0, 200)}`);
        logger.error(`[RETRY] All retry attempts exhausted. Check RPC endpoints availability.`);
      }
      throw error;
    }
  }
  
  logger.error(`[RETRY] Failed ${operationName} after ${maxRetries} attempts. Last error: ${lastError?.message || 'unknown'}`);
  throw lastError || new Error(`Failed ${operationName} after ${maxRetries} attempts`);
}

/**
 * Poll for transaction receipt with rate limit handling
 * @param {Object} provider - Ethers provider
 * @param {string} txHash - Transaction hash
 * @param {Object} options - Polling options
 * @param {number} options.maxAttempts - Maximum polling attempts (default: 60)
 * @param {number} options.pollIntervalMs - Polling interval in milliseconds (default: 2000)
 * @param {Function} options.isRateLimitError - Rate limit check function (optional, uses default if not provided)
 * @returns {Promise<Object>} - Transaction receipt
 */
async function pollForReceipt(provider, txHash, options = {}) {
  const {
    maxAttempts = 60,
    pollIntervalMs = 2000,
    isRateLimitError: customIsRateLimitError = isEndpointSwitchError
  } = options;
  
  for (let i = 0; i < maxAttempts; i++) {
    try {
      const receipt = await provider.getTransactionReceipt(txHash);
      if (receipt) {
        return receipt;
      }
      // Receipt not ready yet, wait before next poll
      await new Promise(resolve => setTimeout(resolve, pollIntervalMs));
    } catch (error) {
      // Re-throw endpoint switch errors (rate limit, auth, HTTP) to trigger retry with endpoint switch
      if (customIsRateLimitError(error)) {
        throw error;
      }
      // Other errors: wait and retry polling (network issues, etc.)
      logger.debug(`[POLL] Error polling receipt (attempt ${i + 1}/${maxAttempts}): ${error.message || String(error)}`);
      await new Promise(resolve => setTimeout(resolve, pollIntervalMs));
    }
  }
  throw new Error(`Transaction receipt not found after ${maxAttempts} polling attempts`);
}

/**
 * Wait for transaction receipt with retry and RPC switching
 * Supports both deploymentTx.wait() and polling fallback
 * @param {Object} deploymentTx - Deployment transaction object (optional)
 * @param {string} txHash - Transaction hash
 * @param {Object} provider - Ethers provider
 * @param {Object} options - Wait options
 * @param {number} options.maxRetries - Maximum retries (default: 3)
 * @param {number} options.initialDelayMs - Initial delay in milliseconds (default: 10000)
 * @param {Object} options.rpcManager - RpcProviderManager instance (optional)
 * @param {Object} options.ethersUtils - EthersUtils instance (optional, for RPC switching)
 * @param {Object} options.contractManager - ContractManager instance (optional, for RPC switching)
 * @param {string} options.contractName - Contract name for logging (optional)
 * @returns {Promise<Object>} - Transaction receipt
 */
async function waitForTransactionReceipt(deploymentTx, txHash, provider, options = {}) {
  const {
    maxRetries = 3,
    initialDelayMs = 10000,
    rpcManager = null,
    ethersUtils = null,
    contractManager = null,
    contractName = 'contract'
  } = options;
  
  if (!txHash) {
    throw new Error(`Transaction hash not available for ${contractName}`);
  }
  
  let receipt;
  let lastError;
  
  for (let attempt = 1; attempt <= maxRetries; attempt++) {
    try {
      // CRITICAL: For regular transactions (not deployments), always use polling
      // because tx.wait() uses internal txListener that can't be caught for rate limit errors
      // Only try tx.wait() for deployment transactions (which are typically slower and benefit from it)
      const isDeploymentTx = deploymentTx && contractName && (
        contractName.toLowerCase().includes('deploy') || 
        contractName.toLowerCase().includes('contract')
      );
      
      // Try deploymentTx.wait() first ONLY for deployment transactions
      if (attempt === 1 && isDeploymentTx && deploymentTx && typeof deploymentTx.wait === 'function') {
        try {
          logger.debug(`[WAIT] Using deploymentTx.wait() for deployment ${txHash} (attempt ${attempt}/${maxRetries})`);
          
          // Wrap in Promise.resolve to ensure proper error handling
          receipt = await Promise.resolve(deploymentTx.wait()).catch((waitError) => {
            logger.debug(`[WAIT] deploymentTx.wait() Promise catch: ${waitError.message || String(waitError)}`);
            throw waitError;
          });
          
          logger.debug(`[WAIT] Successfully received receipt via deploymentTx.wait()`);
          return receipt;
        } catch (waitError) {
          logger.debug(`[WAIT] deploymentTx.wait() caught error: ${waitError.message || String(waitError)}`);
          logger.debug(`[WAIT] Error type: ${waitError.constructor?.name || waitError.name || 'unknown'}`);
          
          // If waitForTransaction is not implemented, fall through to polling
          if (waitError.message && waitError.message.includes('waitForTransaction') && waitError.message.includes('not implemented')) {
            logger.debug(`[WAIT] deploymentTx.wait() not supported, falling back to polling`);
            // Fall through to polling approach
          } else if (isEndpointSwitchError(waitError)) {
            // Rate limit or auth error during wait - deploymentTx.wait() uses old provider
            // We need to switch endpoint and use polling with new provider
            logger.warn(`[WAIT] Rate limit/auth error detected in deploymentTx.wait(), switching to polling with updated provider`);
            logger.warn(`[WAIT] deploymentTx.wait() uses Hardhat's internal provider which may have rate limits`);
            logger.warn(`[WAIT] Will use polling with updated provider instead`);
            throw waitError; // Re-throw to be caught by outer catch block for endpoint switch
          } else {
            // Other error, try polling
            logger.debug(`[WAIT] deploymentTx.wait() failed, falling back to polling: ${waitError.message}`);
          }
        }
      }
      
      // For regular transactions OR if deploymentTx.wait() failed, use polling
      // Polling gives us full control over RPC calls and can handle rate limits properly
      // CRITICAL: Use ethersUtils.provider if available (may have been updated after RPC switch)
      // Otherwise fall back to provided provider
      const currentProvider = ethersUtils?.provider || provider;
      
      // Log provider URL for debugging (try to extract from provider connection)
      let providerUrl = 'unknown';
      try {
        if (currentProvider.connection?.url) {
          providerUrl = currentProvider.connection.url;
        } else if (currentProvider._getConnection) {
          const conn = currentProvider._getConnection();
          providerUrl = conn?.url || 'unknown';
        } else if (currentProvider._network?.then) {
          // Hardhat provider - extract from network config
          providerUrl = 'Hardhat provider';
        }
      } catch (e) {
        // Ignore errors when extracting URL
      }
      
      logger.info(`[WAIT] Polling for transaction receipt: ${txHash} (attempt ${attempt}/${maxRetries})`);
      logger.info(`[WAIT] Using provider: ${providerUrl}`);
      receipt = await pollForReceipt(currentProvider, txHash, {
        isRateLimitError: isEndpointSwitchError,
        maxAttempts: 120, // Increased from 60 to 120 (4 minutes total)
        pollIntervalMs: 2000
      });
      logger.debug(`[WAIT] Successfully received receipt via polling`);
      return receipt;
    } catch (error) {
      lastError = error;
      
      // Check if error requires endpoint switching (rate limit, auth errors, or receipt-not-found timeout)
      if ((isEndpointSwitchError(error) || isReceiptNotFoundError(error)) && attempt < maxRetries) {
        const waitTime = initialDelayMs * attempt;
        
        if (isReceiptNotFoundError(error) && !isEndpointSwitchError(error)) {
          logger.warn(`[WAIT] Receipt not found after polling (attempt ${attempt}/${maxRetries}), switching RPC. TX: ${txHash}`);
        } else {
          // Determine error type for logging (rate limit or auth)
          const isAuthError = (error.message || String(error)).includes('Unauthorized') ||
                             (error.message || String(error)).includes('authenticate') ||
                             (error.message || String(error)).includes('API key');
          if (isAuthError) {
            logger.warn(`[AUTH ERROR] Endpoint requires authentication while waiting for ${contractName} receipt (attempt ${attempt}/${maxRetries})`);
            logger.warn(`[AUTH ERROR] Transaction hash: ${txHash}`);
          } else {
            logger.warn(`[RATE LIMIT] Rate limit hit while waiting for ${contractName} receipt (attempt ${attempt}/${maxRetries})`);
            logger.warn(`[RATE LIMIT] Transaction hash: ${txHash}`);
          }
        }
        
        // Switch to alternative endpoint if available
        const switched = switchToAlternativeEndpoint(rpcManager, ethersUtils, contractManager);
        
        if (!switched) {
          logger.warn(`[RETRY] Waiting ${waitTime/1000}s before retry...`);
        } else {
          logger.info(`[RPC SWITCH] Waiting ${waitTime/1000}s before retry...`);
        }
        
        await new Promise(resolve => setTimeout(resolve, waitTime));
        continue; // Retry polling with (possibly) new provider
      } else {
        // Not an endpoint switch error, or max retries reached
        throw error;
      }
    }
  }
  
  throw lastError || new Error(`Failed to get receipt for ${contractName} after ${maxRetries} attempts. TX: ${txHash || 'unknown'}`);
}

module.exports = {
  isRateLimitError,
  isEndpointSwitchError,
  isNonceError,
  isReceiptNotFoundError,
  switchToAlternativeEndpoint,
  executeWithRateLimitRetry,
  pollForReceipt,
  waitForTransactionReceipt
};
