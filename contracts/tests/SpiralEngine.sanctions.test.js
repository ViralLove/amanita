/**
 * SpiralEngine - Sanctions System (MVP)
 * Smoke/архитектурные инварианты. Deep-кейсы в SpiralEngine.sanctions.deep.test.js
 */
const { expect } = require("chai");
const { ethers } = require("hardhat");

describe("SpiralEngine - Sanctions System", function () {
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

    describe("User Suspension (MVP)", function () {
        it("Should suspend user by admin", async function () {
            await spiralEngine.connect(activator1).mintInvite("SUSPEND-TEST-INVITE", 0);
            const newCodes = Array.from({ length: 12 }, (_, i) => `NEW-${i + 1}`);
            await spiralEngine.connect(activator1).activateUser("SUSPEND-TEST-INVITE", user1.address, newCodes, 0);
            const suspensionDuration = 3600;
            await spiralEngine.connect(deployer).suspendUser(user1.address, suspensionDuration, "Test suspension");
            const suspensionUntil = await spiralEngine.suspensionUntil(user1.address);
            const currentTime = BigInt((await ethers.provider.getBlock("latest")).timestamp);
            const expectedSuspensionUntil = currentTime + BigInt(suspensionDuration);
            const diff = suspensionUntil > expectedSuspensionUntil ? suspensionUntil - expectedSuspensionUntil : expectedSuspensionUntil - suspensionUntil;
            expect(suspensionUntil > currentTime).to.be.true;
            expect(diff <= 5n).to.be.true;
        });
    });

    describe("Violation Counting (MVP)", function () {
        it("Should track violation counts", async function () {
            await spiralEngine.connect(activator1).mintInvite("VIOLATION-TEST-INVITE", 0);
            const newCodes = Array.from({ length: 12 }, (_, i) => `NEW-${i + 1}`);
            await spiralEngine.connect(activator1).activateUser("VIOLATION-TEST-INVITE", user1.address, newCodes, 0);
            const initialViolations = await spiralEngine.violationCount(user1.address);
            expect(initialViolations).to.equal(0n);
            await spiralEngine.connect(deployer).suspendUser(user1.address, 3600, "Violation test");
            const violationsAfterSuspension = await spiralEngine.violationCount(user1.address);
            expect(violationsAfterSuspension > initialViolations).to.be.true;
        });

        it("Should handle multiple violations", async function () {
            await spiralEngine.connect(activator1).mintInvite("VIOLATION-TEST-INVITE", 0);
            const newCodes = Array.from({ length: 12 }, (_, i) => `NEW-${i + 1}`);
            await spiralEngine.connect(activator1).activateUser("VIOLATION-TEST-INVITE", user1.address, newCodes, 0);
            await spiralEngine.connect(deployer).suspendUser(user1.address, 3600, "First violation");
            const violations1 = await spiralEngine.violationCount(user1.address);
            await new Promise((resolve) => setTimeout(resolve, 1000));
            await spiralEngine.connect(deployer).suspendUser(user1.address, 7200, "Second violation");
            const violations2 = await spiralEngine.violationCount(user1.address);
            expect(violations2 > violations1).to.be.true;
        });
    });

    describe("Suspension Effects (MVP)", function () {
        it("Should handle suspension expiration", async function () {
            await spiralEngine.connect(activator1).mintInvite("SUSPEND-EXPIRY-TEST-INVITE", 0);
            const newCodes = Array.from({ length: 12 }, (_, i) => `NEW-${i + 1}`);
            await spiralEngine.connect(activator1).activateUser("SUSPEND-EXPIRY-TEST-INVITE", user1.address, newCodes, 0);
            await spiralEngine.connect(deployer).suspendUser(user1.address, 1, "Short suspension");
            const suspensionUntil = await spiralEngine.suspensionUntil(user1.address);
            expect(suspensionUntil > 0n).to.be.true;
            await new Promise((resolve) => setTimeout(resolve, 2000));
            const currentTime = BigInt((await ethers.provider.getBlock("latest")).timestamp);
            const suspensionUntilAfter = await spiralEngine.suspensionUntil(user1.address);
            expect(suspensionUntilAfter <= currentTime + 1n).to.be.true;
        });
    });
});
