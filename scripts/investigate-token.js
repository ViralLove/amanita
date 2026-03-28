/**
 * Token Investigation Script - Polygon Token Analyzer
 * 
 * Investigates a token on Polygon network, finds specific transfer transactions,
 * and retrieves recipient balance information.
 * 
 * Usage:
 *   # Direct transaction lookup (fastest - recommended if you have tx hash)
 *   npx hardhat run scripts/investigate-token.js --network polygon [tokenAddress] [targetAmount] [maxBlocks] [fromAddress] [txHash]
 *   
 *   # Search through blocks (slower)
 *   npx hardhat run scripts/investigate-token.js --network polygon [tokenAddress] [targetAmount] [maxBlocks] [fromAddress]
 * 
 * Examples:
 *   # Direct transaction lookup (FASTEST - if you have transaction hash)
 *   npx hardhat run scripts/investigate-token.js --network polygon 0xFF5053F2bE129c7A1BbcA839a93ebB027e80eF5a 3030.888 0 null 0xYourTxHash
 *   
 *   # Use default values and search blocks (SLOWER)
 *   npx hardhat run scripts/investigate-token.js --network polygon
 *   
 *   # Custom token, amount, and search range
 *   npx hardhat run scripts/investigate-token.js --network polygon 0xFF5053F2bE129c7A1BbcA839a93ebB027e80eF5a 3030.888 500000
 * 
 * Note: Uses network configuration from hardhat.config.js (uses hre.network.provider directly)
 * 
 * @version 1.0.0
 * @date 2025-01-XX
 */

// Load environment variables
require('dotenv').config();

// Import dependencies
const { ethers } = require('hardhat');
const logger = require('./lib/utils/Logger');

// Constants
const DEFAULT_TOKEN_ADDRESS = '0xFF5053F2bE129c7A1BbcA839a93ebB027e80eF5a';
const DEFAULT_TARGET_AMOUNT = 3030.888;
const DEFAULT_MAX_BLOCKS = 500000; // ~58 days on Polygon (2 sec/block, ~17.3 days per 100k blocks)
const DEFAULT_FROM_ADDRESS = '0x12dc497c4f65c275ee13e385bb67fdd6c689a8f4'; // Sender address for transaction search
const CHUNK_SIZE = 100; // blocks per chunk (public RPC providers usually limit to 100-500 blocks)
const REQUEST_DELAY_MS = 200; // Delay between requests to avoid rate limits (200ms = 5 requests/sec)
const RETRY_DELAY_MS = 10000; // Delay before retry on rate limit (10 seconds)
const MAX_RETRIES = 3; // Maximum retries for rate-limited requests
const DEFAULT_TX_HASH = null; // Optional: transaction hash to get directly

// Load ERC20 ABI with metadata (includes name, symbol, decimals)
const IERC20_ABI = require('../bot/artifacts/@openzeppelin/contracts/token/ERC20/extensions/IERC20Metadata.sol/IERC20Metadata.json').abi;

// ====================================================================
// 🔧 HELPER FUNCTIONS
// ====================================================================

/**
 * Validate Ethereum address format
 * @param {string} address - Address to validate
 * @returns {string} - Validated address with checksum
 * @throws {Error} - If address is invalid
 */
function validateAddress(address) {
  if (!ethers.isAddress(address)) {
    throw new Error(`Invalid address: ${address}`);
  }
  return ethers.getAddress(address); // Returns checksummed address
}

/**
 * Initialize Polygon provider using Hardhat network configuration
 * @returns {Promise<ethers.JsonRpcProvider>} - Initialized provider
 */
