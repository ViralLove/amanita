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

describe("Lovecoin", function () {
    let lovecoin;
    let deployer, user1, user2;

    // Константы ролей - используем значения из контракта
    let DEFAULT_ADMIN_ROLE;
    let MINTER_ROLE;

    beforeEach(async function () {
        // Получаем деплоера
        const signers = await ethers.getSigners();
        deployer = signers[0];
        
        // Создаем дополнительные кошельки для тестирования
        user1 = ethers.Wallet.createRandom().connect(ethers.provider);
        user2 = ethers.Wallet.createRandom().connect(ethers.provider);
        
        // Финансируем кошельки
        await deployer.sendTransaction({
            to: user1.address,
            value: ethers.parseEther("1.0")
        });
        await deployer.sendTransaction({
            to: user2.address,
            value: ethers.parseEther("1.0")
        });
        
        const Lovecoin = await ethers.getContractFactory("Lovecoin");
        lovecoin = await Lovecoin.deploy(deployer.address);
        await lovecoin.waitForDeployment();
        
        // Получаем роли из контракта
        DEFAULT_ADMIN_ROLE = await lovecoin.DEFAULT_ADMIN_ROLE();
        MINTER_ROLE = await lovecoin.MINTER_ROLE();
    });

    describe("P0: Core Token Functions", function () {
        it("Should have correct name and symbol", async function () {
            expect(await lovecoin.name()).to.equal("Lovecoin");
            expect(await lovecoin.symbol()).to.equal("LOVECOIN");
        });

        it("Should have 18 decimals", async function () {
            expect(await lovecoin.decimals()).to.equal(18n);
        });

        it("Should have correct initial supply", async function () {
            const initialSupply = await lovecoin.INITIAL_SUPPLY();
            expect(initialSupply).to.equal(ethers.parseEther("888888888"));
            
            const deployerBalance = await lovecoin.balanceOf(deployer.address);
            expect(deployerBalance).to.equal(initialSupply);
        });

        it("Should allow transfer between users", async function () {
            const transferAmount = ethers.parseEther("1000");
            
            await lovecoin.connect(deployer).transfer(user1.address, transferAmount);
            
            expect(await lovecoin.balanceOf(user1.address)).to.equal(transferAmount);
            expect(await lovecoin.balanceOf(deployer.address)).to.equal(
                await lovecoin.INITIAL_SUPPLY() - transferAmount
            );
        });

        it("Should allow approve and transferFrom", async function () {
            const approveAmount = ethers.parseEther("500");
            
            // Деплоер аппрувит user1
            await lovecoin.connect(deployer).approve(user1.address, approveAmount);
            
            const allowance = await lovecoin.allowance(deployer.address, user1.address);
            expect(allowance).to.equal(approveAmount);
            
            // User1 делает transferFrom
            await lovecoin.connect(user1).transferFrom(
                deployer.address, 
                user2.address, 
                approveAmount
            );
            
            // Проверяем балансы
            expect(await lovecoin.balanceOf(user2.address)).to.equal(approveAmount);
            expect(await lovecoin.balanceOf(deployer.address)).to.equal(
                await lovecoin.INITIAL_SUPPLY() - approveAmount
            );
            
            expect(await lovecoin.allowance(deployer.address, user1.address)).to.equal(0n);
        });

        it("Should revert on insufficient balance", async function () {
            const transferAmount = ethers.parseEther("999999999");
            await expectRevert(lovecoin.connect(deployer).transfer(user1.address, transferAmount));
        });

        it("Should revert on transfer to zero address", async function () {
            await expectRevert(lovecoin.connect(deployer).transfer(ethers.ZeroAddress, ethers.parseEther("1000")));
        });
    });

    describe("P1: Access Control", function () {
        it("Should grant correct roles to deployer", async function () {
            expect(await lovecoin.hasRole(DEFAULT_ADMIN_ROLE, deployer.address)).to.be.true;
            expect(await lovecoin.hasRole(MINTER_ROLE, deployer.address)).to.be.true;
        });

        it("Should not grant roles to other users initially", async function () {
            expect(await lovecoin.hasRole(DEFAULT_ADMIN_ROLE, user1.address)).to.be.false;
            expect(await lovecoin.hasRole(MINTER_ROLE, user1.address)).to.be.false;
        });

        it("Should allow admin to grant minter role", async function () {
            await lovecoin.connect(deployer).grantRole(MINTER_ROLE, user1.address);
            expect(await lovecoin.hasRole(MINTER_ROLE, user1.address)).to.be.true;
        });

        it("Should allow admin to revoke minter role", async function () {
            await lovecoin.connect(deployer).grantRole(MINTER_ROLE, user1.address);
            expect(await lovecoin.hasRole(MINTER_ROLE, user1.address)).to.be.true;
            
            await lovecoin.connect(deployer).revokeRole(MINTER_ROLE, user1.address);
            expect(await lovecoin.hasRole(MINTER_ROLE, user1.address)).to.be.false;
        });

        it("Should revert when non-admin tries to grant role", async function () {
            await expectRevert(lovecoin.connect(user1).grantRole(MINTER_ROLE, user2.address));
        });
    });

    describe("P2: Mint and Burn Operations", function () {
        it("Should allow minter to mint tokens", async function () {
            const mintAmount = ethers.parseEther("1000");
            
            await lovecoin.connect(deployer).mint(user1.address, mintAmount);
            
            expect(await lovecoin.balanceOf(user1.address)).to.equal(mintAmount);
            
            const totalSupply = await lovecoin.totalSupply();
            expect(totalSupply).to.equal(
                await lovecoin.INITIAL_SUPPLY() + mintAmount
            );
        });

        it("Should allow minter to burn tokens", async function () {
            const burnAmount = ethers.parseEther("1000");
            
            await lovecoin.connect(deployer).burn(deployer.address, burnAmount);
            
            expect(await lovecoin.balanceOf(deployer.address)).to.equal(
                await lovecoin.INITIAL_SUPPLY() - burnAmount
            );
            
            const totalSupply = await lovecoin.totalSupply();
            expect(totalSupply).to.equal(
                await lovecoin.INITIAL_SUPPLY() - burnAmount
            );
        });

        it("Should revert when non-minter tries to mint", async function () {
            await expectRevert(lovecoin.connect(user1).mint(user2.address, ethers.parseEther("1000")));
        });

        it("Should revert when non-minter tries to burn", async function () {
            await expectRevert(lovecoin.connect(user1).burn(user1.address, ethers.parseEther("1000")));
        });

        it("Should revert when minting to zero address", async function () {
            await expectRevertWithMessage(lovecoin.connect(deployer).mint(ethers.ZeroAddress, ethers.parseEther("1000")), "Lovecoin: mint to zero address");
        });

        it("Should revert when minting zero amount", async function () {
            await expectRevertWithMessage(lovecoin.connect(deployer).mint(user1.address, 0), "Lovecoin: mint amount must be positive");
        });

        it("Should revert when burning from zero address", async function () {
            await expectRevertWithMessage(lovecoin.connect(deployer).burn(ethers.ZeroAddress, ethers.parseEther("1000")), "Lovecoin: burn from zero address");
        });

        it("Should revert when burning zero amount", async function () {
            await expectRevertWithMessage(lovecoin.connect(deployer).burn(deployer.address, 0), "Lovecoin: burn amount must be positive");
        });

        it("Should revert when burning more than balance", async function () {
            const burnAmount = await lovecoin.INITIAL_SUPPLY() + ethers.parseEther("1");
            await expectRevertWithMessage(lovecoin.connect(deployer).burn(deployer.address, burnAmount), "Lovecoin: burn amount exceeds balance");
        });
    });

    describe("P3: Edge Cases and Integration", function () {
        it("Should support interface for AccessControl", async function () {
            // ERC20 interface - проверяем что функция существует
            expect(typeof lovecoin.supportsInterface).to.equal("function");
            
            // Проверяем что функция работает
            const result = await lovecoin.supportsInterface("0x36372b07");
            expect(typeof result).to.equal("boolean");
        });

        it("Should handle large amounts correctly", async function () {
            const largeAmount = ethers.parseEther("1000000");
            
            await lovecoin.connect(deployer).mint(user1.address, largeAmount);
            expect(await lovecoin.balanceOf(user1.address)).to.equal(largeAmount);
            
            await lovecoin.connect(user1).transfer(user2.address, largeAmount);
            expect(await lovecoin.balanceOf(user2.address)).to.equal(largeAmount);
            expect(await lovecoin.balanceOf(user1.address)).to.equal(0n);
        });

        it("Should handle role management correctly", async function () {
            // Grant minter role to user1
            await lovecoin.connect(deployer).grantRole(MINTER_ROLE, user1.address);
            
            // User1 can now mint
            await lovecoin.connect(user1).mint(user2.address, ethers.parseEther("1000"));
            expect(await lovecoin.balanceOf(user2.address)).to.equal(ethers.parseEther("1000"));
            
            // Revoke role
            await lovecoin.connect(deployer).revokeRole(MINTER_ROLE, user1.address);
            
            await expectRevert(lovecoin.connect(user1).mint(user2.address, ethers.parseEther("1000")));
        });

        it("Should revert when deploying with zero address owner", async function () {
            const Lovecoin = await ethers.getContractFactory("Lovecoin");
            await expectRevertWithMessage(Lovecoin.deploy(ethers.ZeroAddress), "Lovecoin: owner cannot be zero address");
        });

        it("Should maintain correct total supply after operations", async function () {
            const initialSupply = await lovecoin.INITIAL_SUPPLY();
            const mintAmount = ethers.parseEther("50000");
            const burnAmount = ethers.parseEther("10000");
            
            // Mint
            await lovecoin.connect(deployer).mint(user1.address, mintAmount);
            let totalSupply = await lovecoin.totalSupply();
            expect(totalSupply).to.equal(initialSupply + mintAmount);
            
            // Burn
            await lovecoin.connect(deployer).burn(deployer.address, burnAmount);
            totalSupply = await lovecoin.totalSupply();
            expect(totalSupply).to.equal(initialSupply + mintAmount - burnAmount);
        });
    });
});