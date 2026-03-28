/**
 * Invite Actions Module (Layer 4A - Social Structure)
 * 
 * This module handles all invite-related operations and user activation,
 * providing the social structure layer for the Amanita ecosystem.
 * 
 * Responsibilities:
 * - Generate and mint invite codes (Action 777)
 * - Activate users in the system
 * - Manage invite file persistence
 * - Social graph foundation (who invited whom)
 * 
 * Layer 4A: Invite Management - Foundation for spiral social structure
 */

const { ethers } = require('hardhat');
const logger = require('../utils/Logger');
const fs = require('fs');
const path = require('path');
const { executeWithRateLimitRetry } = require('../utils/RateLimitHelpers');

class InviteActions {
  constructor(contractManager, ethersUtils, config, accessControlActions, catalogActions = null) {
    this.contractManager = contractManager;
    this.ethersUtils = ethersUtils;
    this.config = config;
    this.accessControlActions = accessControlActions;
    this.catalogActions = catalogActions; // Layer 5 dependency (set by ActionsManager)
  }

  /**
   * Validate inputs for seller initialization workflows
   * Generic validation for action7, action888, and future seller workflows
   * 
   * @param {string} inviteCode - Invite code to validate
   * @param {string} sellerAddress - Seller address to validate (optional, can be null for generation)
   * @param {Object} options - Validation options
   * @param {boolean} options.requirePrivateKey - Whether to require SELLER_PRIVATE_KEY (default: false)
   * @param {boolean} options.throwOnMissing - Whether to throw or just warn on missing key (default: false)
   * @returns {Promise<Object>} - Validation result
   * @throws {Error} If validation fails
   */
  async validateSellerInitInputs(inviteCode, sellerAddress = null, options = {}) {
    const requirePrivateKey = options.requirePrivateKey || false;
    const throwOnMissing = options.throwOnMissing || false;
    
    logger.info('Validating seller initialization inputs...');
    
    // 1. Validate invite code
    if (!inviteCode || typeof inviteCode !== 'string' || inviteCode.trim() === '') {
      throw new Error('Invite code is required and must be a non-empty string');
    }
    
    logger.info(`✓ Invite code: ${inviteCode}`);
    
    // 2. Validate seller address (if provided)
    if (sellerAddress) {
      if (!this.ethersUtils.isValidAddress(sellerAddress)) {
        throw new Error(`Invalid seller address: ${sellerAddress}`);
      }
      logger.info(`✓ Seller address: ${sellerAddress}`);
    } else {
      logger.info('✓ Seller address: will be generated');
    }
    
    // 3. Check SELLER_PRIVATE_KEY (optional but recommended)
    const sellerPrivateKey = this.config.get('seller.privateKey');
    const hasPrivateKey = !!sellerPrivateKey;
    
    if (requirePrivateKey && !hasPrivateKey) {
      if (throwOnMissing) {
        throw new Error('SELLER_PRIVATE_KEY is required but not found in config');
      } else {
        logger.warn('⚠️ SELLER_PRIVATE_KEY not found - some operations may fail');
        logger.warn('⚠️ Catalog operations require seller private key for transactions');
      }
    }
    
    if (hasPrivateKey) {
      logger.info('✓ SELLER_PRIVATE_KEY: configured');
    }
    
    logger.success('Input validation passed ✓');
    
    return {
      valid: true,
      inviteCode: inviteCode.trim(),
      sellerAddress: sellerAddress,
      hasPrivateKey: hasPrivateKey
    };
  }

