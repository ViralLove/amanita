/**
 * Access Control Actions Module (Layer 3)
 * 
 * This module handles all access control validation and role management,
 * providing security layer for the system and foundation for DAO governance.
 * 
 * Responsibilities:
 * - Validate user roles and permissions
 * - Manage role assignments (SELLER_ROLE, ACTIVATOR_ROLE)
 * - Validate invite codes and activation status
 * - Provide user diagnostics for debugging
 * 
 * Security Critical: This layer is the foundation for DAO governance!
 */

const logger = require('../utils/Logger');
const { ethers } = require('hardhat');

class AccessControlActions {
  constructor(contractManager, ethersUtils, config) {
    this.contractManager = contractManager;
    this.ethersUtils = ethersUtils;
    this.config = config;
  }

  /**
   * Validate that deployer has SELLER_ROLE
   * Used before root invite generation (Action 777)
   * 
   * @param {Object} spiralEngine - SpiralEngine contract instance
   * @throws {Error} If deployer doesn't have SELLER_ROLE
   * @returns {Promise<void>}
   */
  async validateDeployerAccess(spiralEngine) {
    console.log("🔍 Проверяем права деплоера для генерации инвайтов...");
    
    const signer = this.ethersUtils.getSigner();
    const deployerAddress = await signer.getAddress();
    
    // Проверяем что деплоер имеет SELLER_ROLE
    const SELLER_ROLE = await spiralEngine.SELLER_ROLE();
    const hasSellerRole = await spiralEngine.hasRole(SELLER_ROLE, deployerAddress);
    
    if (!hasSellerRole) {
      throw new Error(
        `AccessControl: Deployer ${deployerAddress} не имеет роли SELLER_ROLE для генерации инвайтов. ` +
        `Убедитесь что Action 1 был выполнен и deployer получил админские права.`
      );
    }
    
    console.log(`✅ Права деплоера подтверждены: ${deployerAddress}`);
    console.log(`   SELLER_ROLE: ${SELLER_ROLE.slice(0, 10)}...`);
  }

  /**
   * Validate that seller is activated in the system
   * Used before component upload and role assignment
   * 
   * @param {Object} spiralEngine - SpiralEngine contract instance
   * @param {string} sellerAddress - Seller address to validate
   * @throws {Error} If seller is not activated
   * @returns {Promise<boolean>} - true if activated
   */
  async validateSellerAccess(spiralEngine, sellerAddress) {
    console.log(`🔍 Проверяем активацию seller: ${sellerAddress}...`);
    
    // Проверка zero address
    if (!sellerAddress || sellerAddress === ethers.ZeroAddress) {
      throw new Error('AccessControl: Seller address не может быть zero address');
    }
    
    // Проверяем активацию через usedInviteByUser
    const usedInvite = await spiralEngine.usedInviteByUser(sellerAddress);
    const isActivated = usedInvite > 0;
    
    if (!isActivated) {
      throw new Error(
        `AccessControl: Seller ${sellerAddress} не активирован в системе. ` +
        `Используйте invite code для активации перед загрузкой компонентов.`
      );
    }
    
    console.log(`✅ Seller активирован (invite token ID: ${usedInvite})`);
    return true;
  }

  /**
   * Validate invite code exists and is not used
   * Used before user activation
   * 
   * @param {Object} spiralEngine - SpiralEngine contract instance
   * @param {string} inviteCode - Invite code to validate (e.g., "AMANITA-XXXX-XXXX")
   * @throws {Error} If invite doesn't exist or already used
   * @returns {Promise<Object>} - Invite validation result { exists, used, tokenId }
   */
  async validateInviteCode(spiralEngine, inviteCode) {
    console.log(`🔍 Проверяем invite code: ${inviteCode}...`);
    
    if (!inviteCode || typeof inviteCode !== 'string') {
      throw new Error('AccessControl: Invite code должен быть непустой строкой');
    }
    
    // 1. Проверяем что invite существует
    const inviteExists = await spiralEngine.inviteCodeExists(inviteCode);
    if (!inviteExists) {
      throw new Error(
        `AccessControl: Invite code "${inviteCode}" не существует в системе. ` +
        `Проверьте правильность кода или сгенерируйте новый (Action 777).`
      );
    }
    
    // 2. Получаем tokenId и проверяем что не использован
    const tokenId = await spiralEngine.inviteCodeToTokenId(inviteCode);
    const isUsed = await spiralEngine.isInviteUsed(tokenId);
    
    if (isUsed) {
      throw new Error(
        `AccessControl: Invite code "${inviteCode}" уже был использован для активации. ` +
        `Используйте другой invite code.`
      );
    }
    
    console.log(`✅ Invite code валиден (token ID: ${tokenId}, не использован)`);
    
    return {
      exists: true,
      used: false,
      tokenId: tokenId.toString()
    };
  }

