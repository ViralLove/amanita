/**
 * Contract Manager
 * 
 * This module centralizes all contract operations from deploy_full.js,
 * eliminating 28 contract initialization patterns and 303 contract references.
 * 
 * Based on analysis of contract usage patterns in deploy_full.js
 */

const fs = require('fs');
const path = require('path');
const { ethers } = require('hardhat');
const { SUPPORTED_CONTRACTS, CONTRACT_ENV_MAPPING, ROLES } = require('../config/constants');
const logger = require('../utils/Logger');
const {
  isRateLimitError,
  executeWithRateLimitRetry,
  waitForTransactionReceipt
} = require('../utils/RateLimitHelpers');

class ContractManager {
  constructor(provider, config, ethersUtils, rpcManager = null) {
    this.provider = provider;
    this.config = config;
    this.ethersUtils = ethersUtils;
    this.rpcManager = rpcManager;
    this.contracts = new Map();
    this.contractArtifacts = new Map();
  }

  /**
   * Load contract artifact from file system
   * @param {string} contractName - The contract name
   * @returns {Object} - The contract artifact
   */
  loadContractArtifact(contractName) {
    if (this.contractArtifacts.has(contractName)) {
      return this.contractArtifacts.get(contractName);
    }

    try {
      // Artifacts are in project root /artifacts/, not /scripts/artifacts/
      const artifactPath = path.join(__dirname, '../../../artifacts/contracts', `${contractName}.sol`, `${contractName}.json`);
      const artifact = JSON.parse(fs.readFileSync(artifactPath, 'utf8'));
      this.contractArtifacts.set(contractName, artifact);
      logger.debug(`Loaded artifact for ${contractName}`);
      return artifact;
    } catch (error) {
      logger.error(`Failed to load artifact for ${contractName}:`, error.message);
      throw new Error(`Contract artifact not found: ${contractName}`);
    }
  }

  /**
   * Load contract instance
   * @param {string} contractName - The contract name
   * @param {string} address - The contract address (optional)
   * @returns {Object} - The contract instance
   */
  async loadContract(contractName, address = null) {
    if (this.contracts.has(contractName)) {
      return this.contracts.get(contractName);
    }

    const contractAddress = address || this.config.getContractAddress(contractName);
    if (!contractAddress) {
      throw new Error(`Contract address not found for ${contractName}`);
    }

    try {
      const artifact = this.loadContractArtifact(contractName);
      const contract = new ethers.Contract(contractAddress, artifact.abi, this.provider);
      this.contracts.set(contractName, contract);
      logger.contract(contractName, 'loaded', { address: contractAddress });
      return contract;
    } catch (error) {
      logger.error(`Failed to load contract ${contractName}:`, error.message);
      throw error;
    }
  }

