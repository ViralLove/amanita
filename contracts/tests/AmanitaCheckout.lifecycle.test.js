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

describe("AmanitaCheckout lifecycle and roles", function () {
    let deployer;
    let seller;
    let buyer;
    let outsider;
    let checkout;
    let CHECKOUT_WRITER_ROLE;

    beforeEach(async function () {
        [deployer] = await ethers.getSigners();
        seller = ethers.Wallet.createRandom().connect(ethers.provider);
        buyer = ethers.Wallet.createRandom().connect(ethers.provider);
        outsider = ethers.Wallet.createRandom().connect(ethers.provider);

        await deployer.sendTransaction({ to: seller.address, value: ethers.parseEther("1") });
        await deployer.sendTransaction({ to: buyer.address, value: ethers.parseEther("1") });
        await deployer.sendTransaction({ to: outsider.address, value: ethers.parseEther("1") });

        const AmanitaCheckout = await ethers.getContractFactory("AmanitaCheckout");
        checkout = await AmanitaCheckout.connect(deployer).deploy(deployer.address);
        await checkout.waitForDeployment();
        CHECKOUT_WRITER_ROLE = await checkout.CHECKOUT_WRITER_ROLE();
    });

    async function createOrderAsBuyer(referenceHex = "0x01") {
        const tx = await checkout
            .connect(buyer)
            .createOrder(seller.address, ethers.parseEther("10"), ethers.zeroPadValue(referenceHex, 32));
        const receipt = await tx.wait();
        const event = receipt.logs
            .map((log) => {
                try {
                    return checkout.interface.parseLog(log);
                } catch (_) {
                    return null;
                }
            })
            .find((e) => e && e.name === "OrderCreated");
        return event.args.orderHash;
    }

    it("grants admin and checkout writer roles to deployer", async function () {
        const DEFAULT_ADMIN_ROLE = await checkout.DEFAULT_ADMIN_ROLE();
        expect(await checkout.hasRole(DEFAULT_ADMIN_ROLE, deployer.address)).to.be.true;
        expect(await checkout.hasRole(CHECKOUT_WRITER_ROLE, deployer.address)).to.be.true;
    });

    it("creates order with Created status and buyer=sender", async function () {
        const orderHash = await createOrderAsBuyer("0x11");
        const order = await checkout.getOrder(orderHash);
        expect(order.buyer).to.equal(buyer.address);
        expect(order.seller).to.equal(seller.address);
        expect(order.status).to.equal(1n);
        expect(order.createdAt > 0n).to.be.true;
    });

    it("reverts createOrder with invalid inputs", async function () {
        await expectRevert(
            checkout.connect(buyer).createOrder(ethers.ZeroAddress, ethers.parseEther("10"), ethers.zeroPadValue("0x01", 32)),
        );
        await expectRevert(
            checkout.connect(buyer).createOrder(seller.address, 0, ethers.zeroPadValue("0x01", 32)),
        );
        await expectRevert(
            checkout.connect(buyer).createOrder(seller.address, ethers.parseEther("10"), ethers.ZeroHash),
        );
    });

    it("enforces valid transition Created -> Paid -> Settled", async function () {
        const orderHash = await createOrderAsBuyer("0x12");
        await checkout.connect(deployer).markOrderPaid(orderHash);
        let order = await checkout.getOrder(orderHash);
        expect(order.status).to.equal(2n);
        expect(order.paidAt > 0n).to.be.true;

        await checkout.connect(deployer).markOrderSettled(orderHash);
        order = await checkout.getOrder(orderHash);
        expect(order.status).to.equal(3n);
        expect(order.settledAt > 0n).to.be.true;
    });

    it("allows cancellation only from Created/Paid", async function () {
        const orderHash = await createOrderAsBuyer("0x13");
        await checkout.connect(deployer).cancelOrder(orderHash);
        let order = await checkout.getOrder(orderHash);
        expect(order.status).to.equal(4n);

        const orderHash2 = await createOrderAsBuyer("0x14");
        await checkout.connect(deployer).markOrderPaid(orderHash2);
        await checkout.connect(deployer).cancelOrder(orderHash2);
        order = await checkout.getOrder(orderHash2);
        expect(order.status).to.equal(4n);
    });

    it("allows buyer self-cancel only in Created status", async function () {
        const orderHash = await createOrderAsBuyer("0x18");
        await checkout.connect(buyer).cancelOwnOrder(orderHash);
        const order = await checkout.getOrder(orderHash);
        expect(order.status).to.equal(4n);
    });

    it("rejects buyer self-cancel for non-owner or non-Created status", async function () {
        const orderHash = await createOrderAsBuyer("0x19");
        await expectRevertWithMessage(
            checkout.connect(outsider).cancelOwnOrder(orderHash),
            "AmanitaCheckout: only buyer can self-cancel"
        );

        const orderHash2 = await createOrderAsBuyer("0x20");
        await checkout.connect(deployer).markOrderPaid(orderHash2);
        await expectRevertWithMessage(
            checkout.connect(buyer).cancelOwnOrder(orderHash2),
            "AmanitaCheckout: invalid self-cancel status"
        );
    });

    it("rejects invalid status transitions", async function () {
        const orderHash = await createOrderAsBuyer("0x15");
        await expectRevertWithMessage(
            checkout.connect(deployer).markOrderSettled(orderHash),
            "AmanitaCheckout: invalid transition to settled"
        );

        await checkout.connect(deployer).markOrderPaid(orderHash);
        await expectRevertWithMessage(
            checkout.connect(deployer).markOrderPaid(orderHash),
            "AmanitaCheckout: invalid transition to paid"
        );

        await checkout.connect(deployer).markOrderSettled(orderHash);
        await expectRevertWithMessage(
            checkout.connect(deployer).cancelOrder(orderHash),
            "AmanitaCheckout: invalid transition to cancelled"
        );
    });

    it("restricts writer actions to CHECKOUT_WRITER_ROLE", async function () {
        const orderHash = await createOrderAsBuyer("0x16");
        await expectRevert(checkout.connect(outsider).markOrderPaid(orderHash));
        await expectRevert(checkout.connect(outsider).markOrderSettled(orderHash));
        await expectRevert(checkout.connect(outsider).cancelOrder(orderHash));
    });

    it("supports granting writer role to another operator", async function () {
        await checkout.connect(deployer).grantRole(CHECKOUT_WRITER_ROLE, outsider.address);
        const orderHash = await createOrderAsBuyer("0x17");
        await checkout.connect(outsider).markOrderPaid(orderHash);
        const order = await checkout.getOrder(orderHash);
        expect(order.status).to.equal(2n);
    });
});
