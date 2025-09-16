const { expect } = require("chai");
const { ethers } = require("hardhat");

describe("SoulboundCore", function () {
    let soulboundCore;
    let owner;
    let user1;
    let user2;
    let user3;

    beforeEach(async function () {
        const signers = await ethers.getSigners();
        owner = signers[0];
        
        // Создаем случайные кошельки для тестирования
        user1 = await ethers.Wallet.createRandom().connect(ethers.provider);
        user2 = await ethers.Wallet.createRandom().connect(ethers.provider);
        user3 = await ethers.Wallet.createRandom().connect(ethers.provider);
        
        // Пополняем кошельки для тестирования
        await owner.sendTransaction({
            to: user1.address,
            value: ethers.parseEther("1.0")
        });
        await owner.sendTransaction({
            to: user2.address,
            value: ethers.parseEther("1.0")
        });
        await owner.sendTransaction({
            to: user3.address,
            value: ethers.parseEther("1.0")
        });
        
        const SoulboundCore = await ethers.getContractFactory("SoulboundCore");
        soulboundCore = await SoulboundCore.deploy("Soulbound Core", "SBC");
        await soulboundCore.waitForDeployment();
    });

    describe("Deployment", function () {
        it("Should set the correct name and symbol", async function () {
            expect(await soulboundCore.name()).to.equal("Soulbound Core");
            expect(await soulboundCore.symbol()).to.equal("SBC");
        });

        it("Should set the correct owner", async function () {
            expect(await soulboundCore.owner()).to.equal(owner.address);
        });

        it("Should initialize with nextTokenId = 1", async function () {
            expect(await soulboundCore.getNextTokenId()).to.equal(1);
        });

        it("Should have total supply = 0 initially", async function () {
            expect(await soulboundCore.getTotalSupply()).to.equal(0);
        });
    });

    describe("EIP-5192 Compliance", function () {
        it("Should always return true for locked()", async function () {
            // Test with non-existent token
            expect(await soulboundCore.locked(999)).to.be.true;
            
            // Mint a token and test
            await soulboundCore.mintSoul(user1.address);
            expect(await soulboundCore.locked(1)).to.be.true;
        });

        it("Should emit Locked event on mint", async function () {
            await expect(soulboundCore.mintSoul(user1.address))
                .to.emit(soulboundCore, "Locked")
                .withArgs(1);
        });
    });

    describe("Non-transferability", function () {
        beforeEach(async function () {
            await soulboundCore.mintSoul(user1.address);
        });

        it("Should revert on transferFrom", async function () {
            await expect(
                soulboundCore.connect(user1).transferFrom(user1.address, user2.address, 1)
            ).to.be.revertedWith("SBT: transfer not allowed");
        });

        it("Should revert on safeTransferFrom", async function () {
            await expect(
                soulboundCore.connect(user1).safeTransferFrom(user1.address, user2.address, 1)
            ).to.be.revertedWith("SBT: transfer not allowed");
        });

        it("Should revert on safeTransferFrom with data", async function () {
            await soulboundCore.mintSoul(user1.address);
            
            await expect(
                soulboundCore.connect(user1)["safeTransferFrom(address,address,uint256,bytes)"](user1.address, user2.address, 1, "0x")
            ).to.be.revertedWith("SBT: transfer not allowed");
        });
    });

    describe("No Approval Delegation", function () {
        beforeEach(async function () {
            await soulboundCore.mintSoul(user1.address);
        });

        it("Should revert on approve", async function () {
            await expect(
                soulboundCore.connect(user1).approve(user2.address, 1)
            ).to.be.revertedWith("SBT: approval not allowed");
        });

        it("Should revert on setApprovalForAll", async function () {
            await expect(
                soulboundCore.connect(user1).setApprovalForAll(user2.address, true)
            ).to.be.revertedWith("SBT: approval not allowed");
        });

        it("Should always return address(0) for getApproved", async function () {
            expect(await soulboundCore.getApproved(1)).to.equal(ethers.ZeroAddress);
            expect(await soulboundCore.getApproved(999)).to.equal(ethers.ZeroAddress);
        });

        it("Should always return false for isApprovedForAll", async function () {
            expect(await soulboundCore.isApprovedForAll(user1.address, user2.address)).to.be.false;
            expect(await soulboundCore.isApprovedForAll(user2.address, user1.address)).to.be.false;
        });
    });

    describe("Minting", function () {
        it("Should mint soul to user (owner only)", async function () {
            await expect(soulboundCore.mintSoul(user1.address))
                .to.emit(soulboundCore, "SoulMinted")
                .withArgs(user1.address, 1)
                .and.to.emit(soulboundCore, "Locked")
                .withArgs(1);

            expect(await soulboundCore.ownerOf(1)).to.equal(user1.address);
            expect(await soulboundCore.balanceOf(user1.address)).to.equal(1);
            expect(await soulboundCore.getNextTokenId()).to.equal(2);
            expect(await soulboundCore.getTotalSupply()).to.equal(1);
            expect(await soulboundCore.exists(1)).to.be.true;
        });

        it("Should mint batch souls to user (owner only)", async function () {
            const tx = await soulboundCore.mintSoulBatch(user1.address, 3);
            const receipt = await tx.wait();

            // Check events
            const soulMintedEvents = receipt.logs.filter(log => {
                try {
                    const parsed = soulboundCore.interface.parseLog(log);
                    return parsed.name === "SoulMinted";
                } catch (e) {
                    return false;
                }
            });
            expect(soulMintedEvents).to.have.lengthOf(3);

            // Check balances and ownership
            expect(await soulboundCore.balanceOf(user1.address)).to.equal(3);
            expect(await soulboundCore.ownerOf(1)).to.equal(user1.address);
            expect(await soulboundCore.ownerOf(2)).to.equal(user1.address);
            expect(await soulboundCore.ownerOf(3)).to.equal(user1.address);
            expect(await soulboundCore.getNextTokenId()).to.equal(4);
            expect(await soulboundCore.getTotalSupply()).to.equal(3);
        });

        it("Should revert minting by non-owner", async function () {
            await expect(
                soulboundCore.connect(user1).mintSoul(user2.address)
            ).to.be.revertedWithCustomError(soulboundCore, "OwnableUnauthorizedAccount")
                .withArgs(user1.address);
        });

        it("Should revert batch minting by non-owner", async function () {
            await expect(
                soulboundCore.connect(user1).mintSoulBatch(user2.address, 2)
            ).to.be.revertedWithCustomError(soulboundCore, "OwnableUnauthorizedAccount")
                .withArgs(user1.address);
        });

        it("Should revert batch minting with invalid amount", async function () {
            await expect(
                soulboundCore.mintSoulBatch(user1.address, 0)
            ).to.be.revertedWith("SBT: invalid amount");

            await expect(
                soulboundCore.mintSoulBatch(user1.address, 101)
            ).to.be.revertedWith("SBT: invalid amount");
        });
    });

    describe("Burning", function () {
        beforeEach(async function () {
            await soulboundCore.mintSoul(user1.address);
            await soulboundCore.mintSoul(user2.address);
        });

        it("Should burn soul by owner", async function () {
            await expect(soulboundCore.connect(user1).burnSoul(1))
                .to.emit(soulboundCore, "SoulBurned")
                .withArgs(1);

            await expect(soulboundCore.ownerOf(1)).to.be.revertedWith("ERC721: invalid token ID");
            expect(await soulboundCore.exists(1)).to.be.false;
        });

        it("Should burn soul by contract owner", async function () {
            await soulboundCore.mintSoul(user1.address);
            
            await expect(soulboundCore.burnSoul(1))
                .to.emit(soulboundCore, "SoulBurned")
                .withArgs(1);

            await expect(soulboundCore.ownerOf(1)).to.be.revertedWith("ERC721: invalid token ID");
            expect(await soulboundCore.exists(1)).to.be.false;
        });

        it("Should revert burning by unauthorized user", async function () {
            await expect(
                soulboundCore.connect(user2).burnSoul(1)
            ).to.be.revertedWith("SBT: not authorized to burn");
        });

        it("Should revert burning non-existent token", async function () {
            await expect(
                soulboundCore.connect(user1).burnSoul(999)
            ).to.be.revertedWith("ERC721: invalid token ID");
        });
    });

    describe("View Functions", function () {
        beforeEach(async function () {
            // Создаем новый контракт для изоляции тестов
            const SoulboundCore = await ethers.getContractFactory("SoulboundCore");
            soulboundCore = await SoulboundCore.deploy("Soulbound Core", "SBC");
            await soulboundCore.waitForDeployment();
        });

        it("Should return correct nextTokenId", async function () {
            expect(await soulboundCore.getNextTokenId()).to.equal(1);
            
            await soulboundCore.mintSoul(user1.address);
            expect(await soulboundCore.getNextTokenId()).to.equal(2);
            
            await soulboundCore.mintSoul(user2.address);
            expect(await soulboundCore.getNextTokenId()).to.equal(3);
        });

        it("Should return correct total supply", async function () {
            // Создаем новый контракт для этого теста
            const SoulboundCore = await ethers.getContractFactory("SoulboundCore");
            const testContract = await SoulboundCore.deploy("Soulbound Core", "SBC");
            await testContract.waitForDeployment();
            
            // Начинаем с чистого состояния
            expect(await testContract.getTotalSupply()).to.equal(0);
            
            // Минтим первый токен
            await testContract.mintSoul(user1.address);
            expect(await testContract.getTotalSupply()).to.equal(1);
            
            // Минтим второй токен
            await testContract.mintSoul(user2.address);
            expect(await testContract.getTotalSupply()).to.equal(2);
            
            // Сжигаем первый токен
            await testContract.connect(user1).burnSoul(1);
            expect(await testContract.getTotalSupply()).to.equal(1);
        });

        it("Should return correct exists status", async function () {
            expect(await soulboundCore.exists(1)).to.be.false;
            
            await soulboundCore.mintSoul(user1.address);
            expect(await soulboundCore.exists(1)).to.be.true;
            
            await soulboundCore.connect(user1).burnSoul(1);
            expect(await soulboundCore.exists(1)).to.be.false;
        });
    });

    describe("Edge Cases", function () {
        it("Should handle locked() for non-existent tokens", async function () {
            expect(await soulboundCore.locked(0)).to.be.true;
            expect(await soulboundCore.locked(999)).to.be.true;
            expect(await soulboundCore.locked(ethers.MaxUint256)).to.be.true;
        });

        it("Should handle getApproved() for non-existent tokens", async function () {
            expect(await soulboundCore.getApproved(0)).to.equal(ethers.ZeroAddress);
            expect(await soulboundCore.getApproved(999)).to.equal(ethers.ZeroAddress);
        });

        it("Should handle isApprovedForAll() with zero addresses", async function () {
            expect(await soulboundCore.isApprovedForAll(ethers.ZeroAddress, ethers.ZeroAddress)).to.be.false;
            expect(await soulboundCore.isApprovedForAll(ethers.ZeroAddress, user1.address)).to.be.false;
            expect(await soulboundCore.isApprovedForAll(user1.address, ethers.ZeroAddress)).to.be.false;
        });

        it("Should handle transferFrom with zero addresses", async function () {
            await expect(
                soulboundCore.transferFrom(ethers.ZeroAddress, user1.address, 1)
            ).to.be.revertedWith("SBT: transfer not allowed");

            await expect(
                soulboundCore.transferFrom(user1.address, ethers.ZeroAddress, 1)
            ).to.be.revertedWith("SBT: transfer not allowed");
        });

        it("Should handle approve with zero addresses", async function () {
            await expect(
                soulboundCore.approve(ethers.ZeroAddress, 1)
            ).to.be.revertedWith("SBT: approval not allowed");

            await expect(
                soulboundCore.connect(user1).approve(user2.address, 0)
            ).to.be.revertedWith("SBT: approval not allowed");
        });
    });

    describe("Gas Profiling", function () {
        it("Should profile gas usage for mintSoul", async function () {
            const tx = await soulboundCore.mintSoul(user1.address);
            const receipt = await tx.wait();
            
            console.log(`Gas used for mintSoul: ${receipt.gasUsed.toString()}`);
            expect(receipt.gasUsed).to.be.lessThan(110000); // Реалистичный лимит для полнофункциональный ERC721 SBT
        });

        it("Should profile gas usage for mintSoulBatch", async function () {
            const tx = await soulboundCore.mintSoulBatch(user1.address, 5);
            const receipt = await tx.wait();
            
            const gasPerToken = receipt.gasUsed / 5n;
            console.log(`Gas per token in batch (5 tokens): ${gasPerToken.toString()}`);
            expect(gasPerToken).to.be.lessThan(50000);
        });

        it("Should profile gas usage for burnSoul", async function () {
            await soulboundCore.mintSoul(user1.address);
            
            const tx = await soulboundCore.connect(user1).burnSoul(1);
            const receipt = await tx.wait();
            
            console.log(`Gas used for burnSoul: ${receipt.gasUsed.toString()}`);
        });

        it("Should profile gas usage for locked()", async function () {
            await soulboundCore.mintSoul(user1.address);
            
            const tx = await soulboundCore.locked(1);
            // This is a view function, so no gas cost
            console.log(`locked() is a pure function - no gas cost`);
        });
    });
});