  /**
   * Deploy contract
   * @param {string} contractName - The contract name
   * @param {Array} constructorArgs - Constructor arguments
   * @param {Object} deployOptions - Deployment options
   * @returns {Object} - The deployed contract instance
   */
  async deployContract(contractName, constructorArgs = [], deployOptions = {}) {
    try {
      // Legacy section separator
      logger.legacySection(contractName);
      
      // 🔍 DEBUG: Check private key source
      const privateKeyFromOptions = deployOptions.privateKey;
      const privateKeyFromConfig = this.config.get('deployer.privateKey');
      logger.debug(`[DEBUG] Private key sources for ${contractName}:`);
      logger.debug(`  - deployOptions.privateKey: ${privateKeyFromOptions ? `${privateKeyFromOptions.substring(0, 10)}...` : 'undefined'}`);
      logger.debug(`  - config.deployer.privateKey: ${privateKeyFromConfig ? `${privateKeyFromConfig.substring(0, 10)}...` : 'undefined'}`);
      
      const artifact = this.loadContractArtifact(contractName);
      
      // Get deployer address from private key (needed before balance check)
      const privateKey = deployOptions.privateKey || this.config.get('deployer.privateKey');
      let deployerAddress;
      if (privateKey) {
        // Get address from private key without creating signer (signer will be created after provider may switch)
        const tempWallet = new ethers.Wallet(privateKey);
        deployerAddress = tempWallet.address;
      } else {
        // Fallback: create signer to get address
        const tempSigner = this.ethersUtils.getSigner();
        deployerAddress = await tempSigner.getAddress();
      }
      
      // 🔍 DEBUG: Detailed deployer information
      logger.debug(`[DEBUG] Deployer information for ${contractName}:`);
      logger.debug(`  - Deployer address: ${deployerAddress}`);
      logger.debug(`  - Private key used: ${(privateKey || 'FALLBACK').substring(0, 10)}...`);
      
      // Get balance and network info with retry logic for rate limits
      let balanceBefore;
      let balanceBeforeETH;
      let network;
      let chainId;
      let currency;
      
      await executeWithRateLimitRetry(async () => {
        balanceBefore = await this.ethersUtils.provider.getBalance(deployerAddress);
        balanceBeforeETH = ethers.formatEther(balanceBefore);
        
        // Get network info to determine currency
        network = await this.ethersUtils.provider.getNetwork();
        chainId = Number(network.chainId);
        currency = chainId === 137 ? 'MATIC' : chainId === 80001 ? 'MATIC' : 'ETH';
      }, {
        maxRetries: 3,
        initialDelayMs: 10000,
        rpcManager: this.rpcManager,
        ethersUtils: this.ethersUtils,
        contractManager: this,
        operationName: `balance check for ${contractName}`
      });
      
      // Create signer after balance check (provider may have been switched)
      const signer = this.ethersUtils.getSigner(deployOptions.privateKey);
      
      // Get provider URL for logging
      const providerUrl = this.ethersUtils.provider.connection?.url || 
                         (this.ethersUtils.provider._getConnection ? 
                          JSON.stringify(this.ethersUtils.provider._getConnection()) : 'unknown');
      
      // 🔍 DEBUG: Balance and network info
      logger.info(`[BALANCE] Checking deployer balance for ${contractName}:`);
      logger.info(`  - Deployer address: ${deployerAddress}`);
      logger.info(`  - Balance: ${balanceBeforeETH} ${currency} (${balanceBefore.toString()} wei)`);
      logger.info(`  - Network Chain ID: ${chainId}`);
      logger.info(`  - Network name: ${network.name || 'unknown'}`);
      logger.info(`  - Provider URL: ${typeof providerUrl === 'string' ? providerUrl : 'Hardhat provider'}`);
      
      logger.debug(`[DEBUG] Detailed balance and network check for ${contractName}:`);
      logger.debug(`  - Deployer address: ${deployerAddress}`);
      logger.debug(`  - Balance: ${balanceBeforeETH} ${currency} (${balanceBefore.toString()} wei)`);
      logger.debug(`  - Network Chain ID: ${chainId}`);
      logger.debug(`  - Network name: ${network.name || 'unknown'}`);
      logger.debug(`  - Currency: ${currency}`);
      logger.debug(`  - Provider URL: ${typeof providerUrl === 'string' ? providerUrl : 'Hardhat provider'}`);
      
      // ⚠️ WARNING: Check if balance is zero
      if (balanceBefore === 0n) {
        logger.error(`[ERROR] Deployer account ${deployerAddress} has ZERO balance!`);
        logger.error(`[ERROR] Network: Chain ID ${chainId} (${network.name || 'unknown'})`);
        logger.error(`[ERROR] Provider: ${typeof providerUrl === 'string' ? providerUrl : 'Hardhat provider'}`);
        logger.error(`[ERROR] Please check:`);
        logger.error(`  - Is this the correct network? (Expected: ${chainId === 137 ? 'Polygon Mainnet' : chainId === 80001 ? 'Mumbai Testnet' : 'Local/Other'})`);
        logger.error(`  - Does the account have ${currency} balance on this network?`);
        logger.error(`  - Is the correct private key being used?`);
        logger.error(`  - For Polygon: Check balance on https://polygonscan.com/address/${deployerAddress}`);
        throw new Error(`Deployer account ${deployerAddress} has insufficient funds: balance is 0 ${currency}`);
      }
      
      const ContractFactory = new ethers.ContractFactory(artifact.abi, artifact.bytecode, signer);
      
      // Determine gas price: use provided value, or fallback to fixed value for Polygon mainnet
      // Polygon base fee often 500–600+ gwei; fixed 700 gwei avoids Gas Station API and "max fee < base fee"
      let gasPrice = deployOptions.gasPrice ? BigInt(deployOptions.gasPrice) : undefined;
      if (!gasPrice && chainId === 137) {
        // Polygon mainnet: fixed 700 gwei above typical base fee
        gasPrice = ethers.parseUnits('700', 'gwei');
        logger.debug(`[GAS] Using fixed gas price for Polygon mainnet: 700 gwei`);
      }
      
      // Deploy contract with retry logic for rate limits
      let contract;
      let deploymentTx;
      let txHash = null;
      
      contract = await executeWithRateLimitRetry(async () => {
        try {
          // Deploy contract
          // ethers.js автоматически управляет nonce если НЕ кэшировать Wallet
          const deployedContract = await ContractFactory.deploy(...constructorArgs, {
            gasLimit: deployOptions.gasLimit || 5000000,
            gasPrice: gasPrice
          });
          
          // Get deployment transaction and hash
          const tx = deployedContract.deploymentTransaction();
          if (tx) {
            txHash = tx.hash;
            logger.debug(`[DEPLOY] Transaction sent: ${txHash}`);
          }
          return deployedContract;
        } catch (error) {
          // Handle Gas Station API errors - these should not trigger endpoint switch
          // They should be handled by using fixed gas price (already set above)
          const errorMessage = error.message || String(error);
          if (errorMessage.includes('gas station') || errorMessage.includes('Batch size too large')) {
            logger.warn(`[GAS STATION] Gas Station API error detected: ${errorMessage.substring(0, 100)}`);
            logger.warn(`[GAS STATION] Gas price is already set to: ${gasPrice ? ethers.formatUnits(gasPrice, 'gwei') + ' gwei' : 'undefined'}`);
            // Re-throw to trigger retry (gasPrice should already be set, so retry should work)
            throw error;
          }
          throw error;
        }
      }, {
        maxRetries: 3,
        initialDelayMs: 10000,
        rpcManager: this.rpcManager,
        ethersUtils: this.ethersUtils,
        contractManager: this,
        operationName: `${contractName} deploy`
      });
      
      deploymentTx = contract.deploymentTransaction();
      if (!contract || !deploymentTx || !txHash) {
        throw new Error(`Failed to deploy ${contractName} or get transaction hash`);
      }
      
      // Step 2: Wait for transaction receipt (retry if wait fails with rate limit)
      const receipt = await waitForTransactionReceipt(deploymentTx, txHash, this.ethersUtils.provider, {
        maxRetries: 3,
        initialDelayMs: 10000,
        rpcManager: this.rpcManager,
        ethersUtils: this.ethersUtils,
        contractManager: this,
        contractName: contractName
      });
      const gasUsed = receipt.gasUsed;
      
      // Get contract address from deployed contract
      const contractAddress = await contract.getAddress();
      
      // Get balance after deployment
      const balanceAfter = await this.ethersUtils.provider.getBalance(await signer.getAddress());
      const balanceAfterETH = ethers.formatEther(balanceAfter);
      const cost = (parseFloat(balanceBeforeETH) - parseFloat(balanceAfterETH)).toFixed(6);

      // Log deployment details
      logger.deploymentDetails({
        gasUsed: Number(gasUsed),
        balance: balanceAfterETH,
        cost: cost,
        contractName: contractName
      });

      logger.contract(contractName, 'deployed', { address: contractAddress });
      this.contracts.set(contractName, contract);
      return contract;
    } catch (error) {
      logger.error(`Failed to deploy contract ${contractName}:`, error.message);
      throw error;
    }
  }

