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

async function expectNotReverted(txPromise, failureMessage = "Транзакция не должна была ревертиться") {
    try {
        await txPromise;
    } catch (error) {
        expect.fail(`${failureMessage}: ${error?.message || error}`);
    }
}

describe("ProductRegistry - Clear Catalog Simple (UUPS)", function () {
    let productRegistry;
    let spiralEngine;
    let componentRegistry;
    let admin, seller;
    let SELLER_ROLE;
    let sellerComponentIds;

    beforeEach(async function () {
        [admin, seller] = await ethers.getSigners();
        
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

        sellerComponentIds = ["clear-simple-comp-1", "clear-simple-comp-2", "clear-simple-comp-3"];
        for (const componentId of sellerComponentIds) {
            await componentRegistry.connect(seller).createComponent(componentId, `Qm${componentId}`);
        }
    });

    describe("clearSellerCatalog", function () {
        it("Should clear seller's catalog successfully", async function () {
            console.log("Testing clearSellerCatalog function...");
            console.log("Seller address:", seller.address);
            console.log("Admin address:", admin.address);

            // Создаём три продукта c бизнес-ID
            await productRegistry.connect(seller).createProduct(
                "clear-simple-product-1",
                [sellerComponentIds[0]],
                "QmTest1"
            );
            await productRegistry.connect(seller).createProduct(
                "clear-simple-product-2",
                [sellerComponentIds[1]],
                "QmTest2"
            );
            await productRegistry.connect(seller).createProduct(
                "clear-simple-product-3",
                [sellerComponentIds[2]],
                "QmTest3"
            );

            await productRegistry.connect(seller).activateProduct(1);
            await productRegistry.connect(seller).activateProduct(2);
            await productRegistry.connect(seller).activateProduct(3);

            const productsBefore = await productRegistry.getProductsBySeller(seller.address);
            const activeBefore = await productRegistry.getAllActiveProductIds();
            expect(productsBefore.map(id => Number(id))).to.deep.equal([1, 2, 3]);
            expect(activeBefore.map(id => Number(id))).to.deep.equal([1, 2, 3]);

            await expectEvent(
                productRegistry.connect(seller).clearSellerCatalog(seller.address),
                productRegistry,
                "CatalogCleared",
                args => {
                    expect(args.seller).to.equal(seller.address);
                    expect(Number(args.productsCleared)).to.equal(3);
                }
            );

            const sellerCatalogAfter = await productRegistry.getProductsBySeller(seller.address);
            const activeProductsAfter = await productRegistry.getAllActiveProductIds();
            const fullCatalogAfter = await productRegistry.connect(seller).getProductsBySellerFull();

            expect(sellerCatalogAfter.length).to.equal(0);
            expect(activeProductsAfter.length).to.equal(0);
            expect(fullCatalogAfter.length).to.equal(0);

            await expectRevertCustom(productRegistry.getProduct(1), "ProductDoesNotExist", productRegistry);
            await expectRevertCustom(productRegistry.getProduct(2), "ProductDoesNotExist", productRegistry);
            await expectRevertCustom(productRegistry.getProduct(3), "ProductDoesNotExist", productRegistry);
            await expectRevertCustom(
                productRegistry.getProductIdByBusinessId("clear-simple-product-1"),
                "BusinessIdUnknown",
                productRegistry
            );
            await expectRevertCustom(
                productRegistry.getProductIdByBusinessId("clear-simple-product-2"),
                "BusinessIdUnknown",
                productRegistry
            );
            await expectRevertCustom(
                productRegistry.getProductIdByBusinessId("clear-simple-product-3"),
                "BusinessIdUnknown",
                productRegistry
            );

            expect(Number(await productRegistry.connect(seller).getMyCatalogVersion())).to.equal(7);
        });

        it("Should have proper access control", async function () {
            // Проверяем, что функция требует правильные модификаторы
            // Seller уже активирован, поэтому попытка очистить пустой каталог вернёт CatalogAlreadyEmpty
            await expectRevertCustom(
                productRegistry.connect(seller).clearSellerCatalog(seller.address),
                "CatalogAlreadyEmpty",
                productRegistry
            );
            
            // Admin не имеет SELLER_ROLE, поэтому получит NotASeller
            await expectRevertCustom(
                productRegistry.connect(admin).clearSellerCatalog(seller.address),
                "NotASeller",
                productRegistry
            );
        });

    });

    describe("Contract compilation and deployment", function () {
        it("Should compile without errors", async function () {
            // Проверяем, что контракты скомпилированы
            const Logic = await ethers.getContractFactory("ProductRegistryLogic");
            const Proxy = await ethers.getContractFactory("ProductRegistryProxy");
            
            expect(Logic).to.not.be.undefined;
            expect(Proxy).to.not.be.undefined;
            
            const fragments = productRegistry.interface.fragments;
            expect(fragments.length).to.be.greaterThan(0);
        });

        it("Should have correct UUPS architecture", async function () {
            // Проверяем версию Logic
            expect(Number(await productRegistry.LOGIC_VERSION())).to.equal(1);
            
            // Проверяем, что Proxy делегирует к Logic
            const proxyAddress = await productRegistry.getAddress();
            expect(proxyAddress).to.match(/^0x[a-fA-F0-9]{40}$/);
        });
    });
});
