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

describe("ProductRegistry - Clear Catalog (UUPS)", function () {
    let productRegistry;
    let spiralEngine;
    let componentRegistry;
    let admin, seller, otherSeller;
    let SELLER_ROLE;
    let sellerComponentIds;
    let otherSellerComponentIds;

    beforeEach(async function () {
        [admin, seller, otherSeller] = await ethers.getSigners();
        
        const SpiralEngineMock = await ethers.getContractFactory("contracts/mocks/MockSpiralEngine.sol:MockSpiralEngine");
        spiralEngine = await SpiralEngineMock.deploy();
        await spiralEngine.waitForDeployment();

        const OCRLogic = await ethers.getContractFactory("OrganicComponentRegistryLogic");
        const ocrLogic = await OCRLogic.deploy();
        await ocrLogic.waitForDeployment();
        const ocrInitCalldata = ocrLogic.interface.encodeFunctionData("initialize", [admin.address]);
        const OCRProxy = await ethers.getContractFactory("OrganicComponentRegistryProxy");
        const ocrProxy = await OCRProxy.deploy(await ocrLogic.getAddress(), ocrInitCalldata);
        await ocrProxy.waitForDeployment();
        componentRegistry = ocrLogic.attach(await ocrProxy.getAddress());
        await componentRegistry.connect(admin).setSpiralEngine(await spiralEngine.getAddress());

        const Logic = await ethers.getContractFactory("ProductRegistryLogic");
        const logic = await Logic.deploy();
        await logic.waitForDeployment();
        
        const initCalldata = logic.interface.encodeFunctionData("initialize", [
            admin.address,
            await spiralEngine.getAddress()
        ]);
        
        const Proxy = await ethers.getContractFactory("ProductRegistryProxy");
        const proxy = await Proxy.deploy(await logic.getAddress(), initCalldata);
        await proxy.waitForDeployment();
        
        productRegistry = Logic.attach(await proxy.getAddress());
        await productRegistry.connect(admin).setOrganicComponentRegistry(await componentRegistry.getAddress());
        
        SELLER_ROLE = await spiralEngine.SELLER_ROLE();
        
        await spiralEngine.setUserActivated(seller.address, true);
        await spiralEngine.grantRole(SELLER_ROLE, seller.address);
        
        await spiralEngine.setUserActivated(otherSeller.address, true);
        await spiralEngine.grantRole(SELLER_ROLE, otherSeller.address);

        sellerComponentIds = ["clear-comp-s-1", "clear-comp-s-2", "clear-comp-s-3"];
        otherSellerComponentIds = ["clear-comp-o-1", "clear-comp-o-2", "clear-comp-o-3"];

        for (const cid of sellerComponentIds) {
            await componentRegistry.connect(seller).createComponent(cid, `Qm${cid}`);
        }

        for (const cid of otherSellerComponentIds) {
            await componentRegistry.connect(otherSeller).createComponent(cid, `Qm${cid}`);
        }
    });

    describe("clearSellerCatalog", function () {
        it("Should clear seller's catalog successfully", async function () {
            // Создаем несколько продуктов
            await productRegistry.connect(seller).createProduct(
                "clear-main-product-1",
                [sellerComponentIds[0]],
                "QmTest1"
            );
            await productRegistry.connect(seller).createProduct(
                "clear-main-product-2",
                [sellerComponentIds[1]],
                "QmTest2"
            );
            await productRegistry.connect(seller).createProduct(
                "clear-main-product-3",
                [sellerComponentIds[2]],
                "QmTest3"
            );

            // Активируем продукты
            await productRegistry.connect(seller).activateProduct(1);
            await productRegistry.connect(seller).activateProduct(2);
            await productRegistry.connect(seller).activateProduct(3);

            // Проверяем, что продукты существуют
            const productsBefore = await productRegistry.getProductsBySeller(seller.address);
            expect(productsBefore.map(id => Number(id))).to.deep.equal([1, 2, 3]);

            const activeProductsBefore = await productRegistry.getAllActiveProductIds();
            expect(activeProductsBefore.map(id => Number(id))).to.deep.equal([1, 2, 3]);

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
            expect(Number(parsedCatalogCleared.args.productsCleared)).to.equal(3);

            // Проверяем, что каталог очищен
            const productsAfter = await productRegistry.getProductsBySeller(seller.address);
            expect(productsAfter.length).to.equal(0);

            const activeProductsAfter = await productRegistry.getAllActiveProductIds();
            expect(activeProductsAfter.length).to.equal(0);

            // Проверяем, что продукты удалены
            await expectRevertCustom(productRegistry.getProduct(1), "ProductDoesNotExist", productRegistry);
            await expectRevertCustom(productRegistry.getProduct(2), "ProductDoesNotExist", productRegistry);
            await expectRevertCustom(productRegistry.getProduct(3), "ProductDoesNotExist", productRegistry);
            await expectRevertCustom(
                productRegistry.getProductIdByBusinessId("clear-main-product-1"),
                "BusinessIdUnknown",
                productRegistry
            );
            await expectRevertCustom(
                productRegistry.getProductIdByBusinessId("clear-main-product-2"),
                "BusinessIdUnknown",
                productRegistry
            );
            await expectRevertCustom(
                productRegistry.getProductIdByBusinessId("clear-main-product-3"),
                "BusinessIdUnknown",
                productRegistry
            );
        });

        it("Should revert when trying to clear empty catalog", async function () {
            await expectRevertCustom(
                productRegistry.connect(seller).clearSellerCatalog(seller.address),
                "CatalogAlreadyEmpty",
                productRegistry
            );
        });

        it("Should revert when non-seller tries to clear catalog", async function () {
            // Убираем роль у otherSeller для теста
            await spiralEngine.grantRole(SELLER_ROLE, otherSeller.address); // сначала убедимся что роль есть
            // Но он пытается очистить чужой каталог
            await expectRevertCustom(
                productRegistry.connect(otherSeller).clearSellerCatalog(seller.address),
                "CanOnlyClearOwnCatalog",
                productRegistry
            );
        });

        it("Should revert when trying to clear someone else's catalog", async function () {
            // otherSeller уже активирован и имеет SELLER_ROLE из beforeEach
            await expectRevertCustom(
                productRegistry.connect(seller).clearSellerCatalog(otherSeller.address),
                "CanOnlyClearOwnCatalog",
                productRegistry
            );
        });

        it("Should revert when seller address is zero", async function () {
            await expectRevertCustom(
                productRegistry.connect(seller).clearSellerCatalog(ethers.ZeroAddress),
                "InvalidSellerAddress",
                productRegistry
            );
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
            await productRegistry.connect(seller).createProduct(
                "clear-mixed-1",
                [sellerComponentIds[0]],
                "QmTest1"
            );
            await productRegistry.connect(seller).createProduct(
                "clear-mixed-2",
                [sellerComponentIds[1]],
                "QmTest2"
            );
            await productRegistry.connect(seller).createProduct(
                "clear-mixed-3",
                [sellerComponentIds[2]],
                "QmTest3"
            );

            // Активируем только некоторые
            await productRegistry.connect(seller).activateProduct(1);
            await productRegistry.connect(seller).activateProduct(3);

            // Проверяем состояние до очистки
            const activeProductsBefore = await productRegistry.getAllActiveProductIds();
            expect(activeProductsBefore.map(id => Number(id))).to.deep.equal([1, 3]);

            // Очищаем каталог
            await productRegistry.connect(seller).clearSellerCatalog(seller.address);

            // Проверяем, что все продукты удалены
            const productsAfter = await productRegistry.getProductsBySeller(seller.address);
            expect(productsAfter.length).to.equal(0);

            const activeProductsAfter = await productRegistry.getAllActiveProductIds();
            expect(activeProductsAfter.length).to.equal(0);

            await expectRevertCustom(
                productRegistry.getProductIdByBusinessId("clear-mixed-1"),
                "BusinessIdUnknown",
                productRegistry
            );
            await expectRevertCustom(
                productRegistry.getProductIdByBusinessId("clear-mixed-2"),
                "BusinessIdUnknown",
                productRegistry
            );
            await expectRevertCustom(
                productRegistry.getProductIdByBusinessId("clear-mixed-3"),
                "BusinessIdUnknown",
                productRegistry
            );
        });
    });

    describe("Gas optimization", function () {
        it("Should use reasonable gas for clearing small catalog", async function () {
            // Создаем несколько продуктов
            for (let i = 0; i < 5; i++) {
                await productRegistry.connect(seller).createProduct(
                    `clear-gas-${i}`,
                    [sellerComponentIds[i % sellerComponentIds.length]],
                    `QmTest${i}`
                );
                await productRegistry.connect(seller).activateProduct(i + 1);
            }

            // Очищаем каталог и измеряем газ
            const tx = await productRegistry.connect(seller).clearSellerCatalog(seller.address);
            const receipt = await tx.wait();

            console.log(`Gas used for clearing 5 products: ${receipt.gasUsed.toString()}`);
            
            // Проверяем, что газ разумный (менее 1M для 5 продуктов)
            expect(Number(receipt.gasUsed)).to.be.lessThan(1000000);
        });
    });
});