  /**
   * Load UUPS contract (proxy)
   * Automatically resolves proxy address from .env or MagicRegistry
   * @param {string} contractName - The contract name
   * @param {string} proxyAddress - Optional proxy address (if not provided, auto-resolves)
   * @returns {Object} - The UUPS contract instance
   */
  async loadUUPSContract(contractName, proxyAddress = null) {
    try {
      // Auto-resolve proxy address if not provided
      if (!proxyAddress) {
        // Try .env first
        const envVarName = `${contractName.toUpperCase()}_PROXY_ADDRESS`;
        proxyAddress = process.env[envVarName] || process.env[`${contractName.toUpperCase()}_CONTRACT_ADDRESS`];
        
        // If not in .env, try MagicRegistry
        if (!proxyAddress || proxyAddress === 'undefined') {
          let magicRegistry = this.contracts.get('MagicRegistry');
          
          // If MagicRegistry not in cache, try to load from .env
          if (!magicRegistry) {
            const magicRegistryAddress = process.env.MAGIC_REGISTRY_CONTRACT_ADDRESS;
            if (magicRegistryAddress && magicRegistryAddress !== 'undefined') {
              logger.info('MagicRegistry не в кеше, загружаю из .env...');
              magicRegistry = await this.loadContract('MagicRegistry', magicRegistryAddress);
            }
          }
          
          if (magicRegistry) {
            try {
              proxyAddress = await magicRegistry.get(contractName);
              logger.info(`${contractName} Proxy адрес загружен из MagicRegistry: ${proxyAddress}`);
            } catch (error) {
              throw new Error(`Proxy адрес не найден ни в .env (${envVarName}), ни в MagicRegistry для ${contractName}`);
            }
          } else {
            throw new Error(`Proxy адрес не найден: ${envVarName} не установлен в .env, и MagicRegistry недоступен`);
          }
        }
      }
      
      logger.info(`🔷 Загружаем UUPS контракт ${contractName}`);
      logger.info(`   → Proxy: ${proxyAddress}`);
      
      // Load Logic artifact (for ABI)
      const logicArtifact = this.loadContractArtifact(`${contractName}Logic`);
      logger.info(`   → Logic ABI: ${contractName}Logic`);
      
      // Create contract instance with Logic ABI on Proxy address
      const contract = new ethers.Contract(proxyAddress, logicArtifact.abi, this.provider);
      this.contracts.set(contractName, contract);
      
      logger.contract(contractName, 'UUPS loaded', { proxyAddress });
      return contract;
    } catch (error) {
      logger.error(`Failed to load UUPS contract ${contractName}:`, error.message);
      throw error;
    }
  }