  /**
   * Validate invite code on blockchain
   * Generic validation for any invite code usage
   * 
   * @param {Contract} spiralEngine - SpiralEngine contract instance
   * @param {string} inviteCode - Invite code to validate
   * @param {Object} options - Validation options
   * @param {boolean} options.checkUsed - Whether to check if invite is already used (default: true)
   * @param {boolean} options.throwOnUsed - Whether to throw if invite is used (default: true)
   * @returns {Promise<Object>} - Validation result with invite details
   * @throws {Error} If validation fails
   */
  async validateInviteCode(spiralEngine, inviteCode, options = {}) {
    const checkUsed = options.checkUsed !== false; // default: true
    const throwOnUsed = options.throwOnUsed !== false; // default: true
    
    logger.info(`Validating invite code on blockchain: ${inviteCode}`);
    
    try {
      // 1. Check system has any invites
      const totalInvites = await spiralEngine.totalInvitesMinted();
      logger.info(`Total invites in system: ${totalInvites}`);
      
      if (totalInvites === 0n || totalInvites === 0) {
        throw new Error(
          'No invites exist in SpiralEngine. ' +
          'Please run Action 777 first to generate deployer invites.'
        );
      }
      
      // 2. Check specific invite exists
      logger.info('Checking if invite exists...');
      const inviteExists = await spiralEngine.inviteCodeExists(inviteCode);
      
      if (!inviteExists) {
        const errorMsg = 
          `Invite code "${inviteCode}" not found in blockchain. ` +
          'Possible causes:\n' +
          '  1. Blockchain node was restarted (old session)\n' +
          '  2. Invite not created yet\n' +
          '  3. Typo in invite code\n' +
          'Solution: Run Action 777 to generate new invites.';
        throw new Error(errorMsg);
      }
      
      logger.success('Invite exists ✓');
      
      // 3. Get invite tokenId
      const tokenId = await spiralEngine.inviteCodeToTokenId(inviteCode);
      logger.info(`Invite tokenId: ${tokenId}`);
      
      // 4. Check if invite is used (optional)
      let isUsed = false;
      if (checkUsed) {
        logger.info('Checking if invite is already used...');
        isUsed = await spiralEngine.isInviteUsed(tokenId);
        logger.info(`Invite used: ${isUsed}`);
        
        if (isUsed && throwOnUsed) {
          throw new Error(
            `Invite code "${inviteCode}" (tokenId: ${tokenId}) has already been used. ` +
            'Please use a different invite code.'
          );
        }
        
        if (isUsed) {
          logger.warn(`⚠️ Invite "${inviteCode}" is already used`);
        } else {
          logger.success('Invite is available ✓');
        }
      }
      
      logger.success('Invite validation passed ✓');
      
      return {
        valid: true,
        inviteCode: inviteCode,
        tokenId: tokenId.toString(),
        isUsed: isUsed,
        totalInvitesInSystem: totalInvites.toString()
      };
      
    } catch (error) {
      logger.error(`Invite validation failed: ${error.message}`);
      throw error;
    }
  }

  /**
   * Activate seller with full setup (shared helper)
   * Generic activation logic extracted from action7, shared with action888
   * 
   * @param {Contract} spiralEngine - SpiralEngine contract instance
   * @param {string} inviteCode - Invite code to use for activation
   * @param {string} sellerAddress - Seller address to activate
   * @param {Object} options - Activation options
   * @param {number} options.inviteCount - Number of invites to generate (default: 12)
   * @param {boolean} options.grantRoles - Whether to grant SELLER_ROLE and ACTIVATOR_ROLE (default: true)
   * @param {boolean} options.saveInvites - Whether to save invites to file (default: true)
   * @param {string} options.fileContext - Context for invite file naming (default: 'activation')
   * @returns {Promise<Object>} - Activation result
   */
  async activateSeller(spiralEngine, inviteCode, sellerAddress, options = {}) {
    const inviteCount = options.inviteCount || 12;
    const grantRoles = options.grantRoles !== false; // default: true
    const saveInvites = options.saveInvites !== false; // default: true
    const fileContext = options.fileContext || 'activation';
    
    logger.info(`Activating seller: ${sellerAddress}`);
    logger.info(`Using invite: ${inviteCode}`);
    logger.info(`Invite count: ${inviteCount}`);
    
    try {
      // 1. Generate new invites for the seller
      const newInvites = this.generateAmanitaInviteCodes(inviteCount);
      logger.info(`Generated ${newInvites.length} invites for seller`);
      
      // 2. Activate user on-chain
      logger.info('Calling activateUser on blockchain...');
      const deploySigner = this.ethersUtils.getSigner();
      const spiralEngineWithSigner = spiralEngine.connect(deploySigner);
      
      const tx = await spiralEngineWithSigner.activateUser(
        inviteCode,
        sellerAddress,
        newInvites,
        0 // expiry: 0 = perpetual
      );
      
      await tx.wait();
      logger.success('Seller activated on-chain ✓');
      logger.info(`Transaction: ${tx.hash}`);
      
      // ✅ FIX: Wait for nonce update after activateUser
      logger.info('⏱️ Waiting 500ms for nonce update after activateUser...');
      await new Promise(resolve => setTimeout(resolve, 500));
      
      // 3. Grant roles (optional)
      const rolesGranted = [];
      if (grantRoles) {
        logger.info('Granting roles...');
        
        // Grant SELLER_ROLE
        await this.accessControlActions.grantSellerRole(spiralEngine, sellerAddress);
        rolesGranted.push('SELLER_ROLE');
        logger.success('SELLER_ROLE granted ✓');
        
        // ✅ FIX: Wait for nonce update between role grants
        logger.info('⏱️ Waiting 500ms for nonce update between role grants...');
        await new Promise(resolve => setTimeout(resolve, 500));
        
        // Grant ACTIVATOR_ROLE
        await this.accessControlActions.grantActivatorRole(spiralEngine, sellerAddress);
        rolesGranted.push('ACTIVATOR_ROLE');
        logger.success('ACTIVATOR_ROLE granted ✓');
      }
      
      // 4. Save invites to file (optional)
      if (saveInvites) {
        await this.saveUserInvites(sellerAddress, newInvites, fileContext);
        logger.success('Invites saved to file ✓');
      }
      
      logger.success('Seller activation complete ✓');
      
      return {
        success: true,
        sellerAddress: sellerAddress,
        inviteCodeUsed: inviteCode,
        invitesCreated: newInvites.length,
        invites: newInvites,
        rolesGranted: rolesGranted,
        txHash: tx.hash
      };
      
    } catch (error) {
      logger.error(`Seller activation failed: ${error.message}`);
      throw error;
    }
  }