  /**
   * Check user activation status
   * Simple helper for activation checks
   * 
   * @param {Object} spiralEngine - SpiralEngine contract instance
   * @param {string} userAddress - User address to check
   * @returns {Promise<boolean>} - true if user is activated
   */
  async checkActivationStatus(spiralEngine, userAddress) {
    console.log(`🔍 Проверяем статус активации: ${userAddress}...`);
    
    // Проверка zero address
    if (!userAddress || userAddress === ethers.ZeroAddress) {
      console.log(`⚠️ Zero address - не активирован`);
      return false;
    }
    
    const usedInvite = await spiralEngine.usedInviteByUser(userAddress);
    const isActivated = usedInvite > 0;
    
    if (isActivated) {
      console.log(`✅ Пользователь активирован (invite token ID: ${usedInvite})`);
    } else {
      console.log(`⚠️ Пользователь НЕ активирован`);
    }
    
    return isActivated;
  }

  /**
   * Grant SELLER_ROLE to activated user
   * Requires user to be activated first!
   * 
   * @param {Object} spiralEngine - SpiralEngine contract instance
   * @param {string} userAddress - User address to grant role
   * @throws {Error} If user is not activated or transaction fails
   * @returns {Promise<void>}
   */
  async grantSellerRole(spiralEngine, userAddress) {
    console.log(`🔑 Назначаем SELLER_ROLE для: ${userAddress}...`);
    
    // Проверка zero address
    if (!userAddress || userAddress === ethers.ZeroAddress) {
      throw new Error('AccessControl: User address не может быть zero address');
    }
    
    // Prerequisite: Проверяем что пользователь активирован
    const isActivated = await this.checkActivationStatus(spiralEngine, userAddress);
    if (!isActivated) {
      throw new Error(
        `AccessControl: Не могу назначить SELLER_ROLE для ${userAddress} - ` +
        `пользователь не активирован. Активируйте пользователя через activateUser() сначала.`
      );
    }
    
    // Grant role on-chain
    const signer = this.ethersUtils.getSigner();
    const spiralEngineWithSigner = spiralEngine.connect(signer);
    
    const SELLER_ROLE = await spiralEngine.SELLER_ROLE();
    console.log(`   SELLER_ROLE: ${SELLER_ROLE.slice(0, 10)}...`);
    
    const tx = await spiralEngineWithSigner.grantSellerRole(userAddress);
    await tx.wait();
    
    console.log(`✅ SELLER_ROLE назначена успешно`);
    console.log(`   Transaction: ${tx.hash}`);
    
    // Verify
    const hasRole = await spiralEngine.hasRole(SELLER_ROLE, userAddress);
    if (!hasRole) {
      throw new Error('AccessControl: SELLER_ROLE не была назначена (verification failed)');
    }
  }

  /**
   * Grant ACTIVATOR_ROLE to seller
   * Allows seller to activate their own invited users
   * 
   * @param {Object} spiralEngine - SpiralEngine contract instance
   * @param {string} userAddress - User address to grant role
   * @throws {Error} If transaction fails
   * @returns {Promise<void>}
   */
  async grantActivatorRole(spiralEngine, userAddress) {
    console.log(`🔑 Назначаем ACTIVATOR_ROLE для: ${userAddress}...`);
    
    // Проверка zero address
    if (!userAddress || userAddress === ethers.ZeroAddress) {
      throw new Error('AccessControl: User address не может быть zero address');
    }
    
    const signer = this.ethersUtils.getSigner();
    const spiralEngineWithSigner = spiralEngine.connect(signer);
    
    const ACTIVATOR_ROLE = await spiralEngine.ACTIVATOR_ROLE();
    console.log(`   ACTIVATOR_ROLE: ${ACTIVATOR_ROLE.slice(0, 10)}...`);
    
    const tx = await spiralEngineWithSigner.grantRole(ACTIVATOR_ROLE, userAddress);
    await tx.wait();
    
    console.log(`✅ ACTIVATOR_ROLE назначена успешно`);
    console.log(`   Transaction: ${tx.hash}`);
    
    // Verify
    const hasRole = await spiralEngine.hasRole(ACTIVATOR_ROLE, userAddress);
    if (!hasRole) {
      throw new Error('AccessControl: ACTIVATOR_ROLE не была назначена (verification failed)');
    }
  }