  /**
   * Deploy UUPS contract (proxy + implementation)
   * @param {string} contractName - The contract name
   * @param {Array} constructorArgs - Constructor arguments
   * @param {Object} deployOptions - Deployment options
   * @returns {Object} - The deployed UUPS contract instance
   */
  async deployUUPSContract(contractName, constructorArgs = [], deployOptions = {}) {
    try {
      // Deploy implementation first (legacySection will be called inside deployContract)
      const implementationContract = await this.deployContract(`${contractName}Logic`, constructorArgs, deployOptions);
      const implementationAddress = await implementationContract.getAddress();
      
      // CRITICAL: Wait for nonce to update in provider after Logic deployment
      // This prevents NONCE_EXPIRED errors in Hardhat automining mode
      // deploymentTransaction() is already consumed by deployContract, so we use simple delay
      logger.info(`⏱️ Waiting 500ms for nonce update after ${contractName}Logic deployment...`);
      await new Promise(resolve => setTimeout(resolve, 500));
      logger.info(`✅ Nonce settled, proceeding with ${contractName} Proxy deployment...`);
      
      // Prepare initialize calldata
      const initArgs = deployOptions.initArgs || await this.getInitializeArgs(contractName);
      logger.info(`Initialize args for ${contractName}:`, initArgs);
      const initCalldata = this.prepareInitializeCalldata(contractName, initArgs);
      logger.info(`Initialize calldata prepared: ${initCalldata.substring(0, 10)}...`);
      
      // Deploy proxy with initialization
      logger.legacySection(`${contractName} (Proxy)`);
      
      const proxyArtifact = this.loadContractArtifact(`${contractName}Proxy`);
      const signer = this.ethersUtils.getSigner(deployOptions.privateKey);
      const signerAddress = await signer.getAddress();
      
      // Get balance before proxy deployment with retry logic
      let balanceBefore;
      let balanceBeforeETH;
      await executeWithRateLimitRetry(async () => {
        balanceBefore = await this.ethersUtils.provider.getBalance(signerAddress);
        balanceBeforeETH = ethers.formatEther(balanceBefore);
      }, {
        maxRetries: 3,
        initialDelayMs: 10000,
        rpcManager: this.rpcManager,
        ethersUtils: this.ethersUtils,
        contractManager: this,
        operationName: `balance check for ${contractName} Proxy`
      });
      
      const ProxyFactory = new ethers.ContractFactory(proxyArtifact.abi, proxyArtifact.bytecode, signer);
      
      // Determine gas price: use provided value, or fallback to fixed value for Polygon mainnet
      // Polygon base fee often 500–600+ gwei; fixed 700 gwei avoids Gas Station API and "max fee < base fee"
      let proxyGasPrice = deployOptions.gasPrice ? BigInt(deployOptions.gasPrice) : undefined;
      if (!proxyGasPrice) {
        // Get network info to determine chain ID
        try {
          const network = await this.ethersUtils.provider.getNetwork();
          const proxyChainId = Number(network.chainId);
          if (proxyChainId === 137) {
            // Polygon mainnet: fixed 700 gwei above typical base fee
            proxyGasPrice = ethers.parseUnits('700', 'gwei');
            logger.debug(`[GAS] Using fixed gas price for Polygon mainnet Proxy: 700 gwei`);
          }
        } catch (error) {
          logger.debug(`[GAS] Could not determine network for gas price, using undefined`);
        }
      }
      
      // Deploy proxy with retry logic
      let proxyContract;
      let proxyDeploymentTx;
      let proxyTxHash = null;
      
      proxyContract = await executeWithRateLimitRetry(async () => {
        const deployedProxy = await ProxyFactory.deploy(implementationAddress, initCalldata, {
          gasLimit: deployOptions.gasLimit || 5000000,
          gasPrice: proxyGasPrice
        });
        const tx = deployedProxy.deploymentTransaction();
        if (tx) {
          proxyTxHash = tx.hash;
          logger.debug(`[DEPLOY] Proxy transaction sent: ${proxyTxHash}`);
        }
        return deployedProxy;
      }, {
        maxRetries: 3,
        initialDelayMs: 10000,
        rpcManager: this.rpcManager,
        ethersUtils: this.ethersUtils,
        contractManager: this,
        operationName: `${contractName} Proxy deploy`
      });
      
      proxyDeploymentTx = proxyContract.deploymentTransaction();
      if (!proxyContract || !proxyDeploymentTx || !proxyTxHash) {
        throw new Error(`Failed to deploy ${contractName} Proxy or get transaction hash`);
      }
      
      // Wait for transaction receipt with retry logic
      const proxyReceipt = await waitForTransactionReceipt(proxyDeploymentTx, proxyTxHash, this.ethersUtils.provider, {
        maxRetries: 3,
        initialDelayMs: 10000,
        rpcManager: this.rpcManager,
        ethersUtils: this.ethersUtils,
        contractManager: this,
        contractName: `${contractName} Proxy`
      });
      const proxyGasUsed = proxyReceipt.gasUsed;
      
      // Get proxy address from deployed contract
      const proxyAddress = await proxyContract.getAddress();
      
      // Get balance after proxy deployment with retry logic
      let balanceAfter;
      let balanceAfterETH;
      await executeWithRateLimitRetry(async () => {
        balanceAfter = await this.ethersUtils.provider.getBalance(signerAddress);
        balanceAfterETH = ethers.formatEther(balanceAfter);
      }, {
        maxRetries: 3,
        initialDelayMs: 10000,
        rpcManager: this.rpcManager,
        ethersUtils: this.ethersUtils,
        contractManager: this,
        operationName: `balance check after ${contractName} Proxy deploy`
      });
      const proxyCost = (parseFloat(balanceBeforeETH) - parseFloat(balanceAfterETH)).toFixed(6);

      // Log proxy deployment details
      logger.deploymentDetails({
        gasUsed: Number(proxyGasUsed),
        balance: balanceAfterETH,
        cost: proxyCost,
        contractName: `${contractName} (Proxy)`
      });

      // ВАЖНО: Создаём contract instance с Logic ABI на Proxy адресе
      // Это позволяет вызывать методы Logic через Proxy
      const logicArtifact = this.loadContractArtifact(`${contractName}Logic`);
      const finalContract = new ethers.Contract(proxyAddress, logicArtifact.abi, this.provider);

      logger.contract(contractName, 'UUPS deployed', { 
        proxyAddress,
        implementationAddress
      });
      
      this.contracts.set(contractName, finalContract);
      return finalContract;
    } catch (error) {
      logger.error(`Failed to deploy UUPS contract ${contractName}:`, error.message);
      throw error;
    }
  }

