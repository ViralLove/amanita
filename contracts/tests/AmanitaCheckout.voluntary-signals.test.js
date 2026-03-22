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

describe("AmanitaCheckout voluntary signals (AMN-2.6 attestation)", function () {
    let deployer;
    let seller;
    let buyer;
    let outsider;
    let checkout;
    let amanitaToken;
    let loveToken;
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
        const spiralEngine = await SpiralEngine.connect(deployer).deploy();
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
        await spiralEngine.connect(deployer).mintInvite("VOL-INV", 0);
        const codes = Array.from({ length: 12 }, (_, i) => `VOL-${i}`);
        await spiralEngine.connect(deployer).activateUser("VOL-INV", seller.address, codes, 0);
        await spiralEngine.connect(deployer).grantSellerRole(seller.address);
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

    it("confirmOrderReceived: Paid, buyer, once; does not change status", async function () {
        const h = await createOrder(0x21);
        await checkout.connect(deployer).markOrderPaid(h);
        const tx = await checkout.connect(buyer).confirmOrderReceived(h);
        const receipt = await tx.wait();
        const ev = receipt.logs
            .map((l) => {
                try {
                    return checkout.interface.parseLog(l);
                } catch {
                    return null;
                }
            })
            .find((e) => e && e.name === "OrderReceivedByBuyer");
        expect(ev).to.be.ok;
        const order = await checkout.getOrder(h);
        expect(order.status).to.equal(2n);
        expect(order.receivedByBuyerAt > 0n).to.be.true;

        await expectRevertWithMessage(checkout.connect(buyer).confirmOrderReceived(h), "AmanitaCheckout: already confirmed received");
    });

    it("confirmOrderReceived reverts if not Paid or not buyer", async function () {
        const h = await createOrder(0x22);
        await expectRevertWithMessage(
            checkout.connect(buyer).confirmOrderReceived(h),
            "AmanitaCheckout: invalid status for received",
        );
        await checkout.connect(deployer).markOrderPaid(h);
        await expectRevertWithMessage(
            checkout.connect(outsider).confirmOrderReceived(h),
            "AmanitaCheckout: only buyer",
        );
    });

    it("signalWeakExternalPaymentClaim: Created, buyer, once; optional hooks off OK", async function () {
        const h = await createOrder(0x23);
        const tx = await checkout.connect(buyer).signalWeakExternalPaymentClaim(h);
        const receipt = await tx.wait();
        const ev = receipt.logs
            .map((l) => {
                try {
                    return checkout.interface.parseLog(l);
                } catch {
                    return null;
                }
            })
            .find((e) => e && e.name === "WeakExternalPaymentClaimed");
        expect(ev).to.be.ok;
        const order = await checkout.getOrder(h);
        expect(order.status).to.equal(1n);
        expect(order.weakExternalPaymentClaimed).to.be.true;

        await expectRevertWithMessage(
            checkout.connect(buyer).signalWeakExternalPaymentClaim(h),
            "AmanitaCheckout: weak claim already used",
        );
    });

    it("signalWeakExternalPaymentClaim reverts after Paid", async function () {
        const h = await createOrder(0x24);
        await checkout.connect(deployer).markOrderPaid(h);
        await expectRevertWithMessage(
            checkout.connect(buyer).signalWeakExternalPaymentClaim(h),
            "AmanitaCheckout: invalid status for weak claim",
        );
    });
});