  /**
   * Action 7: Create First Seller (Bootstrap)
   * Creates the very first seller in the system with full configuration
   * 
   * @param {string} inviteCode - Invite code for activation (optional, uses config)
   * @returns {Promise<Object>} - Result with seller address and configuration
   */
  async action7(inviteCode) {
    logger.action(7, "Create first seller (bootstrap)");
    
    try {
      // 1. Resolve invite code
      if (!inviteCode) {
        inviteCode = this.config.get('seller.inviteCode') || this.config.get('bootstrap.inviteCode');
        if (!inviteCode) {
          throw new Error('Invite code not provided. Use: action7(inviteCode) or set seller.inviteCode in config');
        }
      }
      
      logger.info(`Invite code: ${inviteCode}`);
      
      // 2. Get or generate seller wallet
      let sellerAddress;
      let sellerPrivateKey;
      let wasGenerated = false;
      
      const existingAddress = this.config.get('seller.address');
      const existingKey = this.config.get('seller.privateKey');
      
      if (existingAddress && existingKey) {
        logger.info('Using existing seller from config');
        sellerAddress = existingAddress;
        sellerPrivateKey = existingKey;
      } else {
        logger.info('Generating new seller wallet...');
        const wallet = this.ethersUtils.createRandomWallet();
        sellerAddress = wallet.address;
        sellerPrivateKey = wallet.privateKey;
        wasGenerated = true;
        
        logger.warn('⚠️ NEW WALLET GENERATED - SAVE THESE CREDENTIALS:');
        console.log(`\nSELLER_ADDRESS=${sellerAddress}`);
        console.log(`SELLER_PRIVATE_KEY=${sellerPrivateKey}\n`);
      }
      
      // 3. Load SpiralEngine
      logger.info('Loading contracts...');
      const spiralEngine = await this.contractManager.loadUUPSContract('SpiralEngine');
      logger.info('Contracts loaded ✓');
      
      // 4. Activate seller using shared helper
      logger.info(`Activating seller ${sellerAddress}...`);
      const activationResult = await this.activateSeller(
        spiralEngine,
        inviteCode,
        sellerAddress,
        {
          inviteCount: 12,
          grantRoles: true,
          saveInvites: true,
          fileContext: 'action7_bootstrap'
        }
      );
      
      logger.success(7);
      return {
        success: true,
        sellerAddress: sellerAddress,
        sellerPrivateKey: wasGenerated ? sellerPrivateKey : '[EXISTING - NOT SHOWN]',
        wasGenerated: wasGenerated,
        invitesCreated: activationResult.invitesCreated,
        invites: activationResult.invites,
        rolesGranted: activationResult.rolesGranted,
        txHash: activationResult.txHash
      };
    } catch (error) {
      logger.failure(7, error.message);
      throw error;
    }
  }
  
