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

describe("AmanitaCheckout repeated commerce cycles", function () {
    let deployer;
    let seller;
    let buyer;
    let checkout;
    let amanitaToken;
    let loveToken;
    let spiralEngine;

    const orderAmount = ethers.parseEther("10");
    const loveUnit = ethers.parseEther("1");
    let refNonce = 1;

    beforeEach(async function () {
        [deployer] = await ethers.getSigners();
        seller = ethers.Wallet.createRandom().connect(ethers.provider);
        buyer = ethers.Wallet.createRandom().connect(ethers.provider);
        await deployer.sendTransaction({ to: seller.address, value: ethers.parseEther("1") });
        await deployer.sendTransaction({ to: buyer.address, value: ethers.parseEther("1") });

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

        await spiralEngine.connect(deployer).mintInvite("REP-INV", 0);
        const codes = Array.from({ length: 12 }, (_, i) => `REP-${i}`);
        await spiralEngine.connect(deployer).activateUser("REP-INV", seller.address, codes, 0);
        await spiralEngine.connect(deployer).grantSellerRole(seller.address);

        // Create enough debt and balances for repeated order captures/cancellations.
        await amanitaToken.connect(seller).mint(seller.address, orderAmount * 5n);
        await amanitaToken.connect(deployer).transfer(buyer.address, orderAmount * 5n);
        await loveToken.mint(buyer.address, ethers.parseEther("300"));
        await amanitaToken.connect(buyer).approve(await checkout.getAddress(), ethers.MaxUint256);
        await loveToken.connect(buyer).approve(await checkout.getAddress(), ethers.MaxUint256);
    });

    async function createOrder(amount = orderAmount) {
        const ref = ethers.zeroPadValue(`0x${refNonce.toString(16).padStart(2, "0")}`, 32);
        refNonce += 1;
        const tx = await checkout.connect(buyer).createOrder(seller.address, amount, ref);
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

    it("keeps multi-order state isolation across paid/cancelled/created lanes", async function () {
        const debtStart = await amanitaToken.sellerDebt(seller.address);
        const buyerAmnStart = await amanitaToken.balanceOf(buyer.address);
        const buyerLoveStart = await loveToken.balanceOf(buyer.address);

        const paidHash = await createOrder();
        const cancelledHash = await createOrder();
        const openHash = await createOrder();

        // Order A: normal paid path.
        await checkout.connect(buyer).captureAmanitaCoin(paidHash, orderAmount / 2n);
        await checkout.connect(buyer).captureLoveCoin(paidHash, 3n * loveUnit);
        await checkout.connect(buyer).declareFullPayment(paidHash);
        await checkout.connect(seller).acceptFullPayment(paidHash);

        // Order B: mixed captures then cancel by writer.
        await checkout.connect(buyer).captureAmanitaCoin(cancelledHash, orderAmount / 3n);
        await checkout.connect(buyer).captureLoveCoin(cancelledHash, 5n * loveUnit);
        await checkout.connect(deployer).cancelOrder(cancelledHash);

        // Order C: keep open in Created with partial love funding only.
        await checkout.connect(buyer).captureLoveCoin(openHash, 2n * loveUnit);

        const paidOrder = await checkout.getOrder(paidHash);
        const cancelledOrder = await checkout.getOrder(cancelledHash);
        const openOrder = await checkout.getOrder(openHash);

        expect(paidOrder.status).to.equal(2n);
        expect(cancelledOrder.status).to.equal(4n);
        expect(openOrder.status).to.equal(1n);
        expect(openOrder.capturedLove).to.equal(2n * loveUnit);

        // Debt reflects only active AMN repayment left after cancel restoration.
        expect(await amanitaToken.sellerDebt(seller.address)).to.equal(debtStart - (orderAmount / 2n));
        // Buyer AMN decreases only by AMN actually captured in non-cancelled lane.
        expect(await amanitaToken.balanceOf(buyer.address)).to.equal(buyerAmnStart - (orderAmount / 2n));
        // Buyer LOVE net outflow = paid lane + open lane (cancelled lane refunded).
        expect(await loveToken.balanceOf(buyer.address)).to.equal(buyerLoveStart - (3n * loveUnit) - (2n * loveUnit));
    });

    it("enforces one-shot terminal guards per order while allowing new orders to progress", async function () {
        const cancelledHash = await createOrder();
        await checkout.connect(buyer).captureAmanitaCoin(cancelledHash, 1n);
        await checkout.connect(deployer).cancelOrder(cancelledHash);
        await expectRevertWithMessage(
            checkout.connect(buyer).captureLoveCoin(cancelledHash, 1n),
            "AmanitaCheckout: invalid status for capture",
        );
        await expectRevertWithMessage(
            checkout.connect(buyer).declareFullPayment(cancelledHash),
            "AmanitaCheckout: invalid status for declare",
        );

        const settledHash = await createOrder();
        await checkout.connect(buyer).captureAmanitaCoin(settledHash, orderAmount / 4n);
        await checkout.connect(buyer).declareFullPayment(settledHash);
        await checkout.connect(seller).acceptFullPayment(settledHash);
        await checkout.connect(deployer).markOrderSettled(settledHash);
        await expectRevertWithMessage(
            checkout.connect(deployer).cancelOrder(settledHash),
            "AmanitaCheckout: invalid transition to cancelled",
        );

        // A new order remains independent and can still complete.
        const freshHash = await createOrder();
        await checkout.connect(buyer).declareFullPayment(freshHash);
        await checkout.connect(seller).acceptFullPayment(freshHash);
        expect((await checkout.getOrder(freshHash)).status).to.equal(2n);
    });

    it("preserves debt and refund accounting across repeated cancel permutations", async function () {
        const debtStart = await amanitaToken.sellerDebt(seller.address);
        const buyerAmnStart = await amanitaToken.balanceOf(buyer.address);
        const buyerLoveStart = await loveToken.balanceOf(buyer.address);

        const h1 = await createOrder();
        const h2 = await createOrder();
        const h3 = await createOrder();

        // h1: AMN-only capture + cancel => debt restored, buyer AMN refunded.
        await checkout.connect(buyer).captureAmanitaCoin(h1, orderAmount / 2n);
        await checkout.connect(deployer).cancelOrder(h1);

        // h2: LOVE-only capture + self-cancel => love refunded.
        await checkout.connect(buyer).captureLoveCoin(h2, 7n * loveUnit);
        await checkout.connect(buyer).cancelOwnOrder(h2);

        // h3: mixed capture + declare + cancel => both legs compensated.
        await checkout.connect(buyer).captureAmanitaCoin(h3, orderAmount / 5n);
        await checkout.connect(buyer).captureLoveCoin(h3, 4n * loveUnit);
        await checkout.connect(buyer).declareFullPayment(h3);
        await checkout.connect(deployer).cancelOrder(h3);

        expect(await amanitaToken.sellerDebt(seller.address)).to.equal(debtStart);
        expect(await amanitaToken.balanceOf(buyer.address)).to.equal(buyerAmnStart);
        expect(await loveToken.balanceOf(buyer.address)).to.equal(buyerLoveStart);
        expect(await amanitaToken.orderDebtRepaid(h1)).to.equal(0n);
        expect(await amanitaToken.orderDebtRepaid(h3)).to.equal(0n);
        expect(await amanitaToken.orderBuyerRefunded(h1)).to.equal(true);
        expect(await amanitaToken.orderBuyerRefunded(h3)).to.equal(true);
    });
});

