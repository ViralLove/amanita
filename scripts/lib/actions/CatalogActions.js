/**
 * Catalog Actions Module
 * 
 * This module handles all catalog-related actions from deploy_full.js,
 * centralizing product catalog creation and management logic.
 */

const logger = require('../utils/Logger');

class CatalogActions {
  constructor(contractManager, arweaveManager, ethersUtils, config) {
    this.contractManager = contractManager;
    this.arweaveManager = arweaveManager;
    this.ethersUtils = ethersUtils;
    this.config = config;
  }

  /**
   * Prepare context for Arweave upload actions
   * Centralizes context preparation to avoid code duplication (DRY principle)
   * @private
   * @param {Object} options - Configuration options
   * @param {boolean} options.dryRun - Dry-run mode (default: false)
   * @param {boolean} options.arweaveOnly - Arweave-only mode, skip contracts (default: false)
   * @returns {Promise<Object>} - Prepared context with all dependencies
   */
  async _prepareArweaveContext(options = {}) {
    // Initialize Arweave if needed
    if (!this.arweaveManager.isReady()) {
      await this.arweaveManager.initialize();
    }

    // Load AmanitaInternational for title localization
    // Graceful fail: if contract not available, context will have null
    const amanitaInternational = await this.contractManager
      .loadUUPSContract('AmanitaInternational')
      .catch((error) => {
        logger.warn(`Failed to load AmanitaInternational: ${error.message}`);
        return null;
      });

    // Prepare context structure
    const context = {
      // Arweave connection
      arweave: {
        client: this.arweaveManager.arweaveClient,
        key: this.arweaveManager.arweaveKey
      },
      
      // Managers (for business logic layer)
      arweaveManager: this.arweaveManager,
      contractManager: this.contractManager,
      
      // Contracts
      contracts: {
        amanitaInternational: amanitaInternational
      },
      
      // Config and logger
      config: this.config,
      logger: logger,
      
      // Operation flags
      dryRun: options.dryRun || false,
      arweaveOnly: options.arweaveOnly || false,
      
      // Signers (for transaction signing)
      seller: {
        address: this.config.get('seller.address'),
        signer: this.ethersUtils.getSigner(this.config.get('seller.privateKey'))
      },
      deployer: {
        address: this.config.get('deployer.address'),
        signer: this.ethersUtils.getSigner()
      }
    };

    return context;
  }

  /**
   * Action 41: Transform CSV → Product JSONs
   * @returns {Promise<Object>} - Transformation result
   */
  async action41() {
    logger.action(41, "Transform CSV → Product JSONs");
    
    try {
      // Import the transform module
      const { transformProductsFromCSV } = require('../../transform_products_csv.js');
      
      const csvPath = this.config.get('paths.csvPath');
      const outputPath = this.config.get('paths.outputPath');
      const sellerId = this.config.get('seller.id');
      const sourceLang = this.config.get('seller.businessId') || 'en';
      
      const config = {
        csvPath: csvPath,
        outputDir: outputPath,
        sellerId: sellerId,
        sourceLang: sourceLang,
        dryRun: false
      };

      const result = await transformProductsFromCSV(config);
      
      logger.success(41);
      return {
        success: true,
        result: result
      };
    } catch (error) {
      logger.failure(41, error.message);
      throw error;
    }
  }

  /**
   * Action 42: Unified Arweave Upload
   * @returns {Promise<Object>} - Upload result
   */
  async action42() {
    logger.action(42, "Unified Arweave Upload");
    
    try {
      // Import the upload steps module
      const { action42_UnifiedArweaveUpload } = require('../product_upload_steps.js');
      
      // ✅ Resolve paths from config
      const sellerId = this.config.get('seller.businessId') || 'iveta';
      const sellerDir = `data/sellers/${sellerId}`;
      const productsDir = `${sellerDir}/output/products`;
      const outputDir = `${sellerDir}/output`;
      
      // ✅ Use centralized context preparation (DRY principle)
      const context = await this._prepareArweaveContext({
        dryRun: false,
        arweaveOnly: false
      });

      const result = await action42_UnifiedArweaveUpload(context, productsDir, outputDir);
      
      logger.success(42);
      return {
        success: true,
        result: result
      };
    } catch (error) {
      logger.failure(42, error.message);
      throw error;
    }
  }

