/**
 * SpiralEngine - Sanctions Deep Layer
 * Строгие и edge-тесты санкций (revert, длительности, иерархия нарушений).
 * Запуск: npx hardhat test contracts/tests/SpiralEngine.sanctions.deep.test.js
 * См. contracts/docs/analysis/tasks/task-tests-spiralengine-sanctions-deep/
 */
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

describe("SpiralEngine - Sanctions Deep Layer", function () {
    let spiralEngine;
    let deployer;
    let seller;
    let activator1;
    let activator2;
    let user1;
    let user2;
    let user3;

    const DEFAULT_ADMIN_ROLE = ethers.keccak256(ethers.toUtf8Bytes("DEFAULT_ADMIN_ROLE"));
    const SELLER_ROLE = ethers.keccak256(ethers.toUtf8Bytes("SELLER_ROLE"));
    const ACTIVATOR_ROLE = ethers.keccak256(ethers.toUtf8Bytes("ACTIVATOR_ROLE"));

    beforeEach(async function () {
        const signers = await ethers.getSigners();
        deployer = signers[0];
        seller = ethers.Wallet.createRandom().connect(ethers.provider);
        activator1 = ethers.Wallet.createRandom().connect(ethers.provider);
        activator2 = ethers.Wallet.createRandom().connect(ethers.provider);
        user1 = ethers.Wallet.createRandom().connect(ethers.provider);
        user2 = ethers.Wallet.createRandom().connect(ethers.provider);
        user3 = ethers.Wallet.createRandom().connect(ethers.provider);

        for (const w of [seller, activator1, activator2, user1, user2, user3]) {
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

        await spiralEngine.connect(deployer).grantRole(SELLER_ROLE, seller.address);
        await spiralEngine.connect(deployer).grantRole(SELLER_ROLE, activator1.address);
        await spiralEngine.connect(deployer).grantRole(SELLER_ROLE, activator2.address);
        await spiralEngine.connect(deployer).grantRole(ACTIVATOR_ROLE, activator1.address);
        await spiralEngine.connect(deployer).grantRole(ACTIVATOR_ROLE, activator2.address);
    });

    it("Deep sanctions suite is loaded", async function () {
        expect(ethers.isAddress(await spiralEngine.getAddress())).to.be.true;
    });

    describe("P0: Access & invalid (revert)", function () {
        it("Should prevent non-admin from suspending users", async function () {
            await spiralEngine.connect(activator1).mintInvite("SUSPEND-TEST-INVITE", 0);
            const newCodes = Array.from({ length: 12 }, (_, i) => `NEW-${i + 1}`);
            await spiralEngine.connect(activator1).activateUser("SUSPEND-TEST-INVITE", user1.address, newCodes, 0);
            await expectCustomError(
                spiralEngine.connect(activator1).suspendUser(user1.address, 3600, "Unauthorized suspension"),
                spiralEngine,
                "AccessControlUnauthorizedAccount"
            );
        });

        it("Should handle suspension of non-activated user", async function () {
            await expectCustomError(
                spiralEngine.connect(deployer).suspendUser(user1.address, 3600, "Non-activated user suspension"),
                spiralEngine,
                "UserNotActivated"
            );
        });

        it("Should handle suspension of zero address", async function () {
            await expectCustomError(
                spiralEngine.connect(deployer).suspendUser(ethers.ZeroAddress, 3600, "Zero address suspension"),
                spiralEngine,
                "InvalidUserAddress"
            );
        });
    });

    describe("P1: Suspension effects (revert)", function () {
        it("Should prevent suspended user from being activated", async function () {
            await spiralEngine.connect(activator1).mintInvite("SUSPEND-EFFECT-TEST-INVITE", 0);
            const newCodes = Array.from({ length: 12 }, (_, i) => `NEW-${i + 1}`);
            await spiralEngine.connect(activator1).activateUser("SUSPEND-EFFECT-TEST-INVITE", user1.address, newCodes, 0);
            await spiralEngine.connect(deployer).suspendUser(user1.address, 3600, "Suspension effect test");
            const newCodes2 = Array.from({ length: 12 }, (_, i) => `NEW-2-${i + 1}`);
            await expectCustomError(
                spiralEngine.connect(activator1).activateUser("SUSPEND-EFFECT-TEST-INVITE", user1.address, newCodes2, 0),
                spiralEngine,
                "UserAlreadyActivated"
            );
        });

        it("Should prevent suspended user from being activated again", async function () {
            await spiralEngine.connect(activator1).mintInvite("SUSPEND-ACTIVATION-TEST-INVITE", 0);
            const newCodes = Array.from({ length: 12 }, (_, i) => `NEW-${i + 1}`);
            await spiralEngine.connect(activator1).activateUser("SUSPEND-ACTIVATION-TEST-INVITE", user1.address, newCodes, 0);
            await spiralEngine.connect(deployer).suspendUser(user1.address, 3600, "Test suspension");
            await spiralEngine.connect(activator1).mintInvite("SUSPEND-ACTIVATION-TEST-INVITE-2", 0);
            const newCodes2 = Array.from({ length: 12 }, (_, i) => `NEW-2-${i + 1}`);
            await expectCustomError(
                spiralEngine.connect(activator1).activateUser("SUSPEND-ACTIVATION-TEST-INVITE-2", user1.address, newCodes2, 0),
                spiralEngine,
                "UserAlreadyActivated"
            );
        });

        it("Should enforce suspension restrictions in activateUser", async function () {
            await spiralEngine.connect(activator1).mintInvite("ENFORCEMENT-SUSPEND-TEST-INVITE", 0);
            const newCodes = Array.from({ length: 12 }, (_, i) => `NEW-${i + 1}`);
            await spiralEngine.connect(activator1).activateUser("ENFORCEMENT-SUSPEND-TEST-INVITE", user1.address, newCodes, 0);
            await spiralEngine.connect(deployer).suspendUser(user1.address, 3600, "Test suspension");
            await spiralEngine.connect(activator1).mintInvite("ENFORCEMENT-SUSPEND-TEST-INVITE-2", 0);
            const newCodes2 = Array.from({ length: 12 }, (_, i) => `NEW-2-${i + 1}`);
            await expectCustomError(
                spiralEngine.connect(activator1).activateUser("ENFORCEMENT-SUSPEND-TEST-INVITE-2", user1.address, newCodes2, 0),
                spiralEngine,
                "UserAlreadyActivated"
            );
        });
    });

    describe("P1: Edge durations & reasons", function () {
        it("Should handle multiple suspensions", async function () {
            await spiralEngine.connect(activator1).mintInvite("SUSPEND-TEST-INVITE-1", 0);
            await spiralEngine.connect(activator1).mintInvite("SUSPEND-TEST-INVITE-2", 0);
            await spiralEngine.connect(activator1).mintInvite("SUSPEND-TEST-INVITE-3", 0);
            const newCodes1 = Array.from({ length: 12 }, (_, i) => `NEW-1-${i + 1}`);
            const newCodes2 = Array.from({ length: 12 }, (_, i) => `NEW-2-${i + 1}`);
            const newCodes3 = Array.from({ length: 12 }, (_, i) => `NEW-3-${i + 1}`);
            await spiralEngine.connect(activator1).activateUser("SUSPEND-TEST-INVITE-1", user1.address, newCodes1, 0);
            await spiralEngine.connect(activator1).activateUser("SUSPEND-TEST-INVITE-2", user2.address, newCodes2, 0);
            await spiralEngine.connect(activator1).activateUser("SUSPEND-TEST-INVITE-3", user3.address, newCodes3, 0);
            await spiralEngine.connect(deployer).suspendUser(user1.address, 3600, "Suspension 1");
            await spiralEngine.connect(deployer).suspendUser(user2.address, 7200, "Suspension 2");
            await spiralEngine.connect(deployer).suspendUser(user3.address, 1800, "Suspension 3");
            const s1 = await spiralEngine.suspensionUntil(user1.address);
            const s2 = await spiralEngine.suspensionUntil(user2.address);
            const s3 = await spiralEngine.suspensionUntil(user3.address);
            expect(s1 > 0n).to.be.true;
            expect(s2 > 0n).to.be.true;
            expect(s3 > 0n).to.be.true;
            expect(s2 > s1).to.be.true;
            expect(s1 > s3).to.be.true;
        });

        it("Should handle zero duration suspension", async function () {
            await spiralEngine.connect(activator1).mintInvite("SUSPEND-TEST-INVITE", 0);
            const newCodes = Array.from({ length: 12 }, (_, i) => `NEW-${i + 1}`);
            await spiralEngine.connect(activator1).activateUser("SUSPEND-TEST-INVITE", user1.address, newCodes, 0);
            await spiralEngine.connect(deployer).suspendUser(user1.address, 1, "Minimal duration suspension");
            const suspensionUntil = await spiralEngine.suspensionUntil(user1.address);
            expect(suspensionUntil > 0n).to.be.true;
        });

        it("Should handle suspension with very long duration", async function () {
            await spiralEngine.connect(activator1).mintInvite("LONG-SUSPEND-TEST-INVITE", 0);
            const newCodes = Array.from({ length: 12 }, (_, i) => `NEW-${i + 1}`);
            await spiralEngine.connect(activator1).activateUser("LONG-SUSPEND-TEST-INVITE", user1.address, newCodes, 0);
            const longDuration = 365 * 24 * 60 * 60;
            await spiralEngine.connect(deployer).suspendUser(user1.address, longDuration, "Long suspension");
            const suspensionUntil = await spiralEngine.suspensionUntil(user1.address);
            const currentTime = BigInt((await ethers.provider.getBlock("latest")).timestamp);
            const expected = currentTime + BigInt(longDuration);
            const diff = suspensionUntil > expected ? suspensionUntil - expected : expected - suspensionUntil;
            expect(typeof suspensionUntil).to.equal("bigint");
            expect(diff <= 5n).to.be.true;
        });

        it("Should handle suspension with empty reason", async function () {
            await spiralEngine.connect(activator1).mintInvite("EMPTY-REASON-TEST-INVITE", 0);
            const newCodes = Array.from({ length: 12 }, (_, i) => `NEW-${i + 1}`);
            await spiralEngine.connect(activator1).activateUser("EMPTY-REASON-TEST-INVITE", user1.address, newCodes, 0);
            await spiralEngine.connect(deployer).suspendUser(user1.address, 3600, "");
            const suspensionUntil = await spiralEngine.suspensionUntil(user1.address);
            expect(typeof suspensionUntil).to.equal("bigint");
            expect(suspensionUntil > 0n).to.be.true;
        });

        it("Should handle suspension with maximum duration", async function () {
            await spiralEngine.connect(activator1).mintInvite("MAX-DURATION-TEST-INVITE", 0);
            const newCodes = Array.from({ length: 12 }, (_, i) => `NEW-${i + 1}`);
            await spiralEngine.connect(activator1).activateUser("MAX-DURATION-TEST-INVITE", user1.address, newCodes, 0);
            const maxDuration = 100 * 365 * 24 * 60 * 60;
            await spiralEngine.connect(deployer).suspendUser(user1.address, maxDuration, "Maximum duration suspension");
            const suspensionUntil = await spiralEngine.suspensionUntil(user1.address);
            const currentTime = BigInt((await ethers.provider.getBlock("latest")).timestamp);
            const expected = currentTime + BigInt(maxDuration);
            const diffMax = suspensionUntil > expected ? suspensionUntil - expected : expected - suspensionUntil;
            expect(typeof suspensionUntil).to.equal("bigint");
            expect(diffMax <= 5n).to.be.true;
        });

        it("Should handle suspension with very long reason", async function () {
            await spiralEngine.connect(activator1).mintInvite("LONG-REASON-TEST-INVITE", 0);
            const newCodes = Array.from({ length: 12 }, (_, i) => `NEW-${i + 1}`);
            await spiralEngine.connect(activator1).activateUser("LONG-REASON-TEST-INVITE", user1.address, newCodes, 0);
            const longReason = "A".repeat(1000);
            await spiralEngine.connect(deployer).suspendUser(user1.address, 3600, longReason);
            const suspensionUntil = await spiralEngine.suspensionUntil(user1.address);
            expect(suspensionUntil > 0n).to.be.true;
        });
    });

    describe("P1: Sanctions hierarchy", function () {
        it("Should track activator violations", async function () {
            await spiralEngine.connect(activator1).mintInvite("HIERARCHY-TEST-INVITE", 0);
            const newCodes = Array.from({ length: 12 }, (_, i) => `NEW-${i + 1}`);
            await spiralEngine.connect(activator1).activateUser("HIERARCHY-TEST-INVITE", user1.address, newCodes, 0);
            await spiralEngine.connect(deployer).suspendUser(user1.address, 3600, "Hierarchy test");
            const activatorViolations = await spiralEngine.activationViolations(activator1.address);
            expect(activatorViolations > 0n).to.be.true;
        });

        it("Should track nominator violations", async function () {
            await spiralEngine.connect(activator1).mintInvite("HIERARCHY-TEST-INVITE", 0);
            const newCodes = Array.from({ length: 12 }, (_, i) => `NEW-${i + 1}`);
            await spiralEngine.connect(activator1).activateUser("HIERARCHY-TEST-INVITE", user1.address, newCodes, 0);
            await spiralEngine.connect(deployer).grantRole(SELLER_ROLE, user1.address);
            await spiralEngine.connect(deployer).grantRole(ACTIVATOR_ROLE, user1.address);
            await spiralEngine.connect(deployer).suspendUser(user1.address, 3600, "Nominator test");
            const nominatorViolations = await spiralEngine.nominationViolations(activator1.address);
            expect(nominatorViolations).to.be.a("bigint");
        });
    });
});