async function initializeProvider() {
  logger.info('Initializing Polygon provider...');
  
  try {
    // Try to use Hardhat's provider if available (when run via hardhat run)
    let provider;
    let rpcUrl;
    
    try {
      const hre = require('hardhat');
      if (hre.network && hre.network.provider) {
        provider = hre.network.provider;
        logger.debug(`Hardhat network name: ${hre.network.name}`);
        logger.debug(`Using Hardhat provider for network '${hre.network.name}'`);
      } else {
        throw new Error('Hardhat network provider not available');
      }
    } catch (hreError) {
      // Fallback: create provider from config or env
      logger.debug('Hardhat runtime not available, creating provider from config...');
      
      // Try to load hardhat config
      try {
        const hre = require('hardhat');
        const networkConfig = hre.config.networks?.polygon;
        if (networkConfig && networkConfig.url) {
          rpcUrl = networkConfig.url;
          logger.debug(`Using RPC URL from hardhat.config.js: ${rpcUrl.substring(0, 30)}...`);
        }
      } catch (configError) {
        // Ignore config errors, use env fallback
      }
      
      if (!rpcUrl) {
        rpcUrl = process.env.POLYGON_MAINNET_RPC || 'https://polygon-rpc.com';
        logger.debug(`Using RPC URL from env or fallback: ${rpcUrl.substring(0, 30)}...`);
      }
      
      provider = new ethers.JsonRpcProvider(rpcUrl);
    }
    
    // Test connection
    logger.debug('Testing connection to Polygon mainnet...');
    const network = await provider.getNetwork();
    logger.debug(`Network info retrieved: Chain ID ${network.chainId}, Name: ${network.name}`);
    
    // Verify it's Polygon mainnet (Chain ID 137)
    if (network.chainId !== 137n) {
      logger.warn(`⚠️  Warning: Connected to chain ID ${network.chainId}, expected 137 (Polygon Mainnet)`);
    }
    
    const blockNumber = await provider.getBlockNumber();
    logger.debug(`Current block number retrieved: ${blockNumber}`);
    
    logger.info(`✅ Connected to Polygon Mainnet (Chain ID: ${network.chainId})`);
    logger.info(`📦 Current block: ${blockNumber.toLocaleString()}`);
    
    return provider;
  } catch (error) {
    logger.error(`❌ Failed to connect to Polygon: ${error.message}`);
    logger.error(`Make sure to run with: npx hardhat run scripts/investigate-token.js --network polygon`);
    throw error;
  }
}

/**
 * Calculate target amount with tolerance for rounding
 * @param {number} targetAmount - Target amount in token units
 * @param {number} decimals - Token decimals
 * @returns {Object} - {exact, min, max} BigInt values
 */
function calculateTargetAmount(targetAmount, decimals) {
  const amountBigInt = ethers.parseUnits(targetAmount.toString(), decimals);
  // Tolerance: ±0.001 from target amount
  const tolerance = ethers.parseUnits('0.001', decimals);
  return {
    exact: amountBigInt,
    min: amountBigInt - tolerance,
    max: amountBigInt + tolerance
  };
}

// ====================================================================
// 📊 TOKEN INFORMATION
// ====================================================================

/**
 * Get token information (name, symbol, decimals, totalSupply)
 * @param {ethers.JsonRpcProvider} provider - Ethers provider
 * @param {string} tokenAddress - Token contract address
 * @returns {Promise<Object>} - Token information
 */
async function getTokenInfo(provider, tokenAddress) {
  logger.debug(`Creating ERC20 contract instance for ${tokenAddress}...`);
  const tokenContract = new ethers.Contract(tokenAddress, IERC20_ABI, provider);
  logger.debug('Contract instance created, ABI loaded');
  
  try {
    logger.debug('Calling token contract methods: name(), symbol(), decimals(), totalSupply()...');
    
    // All methods should be available in IERC20Metadata ABI
    // Try to call methods directly, with fallback handling
    const [nameResult, symbolResult, decimalsResult, totalSupplyResult] = await Promise.allSettled([
      tokenContract.name().catch((e) => { logger.debug(`name() failed: ${e.message}`); return null; }),
      tokenContract.symbol().catch((e) => { logger.debug(`symbol() failed: ${e.message}`); return null; }),
      tokenContract.decimals().catch((e) => { logger.debug(`decimals() failed: ${e.message}`); return null; }),
      tokenContract.totalSupply().catch((e) => { logger.debug(`totalSupply() failed: ${e.message}`); return null; })
    ]);
    
    logger.debug('All token method calls completed');
    
    // Extract values from Promise.allSettled results
    const name = nameResult.status === 'fulfilled' && nameResult.value ? nameResult.value : 'Unknown Token';
    const symbol = symbolResult.status === 'fulfilled' && symbolResult.value ? symbolResult.value : 'UNKNOWN';
    
    logger.debug(`Token name: ${name}, symbol: ${symbol}`);
    
    let decimals = 18; // Default fallback
    if (decimalsResult.status === 'fulfilled' && decimalsResult.value !== null) {
      decimals = Number(decimalsResult.value);
      logger.debug(`Decimals retrieved: ${decimals}`);
    } else {
      logger.warn(`⚠️  decimals() method failed or not available, using default: 18`);
      logger.debug(`Decimals result: status=${decimalsResult.status}, value=${decimalsResult.value}`);
    }
    
    let totalSupplyFormatted = 'N/A';
    if (totalSupplyResult.status === 'fulfilled' && totalSupplyResult.value !== null) {
      totalSupplyFormatted = ethers.formatUnits(totalSupplyResult.value, decimals);
      logger.debug(`Total supply (raw): ${totalSupplyResult.value.toString()}, formatted: ${totalSupplyFormatted}`);
    } else {
      logger.warn(`⚠️  totalSupply() method failed or not available`);
      logger.debug(`TotalSupply result: status=${totalSupplyResult.status}, value=${totalSupplyResult.value}`);
    }
    
    logger.info(`✅ Token info retrieved successfully`);
    
    return {
      name,
      symbol,
      decimals,
      totalSupply: totalSupplyFormatted
    };
  } catch (error) {
    logger.error(`❌ Failed to get token info: ${error.message}`);
    logger.debug(`Error stack: ${error.stack}`);
    throw error;
  }
}