  /**
   * Action 43: Contract Registration
   * @returns {Promise<Object>} - Registration result
   */
  async action43() {
    logger.action(43, "Contract Registration");
    
    try {
      // Import the upload steps module
      const { action43_UnifiedContractRegistration } = require('../product_upload_steps.js');
      
      const result = await action43_UnifiedContractRegistration({
        contractManager: this.contractManager,
        config: this.config,
        logger: logger
      });
      
      logger.success(43);
      return {
        success: true,
        result: result
      };
    } catch (error) {
      logger.failure(43, error.message);
      throw error;
    }
  }

  /**
   * Action 444: Automatic Pipeline (CSV → Arweave → Contract)
   * 
   * Environment Variables Required:
   * - CSV_FILE: Path to CSV file (e.g., "data/sellers/iveta/catalog/Iveta_catalog.csv")
   * - SELLER_BUSINESS_ID: Seller identifier (e.g., "Iveta")
   * - OUTPUT_DIR: Output directory for transformed products (default: "data/output")
   * - SOURCE_LANG: Source language (default: "en")
   * 
   * @returns {Promise<Object>} - Pipeline result
   */
  async action444() {
    logger.action(444, "Automatic Pipeline");
    
    try {
      // Get parameters from config/env
      const csvPath = this.config.get('catalog.csvPath') || process.env.CSV_FILE;
      const outputDir = this.config.get('catalog.outputDir') || process.env.OUTPUT_DIR || 'data/output';
      const sellerId = this.config.get('catalog.sellerId') || process.env.SELLER_BUSINESS_ID;
      const sourceLang = this.config.get('catalog.sourceLang') || process.env.SOURCE_LANG || 'en';

      // Validate required parameters
      if (!csvPath) {
        throw new Error('CSV_FILE is required. Set in .env: CSV_FILE=data/sellers/iveta/catalog/Iveta_catalog.csv');
      }
      if (!sellerId) {
        throw new Error('SELLER_BUSINESS_ID is required. Set in .env: SELLER_BUSINESS_ID=Iveta');
      }

      // ✅ Use centralized context preparation (DRY principle)
      // This ensures Action 444 has the same complete context as Action 42
      const context = await this._prepareArweaveContext({
        dryRun: false,
        arweaveOnly: false
      });

      const { action444_AutomaticPipeline } = require('../product_upload_steps.js');
      
      const result = await action444_AutomaticPipeline(
        context,  // ✅ Full context with contracts.amanitaInternational, seller.signer, deployer.signer
        csvPath,
        outputDir,
        sellerId,
        sourceLang
      );
      
      logger.success(444);
      return {
        success: true,
        result: result
      };
    } catch (error) {
      logger.failure(444, error.message);
      throw error;
    }
  }

  /**
   * Action 4/40: Create Catalog (Inactive Products) from Legacy Format
   * @returns {Promise<Object>} - Creation result
   */
  async action4() {
    logger.action(4, "Create catalog (inactive products) from legacy format");
    
    try {
      // 1. Get seller address from config
      const sellerAddress = this.config.get('seller.address');
      if (!sellerAddress) {
        throw new Error('SELLER_ADDRESS not configured');
      }
      
      logger.info(`Seller address: ${sellerAddress}`);
      
      // 2. Load contracts
      logger.info('Loading contracts...');
      const spiralEngine = await this.contractManager.loadUUPSContract('SpiralEngine');
      const productRegistry = await this.contractManager.loadUUPSContract('ProductRegistry');
      logger.info('Contracts loaded ✓');
      
      // 3. Validate seller access
      await this.validateSellerAccess(spiralEngine, sellerAddress);
      
      // 4. Clear existing catalog
      const clearResult = await this.clearCatalog(productRegistry, sellerAddress);
      
      // 5. Create catalog from data file
      const createResult = await this.createCatalogFromDataFile(productRegistry, sellerAddress);
      
      logger.success(4);
      return {
        success: true,
        productsCleared: clearResult.cleared,
        productsCreated: createResult.productsCreated,
        productsFailed: createResult.productsFailed,
        totalProducts: createResult.totalProducts
      };
    } catch (error) {
      logger.failure(4, error.message);
      throw error;
    }
  }
  