  /**
   * Get complete user diagnostics
   * Useful for debugging and system monitoring
   * 
   * @param {Object} spiralEngine - SpiralEngine contract instance
   * @param {string} userAddress - User address to diagnose
   * @returns {Promise<Object>} - Complete user diagnostics
   */
  async getUserDiagnostics(spiralEngine, userAddress) {
    console.log(`\n🔍 Диагностика пользователя: ${userAddress}`);
    console.log("=".repeat(60));
    
    // Проверка zero address
    if (!userAddress || userAddress === ethers.ZeroAddress) {
      return {
        address: userAddress,
        valid: false,
        error: 'Zero address'
      };
    }
    
    try {
      // 1. Activation status
      const usedInvite = await spiralEngine.usedInviteByUser(userAddress);
      const isActivated = usedInvite > 0;
      
      // 2. Roles
      const SELLER_ROLE = await spiralEngine.SELLER_ROLE();
      const ACTIVATOR_ROLE = await spiralEngine.ACTIVATOR_ROLE();
      const hasSellerRole = await spiralEngine.hasRole(SELLER_ROLE, userAddress);
      const hasActivatorRole = await spiralEngine.hasRole(ACTIVATOR_ROLE, userAddress);
      
      // 3. Activator info (если активирован)
      let activatorAddress = ethers.ZeroAddress;
      if (isActivated) {
        activatorAddress = await spiralEngine.userActivator(userAddress);
      }
      
      // 4. Invites created by this user
      // Note: Контракт не хранит счетчик напрямую, только через mapping
      // Для production можно добавить event-based counting
      
      const diagnostics = {
        address: userAddress,
        valid: true,
        activation: {
          activated: isActivated,
          usedInviteTokenId: usedInvite.toString(),
          activatedBy: activatorAddress
        },
        roles: {
          SELLER_ROLE: hasSellerRole,
          ACTIVATOR_ROLE: hasActivatorRole
        },
        roleIds: {
          SELLER_ROLE: SELLER_ROLE,
          ACTIVATOR_ROLE: ACTIVATOR_ROLE
        }
      };
      
      // Pretty print
      console.log(`📋 Статус активации:`);
      console.log(`   Активирован: ${diagnostics.activation.activated ? '✅ Да' : '❌ Нет'}`);
      if (diagnostics.activation.activated) {
        console.log(`   Использованный invite: Token ID ${diagnostics.activation.usedInviteTokenId}`);
        console.log(`   Активирован кем: ${diagnostics.activation.activatedBy}`);
      }
      
      console.log(`\n🔑 Роли:`);
      console.log(`   SELLER_ROLE: ${diagnostics.roles.SELLER_ROLE ? '✅ Есть' : '❌ Нет'}`);
      console.log(`   ACTIVATOR_ROLE: ${diagnostics.roles.ACTIVATOR_ROLE ? '✅ Есть' : '❌ Нет'}`);
      
      console.log("=".repeat(60));
      
      return diagnostics;
      
    } catch (error) {
      console.error(`❌ Ошибка диагностики: ${error.message}`);
      return {
        address: userAddress,
        valid: false,
        error: error.message
      };
    }
  }
  
  // ================================================================
  // STANDALONE ACTIONS
  // ================================================================
  