  /**
   * Upgrade UUPS contract to new Logic implementation
   * Deploys new Logic, calls proxy.upgradeToAndCall(newLogic, "0x")
   * @param {string} contractName - UUPS contract name (SpiralEngine, ProductRegistry, etc.)
   * @param {Object} deployOptions - Deployment options (privateKey, gasPrice, etc.)
   * @returns {Object} - The contract instance (Logic ABI) at same Proxy address
   */
  async upgradeUUPSContract(contractName, deployOptions = {}) {
    const uupsContracts = ['SpiralEngine', 'ProductRegistry', 'OrganicComponentRegistry', 'AmanitaInternational'];
    if (!uupsContracts.includes(contractName)) {
      throw new Error(`Contract ${contractName} is not a UUPS contract. Supported: ${uupsContracts.join(', ')}`);
    }

    const proxyAddress = this.config.getContractAddress?.(contractName) ||
      process.env[`${contractName.toUpperCase()}_CONTRACT_ADDRESS`] ||
      process.env[`${contractName.toUpperCase()}_PROXY_ADDRESS`];
    if (!proxyAddress || proxyAddress === 'undefined') {
      throw new Error(`Proxy address not found for ${contractName}. Set ${contractName.toUpperCase()}_CONTRACT_ADDRESS in .env`);
    }

    logger.info(`🔄 Upgrading UUPS contract ${contractName} (Proxy: ${proxyAddress})`);

    const signer = this.ethersUtils.getSigner(deployOptions.privateKey);

    const constructorArgs = this.getLogicConstructorArgs(`${contractName}Logic`);
    const implementationContract = await this.deployContract(`${contractName}Logic`, constructorArgs, deployOptions);
    const newLogicAddress = await implementationContract.getAddress();
    logger.info(`✅ New Logic deployed at ${newLogicAddress}`);

    logger.info(`⏱️ Waiting 500ms for nonce update before upgrade...`);
    await new Promise(resolve => setTimeout(resolve, 500));

    const logicArtifact = this.loadContractArtifact(`${contractName}Logic`);
    const proxyWithSigner = new ethers.Contract(proxyAddress, logicArtifact.abi, signer);

    let upgradeGasPrice = deployOptions.gasPrice ? BigInt(deployOptions.gasPrice) : undefined;
    if (!upgradeGasPrice) {
      try {
        const network = await this.ethersUtils.provider.getNetwork();
        if (Number(network.chainId) === 137) {
          upgradeGasPrice = ethers.parseUnits('700', 'gwei');
        }
      } catch (_) {}
    }

    const upgradeTx = await executeWithRateLimitRetry(async () => {
      return proxyWithSigner.upgradeToAndCall(newLogicAddress, '0x', {
        gasLimit: deployOptions.gasLimit || 500000,
        gasPrice: upgradeGasPrice
      });
    }, {
      maxRetries: 3,
      initialDelayMs: 10000,
      rpcManager: this.rpcManager,
      ethersUtils: this.ethersUtils,
      contractManager: this,
      operationName: `${contractName} upgrade`
    });

    await upgradeTx.wait();
    logger.info(`✅ Upgrade tx confirmed: ${upgradeTx.hash}`);

    const upgradedContract = new ethers.Contract(proxyAddress, logicArtifact.abi, this.provider);
    this.contracts.set(contractName, upgradedContract);
    logger.contract(contractName, 'UUPS upgraded', { proxyAddress, newLogicAddress });
    return upgradedContract;
  }

