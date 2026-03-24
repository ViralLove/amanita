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
    if (messageSubstring) {
        expect(msg.includes(messageSubstring), `expected revert message to contain "${messageSubstring}"`).to.be.true;
    }
}

function makeCodes(prefix, n = 12) {
    return Array.from({ length: n }, (_, i) => `${prefix}-${i + 1}-${Date.now()}`);
}

describe("LoveEmissionEngine real social-mining cluster integration", function () {
    let deployer;
    let seller;
    let author;
    let liker;
    let outsider;
    let emitter;

    let spiral;
    let inviteAdapter;
    let sellerRegistryAdapter;
    let loveDo;
    let lovecoin;
    let govToken;
    let engine;

    beforeEach(async function () {
        [deployer] = await ethers.getSigners();
        seller = ethers.Wallet.createRandom().connect(ethers.provider);
        author = ethers.Wallet.createRandom().connect(ethers.provider);
        liker = ethers.Wallet.createRandom().connect(ethers.provider);
        outsider = ethers.Wallet.createRandom().connect(ethers.provider);
        emitter = ethers.Wallet.createRandom().connect(ethers.provider);

        for (const w of [seller, author, liker, outsider, emitter]) {
            await deployer.sendTransaction({ to: w.address, value: ethers.parseEther("2") });
        }

        const SpiralEngine = await ethers.getContractFactory("SpiralEngine");
        spiral = await SpiralEngine.deploy();
        await spiral.waitForDeployment();

        // Adapters connect LoveDo interfaces to real SpiralEngine state.
        const InviteAdapter = await ethers.getContractFactory("SpiralInviteGraphAdapterMock");
        inviteAdapter = await InviteAdapter.deploy(await spiral.getAddress());
        await inviteAdapter.waitForDeployment();

        const SellerRegistryAdapter = await ethers.getContractFactory("SpiralSellerRegistryAdapterMock");
        sellerRegistryAdapter = await SellerRegistryAdapter.deploy(await spiral.getAddress());
        await sellerRegistryAdapter.waitForDeployment();

        const LoveDoPostNFT = await ethers.getContractFactory("LoveDoPostNFT");
        loveDo = await LoveDoPostNFT.deploy(
            deployer.address,
            await inviteAdapter.getAddress(),
            await sellerRegistryAdapter.getAddress()
        );
        await loveDo.waitForDeployment();

        const Lovecoin = await ethers.getContractFactory("Lovecoin");
        lovecoin = await Lovecoin.deploy(deployer.address);
        await lovecoin.waitForDeployment();

        const AmanitaGovToken = await ethers.getContractFactory("AmanitaGovToken");
        govToken = await AmanitaGovToken.deploy(deployer.address);
        await govToken.waitForDeployment();

        const LoveEmissionEngine = await ethers.getContractFactory("LoveEmissionEngine");
        engine = await LoveEmissionEngine.deploy(
            await lovecoin.getAddress(),
            await govToken.getAddress(),
            await loveDo.getAddress(),
            await inviteAdapter.getAddress(),
            deployer.address
        );
        await engine.waitForDeployment();

        const EMITTER_ROLE = await engine.EMITTER_ROLE();
        await engine.connect(deployer).grantRole(EMITTER_ROLE, emitter.address);

        const LOVE_MINTER_ROLE = await lovecoin.MINTER_ROLE();
        await lovecoin.connect(deployer).grantRole(LOVE_MINTER_ROLE, await engine.getAddress());

        const GOV_MINTER_ROLE = await govToken.MINTER_ROLE();
        await govToken.connect(deployer).grantRole(GOV_MINTER_ROLE, await engine.getAddress());

        // Build real SpiralEngine invite graph:
        // deployer -> seller -> {author, liker}
        await spiral.connect(deployer).mintInvite("INV-SELLER", 0);
        await spiral.connect(deployer).activateUser("INV-SELLER", seller.address, makeCodes("SELLER"), 0);
        await spiral.connect(deployer).grantSellerRole(seller.address);
        const ACTIVATOR_ROLE = await spiral.ACTIVATOR_ROLE();
        await spiral.connect(deployer).grantRole(ACTIVATOR_ROLE, seller.address);

        await spiral.connect(seller).mintInvite("INV-AUTHOR", 0);
        await spiral.connect(seller).activateUser("INV-AUTHOR", author.address, makeCodes("AUTHOR"), 0);

        await spiral.connect(seller).mintInvite("INV-LIKER", 0);
        await spiral.connect(seller).activateUser("INV-LIKER", liker.address, makeCodes("LIKER"), 0);
    });

    it("Should process real-path superlike -> emission -> utility claim", async function () {
        await loveDo.connect(author).mintLoveDoPost(seller.address, "ipfs://real-path-post");
        const tokenId = (await loveDo.nextTokenId()) - 1n;
        const nonce = await loveDo.superlikeNonces(liker.address);
        await loveDo.connect(liker).addSuperlike(tokenId, nonce);

        await engine.connect(emitter).emitForSuperlike(tokenId, liker.address);

        expect(await engine.loveAccrued(seller.address)).to.equal(ethers.parseEther("1"));
        expect(await engine.lgovAccrued(seller.address)).to.equal(ethers.parseEther("1"));

        await lovecoin.connect(deployer).transfer(await engine.getAddress(), ethers.parseEther("100"));
        await engine.connect(seller).claimLOVECOIN();
        expect(await lovecoin.balanceOf(seller.address)).to.equal(ethers.parseEther("1"));
    });

    it("Should enforce superlike nonce boundary in real cluster path", async function () {
        await loveDo.connect(author).mintLoveDoPost(seller.address, "ipfs://nonce-boundary");
        const tokenId = (await loveDo.nextTokenId()) - 1n;
        const wrongNonce = 999n;

        await expectRevertWithMessage(loveDo.connect(liker).addSuperlike(tokenId, wrongNonce));
    });

    it("Should enforce invite/community boundary for non-invited liker", async function () {
        await loveDo.connect(author).mintLoveDoPost(seller.address, "ipfs://community-boundary");
        const tokenId = (await loveDo.nextTokenId()) - 1n;
        const nonce = await loveDo.superlikeNonces(outsider.address);

        await expectRevertWithMessage(
            loveDo.connect(outsider).addSuperlike(tokenId, nonce),
            "LoveDo: user depth below anchor"
        );
    });
});

