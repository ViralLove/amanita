const chai = require("chai");
const { expect } = chai;
const { ethers } = require("hardhat");

async function expectRevertCustom(txPromise, errorName, contract) {
    try {
        await txPromise;
        expect.fail(`Ожидался custom error ${errorName}, но транзакция прошла успешно`);
    } catch (error) {
        if (error && error.errorName) {
            expect(error.errorName).to.equal(errorName);
            return;
        }
        const message = (error?.message || "").toLowerCase();
        if (contract && message.includes("return data:")) {
            const match = message.match(/return data:\s*(0x[0-9a-f]+)/);
            if (match) {
                const selector = contract.interface.getError(errorName).selector.toLowerCase();
                if (match[1].startsWith(selector)) {
                    return;
                }
            }
        }
        expect(message).to.include(errorName.toLowerCase(), `Ожидался custom error ${errorName}, получено: ${error?.message || error}`);
    }
}

async function expectRevertReason(txPromise, reasonSubstring) {
    try {
        await txPromise;
        expect.fail(`Ожидался revert с сообщением "${reasonSubstring}", но транзакция прошла успешно`);
    } catch (error) {
        const message = error?.message || "";
        expect(message).to.include(reasonSubstring, `Ожидался revert с "${reasonSubstring}", получено: ${message}`);
    }
}

async function expectNotReverted(txPromise, failureMessage = "Транзакция не должна была ревертиться") {
    try {
        await txPromise;
    } catch (error) {
        expect.fail(`${failureMessage}: ${error?.message || error}`);
    }
}

