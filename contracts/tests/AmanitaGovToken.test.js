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

describe("AmanitaGovToken", function () {
    let token;
    let deployer;
    let user1;
    let user2;
    let MINTER_ROLE;
    let DEFAULT_ADMIN_ROLE;

    beforeEach(async function () {
        [deployer] = await ethers.getSigners();
        user1 = ethers.Wallet.createRandom().connect(ethers.provider);
        user2 = ethers.Wallet.createRandom().connect(ethers.provider);

        await deployer.sendTransaction({ to: user1.address, value: ethers.parseEther("1") });
        await deployer.sendTransaction({ to: user2.address, value: ethers.parseEther("1") });

        const AmanitaGovToken = await ethers.getContractFactory("AmanitaGovToken");
        token = await AmanitaGovToken.deploy(deployer.address);
        await token.waitForDeployment();

        MINTER_ROLE = await token.MINTER_ROLE();
        DEFAULT_ADMIN_ROLE = await token.DEFAULT_ADMIN_ROLE();
    });

    describe("P0: Deployment and Roles", function () {
        it("Should set correct name and symbol", async function () {
            expect(await token.name()).to.equal("Amanita Governance");
            expect(await token.symbol()).to.equal("AGOV");
        });

        it("Should grant admin and minter roles to admin", async function () {
            expect(await token.hasRole(DEFAULT_ADMIN_ROLE, deployer.address)).to.equal(true);
            expect(await token.hasRole(MINTER_ROLE, deployer.address)).to.equal(true);
        });

        it("Should revert on zero admin address", async function () {
            const AmanitaGovToken = await ethers.getContractFactory("AmanitaGovToken");
            await expectRevert(AmanitaGovToken.deploy(ethers.ZeroAddress));
        });
    });

    describe("P0: Mint Access Control", function () {
        it("Should allow minter to mint", async function () {
            const amount = ethers.parseEther("100");
            await token.connect(deployer).mint(user1.address, amount);

            expect(await token.balanceOf(user1.address)).to.equal(amount);
            expect(await token.totalSupply()).to.equal(amount);
        });

        it("Should revert when non-minter tries to mint", async function () {
            await expectRevert(token.connect(user1).mint(user2.address, ethers.parseEther("1")));
        });
    });

    describe("P1: ERC20Votes core invariants", function () {
        it("Should have zero votes until delegation", async function () {
            const amount = ethers.parseEther("10");
            await token.connect(deployer).mint(user1.address, amount);

            expect(await token.getVotes(user1.address)).to.equal(0n);
        });

        it("Should assign votes after self-delegation", async function () {
            const amount = ethers.parseEther("10");
            await token.connect(deployer).mint(user1.address, amount);
            await token.connect(user1).delegate(user1.address);

            expect(await token.getVotes(user1.address)).to.equal(amount);
        });

        it("Should update delegated votes after transfer", async function () {
            const amount = ethers.parseEther("10");
            await token.connect(deployer).mint(user1.address, amount);
            await token.connect(user1).delegate(user1.address);

            const transferAmount = ethers.parseEther("4");
            await token.connect(user1).transfer(user2.address, transferAmount);

            expect(await token.getVotes(user1.address)).to.equal(amount - transferAmount);
            expect(await token.getVotes(user2.address)).to.equal(0n);

            await token.connect(user2).delegate(user2.address);
            expect(await token.getVotes(user2.address)).to.equal(transferAmount);
        });
    });

    describe("P1: Permit/Nonces surface", function () {
        it("Should expose nonces API", async function () {
            expect(await token.nonces(user1.address)).to.equal(0n);
        });
    });
});

