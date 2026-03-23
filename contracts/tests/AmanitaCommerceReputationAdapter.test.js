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

describe("AmanitaCommerceReputationAdapter live + anchor", function () {
    let deployer;
    let seller;
    let buyer;
    let outsider;
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
        outsider = ethers.Wallet.createRandom().connect(ethers.provider);
        for (const w of [seller, buyer, outsider]) {
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

        const SELLER_ROLE = await spiralEngine.SELLER_ROLE();
        await spiralEngine.connect(deployer).mintInvite("REP-INV", 0);
        const codes = Array.from({ length: 12 }, (_, i) => `REP-${i}`);
        await spiralEngine.connect(deployer).activateUser("REP-INV", seller.address, codes, 0);
        await spiralEngine.connect(deployer).grantSellerRole(seller.address);
        await amanitaToken.connect(seller).mint(seller.address, orderAmount);
        await amanitaToken.connect(deployer).transfer(buyer.address, orderAmount * 2n);
        await loveToken.mint(buyer.address, ethers.parseEther("100"));
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

    it("increments live redemption metrics on each Amanita capture", async function () {
        const h = await createOrder(0x01);
        const half = orderAmount / 2n;
        await checkout.connect(buyer).captureAmanitaCoin(h, half);

        let m = await adapter.getLiveMetrics(seller.address);
        expect(m.sellerRedemptionCount).to.equal(1n);
        expect(m.sellerTotalRedeemedAmount).to.equal(half);
        expect(m.sellerLastRedemptionAt > 0n).to.be.true;

        await checkout.connect(buyer).captureAmanitaCoin(h, half);
        m = await adapter.getLiveMetrics(seller.address);
        expect(m.sellerRedemptionCount).to.equal(2n);
        expect(m.sellerTotalRedeemedAmount).to.equal(orderAmount);
    });

    it("increments successful orders on markOrderSettled only", async function () {
        const h = await createOrder(0x02);
        await checkout.connect(buyer).declareFullPayment(h);
        await checkout.connect(seller).acceptFullPayment(h);
        let m = await adapter.getLiveMetrics(seller.address);
        expect(m.sellerSuccessfulOrdersCount).to.equal(0n);

        await checkout.connect(deployer).markOrderSettled(h);
        m = await adapter.getLiveMetrics(seller.address);
        expect(m.sellerSuccessfulOrdersCount).to.equal(1n);
    });

    it("anchorSeller freezes snapshot; live can diverge", async function () {
        const h = await createOrder(0x03);
        await checkout.connect(buyer).captureAmanitaCoin(h, orderAmount);
        await checkout.connect(buyer).declareFullPayment(h);
        await checkout.connect(seller).acceptFullPayment(h);
        await checkout.connect(deployer).markOrderSettled(h);

        await adapter.connect(deployer).anchorSeller(seller.address);
        const snap = await adapter.getAnchoredSnapshot(seller.address);
        expect(snap.anchoredAt > 0n).to.be.true;
        expect(snap.metrics.sellerRedemptionCount).to.equal(1n);
        expect(snap.metrics.sellerSuccessfulOrdersCount).to.equal(1n);
        expect(snap.metrics.sellerSettledWithBuyerDeclareCount).to.equal(1n);
        expect(snap.metrics.sellerSettledWithoutSellerAcceptCount).to.equal(0n);

        const h2 = await createOrder(0x04);
        await checkout.connect(buyer).captureAmanitaCoin(h2, ethers.parseEther("1"));
        const live = await adapter.getLiveMetrics(seller.address);
        expect(live.sellerRedemptionCount).to.equal(2n);
        const snap2 = await adapter.getAnchoredSnapshot(seller.address);
        expect(snap2.metrics.sellerRedemptionCount).to.equal(1n);
    });

    it("rejects notify from non-checkout", async function () {
        await expectRevertWithMessage(
            adapter.connect(outsider).notifyAmanitaRedemption(seller.address, 1n),
            "CommerceReputation: only checkout",
        );
        await expectRevertWithMessage(
            adapter
                .connect(outsider)
                .notifyOrderSettled(seller.address, buyer.address, true, true, false),
            "CommerceReputation: only checkout",
        );
        await expectRevertWithMessage(
            adapter.connect(outsider).notifyWeakExternalPaymentClaim(buyer.address, seller.address),
            "CommerceReputation: only checkout",
        );
    });

    it("AMN-2.6: buyer confirmed received updates buyer metrics; bps views", async function () {
        const h = await createOrder(0x10);
        await checkout.connect(deployer).markOrderPaid(h);
        await checkout.connect(buyer).confirmOrderReceived(h);
        await checkout.connect(deployer).markOrderSettled(h);

        const b = await adapter.getLiveBuyerMetrics(buyer.address);
        expect(b.settledReceivedCount).to.equal(1n);
        expect(b.settledReceivedMissingDeclareCount).to.equal(1n);
        expect(await adapter.getBuyerReceivedWithoutDeclareBps(buyer.address)).to.equal(10000n);

        const m = await adapter.getLiveMetrics(seller.address);
        expect(m.sellerSettledWithBuyerDeclareCount).to.equal(0n);
    });

    it("AMN-2.6: attestation path + confirm → buyer missing-declare bps zero", async function () {
        const h = await createOrder(0x11);
        await checkout.connect(buyer).declareFullPayment(h);
        await checkout.connect(seller).acceptFullPayment(h);
        await checkout.connect(buyer).confirmOrderReceived(h);
        await checkout.connect(deployer).markOrderSettled(h);

        const b = await adapter.getLiveBuyerMetrics(buyer.address);
        expect(b.settledReceivedCount).to.equal(1n);
        expect(b.settledReceivedMissingDeclareCount).to.equal(0n);
        expect(await adapter.getBuyerReceivedWithoutDeclareBps(buyer.address)).to.equal(0n);

        const m = await adapter.getLiveMetrics(seller.address);
        expect(m.sellerSettledWithBuyerDeclareCount).to.equal(1n);
        expect(m.sellerSettledWithoutSellerAcceptCount).to.equal(0n);
    });

    it("AMN-2.6: declare then emergency paid → seller unsettled-after-declare bps 10000", async function () {
        const h = await createOrder(0x12);
        await checkout.connect(buyer).declareFullPayment(h);
        await checkout.connect(deployer).markOrderPaid(h);
        await checkout.connect(deployer).markOrderSettled(h);

        expect(await adapter.getSellerUnsettledAfterDeclareBps(seller.address)).to.equal(10000n);
    });

    it("AMN-2.6: weak external claim increments buyer counter", async function () {
        const h = await createOrder(0x13);
        await checkout.connect(buyer).signalWeakExternalPaymentClaim(h);
        const b = await adapter.getLiveBuyerMetrics(buyer.address);
        expect(b.weakExternalClaimCount).to.equal(1n);
    });

    it("anchorBuyer freezes buyer signal snapshot", async function () {
        const h = await createOrder(0x14);
        await checkout.connect(buyer).signalWeakExternalPaymentClaim(h);
        await adapter.connect(deployer).anchorBuyer(buyer.address);
        const snap = await adapter.getAnchoredBuyerSnapshot(buyer.address);
        expect(snap.anchoredAt > 0n).to.be.true;
        expect(snap.metrics.weakExternalClaimCount).to.equal(1n);

        const h2 = await createOrder(0x15);
        await checkout.connect(buyer).signalWeakExternalPaymentClaim(h2);
        const live = await adapter.getLiveBuyerMetrics(buyer.address);
        expect(live.weakExternalClaimCount).to.equal(2n);
        const snap2 = await adapter.getAnchoredBuyerSnapshot(buyer.address);
        expect(snap2.metrics.weakExternalClaimCount).to.equal(1n);
    });

    it("AMN-2.4 qualification: cancel/refund does not count as successful commerce settlement", async function () {
        const h = await createOrder(0x16);
        const amnPart = orderAmount / 2n;
        await checkout.connect(buyer).captureAmanitaCoin(h, amnPart);
        await checkout.connect(buyer).captureLoveCoin(h, ethers.parseEther("2"));
        await checkout.connect(buyer).signalWeakExternalPaymentClaim(h);
        await checkout.connect(deployer).cancelOrder(h);

        const sellerMetrics = await adapter.getLiveMetrics(seller.address);
        expect(sellerMetrics.sellerRedemptionCount).to.equal(1n);
        expect(sellerMetrics.sellerSuccessfulOrdersCount).to.equal(0n);
        expect(sellerMetrics.sellerSettledWithBuyerDeclareCount).to.equal(0n);
        expect(sellerMetrics.sellerSettledWithoutSellerAcceptCount).to.equal(0n);

        const buyerMetrics = await adapter.getLiveBuyerMetrics(buyer.address);
        expect(buyerMetrics.weakExternalClaimCount).to.equal(1n);
        expect(buyerMetrics.settledReceivedCount).to.equal(0n);
        expect(buyerMetrics.settledReceivedMissingDeclareCount).to.equal(0n);
    });

    it("recordRefund and recordDispute update live counters", async function () {
        const REPUTATION_OPS_ROLE = await adapter.REPUTATION_OPS_ROLE();
        await adapter.connect(deployer).grantRole(REPUTATION_OPS_ROLE, outsider.address);
        await adapter.connect(outsider).recordRefund(seller.address);
        await adapter.connect(outsider).recordDispute(seller.address);
        const m = await adapter.getLiveMetrics(seller.address);
        expect(m.sellerRefundCount).to.equal(1n);
        expect(m.sellerDisputeCount).to.equal(1n);
    });

    it("admin can rotate checkout address", async function () {
        await adapter.connect(deployer).setCheckout(outsider.address);
        expect(await adapter.checkout()).to.equal(outsider.address);
    });
});