  /**
   * Action 777: Root invites generation for deployer
   * Creates 12 initial invite codes that can be used to activate first users
   * 
   * @returns {Promise<Object>} - Result with invites array
   */
  async action777() {
    console.log("\n" + "=".repeat(60));
    console.log("🎲 Action 777: Генерация инвайтов для деплоера");
    console.log("=".repeat(60));
    
    try {
      // ШАГ 1/4: Загрузка SpiralEngine
      console.log("\n📦 Шаг 1/4: Загрузка SpiralEngine...");
      const spiralEngine = await this.contractManager.loadUUPSContract('SpiralEngine');
      const spiralEngineAddress = await spiralEngine.getAddress();
      console.log("✅ SpiralEngine загружен:", spiralEngineAddress);
      
      // Проверка состояния до минтинга (with retry mechanism for RPC rate limits)
      const totalInvitesBefore = await executeWithRateLimitRetry(
        () => spiralEngine.totalInvitesMinted(),
        {
          maxRetries: 3,
          initialDelayMs: 10000,
          rpcManager: this.contractManager?.rpcManager,
          ethersUtils: this.ethersUtils,
          contractManager: this.contractManager,
          operationName: 'totalInvitesMinted (before minting)'
        }
      );
      console.log(`📊 Текущее количество инвайтов: ${totalInvitesBefore}`);
      
      // ШАГ 2/4: Проверка прав деплоера (delegation → AccessControlActions)
      console.log("\n🔐 Шаг 2/4: Проверка прав деплоера...");
      await this.accessControlActions.validateDeployerAccess(spiralEngine);
      console.log("✅ Деплоер имеет необходимые права");
      
      // ШАГ 3/4: Генерация и минтинг инвайтов
      console.log("\n🎲 Шаг 3/4: Генерация и минтинг инвайтов...");
      const invites = await this.generateAndMintInvites(spiralEngine);
      
      // ШАГ 4/4: Финальная проверка (with retry mechanism for RPC rate limits)
      console.log("\n📊 Шаг 4/4: Финальная проверка...");
      const totalInvitesAfter = await executeWithRateLimitRetry(
        () => spiralEngine.totalInvitesMinted(),
        {
          maxRetries: 3,
          initialDelayMs: 10000,
          rpcManager: this.contractManager?.rpcManager,
          ethersUtils: this.ethersUtils,
          contractManager: this.contractManager,
          operationName: 'totalInvitesMinted (after minting)'
        }
      );
      console.log(`✅ Инвайтов после генерации: ${totalInvitesAfter}`);
      console.log(`✅ Создано новых инвайтов: ${totalInvitesAfter - totalInvitesBefore}`);
      
      console.log("\n" + "=".repeat(60));
      console.log("✅ Action 777 завершен успешно!");
      console.log("=".repeat(60));
      
      return {
        success: true,
        invites: invites,
        totalCreated: invites.length
      };
    } catch (error) {
      logger.failure(777, error.message);
      throw error;
    }
  }
  
  /**
   * Action 888: Full Seller Initialization Pipeline
   * Complete workflow: validation → activation → roles → SBT → catalog → invites
   * 
   * @param {string} inviteCode - Invite code for activation (optional, from config)
   * @param {string} sellerAddress - Seller address (optional, from config)
   * @param {Object} options - Pipeline options
   * @param {boolean} options.skipSBT - Skip SBT integration (default: false)
   * @param {boolean} options.skipCatalog - Skip catalog loading (default: false)
   * @param {boolean} options.skipAdditionalInvites - Skip final invite generation (default: false)
   * @returns {Promise<Object>} - Complete initialization result
   */
  async action888(inviteCode, sellerAddress, options = {}) {
    logger.action(888, "Full seller initialization pipeline");
    
    const skipSBT = options.skipSBT || false;
    const skipCatalog = options.skipCatalog || false;
    const skipAdditionalInvites = options.skipAdditionalInvites || false;
    
    try {
      // STEP 1: Validate inputs
      logger.info('Step 1/8: Validating inputs...');
      const validation = await this.validateSellerInitInputs(inviteCode, sellerAddress, {
        requirePrivateKey: !skipCatalog, // Private key needed for catalog
        throwOnMissing: false // Warn only
      });
      
      inviteCode = validation.inviteCode;
      sellerAddress = validation.sellerAddress;
      
      // If sellerAddress not provided, generate wallet
      if (!sellerAddress) {
        logger.info('Generating new seller wallet...');
        const wallet = this.ethersUtils.createRandomWallet();
        sellerAddress = wallet.address;
        const sellerPrivateKey = wallet.privateKey;
        
        logger.warn('⚠️ NEW WALLET GENERATED - SAVE THESE CREDENTIALS:');
        console.log(`\nSELLER_ADDRESS=${sellerAddress}`);
        console.log(`SELLER_PRIVATE_KEY=${sellerPrivateKey}\n`);
      }
      
      // STEP 2: Load contracts
      logger.info('Step 2/8: Loading contracts...');
      const spiralEngine = await this.contractManager.loadUUPSContract('SpiralEngine');
      logger.success('Contracts loaded ✓');
      
      // STEP 3: Validate invite code on blockchain
      logger.info('Step 3/8: Validating invite on blockchain...');
      await this.validateInviteCode(spiralEngine, inviteCode);
      logger.success('Invite validated ✓');
      
      // STEP 4-7: Activate seller (includes activation + roles)
      logger.info('Step 4-7/8: Activating seller...');
      const activationResult = await this.activateSeller(
        spiralEngine,
        inviteCode,
        sellerAddress,
        {
          inviteCount: 12,
          grantRoles: true,
          saveInvites: true,
          fileContext: 'action888_activation'
        }
      );
      logger.success('Seller activated with roles ✓');
      
      // STEP 8: Setup SoulIdentity (SBT integration)
      let sbtResult = null;
      if (!skipSBT) {
        logger.info('Step 8/8: Setting up SoulIdentity (SBT)...');
        sbtResult = await this.accessControlActions.setupSoulIdentity(sellerAddress, {
          userType: 'seller',
          level: 1,
          reputation: 100
        });
        
        if (sbtResult.skipped) {
          logger.warn('⚠️ SBT integration skipped (SoulIdentity not deployed)');
        } else {
          logger.success('SoulIdentity configured ✓');
        }
      } else {
        logger.info('Step 8/8: Skipping SBT integration (skipSBT=true)');
      }
      
      // STEP 9: Load catalog (smart routing)
      let catalogResult = null;
      if (!skipCatalog) {
        if (!this.catalogActions) {
          logger.warn('⚠️ CatalogActions not injected - skipping catalog loading');
          logger.warn('⚠️ Set catalogActions dependency in ActionsManager');
        } else {
          logger.info('Step 9/8: Loading catalog (smart routing)...');
          catalogResult = await this.catalogActions.loadCatalogAuto(sellerAddress, {
            activateProducts: true
          });
          logger.success(`Catalog loaded via ${catalogResult.pipeline} pipeline ✓`);
        }
      } else {
        logger.info('Step 9/8: Skipping catalog loading (skipCatalog=true)');
      }
      
      // STEP 10: Generate additional invites for seller
      let additionalInvitesResult = null;
      if (!skipAdditionalInvites) {
        logger.info('Step 10/8: Generating additional invites...');
        additionalInvitesResult = await this.action11();
        logger.success('Additional invites generated ✓');
      } else {
        logger.info('Step 10/8: Skipping additional invites (skipAdditionalInvites=true)');
      }
      
      logger.success(888);
      return {
        success: true,
        sellerAddress: sellerAddress,
        inviteCodeUsed: inviteCode,
        activation: {
          invitesCreated: activationResult.invitesCreated,
          rolesGranted: activationResult.rolesGranted,
          txHash: activationResult.txHash
        },
        sbt: sbtResult,
        catalog: catalogResult,
        additionalInvites: additionalInvitesResult,
        stepsCompleted: [
          'validation',
          'contracts',
          'invite_check',
          'activation',
          skipSBT ? null : 'sbt',
          skipCatalog ? null : 'catalog',
          skipAdditionalInvites ? null : 'additional_invites'
        ].filter(Boolean)
      };
      
    } catch (error) {
      logger.failure(888, error.message);
      throw error;
    }
  }

