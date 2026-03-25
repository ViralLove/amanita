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

describe("UUPS post-upgrade pause/safety continuity", function () {
    let admin;
    let userA;

    beforeEach(async function () {
        [admin, userA] = await ethers.getSigners();
    });

    it("SpiralEngine keeps pause guard after upgrade", async function () {
        const Logic = await ethers.getContractFactory("SpiralEngineLogic");
        const v1 = await Logic.deploy();
        await v1.waitForDeployment();
        const init = v1.interface.encodeFunctionData("initialize", [admin.address]);
        const Proxy = await ethers.getContractFactory("SpiralEngineProxy");
        const proxy = await Proxy.deploy(await v1.getAddress(), init);
        await proxy.waitForDeployment();
        const spiral = Logic.attach(await proxy.getAddress());

        await spiral.connect(admin).grantRole(await spiral.SELLER_ROLE(), userA.address);
        await spiral.connect(userA).mintInvite("SAFE-SP-1", 0);

        const v2 = await Logic.deploy();
        await v2.waitForDeployment();
        await spiral.connect(admin).upgradeToAndCall(await v2.getAddress(), "0x");

        await spiral.connect(admin).pause();
        await expectCustomError(spiral.connect(userA).mintInvite("SAFE-SP-2", 0), spiral, "EnforcedPause");
        await spiral.connect(admin).unpause();
        await spiral.connect(userA).mintInvite("SAFE-SP-2", 0);
        expect(await spiral.inviteCodeExists("SAFE-SP-2")).to.equal(true);
    });

    it("ProductRegistry keeps pause guard after upgrade", async function () {
        const SpiralMock = await ethers.getContractFactory("contracts/mocks/MockSpiralEngine.sol:MockSpiralEngine");
        const spiral = await SpiralMock.deploy();
        await spiral.waitForDeployment();
        await spiral.setUserActivated(userA.address, true);
        await spiral.grantRole(await spiral.SELLER_ROLE(), userA.address);

        const OCRLogic = await ethers.getContractFactory("OrganicComponentRegistryLogic");
        const ocrV1 = await OCRLogic.deploy();
        await ocrV1.waitForDeployment();
        const ocrInit = ocrV1.interface.encodeFunctionData("initialize", [admin.address]);
        const OCRProxy = await ethers.getContractFactory("OrganicComponentRegistryProxy");
        const ocrProxy = await OCRProxy.deploy(await ocrV1.getAddress(), ocrInit);
        await ocrProxy.waitForDeployment();
        const ocr = OCRLogic.attach(await ocrProxy.getAddress());
        await ocr.connect(admin).setSpiralEngine(await spiral.getAddress());
        await ocr.connect(admin).grantRole(await ocr.CONTRIBUTOR_ROLE(), userA.address);
        await ocr.connect(userA).createComponent("safe-pr-comp", "QmSafeComp");

        const PRLogic = await ethers.getContractFactory("ProductRegistryLogic");
        const prV1 = await PRLogic.deploy();
        await prV1.waitForDeployment();
        const prInit = prV1.interface.encodeFunctionData("initialize", [admin.address, await spiral.getAddress()]);
        const PRProxy = await ethers.getContractFactory("ProductRegistryProxy");
        const prProxy = await PRProxy.deploy(await prV1.getAddress(), prInit);
        await prProxy.waitForDeployment();
        const registry = PRLogic.attach(await prProxy.getAddress());
        await registry.connect(admin).setOrganicComponentRegistry(await ocr.getAddress());

        await registry.connect(userA).createProduct("safe-pr-1", ["safe-pr-comp"], "QmSafePr1");
        const prV2 = await PRLogic.deploy();
        await prV2.waitForDeployment();
        await registry.connect(admin).upgradeToAndCall(await prV2.getAddress(), "0x");

        await registry.connect(admin).pause();
        await expectCustomError(
            registry.connect(userA).createProduct("safe-pr-2", ["safe-pr-comp"], "QmSafePr2"),
            registry,
            "EnforcedPause"
        );
        await registry.connect(admin).unpause();
        await registry.connect(userA).createProduct("safe-pr-2", ["safe-pr-comp"], "QmSafePr2");
        expect(await registry.getProductIdByBusinessId("safe-pr-2")).to.equal(2n);
    });

    it("OrganicComponentRegistry keeps pause guard after upgrade", async function () {
        const SpiralEngineMock = await ethers.getContractFactory("SpiralEngineMock");
        const spiral = await SpiralEngineMock.deploy();
        await spiral.waitForDeployment();
        await spiral.grantRole(await spiral.ACTIVATOR_ROLE(), admin.address);
        await spiral.grantRole(await spiral.SELLER_ROLE(), userA.address);
        await spiral.connect(admin).activateUser(userA.address, 1);

        const Logic = await ethers.getContractFactory("OrganicComponentRegistryLogic");
        const v1 = await Logic.deploy();
        await v1.waitForDeployment();
        const init = v1.interface.encodeFunctionData("initialize", [admin.address]);
        const Proxy = await ethers.getContractFactory("OrganicComponentRegistryProxy");
        const proxy = await Proxy.deploy(await v1.getAddress(), init);
        await proxy.waitForDeployment();
        const registry = Logic.attach(await proxy.getAddress());
        await registry.connect(admin).setSpiralEngine(await spiral.getAddress());
        await registry.connect(admin).grantRole(await registry.CONTRIBUTOR_ROLE(), userA.address);

        await registry.connect(userA).createComponent("safe-ocr-1", "QmSafeOcr1");
        const v2 = await Logic.deploy();
        await v2.waitForDeployment();
        await registry.connect(admin).upgradeToAndCall(await v2.getAddress(), "0x");

        await registry.connect(admin).pause();
        await expectCustomError(registry.connect(userA).createComponent("safe-ocr-2", "QmSafeOcr2"), registry, "EnforcedPause");
        await registry.connect(admin).unpause();
        await registry.connect(userA).createComponent("safe-ocr-2", "QmSafeOcr2");
        expect(await registry.businessIdToComponentId("safe-ocr-2")).to.equal(2n);
    });

    it("AmanitaInternational keeps pause guard after upgrade", async function () {
        const SpiralMock = await ethers.getContractFactory("contracts/mocks/MockSpiralEngine.sol:MockSpiralEngine");
        const spiral = await SpiralMock.deploy();
        await spiral.waitForDeployment();
        await spiral.grantRole(await spiral.SELLER_ROLE(), userA.address);

        const Logic = await ethers.getContractFactory("AmanitaInternationalLogic");
        const v1 = await Logic.deploy();
        await v1.waitForDeployment();
        const init = v1.interface.encodeFunctionData("initialize", [admin.address, await spiral.getAddress()]);
        const Proxy = await ethers.getContractFactory("AmanitaInternationalProxy");
        const proxy = await Proxy.deploy(await v1.getAddress(), init);
        await proxy.waitForDeployment();
        const intl = Logic.attach(await proxy.getAddress());

        await intl.connect(userA).setSimpleFieldCID("safe.intl.1", "QmSafeIntl1");
        const v2 = await Logic.deploy();
        await v2.waitForDeployment();
        await intl.connect(admin).upgradeToAndCall(await v2.getAddress(), "0x");

        await intl.connect(admin).pause();
        await expectCustomError(intl.connect(userA).setSimpleFieldCID("safe.intl.2", "QmSafeIntl2"), intl, "EnforcedPause");
        await intl.connect(admin).unpause();
        await intl.connect(userA).setSimpleFieldCID("safe.intl.2", "QmSafeIntl2");
        expect(await intl.getSimpleFieldCID("safe.intl.2")).to.equal("QmSafeIntl2");
    });
});

