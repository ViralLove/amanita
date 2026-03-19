/**
 * SpiralEngine - SBT Deep Layer
 * Глубокий слой тестов для non-transferability, approvals, DID, recovery (smoke).
 * Не входит в MVP; запуск: npx hardhat test contracts/tests/SpiralEngine.sbt.deep.test.js
 * См. contracts/docs/analysis/tasks/task-tests-spiralengine-sbt-deep.md
 */
const { expect } = require("chai");
const { ethers } = require("hardhat");

/** Проверка revert с custom error без зависимости от hardhat-chai-matchers */
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

describe("SpiralEngine - SBT Deep Layer", function () {
    let spiralEngine;
    let deployer;
    let seller;
    let activator1;
    let activator2;
    let user1;
    let user2;
    let guardian1;

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
        guardian1 = ethers.Wallet.createRandom().connect(ethers.provider);

        await deployer.sendTransaction({ to: seller.address, value: ethers.parseEther("1.0") });
        await deployer.sendTransaction({ to: activator1.address, value: ethers.parseEther("1.0") });
        await deployer.sendTransaction({ to: activator2.address, value: ethers.parseEther("1.0") });
        await deployer.sendTransaction({ to: user1.address, value: ethers.parseEther("0.1") });
        await deployer.sendTransaction({ to: user2.address, value: ethers.parseEther("0.1") });
        await deployer.sendTransaction({ to: guardian1.address, value: ethers.parseEther("0.1") });

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
        const SPIRAL_ENGINE_ROLE = await soulIdentity.SPIRAL_ENGINE_ROLE();
        await soulIdentity.connect(deployer).grantRole(SPIRAL_ENGINE_ROLE, await spiralEngine.getAddress());

        await spiralEngine.connect(deployer).grantRole(SELLER_ROLE, seller.address);
        await spiralEngine.connect(deployer).grantRole(ACTIVATOR_ROLE, activator1.address);
        await spiralEngine.connect(deployer).grantRole(ACTIVATOR_ROLE, activator2.address);
    });

    it("Deep layer suite is loaded", async function () {
        const addr = await spiralEngine.getAddress();
        expect(addr).to.be.a("string");
        expect(ethers.isAddress(addr)).to.be.true;
    });

    describe("P0: Non-transferability & Approvals", function () {
        const P0_INVITE_CODE = "DEEP-P0-INVITE";

        it("Should enforce non-transferability (transferFrom)", async function () {
            await spiralEngine.connect(seller).mintInvite(P0_INVITE_CODE, 0);
            const tokenId = await spiralEngine.inviteCodeToTokenId(P0_INVITE_CODE);
            const owner = await spiralEngine.ownerOf(tokenId);
            expect(owner).to.equal(seller.address);

            await expectCustomError(
                spiralEngine.connect(seller).transferFrom(seller.address, user2.address, tokenId),
                spiralEngine,
                "TransfersNotAllowed"
            );
            expect(await spiralEngine.ownerOf(tokenId)).to.equal(seller.address);
        });

        it("Should enforce non-transferability (safeTransferFrom)", async function () {
            await spiralEngine.connect(seller).mintInvite(P0_INVITE_CODE, 0);
            const tokenId = await spiralEngine.inviteCodeToTokenId(P0_INVITE_CODE);

            await expectCustomError(
                spiralEngine.connect(seller).safeTransferFrom(seller.address, user2.address, tokenId),
                spiralEngine,
                "TransfersNotAllowed"
            );
        });

        it("Should block approval delegation (approve)", async function () {
            await spiralEngine.connect(seller).mintInvite(P0_INVITE_CODE, 0);
            const tokenId = await spiralEngine.inviteCodeToTokenId(P0_INVITE_CODE);

            await expectCustomError(
                spiralEngine.connect(seller).approve(user2.address, tokenId),
                spiralEngine,
                "ApprovalsNotAllowed"
            );
        });

        it("Should block global approval delegation (setApprovalForAll)", async function () {
            await spiralEngine.connect(seller).mintInvite(P0_INVITE_CODE, 0);

            await expectCustomError(
                spiralEngine.connect(seller).setApprovalForAll(user2.address, true),
                spiralEngine,
                "ApprovalsNotAllowed"
            );
        });
    });

    describe("P1: DID", function () {
        it("Should allow linking DID", async function () {
            await spiralEngine.connect(deployer).mintInvite("DEEP-DID-INVITE", 0);
            const newCodes = Array.from({ length: 12 }, (_, i) => `DID-NEW-${i + 1}`);
            await spiralEngine.connect(deployer).activateUser("DEEP-DID-INVITE", user1.address, newCodes, 0);

            const soulIdentityAddress = await spiralEngine.soulIdentity();
            const soulIdentity = await ethers.getContractAt("SoulIdentity", soulIdentityAddress);
            const soulboundCoreAddress = await soulIdentity.soulboundCore();
            const soulboundCore = await ethers.getContractAt("SoulboundCore", soulboundCoreAddress);
            await soulboundCore.connect(deployer).mintSoul(user1.address);

            const testDID = "did:key:z6MkhaXgBZDvotDkL5257faiztiGiC2QtKLGpbnnEGta2doK";
            await soulIdentity.connect(user1).linkSoulIdentity(testDID);

            const reputation = await spiralEngine.getSoulReputation(user1.address);
            const level = await spiralEngine.getSoulLevel(user1.address);
            expect(reputation).to.equal(100n);
            expect(level).to.equal(1n);
        });
    });

    describe("P1: Recovery (smoke)", function () {
        it("Should allow adding trusted guardians (smoke)", async function () {
            await spiralEngine.connect(deployer).mintInvite("DEEP-RECOVERY-INVITE", 0);
            const newCodes = Array.from({ length: 12 }, (_, i) => `REC-NEW-${i + 1}`);
            await spiralEngine.connect(deployer).activateUser("DEEP-RECOVERY-INVITE", user1.address, newCodes, 0);

            const soulIdentityAddress = await spiralEngine.soulIdentity();
            const soulIdentity = await ethers.getContractAt("SoulIdentity", soulIdentityAddress);
            const soulboundCoreAddress = await soulIdentity.soulboundCore();
            const soulboundCore = await ethers.getContractAt("SoulboundCore", soulboundCoreAddress);
            await soulboundCore.connect(deployer).mintSoul(user1.address);

            const SoulRecovery = await ethers.getContractFactory("SoulRecovery");
            const soulRecovery = await SoulRecovery.connect(deployer).deploy(await soulboundCore.getAddress());
            await soulRecovery.waitForDeployment();
            await soulboundCore.connect(deployer).setRecoveryContract(await soulRecovery.getAddress());
            await soulRecovery.connect(deployer).setSoulIdentity(await soulIdentity.getAddress());
            await soulIdentity.connect(deployer).setSoulRecovery(await soulRecovery.getAddress());

            const tx = await soulIdentity.connect(user1).addTrustedGuardian(guardian1.address);
            await tx.wait();
        });

        it("Should return profile with guardians (smoke)", async function () {
            await spiralEngine.connect(deployer).mintInvite("DEEP-PROFILE-INVITE", 0);
            const newCodes = Array.from({ length: 12 }, (_, i) => `PRF-NEW-${i + 1}`);
            await spiralEngine.connect(deployer).activateUser("DEEP-PROFILE-INVITE", user1.address, newCodes, 0);

            const soulIdentityAddress = await spiralEngine.soulIdentity();
            const soulIdentity = await ethers.getContractAt("SoulIdentity", soulIdentityAddress);
            const soulboundCoreAddress = await soulIdentity.soulboundCore();
            const soulboundCore = await ethers.getContractAt("SoulboundCore", soulboundCoreAddress);
            await soulboundCore.connect(deployer).mintSoul(user1.address);

            const SoulRecovery = await ethers.getContractFactory("SoulRecovery");
            const soulRecovery = await SoulRecovery.connect(deployer).deploy(await soulboundCore.getAddress());
            await soulRecovery.waitForDeployment();
            await soulboundCore.connect(deployer).setRecoveryContract(await soulRecovery.getAddress());
            await soulRecovery.connect(deployer).setSoulIdentity(await soulIdentity.getAddress());
            await soulIdentity.connect(deployer).setSoulRecovery(await soulRecovery.getAddress());
            await soulIdentity.connect(user1).addTrustedGuardian(guardian1.address);

            const profile = await spiralEngine.getSoulProfile(user1.address);
            expect(profile.level).to.be.a("bigint");
            expect(profile.reputation).to.be.a("bigint");
            expect(profile.identity).to.be.a("string");
            expect(profile.guardians).to.be.an("array");
            expect(profile.guardians.length).to.equal(1);
            expect(profile.guardians[0]).to.equal(guardian1.address);
        });
    });

    // P2: при появлении полного API временных ключей/репутации обновить ожидания (ненулевой ключ, истечение срока, реальные лимиты)
    describe("P2: Edge (current stub behavior)", function () {
        it("Should handle temporary key creation and expiration", async function () {
            await spiralEngine.connect(deployer).mintInvite("DEEP-P2-TEMP-INVITE", 0);
            const newCodes = Array.from({ length: 12 }, (_, i) => `P2-TEMP-${i + 1}`);
            await spiralEngine.connect(deployer).activateUser("DEEP-P2-TEMP-INVITE", user1.address, newCodes, 0);
            const soulIdentityAddress = await spiralEngine.soulIdentity();
            const soulIdentity = await ethers.getContractAt("SoulIdentity", soulIdentityAddress);
            const soulboundCoreAddress = await soulIdentity.soulboundCore();
            const soulboundCore = await ethers.getContractAt("SoulboundCore", soulboundCoreAddress);
            await soulboundCore.connect(deployer).mintSoul(user1.address);

            // Текущая реализация: заглушки. При полном API обновить: ожидать ненулевой ключ после create, valid=true до истечения срока
            await soulIdentity.connect(user1).createTemporaryKey(guardian1.address, 3600);
            const tempKey = await soulIdentity.getTemporaryKey(user1.address);
            const valid = await soulIdentity.isTemporaryKeyValid(guardian1.address);
            expect(tempKey).to.equal(ethers.ZeroAddress);
            expect(valid).to.be.false;
        });

        it("Should prevent duplicate temporary key creation", async function () {
            await spiralEngine.connect(deployer).mintInvite("DEEP-P2-DUP-INVITE", 0);
            const newCodes = Array.from({ length: 12 }, (_, i) => `P2-DUP-${i + 1}`);
            await spiralEngine.connect(deployer).activateUser("DEEP-P2-DUP-INVITE", user1.address, newCodes, 0);
            const soulIdentityAddress = await spiralEngine.soulIdentity();
            const soulIdentity = await ethers.getContractAt("SoulIdentity", soulIdentityAddress);
            const soulboundCoreAddress = await soulIdentity.soulboundCore();
            const soulboundCore = await ethers.getContractAt("SoulboundCore", soulboundCoreAddress);
            await soulboundCore.connect(deployer).mintSoul(user1.address);

            // Заглушка: повторный вызов не ревертит; getTemporaryKey=0. При полном API: ожидать revert или перезапись при duplicate
            await soulIdentity.connect(user1).createTemporaryKey(guardian1.address, 3600);
            await soulIdentity.connect(user1).createTemporaryKey(guardian1.address, 7200);
            const tempKey = await soulIdentity.getTemporaryKey(user1.address);
            expect(tempKey).to.equal(ethers.ZeroAddress);
        });

        it("Should validate reputation requirements", async function () {
            // Пользователь без SBT — репутация 0
            const repNoSbt = await spiralEngine.getSoulReputation(user2.address);
            expect(repNoSbt).to.equal(0n);

            // Пользователь с SBT и DID — репутация от SoulIdentity (заглушка возвращает 100)
            await spiralEngine.connect(deployer).mintInvite("DEEP-P2-REP-INVITE", 0);
            const newCodes = Array.from({ length: 12 }, (_, i) => `P2-REP-${i + 1}`);
            await spiralEngine.connect(deployer).activateUser("DEEP-P2-REP-INVITE", user1.address, newCodes, 0);
            const soulIdentityAddress = await spiralEngine.soulIdentity();
            const soulIdentity = await ethers.getContractAt("SoulIdentity", soulIdentityAddress);
            const soulboundCoreAddress = await soulIdentity.soulboundCore();
            const soulboundCore = await ethers.getContractAt("SoulboundCore", soulboundCoreAddress);
            await soulboundCore.connect(deployer).mintSoul(user1.address);
            await soulIdentity.connect(user1).linkSoulIdentity("did:key:z6MkP2");
            const repWithSbt = await spiralEngine.getSoulReputation(user1.address);
            expect(repWithSbt).to.equal(100n);
        });
    });
});