// ====================================================================
// 🔍 TRANSACTION SEARCH
// ====================================================================

/**
 * Find Transfer events matching target amount (chunked search)
 * @param {ethers.JsonRpcProvider} provider - Ethers provider
 * @param {string} tokenAddress - Token contract address
 * @param {number} targetAmount - Target amount to search for
 * @param {number} decimals - Token decimals
 * @param {number} maxBlocks - Maximum blocks to search (default: DEFAULT_MAX_BLOCKS)
 * @param {string} fromAddress - Optional: filter by sender address (much faster)
 * @returns {Promise<Array>} - Array of matching Transfer events
 */
async function findTransferByAmountChunked(provider, tokenAddress, targetAmount, decimals, maxBlocks = DEFAULT_MAX_BLOCKS, fromAddress = null) {
  logger.debug('Calculating target amount range...');
  const { exact, min, max } = calculateTargetAmount(targetAmount, decimals);
  logger.debug(`Target amount calculation: exact=${exact.toString()}, min=${min.toString()}, max=${max.toString()}`);
  
  logger.debug(`Creating contract instance for filtering Transfer events...`);
  const tokenContract = new ethers.Contract(tokenAddress, IERC20_ABI, provider);
  
  logger.debug('Getting current block number...');
  const currentBlock = await provider.getBlockNumber();
  const fromBlock = Math.max(0, currentBlock - maxBlocks);
  
  logger.info(`🔍 Searching Transfer events from block ${fromBlock.toLocaleString()} to ${currentBlock.toLocaleString()}...`);
  logger.info(`   Block range: ${(currentBlock - fromBlock).toLocaleString()} blocks`);
  logger.info(`   Target amount: ${targetAmount} (search range: ${ethers.formatUnits(min, decimals)} - ${ethers.formatUnits(max, decimals)})`);
  if (fromAddress) {
    logger.info(`   Filter by sender: ${fromAddress}`);
  } else {
    logger.info(`   No sender filter: searching all transfers`);
  }
  logger.info(`   Chunk size: ${CHUNK_SIZE} blocks per request`);
  
  const totalChunks = Math.ceil((currentBlock - fromBlock) / CHUNK_SIZE);
  logger.debug(`Total chunks to process: ${totalChunks}`);
  
  const matchingEvents = [];
  let processedBlocks = 0;
  const totalBlocks = currentBlock - fromBlock;
  let totalEventsChecked = 0;
  let chunkNumber = 0;
  
  // Helper function to query with retry logic
  const queryWithRetry = async (filter, start, end, retryCount = 0) => {
    try {
      await new Promise(resolve => setTimeout(resolve, REQUEST_DELAY_MS)); // Rate limiting
      const events = await tokenContract.queryFilter(filter, start, end);
      return { success: true, events };
    } catch (error) {
      const isRateLimit = error.message?.includes('rate limit') || 
                          error.code === 'UNKNOWN_ERROR' && error.data?.message?.includes('rate limit') ||
                          error.data?.message?.includes('Too many requests');
      
      if (isRateLimit && retryCount < MAX_RETRIES) {
        const waitTime = RETRY_DELAY_MS * (retryCount + 1); // Exponential backoff
        logger.warn(`⚠️  Rate limit hit for blocks ${start}-${end}, waiting ${waitTime/1000}s before retry ${retryCount + 1}/${MAX_RETRIES}...`);
        await new Promise(resolve => setTimeout(resolve, waitTime));
        return queryWithRetry(filter, start, end, retryCount + 1);
      }
      throw error;
    }
  };
  
  for (let start = fromBlock; start <= currentBlock; start += CHUNK_SIZE) {
    chunkNumber++;
    const end = Math.min(start + CHUNK_SIZE - 1, currentBlock);
    
    try {
      logger.debug(`Processing chunk ${chunkNumber}/${totalChunks}: blocks ${start}-${end}...`);
      
      // Filter by sender address if provided (much faster)
      const filter = fromAddress 
        ? tokenContract.filters.Transfer(fromAddress, null)  // from address is indexed
        : tokenContract.filters.Transfer();
      
      logger.debug(`Querying Transfer events for blocks ${start}-${end}...`);
      const result = await queryWithRetry(filter, start, end);
      const events = result.events;
      logger.debug(`Found ${events.length} Transfer event(s) in blocks ${start}-${end}`);
      
      totalEventsChecked += events.length;
      
      const matched = events.filter(e => {
        const value = e.args.value;
        const isMatch = value >= min && value <= max;
        if (isMatch) {
          logger.debug(`Match found! Value: ${ethers.formatUnits(value, decimals)}, TX: ${e.transactionHash}`);
        }
        return isMatch;
      });
      
      matchingEvents.push(...matched);
      
      processedBlocks += (end - start + 1);
      const progress = ((processedBlocks / totalBlocks) * 100).toFixed(1);
      
      if (matched.length > 0) {
        logger.info(`✅ Found ${matched.length} match(es) in blocks ${start.toLocaleString()}-${end.toLocaleString()} (Progress: ${progress}%)`);
      } else if (chunkNumber % 50 === 0 || chunkNumber === 1) {
        // Show progress every 50 chunks or on first chunk
        logger.info(`   Progress: ${progress}% (chunk ${chunkNumber}/${totalChunks}, ${events.length} events checked in this chunk)`);
      }
      
    } catch (error) {
      logger.warn(`⚠️  Failed to query blocks ${start}-${end} after retries: ${error.message}`);
      logger.debug(`Error details: ${error.code || 'unknown'}, ${error.data?.message || error.message}`);
      // Continue search despite errors in individual chunks
    }
  }
  
  logger.info(`✅ Search complete!`);
  logger.info(`   Total events checked: ${totalEventsChecked.toLocaleString()}`);
  logger.info(`   Matching transactions found: ${matchingEvents.length}`);
  
  return matchingEvents;
}

