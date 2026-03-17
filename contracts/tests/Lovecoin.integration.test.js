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
    const msg = (err?.message || err?.error?.message || String(err)) || "";
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

describe("Lovecoin Integration Tests", function () {
    let lovecoin;
    let deployer, user1, user2, minter;

    beforeEach(async function () {
        // Получаем деплоера
        const signers = await ethers.getSigners();
        deployer = signers[0];

        // Создаем дополнительные кошельки для тестирования
        user1 = ethers.Wallet.createRandom().connect(ethers.provider);
        user2 = ethers.Wallet.createRandom().connect(ethers.provider);
        minter = ethers.Wallet.createRandom().connect(ethers.provider);

        // Финансируем кошельки
        await deployer.sendTransaction({
            to: user1.address,
            value: ethers.parseEther("1.0")
        });
        await deployer.sendTransaction({
            to: user2.address,
            value: ethers.parseEther("1.0")
        });
        await deployer.sendTransaction({
            to: minter.address,
            value: ethers.parseEther("1.0")
        });
        
        const Lovecoin = await ethers.getContractFactory("Lovecoin");
        lovecoin = await Lovecoin.deploy(deployer.address);
        await lovecoin.waitForDeployment();

        // Даем minter роль MINTER_ROLE
        const MINTER_ROLE = await lovecoin.MINTER_ROLE();
        await lovecoin.connect(deployer).grantRole(MINTER_ROLE, minter.address);
    });

    describe("P0: LoveEmissionEngine Integration", function () {
        it("Should allow minter to mint tokens for emission", async function () {
            const mintAmount = ethers.parseEther("1000");
            
            await lovecoin.connect(minter).mint(user1.address, mintAmount);
            expect(await lovecoin.balanceOf(user1.address)).to.equal(mintAmount);
            
            const totalSupply = await lovecoin.totalSupply();
            expect(totalSupply).to.equal(
                await lovecoin.INITIAL_SUPPLY() + mintAmount
            );
        });

        it("Should handle multiple emissions correctly", async function () {
            const emissionAmount = ethers.parseEther("100");
            const emissions = 5;
            
            for (let i = 0; i < emissions; i++) {
                await lovecoin.connect(minter).mint(user1.address, emissionAmount);
            }
            
            expect(await lovecoin.balanceOf(user1.address)).to.equal(
                emissionAmount * BigInt(emissions)
            );
        });

        it("Should track total supply correctly with emissions", async function () {
            const initialSupply = await lovecoin.INITIAL_SUPPLY();
            const emission1 = ethers.parseEther("500");
            const emission2 = ethers.parseEther("300");
            
            await lovecoin.connect(minter).mint(user1.address, emission1);
            await lovecoin.connect(minter).mint(user2.address, emission2);
            
            expect(await lovecoin.totalSupply()).to.equal(
                initialSupply + emission1 + emission2
            );
        });
    });

    describe("P1: SpiralEngine Integration", function () {
        it("Should allow role management for SpiralEngine integration", async function () {
            const MINTER_ROLE = await lovecoin.MINTER_ROLE();
            const ADMIN_ROLE = await lovecoin.DEFAULT_ADMIN_ROLE();
            
            // Проверяем, что deployer имеет ADMIN_ROLE
            expect(await lovecoin.hasRole(ADMIN_ROLE, deployer.address)).to.be.true;
            
            // Проверяем, что minter имеет MINTER_ROLE
            expect(await lovecoin.hasRole(MINTER_ROLE, minter.address)).to.be.true;
            
            // Проверяем, что user1 не имеет ролей
            expect(await lovecoin.hasRole(ADMIN_ROLE, user1.address)).to.be.false;
            expect(await lovecoin.hasRole(MINTER_ROLE, user1.address)).to.be.false;
        });

        it("Should allow admin to grant and revoke minter role", async function () {
            const MINTER_ROLE = await lovecoin.MINTER_ROLE();
            
            // Grant role
            await lovecoin.connect(deployer).grantRole(MINTER_ROLE, user1.address);
            expect(await lovecoin.hasRole(MINTER_ROLE, user1.address)).to.be.true;
            
            // User1 can now mint
            await lovecoin.connect(user1).mint(user2.address, ethers.parseEther("100"));
            expect(await lovecoin.balanceOf(user2.address)).to.equal(ethers.parseEther("100"));
            
            // Revoke role
            await lovecoin.connect(deployer).revokeRole(MINTER_ROLE, user1.address);
            expect(await lovecoin.hasRole(MINTER_ROLE, user1.address)).to.be.false;
            
            await expectRevert(lovecoin.connect(user1).mint(user2.address, ethers.parseEther("100")));
        });
    });

    describe("P2: Social Mining Simulation", function () {
        it("Should simulate social mining through multiple mints", async function () {
            const superlikeReward = ethers.parseEther("1"); // 1 LOVECOIN per superlike
            const superlikes = 10;
            
            // Simulate 10 superlikes
            for (let i = 0; i < superlikes; i++) {
                await lovecoin.connect(minter).mint(user1.address, superlikeReward);
            }
            
            expect(await lovecoin.balanceOf(user1.address)).to.equal(
                superlikeReward * BigInt(superlikes)
            );
        });

        it("Should handle large-scale social mining", async function () {
            const superlikeReward = ethers.parseEther("1");
            const largeScaleSuperlikes = 1000;
            
            // Simulate large-scale social mining
            await lovecoin.connect(minter).mint(user1.address, superlikeReward * BigInt(largeScaleSuperlikes));
            
            expect(await lovecoin.balanceOf(user1.address)).to.equal(
                superlikeReward * BigInt(largeScaleSuperlikes)
            );
            
            const totalSupply = await lovecoin.totalSupply();
            expect(totalSupply).to.equal(
                await lovecoin.INITIAL_SUPPLY() + superlikeReward * BigInt(largeScaleSuperlikes)
            );
        });
    });

    describe("P3: Edge Cases and Error Handling", function () {
        it("Should handle zero amount minting", async function () {
            await expectRevertWithMessage(lovecoin.connect(minter).mint(user1.address, 0), "Lovecoin: mint amount must be positive");
        });

        it("Should handle minting to zero address", async function () {
            await expectRevertWithMessage(lovecoin.connect(minter).mint(ethers.ZeroAddress, ethers.parseEther("100")), "Lovecoin: mint to zero address");
        });

        it("Should handle burning more than balance", async function () {
            const burnAmount = ethers.parseEther("999999999");
            await expectRevertWithMessage(lovecoin.connect(minter).burn(deployer.address, burnAmount), "Lovecoin: burn amount exceeds balance");
        });

        it("Should handle role management edge cases", async function () {
            const MINTER_ROLE = await lovecoin.MINTER_ROLE();
            await expectRevert(lovecoin.connect(user1).grantRole(MINTER_ROLE, user2.address));
            await expectRevert(lovecoin.connect(user1).revokeRole(MINTER_ROLE, minter.address));
        });
    });

    describe("P4: Gas Optimization", function () {
        it("Should have reasonable gas costs for minting", async function () {
            const tx = await lovecoin.connect(minter).mint(user1.address, ethers.parseEther("100"));
            const receipt = await tx.wait();
            expect(receipt.gasUsed < 100000n).to.be.true;
        });

        it("Should have reasonable gas costs for role management", async function () {
            const MINTER_ROLE = await lovecoin.MINTER_ROLE();
            const tx = await lovecoin.connect(deployer).grantRole(MINTER_ROLE, user1.address);
            const receipt = await tx.wait();
            expect(receipt.gasUsed < 150000n).to.be.true;
        });
    });
});