  /**
   * Action 13: Diagnose Seller State
   * Comprehensive seller diagnostics including catalog info
   * 
   * @returns {Promise<Object>} - Full diagnostics result
   */
  async action13() {
    logger.action(13, "Diagnose seller state");
    
    try {
      // 1. Get seller address from config
      const sellerAddress = this.config.get('seller.address');
      if (!sellerAddress) {
        throw new Error('SELLER_ADDRESS not configured');
      }
      
      logger.info(`Seller address: ${sellerAddress}`);
      logger.info("=".repeat(60));
      
      // 2. Load contracts
      logger.info('Loading contracts...');
      const spiralEngine = await this.contractManager.loadUUPSContract('SpiralEngine');
      const productRegistry = await this.contractManager.loadUUPSContract('ProductRegistry');
      logger.info('Contracts loaded ✓');
      
      // 3. Get base diagnostics (activation + roles)
      const baseDiagnostics = await this.getUserDiagnostics(spiralEngine, sellerAddress);
      
      if (!baseDiagnostics.valid || !baseDiagnostics.activation.activated) {
        logger.warn('Seller not activated - skipping catalog check');
        return {
          success: true,
          diagnostics: baseDiagnostics,
          readinessScore: 0,
          readinessPercent: 0
        };
      }
      
      // 4. Get catalog info (requires seller to have SELLER_ROLE)
      let catalogInfo = null;
      try {
        logger.info('\n📦 Checking product catalog...');
        
        const products = await productRegistry.getProductsBySeller(sellerAddress);
        logger.info(`Total products: ${products.length}`);
        
        let activeCount = 0;
        if (products.length > 0 && baseDiagnostics.roles.SELLER_ROLE) {
          // Get active products from contract
          const allActiveIds = await productRegistry.getAllActiveProductIds();
          activeCount = products.filter(id => allActiveIds.includes(id)).length;
        }
        
        catalogInfo = {
          totalProducts: products.length,
          activeProducts: activeCount,
          inactiveProducts: products.length - activeCount,
          hasCatalog: products.length > 0
        };
        
        logger.info(`Active products: ${activeCount}`);
        logger.info(`Inactive products: ${catalogInfo.inactiveProducts}`);
        
      } catch (error) {
        logger.warn(`Could not get catalog info: ${error.message}`);
        catalogInfo = {
          totalProducts: 0,
          activeProducts: 0,
          inactiveProducts: 0,
          hasCatalog: false,
          error: error.message
        };
      }
      
      // 5. Calculate readiness score (0-5)
      const readinessChecks = {
        activated: baseDiagnostics.activation.activated,
        hasSellerRole: baseDiagnostics.roles.SELLER_ROLE,
        hasActivatorRole: baseDiagnostics.roles.ACTIVATOR_ROLE,
        hasCatalog: catalogInfo.hasCatalog,
        hasActiveProducts: catalogInfo.activeProducts > 0
      };
      
      const readinessScore = Object.values(readinessChecks).filter(Boolean).length;
      const readinessPercent = Math.round((readinessScore / 5) * 100);
      
      // 6. Pretty print summary
      logger.info('\n🎯 Readiness Summary:');
      logger.info(`   Activated: ${readinessChecks.activated ? '✅' : '❌'}`);
      logger.info(`   SELLER_ROLE: ${readinessChecks.hasSellerRole ? '✅' : '❌'}`);
      logger.info(`   ACTIVATOR_ROLE: ${readinessChecks.hasActivatorRole ? '✅' : '❌'}`);
      logger.info(`   Has Catalog: ${readinessChecks.hasCatalog ? '✅' : '❌'}`);
      logger.info(`   Has Active Products: ${readinessChecks.hasActiveProducts ? '✅' : '❌'}`);
      logger.info(`\n📊 Readiness Score: ${readinessScore}/5 (${readinessPercent}%)`);
      
      if (readinessScore === 5) {
        logger.success('🎉 Seller fully ready!');
      } else if (readinessScore >= 3) {
        logger.warn('⚠️ Seller partially ready');
      } else {
        logger.error('❌ Seller not ready');
      }
      
      logger.info("=".repeat(60));
      logger.success(13);
      
      return {
        success: true,
        diagnostics: {
          ...baseDiagnostics,
          catalog: catalogInfo
        },
        readinessChecks: readinessChecks,
        readinessScore: readinessScore,
        readinessPercent: readinessPercent
      };
    } catch (error) {
      logger.failure(13, error.message);
      throw error;
    }
  }
  