/**
 * Get transaction directly by hash and extract Transfer events
 * @param {ethers.JsonRpcProvider} provider - Ethers provider
 * @param {string} tokenAddress - Token contract address
 * @param {string} txHash - Transaction hash
 * @param {number} decimals - Token decimals
 * @param {number} targetAmount - Target amount to filter (optional)
 * @returns {Promise<Array>} - Array of matching Transfer events with enriched data
 */
async function getTransactionByHash(provider, tokenAddress, txHash, decimals, targetAmount = null) {
  logger.info(`Getting transaction directly by hash: ${txHash}`);
  
  try {
    // Get transaction and receipt
    logger.debug('Fetching transaction and receipt...');
    const tx = await provider.getTransaction(txHash);
    const receipt = await provider.getTransactionReceipt(txHash);
    
    if (!tx || !receipt) {
      throw new Error(`Transaction ${txHash} not found`);
    }
    
    logger.debug(`Transaction found: block ${receipt.blockNumber}, status: ${receipt.status}`);
    
    // Get block for timestamp
    const block = await provider.getBlock(receipt.blockNumber);
    
    // Create contract interface to parse logs
    const tokenContract = new ethers.Contract(tokenAddress, IERC20_ABI, provider);
    const iface = tokenContract.interface;
    
    // Parse Transfer events from logs
    const transferEvents = [];
    for (const log of receipt.logs) {
      try {
        // Check if this log is from our token contract
        if (log.address.toLowerCase() !== tokenAddress.toLowerCase()) {
          continue;
        }
        
        // Try to parse as Transfer event
        const parsedLog = iface.parseLog(log);
        if (parsedLog && parsedLog.name === 'Transfer') {
          const value = parsedLog.args.value;
          
          // If target amount specified, filter by it
          if (targetAmount !== null) {
            const { min, max } = calculateTargetAmount(targetAmount, decimals);
            if (value < min || value > max) {
              logger.debug(`Transfer event amount ${ethers.formatUnits(value, decimals)} doesn't match target ${targetAmount}, skipping`);
              continue;
            }
          }
          
          transferEvents.push({
            txHash: txHash,
            blockNumber: receipt.blockNumber,
            timestamp: new Date(block.timestamp * 1000),
            from: parsedLog.args.from,
            to: parsedLog.args.to,
            amount: ethers.formatUnits(value, decimals),
            amountRaw: value.toString(),
            gasPrice: tx.gasPrice ? ethers.formatUnits(tx.gasPrice, 'gwei') + ' gwei' : 'N/A',
            gasUsed: receipt.gasUsed.toString(),
            status: receipt.status === 1 ? 'success' : 'failed'
          });
        }
      } catch (parseError) {
        // Not a Transfer event, skip
        continue;
      }
    }
    
    logger.info(`✅ Found ${transferEvents.length} Transfer event(s) in transaction ${txHash}`);
    return transferEvents;
    
  } catch (error) {
    logger.error(`❌ Failed to get transaction ${txHash}: ${error.message}`);
    throw error;
  }
}

