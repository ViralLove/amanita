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
    const selector = contract.interface.getError(errorName).selector;
    const data = err?.data || err?.error?.data || err?.receipt || "";
    const hex = typeof data === "string" ? data : (data && data.toString ? data.toString() : "");
    expect(hex.toLowerCase().includes(selector.toLowerCase()), `expected error ${errorName}`).to.be.true;
}

function makeCodes(prefix, n = 12) {
    return Array.from({ length: n }, (_, i) => `${prefix}-${i + 1}`);
}

describe("SpiralEngine master cycle", function () {
    let spiralEngine;
    let deployer;
    let activator;
    let candidateSeller;
    let observer;

    const SELLER_ROLE = ethers.keccak256(ethers.toUtf8Bytes("SELLER_ROLE"));
    const ACTIVATOR_ROLE = ethers.keccak256(ethers.toUtf8Bytes("ACTIVATOR_ROLE"));

    beforeEach(async function () {
        [deployer] = await ethers.getSigners();
        activator = ethers.Wallet.createRandom().connect(ethers.provider);
        candidateSeller = ethers.Wallet.createRandom().connect(ethers.provider);
        observer = ethers.Wallet.createRandom().connect(ethers.provider);

        for (const w of [activator, candidateSeller, observer]) {
            await deployer.sendTransaction({ to: w.address, value: ethers.parseEther("1.0") });
        }

        const SoulboundCore = await ethers.getContractFactory("SoulboundCore");
        const soulboundCore = await SoulboundCore.connect(deployer).deploy("Amanita Soul", "ASOUL");
        await soulboundCore.waitForDeployment();

        const SoulMetadata = await ethers.getContractFactory("SoulMetadata");
        const soulMetadata = await SoulMetadata.connect(deployer).deploy(await soulboundCore.getAddress());
        await soulMetadata.waitForDeployment();
        await soulboundCore.connect(deployer).setMetadataContract(await soulMetadata.getAddress());

        const SoulIdentity = await ethers.getContractFactory("SoulIdentity");
        const soulIdentity = await SoulIdentity.connect(deployer).deploy(
            await soulboundCore.getAddress(),
            await soulMetadata.getAddress()
        );
        await soulIdentity.waitForDeployment();

        const Logic = await ethers.getContractFactory("SpiralEngineLogic");
        const logicImpl = await Logic.connect(deployer).deploy();
        await logicImpl.waitForDeployment();
        const initCalldata = logicImpl.interface.encodeFunctionData("initialize", [deployer.address]);

        const Proxy = await ethers.getContractFactory("SpiralEngineProxy");
        const proxy = await Proxy.connect(deployer).deploy(await logicImpl.getAddress(), initCalldata);
        await proxy.waitForDeployment();

        spiralEngine = Logic.attach(await proxy.getAddress());
        await spiralEngine.connect(deployer).setSoulIdentity(await soulIdentity.getAddress());

        await spiralEngine.connect(deployer).grantRole(SELLER_ROLE, activator.address);
        await spiralEngine.connect(deployer).grantRole(ACTIVATOR_ROLE, activator.address);
    });

    it("runs activate -> seller grant -> sanction impact -> visibility cycle", async function () {
        // 1) Activator mints invite and activates candidate seller.
        await spiralEngine.connect(activator).mintInvite("MASTER-CYCLE-INVITE", 0);
        await spiralEngine
            .connect(activator)
            .activateUser("MASTER-CYCLE-INVITE", candidateSeller.address, makeCodes("MASTER-NEW"), 0);

        expect(await spiralEngine.usedInviteByUser(candidateSeller.address)).to.not.equal(0n);
        expect(await spiralEngine.userActivator(candidateSeller.address)).to.equal(activator.address);
        expect(await spiralEngine.hasRole(ACTIVATOR_ROLE, candidateSeller.address)).to.be.true;

        const circleMembers = await spiralEngine.getCircleMembers(activator.address);
        expect(circleMembers).to.include(candidateSeller.address);

        // 2) Admin grants seller role to activated user.
        await spiralEngine.connect(deployer).grantSellerRole(candidateSeller.address);
        expect(await spiralEngine.hasRole(SELLER_ROLE, candidateSeller.address)).to.be.true;
        expect(await spiralEngine.sellerNominator(candidateSeller.address)).to.equal(deployer.address);

        // 3) Visibility before sanctions.
        const [isActivatedBefore, hasSellerBefore, hasActivatorBefore, inviteCountBefore, totalInvitesBefore] =
            await spiralEngine.getSellerPublicInfo(candidateSeller.address);
        expect(isActivatedBefore).to.equal(true);
        expect(hasSellerBefore).to.equal(true);
        expect(hasActivatorBefore).to.equal(true);
        expect(inviteCountBefore).to.equal(12n);
        expect(totalInvitesBefore).to.equal(12n);

        // 4) Sanctions: suspension and cascade counters.
        expect(await spiralEngine.violationCount(candidateSeller.address)).to.equal(0n);
        expect(await spiralEngine.activationViolations(activator.address)).to.equal(0n);
        expect(await spiralEngine.nominationViolations(deployer.address)).to.equal(0n);

        const duration = 2 * 24 * 60 * 60;
        await spiralEngine.connect(deployer).suspendUser(candidateSeller.address, duration, "master-cycle sanction");

        const now = BigInt((await ethers.provider.getBlock("latest")).timestamp);
        const until = await spiralEngine.suspensionUntil(candidateSeller.address);
        expect(until > now).to.equal(true);
        expect(await spiralEngine.violationCount(candidateSeller.address)).to.equal(1n);
        expect(await spiralEngine.activationViolations(activator.address)).to.equal(1n);
        expect(await spiralEngine.nominationViolations(deployer.address)).to.equal(1n);

        // 5) Visibility remains queryable after sanction (status is represented via suspensionUntil/counters).
        const [isActivatedAfter, hasSellerAfter, hasActivatorAfter] =
            await spiralEngine.getSellerPublicInfo(candidateSeller.address);
        expect(isActivatedAfter).to.equal(true);
        expect(hasSellerAfter).to.equal(true);
        expect(hasActivatorAfter).to.equal(true);
    });

    it("enforces diagnostics visibility boundary and keeps admin visibility post-sanction", async function () {
        await spiralEngine.connect(activator).mintInvite("DIAG-MASTER-INVITE", 0);
        await spiralEngine
            .connect(activator)
            .activateUser("DIAG-MASTER-INVITE", candidateSeller.address, makeCodes("DIAG-NEW"), 0);
        await spiralEngine.connect(deployer).grantSellerRole(candidateSeller.address);

        await expectCustomError(
            spiralEngine.connect(observer).getSellerDiagnostics(candidateSeller.address),
            spiralEngine,
            "UnauthorizedDiagnosticAccess"
        );

        const selfDiag = await spiralEngine.connect(candidateSeller).getSellerDiagnostics(candidateSeller.address);
        expect(selfDiag.isActivated).to.equal(true);
        expect(selfDiag.hasSellerRole).to.equal(true);
        expect(selfDiag.userInvites.length).to.equal(12);

        await spiralEngine.connect(deployer).suspendUser(candidateSeller.address, 3600, "diag sanction");
        const adminDiag = await spiralEngine.connect(deployer).getSellerDiagnostics(candidateSeller.address);
        expect(adminDiag.isActivated).to.equal(true);
        expect(adminDiag.hasSellerRole).to.equal(true);
        expect(await spiralEngine.violationCount(candidateSeller.address)).to.equal(1n);
    });
});

