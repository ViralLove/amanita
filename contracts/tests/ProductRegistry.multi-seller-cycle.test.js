const { expect } = require("chai");
const { ethers } = require("hardhat");

async function expectCustomError(txPromise, contract, errorName) {
    let err;
    try {
        const tx = await txPromise;
        if (tx && typeof tx.wait === "function") await tx.wait();
    } catch (e) {
        err = e;
    }
    expect(err, "expected transaction to revert").to.be.ok;
    const selector = contract.interface.getError(errorName).selector.toLowerCase();
    const data = err?.data || err?.error?.data || err?.receipt || "";
    const hex = typeof data === "string" ? data.toLowerCase() : (data && data.toString ? data.toString().toLowerCase() : "");
    const msg = (err?.reason || err?.shortMessage || err?.message || err?.error?.message || String(err)).toLowerCase();
    const matched = hex.includes(selector) || msg.includes(errorName.toLowerCase()) || msg.includes(selector);
    expect(matched, `expected error ${errorName}`).to.equal(true);
}

describe("ProductRegistry multi-seller repeated lifecycle cycle", function () {
    let admin;
    let sellerA;
    let sellerB;
    let outsider;
    let productRegistry;
    let componentRegistry;
    let spiralEngine;
    let SELLER_ROLE;
    let CONTRIBUTOR_ROLE;

    beforeEach(async function () {
        [admin, sellerA, sellerB, outsider] = await ethers.getSigners();

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

        const PRLogic = await ethers.getContractFactory("ProductRegistryLogic");
        const prLogic = await PRLogic.deploy();
        await prLogic.waitForDeployment();
        const prInitCalldata = prLogic.interface.encodeFunctionData("initialize", [admin.address, await spiralEngine.getAddress()]);

        const PRProxy = await ethers.getContractFactory("ProductRegistryProxy");
        const prProxy = await PRProxy.deploy(await prLogic.getAddress(), prInitCalldata);
        await prProxy.waitForDeployment();
        productRegistry = prLogic.attach(await prProxy.getAddress());
        await productRegistry.connect(admin).setOrganicComponentRegistry(await componentRegistry.getAddress());

        SELLER_ROLE = await spiralEngine.SELLER_ROLE();
        CONTRIBUTOR_ROLE = await componentRegistry.CONTRIBUTOR_ROLE();

        for (const seller of [sellerA, sellerB]) {
            await spiralEngine.setUserActivated(seller.address, true);
            await spiralEngine.grantRole(SELLER_ROLE, seller.address);
            await componentRegistry.grantRole(CONTRIBUTOR_ROLE, seller.address);
        }

        await componentRegistry.connect(sellerA).createComponent("a-comp-1", "QmA1");
        await componentRegistry.connect(sellerA).createComponent("a-comp-2", "QmA2");
        await componentRegistry.connect(sellerB).createComponent("b-comp-1", "QmB1");
        await componentRegistry.connect(sellerB).createComponent("b-comp-2", "QmB2");
    });

    it("keeps repeated lifecycle isolated per seller", async function () {
        // Seller A: create two products, activate both, update/deactivate/reactivate one.
        await productRegistry.connect(sellerA).createProduct("a-prod-1", ["a-comp-1"], "QmAProd1");
        await productRegistry.connect(sellerA).createProduct("a-prod-2", ["a-comp-2"], "QmAProd2");
        await productRegistry.connect(sellerA).activateProduct(1);
        await productRegistry.connect(sellerA).activateProduct(2);
        await productRegistry.connect(sellerA).updateProduct(1, "QmAProd1-v2", 100);
        await productRegistry.connect(sellerA).deactivateProduct(1);
        await productRegistry.connect(sellerA).activateProduct(1);

        // Seller B: create one product, activate then deactivate.
        await productRegistry.connect(sellerB).createProduct("b-prod-1", ["b-comp-1"], "QmBProd1");
        await productRegistry.connect(sellerB).activateProduct(3);
        await productRegistry.connect(sellerB).deactivateProduct(3);

        const sellerAProducts = await productRegistry.getProductsBySeller(sellerA.address);
        const sellerBProducts = await productRegistry.getProductsBySeller(sellerB.address);
        expect(sellerAProducts.map(String)).to.deep.equal(["1", "2"]);
        expect(sellerBProducts.map(String)).to.deep.equal(["3"]);

        const p1 = await productRegistry.getProduct(1);
        const p2 = await productRegistry.getProduct(2);
        const p3 = await productRegistry.getProduct(3);
        expect(p1.seller).to.equal(sellerA.address);
        expect(p2.seller).to.equal(sellerA.address);
        expect(p3.seller).to.equal(sellerB.address);
        expect(p1.active).to.equal(true);
        expect(p2.active).to.equal(true);
        expect(p3.active).to.equal(false);

        // Active index should contain only seller A products at this point.
        const activeIds = (await productRegistry.getAllActiveProductIds()).map((v) => Number(v));
        expect(activeIds.sort((a, b) => a - b)).to.deep.equal([1, 2]);
    });

    it("supports cleanup of one seller catalog without affecting other seller", async function () {
        await productRegistry.connect(sellerA).createProduct("a-clean-1", ["a-comp-1"], "QmAClean1");
        await productRegistry.connect(sellerA).createProduct("a-clean-2", ["a-comp-2"], "QmAClean2");
        await productRegistry.connect(sellerA).activateProduct(1);
        await productRegistry.connect(sellerA).activateProduct(2);

        await productRegistry.connect(sellerB).createProduct("b-survive-1", ["b-comp-1"], "QmBSurvive1");
        await productRegistry.connect(sellerB).activateProduct(3);

        await productRegistry.connect(sellerA).clearSellerCatalog(sellerA.address);

        await expectCustomError(productRegistry.getProductIdByBusinessId("a-clean-1"), productRegistry, "BusinessIdUnknown");
        await expectCustomError(productRegistry.getProductIdByBusinessId("a-clean-2"), productRegistry, "BusinessIdUnknown");
        await expectCustomError(productRegistry.getProduct(1), productRegistry, "ProductDoesNotExist");
        await expectCustomError(productRegistry.getProduct(2), productRegistry, "ProductDoesNotExist");

        const bProductId = await productRegistry.getProductIdByBusinessId("b-survive-1");
        expect(bProductId).to.equal(3n);
        const bProduct = await productRegistry.getProduct(3);
        expect(bProduct.seller).to.equal(sellerB.address);
        expect(bProduct.active).to.equal(true);

        const sellerAProducts = await productRegistry.getProductsBySeller(sellerA.address);
        const sellerBProducts = await productRegistry.getProductsBySeller(sellerB.address);
        expect(sellerAProducts.length).to.equal(0);
        expect(sellerBProducts.map(String)).to.deep.equal(["3"]);
    });

    it("enforces ownership boundaries for lifecycle actions across sellers", async function () {
        await productRegistry.connect(sellerA).createProduct("a-own-1", ["a-comp-1"], "QmOwn1");
        await productRegistry.connect(sellerA).activateProduct(1);

        await expectCustomError(productRegistry.connect(sellerB).updateProduct(1, "QmWrong", 100), productRegistry, "NotProductSeller");
        await expectCustomError(productRegistry.connect(sellerB).deactivateProduct(1), productRegistry, "NotProductSeller");
        await expectCustomError(productRegistry.connect(sellerB).activateProduct(1), productRegistry, "NotProductSeller");
        await expectCustomError(
            productRegistry.connect(outsider).clearSellerCatalog(sellerA.address),
            productRegistry,
            "NotASeller"
        );
    });
});