/**
 * Process Transfer events and enrich with block/tx data
 * @param {ethers.JsonRpcProvider} provider - Ethers provider
 * @param {Array} events - Transfer events from queryFilter
 * @param {number} decimals - Token decimals
 * @returns {Promise<Array>} - Enriched transaction data
 */
async function processTransferEvents(provider, events, decimals) {
  const results = [];
  
  logger.info(`Processing ${events.length} transfer event(s)...`);
  
  for (let i = 0; i < events.length; i++) {
    const event = events[i];
    
    try {
      const block = await provider.getBlock(event.blockNumber);
      const tx = await provider.getTransaction(event.transactionHash);
      
      results.push({
        txHash: event.transactionHash,
        blockNumber: event.blockNumber,
        timestamp: new Date(block.timestamp * 1000),
        from: event.args.from,
        to: event.args.to,
        amount: ethers.formatUnits(event.args.value, decimals),
        amountRaw: event.args.value.toString(),
        gasPrice: tx.gasPrice ? ethers.formatUnits(tx.gasPrice, 'gwei') + ' gwei' : 'N/A'
      });
      
      logger.debug(`  Processed ${i + 1}/${events.length}: ${event.transactionHash}`);
    } catch (error) {
      logger.warn(`Failed to process event ${event.transactionHash}: ${error.message}`);
      // Continue processing other events
    }
  }
  
  return results;
}

// ====================================================================
// 💰 BALANCE QUERIES
// ====================================================================

/**
 * Get token balance for an address
 * @param {ethers.JsonRpcProvider} provider - Ethers provider
 * @param {string} tokenAddress - Token contract address
 * @param {string} recipientAddress - Address to check balance for
 * @param {number} decimals - Token decimals
 * @returns {Promise<Object>} - Balance information (raw and formatted)
 */
async function getRecipientBalance(provider, tokenAddress, recipientAddress, decimals) {
  const tokenContract = new ethers.Contract(tokenAddress, IERC20_ABI, provider);
  
  try {
    const balance = await tokenContract.balanceOf(recipientAddress);
    return {
      raw: balance.toString(),
      formatted: ethers.formatUnits(balance, decimals)
    };
  } catch (error) {
    logger.error(`Failed to get balance: ${error.message}`);
    throw error;
  }
}

// ====================================================================
// 📋 OUTPUT FORMATTING
// ====================================================================

