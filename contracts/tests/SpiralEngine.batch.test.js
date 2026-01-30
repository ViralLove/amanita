const { expect } = require("chai");
const { ethers } = require("hardhat");
const { expectRevertCustom } = require("./helpers/testHelpers");

/**
 * SpiralEngine — тесты mintInviteBatch
 *
 * Покрытие: успешный batch (2–3, 12), пустой массив, разная длина массивов,
 * дубликат inviteCode в batch, вызов не от SELLER_ROLE, пауза, BatchTooLarge.
 */

describe("SpiralEngine - mintInviteBatch", function () {
    let admin, seller, user;
    let spiralEngine;

    beforeEach(async function () {
        [admin, seller, user] = await ethers.getSigners();

        const Logic = await ethers.getContractFactory("SpiralEngineLogic");
        const logicImpl = await Logic.deploy();
        await logicImpl.waitForDeployment();

        const initCalldata = logicImpl.interface.encodeFunctionData("initialize", [
            admin.address
        ]);
        const Proxy = await ethers.getContractFactory("SpiralEngineProxy");
        const proxy = await Proxy.deploy(await logicImpl.getAddress(), initCalldata);
        await proxy.waitForDeployment();

        spiralEngine = Logic.attach(await proxy.getAddress());
        await spiralEngine.connect(admin).grantRole(
            await spiralEngine.SELLER_ROLE(),
            seller.address
        );
    });

    describe("Успешный batch", function () {
        it("Should mint batch of 2 invites successfully", async function () {
            const inviteCodes = ["BATCH_A", "BATCH_B"];
            const expiries = [0n, 0n];

            const tx = await spiralEngine.connect(seller).mintInviteBatch(inviteCodes, expiries);
            const receipt = await tx.wait();

            const parsedLogs = receipt.logs
                .map(log => {
                    try {
                        return spiralEngine.interface.parseLog(log);
                    } catch (_) {
                        return null;
                    }
                })
                .filter(e => e && e.name === "InviteMinted");
            expect(parsedLogs.length).to.equal(2);

            expect(await spiralEngine.totalInvitesMinted()).to.equal(2n);
            expect(await spiralEngine.inviteCodeExists("BATCH_A")).to.be.true;
            expect(await spiralEngine.inviteCodeExists("BATCH_B")).to.be.true;
        });

        it("Should mint batch of 3 invites and return correct tokenIds", async function () {
            const inviteCodes = ["BATCH_1", "BATCH_2", "BATCH_3"];
            const expiries = [0n, 0n, 0n];

            const tokenIds = await spiralEngine.connect(seller).mintInviteBatch.staticCall(inviteCodes, expiries);
            await spiralEngine.connect(seller).mintInviteBatch(inviteCodes, expiries);

            expect(tokenIds.length).to.equal(3);
            expect(await spiralEngine.totalInvitesMinted()).to.equal(3n);
            expect(await spiralEngine.inviteCodeToTokenId("BATCH_1")).to.equal(tokenIds[0]);
            expect(await spiralEngine.inviteCodeToTokenId("BATCH_2")).to.equal(tokenIds[1]);
            expect(await spiralEngine.inviteCodeToTokenId("BATCH_3")).to.equal(tokenIds[2]);
        });

        it("Should mint batch of 12 invites successfully", async function () {
            const inviteCodes = [];
            const expiries = [];
            for (let i = 0; i < 12; i++) {
                inviteCodes.push(`BATCH_12_${i}`);
                expiries.push(0n);
            }

            await spiralEngine.connect(seller).mintInviteBatch(inviteCodes, expiries);

            expect(await spiralEngine.totalInvitesMinted()).to.equal(12n);
            for (let i = 0; i < 12; i++) {
                expect(await spiralEngine.inviteCodeExists(`BATCH_12_${i}`)).to.be.true;
            }
        });
    });

    describe("Валидация массивов", function () {
        it("Should revert on empty inviteCodes (BatchEmpty)", async function () {
            await expectRevertCustom(
                spiralEngine.connect(seller).mintInviteBatch([], []),
                "BatchEmpty",
                spiralEngine
            );
        });

        it("Should revert when inviteCodes and expiries length mismatch (BatchLengthMismatch)", async function () {
            await expectRevertCustom(
                spiralEngine.connect(seller).mintInviteBatch(["A", "B"], [0n]),
                "BatchLengthMismatch",
                spiralEngine
            );
            await expectRevertCustom(
                spiralEngine.connect(seller).mintInviteBatch(["A"], [0n, 0n]),
                "BatchLengthMismatch",
                spiralEngine
            );
        });

        it("Should revert when batch size exceeds MAX_BATCH_SIZE (BatchTooLarge)", async function () {
            const maxBatch = Number(await spiralEngine.MAX_BATCH_SIZE());
            const inviteCodes = Array(maxBatch + 1).fill("X").map((_, i) => `TOOLARGE_${i}`);
            const expiries = Array(maxBatch + 1).fill(0n);

            await expectRevertCustom(
                spiralEngine.connect(seller).mintInviteBatch(inviteCodes, expiries),
                "BatchTooLarge",
                spiralEngine
            );
        });

        it("Should revert when duplicate inviteCode in same batch (InviteCodeAlreadyExists)", async function () {
            await expectRevertCustom(
                spiralEngine.connect(seller).mintInviteBatch(["DUP", "DUP"], [0n, 0n]),
                "InviteCodeAlreadyExists",
                spiralEngine
            );
        });
    });

    describe("Роли и пауза", function () {
        it("Should revert when caller has no SELLER_ROLE", async function () {
            await expectRevertCustom(
                spiralEngine.connect(user).mintInviteBatch(["A", "B"], [0n, 0n]),
                "AccessControlUnauthorizedAccount",
                spiralEngine
            );
        });

        it("Should revert when contract is paused", async function () {
            await spiralEngine.connect(admin).pause();
            await expectRevertCustom(
                spiralEngine.connect(seller).mintInviteBatch(["A", "B"], [0n, 0n]),
                "EnforcedPause",
                spiralEngine
            );
            await spiralEngine.connect(admin).unpause();
        });
    });
});