  /**
   * Action 6: Clear Seller Catalog
   * @returns {Promise<Object>} - Clearing result
   */
  async action6() {
    logger.action(6, "Clear seller catalog");
    
    try {
      // 1. Get seller address from config
      const sellerAddress = this.config.get('seller.address');
      if (!sellerAddress) {
        throw new Error('SELLER_ADDRESS not configured');
      }
      
      logger.info(`Seller address: ${sellerAddress}`);
      
      // 2. Load ProductRegistry contract
      logger.info('Loading ProductRegistry contract...');
      const productRegistry = await this.contractManager.loadUUPSContract('ProductRegistry');
      logger.info('Contract loaded ✓');
      
      // 3. Delegate to clearCatalog helper
      const result = await this.clearCatalog(productRegistry, sellerAddress);
      
      logger.success(6);
      return {
        success: true,
        cleared: result.cleared,
        skipped: result.skipped
      };
    } catch (error) {
      logger.failure(6, error.message);
      throw error;
    }
  }
  
  /**
   * Action 40: Alias for action4()
   * @returns {Promise<Object>} - Creation result
   */
  async action40() {
    return this.action4();
  }
  
  /**
   * Action 46: Activate Existing Products
   * Batch activate all inactive products in seller's catalog
   * 
   * @returns {Promise<Object>} - Activation result
   */
  async action46() {
    logger.action(46, "Activate existing products in catalog");
    
    try {
      // 1. Get seller address from config
      const sellerAddress = this.config.get('seller.address');
      if (!sellerAddress) {
        throw new Error('SELLER_ADDRESS not configured');
      }
      
      logger.info(`Seller address: ${sellerAddress}`);
      
      // 2. Load contracts
      logger.info('Loading contracts...');
      const spiralEngine = await this.contractManager.loadUUPSContract('SpiralEngine');
      const productRegistry = await this.contractManager.loadUUPSContract('ProductRegistry');
      logger.info('Contracts loaded ✓');
      
      // 3. Validate seller access
      await this.validateSellerAccess(spiralEngine, sellerAddress);
      
      // 4. Activate products
      const result = await this.activateProducts(productRegistry, sellerAddress);
      
      logger.success(46);
      return {
        success: true,
        totalProducts: result.totalProducts,
        activatedCount: result.activatedCount,
        alreadyActiveCount: result.alreadyActiveCount,
        failedCount: result.failedCount
      };
    } catch (error) {
      logger.failure(46, error.message);
      throw error;
    }
  }

  // NOTE: action888 moved to InviteActions (Layer 4A)
  // Reason: action888 is seller initialization pipeline, belongs to invite/social layer
  // Location: scripts/lib/actions/InviteActions.js
  // Routing: Updated in ActionsManager.executeAction()
  
  // ================================================================
  // PRIVATE HELPERS
  // ================================================================
  