/**
 * Format and display results
 * @param {Object} tokenInfo - Token information
 * @param {Array} transferEvents - Processed transfer events
 * @param {Object} recipientBalance - Recipient balance information
 */
function formatResults(tokenInfo, transferEvents, recipientBalance) {
  console.log('\n' + '='.repeat(70));
  console.log('📊 TOKEN INFORMATION');
  console.log('='.repeat(70));
  console.log(`Name: ${tokenInfo.name}`);
  console.log(`Symbol: ${tokenInfo.symbol}`);
  console.log(`Decimals: ${tokenInfo.decimals}`);
  console.log(`Total Supply: ${tokenInfo.totalSupply} ${tokenInfo.symbol}`);
  
  console.log('\n' + '='.repeat(70));
  console.log('🔍 TARGET TRANSACTION(S)');
  console.log('='.repeat(70));
  
  if (transferEvents.length === 0) {
    console.log('❌ No matching transactions found');
    console.log('\nSuggestions:');
    console.log('  - Expand search range by increasing maxBlocks parameter');
    console.log('  - Check if the transaction amount is correct');
    console.log('  - Verify the token address is correct');
  } else {
    transferEvents.forEach((tx, index) => {
      console.log(`\nTransaction ${index + 1}:`);
      console.log(`  Hash: ${tx.txHash}`);
      console.log(`  Block: ${tx.blockNumber}`);
      console.log(`  Timestamp: ${tx.timestamp.toISOString()}`);
      console.log(`  From: ${tx.from}`);
      console.log(`  To: ${tx.to}`);
      console.log(`  Amount: ${tx.amount} ${tokenInfo.symbol}`);
      console.log(`  Gas Price: ${tx.gasPrice}`);
      
      // PolygonScan link
      console.log(`  View on PolygonScan: https://polygonscan.com/tx/${tx.txHash}`);
    });
  }
  
  if (transferEvents.length > 0) {
    const recipient = transferEvents[0].to;
    console.log('\n' + '='.repeat(70));
    console.log('💰 RECIPIENT BALANCE');
    console.log('='.repeat(70));
    console.log(`Address: ${recipient}`);
    console.log(`Current Balance: ${recipientBalance.formatted} ${tokenInfo.symbol}`);
    console.log(`Raw Balance: ${recipientBalance.raw}`);
    console.log(`View on PolygonScan: https://polygonscan.com/address/${recipient}`);
  }
  
  console.log('\n' + '='.repeat(70));
}

// ====================================================================
// 🚀 MAIN FUNCTION
// ====================================================================

/**
 * Main execution function
 */
