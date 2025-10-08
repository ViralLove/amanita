const { expect } = require("chai");
const { ethers } = require("hardhat");

/**
 * 🧪 ProductRegistry UUPS - Comprehensive Tests
 * 
 * Цель: Полное покрытие P0 + P1 UUPS функционала
 * 
 * Проверяемые элементы:
 * - P0: Full State Preservation при upgrade (КРИТИЧНО!)
 * - P1: whenNotPaused модификатор на всех функциях
 * 
 * Базируется на: OrganicComponentRegistry.UUPS.test.js (эталон)
 */

describe("🔥 ProductRegistry UUPS - Comprehensive Tests", function () {
    let admin, seller, otherSeller, user1;
    let proxy, logic, productRegistry;
    let spiralEngine;
    let SELLER_ROLE;

    beforeEach(async function () {
        [admin, seller, otherSeller, user1] = await ethers.getSigners();
        
        console.log("\n🔥 Comprehensive Test Setup Starting...");
        
        // ===== Deploy Mock SpiralEngine =====
        console.log("🔷 Deploying Mock SpiralEngine...");
        const SpiralEngineMock = await ethers.getContractFactory("contracts/mocks/MockSpiralEngine.sol:MockSpiralEngine");
        spiralEngine = await SpiralEngineMock.deploy();
        await spiralEngine.waitForDeployment();
        console.log(`   ✅ Mock SpiralEngine deployed: ${await spiralEngine.getAddress()}`);
        
        // ===== Deploy ProductRegistry UUPS =====
        console.log("🔷 Deploying ProductRegistry UUPS...");
        
        // 1. Deploy Logic implementation
        const Logic = await ethers.getContractFactory("ProductRegistryLogic");
        logic = await Logic.deploy();
        await logic.waitForDeployment();
        console.log(`   ✅ Logic deployed: ${await logic.getAddress()}`);
        
        // 2. Encode initialize(admin, spiralEngine) calldata
        const initCalldata = logic.interface.encodeFunctionData("initialize", [
            admin.address,
            await spiralEngine.getAddress()
        ]);
        
        // 3. Deploy Proxy with implementation and init data
        const Proxy = await ethers.getContractFactory("ProductRegistryProxy");
        proxy = await Proxy.deploy(await logic.getAddress(), initCalldata);
        await proxy.waitForDeployment();
        console.log(`   ✅ Proxy deployed: ${await proxy.getAddress()}`);
        
        // 4. Attach Logic ABI to proxy address
        productRegistry = Logic.attach(await proxy.getAddress());
        
        // ===== Setup mock SpiralEngine для sellers =====
        SELLER_ROLE = await spiralEngine.SELLER_ROLE();
        
        // Активируем seller в моке
        await spiralEngine.setUserActivated(seller.address, true);
        await spiralEngine.grantRole(SELLER_ROLE, seller.address);
        
        // Активируем otherSeller в моке
        await spiralEngine.setUserActivated(otherSeller.address, true);
        await spiralEngine.grantRole(SELLER_ROLE, otherSeller.address);
        
        console.log("   ✅ Sellers configured in mock");
        console.log("   ✅ Comprehensive Test Setup Complete");
    });

    // ==========================================
    // TEST SUITE 1: Full State Preservation (P0)
    // ==========================================
    describe("💾 Full State Preservation - P0 CRITICAL", function () {
        it("Should preserve ALL storage variables during upgrade", async function () {
            console.log("   🔍 Testing COMPLETE state preservation...");
            
            // ===== PHASE 1: Создание тестовых данных =====
            console.log("   📝 PHASE 1: Creating test data...");
            
            // Создаём 3 продукта от seller
            await productRegistry.connect(seller).createProduct("QmProduct1");
            await productRegistry.connect(seller).createProduct("QmProduct2");
            await productRegistry.connect(seller).createProduct("QmProduct3");
            console.log("   ✅ Created 3 products from seller");
            
            // Активируем продукты 1 и 3 (2 остаётся неактивным)
            await productRegistry.connect(seller).activateProduct(1);
            await productRegistry.connect(seller).activateProduct(3);
            console.log("   ✅ Activated products 1 and 3");
            
            // Создаём 2 продукта от otherSeller
            await productRegistry.connect(otherSeller).createProduct("QmOtherProduct1");
            await productRegistry.connect(otherSeller).createProduct("QmOtherProduct2");
            await productRegistry.connect(otherSeller).activateProduct(4);
            console.log("   ✅ Created 2 products from otherSeller, activated product 4");
            
            // ===== PHASE 2: Сохранение состояния ДО upgrade =====
            console.log("   💾 PHASE 2: Saving state before upgrade...");
            
            // Примечание: _productIdCounter - приватная переменная, нет публичного getter
            // Проверяем состояние через публичные функции
            
            // Products mapping (через getProduct)
            const product1Before = await productRegistry.getProduct(1);
            const product2Before = await productRegistry.getProduct(2);
            const product3Before = await productRegistry.getProduct(3);
            const product4Before = await productRegistry.getProduct(4);
            const product5Before = await productRegistry.getProduct(5);
            console.log("   ✅ Saved 5 products state");
            
            // activeProductIds array
            const activeProductIdsBefore = await productRegistry.getAllActiveProductIds();
            console.log(`   📊 activeProductIds: [${activeProductIdsBefore.map(id => id.toString()).join(", ")}]`);
            
            // sellerProducts mapping
            const sellerProductsBefore = await productRegistry.getProductsBySeller(seller.address);
            const otherSellerProductsBefore = await productRegistry.getProductsBySeller(otherSeller.address);
            console.log(`   📊 seller products: [${sellerProductsBefore.map(id => id.toString()).join(", ")}]`);
            console.log(`   📊 otherSeller products: [${otherSellerProductsBefore.map(id => id.toString()).join(", ")}]`);
            
            // catalogVersion mapping
            const sellerVersionBefore = await productRegistry.connect(seller).getMyCatalogVersion();
            const otherSellerVersionBefore = await productRegistry.connect(otherSeller).getMyCatalogVersion();
            console.log(`   📊 seller catalogVersion: ${sellerVersionBefore}`);
            console.log(`   📊 otherSeller catalogVersion: ${otherSellerVersionBefore}`);
            
            // ===== PHASE 3: Выполнение UUPS Upgrade =====
            console.log("   🔄 PHASE 3: Performing UUPS upgrade...");
            
            const LogicV2 = await ethers.getContractFactory("ProductRegistryLogic");
            const logicV2 = await LogicV2.deploy();
            await logicV2.waitForDeployment();
            console.log(`   ✅ LogicV2 deployed: ${await logicV2.getAddress()}`);
            
            await productRegistry.connect(admin).upgradeToAndCall(
                await logicV2.getAddress(),
                "0x"
            );
            console.log("   ✅ Upgrade completed");
            
            // ===== PHASE 4: Проверка состояния ПОСЛЕ upgrade =====
            console.log("   🔍 PHASE 4: Validating state after upgrade...");
            
            // 4.2 Products mapping - проверяем ВСЕ поля
            const product1After = await productRegistry.getProduct(1);
            expect(product1After.id).to.equal(product1Before.id);
            expect(product1After.seller).to.equal(product1Before.seller);
            expect(product1After.ipfsCID).to.equal(product1Before.ipfsCID);
            expect(product1After.active).to.equal(product1Before.active);
            expect(product1After.timestamp).to.equal(product1Before.timestamp);
            console.log("   ✅ Product 1 fully preserved (all 5 fields)");
            
            const product2After = await productRegistry.getProduct(2);
            expect(product2After.id).to.equal(product2Before.id);
            expect(product2After.seller).to.equal(product2Before.seller);
            expect(product2After.active).to.equal(product2Before.active); // false (неактивный)
            console.log("   ✅ Product 2 fully preserved (inactive)");
            
            const product3After = await productRegistry.getProduct(3);
            expect(product3After.id).to.equal(product3Before.id);
            expect(product3After.seller).to.equal(product3Before.seller);
            expect(product3After.active).to.equal(product3Before.active); // true (активный)
            console.log("   ✅ Product 3 fully preserved (active)");
            
            const product4After = await productRegistry.getProduct(4);
            expect(product4After.seller).to.equal(product4Before.seller);
            expect(product4After.ipfsCID).to.equal(product4Before.ipfsCID);
            expect(product4After.active).to.equal(product4Before.active); // true
            console.log("   ✅ Product 4 fully preserved (otherSeller)");
            
            const product5After = await productRegistry.getProduct(5);
            expect(product5After.seller).to.equal(product5Before.seller);
            expect(product5After.ipfsCID).to.equal(product5Before.ipfsCID);
            expect(product5After.active).to.equal(product5Before.active); // false
            console.log("   ✅ Product 5 fully preserved (otherSeller, inactive)");
            
            // 4.3 activeProductIds array
            const activeProductIdsAfter = await productRegistry.getAllActiveProductIds();
            expect(activeProductIdsAfter.length).to.equal(activeProductIdsBefore.length);
            expect(activeProductIdsAfter.length).to.equal(3); // Продукты 1, 3, 4
            
            // Проверяем каждый элемент массива
            for (let i = 0; i < activeProductIdsAfter.length; i++) {
                expect(activeProductIdsAfter[i]).to.equal(activeProductIdsBefore[i]);
            }
            console.log(`   ✅ activeProductIds array preserved: [${activeProductIdsAfter.map(id => id.toString()).join(", ")}]`);
            
            // 4.4 sellerProducts mapping
            const sellerProductsAfter = await productRegistry.getProductsBySeller(seller.address);
            expect(sellerProductsAfter.length).to.equal(sellerProductsBefore.length);
            expect(sellerProductsAfter.length).to.equal(3); // Продукты 1, 2, 3
            
            for (let i = 0; i < sellerProductsAfter.length; i++) {
                expect(sellerProductsAfter[i]).to.equal(sellerProductsBefore[i]);
            }
            console.log(`   ✅ seller sellerProducts mapping preserved: [${sellerProductsAfter.map(id => id.toString()).join(", ")}]`);
            
            const otherSellerProductsAfter = await productRegistry.getProductsBySeller(otherSeller.address);
            expect(otherSellerProductsAfter.length).to.equal(otherSellerProductsBefore.length);
            expect(otherSellerProductsAfter.length).to.equal(2); // Продукты 4, 5
            
            for (let i = 0; i < otherSellerProductsAfter.length; i++) {
                expect(otherSellerProductsAfter[i]).to.equal(otherSellerProductsBefore[i]);
            }
            console.log(`   ✅ otherSeller sellerProducts mapping preserved: [${otherSellerProductsAfter.map(id => id.toString()).join(", ")}]`);
            
            // 4.5 catalogVersion mapping
            const sellerVersionAfter = await productRegistry.connect(seller).getMyCatalogVersion();
            expect(sellerVersionAfter).to.equal(sellerVersionBefore);
            console.log(`   ✅ seller catalogVersion preserved: ${sellerVersionAfter}`);
            
            const otherSellerVersionAfter = await productRegistry.connect(otherSeller).getMyCatalogVersion();
            expect(otherSellerVersionAfter).to.equal(otherSellerVersionBefore);
            console.log(`   ✅ otherSeller catalogVersion preserved: ${otherSellerVersionAfter}`);
            
            // ===== PHASE 5: Проверка функциональности ПОСЛЕ upgrade =====
            console.log("   🔧 PHASE 5: Testing functionality after upgrade...");
            
            // Создание нового продукта (должен получить ID = 6)
            await productRegistry.connect(seller).createProduct("QmPostUpgrade");
            const newProduct = await productRegistry.getProduct(6);
            expect(newProduct.id).to.equal(6);
            expect(newProduct.ipfsCID).to.equal("QmPostUpgrade");
            expect(newProduct.seller).to.equal(seller.address);
            console.log("   ✅ New product creation works after upgrade (ID = 6)");
            
            // Активация нового продукта
            await productRegistry.connect(seller).activateProduct(6);
            const activeIdsAfterNew = await productRegistry.getAllActiveProductIds();
            expect(activeIdsAfterNew.length).to.equal(activeProductIdsBefore.length + 1);
            expect(activeIdsAfterNew.length).to.equal(4); // 1, 3, 4, 6
            console.log("   ✅ Product activation works after upgrade");
            
            // Обновление продукта
            await productRegistry.connect(seller).updateProduct(6, "QmUpdated", 100);
            const updatedProduct = await productRegistry.getProduct(6);
            expect(updatedProduct.ipfsCID).to.equal("QmUpdated");
            console.log("   ✅ Product update works after upgrade");
            
            console.log("   🎉 FULL STATE PRESERVATION TEST PASSED");
        });
    });

    // ==========================================
    // TEST SUITE 2: Pausable Protection (P1)
    // ==========================================
    describe("⏸️ Pausable Protection - Comprehensive", function () {
        beforeEach(async function () {
            // Создаём базовые данные для тестов паузы
            await productRegistry.connect(seller).createProduct("QmPauseTest");
            await productRegistry.connect(seller).activateProduct(1);
            console.log("   ✅ Base product created and activated for Pausable tests");
        });

        it("Should block createProduct when paused", async function () {
            console.log("   🔍 Testing createProduct pause protection...");
            
            // Пауза
            await productRegistry.connect(admin).pause();
            console.log("   ⏸️  Contract paused");
            
            // Попытка создать продукт должна провалиться
            await expect(
                productRegistry.connect(seller).createProduct("QmPaused")
            ).to.be.revertedWithCustomError(productRegistry, "EnforcedPause");
            console.log("   ✅ createProduct blocked during pause");
            
            // Снятие паузы
            await productRegistry.connect(admin).unpause();
            console.log("   ▶️  Contract unpaused");
            
            // Теперь должно работать
            await productRegistry.connect(seller).createProduct("QmPaused");
            const newProduct = await productRegistry.getProduct(2);
            expect(newProduct.id).to.equal(2);
            expect(newProduct.ipfsCID).to.equal("QmPaused");
            console.log("   ✅ createProduct works after unpause");
        });

        it("Should block activateProduct when paused", async function () {
            console.log("   🔍 Testing activateProduct pause protection...");
            
            // Создаём продукт ДО паузы
            await productRegistry.connect(seller).createProduct("QmPauseActivate");
            console.log("   ✅ Product created before pause");
            
            // Пауза
            await productRegistry.connect(admin).pause();
            console.log("   ⏸️  Contract paused");
            
            // Попытка активировать должна провалиться
            await expect(
                productRegistry.connect(seller).activateProduct(2)
            ).to.be.revertedWithCustomError(productRegistry, "EnforcedPause");
            console.log("   ✅ activateProduct blocked during pause");
            
            // Снятие паузы
            await productRegistry.connect(admin).unpause();
            console.log("   ▶️  Contract unpaused");
            
            // Теперь должно работать
            await productRegistry.connect(seller).activateProduct(2);
            const product = await productRegistry.getProduct(2);
            expect(product.active).to.be.true;
            console.log("   ✅ activateProduct works after unpause");
        });

        it("Should block deactivateProduct when paused", async function () {
            console.log("   🔍 Testing deactivateProduct pause protection...");
            
            // Пауза
            await productRegistry.connect(admin).pause();
            console.log("   ⏸️  Contract paused");
            
            // Попытка деактивировать должна провалиться
            await expect(
                productRegistry.connect(seller).deactivateProduct(1)
            ).to.be.revertedWithCustomError(productRegistry, "EnforcedPause");
            console.log("   ✅ deactivateProduct blocked during pause");
            
            // Снятие паузы
            await productRegistry.connect(admin).unpause();
            console.log("   ▶️  Contract unpaused");
            
            // Теперь должно работать
            await productRegistry.connect(seller).deactivateProduct(1);
            const product = await productRegistry.getProduct(1);
            expect(product.active).to.be.false;
            console.log("   ✅ deactivateProduct works after unpause");
        });

        it("Should block updateProduct when paused", async function () {
            console.log("   🔍 Testing updateProduct pause protection...");
            
            // Пауза
            await productRegistry.connect(admin).pause();
            console.log("   ⏸️  Contract paused");
            
            // Попытка обновить должна провалиться
            await expect(
                productRegistry.connect(seller).updateProduct(1, "QmUpdated", 100)
            ).to.be.revertedWithCustomError(productRegistry, "EnforcedPause");
            console.log("   ✅ updateProduct blocked during pause");
            
            // Снятие паузы
            await productRegistry.connect(admin).unpause();
            console.log("   ▶️  Contract unpaused");
            
            // Теперь должно работать
            await productRegistry.connect(seller).updateProduct(1, "QmUpdated", 100);
            const product = await productRegistry.getProduct(1);
            expect(product.ipfsCID).to.equal("QmUpdated");
            console.log("   ✅ updateProduct works after unpause");
        });

        it("Should block clearSellerCatalog when paused", async function () {
            console.log("   🔍 Testing clearSellerCatalog pause protection...");
            
            // Пауза
            await productRegistry.connect(admin).pause();
            console.log("   ⏸️  Contract paused");
            
            // Попытка очистить каталог должна провалиться
            await expect(
                productRegistry.connect(seller).clearSellerCatalog(seller.address)
            ).to.be.revertedWithCustomError(productRegistry, "EnforcedPause");
            console.log("   ✅ clearSellerCatalog blocked during pause");
            
            // Снятие паузы
            await productRegistry.connect(admin).unpause();
            console.log("   ▶️  Contract unpaused");
            
            // Теперь должно работать
            await productRegistry.connect(seller).clearSellerCatalog(seller.address);
            const products = await productRegistry.getProductsBySeller(seller.address);
            expect(products.length).to.equal(0);
            console.log("   ✅ clearSellerCatalog works after unpause");
        });
    });
});