  /**
   * Prepare initialization calldata for UUPS contracts
   * @param {string} contractName - The contract name
   * @param {Array} initArgs - Initialization arguments
   * @returns {string} - The encoded initialization calldata
   */
  prepareInitializeCalldata(contractName, initArgs = []) {
    try {
      const artifact = this.loadContractArtifact(`${contractName}Logic`);
      const contractInterface = new ethers.Interface(artifact.abi);
      return contractInterface.encodeFunctionData('initialize', initArgs);
    } catch (error) {
      logger.error(`Failed to prepare initialize calldata for ${contractName}:`, error.message);
      throw error;
    }
  }

  /**
   * Get logic constructor arguments for UUPS contracts
   * @param {string} contractName - The contract name
   * @returns {Array} - Constructor arguments
   */
  getLogicConstructorArgs(contractName) {
    // This would be customized based on each contract's requirements
    const constructorArgsMap = {
      'SpiralEngineLogic': [],
      'ProductRegistryLogic': [],
      'OrganicComponentRegistryLogic': [],
      'AmanitaInternationalLogic': []
    };
    
    return constructorArgsMap[contractName] || [];
  }

  /**
   * Get initialize arguments for UUPS contracts
   * @param {string} contractName - The UUPS contract name
   * @returns {Promise<Array>} - Initialize arguments
   */
  async getInitializeArgs(contractName) {
    // Get deployer address (admin for all contracts)
    const signer = this.ethersUtils.getSigner();
    const adminAddress = await signer.getAddress();
    
    // SpiralEngine: initialize(address admin)
    if (contractName === 'SpiralEngine') {
      return [adminAddress];
    }
    
    // ProductRegistry: initialize(address admin, address _spiralEngine)
    if (contractName === 'ProductRegistry') {
      const spiralEngine = this.getContract('SpiralEngine');
      if (!spiralEngine) {
        throw new Error('SpiralEngine must be deployed before ProductRegistry');
      }
      return [adminAddress, await spiralEngine.getAddress()];
    }
    
    // OrganicComponentRegistry: initialize(address admin)
    if (contractName === 'OrganicComponentRegistry') {
      return [adminAddress];
    }
    
    // AmanitaInternational: initialize(address admin, address _spiralEngine)
    if (contractName === 'AmanitaInternational') {
      const spiralEngine = this.getContract('SpiralEngine');
      if (!spiralEngine) {
        throw new Error('SpiralEngine must be deployed before AmanitaInternational');
      }
      return [adminAddress, await spiralEngine.getAddress()];
    }
    
    return [];
  }

