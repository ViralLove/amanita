const { expect } = require("chai");
const { ethers } = require("hardhat");

async function expectRevertWithMessage(txPromise, messageSubstring) {
    let err;
    try {
        const tx = await txPromise;
        if (tx && typeof tx.wait === "function") await tx.wait();
    } catch (e) {
        err = e;
    }
    expect(err, "expected transaction to revert").to.be.ok;
    const msg = (err?.reason || err?.shortMessage || err?.message || err?.error?.message || String(err)) || "";
    expect(msg.includes(messageSubstring), `expected revert message to contain "${messageSubstring}"`).to.be.true;
}

async function expectRevert(txPromise) {
    let err;
    try {
        const tx = await txPromise;
        if (tx && typeof tx.wait === "function") await tx.wait();
    } catch (e) {
        err = e;
    }
    expect(err, "expected transaction to revert").to.be.ok;
}

describe("LoveEmissionEngine with Lovecoin", function () {
    let lovecoin;
    let lgovToken;
    let loveDoPostNFT;
    let inviteGraph;
    let loveEmissionEngine;
    let deployer, user1, user2, seller, liker, emitter, likerFar, likerOther;

    beforeEach(async function () {
        // Получаем деплоера
        const signers = await ethers.getSigners();
        deployer = signers[0];

        // Создаем дополнительные кошельки для тестирования
        user1 = ethers.Wallet.createRandom().connect(ethers.provider);
        user2 = ethers.Wallet.createRandom().connect(ethers.provider);
        seller = ethers.Wallet.createRandom().connect(ethers.provider);
        liker = ethers.Wallet.createRandom().connect(ethers.provider);
        emitter = ethers.Wallet.createRandom().connect(ethers.provider);

        // Финансируем кошельки
        const fundingAmount = ethers.parseEther("1.0");
        likerFar = ethers.Wallet.createRandom().connect(ethers.provider);
        likerOther = ethers.Wallet.createRandom().connect(ethers.provider);

        for (const user of [user1, user2, seller, liker, emitter, likerFar, likerOther]) {
            await deployer.sendTransaction({
                to: user.address,
                value: fundingAmount
            });
        }

        // Деплоим Lovecoin
        const Lovecoin = await ethers.getContractFactory("Lovecoin");
        lovecoin = await Lovecoin.deploy(deployer.address);
        await lovecoin.waitForDeployment();

        // Деплоим LGOV Token (AmanitaGovToken)
        const AmanitaGovToken = await ethers.getContractFactory("AmanitaGovToken");
        lgovToken = await AmanitaGovToken.deploy(deployer.address);
        await lgovToken.waitForDeployment();

        // Моки: граф инвайтов (getInviterOf/invitedBy) и реестр (hasSellerRole) для LoveDoPostNFT
        const LoveInviteGraphMock = await ethers.getContractFactory("LoveInviteGraphMock");
        inviteGraph = await LoveInviteGraphMock.deploy();
        await inviteGraph.waitForDeployment();

        const LoveAmanitaRegistryMock = await ethers.getContractFactory("LoveAmanitaRegistryMock");
        const registryMock = await LoveAmanitaRegistryMock.deploy();
        await registryMock.waitForDeployment();

        const LoveDoPostNFT = await ethers.getContractFactory("LoveDoPostNFT");
        loveDoPostNFT = await LoveDoPostNFT.deploy(
            deployer.address,
            await inviteGraph.getAddress(),
            await registryMock.getAddress()
        );
        await loveDoPostNFT.waitForDeployment();

        // Root-граф (L=1 по умолчанию):
        // deployer(root) -> seller(depth1, anchor=seller) -> user1(depth2) -> liker(depth3)
        await inviteGraph.setInviter(seller.address, deployer.address);
        await inviteGraph.setInviter(user1.address, seller.address);
        await inviteGraph.setInviter(liker.address, user1.address);

        // far-цепочка с тем же anchor(seller), но depth слишком далек:
        // seller -> far1 -> far2 -> far3 -> likerFar (depth=5, diff с seller=4 > K=3)
        const far1 = ethers.Wallet.createRandom().address;
        const far2 = ethers.Wallet.createRandom().address;
        const far3 = ethers.Wallet.createRandom().address;
        await inviteGraph.setInviter(far1, seller.address);
        await inviteGraph.setInviter(far2, far1);
        await inviteGraph.setInviter(far3, far2);
        await inviteGraph.setInviter(likerFar.address, far3);

        // Другая ветка anchor на L=1:
        await inviteGraph.setInviter(user2.address, deployer.address); // другой anchor
        await inviteGraph.setInviter(likerOther.address, user2.address);

        // Деплоим LoveEmissionEngine
        const LoveEmissionEngine = await ethers.getContractFactory("LoveEmissionEngine");
        loveEmissionEngine = await LoveEmissionEngine.deploy(
            await lovecoin.getAddress(),
            await lgovToken.getAddress(),
            await loveDoPostNFT.getAddress(),
            await inviteGraph.getAddress(),
            deployer.address
        );
        await loveEmissionEngine.waitForDeployment();

        // Настраиваем роли
        const EMITTER_ROLE = await loveEmissionEngine.EMITTER_ROLE();
        await loveEmissionEngine.connect(deployer).grantRole(EMITTER_ROLE, emitter.address);

        // Настраиваем Lovecoin для LoveEmissionEngine
        const MINTER_ROLE = await lovecoin.MINTER_ROLE();
        await lovecoin.connect(deployer).grantRole(MINTER_ROLE, await loveEmissionEngine.getAddress());

        // Настраиваем LGOV для LoveEmissionEngine
        const LGOV_MINTER_ROLE = await lgovToken.MINTER_ROLE();
        await lgovToken.connect(deployer).grantRole(LGOV_MINTER_ROLE, await loveEmissionEngine.getAddress());
    });

    describe("P0: Core Emission Functions", function () {
        it("Should emit Lovecoin and LGOV for superlike", async function () {
            await loveDoPostNFT.connect(user1).mintLoveDoPost(seller.address, "ipfs://test");
            const tokenId = (await loveDoPostNFT.nextTokenId()) - 1n;
            const nonce = await loveDoPostNFT.superlikeNonces(liker.address);
            await loveDoPostNFT.connect(liker).addSuperlike(tokenId, nonce);

            await loveEmissionEngine.connect(emitter).emitForSuperlike(tokenId, liker.address);

            // Проверяем накопление токенов
            const loveAccrued = await loveEmissionEngine.loveAccrued(seller.address);
            const lgovAccrued = await loveEmissionEngine.lgovAccrued(seller.address);

            expect(loveAccrued).to.equal(ethers.parseEther("1"));
            expect(lgovAccrued).to.equal(ethers.parseEther("1"));
        });

        it("Should claim Lovecoin tokens", async function () {
            const amount = ethers.parseEther("100");
            await lovecoin.connect(deployer).transfer(await loveEmissionEngine.getAddress(), amount);

            await loveDoPostNFT.connect(user1).mintLoveDoPost(seller.address, "ipfs://test");
            const tokenId = (await loveDoPostNFT.nextTokenId()) - 1n;
            const nonce = await loveDoPostNFT.superlikeNonces(liker.address);
            await loveDoPostNFT.connect(liker).addSuperlike(tokenId, nonce);
            await loveEmissionEngine.connect(emitter).emitForSuperlike(tokenId, liker.address);

            const balanceBefore = await lovecoin.balanceOf(seller.address);
            expect(balanceBefore).to.equal(0n);

            // Клеймим Lovecoin
            await loveEmissionEngine.connect(seller).claimLOVECOIN();

            // Проверяем баланс после клейма
            const balanceAfter = await lovecoin.balanceOf(seller.address);
            expect(balanceAfter).to.equal(ethers.parseEther("1"));

            const loveAccrued = await loveEmissionEngine.loveAccrued(seller.address);
            expect(loveAccrued).to.equal(0n);
        });
    });

    describe("P1: LGOV Activation", function () {
        it("Should activate LGOV when reputation threshold is met", async function () {
            for (let i = 0; i < 8; i++) {
                await loveDoPostNFT.connect(user1).mintLoveDoPost(seller.address, `ipfs://post-${i}`);
            }
            const tokenId = (await loveDoPostNFT.nextTokenId()) - 1n; // 8-й пост (getLoveDoCount(seller) = 8)
            const nonce = await loveDoPostNFT.superlikeNonces(liker.address);
            await loveDoPostNFT.connect(liker).addSuperlike(tokenId, nonce);
            await loveEmissionEngine.connect(emitter).emitForSuperlike(tokenId, liker.address);

            // Проверяем накопленные LGOV
            const lgovAccrued = await loveEmissionEngine.lgovAccrued(seller.address);
            expect(lgovAccrued).to.equal(ethers.parseEther("1"));

            // Активируем LGOV
            await loveEmissionEngine.connect(seller).claimLGOV();

            // Проверяем, что LGOV были заминчены
            const lgovBalance = await lgovToken.balanceOf(seller.address);
            expect(lgovBalance).to.equal(ethers.parseEther("1"));

            const lgovAccruedAfter = await loveEmissionEngine.lgovAccrued(seller.address);
            expect(lgovAccruedAfter).to.equal(0n);
        });

        it("Should not activate LGOV when reputation threshold is not met", async function () {
            for (let i = 0; i < 7; i++) {
                await loveDoPostNFT.connect(user1).mintLoveDoPost(seller.address, `ipfs://post-${i}`);
            }
            const tokenId = (await loveDoPostNFT.nextTokenId()) - 1n; // последний из 7 постов
            const nonce = await loveDoPostNFT.superlikeNonces(liker.address);
            await loveDoPostNFT.connect(liker).addSuperlike(tokenId, nonce);
            await loveEmissionEngine.connect(emitter).emitForSuperlike(tokenId, liker.address);
            // getLoveDoCount(seller) = 7 < 8, claimLGOV должен ревертиться
            await expectRevertWithMessage(loveEmissionEngine.connect(seller).claimLGOV(), "LoveEmission: not enough LoveDo posts");
        });
    });

    describe("P2: Error Handling", function () {
        it("Should revert when claiming zero Lovecoin", async function () {
            // Hardhat может не передавать причину require; проверяем только факт реверта
            await expectRevert(loveEmissionEngine.connect(seller).claimLOVECOIN());
        });

        it("Should revert when claiming zero LGOV", async function () {
            // При нуле постов реверт: "not enough LoveDo posts"
            await expectRevertWithMessage(loveEmissionEngine.connect(seller).claimLGOV(), "LoveEmission: not enough LoveDo posts");
        });

        it("Should revert when non-emitter tries to emit", async function () {
            await loveDoPostNFT.connect(user1).mintLoveDoPost(seller.address, "ipfs://test");
            const tokenId = (await loveDoPostNFT.nextTokenId()) - 1n;
            const nonce = await loveDoPostNFT.superlikeNonces(liker.address);
            await loveDoPostNFT.connect(liker).addSuperlike(tokenId, nonce);

            await expectRevert(loveEmissionEngine.connect(user1).emitForSuperlike(tokenId, liker.address));
        });

        it("Should revert when emit is called without liker superlike", async function () {
            await loveDoPostNFT.connect(user1).mintLoveDoPost(seller.address, "ipfs://test");
            const tokenId = (await loveDoPostNFT.nextTokenId()) - 1n;

            await expectRevertWithMessage(
                loveEmissionEngine.connect(emitter).emitForSuperlike(tokenId, liker.address),
                "LoveEmission: superlike not found for liker"
            );
        });

        it("Should revert on duplicate emission for same like", async function () {
            await loveDoPostNFT.connect(user1).mintLoveDoPost(seller.address, "ipfs://test");
            const tokenId = (await loveDoPostNFT.nextTokenId()) - 1n;
            const nonce = await loveDoPostNFT.superlikeNonces(liker.address);
            await loveDoPostNFT.connect(liker).addSuperlike(tokenId, nonce);

            await loveEmissionEngine.connect(emitter).emitForSuperlike(tokenId, liker.address);

            await expectRevertWithMessage(
                loveEmissionEngine.connect(emitter).emitForSuperlike(tokenId, liker.address),
                "LoveEmission: emission already processed for like"
            );
        });

        it("Should revert when liker depth distance exceeds K", async function () {
            await loveDoPostNFT.connect(user1).mintLoveDoPost(seller.address, "ipfs://test");
            const tokenId = (await loveDoPostNFT.nextTokenId()) - 1n;
            const farNonce = await loveDoPostNFT.superlikeNonces(likerFar.address);

            await expectRevertWithMessage(
                loveDoPostNFT.connect(likerFar).addSuperlike(tokenId, farNonce),
                "LoveDo: liker outside seller community"
            );
        });

        it("Should revert when liker has different anchor community", async function () {
            await loveDoPostNFT.connect(user1).mintLoveDoPost(seller.address, "ipfs://test");
            const tokenId = (await loveDoPostNFT.nextTokenId()) - 1n;
            const otherNonce = await loveDoPostNFT.superlikeNonces(likerOther.address);

            await expectRevertWithMessage(
                loveDoPostNFT.connect(likerOther).addSuperlike(tokenId, otherNonce),
                "LoveDo: liker outside seller community"
            );
        });

        it("Should revert when user depth is below anchor L", async function () {
            await loveDoPostNFT.connect(user1).mintLoveDoPost(seller.address, "ipfs://test");
            const tokenId = (await loveDoPostNFT.nextTokenId()) - 1n;
            const rootNonce = await loveDoPostNFT.superlikeNonces(deployer.address);

            await expectRevertWithMessage(
                loveDoPostNFT.connect(deployer).addSuperlike(tokenId, rootNonce),
                "LoveDo: user depth below anchor"
            );
        });
    });

    describe("P3: Integration with Token Contracts", function () {
        it("Should correctly interact with Lovecoin contract", async function () {
            // Проверяем, что LoveEmissionEngine имеет MINTER_ROLE в Lovecoin
            const MINTER_ROLE = await lovecoin.MINTER_ROLE();
            expect(await lovecoin.hasRole(MINTER_ROLE, await loveEmissionEngine.getAddress())).to.be.true;
        });

        it("Should correctly interact with LGOV contract", async function () {
            // Проверяем, что LoveEmissionEngine имеет MINTER_ROLE в LGOV
            const LGOV_MINTER_ROLE = await lgovToken.MINTER_ROLE();
            expect(await lgovToken.hasRole(LGOV_MINTER_ROLE, await loveEmissionEngine.getAddress())).to.be.true;
        });
    });
});