  /**
   * Validate seller has activation + SELLER_ROLE
   * @param {Contract} spiralEngine - SpiralEngine contract
   * @param {string} sellerAddress - Seller address
   * @throws {Error} If seller not valid
   * @private
   */
  async validateSellerAccess(spiralEngine, sellerAddress) {
    logger.info('Validating seller access...');
    
    // Check activation
    const usedInvite = await spiralEngine.usedInviteByUser(sellerAddress);
    if (usedInvite === 0 || usedInvite === 0n) {
      throw new Error(`Seller ${sellerAddress} not activated`);
    }
    
    logger.info(`  Seller activated ✓ (used invite: ${usedInvite})`);
    
    // Check SELLER_ROLE
    const SELLER_ROLE = await spiralEngine.SELLER_ROLE();
    const hasSellerRole = await spiralEngine.hasRole(SELLER_ROLE, sellerAddress);
    if (!hasSellerRole) {
      throw new Error(`Seller ${sellerAddress} does not have SELLER_ROLE`);
    }
    
    logger.success('Seller access validated ✓');
  }
  
  /**
   * Clear existing seller catalog
   * @param {Contract} productRegistry - ProductRegistry contract
   * @param {string} sellerAddress - Seller address
   * @returns {Promise<Object>} - Clearing result {cleared, skipped}
   * @private
   */
  async clearCatalog(productRegistry, sellerAddress) {
    logger.info('Clearing existing catalog...');
    
    try {
      // 1. Check existing products
      const existingProducts = await productRegistry.getProductsBySeller(sellerAddress);
      logger.info(`Found ${existingProducts.length} existing products`);
      
      if (existingProducts.length === 0) {
        logger.info('Catalog already empty, skipping clearing ✓');
        return { cleared: 0, skipped: true };
      }
      
      // 2. Get seller signer
      const sellerPrivateKey = this.config.get('seller.privateKey');
      if (!sellerPrivateKey) {
        throw new Error('SELLER_PRIVATE_KEY not found in config');
      }
      
      const sellerSigner = this.ethersUtils.getSigner(sellerPrivateKey);
      const productRegistryWithSigner = productRegistry.connect(sellerSigner);
      
      // 3. Clear catalog
      logger.info('Sending clearSellerCatalog transaction...');
      const tx = await productRegistryWithSigner.clearSellerCatalog(sellerAddress, {
        gasLimit: this.config.get('network.name') === 'polygon' ? 2000000 : 1000000
      });
      
      logger.info(`Transaction sent: ${tx.hash}`);
      const receipt = await tx.wait();
      logger.info(`Transaction confirmed in block ${receipt.blockNumber}`);
      
      // 4. Validate clearing
      const remainingProducts = await productRegistry.getProductsBySeller(sellerAddress);
      if (remainingProducts.length !== 0) {
        throw new Error(`Catalog clearing failed: ${remainingProducts.length} products remain`);
      }
      
      logger.success(`Catalog cleared: ${existingProducts.length} products removed ✓`);
      return { cleared: existingProducts.length, skipped: false };
      
    } catch (error) {
      if (error.message && error.message.includes('Catalog is already empty')) {
        logger.info('Catalog already empty ✓');
        return { cleared: 0, skipped: true };
      }
      throw error;
    }
  }
  