async function main() {
  try {
    // Parse CLI arguments
    const args = process.argv.slice(2);
    const options = {
      tokenAddress: args[0] || DEFAULT_TOKEN_ADDRESS,
      targetAmount: args[1] ? parseFloat(args[1]) : DEFAULT_TARGET_AMOUNT,
      maxBlocks: args[2] ? parseInt(args[2]) : DEFAULT_MAX_BLOCKS,
      fromAddress: args[3] === 'null' ? null : (args[3] || DEFAULT_FROM_ADDRESS),  // Use default sender address for faster search
      txHash: args[4] || DEFAULT_TX_HASH,  // Optional: transaction hash for direct lookup
      useAPI: args.includes('--api'),
      apiKey: process.env.POLYGONSCAN_API_KEY
    };
    
    // Validate fromAddress if provided
    if (options.fromAddress) {
      options.fromAddress = validateAddress(options.fromAddress);
    }
    
    // Validate token address
    const tokenAddress = validateAddress(options.tokenAddress);
    
    // Validate txHash if provided
    if (options.txHash) {
      if (!ethers.isHexString(options.txHash, 32)) {
        throw new Error(`Invalid transaction hash: ${options.txHash}`);
      }
    }
    
    logger.section('Token Investigation - CAPY Token');
    logger.info(`📝 Configuration:`);
    logger.info(`   Token Address: ${tokenAddress}`);
    logger.info(`   Target Amount: ${options.targetAmount}`);
    if (options.txHash) {
      logger.info(`   Transaction Hash: ${options.txHash} (direct lookup)`);
      logger.info(`   ⚡ Using direct transaction lookup - much faster!`);
    } else {
      logger.info(`   Max Blocks to Search: ${options.maxBlocks.toLocaleString()}`);
      if (options.fromAddress) {
        logger.info(`   Filter by sender: ${options.fromAddress}`);
      } else {
        logger.info(`   No sender filter (searching all transfers)`);
      }
    }
    logger.info('');
    
    // 1. Initialize provider
    logger.info('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
    logger.info('STEP 1: Initializing Polygon Provider');
    logger.info('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
    const provider = await initializeProvider();
    logger.info('');
    
    // 2. Get token information
    logger.info('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
    logger.info('STEP 2: Fetching Token Information');
    logger.info('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
    const tokenInfo = await getTokenInfo(provider, tokenAddress);
    logger.info(`📊 Token Information:`);
    logger.info(`   Name: ${tokenInfo.name}`);
    logger.info(`   Symbol: ${tokenInfo.symbol}`);
    logger.info(`   Decimals: ${tokenInfo.decimals}`);
    logger.info(`   Total Supply: ${tokenInfo.totalSupply} ${tokenInfo.symbol}`);
    logger.info('');
    
    // 3. Get transaction data
    logger.info('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
    logger.info('STEP 3: Getting Transaction Data');
    logger.info('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
    
    let processedEvents = [];
    
    if (options.txHash) {
      // Direct transaction lookup - much faster!
      logger.info(`⚡ Using direct transaction lookup by hash: ${options.txHash}`);
      processedEvents = await getTransactionByHash(
        provider,
        tokenAddress,
        options.txHash,
        tokenInfo.decimals,
        options.targetAmount
      );
      
      logger.info('');
      
      if (processedEvents.length === 0) {
        logger.warn(`❌ No Transfer events matching amount ${options.targetAmount} found in transaction ${options.txHash}`);
        logger.info('💡 The transaction may not contain a transfer with the specified amount');
        return;
      }
    } else {
      // Search through blocks
      logger.info(`Looking for transaction with amount: ${options.targetAmount} ${tokenInfo.symbol}`);
      const transferEvents = await findTransferByAmountChunked(
        provider,
        tokenAddress,
        options.targetAmount,
        tokenInfo.decimals,
        options.maxBlocks,
        options.fromAddress
      );
      
      logger.info('');
      
      if (transferEvents.length === 0) {
        logger.warn('❌ No matching transactions found in specified block range');
        logger.info('💡 Suggestions:');
        logger.info('   - Try expanding search range (increase maxBlocks parameter)');
        logger.info('   - Provide transaction hash directly for faster lookup (5th parameter)');
        logger.info('   - Verify the target amount is correct');
        logger.info('   - Check if the transaction exists on PolygonScan');
        return;
      }
      
      // Process events
      logger.info('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
      logger.info('STEP 4: Processing Transaction Events');
      logger.info('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
      logger.info(`✅ Found ${transferEvents.length} matching transaction(s)`);
      processedEvents = await processTransferEvents(provider, transferEvents, tokenInfo.decimals);
      logger.info('');
    }
    
    // 4/5. Get recipient balance
    logger.info('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
    logger.info(options.txHash ? 'STEP 4: Retrieving Recipient Balance' : 'STEP 5: Retrieving Recipient Balance');
    logger.info('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
    const recipientAddress = processedEvents[0].to;
    logger.info(`Getting balance for recipient: ${recipientAddress}`);
    const recipientBalance = await getRecipientBalance(
      provider,
      tokenAddress,
      recipientAddress,
      tokenInfo.decimals
    );
    
    // 5/6. Display results
    logger.info('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
    logger.info(options.txHash ? 'STEP 5: Final Results' : 'STEP 6: Final Results');
    logger.info('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
    formatResults(tokenInfo, processedEvents, recipientBalance);
    
  } catch (error) {
    logger.error('Investigation failed:', error.message);
    console.error(error);
    process.exit(1);
  }
}

// Execute if run directly
if (require.main === module) {
  main().catch(error => {
    console.error('Unhandled error:', error);
    process.exit(1);
  });
}

// Export for potential use as module
module.exports = {
  initializeProvider,
  getTokenInfo,
  getTransactionByHash,
  findTransferByAmountChunked,
  processTransferEvents,
  getRecipientBalance,
  validateAddress,
  calculateTargetAmount
};

