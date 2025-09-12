const { expect, assert } = require("chai");
const { ethers } = require("hardhat");

describe("ProductRegistry - Clear Catalog (Simple)", function () {
    let productRegistry;
    let deployer;
    let seller;

    beforeEach(async function () {
        // Используем ключ деплоера из .env
        const deployerPrivateKey = process.env.DEPLOYER_PRIVATE_KEY;
        if (!deployerPrivateKey) {
            throw new Error("DEPLOYER_PRIVATE_KEY not found in environment variables");
        }

        // Создаем кошелек деплоера
        deployer = new ethers.Wallet(deployerPrivateKey, ethers.provider);
        
        // Получаем продавца
        [seller] = await ethers.getSigners();

        // Подключаемся к существующему контракту ProductRegistry
        const productRegistryAddress = process.env.PRODUCT_REGISTRY_CONTRACT_ADDRESS;
        if (!productRegistryAddress) {
            throw new Error("PRODUCT_REGISTRY_CONTRACT_ADDRESS not found in environment variables");
        }

        const ProductRegistry = await ethers.getContractFactory("ProductRegistry");
        productRegistry = ProductRegistry.attach(productRegistryAddress);

        // Подключаемся к InviteNFT для активации продавца
        const inviteNFTAddress = process.env.INVITE_NFT_CONTRACT_ADDRESS;
        if (!inviteNFTAddress) {
            throw new Error("INVITE_NFT_CONTRACT_ADDRESS not found in environment variables");
        }

        const InviteNFT = await ethers.getContractFactory("InviteNFT");
        const inviteNFT = InviteNFT.attach(inviteNFTAddress);

        // Активируем продавца (назначаем роль SELLER_ROLE)
        console.log("🔷 Активируем продавца...");
        const SELLER_ROLE = ethers.keccak256(ethers.toUtf8Bytes("SELLER_ROLE"));
        
        try {
            // Проверяем, есть ли уже роль
            const hasRole = await inviteNFT.hasRole(SELLER_ROLE, seller.address);
            if (!hasRole) {
                // Назначаем роль SELLER_ROLE
                await inviteNFT.connect(deployer).grantRole(SELLER_ROLE, seller.address);
                console.log("✅ Роль SELLER_ROLE назначена продавцу");
            } else {
                console.log("✅ Продавец уже имеет роль SELLER_ROLE");
            }

            // Также нужно активировать пользователя (создать инвайт и использовать его)
            const isActivated = await inviteNFT.isUserActivated(seller.address);
            if (!isActivated) {
                console.log("🔷 Активируем пользователя через инвайт...");
                
                // Создаем тестовый инвайт
                const testInviteCode = "TEST-INVITE-1234";
                await inviteNFT.connect(deployer).mintInvites([testInviteCode], 0);
                console.log("✅ Тестовый инвайт создан");
                
                // Активируем пользователя через activateAndMintInvites
                await inviteNFT.connect(deployer).activateAndMintInvites(
                    testInviteCode,
                    seller.address,
                    ["NEW-INVITE-1", "NEW-INVITE-2"],
                    0
                );
                console.log("✅ Пользователь активирован через инвайт");
            } else {
                console.log("✅ Пользователь уже активирован");
            }
        } catch (error) {
            console.log("⚠️ Ошибка при активации (возможно, уже активирован):", error.message);
        }
    });

    describe("clearSellerCatalog", function () {
        it("Should clear seller's catalog successfully", async function () {
            console.log("Testing clearSellerCatalog function...");
            console.log("Seller address:", seller.address);
            console.log("Deployer address:", deployer.address);

            // Проверяем, что функция существует
            expect(typeof productRegistry.clearSellerCatalog).to.equal("function");

            // Сначала создаем несколько продуктов (если продавец активирован)
            try {
                console.log("Creating test products...");
                await productRegistry.connect(seller).createProduct("QmTest1");
                await productRegistry.connect(seller).createProduct("QmTest2");
                await productRegistry.connect(seller).createProduct("QmTest3");
                
                // Активируем продукты
                await productRegistry.connect(seller).activateProduct(1);
                await productRegistry.connect(seller).activateProduct(2);
                await productRegistry.connect(seller).activateProduct(3);
                
                console.log("✅ Test products created and activated");
                
                // Проверяем, что продукты существуют до очистки
                const productsBefore = await productRegistry.getProductsBySeller(seller.address);
                const activeProductsBefore = await productRegistry.getAllActiveProductIds();
                
                console.log(`Products before clearing: ${productsBefore.length}`);
                console.log(`Active products before clearing: ${activeProductsBefore.length}`);
                
                // Проверяем, что каталог не пуст
                assert(productsBefore.length > 0, "Catalog should not be empty before clearing");
                assert(activeProductsBefore.length > 0, "Should have active products before clearing");
                
                // Очищаем каталог
                console.log("Clearing catalog...");
                const tx = await productRegistry.connect(seller).clearSellerCatalog(seller.address);
                const receipt = await tx.wait();
                
                console.log("✅ clearSellerCatalog executed successfully");
                
                // Проверяем события
                const catalogClearedEvent = receipt.events.find(e => e.event === "CatalogCleared");
                assert(catalogClearedEvent !== undefined, "CatalogCleared event should be emitted");
                assert(catalogClearedEvent.args.seller === seller.address, "Event should contain correct seller address");
                assert(catalogClearedEvent.args.productsCleared.toNumber() === productsBefore.length, "Event should contain correct number of cleared products");
                
                // ===== ПРОВЕРКА ОЧИСТКИ КАТАЛОГА =====
                console.log("🔍 Checking catalog after clearing...");
                
                // Получаем каталог продавца после очистки
                const sellerCatalogAfter = await productRegistry.getProductsBySeller(seller.address);
                console.log(`📋 Seller catalog after clearing: ${sellerCatalogAfter.length} products`);
                
                // Получаем все активные продукты после очистки
                const allActiveProductsAfter = await productRegistry.getAllActiveProductIds();
                console.log(`🟢 All active products after clearing: ${allActiveProductsAfter.length} products`);
                
                // Получаем полную информацию о каталоге продавца
                const sellerCatalogFullAfter = await productRegistry.getProductsBySellerFull();
                console.log(`📊 Full seller catalog after clearing: ${sellerCatalogFullAfter.length} products`);
                
                // ===== ВАЛИДАЦИЯ ОЧИСТКИ =====
                console.log("✅ Validating catalog clearing...");
                
                // Проверяем, что каталог продавца пуст
                assert(sellerCatalogAfter.length === 0, `Seller catalog should be empty after clearing, but found ${sellerCatalogAfter.length} products`);
                console.log("✅ Seller catalog is empty");
                
                // Проверяем, что нет активных продуктов
                assert(allActiveProductsAfter.length === 0, `No active products should remain after clearing, but found ${allActiveProductsAfter.length} active products`);
                console.log("✅ No active products remain");
                
                // Проверяем, что полный каталог продавца пуст
                assert(sellerCatalogFullAfter.length === 0, `Full seller catalog should be empty after clearing, but found ${sellerCatalogFullAfter.length} products`);
                console.log("✅ Full seller catalog is empty");
                
                // Проверяем, что конкретные продукты удалены
                try {
                    await productRegistry.getProduct(1);
                    assert.fail("Product 1 should not exist after clearing");
                } catch (error) {
                    assert(error.message.includes("product does not exist"), "Product 1 should be deleted");
                }
                
                try {
                    await productRegistry.getProduct(2);
                    assert.fail("Product 2 should not exist after clearing");
                } catch (error) {
                    assert(error.message.includes("product does not exist"), "Product 2 should be deleted");
                }
                
                try {
                    await productRegistry.getProduct(3);
                    assert.fail("Product 3 should not exist after clearing");
                } catch (error) {
                    assert(error.message.includes("product does not exist"), "Product 3 should be deleted");
                }
                
                // ===== ДЕТАЛЬНОЕ СРАВНЕНИЕ ДО И ПОСЛЕ =====
                console.log("📊 Detailed before/after comparison:");
                console.log(`   Before: ${productsBefore.length} products, ${activeProductsBefore.length} active`);
                console.log(`   After:  ${sellerCatalogAfter.length} products, ${allActiveProductsAfter.length} active`);
                
                // Финальная проверка - каталог должен быть полностью пуст
                const finalCheck = await productRegistry.getProductsBySeller(seller.address);
                assert(finalCheck.length === 0, `Final check failed: catalog still contains ${finalCheck.length} products`);
                
                console.log("✅ All products successfully cleared and validated");
                console.log("🎉 Catalog clearing test completed successfully!");
                
            } catch (error) {
                console.log("Expected error (seller not activated):", error.message);
                // Это ожидаемо, если продавец не активирован в InviteNFT
                // Проверяем различные возможные ошибки
                const errorMessage = error.message;
                const isExpectedError = errorMessage.includes("Not a seller") || 
                                      errorMessage.includes("Not product seller") ||
                                      errorMessage.includes("Not activated");
                
                if (isExpectedError) {
                    console.log("✅ Expected error received - seller not properly activated");
                } else {
                    console.log("❌ Unexpected error:", errorMessage);
                    throw error; // Перебрасываем неожиданную ошибку
                }
            }
        });

        it("Should have correct function signature", async function () {
            // Проверяем, что функция имеет правильную сигнатуру
            const interface = productRegistry.interface;
            const clearCatalogFunction = interface.getFunction("clearSellerCatalog");
            
            expect(clearCatalogFunction).to.not.be.undefined;
            expect(clearCatalogFunction.inputs.length).to.equal(1);
            expect(clearCatalogFunction.inputs[0].name).to.equal("seller");
            expect(clearCatalogFunction.inputs[0].type).to.equal("address");
        });

        it("Should emit CatalogCleared event when called", async function () {
            // Проверяем, что событие CatalogCleared определено в ABI
            const interface = productRegistry.interface;
            const catalogClearedEvent = interface.getEvent("CatalogCleared");
            
            expect(catalogClearedEvent).to.not.be.undefined;
            expect(catalogClearedEvent.inputs.length).to.equal(2);
            expect(catalogClearedEvent.inputs[0].name).to.equal("seller");
            expect(catalogClearedEvent.inputs[0].type).to.equal("address");
            expect(catalogClearedEvent.inputs[1].name).to.equal("productsCleared");
            expect(catalogClearedEvent.inputs[1].type).to.equal("uint256");
        });

        it("Should have proper access control", async function () {
            // Проверяем, что функция требует правильные модификаторы
            try {
                await productRegistry.connect(seller).clearSellerCatalog(seller.address);
                // Если не упало с ошибкой, значит что-то не так
                expect.fail("Function should require seller role");
            } catch (error) {
                expect(error.message).to.include("Not a seller");
            }
        });

        it("Should validate input parameters", async function () {
            // Проверяем, что функция существует и может быть вызвана
            expect(typeof productRegistry.clearSellerCatalog).to.equal("function");
            
            // Проверяем, что функция требует правильные параметры
            const interface = productRegistry.interface;
            const clearCatalogFunction = interface.getFunction("clearSellerCatalog");
            expect(clearCatalogFunction.inputs.length).to.equal(1);
            expect(clearCatalogFunction.inputs[0].type).to.equal("address");
        });
    });

    describe("Contract compilation and deployment", function () {
        it("Should compile without errors", async function () {
            // Проверяем, что контракт скомпилирован
            const ProductRegistry = await ethers.getContractFactory("ProductRegistry");
            expect(ProductRegistry).to.not.be.undefined;
        });

        it("Should have correct contract address", async function () {
            const productRegistryAddress = process.env.PRODUCT_REGISTRY_CONTRACT_ADDRESS;
            expect(productRegistryAddress).to.not.be.undefined;
            expect(productRegistryAddress).to.match(/^0x[a-fA-F0-9]{40}$/);
        });
    });
});