  /**
   * Create catalog from data file format
   * Uses product_registry_upload_data.json (specific JSON structure)
   * 
   * @param {Contract} productRegistry - ProductRegistry contract
   * @param {string} sellerAddress - Seller address
   * @returns {Promise<Object>} - Creation result
   * @private
   */
  async createCatalogFromDataFile(productRegistry, sellerAddress) {
    logger.info('Creating catalog from data file format...');
    
    const fs = require('fs');
    const path = require('path');
    
    // 1. Load data file
    const projectRoot = this.config.get('paths.projectRoot') || process.cwd();
    const dataFile = path.join(projectRoot, 'bot', 'catalog', 'product_registry_upload_data.json');
    
    if (!fs.existsSync(dataFile)) {
      throw new Error(`Data file not found: ${dataFile}`);
    }
    
    const productsData = JSON.parse(fs.readFileSync(dataFile, 'utf8'));
    logger.info(`Loaded ${productsData.length} products from legacy data file`);
    
    // 2. Gas estimation
    await this.estimateGasForBatch(productRegistry, sellerAddress, productsData);
    
    // 3. Check seller balance
    const balance = await this.ethersUtils.provider.getBalance(sellerAddress);
    const balanceEth = this.ethersUtils.formatEther(balance);
    logger.info(`Seller balance: ${balanceEth} ETH`);
    
    // 4. Get seller signer
    const sellerPrivateKey = this.config.get('seller.privateKey');
    const sellerSigner = this.ethersUtils.getSigner(sellerPrivateKey);
    const productRegistryWithSigner = productRegistry.connect(sellerSigner);
    
    // 5. Create products loop
    let created = 0;
    let failed = 0;
    
    for (let i = 0; i < productsData.length; i++) {
      const product = productsData[i];
      
      try {
        logger.info(`[${i+1}/${productsData.length}] Creating product: ${product.id}`);
        logger.info(`  componentIds: ${product.componentIds?.join(', ') || '[]'}`);
        logger.info(`  metadataCID: ${product.metadataCID}`);
        
        const tx = await productRegistryWithSigner.createProduct(
          product.componentIds || [],
          product.metadataCID,
          { gasLimit: 1000000 }
        );
        
        const receipt = await tx.wait();
        created++;
        logger.success(`  Product ${product.id} created ✓ (tx: ${receipt.hash})`);
        
        // Delay for mainnet
        if (this.config.get('network.name') === 'polygon' && i < productsData.length - 1) {
          logger.info('  Waiting 2 seconds before next product...');
          await new Promise(resolve => setTimeout(resolve, 2000));
        }
        
      } catch (error) {
        failed++;
        logger.error(`  Failed to create product ${product.id}: ${error.message}`);
      }
    }
    
    // 6. Validate creation
    logger.info('Validating created products...');
    
    // Note: getProductsBySellerFull() requires caller to be seller
    const finalProducts = await productRegistryWithSigner.getProductsBySellerFull();
    logger.info(`Final catalog size: ${finalProducts.length} products`);
    
    // Check all are inactive
    const activeCount = finalProducts.filter(p => p.active).length;
    if (activeCount > 0) {
      logger.warn(`Warning: ${activeCount} products are active (expected all inactive)`);
    } else {
      logger.success('All products created as inactive ✓');
    }
    
    // Verify data integrity
    let matchedCount = 0;
    for (const product of finalProducts) {
      const originalProduct = productsData.find(p => p.metadataCID === product.metadataCID);
      if (originalProduct) {
        matchedCount++;
      }
    }
    
    logger.info(`Data integrity: ${matchedCount}/${finalProducts.length} products matched`);
    
    logger.success(`Catalog created: ${created} products, ${failed} failed ✓`);
    
    return {
      productsCreated: created,
      productsFailed: failed,
      totalProducts: productsData.length,
      activeProducts: activeCount
    };
  }
  