async function expectEvent(txPromise, contract, eventName, assertFn) {
    const tx = await txPromise;
    const receipt = await tx.wait();
    const parsedEvent = receipt.logs
        .map(log => {
            try {
                return contract.interface.parseLog(log);
            } catch (_) {
                return null;
            }
        })
        .find(event => event && event.name === eventName);

    expect(parsedEvent, `Событие ${eventName} не найдено`).to.exist;

    if (assertFn) {
        await assertFn(parsedEvent.args);
    }

    return parsedEvent;
}

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
    let componentRegistry;
    let SELLER_ROLE;
    let sellerComponentIds;
    let otherSellerComponentIds;

    beforeEach(async function () {
        [admin, seller, otherSeller, user1] = await ethers.getSigners();
        
        console.log("\n🔥 Comprehensive Test Setup Starting...");
        
        // ===== Deploy Mock SpiralEngine =====
        console.log("🔷 Deploying Mock SpiralEngine...");
        const SpiralEngineMock = await ethers.getContractFactory("contracts/mocks/MockSpiralEngine.sol:MockSpiralEngine");
        spiralEngine = await SpiralEngineMock.deploy();
        await spiralEngine.waitForDeployment();
        console.log(`   ✅ Mock SpiralEngine deployed: ${await spiralEngine.getAddress()}`);

        // ===== Deploy OrganicComponentRegistry UUPS =====
        console.log("🔷 Deploying OrganicComponentRegistry UUPS...");
        const OCRLogic = await ethers.getContractFactory("OrganicComponentRegistryLogic");
        const ocrLogic = await OCRLogic.deploy();
        await ocrLogic.waitForDeployment();
        console.log(`   ✅ OCR Logic deployed: ${await ocrLogic.getAddress()}`);

        const ocrInitCalldata = ocrLogic.interface.encodeFunctionData("initialize", [admin.address]);
        const OCRProxy = await ethers.getContractFactory("OrganicComponentRegistryProxy");
        const ocrProxy = await OCRProxy.deploy(await ocrLogic.getAddress(), ocrInitCalldata);
        await ocrProxy.waitForDeployment();
        console.log(`   ✅ OCR Proxy deployed: ${await ocrProxy.getAddress()}`);

        componentRegistry = ocrLogic.attach(await ocrProxy.getAddress());
        await componentRegistry.connect(admin).setSpiralEngine(await spiralEngine.getAddress());
        console.log("   ✅ OrganicComponentRegistry configured with SpiralEngine");

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

        // ===== Link registries =====
        await productRegistry.connect(admin).setOrganicComponentRegistry(await componentRegistry.getAddress());
        console.log("   ✅ ProductRegistry linked to OrganicComponentRegistry");

        // ===== Setup mock SpiralEngine для sellers =====
        SELLER_ROLE = await spiralEngine.SELLER_ROLE();

        // Активируем seller и otherSeller в моке
        await spiralEngine.setUserActivated(seller.address, true);
        await spiralEngine.grantRole(SELLER_ROLE, seller.address);
        await spiralEngine.setUserActivated(otherSeller.address, true);
        await spiralEngine.grantRole(SELLER_ROLE, otherSeller.address);

        console.log("   ✅ Sellers configured in mock SpiralEngine");

        // ===== Создаём компоненты для продавцов =====
        sellerComponentIds = ["seller-comp-1", "seller-comp-2", "seller-comp-3"];
        otherSellerComponentIds = ["other-seller-comp-1", "other-seller-comp-2"];

        for (const componentId of sellerComponentIds) {
            await componentRegistry.connect(seller).createComponent(componentId, `Qm${componentId}`);
        }

        for (const componentId of otherSellerComponentIds) {
            await componentRegistry.connect(otherSeller).createComponent(componentId, `Qm${componentId}`);
        }

        console.log("   ✅ Components created for sellers");
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
            await productRegistry.connect(seller).createProduct(
                "seller-product-1",
                [sellerComponentIds[0]],
                "QmProduct1"
            );
            await productRegistry.connect(seller).createProduct(
                "seller-product-2",
                [sellerComponentIds[1]],
                "QmProduct2"
            );
            await productRegistry.connect(seller).createProduct(
                "seller-product-3",
                [sellerComponentIds[2]],
                "QmProduct3"
            );
            console.log("   ✅ Created 3 products from seller");
            
            // Активируем продукты 1 и 3 (2 остаётся неактивным)
            await productRegistry.connect(seller).activateProduct(1);
            await productRegistry.connect(seller).activateProduct(3);
            console.log("   ✅ Activated products 1 and 3");
            
            // Создаём 2 продукта от otherSeller
            await productRegistry.connect(otherSeller).createProduct(
                "other-product-1",
                [otherSellerComponentIds[0]],
                "QmOtherProduct1"
            );
            await productRegistry.connect(otherSeller).createProduct(
                "other-product-2",
                [otherSellerComponentIds[1]],
                "QmOtherProduct2"
            );
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
            expect(product1After.businessId).to.equal(product1Before.businessId);
            expect(product1After.metadataCID).to.equal(product1Before.metadataCID);
            expect(product1After.componentIds).to.deep.equal(product1Before.componentIds);
            expect(product1After.active).to.equal(product1Before.active);
            console.log("   ✅ Product 1 fully preserved (id, seller, businessId, metadata, components, status)");
            
            const product2After = await productRegistry.getProduct(2);
            expect(product2After.id).to.equal(product2Before.id);
            expect(product2After.seller).to.equal(product2Before.seller);
            expect(product2After.businessId).to.equal(product2Before.businessId);
            expect(product2After.metadataCID).to.equal(product2Before.metadataCID);
            expect(product2After.componentIds).to.deep.equal(product2Before.componentIds);
            expect(product2After.active).to.equal(product2Before.active); // false (неактивный)
            console.log("   ✅ Product 2 fully preserved (inactive)");
            
            const product3After = await productRegistry.getProduct(3);
            expect(product3After.id).to.equal(product3Before.id);
            expect(product3After.seller).to.equal(product3Before.seller);
            expect(product3After.businessId).to.equal(product3Before.businessId);
            expect(product3After.metadataCID).to.equal(product3Before.metadataCID);
            expect(product3After.componentIds).to.deep.equal(product3Before.componentIds);
            expect(product3After.active).to.equal(product3Before.active); // true (активный)
            console.log("   ✅ Product 3 fully preserved (active)");
            
            const product4After = await productRegistry.getProduct(4);
            expect(product4After.id).to.equal(product4Before.id);
            expect(product4After.seller).to.equal(product4Before.seller);
            expect(product4After.businessId).to.equal(product4Before.businessId);
            expect(product4After.metadataCID).to.equal(product4Before.metadataCID);
            expect(product4After.componentIds).to.deep.equal(product4Before.componentIds);
            expect(product4After.active).to.equal(product4Before.active); // true
            console.log("   ✅ Product 4 fully preserved (otherSeller)");
            
            const product5After = await productRegistry.getProduct(5);
            expect(product5After.id).to.equal(product5Before.id);
            expect(product5After.seller).to.equal(product5Before.seller);
            expect(product5After.businessId).to.equal(product5Before.businessId);
            expect(product5After.metadataCID).to.equal(product5Before.metadataCID);
            expect(product5After.componentIds).to.deep.equal(product5Before.componentIds);
            expect(product5After.active).to.equal(product5Before.active); // false
            console.log("   ✅ Product 5 fully preserved (otherSeller, inactive)");
            
            // 4.3 businessId mapping
            expect(Number(await productRegistry.getProductIdByBusinessId("seller-product-1"))).to.equal(1);
            expect(Number(await productRegistry.getProductIdByBusinessId("seller-product-2"))).to.equal(2);
            expect(Number(await productRegistry.getProductIdByBusinessId("seller-product-3"))).to.equal(3);
            expect(Number(await productRegistry.getProductIdByBusinessId("other-product-1"))).to.equal(4);
            expect(Number(await productRegistry.getProductIdByBusinessId("other-product-2"))).to.equal(5);
            console.log("   ✅ businessIdToProductId mapping preserved for all products");
            
            // 4.4 activeProductIds array
            const activeProductIdsAfter = await productRegistry.getAllActiveProductIds();
            const activeBefore = activeProductIdsBefore.map(id => id.toString());
            const activeAfter = activeProductIdsAfter.map(id => id.toString());
            expect(activeAfter).to.deep.equal(activeBefore);
            console.log(`   ✅ activeProductIds array preserved: [${activeAfter.join(", ")}]`);
            
            // 4.5 sellerProducts mapping
            const sellerProductsAfter = await productRegistry.getProductsBySeller(seller.address);
            const otherSellerProductsAfter = await productRegistry.getProductsBySeller(otherSeller.address);
            expect(sellerProductsAfter.map(id => id.toString())).to.deep.equal(sellerProductsBefore.map(id => id.toString()));
            expect(otherSellerProductsAfter.map(id => id.toString())).to.deep.equal(otherSellerProductsBefore.map(id => id.toString()));
            console.log(`   ✅ sellerProducts mapping preserved for seller and otherSeller`);
            
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
            await expectEvent(
                productRegistry.connect(seller).createProduct(
                    "seller-product-post-upgrade",
                    [sellerComponentIds[0]],
                    "QmPostUpgrade"
                ),
                productRegistry,
                "ProductCreated",
                args => {
                    expect(args.seller).to.equal(seller.address);
                    expect(Number(args.productId)).to.equal(6);
                    expect(args.businessId).to.equal("seller-product-post-upgrade");
                    expect(args.metadataCID).to.equal("QmPostUpgrade");
                    expect(args.componentIds).to.deep.equal([sellerComponentIds[0]]);
                }
            );
            const newProduct = await productRegistry.getProduct(6);
            expect(Number(newProduct.id)).to.equal(6);
            expect(newProduct.seller).to.equal(seller.address);
            expect(newProduct.businessId).to.equal("seller-product-post-upgrade");
            expect(newProduct.metadataCID).to.equal("QmPostUpgrade");
            expect(newProduct.componentIds).to.deep.equal([sellerComponentIds[0]]);
            expect(newProduct.active).to.be.false;
            expect(Number(await productRegistry.getProductIdByBusinessId("seller-product-post-upgrade"))).to.equal(6);
            console.log("   ✅ New product creation works after upgrade (ID = 6 + mapping)");
            
            // Активация нового продукта
            await expectNotReverted(
                productRegistry.connect(seller).activateProduct(6),
                "Activation should succeed after upgrade"
            );
            const activeIdsAfterNew = await productRegistry.getAllActiveProductIds();
            const expectedActiveIds = [...activeProductIdsBefore.map(id => id.toString()), "6"];
            expect(activeIdsAfterNew.map(id => id.toString())).to.deep.equal(expectedActiveIds);
            console.log("   ✅ Product activation works after upgrade");
            
            // Обновление продукта
            await expectEvent(
                productRegistry.connect(seller).updateProduct(6, "QmUpdated", 100),
                productRegistry,
                "ProductUpdated",
                args => {
                    expect(Number(args.productId)).to.equal(6);
                    expect(args.businessId).to.equal("seller-product-post-upgrade");
                    expect(args.ipfsCID).to.equal("QmUpdated");
                }
            );
            const updatedProduct = await productRegistry.getProduct(6);
            expect(updatedProduct.metadataCID).to.equal("QmUpdated");
            expect(updatedProduct.businessId).to.equal("seller-product-post-upgrade");
            expect(updatedProduct.componentIds).to.deep.equal([sellerComponentIds[0]]);
            expect(updatedProduct.active).to.be.true;
            console.log("   ✅ Product update works after upgrade (metadata + businessId preserved)");
            
            console.log("   🎉 FULL STATE PRESERVATION TEST PASSED");
        });
    });

    // ==========================================
    // TEST SUITE 2: Pausable Protection (P1)
    // ==========================================
    describe("⏸️ Pausable Protection - Comprehensive", function () {
        beforeEach(async function () {
            // Создаём базовые данные для тестов паузы
            await productRegistry.connect(seller).createProduct(
                "seller-product-pause-base",
                [sellerComponentIds[0]],
                "QmPauseTest"
            );
            await productRegistry.connect(seller).activateProduct(1);
            console.log("   ✅ Base product created and activated for Pausable tests");
        });

        it("Should block createProduct when paused", async function () {
            console.log("   🔍 Testing createProduct pause protection...");
            
            // Пауза
            await productRegistry.connect(admin).pause();
            console.log("   ⏸️  Contract paused");
            
            // Попытка создать продукт должна провалиться
            await expectRevertCustom(
                productRegistry.connect(seller).createProduct(
                    "seller-product-paused",
                    [sellerComponentIds[1]],
                    "QmPaused"
                ),
                "EnforcedPause",
                productRegistry
            );
            console.log("   ✅ createProduct blocked during pause");
            
            // Снятие паузы
            await productRegistry.connect(admin).unpause();
            console.log("   ▶️  Contract unpaused");
            
            // Теперь должно работать
            await productRegistry.connect(seller).createProduct(
                "seller-product-unpaused",
                [sellerComponentIds[1]],
                "QmPaused"
            );
            const newProduct = await productRegistry.getProduct(2);
            expect(Number(newProduct.id)).to.equal(2);
            expect(newProduct.metadataCID).to.equal("QmPaused");
            expect(newProduct.businessId).to.equal("seller-product-unpaused");
            expect(newProduct.componentIds).to.deep.equal([sellerComponentIds[1]]);
            console.log("   ✅ createProduct works after unpause");
        });

        it("Should block activateProduct when paused", async function () {
            console.log("   🔍 Testing activateProduct pause protection...");
            
            // Создаём продукт ДО паузы
            await productRegistry.connect(seller).createProduct(
                "seller-product-pause-activate",
                [sellerComponentIds[2]],
                "QmPauseActivate"
            );
            console.log("   ✅ Product created before pause");
            
            // Пауза
            await productRegistry.connect(admin).pause();
            console.log("   ⏸️  Contract paused");
            
            // Попытка активировать должна провалиться
            await expectRevertCustom(
                productRegistry.connect(seller).activateProduct(2),
                "EnforcedPause",
                productRegistry
            );
            console.log("   ✅ activateProduct blocked during pause");
            
            // Снятие паузы
            await productRegistry.connect(admin).unpause();
            console.log("   ▶️  Contract unpaused");
            
            // Теперь должно работать
            await expectNotReverted(
                productRegistry.connect(seller).activateProduct(2),
                "Activation should work after unpause"
            );
            const product = await productRegistry.getProduct(2);
            expect(product.active).to.be.true;
            expect(product.businessId).to.equal("seller-product-pause-activate");
            console.log("   ✅ activateProduct works after unpause");
        });

        it("Should block deactivateProduct when paused", async function () {
            console.log("   🔍 Testing deactivateProduct pause protection...");
            
            // Пауза
            await productRegistry.connect(admin).pause();
            console.log("   ⏸️  Contract paused");
            
            // Попытка деактивировать должна провалиться
            await expectRevertCustom(
                productRegistry.connect(seller).deactivateProduct(1),
                "EnforcedPause",
                productRegistry
            );
            console.log("   ✅ deactivateProduct blocked during pause");
            
            // Снятие паузы
            await productRegistry.connect(admin).unpause();
            console.log("   ▶️  Contract unpaused");
            
            // Теперь должно работать
            await expectNotReverted(
                productRegistry.connect(seller).deactivateProduct(1),
                "Deactivation should work after unpause"
            );
            const product = await productRegistry.getProduct(1);
            expect(product.active).to.be.false;
            expect(product.businessId).to.equal("seller-product-pause-base");
            console.log("   ✅ deactivateProduct works after unpause");
        });

        it("Should block updateProduct when paused", async function () {
            console.log("   🔍 Testing updateProduct pause protection...");
            
            // Пауза
            await productRegistry.connect(admin).pause();
            console.log("   ⏸️  Contract paused");
            
            // Попытка обновить должна провалиться
            await expectRevertCustom(
                productRegistry.connect(seller).updateProduct(1, "QmUpdated", 100),
                "EnforcedPause",
                productRegistry
            );
            console.log("   ✅ updateProduct blocked during pause");
            
            // Снятие паузы
            await productRegistry.connect(admin).unpause();
            console.log("   ▶️  Contract unpaused");
            
            // Теперь должно работать
            await expectEvent(
                productRegistry.connect(seller).updateProduct(1, "QmUpdated", 100),
                productRegistry,
                "ProductUpdated",
                args => {
                    expect(Number(args.productId)).to.equal(1);
                    expect(args.businessId).to.equal("seller-product-pause-base");
                    expect(args.ipfsCID).to.equal("QmUpdated");
                }
            );
            const product = await productRegistry.getProduct(1);
            expect(product.metadataCID).to.equal("QmUpdated");
            expect(product.businessId).to.equal("seller-product-pause-base");
            console.log("   ✅ updateProduct works after unpause");
        });

        it("Should block clearSellerCatalog when paused", async function () {
            console.log("   🔍 Testing clearSellerCatalog pause protection...");
            
            // Пауза
            await productRegistry.connect(admin).pause();
            console.log("   ⏸️  Contract paused");
            
            // Попытка очистить каталог должна провалиться
            await expectRevertCustom(
                productRegistry.connect(seller).clearSellerCatalog(seller.address),
                "EnforcedPause",
                productRegistry
            );
            console.log("   ✅ clearSellerCatalog blocked during pause");
            
            // Снятие паузы
            await productRegistry.connect(admin).unpause();
            console.log("   ▶️  Contract unpaused");
            
            // Теперь должно работать
            await expectEvent(
                productRegistry.connect(seller).clearSellerCatalog(seller.address),
                productRegistry,
                "CatalogCleared",
                args => {
                    expect(args.seller).to.equal(seller.address);
                    expect(Number(args.productsCleared)).to.equal(1);
                }
            );
            const products = await productRegistry.getProductsBySeller(seller.address);
            expect(products.length).to.equal(0);
            await expectRevertCustom(
                productRegistry.getProductIdByBusinessId("seller-product-pause-base"),
                "BusinessIdUnknown",
                productRegistry
            );
            console.log("   ✅ clearSellerCatalog works after unpause");
        });
    });
});