  /**
   * Get constructor arguments for SBT contracts (with dynamic dependencies)
   * @param {string} contractName - The SBT contract name
   * @returns {Promise<Array>} - Constructor arguments
   */
  async getSBTConstructorArgs(contractName) {
    // SoulboundCore - static args
    if (contractName === 'SoulboundCore') {
      return ['Amanita Soul', 'ASOUL'];
    }
    
    // SoulMetadata - depends on SoulboundCore
    if (contractName === 'SoulMetadata') {
      const soulboundCore = this.getContract('SoulboundCore');
      if (!soulboundCore) {
        throw new Error('SoulboundCore must be deployed before SoulMetadata');
      }
      return [await soulboundCore.getAddress()];
    }
    
    // SoulRecovery - depends on SoulboundCore
    if (contractName === 'SoulRecovery') {
      const soulboundCore = this.getContract('SoulboundCore');
      if (!soulboundCore) {
        throw new Error('SoulboundCore must be deployed before SoulRecovery');
      }
      return [await soulboundCore.getAddress()];
    }
    
    // SoulIntegration - depends on SpiralEngine + SoulboundCore
    if (contractName === 'SoulIntegration') {
      const spiralEngine = this.getContract('SpiralEngine');
      if (!spiralEngine) {
        throw new Error('SpiralEngine must be deployed before SoulIntegration');
      }
      
      const soulboundCore = this.getContract('SoulboundCore');
      if (!soulboundCore) {
        throw new Error('SoulboundCore must be deployed before SoulIntegration');
      }
      
      return [
        await spiralEngine.getAddress(),
        await soulboundCore.getAddress()
      ];
    }
    
    // SoulIdentity - depends on SoulboundCore + SoulMetadata
    if (contractName === 'SoulIdentity') {
      const soulboundCore = this.getContract('SoulboundCore');
      if (!soulboundCore) {
        throw new Error('SoulboundCore must be deployed before SoulIdentity');
      }
      
      const soulMetadata = this.getContract('SoulMetadata');
      if (!soulMetadata) {
        throw new Error('SoulMetadata must be deployed before SoulIdentity');
      }
      
      return [
        await soulboundCore.getAddress(),
        await soulMetadata.getAddress()
      ];
    }
    
    return [];
  }

  /**
   * Check if contract exists in environment
   * @param {string} contractName - The contract name
   * @returns {Object|null} - The contract instance or null
   */
  async checkExistingContract(contractName) {
    try {
      const address = this.config.getContractAddress(contractName);
      if (address) {
        return await this.loadContract(contractName, address);
      }
      return null;
    } catch (error) {
      logger.debug(`Contract ${contractName} not found in environment`);
      return null;
    }
  }

  /**
   * Register contract in registry
   * @param {string} contractName - The contract name
   * @param {string} contractAddress - The contract address
   * @param {Object} registryContract - The registry contract instance
   */
  async registerContractInRegistry(contractName, contractAddress, registryContract) {
    try {
      const signer = this.ethersUtils.getSigner();
      const registryWithSigner = registryContract.connect(signer);
      
      // MagicRegistry uses set(key, value) not registerContract()
      const tx = await registryWithSigner.set(contractName, contractAddress, {
        gasLimit: 500000
      });
      
      const receipt = await tx.wait();
      logger.contract(contractName, 'registered in registry', { address: contractAddress, txHash: receipt.hash });
      return receipt;
    } catch (error) {
      logger.error(`Failed to register contract ${contractName}:`, error.message);
      throw error;
    }
  }