  /**
   * Activate all inactive products in seller's catalog
   * @param {Contract} productRegistry - ProductRegistry contract
   * @param {string} sellerAddress - Seller address
   * @returns {Promise<Object>} - Activation result
   * @private
   */
  async activateProducts(productRegistry, sellerAddress) {
    logger.info('Activating products in catalog...');
    
    // 1. Get seller signer
    const sellerPrivateKey = this.config.get('seller.privateKey');
    if (!sellerPrivateKey) {
      throw new Error('SELLER_PRIVATE_KEY not found in config');
    }
    
    const sellerSigner = this.ethersUtils.getSigner(sellerPrivateKey);
    const productRegistryWithSigner = productRegistry.connect(sellerSigner);
    
    // 2. Get all seller products
    const products = await productRegistryWithSigner.getProductsBySellerFull();
    logger.info(`Found ${products.length} products`);
    
    if (products.length === 0) {
      logger.warn('No products to activate. Create catalog first (action 4)');
      return {
        totalProducts: 0,
        activatedCount: 0,
        alreadyActiveCount: 0,
        failedCount: 0
      };
    }
    
    // 3. Filter inactive products
    const inactiveProducts = products.filter(p => !p.active);
    logger.info(`Inactive products: ${inactiveProducts.length}`);
    logger.info(`Already active: ${products.length - inactiveProducts.length}`);
    
    // 4. Activate each inactive product
    let activatedCount = 0;
    let failedCount = 0;
    
    for (let i = 0; i < inactiveProducts.length; i++) {
      const product = inactiveProducts[i];
      
      try {
        logger.info(`[${i+1}/${inactiveProducts.length}] Activating product ID: ${product.id}`);
        logger.info(`  metadataCID: ${product.metadataCID}`);
        
        const tx = await productRegistryWithSigner.activateProduct(product.id, {
          gasLimit: 200000
        });
        
        await tx.wait();
        activatedCount++;
        logger.success(`  Product ${product.id} activated ✓`);
        
      } catch (error) {
        failedCount++;
        logger.error(`  Failed to activate product ${product.id}: ${error.message}`);
      }
    }
    
    // 5. Validation - get final state
    logger.info('Validating activation results...');
    const finalProducts = await productRegistryWithSigner.getProductsBySellerFull();
    const finalActiveCount = finalProducts.filter(p => p.active).length;
    
    logger.info(`Final state: ${finalActiveCount}/${finalProducts.length} products active`);
    logger.success(`Activation complete: ${activatedCount} activated, ${failedCount} failed ✓`);
    
    return {
      totalProducts: products.length,
      activatedCount: activatedCount,
      alreadyActiveCount: products.length - inactiveProducts.length,
      failedCount: failedCount
    };
  }
  
  /**
   * Estimate gas for product batch creation
   * @param {Contract} productRegistry - ProductRegistry contract
   * @param {string} sellerAddress - Seller address
   * @param {Array} productsData - Products data array
   * @private
   */
  /**
   * Check if components are loaded (state files or contract)
   * Generic component detection utility
   * 
   * @param {Object} options - Check options
   * @param {string} options.network - Network to check (default: from config)
   * @returns {Promise<boolean>} - True if components found, false otherwise
   */
  async checkComponentsLoaded(options = {}) {
    const fs = require('fs');
    const path = require('path');
    
    const network = options.network || this.config.get('network.name') || 'localhost';
    
    logger.info('Checking if components are loaded...');
    
    try {
      // 1. Check state files for uploaded components
      const stateFile = path.join(
        __dirname,
        '..',
        '..',
        '..',
        'data',
        `_upload_state_${network}.json`
      );
      
      logger.info(`Checking state file: ${path.basename(stateFile)}`);
      
      if (fs.existsSync(stateFile)) {
        const stateData = JSON.parse(fs.readFileSync(stateFile, 'utf8'));
        if (stateData.components && Object.keys(stateData.components).length > 0) {
          const componentCount = Object.keys(stateData.components).length;
          logger.success(`✓ Found ${componentCount} components in state file`);
          return true;
        }
      }
      
      // 2. Check contract for components
      logger.info('Checking OrganicComponentRegistry contract...');
      
      try {
        const componentRegistry = await this.contractManager.loadUUPSContract('OrganicComponentRegistry');
        const totalComponents = await componentRegistry.getTotalComponents();
        
        if (totalComponents > 0n) {
          logger.success(`✓ Found ${totalComponents} components in contract`);
          return true;
        }
        
        logger.info('No components found in contract');
      } catch (error) {
        logger.warn(`Contract check failed: ${error.message}`);
      }
      
      logger.info('No components found');
      return false;
      
    } catch (error) {
      logger.warn(`Component check failed: ${error.message}`);
      return false; // Non-fatal - return false on errors
    }
  }

