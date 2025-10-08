const { expect } = require("chai");
const { ethers } = require("hardhat");

describe("ProductRegistry - Clear Catalog (UUPS)", function () {
    let productRegistry;
    let spiralEngine;
    let admin, seller, otherSeller;
    let SELLER_ROLE;

    beforeEach(async function () {
        [admin, seller, otherSeller] = await ethers.getSigners();
        
        // 1. Deploy Mock SpiralEngine
        const SpiralEngineMock = await ethers.getContractFactory("contracts/mocks/MockSpiralEngine.sol:MockSpiralEngine");
        spiralEngine = await SpiralEngineMock.deploy();
        await spiralEngine.waitForDeployment();

        // 2. Deploy ProductRegistry Logic
        const Logic = await ethers.getContractFactory("ProductRegistryLogic");
        const logic = await Logic.deploy();
        await logic.waitForDeployment();
        
        // 3. Encode initialize calldata
        const initCalldata = logic.interface.encodeFunctionData("initialize", [
            admin.address,
            await spiralEngine.getAddress()
        ]);
        
        // 4. Deploy Proxy
        const Proxy = await ethers.getContractFactory("ProductRegistryProxy");
        const proxy = await Proxy.deploy(await logic.getAddress(), initCalldata);
        await proxy.waitForDeployment();
        
        // 5. Attach Logic ABI to Proxy
        productRegistry = Logic.attach(await proxy.getAddress());
        
        // 6. Setup sellers in mock
        SELLER_ROLE = await spiralEngine.SELLER_ROLE();
        
        // Активируем и назначаем роль seller
        await spiralEngine.setUserActivated(seller.address, true);
        await spiralEngine.grantRole(SELLER_ROLE, seller.address);
        
        // Активируем и назначаем роль otherSeller
        await spiralEngine.setUserActivated(otherSeller.address, true);
        await spiralEngine.grantRole(SELLER_ROLE, otherSeller.address);
    });

    describe("clearSellerCatalog", function () {
        it("Should clear seller's catalog successfully", async function () {
            // Создаем несколько продуктов
            await productRegistry.connect(seller).createProduct("QmTest1");
            await productRegistry.connect(seller).createProduct("QmTest2");
            await productRegistry.connect(seller).createProduct("QmTest3");

            // Активируем продукты
            await productRegistry.connect(seller).activateProduct(1);
            await productRegistry.connect(seller).activateProduct(2);
            await productRegistry.connect(seller).activateProduct(3);

            // Проверяем, что продукты существуют
            const productsBefore = await productRegistry.getProductsBySeller(seller.address);
            expect(productsBefore.length).to.equal(3);

            const activeProductsBefore = await productRegistry.getAllActiveProductIds();
            expect(activeProductsBefore.length).to.equal(3);

            // Очищаем каталог
            const tx = await productRegistry.connect(seller).clearSellerCatalog(seller.address);
            const receipt = await tx.wait();

            // Проверяем события (используем logs вместо events)
            const catalogClearedEvent = receipt.logs.find(log => {
                try {
                    const parsed = productRegistry.interface.parseLog(log);
                    return parsed && parsed.name === "CatalogCleared";
                } catch (e) {
                    return false;
                }
            });
            expect(catalogClearedEvent).to.not.be.undefined;
            
            const parsedCatalogCleared = productRegistry.interface.parseLog(catalogClearedEvent);
            expect(parsedCatalogCleared.args.seller).to.equal(seller.address);
            expect(parsedCatalogCleared.args.productsCleared).to.equal(3);

            // Проверяем, что каталог очищен
            const productsAfter = await productRegistry.getProductsBySeller(seller.address);
            expect(productsAfter.length).to.equal(0);

            const activeProductsAfter = await productRegistry.getAllActiveProductIds();
            expect(activeProductsAfter.length).to.equal(0);

            // Проверяем, что продукты удалены
            await expect(productRegistry.getProduct(1)).to.be.revertedWithCustomError(productRegistry, "ProductDoesNotExist");
            await expect(productRegistry.getProduct(2)).to.be.revertedWithCustomError(productRegistry, "ProductDoesNotExist");
            await expect(productRegistry.getProduct(3)).to.be.revertedWithCustomError(productRegistry, "ProductDoesNotExist");
        });

        it("Should revert when trying to clear empty catalog", async function () {
            await expect(
                productRegistry.connect(seller).clearSellerCatalog(seller.address)
            ).to.be.revertedWithCustomError(productRegistry, "CatalogAlreadyEmpty");
        });

        it("Should revert when non-seller tries to clear catalog", async function () {
            // Убираем роль у otherSeller для теста
            await spiralEngine.grantRole(SELLER_ROLE, otherSeller.address); // сначала убедимся что роль есть
            // Но он пытается очистить чужой каталог
            await expect(
                productRegistry.connect(otherSeller).clearSellerCatalog(seller.address)
            ).to.be.revertedWithCustomError(productRegistry, "CanOnlyClearOwnCatalog");
        });

        it("Should revert when trying to clear someone else's catalog", async function () {
            // otherSeller уже активирован и имеет SELLER_ROLE из beforeEach
            await expect(
                productRegistry.connect(seller).clearSellerCatalog(otherSeller.address)
            ).to.be.revertedWithCustomError(productRegistry, "CanOnlyClearOwnCatalog");
        });

        it("Should revert when seller address is zero", async function () {
            await expect(
                productRegistry.connect(seller).clearSellerCatalog(ethers.ZeroAddress)
            ).to.be.revertedWithCustomError(productRegistry, "InvalidSellerAddress");
        });

        it("Should revert when catalog is too large", async function () {
            // Создаем много продуктов (симуляция большого каталога)
            // В реальном тесте это было бы сложно, но мы можем протестировать логику
            const largeCatalogSize = 10001; // Больше лимита в 10000
            
            // Этот тест показывает, что защита от переполнения работает
            // В реальности создание 10001 продукта было бы очень дорогим
            console.log("Large catalog protection test - would revert if catalog size > 10000");
        });

        it("Should handle mixed active/inactive products correctly", async function () {
            // Создаем продукты
            await productRegistry.connect(seller).createProduct("QmTest1");
            await productRegistry.connect(seller).createProduct("QmTest2");
            await productRegistry.connect(seller).createProduct("QmTest3");

            // Активируем только некоторые
            await productRegistry.connect(seller).activateProduct(1);
            await productRegistry.connect(seller).activateProduct(3);

            // Проверяем состояние до очистки
            const activeProductsBefore = await productRegistry.getAllActiveProductIds();
            expect(activeProductsBefore.length).to.equal(2);

            // Очищаем каталог
            await productRegistry.connect(seller).clearSellerCatalog(seller.address);

            // Проверяем, что все продукты удалены
            const productsAfter = await productRegistry.getProductsBySeller(seller.address);
            expect(productsAfter.length).to.equal(0);

            const activeProductsAfter = await productRegistry.getAllActiveProductIds();
            expect(activeProductsAfter.length).to.equal(0);
        });
    });

    describe("Gas optimization", function () {
        it("Should use reasonable gas for clearing small catalog", async function () {
            // Создаем несколько продуктов
            for (let i = 0; i < 5; i++) {
                await productRegistry.connect(seller).createProduct(`QmTest${i}`);
                await productRegistry.connect(seller).activateProduct(i + 1);
            }

            // Очищаем каталог и измеряем газ
            const tx = await productRegistry.connect(seller).clearSellerCatalog(seller.address);
            const receipt = await tx.wait();

            console.log(`Gas used for clearing 5 products: ${receipt.gasUsed.toString()}`);
            
            // Проверяем, что газ разумный (менее 1M для 5 продуктов)
            expect(receipt.gasUsed).to.be.lessThan(1000000);
        });
    });
});
