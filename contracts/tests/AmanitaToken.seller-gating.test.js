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

function getEventArgsFromReceipt(contract, receipt, eventName) {
    for (const log of receipt.logs) {
        try {
            const parsed = contract.interface.parseLog(log);
            if (parsed && parsed.name === eventName) {
                return parsed.args;
            }
        } catch (_) {
            // ignore non-matching logs
        }
    }
    return null;
}

describe("AmanitaToken seller-only emission gating", function () {
    let deployer;
    let seller;
    let nonSeller;
    let recipient;
    let spiralEngine;
    let amanitaToken;
    let SELLER_ROLE;

    beforeEach(async function () {
        [deployer] = await ethers.getSigners();
        seller = ethers.Wallet.createRandom().connect(ethers.provider);
        nonSeller = ethers.Wallet.createRandom().connect(ethers.provider);
        recipient = ethers.Wallet.createRandom().connect(ethers.provider);

        await deployer.sendTransaction({ to: seller.address, value: ethers.parseEther("1") });
        await deployer.sendTransaction({ to: nonSeller.address, value: ethers.parseEther("1") });
        await deployer.sendTransaction({ to: recipient.address, value: ethers.parseEther("1") });

        const SpiralEngine = await ethers.getContractFactory("SpiralEngine");
        spiralEngine = await SpiralEngine.connect(deployer).deploy();
        await spiralEngine.waitForDeployment();
        SELLER_ROLE = await spiralEngine.SELLER_ROLE();

        const AmanitaToken = await ethers.getContractFactory("AmanitaToken");
        amanitaToken = await AmanitaToken.connect(deployer).deploy(deployer.address);
        await amanitaToken.waitForDeployment();
    });

    async function prepareActivatedSeller(user, inviteCodePrefix) {
        await amanitaToken.connect(deployer).setSpiralEngine(await spiralEngine.getAddress());
        await spiralEngine.connect(deployer).mintInvite(`${inviteCodePrefix}-INVITE`, 0);
        const newCodes = Array.from({ length: 12 }, (_, i) => `${inviteCodePrefix}-${i + 1}`);
        await spiralEngine
            .connect(deployer)
            .activateUser(`${inviteCodePrefix}-INVITE`, user.address, newCodes, 0);
        await spiralEngine.connect(deployer).grantSellerRole(user.address);
    }

    it("reverts mint when spiral engine is not set", async function () {
        await expectRevertWithMessage(
            amanitaToken.connect(deployer).mint(recipient.address, ethers.parseEther("1")),
            "AmanitaToken: spiral engine not set"
        );
    });

    it("allows only admin to set spiral engine", async function () {
        await expectRevertWithMessage(
            amanitaToken.connect(nonSeller).setSpiralEngine(await spiralEngine.getAddress()),
            "AccessControl"
        );
        await amanitaToken.connect(deployer).setSpiralEngine(await spiralEngine.getAddress());
        expect(await amanitaToken.spiralEngine()).to.equal(await spiralEngine.getAddress());
    });

    it("reverts setSpiralEngine for zero address", async function () {
        await expectRevertWithMessage(
            amanitaToken.connect(deployer).setSpiralEngine(ethers.ZeroAddress),
            "AmanitaToken: spiral engine required"
        );
    });

    it("reverts mint for non-seller caller", async function () {
        await amanitaToken.connect(deployer).setSpiralEngine(await spiralEngine.getAddress());

        await expectRevertWithMessage(
            amanitaToken.connect(nonSeller).mint(recipient.address, ethers.parseEther("1")),
            "AmanitaToken: seller role required"
        );
    });

    it("reverts mint for seller role holder without activation", async function () {
        await amanitaToken.connect(deployer).setSpiralEngine(await spiralEngine.getAddress());
        await spiralEngine.connect(deployer).grantRole(SELLER_ROLE, nonSeller.address);

        await expectRevertWithMessage(
            amanitaToken.connect(nonSeller).mint(recipient.address, ethers.parseEther("1")),
            "AmanitaToken: seller not activated"
        );
    });

    it("allows mint for activated seller", async function () {
        await prepareActivatedSeller(seller, "SELLER-ACT");

        await amanitaToken.connect(seller).mint(recipient.address, ethers.parseEther("5"));
        expect(await amanitaToken.balanceOf(recipient.address)).to.equal(ethers.parseEther("5"));
    });

    it("reverts mint for suspended seller", async function () {
        await amanitaToken.connect(deployer).setSpiralEngine(await spiralEngine.getAddress());

        await spiralEngine.connect(deployer).mintInvite("SELLER-SUSP-INVITE", 0);
        const newCodes = Array.from({ length: 12 }, (_, i) => `SELLER-SUSP-${i + 1}`);
        await spiralEngine
            .connect(deployer)
            .activateUser("SELLER-SUSP-INVITE", seller.address, newCodes, 0);
        await spiralEngine.connect(deployer).grantSellerRole(seller.address);
        await spiralEngine.connect(deployer).suspendUser(seller.address, 3600, "test");

        await expectRevertWithMessage(
            amanitaToken.connect(seller).mint(recipient.address, ethers.parseEther("1")),
            "AmanitaToken: seller suspended"
        );
    });

    it("tracks seller debt and emitted totals on mint", async function () {
        await prepareActivatedSeller(seller, "SELLER-DEBT");

        const amount = ethers.parseEther("7");
        await amanitaToken.connect(seller).mint(recipient.address, amount);
        expect(await amanitaToken.sellerDebt(seller.address)).to.equal(amount);
        expect(await amanitaToken.sellerTotalEmitted(seller.address)).to.equal(amount);
    });

    it("reverts mint when absolute debt cap is exceeded", async function () {
        await prepareActivatedSeller(seller, "SELLER-CAP");
        await amanitaToken.connect(deployer).setDebtPolicy(true, false, ethers.parseEther("5"), 10000);

        await expectRevertWithMessage(
            amanitaToken.connect(seller).mint(recipient.address, ethers.parseEther("6")),
            "AmanitaToken: debt cap exceeded"
        );
    });

    it("enforces debt/liquidity ratio cap when active liquidity exists", async function () {
        await prepareActivatedSeller(seller, "SELLER-RATIO");
        await amanitaToken.connect(deployer).setDebtPolicy(false, true, 0, 5000);

        await amanitaToken
            .connect(deployer)
            .recordAcceptedPayment(seller.address, ethers.parseEther("10"));

        await expectRevertWithMessage(
            amanitaToken.connect(seller).mint(recipient.address, ethers.parseEther("6")),
            "AmanitaToken: debt/liquidity cap exceeded"
        );
    });

    it("tracks active liquidity as accepted minus refunds", async function () {
        await amanitaToken
            .connect(deployer)
            .recordAcceptedPayment(seller.address, ethers.parseEther("10"));
        await amanitaToken
            .connect(deployer)
            .recordLiquidityRefund(seller.address, ethers.parseEther("4"));

        expect(await amanitaToken.getSellerActiveLiquidity(seller.address)).to.equal(ethers.parseEther("6"));
    });

    it("reverts when refund exceeds active liquidity", async function () {
        await amanitaToken
            .connect(deployer)
            .recordAcceptedPayment(seller.address, ethers.parseEther("3"));

        await expectRevertWithMessage(
            amanitaToken.connect(deployer).recordLiquidityRefund(seller.address, ethers.parseEther("4")),
            "AmanitaToken: refund exceeds active liquidity"
        );
    });

    it("allows mint after suspension expires", async function () {
        await prepareActivatedSeller(seller, "SELLER-EXP");
        await spiralEngine.connect(deployer).suspendUser(seller.address, 3600, "test");

        await expectRevertWithMessage(
            amanitaToken.connect(seller).mint(recipient.address, ethers.parseEther("1")),
            "AmanitaToken: seller suspended"
        );

        await ethers.provider.send("evm_increaseTime", [3601]);
        await ethers.provider.send("evm_mine", []);

        await amanitaToken.connect(seller).mint(recipient.address, ethers.parseEther("1"));
        expect(await amanitaToken.balanceOf(recipient.address)).to.equal(ethers.parseEther("1"));
    });

    it("allows bootstrap mint when ratio enabled and activeLiquidity is zero", async function () {
        await prepareActivatedSeller(seller, "SELLER-BOOT");
        await amanitaToken.connect(deployer).setDebtPolicy(false, true, 0, 5000);

        await amanitaToken.connect(seller).mint(recipient.address, ethers.parseEther("2"));
        expect(await amanitaToken.sellerDebt(seller.address)).to.equal(ethers.parseEther("2"));
    });

    it("reverts debt policy/accounting writes for non-admin", async function () {
        await expectRevertWithMessage(
            amanitaToken.connect(nonSeller).setDebtPolicy(true, true, ethers.parseEther("1"), 1000),
            "AccessControl"
        );
        await expectRevertWithMessage(
            amanitaToken.connect(nonSeller).recordAcceptedPayment(seller.address, ethers.parseEther("1")),
            "AccessControl"
        );
        await expectRevertWithMessage(
            amanitaToken.connect(nonSeller).recordLiquidityRefund(seller.address, ethers.parseEther("1")),
            "AccessControl"
        );
    });

    it("emits debt and policy events", async function () {
        await prepareActivatedSeller(seller, "SELLER-EVENT");

        const policyTx = await amanitaToken
            .connect(deployer)
            .setDebtPolicy(true, true, ethers.parseEther("9"), 9000);
        const policyReceipt = await policyTx.wait();
        const policyArgs = getEventArgsFromReceipt(amanitaToken, policyReceipt, "DebtPolicyUpdated");
        expect(policyArgs).to.not.equal(null);
        expect(policyArgs.enforceAbsoluteDebtCap).to.equal(true);
        expect(policyArgs.enforceDebtToLiquidityRatio).to.equal(true);
        expect(policyArgs.absoluteDebtCap).to.equal(ethers.parseEther("9"));
        expect(policyArgs.maxDebtToLiquidityBps).to.equal(9000n);

        const mintTx = await amanitaToken.connect(seller).mint(recipient.address, ethers.parseEther("2"));
        const mintReceipt = await mintTx.wait();
        const mintArgs = getEventArgsFromReceipt(amanitaToken, mintReceipt, "SellerDebtIncreased");
        expect(mintArgs).to.not.equal(null);
        expect(mintArgs.seller).to.equal(seller.address);
        expect(mintArgs.amount).to.equal(ethers.parseEther("2"));
        expect(mintArgs.newDebt).to.equal(ethers.parseEther("2"));
    });

    it("emits liquidity accounting events", async function () {
        const acceptedTx = await amanitaToken
            .connect(deployer)
            .recordAcceptedPayment(seller.address, ethers.parseEther("10"));
        const acceptedReceipt = await acceptedTx.wait();
        const acceptedArgs = getEventArgsFromReceipt(amanitaToken, acceptedReceipt, "SellerAcceptedPaymentRecorded");
        expect(acceptedArgs).to.not.equal(null);
        expect(acceptedArgs.seller).to.equal(seller.address);
        expect(acceptedArgs.amount).to.equal(ethers.parseEther("10"));
        expect(acceptedArgs.newAcceptedPayments).to.equal(ethers.parseEther("10"));

        const refundTx = await amanitaToken
            .connect(deployer)
            .recordLiquidityRefund(seller.address, ethers.parseEther("4"));
        const refundReceipt = await refundTx.wait();
        const refundArgs = getEventArgsFromReceipt(amanitaToken, refundReceipt, "SellerLiquidityRefundRecorded");
        expect(refundArgs).to.not.equal(null);
        expect(refundArgs.seller).to.equal(seller.address);
        expect(refundArgs.amount).to.equal(ethers.parseEther("4"));
        expect(refundArgs.newLiquidityRefunds).to.equal(ethers.parseEther("4"));
    });

    it("reverts setDebtPolicy with invalid bps > 10000", async function () {
        await expectRevertWithMessage(
            amanitaToken.connect(deployer).setDebtPolicy(true, true, ethers.parseEther("1"), 10001),
            "AmanitaToken: invalid bps"
        );
    });

    it("enforces bps=0 as strict zero ratio cap when active liquidity exists", async function () {
        await prepareActivatedSeller(seller, "SELLER-BPS0");
        await amanitaToken.connect(deployer).setDebtPolicy(false, true, 0, 0);
        await amanitaToken
            .connect(deployer)
            .recordAcceptedPayment(seller.address, ethers.parseEther("10"));

        await expectRevertWithMessage(
            amanitaToken.connect(seller).mint(recipient.address, ethers.parseEther("1")),
            "AmanitaToken: debt/liquidity cap exceeded"
        );
    });

    it("allows mint at exact ratio cap for bps=10000 and reverts above cap", async function () {
        await prepareActivatedSeller(seller, "SELLER-BPS100");
        await amanitaToken.connect(deployer).setDebtPolicy(false, true, 0, 10000);
        await amanitaToken
            .connect(deployer)
            .recordAcceptedPayment(seller.address, ethers.parseEther("5"));

        await amanitaToken.connect(seller).mint(recipient.address, ethers.parseEther("5"));
        await expectRevertWithMessage(
            amanitaToken.connect(seller).mint(recipient.address, ethers.parseEther("1")),
            "AmanitaToken: debt/liquidity cap exceeded"
        );
    });

    it("allows mint at exact absolute cap and reverts above cap", async function () {
        await prepareActivatedSeller(seller, "SELLER-ABS");
        await amanitaToken.connect(deployer).setDebtPolicy(true, false, ethers.parseEther("5"), 10000);

        await amanitaToken.connect(seller).mint(recipient.address, ethers.parseEther("5"));
        await expectRevertWithMessage(
            amanitaToken.connect(seller).mint(recipient.address, ethers.parseEther("1")),
            "AmanitaToken: debt cap exceeded"
        );
    });

    it("allows admin burn and reverts for non-admin burn", async function () {
        const amount = ethers.parseEther("3");
        await amanitaToken.connect(deployer).transfer(recipient.address, amount);
        await amanitaToken.connect(deployer).burn(recipient.address, ethers.parseEther("1"));
        expect(await amanitaToken.balanceOf(recipient.address)).to.equal(ethers.parseEther("2"));

        await expectRevertWithMessage(
            amanitaToken.connect(nonSeller).burn(recipient.address, ethers.parseEther("1")),
            "AccessControl"
        );
    });

    it("reverts burn for zero address and insufficient balance", async function () {
        await expectRevert(amanitaToken.connect(deployer).burn(ethers.ZeroAddress, ethers.parseEther("1")));
        await expectRevert(amanitaToken.connect(deployer).burn(recipient.address, ethers.parseEther("1")));
    });
});