  /**
   * Action 846: Prepare Activity Creator Address
   * Unified flow for ActivityRegistry creator readiness:
   * - activate user with DEPLOYER_INVITE (if not activated)
   * - ensure ACTIVATOR_ROLE (if not granted)
   *
   * @param {Object} options - Optional overrides
   * @param {string} options.activityCreatorAddress - Target address (fallback: config.activityCreator.address)
   * @param {string} options.inviteCode - Invite code (fallback: config.deployer.invite / env DEPLOYER_INVITE)
   * @returns {Promise<Object>} - Preparation result
   */
  async action846(options = {}) {
    logger.action(846, "Prepare ACTIVITY_CREATOR_ADDRESS (activate + ensure ACTIVATOR_ROLE)");

    try {
      const activityCreatorAddress =
        options.activityCreatorAddress ||
        this.config.get('activityCreator.address') ||
        process.env.ACTIVITY_CREATOR_ADDRESS;

      const inviteCode =
        options.inviteCode ||
        this.config.get('deployer.invite') ||
        process.env.DEPLOYER_INVITE;

      if (!activityCreatorAddress || !this.ethersUtils.isValidAddress(activityCreatorAddress)) {
        throw new Error('ACTIVITY_CREATOR_ADDRESS is required and must be a valid address');
      }

      if (!inviteCode || typeof inviteCode !== 'string' || inviteCode.trim() === '') {
        throw new Error('DEPLOYER_INVITE is required for activity creator activation');
      }

      logger.info(`Activity creator address: ${activityCreatorAddress}`);
      logger.info(`Invite code: ${inviteCode}`);

      const spiralEngine = await this.contractManager.loadUUPSContract('SpiralEngine');
      logger.info('SpiralEngine contract loaded ✓');

      const usedInvite = await spiralEngine.usedInviteByUser(activityCreatorAddress);
      const isActivated = usedInvite > 0;

      let activationResult = null;
      if (!isActivated) {
        logger.info('Address is not activated, running activateUser...');
        activationResult = await this.activateUser(spiralEngine, inviteCode, activityCreatorAddress);
      } else {
        logger.info(`Address already activated (usedInviteByUser=${usedInvite})`);
      }

      const ACTIVATOR_ROLE = await spiralEngine.ACTIVATOR_ROLE();
      const hasActivatorRole = await spiralEngine.hasRole(ACTIVATOR_ROLE, activityCreatorAddress);

      let roleGranted = false;
      if (!hasActivatorRole) {
        logger.info('ACTIVATOR_ROLE missing, granting role...');
        await this.accessControlActions.grantActivatorRole(spiralEngine, activityCreatorAddress);
        roleGranted = true;
      } else {
        logger.info('ACTIVATOR_ROLE already granted');
      }

      const finalUsedInvite = await spiralEngine.usedInviteByUser(activityCreatorAddress);
      const finalHasActivatorRole = await spiralEngine.hasRole(ACTIVATOR_ROLE, activityCreatorAddress);

      if (finalUsedInvite == 0 || !finalHasActivatorRole) {
        throw new Error(
          `Action 846 verification failed: activated=${finalUsedInvite != 0}, activatorRole=${finalHasActivatorRole}`
        );
      }

      logger.success(846);
      return {
        success: true,
        activityCreatorAddress,
        wasActivated: !isActivated,
        activationResult,
        roleGranted,
        finalState: {
          usedInviteByUser: finalUsedInvite.toString(),
          hasActivatorRole: finalHasActivatorRole
        }
      };
    } catch (error) {
      logger.failure(846, error.message);
      throw error;
    }
  }