  /**
   * Deploy single contract with full setup
   * @param {string} contractName - The contract name
   * @param {Object} options - Deployment options
   * @returns {Object} - The deployed contract instance
   */
  async deploySingleContract(contractName, options = {}) {
    try {
      // Check if already exists
      const existing = await this.checkExistingContract(contractName);
      if (existing) {
        const existingAddress = await existing.getAddress();
        logger.info(`Contract ${contractName} already exists at ${existingAddress}`);
        return existing;
      }

      // Auto-detect contract type
      const uupsContracts = [
        'SpiralEngine',
        'ProductRegistry',
        'OrganicComponentRegistry',
        'AmanitaInternational'
      ];
      
      const sbtContracts = [
        'SoulboundCore',
        'SoulMetadata',
        'SoulRecovery',
        'SoulIntegration',
        'SoulIdentity'
      ];
      
      const isUUPSContract = options.isUUPS !== undefined 
        ? options.isUUPS 
        : uupsContracts.includes(contractName);
      
      const isSBTContract = sbtContracts.includes(contractName);

      // Ensure privateKey is passed through options (fallback to config if not provided)
      if (!options.privateKey) {
        options.privateKey = this.config.get('deployer.privateKey');
        logger.debug(`[DEBUG] deploySingleContract: Using privateKey from config.deployer.privateKey`);
      } else {
        logger.debug(`[DEBUG] deploySingleContract: Using privateKey from options`);
      }

      // Deploy based on contract type
      let deployedContract;
      
      if (isUUPSContract) {
        // UUPS deployment
        const constructorArgs = this.getLogicConstructorArgs(`${contractName}Logic`);
        deployedContract = await this.deployUUPSContract(contractName, constructorArgs, options);
      } else if (isSBTContract) {
        // SBT deployment with dynamic dependencies
        const constructorArgs = options.constructorArgs || await this.getSBTConstructorArgs(contractName);
        logger.info(`SBT contract ${contractName} constructor args:`, constructorArgs);
        deployedContract = await this.deployContract(contractName, constructorArgs, options);
      } else {
        // Regular deployment
        const constructorArgs = options.constructorArgs || [];
        deployedContract = await this.deployContract(contractName, constructorArgs, options);
      }

      // Register in registry if provided
      if (options.registry) {
        const deployedAddress = await deployedContract.getAddress();
        
        // ✅ FIX: Wait for nonce update before registry registration
        // Same issue as Logic→Proxy: Hardhat automining needs time to update nonce
        logger.info(`⏱️ Waiting 500ms for nonce update before registry registration...`);
        await new Promise(resolve => setTimeout(resolve, 500));
        logger.info(`✅ Nonce settled, proceeding with registry registration...`);
        
        await this.registerContractInRegistry(contractName, deployedAddress, options.registry);
      }

      logger.success(`Contract ${contractName} deployed successfully`);
      return deployedContract;
    } catch (error) {
      logger.error(`Failed to deploy single contract ${contractName}:`, error.message);
      throw error;
    }
  }

  /**
   * Ensure contract exists (load or deploy)
   * @param {string} contractName - The contract name
   * @param {Object} options - Options for deployment
   * @returns {Object} - The contract instance
   */
  async ensureContractExists(contractName, options = {}) {
    try {
      // Try to load existing contract first
      const existing = await this.checkExistingContract(contractName);
      if (existing) {
        return existing;
      }

      // Deploy if not exists
      return await this.deploySingleContract(contractName, options);
    } catch (error) {
      logger.error(`Failed to ensure contract exists ${contractName}:`, error.message);
      throw error;
    }
  }

  /**
   * Get contract instance
   * @param {string} contractName - The contract name
   * @returns {Object} - The contract instance
   */
  getContract(contractName) {
    return this.contracts.get(contractName);
  }

  /**
   * Get all loaded contracts
   * @returns {Map} - Map of all loaded contracts
   */
  getAllContracts() {
    return this.contracts;
  }

  /**
   * Clear all contracts (for testing)
   */
  clearContracts() {
    this.contracts.clear();
    this.contractArtifacts.clear();
  }
}

module.exports = ContractManager;
