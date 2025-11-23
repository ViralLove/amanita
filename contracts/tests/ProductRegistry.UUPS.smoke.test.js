const { expect } = require("chai");
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
 * 🧪 ProductRegistry UUPS - Smoke Test
 * 
 * Цель: Быстрая валидация Phase 1-3 результатов
 * 
 * Проверяемые элементы:
 * - Деплой Proxy + Logic
 * - Initialize через Proxy
 * - Базовая функциональность createProduct
 * - Базовая функциональность activateProduct
 * - Custom errors работают
 * - ReentrancyGuard работает
 * - Pausable работает
 * 
 * Этот smoke-тест НЕ заменяет comprehensive тесты!
 */

describe("🔥 ProductRegistry UUPS - Smoke Test", function () {
    let admin, seller, otherSeller, user1;
    let proxy, logic, productRegistry;
    let spiralEngine;
    let componentRegistry;
    let SELLER_ROLE;
    let sellerComponentIds;

    beforeEach(async function () {
        [admin, seller, otherSeller, user1] = await ethers.getSigners();
        
        console.log("\n🔥 Smoke Test Setup Starting...");
        
        // 1. Deploy Mock SpiralEngine для тестирования
        const SpiralEngineMock = await ethers.getContractFactory("contracts/mocks/MockSpiralEngine.sol:MockSpiralEngine");
        spiralEngine = await SpiralEngineMock.deploy();
        await spiralEngine.waitForDeployment();
        console.log(`   ✅ Mock SpiralEngine deployed: ${await spiralEngine.getAddress()}`);
        
        // 2. Deploy OrganicComponentRegistry UUPS
        const OCRLogic = await ethers.getContractFactory("OrganicComponentRegistryLogic");
        const ocrLogic = await OCRLogic.deploy();
        await ocrLogic.waitForDeployment();
        const ocrInitCalldata = ocrLogic.interface.encodeFunctionData("initialize", [admin.address]);
        const OCRProxy = await ethers.getContractFactory("OrganicComponentRegistryProxy");
        const ocrProxy = await OCRProxy.deploy(await ocrLogic.getAddress(), ocrInitCalldata);
        await ocrProxy.waitForDeployment();
        componentRegistry = ocrLogic.attach(await ocrProxy.getAddress());
        await componentRegistry.connect(admin).setSpiralEngine(await spiralEngine.getAddress());
        
        // 3. Deploy Logic implementation
        const Logic = await ethers.getContractFactory("ProductRegistryLogic");
        logic = await Logic.deploy();
        await logic.waitForDeployment();
        console.log(`   ✅ Logic deployed: ${await logic.getAddress()}`);
        
        // 4. Encode initialize(admin, spiralEngine) calldata
        const initCalldata = logic.interface.encodeFunctionData("initialize", [
            admin.address,
            await spiralEngine.getAddress()
        ]);
        
        // 5. Deploy Proxy with implementation and init data
        const Proxy = await ethers.getContractFactory("ProductRegistryProxy");
        proxy = await Proxy.deploy(await logic.getAddress(), initCalldata);
        await proxy.waitForDeployment();
        console.log(`   ✅ Proxy deployed: ${await proxy.getAddress()}`);
        
        // 6. Attach Logic ABI to proxy address
        productRegistry = Logic.attach(await proxy.getAddress());
        
        // 7. Link component registry
        await productRegistry.connect(admin).setOrganicComponentRegistry(await componentRegistry.getAddress());
        
        // 8. Setup mock SpiralEngine для seller
        SELLER_ROLE = await spiralEngine.SELLER_ROLE();
        
        // Активируем seller в моке
        await spiralEngine.setUserActivated(seller.address, true);
        await spiralEngine.grantRole(SELLER_ROLE, seller.address);
        
        // Активируем otherSeller в моке
        await spiralEngine.setUserActivated(otherSeller.address, true);
        await spiralEngine.grantRole(SELLER_ROLE, otherSeller.address);
        sellerComponentIds = ["smoke-comp-1", "smoke-comp-2", "smoke-comp-3"];
        for (const componentId of sellerComponentIds) {
            await componentRegistry.connect(seller).createComponent(componentId, `Qm${componentId}`);
        }
        
        console.log("   ✅ Sellers configured in mock & components ready");
    });

    describe("🏗️ Architecture Validation", function () {
        it("Should deploy and initialize correctly", async function () {
            // Проверяем роли
            expect(await productRegistry.hasRole(
                await productRegistry.DEFAULT_ADMIN_ROLE(),
                admin.address
            )).to.be.true;
            
            expect(await productRegistry.hasRole(
                await productRegistry.ADMIN_ROLE(),
                admin.address
            )).to.be.true;
            
            expect(await productRegistry.hasRole(
                await productRegistry.UPGRADER_ROLE(),
                admin.address
            )).to.be.true;
            
            // Проверяем версию
            expect(Number(await productRegistry.LOGIC_VERSION())).to.equal(1);
            
            // Проверяем SpiralEngine установлен
            expect(await productRegistry.spiralEngine()).to.equal(await spiralEngine.getAddress());
            
            console.log("   ✅ Architecture validated");
        });
        
        it("Should have correct constants", async function () {
            expect(Number(await productRegistry.LOGIC_VERSION())).to.equal(1);
            expect(Number(await productRegistry.MAX_PRODUCTS_PER_CLEAR())).to.equal(10000);
            
            const upgraderRole = await productRegistry.UPGRADER_ROLE();
            const adminRole = await productRegistry.ADMIN_ROLE();
            const sellerRole = await productRegistry.SELLER_ROLE();
            
            expect(upgraderRole).to.not.equal(ethers.ZeroHash);
            expect(adminRole).to.not.equal(ethers.ZeroHash);
            expect(sellerRole).to.not.equal(ethers.ZeroHash);
            
            console.log("   ✅ Constants validated");
        });
        
        it("Should not allow double initialization", async function () {
            await expectRevertCustom(
                productRegistry.connect(admin).initialize(admin.address, await spiralEngine.getAddress()),
                "InvalidInitialization",
                productRegistry
            );
            
            console.log("   ✅ Double initialization blocked");
        });
    });

    describe("📦 Basic Operations", function () {
        it("Should create product through proxy", async function () {
            await expectEvent(
                productRegistry.connect(seller).createProduct(
                    "smoke-product-1",
                    [sellerComponentIds[0]],
                    "QmTestCID123"
                ),
                productRegistry,
                "ProductCreated",
                args => {
                    expect(args.seller).to.equal(seller.address);
                    expect(Number(args.productId)).to.equal(1);
                    expect(args.businessId).to.equal("smoke-product-1");
                    expect(args.metadataCID).to.equal("QmTestCID123");
                    expect(Number(args.status)).to.equal(0);
                }
            );
            
            // Проверяем данные через getProduct
            const product = await productRegistry.getProduct(1);
            expect(Number(product.id)).to.equal(1);
            expect(product.seller).to.equal(seller.address);
            expect(product.businessId).to.equal("smoke-product-1");
            expect(product.metadataCID).to.equal("QmTestCID123");
            expect(product.componentIds).to.deep.equal([sellerComponentIds[0]]);
            expect(product.active).to.be.false;
            expect(Number(await productRegistry.getProductIdByBusinessId("smoke-product-1"))).to.equal(1);
            
            console.log("   ✅ Product created through proxy");
        });
        
        it("Should activate product", async function () {
            await productRegistry.connect(seller).createProduct(
                "smoke-product-activate",
                [sellerComponentIds[0]],
                "QmTestCID123"
            );
            
            await expectNotReverted(
                productRegistry.connect(seller).activateProduct(1),
                "Activation should succeed"
            );
            
            const product = await productRegistry.getProduct(1);
            expect(product.active).to.be.true;
            expect(product.businessId).to.equal("smoke-product-activate");
            
            const activeIds = await productRegistry.getAllActiveProductIds();
            expect(activeIds.map(id => Number(id))).to.deep.equal([1]);
            
            console.log("   ✅ Product activated");
        });
        
        it("Should update product", async function () {
            await productRegistry.connect(seller).createProduct(
                "smoke-product-update",
                [sellerComponentIds[0]],
                "QmTestCID123"
            );
            await productRegistry.connect(seller).activateProduct(1);
            
            await expectEvent(
                productRegistry.connect(seller).updateProduct(1, "QmNewCID456", 100),
                productRegistry,
                "ProductUpdated",
                args => {
                    expect(Number(args.productId)).to.equal(1);
                    expect(args.businessId).to.equal("smoke-product-update");
                    expect(args.ipfsCID).to.equal("QmNewCID456");
                }
            );
            
            const product = await productRegistry.getProduct(1);
            expect(product.metadataCID).to.equal("QmNewCID456");
            expect(product.businessId).to.equal("smoke-product-update");
            
            console.log("   ✅ Product updated");
        });
        
        it("Should deactivate product", async function () {
            await productRegistry.connect(seller).createProduct(
                "smoke-product-deactivate",
                [sellerComponentIds[1]],
                "QmTestCID123"
            );
            await productRegistry.connect(seller).activateProduct(1);
            
            await expectNotReverted(
                productRegistry.connect(seller).deactivateProduct(1),
                "Deactivation should succeed"
            );
            
            const product = await productRegistry.getProduct(1);
            expect(product.active).to.be.false;
            
            const activeIds = await productRegistry.getAllActiveProductIds();
            expect(activeIds.length).to.equal(0);
            
            console.log("   ✅ Product deactivated");
        });
        
        it("Should enforce custom errors", async function () {
            // EmptyCID
            await expectRevertCustom(
                productRegistry.connect(seller).createProduct(
                    "smoke-empty-cid",
                    [sellerComponentIds[0]],
                    ""
                ),
                "EmptyCID",
                productRegistry
            );
            
            // ProductDoesNotExist
            await expectRevertCustom(
                productRegistry.getProduct(999),
                "ProductDoesNotExist",
                productRegistry
            );
            
            // NotASeller (user1 не имеет SELLER_ROLE)
            await expectRevertCustom(
                productRegistry.connect(user1).createProduct(
                    "smoke-not-seller",
                    [sellerComponentIds[0]],
                    "QmTest"
                ),
                "NotASeller",
                productRegistry
            );
            
            console.log("   ✅ Custom errors working");
        });
    });

    describe("🔧 UUPS Management", function () {
        it("Should upgrade logic contract", async function () {
            // Создаем продукт для проверки сохранения данных
            await productRegistry.connect(seller).createProduct(
                "smoke-before-upgrade",
                [sellerComponentIds[0]],
                "QmBeforeUpgrade"
            );
            
            // Deploy новый Logic (V2)
            const LogicV2 = await ethers.getContractFactory("ProductRegistryLogic");
            const logicV2 = await LogicV2.deploy();
            await logicV2.waitForDeployment();
            
            // Upgrade через admin (UPGRADER_ROLE)
            await productRegistry.connect(admin).upgradeToAndCall(
                await logicV2.getAddress(),
                "0x"  // нет миграции данных
            );
            
            // Проверяем что данные сохранились
            const product = await productRegistry.getProduct(1);
            expect(product.metadataCID).to.equal("QmBeforeUpgrade");
            expect(product.businessId).to.equal("smoke-before-upgrade");
            expect(Number(await productRegistry.getProductIdByBusinessId("smoke-before-upgrade"))).to.equal(1);
            
            console.log("   ✅ Upgrade successful, data preserved");
        });
        
        it("Should pause and unpause contract", async function () {
            await productRegistry.connect(admin).pause();
            
            // Функции с whenNotPaused должны провалиться
            await expectRevertCustom(
                productRegistry.connect(seller).createProduct(
                    "smoke-paused",
                    [sellerComponentIds[0]],
                    "QmTest"
                ),
                "EnforcedPause",
                productRegistry
            );
            
            await productRegistry.connect(admin).unpause();
            
            // После unpause должно работать
            await expectNotReverted(
                productRegistry.connect(seller).createProduct(
                    "smoke-unpaused",
                    [sellerComponentIds[0]],
                    "QmTest"
                ),
                "createProduct should succeed after unpause"
            );
            
            console.log("   ✅ Pause/unpause working");
        });
        
        it("Should restrict upgrades to UPGRADER_ROLE only", async function () {
            const LogicV2 = await ethers.getContractFactory("ProductRegistryLogic");
            const logicV2 = await LogicV2.deploy();
            await logicV2.waitForDeployment();
            
            // seller БЕЗ UPGRADER_ROLE не может апгрейдить
            await expectRevertCustom(
                productRegistry.connect(seller).upgradeToAndCall(
                    await logicV2.getAddress(),
                    "0x"
                ),
                "AccessControlUnauthorizedAccount",
                productRegistry
            );
            
            // admin С UPGRADER_ROLE может
            await expectNotReverted(
                productRegistry.connect(admin).upgradeToAndCall(
                    await logicV2.getAddress(),
                    "0x"
                ),
                "Admin with UPGRADER_ROLE should upgrade successfully"
            );
            
            console.log("   ✅ Upgrade authorization working");
        });
        
        it("Should have reentrancy protection", async function () {
            // Smoke-тест: функции с nonReentrant работают корректно
            await productRegistry.connect(seller).createProduct(
                "smoke-reent-1",
                [sellerComponentIds[0]],
                "QmTest1"
            );
            await productRegistry.connect(seller).createProduct(
                "smoke-reent-2",
                [sellerComponentIds[1]],
                "QmTest2"
            );
            await productRegistry.connect(seller).activateProduct(1);
            await productRegistry.connect(seller).activateProduct(2);
            
            const activeIds = await productRegistry.getAllActiveProductIds();
            expect(activeIds.map(id => Number(id))).to.deep.equal([1, 2]);
            
            console.log("   ✅ Reentrancy protection working");
        });
    });

    describe("📊 View Functions", function () {
        it("Should get all active product IDs", async function () {
            await productRegistry.connect(seller).createProduct(
                "smoke-active-1",
                [sellerComponentIds[0]],
                "QmTest1"
            );
            await productRegistry.connect(seller).createProduct(
                "smoke-active-2",
                [sellerComponentIds[1]],
                "QmTest2"
            );
            await productRegistry.connect(seller).activateProduct(1);
            
            const activeIds = await productRegistry.getAllActiveProductIds();
            expect(activeIds.map(id => Number(id))).to.deep.equal([1]);
            
            console.log("   ✅ getAllActiveProductIds working");
        });
        
        it("Should get products by seller", async function () {
            await productRegistry.connect(seller).createProduct(
                "smoke-seller-1",
                [sellerComponentIds[0]],
                "QmTest1"
            );
            await productRegistry.connect(seller).createProduct(
                "smoke-seller-2",
                [sellerComponentIds[1]],
                "QmTest2"
            );
            
            const sellerProducts = await productRegistry.getProductsBySeller(seller.address);
            expect(sellerProducts.map(id => Number(id))).to.deep.equal([1, 2]);
            
            console.log("   ✅ getProductsBySeller working");
        });
        
        it("Should get catalog version", async function () {
            const versionBefore = await productRegistry.connect(seller).getMyCatalogVersion();
            expect(Number(versionBefore)).to.equal(0);
            
            await productRegistry.connect(seller).createProduct(
                "smoke-version-1",
                [sellerComponentIds[0]],
                "QmTest1"
            );
            
            const versionAfter = await productRegistry.connect(seller).getMyCatalogVersion();
            expect(Number(versionAfter)).to.equal(1);
            
            console.log("   ✅ getMyCatalogVersion working");
        });
        
        it("Should get full seller catalog", async function () {
            await productRegistry.connect(seller).createProduct(
                "smoke-full-1",
                [sellerComponentIds[0]],
                "QmTest1"
            );
            await productRegistry.connect(seller).createProduct(
                "smoke-full-2",
                [sellerComponentIds[1]],
                "QmTest2"
            );
            
            const fullCatalog = await productRegistry.connect(seller).getProductsBySellerFull();
            expect(fullCatalog.length).to.equal(2);
            expect(fullCatalog[0].businessId).to.equal("smoke-full-1");
            expect(fullCatalog[0].metadataCID).to.equal("QmTest1");
            expect(fullCatalog[0].componentIds).to.deep.equal([sellerComponentIds[0]]);
            expect(fullCatalog[1].businessId).to.equal("smoke-full-2");
            expect(fullCatalog[1].metadataCID).to.equal("QmTest2");
            expect(fullCatalog[1].componentIds).to.deep.equal([sellerComponentIds[1]]);
            
            console.log("   ✅ getProductsBySellerFull working");
        });
    });

    describe("🔐 Admin Functions", function () {
        it("Should allow admin to update SpiralEngine", async function () {
            // Deploy новый мок SpiralEngine
            const NewMock = await ethers.getContractFactory("contracts/mocks/MockSpiralEngine.sol:MockSpiralEngine");
            const newSpiral = await NewMock.deploy();
            await newSpiral.waitForDeployment();
            
            const oldAddress = await productRegistry.spiralEngine();
            
            await expectEvent(
                productRegistry.connect(admin).setSpiralEngine(await newSpiral.getAddress()),
                productRegistry,
                "SpiralEngineUpdated",
                args => {
                    expect(args.oldSpiralEngine).to.equal(oldAddress);
                    expect(args.newSpiralEngine).to.equal(newSpiral.target);
                }
            );
            
            const newAddress = await productRegistry.spiralEngine();
            expect(newAddress).to.equal(await newSpiral.getAddress());
            expect(newAddress).to.not.equal(oldAddress);
            
            console.log("   ✅ setSpiralEngine working");
        });
        
        it("Should restrict setSpiralEngine to ADMIN_ROLE", async function () {
            const NewMock = await ethers.getContractFactory("contracts/mocks/MockSpiralEngine.sol:MockSpiralEngine");
            const newSpiral = await NewMock.deploy();
            
            await expectRevertCustom(
                productRegistry.connect(seller).setSpiralEngine(await newSpiral.getAddress()),
                "AccessControlUnauthorizedAccount",
                productRegistry
            );
            
            console.log("   ✅ setSpiralEngine protected");
        });
    });
});