  /**
   * Action 11: Generate Invites for Active Seller
   * Seller mints their own invites (requires SELLER_ROLE)
   * 
   * @returns {Promise<Object>} - Generation result
   */
  async action11() {
    logger.action(11, "Generate invites for active seller");
    
    try {
      // 1. Get seller address and config
      const sellerAddress = this.config.get('seller.address');
      if (!sellerAddress) {
        throw new Error('SELLER_ADDRESS not configured');
      }
      
      const inviteCount = this.config.get('seller.inviteCount') || 12;
      logger.info(`Seller address: ${sellerAddress}`);
      logger.info(`Invite count: ${inviteCount}`);
      
      // 2. Load SpiralEngine
      logger.info('Loading SpiralEngine contract...');
      const spiralEngine = await this.contractManager.loadUUPSContract('SpiralEngine');
      logger.info('Contract loaded ✓');
      
      // 3. Validate seller access (delegation to AccessControlActions)
      await this.accessControlActions.validateSellerAccess(spiralEngine, sellerAddress);
      
      // 4. Generate and mint invites FOR SELLER
      const invites = await this.generateAndMintInvitesForSeller(
        spiralEngine, 
        sellerAddress, 
        inviteCount
      );
      
      // 5. Save to file
      await this.saveUserInvites(sellerAddress, invites, 'action11');
      
      logger.success(11);
      return {
        success: true,
        sellerAddress: sellerAddress,
        invitesCreated: invites.length,
        invites: invites
      };
    } catch (error) {
      logger.failure(11, error.message);
      throw error;
    }
  }

  /**
   * Генерация и минтинг инвайтов для деплоера
   * @param {Object} spiralEngine - SpiralEngine contract instance
   * @returns {Promise<Array>} - Array of minted invite codes
   * @private
   */
  async generateAndMintInvites(spiralEngine) {
    const signer = this.ethersUtils.getSigner();
    const deployerAddress = await signer.getAddress();

    console.log(`🔷 Минтим инвайты от адреса: ${deployerAddress}`);

    // Генерация 12 инвайтов
    console.log('\n🔷 Генерируем 12 инвайтов для деплоера...');
    const invites = this.generateAmanitaInviteCodes(12);

    // Один батч: mintInviteBatch(inviteCodes, expiries) — одна tx вместо 12 (RPC-надежность)
    console.log('\n🔷 Минтим 1 батч по 12 инвайтов (mintInviteBatch)...');

    const chainId = Number(await this.ethersUtils.getNetworkId());
    const txOverridesPolygon = chainId === 137 ? { gasPrice: ethers.parseUnits('700', 'gwei') } : {};

    const inviteCodes = invites;
    const expiries = Array(invites.length).fill(0);

    const doBatchMint = () => {
      const currentSigner = this.ethersUtils.getSigner();
      const spiralEngineWithSigner = spiralEngine.connect(currentSigner);
      return spiralEngineWithSigner.mintInviteBatch(inviteCodes, expiries, txOverridesPolygon);
    };

    const tx = await executeWithRateLimitRetry(doBatchMint, {
      maxRetries: 3,
      initialDelayMs: 10000,
      rpcManager: this.contractManager?.rpcManager,
      ethersUtils: this.ethersUtils,
      contractManager: this.contractManager,
      operationName: 'mintInviteBatch (12 invites)'
    });

    logger.info(`[TX] Batch transaction sent: ${tx.hash}`);
    console.log(`[TX] Check on polygonscan: https://polygonscan.com/tx/${tx.hash}`);

    await tx.wait();

    for (let i = 0; i < invites.length; i++) {
      console.log(`✅ Заминчен инвайт ${i + 1}/12: ${invites[i]}`);
    }
    console.log('✅ Батч 1 успешно заминчен');
    await this.saveInvitesToFile(invites);
    return invites;
  }

