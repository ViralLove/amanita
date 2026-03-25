const { expect } = require("chai");
const { ethers } = require("hardhat");

function implSlot() {
    return "0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc";
}

async function getImplementation(proxyAddress) {
    const raw = await ethers.provider.getStorage(proxyAddress, implSlot());
    return `0x${raw.slice(-40)}`.toLowerCase();
}

describe("UUPS portfolio invariants harness", function () {
    let admin;
    let userA;
    let userB;

    beforeEach(async function () {
        [admin, userA, userB] = await ethers.getSigners();
    });

    it("SpiralEngine: keeps state marker and role continuity across upgrade", async function () {
        const Logic = await ethers.getContractFactory("SpiralEngineLogic");
        const logicV1 = await Logic.deploy();
        await logicV1.waitForDeployment();
        const init = logicV1.interface.encodeFunctionData("initialize", [admin.address]);

        const Proxy = await ethers.getContractFactory("SpiralEngineProxy");
        const proxy = await Proxy.deploy(await logicV1.getAddress(), init);
        await proxy.waitForDeployment();
        const spiral = Logic.attach(await proxy.getAddress());

        const SELLER_ROLE = await spiral.SELLER_ROLE();
        const UPGRADER_ROLE = await spiral.UPGRADER_ROLE();
        await spiral.connect(admin).grantRole(SELLER_ROLE, userA.address);
        await spiral.connect(userA).mintInvite("UUPS-SPIRAL", 0);

        const beforeImpl = await getImplementation(await proxy.getAddress());
        expect(await spiral.totalInvitesMinted()).to.equal(1n);
        expect(await spiral.inviteCodeExists("UUPS-SPIRAL")).to.equal(true);
        expect(await spiral.hasRole(UPGRADER_ROLE, admin.address)).to.equal(true);

        const logicV2 = await Logic.deploy();
        await logicV2.waitForDeployment();
        await spiral.connect(admin).upgradeToAndCall(await logicV2.getAddress(), "0x");

        const afterImpl = await getImplementation(await proxy.getAddress());
        expect(afterImpl).to.not.equal(beforeImpl);
        expect(await spiral.totalInvitesMinted()).to.equal(1n);
        expect(await spiral.inviteCodeExists("UUPS-SPIRAL")).to.equal(true);
        expect(await spiral.hasRole(UPGRADER_ROLE, admin.address)).to.equal(true);
    });

    it("ProductRegistry: preserves seller catalog marker after upgrade", async function () {
        const SpiralMockFactory = await ethers.getContractFactory("contracts/mocks/MockSpiralEngine.sol:MockSpiralEngine");
        const spiralMock = await SpiralMockFactory.deploy();
        await spiralMock.waitForDeployment();

        const OCRLogicFactory = await ethers.getContractFactory("OrganicComponentRegistryLogic");
        const ocrLogic = await OCRLogicFactory.deploy();
        await ocrLogic.waitForDeployment();
        const ocrInit = ocrLogic.interface.encodeFunctionData("initialize", [admin.address]);
        const OCRProxy = await ethers.getContractFactory("OrganicComponentRegistryProxy");
        const ocrProxy = await OCRProxy.deploy(await ocrLogic.getAddress(), ocrInit);
        await ocrProxy.waitForDeployment();
        const ocr = OCRLogicFactory.attach(await ocrProxy.getAddress());
        await ocr.connect(admin).setSpiralEngine(await spiralMock.getAddress());

        const PRLogicFactory = await ethers.getContractFactory("ProductRegistryLogic");
        const prLogicV1 = await PRLogicFactory.deploy();
        await prLogicV1.waitForDeployment();
        const prInit = prLogicV1.interface.encodeFunctionData("initialize", [admin.address, await spiralMock.getAddress()]);
        const PRProxy = await ethers.getContractFactory("ProductRegistryProxy");
        const prProxy = await PRProxy.deploy(await prLogicV1.getAddress(), prInit);
        await prProxy.waitForDeployment();
        const productRegistry = PRLogicFactory.attach(await prProxy.getAddress());
        await productRegistry.connect(admin).setOrganicComponentRegistry(await ocr.getAddress());

        const SELLER_ROLE = await spiralMock.SELLER_ROLE();
        await spiralMock.setUserActivated(userA.address, true);
        await spiralMock.grantRole(SELLER_ROLE, userA.address);
        await ocr.connect(admin).grantRole(await ocr.CONTRIBUTOR_ROLE(), userA.address);
        await ocr.connect(userA).createComponent("uups-pr-comp", "QmUupsPrComp");
        await productRegistry.connect(userA).createProduct("uups-pr-product", ["uups-pr-comp"], "QmUupsPrProduct");

        const beforeImpl = await getImplementation(await prProxy.getAddress());
        expect(await productRegistry.getProductIdByBusinessId("uups-pr-product")).to.equal(1n);
        expect((await productRegistry.getProductsBySeller(userA.address)).length).to.equal(1);

        const prLogicV2 = await PRLogicFactory.deploy();
        await prLogicV2.waitForDeployment();
        await productRegistry.connect(admin).upgradeToAndCall(await prLogicV2.getAddress(), "0x");

        const afterImpl = await getImplementation(await prProxy.getAddress());
        expect(afterImpl).to.not.equal(beforeImpl);
        expect(await productRegistry.getProductIdByBusinessId("uups-pr-product")).to.equal(1n);
        expect((await productRegistry.getProductsBySeller(userA.address)).length).to.equal(1);
    });

    it("ActivityRegistry: preserves creator activity marker after upgrade", async function () {
        const SpiralMockFactory = await ethers.getContractFactory("contracts/mocks/MockSpiralEngine.sol:MockSpiralEngine");
        const spiralMock = await SpiralMockFactory.deploy();
        await spiralMock.waitForDeployment();
        const ACTIVATOR_ROLE = await spiralMock.ACTIVATOR_ROLE();
        await spiralMock.grantRole(ACTIVATOR_ROLE, userA.address);
        await spiralMock.setUserActivated(userA.address, true);

        const LogicFactory = await ethers.getContractFactory("ActivityRegistryLogic");
        const logicV1 = await LogicFactory.deploy();
        await logicV1.waitForDeployment();
        const init = logicV1.interface.encodeFunctionData("initialize", [admin.address, await spiralMock.getAddress()]);
        const Proxy = await ethers.getContractFactory("ActivityRegistryProxy");
        const proxy = await Proxy.deploy(await logicV1.getAddress(), init);
        await proxy.waitForDeployment();
        const activity = LogicFactory.attach(await proxy.getAddress());

        await activity.connect(userA).createActivity(0, "QmUupsActivity");
        const beforeImpl = await getImplementation(await proxy.getAddress());
        expect((await activity.getActivitiesByCreator(userA.address)).length).to.equal(1);

        const logicV2 = await LogicFactory.deploy();
        await logicV2.waitForDeployment();
        await activity.connect(admin).upgradeToAndCall(await logicV2.getAddress(), "0x");

        const afterImpl = await getImplementation(await proxy.getAddress());
        expect(afterImpl).to.not.equal(beforeImpl);
        expect((await activity.getActivitiesByCreator(userA.address)).length).to.equal(1);
        expect((await activity.getActivity(1)).metadataCID).to.equal("QmUupsActivity");
    });

    it("OrganicComponentRegistry: preserves component marker and roles after upgrade", async function () {
        const SpiralEngineMock = await ethers.getContractFactory("SpiralEngineMock");
        const spiral = await SpiralEngineMock.deploy();
        await spiral.waitForDeployment();
        await spiral.grantRole(await spiral.ACTIVATOR_ROLE(), admin.address);
        await spiral.grantRole(await spiral.SELLER_ROLE(), userA.address);
        await spiral.connect(admin).activateUser(userA.address, 1);

        const LogicFactory = await ethers.getContractFactory("OrganicComponentRegistryLogic");
        const logicV1 = await LogicFactory.deploy();
        await logicV1.waitForDeployment();
        const init = logicV1.interface.encodeFunctionData("initialize", [admin.address]);
        const Proxy = await ethers.getContractFactory("OrganicComponentRegistryProxy");
        const proxy = await Proxy.deploy(await logicV1.getAddress(), init);
        await proxy.waitForDeployment();
        const registry = LogicFactory.attach(await proxy.getAddress());
        await registry.connect(admin).setSpiralEngine(await spiral.getAddress());
        await registry.connect(admin).grantRole(await registry.CONTRIBUTOR_ROLE(), userA.address);

        await registry.connect(userA).createComponent("uups-ocr-comp", "QmUupsOcr");
        const beforeImpl = await getImplementation(await proxy.getAddress());
        expect(await registry.businessIdToComponentId("uups-ocr-comp")).to.equal(1n);
        expect(await registry.hasRole(await registry.CONTRIBUTOR_ROLE(), userA.address)).to.equal(true);

        const logicV2 = await LogicFactory.deploy();
        await logicV2.waitForDeployment();
        await registry.connect(admin).upgradeToAndCall(await logicV2.getAddress(), "0x");

        const afterImpl = await getImplementation(await proxy.getAddress());
        expect(afterImpl).to.not.equal(beforeImpl);
        expect(await registry.businessIdToComponentId("uups-ocr-comp")).to.equal(1n);
        expect(await registry.hasRole(await registry.CONTRIBUTOR_ROLE(), userA.address)).to.equal(true);
    });

    it("AmanitaInternational: preserves translation marker across upgrade", async function () {
        const SpiralMockFactory = await ethers.getContractFactory("contracts/mocks/MockSpiralEngine.sol:MockSpiralEngine");
        const spiral = await SpiralMockFactory.deploy();
        await spiral.waitForDeployment();
        const SELLER_ROLE = await spiral.SELLER_ROLE();
        await spiral.grantRole(SELLER_ROLE, userA.address);

        const LogicFactory = await ethers.getContractFactory("AmanitaInternationalLogic");
        const logicV1 = await LogicFactory.deploy();
        await logicV1.waitForDeployment();
        const init = logicV1.interface.encodeFunctionData("initialize", [admin.address, await spiral.getAddress()]);
        const Proxy = await ethers.getContractFactory("AmanitaInternationalProxy");
        const proxy = await Proxy.deploy(await logicV1.getAddress(), init);
        await proxy.waitForDeployment();
        const intl = LogicFactory.attach(await proxy.getAddress());

        await intl.connect(userA).setSimpleFieldCID("uups.intl.title", "QmIntlTitleV1");
        const beforeImpl = await getImplementation(await proxy.getAddress());
        const statsBefore = await intl.getStatistics();
        expect(await intl.getSimpleFieldCID("uups.intl.title")).to.equal("QmIntlTitleV1");
        expect(statsBefore.totalSimpleFields).to.equal(1n);

        const logicV2 = await LogicFactory.deploy();
        await logicV2.waitForDeployment();
        await intl.connect(admin).upgradeToAndCall(await logicV2.getAddress(), "0x");

        const afterImpl = await getImplementation(await proxy.getAddress());
        expect(afterImpl).to.not.equal(beforeImpl);
        expect(await intl.getSimpleFieldCID("uups.intl.title")).to.equal("QmIntlTitleV1");
        const statsAfter = await intl.getStatistics();
        expect(statsAfter.totalSimpleFields).to.equal(1n);
    });
});