  /**
   * Smart catalog loading with automatic routing
   * Auto-detects components and routes to modern (action444) or classic (action4+46) pipeline
   * 
   * @param {string} sellerAddress - Seller address
   * @param {Object} options - Loading options
   * @param {string} options.catalogDataPath - Path to catalog data (for classic pipeline)
   * @param {boolean} options.activateProducts - Whether to activate products after creation (default: true)
   * @returns {Promise<Object>} - Catalog loading result
   */
  async loadCatalogAuto(sellerAddress, options = {}) {
    const activateProducts = options.activateProducts !== false; // default: true
    
    logger.info(`Smart catalog loading for seller: ${sellerAddress}`);
    
    try {
      // 1. Check if components are loaded
      logger.info('Detecting components...');
      const componentsLoaded = await this.checkComponentsLoaded();
      
      if (componentsLoaded) {
        // 2a. MODERN PIPELINE: Use action444
        logger.info('✓ Components detected → using MODERN pipeline (action444)');
        logger.info('Delegating to action444()...');
        
        const result = await this.action444();
        
        return {
          success: true,
          pipeline: 'modern',
          action: '444',
          ...result
        };
        
      } else {
        // 2b. CLASSIC PIPELINE: Use action4 + action46
        logger.warn('⚠️ No components detected → using CLASSIC pipeline (action4 + action46)');
        logger.info('Recommendation: Run action555 first to upload components');
        logger.info('Continuing with classic catalog creation...');
        
        // Step 1: Create catalog from data file (inactive products)
        logger.info('Step 1/2: Creating catalog (inactive)...');
        const createResult = await this.action4();
        
        let activateResult = null;
        if (activateProducts) {
          // Step 2: Activate products
          logger.info('Step 2/2: Activating products...');
          activateResult = await this.action46();
        } else {
          logger.info('Skipping product activation (activateProducts=false)');
        }
        
        return {
          success: true,
          pipeline: 'classic',
          actions: ['4', activateProducts ? '46' : null].filter(Boolean),
          createResult: createResult,
          activateResult: activateResult
        };
      }
      
    } catch (error) {
      logger.error(`Smart catalog loading failed: ${error.message}`);
      throw error;
    }
  }

  async estimateGasForBatch(productRegistry, sellerAddress, productsData) {
    if (productsData.length === 0) {
      return;
    }
    
    try {
      logger.info('Estimating gas for batch...');
      
      // Estimate for first product
      const firstProduct = productsData[0];
      const gasEstimate = await productRegistry.createProduct.estimateGas(
        firstProduct.componentIds || [],
        firstProduct.metadataCID,
        { from: sellerAddress }
      );
      
      // Get gas price
      const provider = productRegistry.runner.provider;
      const feeData = await provider.getFeeData();
      const gasPrice = feeData.gasPrice;
      
      // Calculate costs
      const gasPriceGwei = this.ethersUtils.formatUnits(gasPrice, 'gwei');
      const costPerProduct = gasEstimate * gasPrice;
      const costPerProductEth = this.ethersUtils.formatEther(costPerProduct);
      
      const totalGas = gasEstimate * BigInt(productsData.length);
      const totalCost = totalGas * gasPrice;
      const totalCostEth = this.ethersUtils.formatEther(totalCost);
      
      const recommendedBalance = (parseFloat(totalCostEth) * 1.2).toFixed(6);
      
      logger.info('Gas Estimation:');
      logger.info(`  Per product: ${gasEstimate.toString()} gas`);
      logger.info(`  Gas price: ${gasPriceGwei} Gwei`);
      logger.info(`  Cost per product: ${costPerProductEth} ETH`);
      logger.info(`  Total (${productsData.length} products): ${totalCostEth} ETH`);
      logger.info(`  Recommended balance: ${recommendedBalance} ETH (+20% buffer)`);
      
    } catch (error) {
      logger.warn(`Gas estimation failed: ${error.message}`);
      logger.info('Continuing without gas estimation...');
    }
  }
}

module.exports = CatalogActions;