  /**
   * Generate and mint invites FOR SELLER
   * Similar to generateAndMintInvites but uses seller signer
   * 
   * @param {Contract} spiralEngine - SpiralEngine contract
   * @param {string} sellerAddress - Seller address
   * @param {number} count - Number of invites to generate
   * @returns {Promise<Array>} - Array of minted invite codes
   * @private
   */
  async generateAndMintInvitesForSeller(spiralEngine, sellerAddress, count) {
    // 1. Get seller signer
    const sellerPrivateKey = this.config.get('seller.privateKey');
    if (!sellerPrivateKey) {
      throw new Error('SELLER_PRIVATE_KEY not found in config');
    }
    
    const sellerSigner = this.ethersUtils.getSigner(sellerPrivateKey);
    console.log(`🔷 Минтим invites от seller: ${sellerAddress}`);
    
    // 2. Generate invite codes
    console.log(`\n🔷 Генерируем ${count} invites для seller...`);
    const invites = this.generateAmanitaInviteCodes(count);
    
    // 3. Mint invites
    console.log(`\n🔷 Минтим ${count} invites...`);
    const spiralEngineWithSigner = spiralEngine.connect(sellerSigner);
    
    // Get initial nonce for manual management (prevents race conditions in automining)
    let nonce = await sellerSigner.getNonce();
    logger.info(`Starting seller nonce: ${nonce}`);

    // Polygon mainnet (137): fixed 700 gwei above typical base fee to avoid Gas Station API errors
    const chainId = Number(await this.ethersUtils.getNetworkId());
    const txOverridesPolygon = chainId === 137 ? { gasPrice: ethers.parseUnits('700', 'gwei') } : {};
    
    for (let i = 0; i < invites.length; i++) {
      const invite = invites[i];
      const expiry = 0; // Perpetual invites
      
      const tx = await spiralEngineWithSigner.mintInvite(invite, expiry, {
        nonce: nonce++,
        ...txOverridesPolygon
      });
      await tx.wait();
      
      console.log(`✅ Invite ${i + 1}/${count} minted: ${invite} (tx: ${tx.hash})`);
    }
    
    console.log(`✅ All ${count} invites minted successfully`);
    
    return invites;
  }

  /**
   * Генерация инвайт кодов в формате AMANITA-XXXX-XXXX
   * @param {number} count - Количество кодов
   * @returns {Array} - Array of invite codes
   * @private
   */
  generateAmanitaInviteCodes(count) {
    const invites = [];
    const usedCodes = new Set();
    
    for (let i = 0; i < count; i++) {
      let alpha, beta, invite;
      do {
        alpha = this.generateRandomAlphanumeric(4);
        beta = this.generateRandomAlphanumeric(4);
        invite = `AMANITA-${alpha}-${beta}`;
      } while (usedCodes.has(invite));
      
      usedCodes.add(invite);
      invites.push(invite);
      console.log(`Сгенерирован инвайт ${i + 1}/${count}:`, invite);
    }
    
    return invites;
  }

  /**
   * Генерация случайной строки из букв и цифр
   * @param {number} length - Длина строки
   * @returns {string} - Random alphanumeric string
   * @private
   */
  generateRandomAlphanumeric(length) {
    const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789';
    let result = '';
    for (let i = 0; i < length; i++) {
      result += chars.charAt(Math.floor(Math.random() * chars.length));
    }
    return result;
  }

  /**
   * Save user invites to file (universal method)
   * Supports custom suffix for different use cases (deployer, seller, etc.)
   * 
   * @param {string} userAddress - User address (or 'deployer' for backward compatibility)
   * @param {Array} invites - Array of invite codes
   * @param {string} suffix - Optional filename suffix (default: network name for deployer compatibility)
   * @returns {Promise<string>} - File path
   */
  async saveUserInvites(userAddress, invites, suffix = null) {
    const network = this.config.get('network.name') || 'localhost';
    const logsDir = path.join(__dirname, "..", "..", "..", "bot", "flowers");
    
    if (!fs.existsSync(logsDir)) {
      fs.mkdirSync(logsDir, { recursive: true });
    }
    
    // Determine filename based on userAddress and suffix
    let fileName;
    if (userAddress === 'deployer' || !suffix) {
      // Network-agnostic: deployer_invites.txt (no network suffix)
      // Deployer invites универсальны (можно использовать на любой сети)
      fileName = `deployer_invites.txt`;
    } else {
      // New format: {address}_invites_{suffix}.txt
      fileName = `${userAddress}_invites_${suffix}.txt`;
    }
    
    const filePath = path.join(logsDir, fileName);
    fs.writeFileSync(filePath, invites.join("\n"));
    
    console.log(`✅ Инвайты сохранены в: ${filePath}`);
    return filePath;
  }

  /**
   * @deprecated Use saveUserInvites() instead
   * Legacy method for backward compatibility with action777
   */
  async saveInvitesToFile(invites) {
    return await this.saveUserInvites('deployer', invites);
  }

