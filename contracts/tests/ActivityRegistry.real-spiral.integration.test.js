const { expect } = require("chai");
const { ethers } = require("hardhat");

async function expectRevertCustom(txPromise, contract, errorName) {
    let err;
    try {
        const tx = await txPromise;
        if (tx && typeof tx.wait === "function") await tx.wait();
    } catch (e) {
        err = e;
    }
    expect(err, "expected transaction to revert").to.be.ok;
    const selector = contract.interface.getError(errorName).selector.toLowerCase();
    const haystack = [
        err?.data,
        err?.error?.data,
        err?.reason,
        err?.shortMessage,
        err?.message
    ]
        .map(v => (v == null ? "" : String(v).toLowerCase()))
        .join(" | ");
    expect(
        haystack.includes(selector) || haystack.includes(errorName.toLowerCase()),
        `expected custom error ${errorName}`
    ).to.be.true;
}

function makeCodes(prefix, n = 12) {
    return Array.from({ length: n }, (_, i) => `${prefix}-${i + 1}-${Date.now()}`);
}

describe("ActivityRegistry real SpiralEngine integration", function () {
    let admin;
    let creator;
    let notActivated;
    let sanctioned;

    let spiral;
    let registry;

    beforeEach(async function () {
        [admin] = await ethers.getSigners();
        creator = ethers.Wallet.createRandom().connect(ethers.provider);
        notActivated = ethers.Wallet.createRandom().connect(ethers.provider);
        sanctioned = ethers.Wallet.createRandom().connect(ethers.provider);

        for (const w of [creator, notActivated, sanctioned]) {
            await admin.sendTransaction({ to: w.address, value: ethers.parseEther("2") });
        }

        const SpiralEngine = await ethers.getContractFactory("SpiralEngine");
        spiral = await SpiralEngine.deploy();
        await spiral.waitForDeployment();

        const ActivityLogic = await ethers.getContractFactory("ActivityRegistryLogic");
        const logic = await ActivityLogic.deploy();
        await logic.waitForDeployment();

        const initCalldata = logic.interface.encodeFunctionData("initialize", [
            admin.address,
            await spiral.getAddress()
        ]);

        const ActivityProxy = await ethers.getContractFactory("ActivityRegistryProxy");
        const proxy = await ActivityProxy.deploy(await logic.getAddress(), initCalldata);
        await proxy.waitForDeployment();
        registry = ActivityLogic.attach(await proxy.getAddress());

        // Real spiral path: admin (default SELLER+ACTIVATOR) activates users.
        await spiral.connect(admin).mintInvite("INV-CREATOR", 0);
        await spiral.connect(admin).activateUser("INV-CREATOR", creator.address, makeCodes("CR"), 0);
        const ACTIVATOR_ROLE = await spiral.ACTIVATOR_ROLE();
        await spiral.connect(admin).grantRole(ACTIVATOR_ROLE, creator.address);

        await spiral.connect(admin).mintInvite("INV-SANCTIONED", 0);
        await spiral.connect(admin).activateUser("INV-SANCTIONED", sanctioned.address, makeCodes("SN"), 0);
        await spiral.connect(admin).grantRole(ACTIVATOR_ROLE, sanctioned.address);

        // Role-only user without activation (usedInviteByUser == 0).
        await spiral.connect(admin).grantRole(ACTIVATOR_ROLE, notActivated.address);
    });

    it("Should allow real activated creator with ACTIVATOR_ROLE to create and activate activity", async function () {
        await registry.connect(creator).createActivity(0, "QmRealSpiralCID");
        const ids = await registry.getActivitiesByCreator(creator.address);
        expect(ids.length).to.equal(1);
        expect(Number(ids[0])).to.equal(1);

        await registry.connect(creator).activateActivity(1);
        const a = await registry.getActivity(1);
        expect(a.active).to.equal(true);
    });

    it("Should revert when ACTIVATOR_ROLE exists but user is not activated in real SpiralEngine", async function () {
        await expectRevertCustom(
            registry.connect(notActivated).createActivity(0, "QmRoleOnlyNoInvite"),
            registry,
            "NotActivatedActivityCreator"
        );
    });

    it("Should block sanctioned user when role is revoked after suspension", async function () {
        const ACTIVATOR_ROLE = await spiral.ACTIVATOR_ROLE();
        await spiral.connect(admin).suspendUser(sanctioned.address, 7 * 24 * 60 * 60, "integration-sanction");
        await spiral.connect(admin).revokeRole(ACTIVATOR_ROLE, sanctioned.address);

        await expectRevertCustom(
            registry.connect(sanctioned).createActivity(0, "QmSanctionedBlocked"),
            registry,
            "NotActivatedActivityCreator"
        );
    });
});

