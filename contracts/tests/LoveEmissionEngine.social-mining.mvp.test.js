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

describe("LoveEmissionEngine social-mining MVP invariants", function () {
    let deployer;
    let emitter;
    let seller;
    let author;
    let liker;
    let lovecoin;
    let lgovToken;
    let inviteGraph;
    let loveDoPostNFT;
    let loveEmissionEngine;

    async function fundedWallet() {
        const w = ethers.Wallet.createRandom().connect(ethers.provider);
        await deployer.sendTransaction({ to: w.address, value: ethers.parseEther("1") });
        return w;
    }

    async function mintPostByAuthor(authorWallet, sellerAddress, uri = "ipfs://post") {
        return loveDoPostNFT.connect(authorWallet).mintLoveDoPost(sellerAddress, uri);
    }

    async function likeByLiker(likerWallet, tokenId) {
        const nonce = await loveDoPostNFT.superlikeNonces(likerWallet.address);
        return loveDoPostNFT.connect(likerWallet).addSuperlike(tokenId, nonce);
    }

    beforeEach(async function () {
        [deployer] = await ethers.getSigners();
        emitter = await fundedWallet();
        seller = await fundedWallet();
        author = await fundedWallet();
        liker = await fundedWallet();

        const Lovecoin = await ethers.getContractFactory("Lovecoin");
        lovecoin = await Lovecoin.deploy(deployer.address);
        await lovecoin.waitForDeployment();

        const AmanitaGovToken = await ethers.getContractFactory("AmanitaGovToken");
        lgovToken = await AmanitaGovToken.deploy(deployer.address);
        await lgovToken.waitForDeployment();

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

        const LoveEmissionEngine = await ethers.getContractFactory("LoveEmissionEngine");
        loveEmissionEngine = await LoveEmissionEngine.deploy(
            await lovecoin.getAddress(),
            await lgovToken.getAddress(),
            await loveDoPostNFT.getAddress(),
            await inviteGraph.getAddress(),
            deployer.address
        );
        await loveEmissionEngine.waitForDeployment();

        const EMITTER_ROLE = await loveEmissionEngine.EMITTER_ROLE();
        await loveEmissionEngine.connect(deployer).grantRole(EMITTER_ROLE, emitter.address);

        const MINTER_ROLE = await lovecoin.MINTER_ROLE();
        await lovecoin.connect(deployer).grantRole(MINTER_ROLE, await loveEmissionEngine.getAddress());

        const LGOV_MINTER_ROLE = await lgovToken.MINTER_ROLE();
        await lgovToken.connect(deployer).grantRole(LGOV_MINTER_ROLE, await loveEmissionEngine.getAddress());

        // Default graph: root=deployer, seller depth=1, author depth=2, liker depth=3.
        await inviteGraph.setInviter(seller.address, deployer.address);
        await inviteGraph.setInviter(author.address, seller.address);
        await inviteGraph.setInviter(liker.address, author.address);
    });

    it("P0: one valid superlike accrues EMISSION_RATE for LOVECOIN and LGOV", async function () {
        await mintPostByAuthor(author, seller.address);
        const tokenId = (await loveDoPostNFT.nextTokenId()) - 1n;
        await likeByLiker(liker, tokenId);

        await loveEmissionEngine.connect(emitter).emitForSuperlike(tokenId, liker.address);

        expect(await loveEmissionEngine.loveAccrued(seller.address)).to.equal(ethers.parseEther("1"));
        expect(await loveEmissionEngine.lgovAccrued(seller.address)).to.equal(ethers.parseEther("1"));
    });

    it("P0: depth-circle rejects liker from different anchor community", async function () {
        const otherAnchor = await fundedWallet();
        const otherLiker = await fundedWallet();
        await inviteGraph.setInviter(otherAnchor.address, deployer.address);
        await inviteGraph.setInviter(otherLiker.address, otherAnchor.address);

        await mintPostByAuthor(author, seller.address);
        const tokenId = (await loveDoPostNFT.nextTokenId()) - 1n;
        const nonce = await loveDoPostNFT.superlikeNonces(otherLiker.address);

        await expectRevertWithMessage(
            loveDoPostNFT.connect(otherLiker).addSuperlike(tokenId, nonce),
            "LoveDo: liker outside seller community"
        );
    });

    it("P0: depth-circle rejects liker when depth difference exceeds K", async function () {
        const far1 = await fundedWallet();
        const far2 = await fundedWallet();
        const far3 = await fundedWallet();
        const farLiker = await fundedWallet();

        await inviteGraph.setInviter(far1.address, seller.address);
        await inviteGraph.setInviter(far2.address, far1.address);
        await inviteGraph.setInviter(far3.address, far2.address);
        await inviteGraph.setInviter(farLiker.address, far3.address);

        await mintPostByAuthor(author, seller.address);
        const tokenId = (await loveDoPostNFT.nextTokenId()) - 1n;
        const nonce = await loveDoPostNFT.superlikeNonces(farLiker.address);

        await expectRevertWithMessage(
            loveDoPostNFT.connect(farLiker).addSuperlike(tokenId, nonce),
            "LoveDo: liker outside seller community"
        );
    });

    it("P0: anti-double-emit blocks second emission for same (tokenId, liker)", async function () {
        await mintPostByAuthor(author, seller.address);
        const tokenId = (await loveDoPostNFT.nextTokenId()) - 1n;
        await likeByLiker(liker, tokenId);

        await loveEmissionEngine.connect(emitter).emitForSuperlike(tokenId, liker.address);

        await expectRevertWithMessage(
            loveEmissionEngine.connect(emitter).emitForSuperlike(tokenId, liker.address),
            "LoveEmission: emission already processed for like"
        );
    });

    it("P0: LGOV threshold and one-shot claim are enforced", async function () {
        // < threshold
        for (let i = 0; i < 7; i++) {
            await mintPostByAuthor(author, seller.address, `ipfs://p-${i}`);
        }
        let tokenId = (await loveDoPostNFT.nextTokenId()) - 1n;
        await likeByLiker(liker, tokenId);
        await loveEmissionEngine.connect(emitter).emitForSuperlike(tokenId, liker.address);
        await expectRevertWithMessage(
            loveEmissionEngine.connect(seller).claimLGOV(),
            "LoveEmission: not enough LoveDo posts"
        );

        // >= threshold then one-shot
        await mintPostByAuthor(author, seller.address, "ipfs://p-7");
        tokenId = (await loveDoPostNFT.nextTokenId()) - 1n;
        await likeByLiker(liker, tokenId);
        await loveEmissionEngine.connect(emitter).emitForSuperlike(tokenId, liker.address);

        await loveEmissionEngine.connect(seller).claimLGOV();
        await expectRevert(loveEmissionEngine.connect(seller).claimLGOV());
    });

    it("P0: monthly post limit is enforced (8 pass, 9 revert)", async function () {
        const authorSingle = await fundedWallet();
        await inviteGraph.setInviter(authorSingle.address, seller.address);

        for (let i = 0; i < 8; i++) {
            const sellerI = await fundedWallet();
            await inviteGraph.setInviter(sellerI.address, deployer.address);
            await mintPostByAuthor(authorSingle, sellerI.address, `ipfs://mp-${i}`);
        }

        const seller9 = await fundedWallet();
        await inviteGraph.setInviter(seller9.address, deployer.address);
        await expectRevertWithMessage(
            mintPostByAuthor(authorSingle, seller9.address, "ipfs://mp-9"),
            "Monthly post limit reached"
        );
    });

    it("P0: monthly mention limit per seller is enforced (8 pass, 9 revert)", async function () {
        for (let i = 0; i < 8; i++) {
            const authorI = await fundedWallet();
            await inviteGraph.setInviter(authorI.address, seller.address);
            await mintPostByAuthor(authorI, seller.address, `ipfs://mm-${i}`);
        }

        const author9 = await fundedWallet();
        await inviteGraph.setInviter(author9.address, seller.address);
        await expectRevertWithMessage(
            mintPostByAuthor(author9, seller.address, "ipfs://mm-9"),
            "Seller mention limit reached"
        );
    });

    it("P0: monthly superlike limit per liker is enforced (8 pass, 9 revert)", async function () {
        const tokenIds = [];
        for (let i = 0; i < 8; i++) {
            const authorI = await fundedWallet();
            await inviteGraph.setInviter(authorI.address, seller.address);
            await mintPostByAuthor(authorI, seller.address, `ipfs://sl-${i}`);
            tokenIds.push((await loveDoPostNFT.nextTokenId()) - 1n);
        }

        for (const tokenId of tokenIds) {
            await likeByLiker(liker, tokenId);
        }

        const nonce = await loveDoPostNFT.superlikeNonces(liker.address);
        await expectRevert(loveDoPostNFT.connect(liker).addSuperlike(tokenIds[0], nonce));
    });
});