  /**
   * Activate user in the system
   * Used by ComponentActions for seller activation
   * 
   * @param {Object} spiralEngine - SpiralEngine contract instance
   * @param {string} inviteCode - Invite code to use for activation
   * @param {string} userAddress - User address to activate
   * @returns {Promise<Object>} - Activation result with new invites
   */
  async activateUser(spiralEngine, inviteCode, userAddress) {
    console.log(`\n👤 Активируем пользователя: ${userAddress}`);
    console.log(`   Используем invite: ${inviteCode}`);
    
    // Generate 12 new invites for the activated user
    const newInvites = this.generateAmanitaInviteCodes(12);
    console.log(`✅ Сгенерировано ${newInvites.length} новых invites для пользователя`);
    
    // Activate user on-chain
    const signer = this.ethersUtils.getSigner();
    const spiralEngineWithSigner = spiralEngine.connect(signer);
    
    console.log(`📝 Активация пользователя on-chain...`);
    const tx = await spiralEngineWithSigner.activateUser(inviteCode, userAddress, newInvites, 0);
    await tx.wait();
    
    console.log(`✅ Пользователь активирован успешно`);
    console.log(`   Transaction: ${tx.hash}`);
    console.log(`   Новых invites создано: ${newInvites.length}`);
    
    return {
      success: true,
      userAddress: userAddress,
      usedInvite: inviteCode,
      newInvites: newInvites,
      txHash: tx.hash
    };
  }

  /**
   * Activate seller with complete setup (activation + SELLER_ROLE)
   * Idempotent: safe to call multiple times
   * 
   * @param {Object} spiralEngine - SpiralEngine contract instance
   * @param {string} inviteCode - Invite code to use for activation
   * @param {string} sellerAddress - Seller address to activate
   * @returns {Promise<Object>} - Complete activation result
   */
  async activateSeller(spiralEngine, inviteCode, sellerAddress) {
    console.log(`\n🔷 Активация seller (полная)...`);
    console.log(`👤 Seller: ${sellerAddress}`);
    console.log(`🎫 Invite: ${inviteCode}`);
    
    // Step 1: Check current status
    console.log(`\n📊 Проверка текущего статуса...`);
    const usedInvite = await spiralEngine.usedInviteByUser(sellerAddress);
    const SELLER_ROLE = await spiralEngine.SELLER_ROLE();
    const hasSellerRole = await spiralEngine.hasRole(SELLER_ROLE, sellerAddress);
    
    const isActivated = usedInvite > 0;
    console.log(`   Активирован: ${isActivated ? '✅' : '❌'}`);
    console.log(`   SELLER_ROLE: ${hasSellerRole ? '✅' : '❌'}`);
    
    let activationResult = null;
    let newInvites = [];
    
    // Step 2: Conditional activation
    if (!isActivated) {
      console.log(`\n🔷 Активируем seller через activateUser...`);
      
      // Validate invite code exists
      const inviteExists = await spiralEngine.inviteCodeExists(inviteCode);
      if (!inviteExists) {
        throw new Error(
          `InviteActions.activateSeller: Invite код "${inviteCode}" не существует. ` +
          `Выполните Action 777 для генерации root invites.`
        );
      }
      
      // Activate via activateUser
      activationResult = await this.activateUser(spiralEngine, inviteCode, sellerAddress);
      newInvites = activationResult.newInvites;
      
      console.log(`✅ Seller активирован через activateUser()`);
      
      // Save seller invites
      await this.saveUserInvites(sellerAddress, newInvites, 'seller');
      console.log(`✅ Invites сохранены в файл`);
      
      // ✅ FIX: Wait for nonce update after activateUser
      console.log(`⏱️ Ожидаем обновление nonce после activateUser...`);
      await new Promise(resolve => setTimeout(resolve, 500));
    } else {
      console.log(`✅ Seller уже активирован (пропуск активации)`);
    }
    
    // Step 3: Conditional role assignment (delegation → AccessControlActions)
    if (!hasSellerRole) {
      console.log(`\n🔷 Назначаем SELLER_ROLE через AccessControlActions...`);
      await this.accessControlActions.grantSellerRole(spiralEngine, sellerAddress);
      console.log(`✅ SELLER_ROLE назначена успешно`);
    } else {
      console.log(`✅ SELLER_ROLE уже назначена (пропуск назначения)`);
    }
    
    // Step 4: Return structured result
    console.log(`\n✅ Seller готов к регистрации компонентов`);
    
    return {
      success: true,
      sellerAddress: sellerAddress,
      wasActivated: !isActivated,
      wasRoleGranted: !hasSellerRole,
      newInvites: newInvites,
      activationResult: activationResult
    };
  }
}

module.exports = InviteActions;