  /**
   * Action 9: Grant ACTIVATOR_ROLE to Seller
   * Standalone action for granting ACTIVATOR_ROLE to a seller from config
   * 
   * @returns {Promise<Object>} - Grant result
   */
  async action9() {
    logger.action(9, "Grant ACTIVATOR_ROLE to seller");
    
    try {
      // 1. Get seller address from config
      const sellerAddress = this.config.get('seller.address');
      if (!sellerAddress) {
        throw new Error('SELLER_ADDRESS not configured');
      }
      
      logger.info(`Seller address: ${sellerAddress}`);
      
      // 2. Load SpiralEngine contract
      logger.info('Loading SpiralEngine contract...');
      const spiralEngine = await this.contractManager.loadUUPSContract('SpiralEngine');
      logger.info('Contract loaded ✓');
      
      // 3. Optional: Check seller activation status (warning only)
      try {
        const usedInvite = await spiralEngine.usedInviteByUser(sellerAddress);
        if (usedInvite === 0 || usedInvite === 0n) {
          logger.warn(`⚠️ Seller ${sellerAddress} not activated yet (will continue anyway)`);
        } else {
          logger.info(`Seller activated ✓ (used invite: ${usedInvite})`);
        }
      } catch (error) {
        logger.warn(`Could not check activation status: ${error.message}`);
      }
      
      // 4. Delegate to grantActivatorRole helper
      await this.grantActivatorRole(spiralEngine, sellerAddress);
      
      logger.success(9);
      return {
        success: true,
        sellerAddress: sellerAddress,
        roleGranted: 'ACTIVATOR_ROLE'
      };
    } catch (error) {
      logger.failure(9, error.message);
      throw error;
    }
  }
  /**
   * Setup SoulIdentity Integration (Generic SBT System)
   * Creates SBT token, initializes metadata, links DID for any user type
   * 
   * @param {string} userAddress - User address (seller, buyer, admin, etc.)
   * @param {Object} options - Configuration options
   * @param {string} options.userType - User type (default: 'seller')
   * @param {number} options.level - Initial level (default: 1)
   * @param {number} options.reputation - Initial reputation (default: 100)
   * @returns {Promise<Object>} - SBT integration result
   */
  async setupSoulIdentity(userAddress, options = {}) {
    const userType = options.userType || 'seller';
    const level = options.level || 1;
    const reputation = options.reputation || 100;
    
    logger.info(`Setting up SoulIdentity for ${userAddress} (type: ${userType})...`);
    
    try {
      // 1. Load SoulIdentity contract
      let soulIdentity;
      try {
        soulIdentity = await this.contractManager.loadContract('SoulIdentity');
        logger.info(`SoulIdentity: ${await soulIdentity.getAddress()}`);
      } catch (error) {
        logger.warn('SoulIdentity not deployed - skipping SBT integration');
        return { 
          skipped: true, 
          reason: 'SoulIdentity not deployed',
          userAddress: userAddress
        };
      }
      
      // 2. Load SBT ecosystem contracts
      const soulboundCore = await this.contractManager.loadContract('SoulboundCore');
      const soulMetadata = await this.contractManager.loadContract('SoulMetadata');
      
      logger.info(`SoulboundCore: ${await soulboundCore.getAddress()}`);
      logger.info(`SoulMetadata: ${await soulMetadata.getAddress()}`);
      
      // 3. Check if user already has SBT token
      const balance = await soulboundCore.balanceOf(userAddress);
      logger.info(`User SBT balance: ${balance}`);
      
      let tokenId;
      
      if (balance === 0n) {
        // 3.1. Create new SBT token
        logger.info('Creating SBT token for user...');
        
        const deploySigner = this.ethersUtils.getSigner();
        const soulboundCoreWithSigner = soulboundCore.connect(deploySigner);
        
        const mintTx = await soulboundCoreWithSigner.mintSoul(userAddress);
        const receipt = await mintTx.wait();
        
        logger.success(`SBT token created (tx: ${receipt.hash})`);
        
        // 3.2. Get tokenId (just minted)
        const nextTokenId = await soulboundCore.getNextTokenId();
        tokenId = nextTokenId - 1n;
        
        logger.info(`Token ID: ${tokenId}`);
        
        // 3.3. Initialize metadata
        logger.info('Initializing metadata...');
        
        // Get user private key for metadata initialization (owner must initialize)
        const userPrivateKey = this.config.get('seller.privateKey') || 
                               this.config.get('user.privateKey');
        
        if (!userPrivateKey) {
          logger.warn('User private key not found - cannot initialize metadata');
          logger.warn('SBT token created but metadata not initialized');
          return {
            success: true,
            tokenId: tokenId.toString(),
            metadataWarning: 'Not initialized - user private key required'
          };
        }
        
        const userSigner = this.ethersUtils.getSigner(userPrivateKey);
        const soulMetadataWithSigner = soulMetadata.connect(userSigner);
        
        const metadataJson = JSON.stringify({
          type: userType,
          level: level,
          reputation: reputation,
          created: Date.now()
        });
        
        const initTx = await soulMetadataWithSigner.initializeMetadata(
          tokenId,
          userType,
          metadataJson,
          "" // IPFS hash empty for now
        );
        await initTx.wait();
        
        logger.success('Metadata initialized ✓');
        
      } else {
        // 3.4. Find existing SBT tokenId
        logger.info('Finding existing SBT tokenId...');
        
        const totalSupply = await soulboundCore.getTotalSupply();
        logger.info(`Total SBT supply: ${totalSupply}`);
        
        let found = false;
        for (let i = 1n; i <= totalSupply && i <= 1000n; i++) {
          try {
            const owner = await soulboundCore.ownerOf(i);
            if (owner.toLowerCase() === userAddress.toLowerCase()) {
              tokenId = i;
              found = true;
              break;
            }
          } catch (error) {
            // Token doesn't exist or error - continue search
            continue;
          }
        }
        
        if (!found) {
          throw new Error(`Could not find existing SBT token for user ${userAddress}`);
        }
        
        logger.success(`Found existing SBT token: ${tokenId}`);
      }
      
      // 4. Link DID via SoulIdentity
      logger.info('Linking DID...');
      
      const soulDID = `did:spiral:${userAddress.toLowerCase()}`;
      
      const deploySigner = this.ethersUtils.getSigner();
      const soulIdentityWithSigner = soulIdentity.connect(deploySigner);
      
      try {
        const linkTx = await soulIdentityWithSigner.linkExternalIdentity(
          userAddress,
          "did:spiral",
          soulDID,
          false // not verified (legacy compatibility)
        );
        await linkTx.wait();
        
        logger.success(`DID linked: ${soulDID}`);
      } catch (error) {
        // DID may already be linked - check if it's just duplicate
        if (error.message.includes('already') || error.message.includes('exists')) {
          logger.warn(`DID may already be linked: ${error.message}`);
        } else {
          throw error;
        }
      }
      
      // 5. Validate integration (optional - non-fatal if fails)
      logger.info('Validating SBT integration...');
      
      let validationResult = {};
      try {
        const primaryIdentity = await soulIdentity.getPrimaryIdentity(userAddress);
        const soulLevel = await soulIdentity.getSoulLevel(userAddress);
        const soulReputation = await soulIdentity.getSoulReputation(userAddress);
        
        logger.success(`Primary identity: ${primaryIdentity.identityType} = ${primaryIdentity.identityValue}`);
        logger.success(`Soul level: ${soulLevel}`);
        logger.success(`Soul reputation: ${soulReputation}`);
        
        validationResult = {
          primaryIdentity: {
            type: primaryIdentity.identityType,
            value: primaryIdentity.identityValue
          },
          level: soulLevel.toString(),
          reputation: soulReputation.toString()
        };
      } catch (error) {
        logger.warn(`Validation partially failed: ${error.message}`);
        validationResult = {
          validationWarning: error.message
        };
      }
      
      // 6. Return comprehensive result
      return {
        success: true,
        userAddress: userAddress,
        tokenId: tokenId.toString(),
        did: soulDID,
        userType: userType,
        ...validationResult
      };
      
    } catch (error) {
      logger.error(`SBT setup failed: ${error.message}`);
      throw error;
    }
  }
}

module.exports = AccessControlActions;

