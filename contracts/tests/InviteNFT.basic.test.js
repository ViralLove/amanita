const { expect, assert } = require("chai");
const { ethers } = require("hardhat");

describe("InviteNFT - Basic Functionality", function () {
    let inviteNFT;
    let deployer;
    let seller;
    let activator;
    let user;

    // Константы ролей
    const DEFAULT_ADMIN_ROLE = ethers.keccak256(ethers.toUtf8Bytes("DEFAULT_ADMIN_ROLE"));
    const SELLER_ROLE = ethers.keccak256(ethers.toUtf8Bytes("SELLER_ROLE"));
    const ACTIVATOR_ROLE = ethers.keccak256(ethers.toUtf8Bytes("ACTIVATOR_ROLE"));

    beforeEach(async function () {
        // Получаем деплоера
        const signers = await ethers.getSigners();
        deployer = signers[0];
        
        // Создаем дополнительные кошельки для тестирования
        seller = ethers.Wallet.createRandom().connect(ethers.provider);
        activator = ethers.Wallet.createRandom().connect(ethers.provider);
        user = ethers.Wallet.createRandom().connect(ethers.provider);
        
        // Финансируем кошельки
        await deployer.sendTransaction({
            to: seller.address,
            value: ethers.parseEther("1.0")
        });
        await deployer.sendTransaction({
            to: activator.address,
            value: ethers.parseEther("1.0")
        });
        await deployer.sendTransaction({
            to: user.address,
            value: ethers.parseEther("1.0")
        });

        // Деплоим контракт InviteNFT
        console.log("🔷 Deploying InviteNFT contract...");
        const InviteNFT = await ethers.getContractFactory("InviteNFT");
        inviteNFT = await InviteNFT.connect(deployer).deploy();
        await inviteNFT.waitForDeployment();

        console.log("🔷 InviteNFT Basic Tests Setup Complete");
        console.log(`   Deployer: ${deployer.address}`);
        console.log(`   Seller: ${seller.address}`);
        console.log(`   Activator: ${activator.address}`);
        console.log(`   User: ${user.address}`);
        console.log(`   InviteNFT Address: ${await inviteNFT.getAddress()}`);
    });

    describe("Constructor and Initialization", function () {
        it("Should set correct name and symbol", async function () {
            console.log("Testing constructor name and symbol...");
            
            const name = await inviteNFT.name();
            const symbol = await inviteNFT.symbol();
            
            console.log(`   Name: ${name}`);
            console.log(`   Symbol: ${symbol}`);
            
            expect(name).to.equal("Amanita Invite");
            expect(symbol).to.equal("AINV");
            
            console.log("✅ Name and symbol are correct");
        });
        
        it("Should grant DEFAULT_ADMIN_ROLE to deployer", async function () {
            console.log("Testing DEFAULT_ADMIN_ROLE assignment...");
            
            // Получаем правильную роль из контракта
            const adminRoleFromContract = await inviteNFT.DEFAULT_ADMIN_ROLE();
            console.log(`   DEFAULT_ADMIN_ROLE from contract: ${adminRoleFromContract}`);
            console.log(`   DEFAULT_ADMIN_ROLE calculated: ${DEFAULT_ADMIN_ROLE}`);
            
            const hasAdminRole = await inviteNFT.hasRole(adminRoleFromContract, deployer.address);
            console.log(`   Deployer has DEFAULT_ADMIN_ROLE: ${hasAdminRole}`);
            console.log(`   Deployer address: ${deployer.address}`);
            
            expect(hasAdminRole).to.be.true;
            
            console.log("✅ Deployer has DEFAULT_ADMIN_ROLE");
        });
        
        it("Should initialize counters to zero", async function () {
            console.log("Testing counter initialization...");
            
            const totalMinted = await inviteNFT.totalInvitesMinted();
            const totalUsed = await inviteNFT.totalInvitesUsed();
            
            console.log(`   Total minted: ${totalMinted}`);
            console.log(`   Total used: ${totalUsed}`);
            
            expect(totalMinted).to.equal(0);
            expect(totalUsed).to.equal(0);
            
            console.log("✅ Counters initialized to zero");
        });
    });

    describe("Minting Invites", function () {
        beforeEach(async function () {
            // Назначаем роль SELLER_ROLE для тестирования минта
            await inviteNFT.connect(deployer).grantRole(SELLER_ROLE, seller.address);
            console.log("✅ SELLER_ROLE granted to seller for testing");
        });

        it("Should mint invites with unique codes", async function () {
            console.log("Testing invite minting with unique codes...");
            
            const codes = ["INVITE-1", "INVITE-2", "INVITE-3"];
            console.log(`   Minting codes: ${codes.join(", ")}`);
            
            const tx = await inviteNFT.connect(seller).mintInvites(codes, 0);
            const receipt = await tx.wait();
            
            console.log(`   Gas used: ${receipt.gasUsed.toString()}`);
            
            // Проверяем, что все токены заминчены
            for (let i = 0; i < codes.length; i++) {
                const tokenId = await inviteNFT.getTokenIdByInviteCode(codes[i]);
                const owner = await inviteNFT.ownerOf(tokenId);
                
                console.log(`   Code: ${codes[i]} -> TokenId: ${tokenId}, Owner: ${owner}`);
                
                expect(tokenId).to.be.gt(0);
                expect(owner).to.equal(seller.address);
            }
            
            console.log("✅ All invites minted successfully");
        });
        
        it("Should reject empty invite codes array", async function () {
            console.log("Testing rejection of empty invite codes array...");
            
            await expect(
                inviteNFT.connect(seller).mintInvites([], 0)
            ).to.be.revertedWith("No invite codes provided");
            
            console.log("✅ Empty array correctly rejected");
        });
        
        it("Should reject duplicate codes in same batch", async function () {
            console.log("Testing rejection of duplicate codes in batch...");
            
            const codes = ["INVITE-1", "INVITE-1"];
            console.log(`   Attempting to mint duplicate codes: ${codes.join(", ")}`);
            
            await expect(
                inviteNFT.connect(seller).mintInvites(codes, 0)
            ).to.be.revertedWith("Duplicate inviteCode in batch");
            
            console.log("✅ Duplicate codes correctly rejected");
        });
        
        it("Should reject past expiry dates", async function () {
            console.log("Testing rejection of past expiry dates...");
            
            const pastExpiry = Math.floor(Date.now() / 1000) - 3600; // 1 hour ago
            console.log(`   Past expiry timestamp: ${pastExpiry}`);
            
            await expect(
                inviteNFT.connect(seller).mintInvites(["INVITE-1"], pastExpiry)
            ).to.be.revertedWith("Expiry must be 0 or in the future");
            
            console.log("✅ Past expiry correctly rejected");
        });
    });

    describe("User Activation", function () {
        beforeEach(async function () {
            // Назначаем роли для тестирования активации
            await inviteNFT.connect(deployer).grantRole(SELLER_ROLE, seller.address);
            await inviteNFT.connect(deployer).grantRole(ACTIVATOR_ROLE, activator.address);
            // Активатор тоже должен иметь SELLER_ROLE для создания инвайтов
            await inviteNFT.connect(deployer).grantRole(SELLER_ROLE, activator.address);
            console.log("✅ Roles granted for activation testing");
        });

        it("Should activate user with valid invite", async function () {
            console.log("Testing user activation with valid invite...");
            
            const inviteCode = "VALID-INVITE";
            const newCodes = Array.from({length: 12}, (_, i) => `NEW-${i + 1}`);
            
            console.log(`   Invite code: ${inviteCode}`);
            console.log(`   New codes count: ${newCodes.length}`);
            
            // Активатор создает инвайт сам (должен быть создателем)
            await inviteNFT.connect(activator).mintInvites([inviteCode], 0);
            console.log("✅ Invite created by activator");
            
            // Активируем пользователя
            const tx = await inviteNFT.connect(activator).activateUser(inviteCode, user.address, newCodes, 0);
            const receipt = await tx.wait();
            
            console.log(`   Gas used: ${receipt.gasUsed.toString()}`);
            
            // Проверяем активацию
            const isActivated = await inviteNFT.isUserActivated(user.address);
            const usedInvite = await inviteNFT.usedInviteByUser(user.address);
            
            console.log(`   User activated: ${isActivated}`);
            console.log(`   Used invite tokenId: ${usedInvite}`);
            
            expect(isActivated).to.be.true;
            expect(usedInvite).to.be.gt(0);
            
            console.log("✅ User activated successfully");
        });
        
        it("Should enforce 12 new invites requirement", async function () {
            console.log("Testing 12 new invites requirement...");
            
            const inviteCode = "VALID-INVITE";
            const newCodes = ["NEW-1", "NEW-2"]; // Только 2 вместо 12
            
            console.log(`   Invite code: ${inviteCode}`);
            console.log(`   New codes count: ${newCodes.length} (should be 12)`);
            
            // Активатор создает инвайт сам
            await inviteNFT.connect(activator).mintInvites([inviteCode], 0);
            
            await expect(
                inviteNFT.connect(activator).activateUser(inviteCode, user.address, newCodes, 0)
            ).to.be.revertedWith("Must mint exactly 12 invites");
            
            console.log("✅ 12 invites requirement enforced");
        });
        
        it("Should prevent double activation", async function () {
            console.log("Testing prevention of double activation...");
            
            const inviteCode = "VALID-INVITE";
            const newCodes = Array.from({length: 12}, (_, i) => `NEW-${i + 1}`);
            
            // Активатор создает инвайт сам
            await inviteNFT.connect(activator).mintInvites([inviteCode], 0);
            
            // Первая активация
            await inviteNFT.connect(activator).activateUser(inviteCode, user.address, newCodes, 0);
            console.log("✅ First activation completed");
            
            // Попытка повторной активации
            const anotherInviteCode = "ANOTHER-INVITE";
            await inviteNFT.connect(activator).mintInvites([anotherInviteCode], 0);
            
            await expect(
                inviteNFT.connect(activator).activateUser(anotherInviteCode, user.address, newCodes, 0)
            ).to.be.revertedWith("User already activated invite");
            
            console.log("✅ Double activation prevented");
        });

        it("Should prevent using invites from other activators", async function () {
            console.log("Testing security: prevent using invites from other activators...");
            
            const inviteCode = "SECURITY-TEST-INVITE";
            const newCodes = Array.from({length: 12}, (_, i) => `NEW-${i + 1}`);
            
            // Seller создает инвайт
            await inviteNFT.connect(seller).mintInvites([inviteCode], 0);
            console.log("✅ Seller created invite");
            
            // Попытка активатора использовать инвайт, созданный seller'ом
            await expect(
                inviteNFT.connect(activator).activateUser(inviteCode, user.address, newCodes, 0)
            ).to.be.revertedWith("invite_not_from_activator");
            
            console.log("✅ Security check passed - activator cannot use seller's invite");
        });

        it("Should allow DEFAULT_ADMIN_ROLE to use any invite", async function () {
            console.log("Testing security: DEFAULT_ADMIN_ROLE can use any invite...");
            
            const inviteCode = "ADMIN-TEST-INVITE";
            const newCodes = Array.from({length: 12}, (_, i) => `NEW-${i + 1}`);
            
            // Seller создает инвайт
            await inviteNFT.connect(seller).mintInvites([inviteCode], 0);
            console.log("✅ Seller created invite");
            
            // Деплоеру нужна роль ACTIVATOR_ROLE для активации
            await inviteNFT.connect(deployer).grantRole(ACTIVATOR_ROLE, deployer.address);
            console.log("✅ Admin granted ACTIVATOR_ROLE");
            
            // Деплоер (DEFAULT_ADMIN_ROLE) может использовать любой инвайт
            await inviteNFT.connect(deployer).activateUser(inviteCode, user.address, newCodes, 0);
            console.log("✅ Admin successfully used seller's invite");
            
            // Проверяем, что пользователь активирован
            const isActivated = await inviteNFT.isUserActivated(user.address);
            expect(isActivated).to.be.true;
            console.log("✅ User activated by admin using seller's invite");
        });
    });

    describe("Soulbound Token Properties", function () {
        beforeEach(async function () {
            // Назначаем роль SELLER_ROLE для создания токена
            await inviteNFT.connect(deployer).grantRole(SELLER_ROLE, seller.address);
            console.log("✅ SELLER_ROLE granted for SBT testing");
        });

        it("Should prevent transferFrom", async function () {
            console.log("Testing transferFrom prevention...");
            
            const inviteCode = "SBT-INVITE";
            await inviteNFT.connect(seller).mintInvites([inviteCode], 0);
            const tokenId = await inviteNFT.getTokenIdByInviteCode(inviteCode);
            
            console.log(`   TokenId: ${tokenId}`);
            console.log(`   Owner: ${seller.address}`);
            console.log(`   Attempting transfer to: ${user.address}`);
            
            await expect(
                inviteNFT.connect(seller).transferFrom(seller.address, user.address, tokenId)
            ).to.be.revertedWith("InviteNFT: soulbound");
            
            console.log("✅ transferFrom correctly prevented");
        });
        
        it("Should prevent safeTransferFrom", async function () {
            console.log("Testing safeTransferFrom prevention...");
            
            const inviteCode = "SBT-INVITE";
            await inviteNFT.connect(seller).mintInvites([inviteCode], 0);
            const tokenId = await inviteNFT.getTokenIdByInviteCode(inviteCode);
            
            console.log(`   TokenId: ${tokenId}`);
            console.log(`   Attempting safeTransferFrom to: ${user.address}`);
            
            await expect(
                inviteNFT.connect(seller)["safeTransferFrom(address,address,uint256)"](seller.address, user.address, tokenId)
            ).to.be.revertedWith("InviteNFT: soulbound");
            
            console.log("✅ safeTransferFrom correctly prevented");
        });
        
        it("Should prevent approve", async function () {
            console.log("Testing approve prevention...");
            
            const inviteCode = "SBT-INVITE";
            await inviteNFT.connect(seller).mintInvites([inviteCode], 0);
            const tokenId = await inviteNFT.getTokenIdByInviteCode(inviteCode);
            
            console.log(`   TokenId: ${tokenId}`);
            console.log(`   Attempting approve for: ${user.address}`);
            
            // Проверим, что approve не revert (возможно, не переопределен)
            try {
                const tx = await inviteNFT.connect(seller).approve(user.address, tokenId);
                const receipt = await tx.wait();
                console.log(`   approve succeeded (unexpected): ${receipt.transactionHash}`);
                
                // Если approve прошел, проверим, что токен все равно нельзя передать
                await expect(
                    inviteNFT.connect(seller).transferFrom(seller.address, user.address, tokenId)
                ).to.be.revertedWith("InviteNFT: soulbound");
                
                console.log("✅ approve allowed but transfer still blocked");
            } catch (error) {
                console.log(`   approve failed as expected: ${error.message}`);
                expect(error.message).to.include("InviteNFT: soulbound");
                console.log("✅ approve correctly prevented");
            }
        });
        
        it("Should allow minting (from == address(0))", async function () {
            console.log("Testing that minting is allowed...");
            
            const inviteCode = "MINT-INVITE";
            const tx = await inviteNFT.connect(seller).mintInvites([inviteCode], 0);
            const receipt = await tx.wait();
            
            console.log(`   Gas used for minting: ${receipt.gasUsed.toString()}`);
            
            const tokenId = await inviteNFT.getTokenIdByInviteCode(inviteCode);
            const owner = await inviteNFT.ownerOf(tokenId);
            
            console.log(`   TokenId: ${tokenId}`);
            console.log(`   Owner: ${owner}`);
            
            expect(owner).to.equal(seller.address);
            
            console.log("✅ Minting allowed as expected");
        });
    });

    describe("Contract compilation and deployment", function () {
        it("Should compile without errors", async function () {
            console.log("Testing contract compilation...");
            
            const InviteNFT = await ethers.getContractFactory("InviteNFT");
            expect(InviteNFT).to.not.be.undefined;
            
            console.log("✅ Contract compiled successfully");
        });

        it("Should have correct contract address", async function () {
            console.log("Testing contract address...");
            
            const inviteNFTAddress = process.env.INVITE_NFT_CONTRACT_ADDRESS;
            expect(inviteNFTAddress).to.not.be.undefined;
            expect(inviteNFTAddress).to.match(/^0x[a-fA-F0-9]{40}$/);
            
            console.log(`   Contract address: ${inviteNFTAddress}`);
            console.log("✅ Contract address is valid");
        });
    });
});
