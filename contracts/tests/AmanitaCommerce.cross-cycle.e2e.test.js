const { expect } = require("chai");
const { ethers } = require("hardhat");

describe("Cross-cycle E2E: Spiral -> Checkout -> Reputation anchor progression", function () {
    let deployer;
    let seller;
    let buyer;
    let spiralEngine;
    let amanitaToken;
    let loveToken;
    let checkout;
    let adapter;
    const orderAmount = ethers.parseEther("10");

    beforeEach(async function () {
        [deployer] = await ethers.getSigners();
        seller = ethers.Wallet.createRandom().connect(ethers.provider);
        buyer = ethers.Wallet.createRandom().connect(ethers.provider);
        for (const w of [seller, buyer]) {
            await deployer.sendTransaction({ to: w.address, value: ethers.parseEther("1") });
        }

        const SpiralEngine = await ethers.getContractFactory("SpiralEngine");
        spiralEngine = await SpiralEngine.connect(deployer).deploy();
        await spiralEngine.waitForDeployment();

        const AmanitaToken = await ethers.getContractFactory("AmanitaToken");
        amanitaToken = await AmanitaToken.connect(deployer).deploy(deployer.address);
        await amanitaToken.waitForDeployment();
        await amanitaToken.connect(deployer).setSpiralEngine(await spiralEngine.getAddress());

        const MockERC20 = await ethers.getContractFactory("MockERC20");
        loveToken = await MockERC20.connect(deployer).deploy("Love", "LOVE");
        await loveToken.waitForDeployment();

        const AmanitaCheckout = await ethers.getContractFactory("AmanitaCheckout");
        checkout = await AmanitaCheckout.connect(deployer).deploy(
            deployer.address,
            await amanitaToken.getAddress(),
            await loveToken.getAddress(),
        );
        await checkout.waitForDeployment();
        await amanitaToken.connect(deployer).setAmanitaCheckout(await checkout.getAddress());

        const Adapter = await ethers.getContractFactory("AmanitaCommerceReputationAdapter");
        adapter = await Adapter.connect(deployer).deploy(deployer.address, await checkout.getAddress());
        await adapter.waitForDeployment();
        await checkout.connect(deployer).setReputationHooks(await adapter.getAddress());

        // Spiral preparation.
        await spiralEngine.connect(deployer).mintInvite("E2E-INV", 0);
        await spiralEngine.connect(deployer).activateUser("E2E-INV", seller.address, Array.from({ length: 12 }, (_, i) => `E2E-${i}`), 0);
        await spiralEngine.connect(deployer).grantSellerRole(seller.address);

        // Commerce balances.
        await amanitaToken.connect(seller).mint(seller.address, orderAmount * 3n);
        await amanitaToken.connect(deployer).transfer(buyer.address, orderAmount * 3n);
        await loveToken.mint(buyer.address, ethers.parseEther("50"));
        await amanitaToken.connect(buyer).approve(await checkout.getAddress(), ethers.MaxUint256);
        await loveToken.connect(buyer).approve(await checkout.getAddress(), ethers.MaxUint256);
    });

    async function createOrder(refByte) {
        const ref = ethers.zeroPadValue(`0x${refByte.toString(16).padStart(2, "0")}`, 32);
        const tx = await checkout.connect(buyer).createOrder(seller.address, orderAmount, ref);
        const receipt = await tx.wait();
        const ev = receipt.logs
            .map((l) => {
                try {
                    return checkout.interface.parseLog(l);
                } catch {
                    return null;
                }
            })
            .find((e) => e && e.name === "OrderCreated");
        return ev.args.orderHash;
    }

    it("preserves coherent progression from activation to anchor snapshots", async function () {
        const [isActivated, hasSellerRole] = await spiralEngine.getSellerPublicInfo(seller.address);
        expect(isActivated).to.equal(true);
        expect(hasSellerRole).to.equal(true);

        const h1 = await createOrder(0x01);
        await checkout.connect(buyer).captureAmanitaCoin(h1, orderAmount / 2n);
        await checkout.connect(buyer).captureLoveCoin(h1, ethers.parseEther("2"));
        await checkout.connect(buyer).declareFullPayment(h1);
        await checkout.connect(seller).acceptFullPayment(h1);
        await checkout.connect(buyer).confirmOrderReceived(h1);
        await checkout.connect(deployer).markOrderSettled(h1);

        const sellerLiveAfterH1 = await adapter.getLiveMetrics(seller.address);
        const buyerLiveAfterH1 = await adapter.getLiveBuyerMetrics(buyer.address);
        expect(sellerLiveAfterH1.sellerRedemptionCount).to.equal(1n);
        expect(sellerLiveAfterH1.sellerSuccessfulOrdersCount).to.equal(1n);
        expect(sellerLiveAfterH1.sellerSettledWithBuyerDeclareCount).to.equal(1n);
        expect(buyerLiveAfterH1.settledReceivedCount).to.equal(1n);
        expect(buyerLiveAfterH1.settledReceivedMissingDeclareCount).to.equal(0n);

        await adapter.connect(deployer).anchorSeller(seller.address);
        await adapter.connect(deployer).anchorBuyer(buyer.address);
        const sellerSnap1 = await adapter.getAnchoredSnapshot(seller.address);
        const buyerSnap1 = await adapter.getAnchoredBuyerSnapshot(buyer.address);
        expect(sellerSnap1.anchoredAt > 0n).to.equal(true);
        expect(buyerSnap1.anchoredAt > 0n).to.equal(true);
        expect(sellerSnap1.metrics.sellerSuccessfulOrdersCount).to.equal(1n);
        expect(buyerSnap1.metrics.settledReceivedCount).to.equal(1n);

        const h2 = await createOrder(0x02);
        await checkout.connect(buyer).signalWeakExternalPaymentClaim(h2);
        await checkout.connect(buyer).declareFullPayment(h2);
        await checkout.connect(deployer).markOrderPaid(h2);
        await checkout.connect(deployer).markOrderSettled(h2);

        const sellerLiveAfterH2 = await adapter.getLiveMetrics(seller.address);
        const buyerLiveAfterH2 = await adapter.getLiveBuyerMetrics(buyer.address);
        expect(sellerLiveAfterH2.sellerSuccessfulOrdersCount).to.equal(2n);
        expect(sellerLiveAfterH2.sellerSettledWithBuyerDeclareCount).to.equal(2n);
        expect(sellerLiveAfterH2.sellerSettledWithoutSellerAcceptCount).to.equal(1n);
        expect(await adapter.getSellerUnsettledAfterDeclareBps(seller.address)).to.equal(5000n);
        expect(buyerLiveAfterH2.weakExternalClaimCount).to.equal(1n);
        expect(buyerLiveAfterH2.settledReceivedCount).to.equal(1n);

        const sellerSnapStill = await adapter.getAnchoredSnapshot(seller.address);
        const buyerSnapStill = await adapter.getAnchoredBuyerSnapshot(buyer.address);
        expect(sellerSnapStill.metrics.sellerSuccessfulOrdersCount).to.equal(1n);
        expect(buyerSnapStill.metrics.weakExternalClaimCount).to.equal(0n);

        await adapter.connect(deployer).anchorSeller(seller.address);
        await adapter.connect(deployer).anchorBuyer(buyer.address);
        const sellerSnap2 = await adapter.getAnchoredSnapshot(seller.address);
        const buyerSnap2 = await adapter.getAnchoredBuyerSnapshot(buyer.address);
        expect(sellerSnap2.metrics.sellerSuccessfulOrdersCount).to.equal(2n);
        expect(sellerSnap2.metrics.sellerSettledWithoutSellerAcceptCount).to.equal(1n);
        expect(buyerSnap2.metrics.weakExternalClaimCount).to.equal(1n);
    });
});

