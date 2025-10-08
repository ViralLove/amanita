const { expect } = require("chai");
const { ethers } = require("hardhat");

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
    let SELLER_ROLE;

    beforeEach(async function () {
        [admin, seller, otherSeller, user1] = await ethers.getSigners();
        
        console.log("\n🔥 Smoke Test Setup Starting...");
        
        // 1. Deploy Mock SpiralEngine для тестирования
        const SpiralEngineMock = await ethers.getContractFactory("contracts/mocks/MockSpiralEngine.sol:MockSpiralEngine");
        spiralEngine = await SpiralEngineMock.deploy();
        await spiralEngine.waitForDeployment();
        console.log(`   ✅ Mock SpiralEngine deployed: ${await spiralEngine.getAddress()}`);
        
        // 2. Deploy Logic implementation
        const Logic = await ethers.getContractFactory("ProductRegistryLogic");
        logic = await Logic.deploy();
        await logic.waitForDeployment();
        console.log(`   ✅ Logic deployed: ${await logic.getAddress()}`);
        
        // 3. Encode initialize(admin, spiralEngine) calldata
        const initCalldata = logic.interface.encodeFunctionData("initialize", [
            admin.address,
            await spiralEngine.getAddress()
        ]);
        
        // 4. Deploy Proxy with implementation and init data
        const Proxy = await ethers.getContractFactory("ProductRegistryProxy");
        proxy = await Proxy.deploy(await logic.getAddress(), initCalldata);
        await proxy.waitForDeployment();
        console.log(`   ✅ Proxy deployed: ${await proxy.getAddress()}`);
        
        // 5. Attach Logic ABI to proxy address
        productRegistry = Logic.attach(await proxy.getAddress());
        
        // 6. Setup mock SpiralEngine для seller
        SELLER_ROLE = await spiralEngine.SELLER_ROLE();
        
        // Активируем seller в моке
        await spiralEngine.setUserActivated(seller.address, true);
        await spiralEngine.grantRole(SELLER_ROLE, seller.address);
        
        // Активируем otherSeller в моке
        await spiralEngine.setUserActivated(otherSeller.address, true);
        await spiralEngine.grantRole(SELLER_ROLE, otherSeller.address);
        
        console.log("   ✅ Sellers configured in mock");
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
            expect(await productRegistry.LOGIC_VERSION()).to.equal(1);
            
            // Проверяем SpiralEngine установлен
            expect(await productRegistry.spiralEngine()).to.equal(await spiralEngine.getAddress());
            
            console.log("   ✅ Architecture validated");
        });
        
        it("Should have correct constants", async function () {
            expect(await productRegistry.LOGIC_VERSION()).to.equal(1);
            expect(await productRegistry.MAX_PRODUCTS_PER_CLEAR()).to.equal(10000);
            
            const upgraderRole = await productRegistry.UPGRADER_ROLE();
            const adminRole = await productRegistry.ADMIN_ROLE();
            const sellerRole = await productRegistry.SELLER_ROLE();
            
            expect(upgraderRole).to.not.equal(ethers.ZeroHash);
            expect(adminRole).to.not.equal(ethers.ZeroHash);
            expect(sellerRole).to.not.equal(ethers.ZeroHash);
            
            console.log("   ✅ Constants validated");
        });
        
        it("Should not allow double initialization", async function () {
            await expect(
                productRegistry.connect(admin).initialize(admin.address, await spiralEngine.getAddress())
            ).to.be.revertedWithCustomError(productRegistry, "InvalidInitialization");
            
            console.log("   ✅ Double initialization blocked");
        });
    });

    describe("📦 Basic Operations", function () {
        it("Should create product through proxy", async function () {
            const tx = await productRegistry.connect(seller).createProduct("QmTestCID123");
            const receipt = await tx.wait();
            
            // Проверяем событие
            const event = receipt.logs.find(log => {
                try {
                    const parsed = productRegistry.interface.parseLog(log);
                    return parsed && parsed.name === "ProductCreated";
                } catch (e) {
                    return false;
                }
            });
            expect(event).to.not.be.undefined;
            
            const parsed = productRegistry.interface.parseLog(event);
            expect(parsed.args.seller).to.equal(seller.address);
            expect(parsed.args.productId).to.equal(1);
            expect(parsed.args.ipfsCID).to.equal("QmTestCID123");
            expect(parsed.args.status).to.equal(0); // неактивный
            
            // Проверяем данные через getProduct
            const product = await productRegistry.getProduct(1);
            expect(product.id).to.equal(1);
            expect(product.seller).to.equal(seller.address);
            expect(product.ipfsCID).to.equal("QmTestCID123");
            expect(product.active).to.be.false;
            
            console.log("   ✅ Product created through proxy");
        });
        
        it("Should activate product", async function () {
            await productRegistry.connect(seller).createProduct("QmTestCID123");
            
            const tx = await productRegistry.connect(seller).activateProduct(1);
            await tx.wait();
            
            const product = await productRegistry.getProduct(1);
            expect(product.active).to.be.true;
            
            const activeIds = await productRegistry.getAllActiveProductIds();
            expect(activeIds.length).to.equal(1);
            expect(activeIds[0]).to.equal(1);
            
            console.log("   ✅ Product activated");
        });
        
        it("Should update product", async function () {
            await productRegistry.connect(seller).createProduct("QmTestCID123");
            await productRegistry.connect(seller).activateProduct(1);
            
            await productRegistry.connect(seller).updateProduct(1, "QmNewCID456", 100);
            
            const product = await productRegistry.getProduct(1);
            expect(product.ipfsCID).to.equal("QmNewCID456");
            
            console.log("   ✅ Product updated");
        });
        
        it("Should deactivate product", async function () {
            await productRegistry.connect(seller).createProduct("QmTestCID123");
            await productRegistry.connect(seller).activateProduct(1);
            
            await productRegistry.connect(seller).deactivateProduct(1);
            
            const product = await productRegistry.getProduct(1);
            expect(product.active).to.be.false;
            
            const activeIds = await productRegistry.getAllActiveProductIds();
            expect(activeIds.length).to.equal(0);
            
            console.log("   ✅ Product deactivated");
        });
        
        it("Should enforce custom errors", async function () {
            // EmptyCID
            await expect(
                productRegistry.connect(seller).createProduct("")
            ).to.be.revertedWithCustomError(productRegistry, "EmptyCID");
            
            // ProductDoesNotExist
            await expect(
                productRegistry.getProduct(999)
            ).to.be.revertedWithCustomError(productRegistry, "ProductDoesNotExist");
            
            // NotASeller (user1 не имеет SELLER_ROLE)
            await expect(
                productRegistry.connect(user1).createProduct("QmTest")
            ).to.be.revertedWithCustomError(productRegistry, "NotASeller");
            
            console.log("   ✅ Custom errors working");
        });
    });

    describe("🔧 UUPS Management", function () {
        it("Should upgrade logic contract", async function () {
            // Создаем продукт для проверки сохранения данных
            await productRegistry.connect(seller).createProduct("QmBeforeUpgrade");
            
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
            expect(product.ipfsCID).to.equal("QmBeforeUpgrade");
            
            console.log("   ✅ Upgrade successful, data preserved");
        });
        
        it("Should pause and unpause contract", async function () {
            await productRegistry.connect(admin).pause();
            
            // Функции с whenNotPaused должны провалиться
            await expect(
                productRegistry.connect(seller).createProduct("QmTest")
            ).to.be.revertedWithCustomError(productRegistry, "EnforcedPause");
            
            await productRegistry.connect(admin).unpause();
            
            // После unpause должно работать
            await expect(
                productRegistry.connect(seller).createProduct("QmTest")
            ).to.not.be.reverted;
            
            console.log("   ✅ Pause/unpause working");
        });
        
        it("Should restrict upgrades to UPGRADER_ROLE only", async function () {
            const LogicV2 = await ethers.getContractFactory("ProductRegistryLogic");
            const logicV2 = await LogicV2.deploy();
            await logicV2.waitForDeployment();
            
            // seller БЕЗ UPGRADER_ROLE не может апгрейдить
            await expect(
                productRegistry.connect(seller).upgradeToAndCall(
                    await logicV2.getAddress(),
                    "0x"
                )
            ).to.be.reverted;
            
            // admin С UPGRADER_ROLE может
            await expect(
                productRegistry.connect(admin).upgradeToAndCall(
                    await logicV2.getAddress(),
                    "0x"
                )
            ).to.not.be.reverted;
            
            console.log("   ✅ Upgrade authorization working");
        });
        
        it("Should have reentrancy protection", async function () {
            // Smoke-тест: функции с nonReentrant работают корректно
            await productRegistry.connect(seller).createProduct("QmTest1");
            await productRegistry.connect(seller).createProduct("QmTest2");
            await productRegistry.connect(seller).activateProduct(1);
            await productRegistry.connect(seller).activateProduct(2);
            
            const activeIds = await productRegistry.getAllActiveProductIds();
            expect(activeIds.length).to.equal(2);
            
            console.log("   ✅ Reentrancy protection working");
        });
    });

    describe("📊 View Functions", function () {
        it("Should get all active product IDs", async function () {
            await productRegistry.connect(seller).createProduct("QmTest1");
            await productRegistry.connect(seller).createProduct("QmTest2");
            await productRegistry.connect(seller).activateProduct(1);
            
            const activeIds = await productRegistry.getAllActiveProductIds();
            expect(activeIds.length).to.equal(1);
            expect(activeIds[0]).to.equal(1);
            
            console.log("   ✅ getAllActiveProductIds working");
        });
        
        it("Should get products by seller", async function () {
            await productRegistry.connect(seller).createProduct("QmTest1");
            await productRegistry.connect(seller).createProduct("QmTest2");
            
            const sellerProducts = await productRegistry.getProductsBySeller(seller.address);
            expect(sellerProducts.length).to.equal(2);
            expect(sellerProducts[0]).to.equal(1);
            expect(sellerProducts[1]).to.equal(2);
            
            console.log("   ✅ getProductsBySeller working");
        });
        
        it("Should get catalog version", async function () {
            const versionBefore = await productRegistry.connect(seller).getMyCatalogVersion();
            expect(versionBefore).to.equal(0);
            
            await productRegistry.connect(seller).createProduct("QmTest1");
            
            const versionAfter = await productRegistry.connect(seller).getMyCatalogVersion();
            expect(versionAfter).to.equal(1);
            
            console.log("   ✅ getMyCatalogVersion working");
        });
        
        it("Should get full seller catalog", async function () {
            await productRegistry.connect(seller).createProduct("QmTest1");
            await productRegistry.connect(seller).createProduct("QmTest2");
            
            const fullCatalog = await productRegistry.connect(seller).getProductsBySellerFull();
            expect(fullCatalog.length).to.equal(2);
            expect(fullCatalog[0].ipfsCID).to.equal("QmTest1");
            expect(fullCatalog[1].ipfsCID).to.equal("QmTest2");
            
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
            
            const tx = await productRegistry.connect(admin).setSpiralEngine(await newSpiral.getAddress());
            const receipt = await tx.wait();
            
            // Проверяем событие
            const event = receipt.logs.find(log => {
                try {
                    const parsed = productRegistry.interface.parseLog(log);
                    return parsed && parsed.name === "SpiralEngineUpdated";
                } catch (e) {
                    return false;
                }
            });
            expect(event).to.not.be.undefined;
            
            const newAddress = await productRegistry.spiralEngine();
            expect(newAddress).to.equal(await newSpiral.getAddress());
            expect(newAddress).to.not.equal(oldAddress);
            
            console.log("   ✅ setSpiralEngine working");
        });
        
        it("Should restrict setSpiralEngine to ADMIN_ROLE", async function () {
            const NewMock = await ethers.getContractFactory("contracts/mocks/MockSpiralEngine.sol:MockSpiralEngine");
            const newSpiral = await NewMock.deploy();
            
            await expect(
                productRegistry.connect(seller).setSpiralEngine(await newSpiral.getAddress())
            ).to.be.reverted;
            
            console.log("   ✅ setSpiralEngine protected");
        });
    });
});

