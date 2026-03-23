const { expect } = require("chai");
const { ethers } = require("hardhat");

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

describe("AmanitaCheckout composite funding and attestation-gated Paid", function () {
    let deployer;
    let seller;
    let buyer;
    let checkout;
    let amanitaToken;
    let loveToken;
    let spiralEngine;
    const orderAmount = ethers.parseEther("10");

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

        const SELLER_ROLE = await spiralEngine.SELLER_ROLE();
        await spiralEngine.connect(deployer).mintInvite("COMP-INV", 0);
        const codes = Array.from({ length: 12 }, (_, i) => `COMP-${i}`);
        await spiralEngine.connect(deployer).activateUser("COMP-INV", seller.address, codes, 0);
        await spiralEngine.connect(deployer).grantSellerRole(seller.address);

        await amanitaToken.connect(seller).mint(seller.address, orderAmount);
        expect(await amanitaToken.sellerDebt(seller.address)).to.equal(orderAmount);

        await amanitaToken.connect(deployer).transfer(buyer.address, orderAmount);
        await loveToken.mint(buyer.address, ethers.parseEther("100"));
        await amanitaToken.connect(buyer).approve(await checkout.getAddress(), ethers.MaxUint256);
        await loveToken.connect(buyer).approve(await checkout.getAddress(), ethers.MaxUint256);
    });

    async function createOrder(refByte) {
        const ref = ethers.zeroPadValue(`0x${refByte.toString(16).padStart(2, "0")}`, 32);
        const tx = await checkout.connect(buyer).createOrder(seller.address, orderAmount, ref);
        const receipt = await tx.wait();
        const parsed = receipt.logs
            .map((l) => {
                try {
                    return checkout.interface.parseLog(l);
                } catch {
                    return null;
                }
            })
            .find((e) => e && e.name === "OrderCreated");
        return parsed.args.orderHash;
    }

    it("does not reach Paid from capture alone (AMN + Love) — needs declare + accept", async function () {
        const orderHash = await createOrder(0x01);
        const half = orderAmount / 2n;
        await checkout.connect(buyer).captureAmanitaCoin(orderHash, half);
        await checkout.connect(buyer).captureAmanitaCoin(orderHash, half);
        await checkout.connect(buyer).captureLoveCoin(orderHash, ethers.parseEther("5"));

        let order = await checkout.getOrder(orderHash);
        expect(order.status).to.equal(1n);
        expect(order.capturedAmanita).to.equal(orderAmount);
        expect(order.capturedLove).to.equal(ethers.parseEther("5"));

        await expectRevertWithMessage(
            checkout.connect(seller).acceptFullPayment(orderHash),
            "AmanitaCheckout: full payment not declared",
        );

        await checkout.connect(buyer).declareFullPayment(orderHash);
        await checkout.connect(seller).acceptFullPayment(orderHash);
        order = await checkout.getOrder(orderHash);
        expect(order.status).to.equal(2n);
    });

    it("reduces sellerDebt on Amanita captures; Love capture does not change debt", async function () {
        const orderHash = await createOrder(0x02);
        const debtBefore = await amanitaToken.sellerDebt(seller.address);

        await checkout.connect(buyer).captureLoveCoin(orderHash, ethers.parseEther("20"));
        expect(await amanitaToken.sellerDebt(seller.address)).to.equal(debtBefore);

        const part = orderAmount / 2n;
        await checkout.connect(buyer).captureAmanitaCoin(orderHash, part);
        expect(await amanitaToken.sellerDebt(seller.address)).to.equal(debtBefore - part);

        await checkout.connect(buyer).captureAmanitaCoin(orderHash, part);
        expect(await amanitaToken.sellerDebt(seller.address)).to.equal(0n);

        await checkout.connect(buyer).declareFullPayment(orderHash);
        await checkout.connect(seller).acceptFullPayment(orderHash);
    });

    it("external leg only: declare + accept without any capture reaches Paid", async function () {
        const orderHash = await createOrder(0x03);
        const order = await checkout.getOrder(orderHash);
        expect(order.capturedAmanita).to.equal(0n);
        expect(order.capturedLove).to.equal(0n);

        await checkout.connect(buyer).declareFullPayment(orderHash);
        await checkout.connect(seller).acceptFullPayment(orderHash);
        expect((await checkout.getOrder(orderHash)).status).to.equal(2n);
    });

    it("reverts capture after declare, Paid, or cancel", async function () {
        const h1 = await createOrder(0x10);
        await checkout.connect(buyer).declareFullPayment(h1);
        await expectRevertWithMessage(
            checkout.connect(buyer).captureAmanitaCoin(h1, 1n),
            "AmanitaCheckout: funding locked after declare",
        );

        const h2 = await createOrder(0x11);
        await checkout.connect(buyer).declareFullPayment(h2);
        await checkout.connect(seller).acceptFullPayment(h2);
        await expectRevertWithMessage(
            checkout.connect(buyer).captureAmanitaCoin(h2, 1n),
            "AmanitaCheckout: invalid status for capture",
        );

        const h3 = await createOrder(0x12);
        await checkout.connect(buyer).cancelOwnOrder(h3);
        await expectRevertWithMessage(
            checkout.connect(buyer).captureLoveCoin(h3, 1n),
            "AmanitaCheckout: invalid status for capture",
        );
    });

    it("reverts amanita capture exceeding order.amount", async function () {
        const orderHash = await createOrder(0x20);
        await checkout.connect(buyer).captureAmanitaCoin(orderHash, orderAmount);
        await expectRevertWithMessage(
            checkout.connect(buyer).captureAmanitaCoin(orderHash, 1n),
            "AmanitaCheckout: amanita exceeds order amount",
        );
    });

    it("rejects wrong actors for declare/accept and double declare", async function () {
        const orderHash = await createOrder(0x30);
        await expectRevertWithMessage(
            checkout.connect(seller).declareFullPayment(orderHash),
            "AmanitaCheckout: only buyer",
        );
        await checkout.connect(buyer).declareFullPayment(orderHash);
        await expectRevertWithMessage(
            checkout.connect(buyer).declareFullPayment(orderHash),
            "AmanitaCheckout: already declared",
        );
        await expectRevertWithMessage(
            checkout.connect(buyer).acceptFullPayment(orderHash),
            "AmanitaCheckout: only seller",
        );
    });

    it("rejects accept without declare", async function () {
        const orderHash = await createOrder(0x31);
        await expectRevertWithMessage(
            checkout.connect(seller).acceptFullPayment(orderHash),
            "AmanitaCheckout: full payment not declared",
        );
    });

    it("AMN-2.7: cancelOwnOrder auto-refunds Love escrow to buyer", async function () {
        const orderHash = await createOrder(0x40);
        const loveAmount = ethers.parseEther("7");
        const debtBefore = await amanitaToken.sellerDebt(seller.address);
        await checkout.connect(buyer).captureLoveCoin(orderHash, loveAmount);
        const buyerLoveBefore = await loveToken.balanceOf(buyer.address);

        await checkout.connect(buyer).cancelOwnOrder(orderHash);

        const buyerLoveAfter = await loveToken.balanceOf(buyer.address);
        expect(buyerLoveAfter - buyerLoveBefore).to.equal(loveAmount);
        expect(await amanitaToken.sellerDebt(seller.address)).to.equal(debtBefore);
        const order = await checkout.getOrder(orderHash);
        expect(order.status).to.equal(4n);
        expect(order.capturedLove).to.equal(0n);
    });

    it("AMN-2.7: cancel restores sellerDebt by order repaid AMN amount", async function () {
        const orderHash = await createOrder(0x41);
        const debtBefore = await amanitaToken.sellerDebt(seller.address);
        const buyerAmnBefore = await amanitaToken.balanceOf(buyer.address);
        const part = orderAmount / 2n;
        await checkout.connect(buyer).captureAmanitaCoin(orderHash, part);
        expect(await amanitaToken.sellerDebt(seller.address)).to.equal(debtBefore - part);

        await checkout.connect(deployer).cancelOrder(orderHash);
        expect(await amanitaToken.sellerDebt(seller.address)).to.equal(debtBefore);
        expect(await amanitaToken.orderDebtRepaid(orderHash)).to.equal(0n);
        expect(await amanitaToken.balanceOf(buyer.address)).to.equal(buyerAmnBefore);
        expect(await amanitaToken.orderBuyerRefunded(orderHash)).to.equal(true);
        const order = await checkout.getOrder(orderHash);
        expect(order.capturedAmanita).to.equal(0n);
    });

    it("AMN-2.7: cancel after mixed AMN+Love refunds love and restores debt", async function () {
        const orderHash = await createOrder(0x42);
        const debtBefore = await amanitaToken.sellerDebt(seller.address);
        const buyerAmnBefore = await amanitaToken.balanceOf(buyer.address);
        const buyerLoveBefore = await loveToken.balanceOf(buyer.address);
        const amnPart = orderAmount / 2n;
        const lovePart = ethers.parseEther("3");
        await checkout.connect(buyer).captureAmanitaCoin(orderHash, amnPart);
        await checkout.connect(buyer).captureLoveCoin(orderHash, lovePart);
        await checkout.connect(buyer).declareFullPayment(orderHash);
        await checkout.connect(deployer).cancelOrder(orderHash);

        expect(await amanitaToken.sellerDebt(seller.address)).to.equal(debtBefore);
        expect(await amanitaToken.balanceOf(buyer.address)).to.equal(buyerAmnBefore);
        expect(await loveToken.balanceOf(buyer.address)).to.equal(buyerLoveBefore);
        const order = await checkout.getOrder(orderHash);
        expect(order.capturedAmanita).to.equal(0n);
        expect(order.capturedLove).to.equal(0n);
    });

    it("AMN-2.8: emits BuyerOrderAmnRefunded with capturedAmanita amount", async function () {
        const orderHash = await createOrder(0x43);
        const part = orderAmount / 2n;
        await checkout.connect(buyer).captureAmanitaCoin(orderHash, part);
        const tx = await checkout.connect(deployer).cancelOrder(orderHash);
        const receipt = await tx.wait();
        const ev = receipt.logs
            .map((l) => {
                try {
                    return checkout.interface.parseLog(l);
                } catch {
                    return null;
                }
            })
            .find((e) => e && e.name === "BuyerOrderAmnRefunded");
        expect(ev).to.not.equal(undefined);
        expect(ev.args.orderHash).to.equal(orderHash);
        expect(ev.args.buyer).to.equal(buyer.address);
        expect(ev.args.amount).to.equal(part);
    });

    it("AMN-2.4 qualification: AMN cancel emits paired refund events with same amount", async function () {
        const orderHash = await createOrder(0x44);
        const part = orderAmount / 2n;
        const tx1 = await checkout.connect(buyer).captureAmanitaCoin(orderHash, part);
        await tx1.wait();

        const tx2 = await checkout.connect(deployer).cancelOrder(orderHash);
        const receipt = await tx2.wait();
        const parsed = receipt.logs
            .map((l) => {
                try {
                    return checkout.interface.parseLog(l);
                } catch {
                    return null;
                }
            })
            .filter(Boolean);

        const buyerRefund = parsed.find((e) => e.name === "BuyerOrderAmnRefunded");
        const railRefund = parsed.find((e) => e.name === "OrderRefunded" && e.args.rail === 0n);

        expect(buyerRefund).to.not.equal(undefined);
        expect(railRefund).to.not.equal(undefined);
        expect(buyerRefund.args.amount).to.equal(part);
        expect(railRefund.args.amount).to.equal(part);
    });

    it("AMN-2.4 qualification: buyer refund one-shot guard blocks second token payout", async function () {
        const orderHash = await createOrder(0x45);
        const part = orderAmount / 2n;
        await checkout.connect(buyer).captureAmanitaCoin(orderHash, part);
        await checkout.connect(deployer).cancelOrder(orderHash);

        await amanitaToken.connect(deployer).setAmanitaCheckout(deployer.address);
        await expectRevertWithMessage(
            amanitaToken.connect(deployer).refundBuyerOnOrderCancel(buyer.address, orderHash, part),
            "AmanitaToken: buyer already refunded",
        );
    });

    it("AMN-2.4 qualification: no cancel refund path after Settled", async function () {
        const orderHash = await createOrder(0x46);
        const part = orderAmount / 2n;
        const buyerAmnBefore = await amanitaToken.balanceOf(buyer.address);

        await checkout.connect(buyer).captureAmanitaCoin(orderHash, part);
        await checkout.connect(buyer).declareFullPayment(orderHash);
        await checkout.connect(seller).acceptFullPayment(orderHash);
        await checkout.connect(deployer).markOrderSettled(orderHash);

        await expectRevertWithMessage(
            checkout.connect(deployer).cancelOrder(orderHash),
            "AmanitaCheckout: invalid transition to cancelled",
        );
        expect(await amanitaToken.balanceOf(buyer.address)).to.equal(buyerAmnBefore - part);
        expect(await amanitaToken.orderBuyerRefunded(orderHash)).to.equal(false);
    });
});
