const { expect } = require("chai");
const { ethers } = require("hardhat");
const { expectRevertCustom, expectRevertReason, expectNotReverted, expectEvent } = require("./helpers/testHelpers");

/**
 * ActivityRegistry UUPS — Comprehensive Tests (Фаза 3: Proxy + Logic)
 *
 * Цель: P0 + P1 покрытие по solution-architecture-task1-activity-registry.md.
 * Деплой: Logic → Proxy(logic, initCalldata) → attach Logic ABI к Proxy.
 */
describe("ActivityRegistry UUPS - Comprehensive Tests", function () {
    let admin, creator, otherCreator, user1;
    let activityRegistry, spiralEngine, logic, proxy;

    beforeEach(async function () {
        [admin, creator, otherCreator, user1] = await ethers.getSigners();

        // Деплой MockSpiralEngine
        const MockSpiralEngine = await ethers.getContractFactory("contracts/mocks/MockSpiralEngine.sol:MockSpiralEngine");
        spiralEngine = await MockSpiralEngine.deploy();
        await spiralEngine.waitForDeployment();

        // ACTIVATOR_ROLE и setUserActivated для creator и otherCreator
        const ACTIVATOR_ROLE = await spiralEngine.ACTIVATOR_ROLE();
        await spiralEngine.grantRole(ACTIVATOR_ROLE, creator.address);
        await spiralEngine.setUserActivated(creator.address, true);
        await spiralEngine.grantRole(ACTIVATOR_ROLE, otherCreator.address);
        await spiralEngine.setUserActivated(otherCreator.address, true);

        // Деплой ActivityRegistryLogic
        const Logic = await ethers.getContractFactory("ActivityRegistryLogic");
        logic = await Logic.deploy();
        await logic.waitForDeployment();

        // Encode initialize(admin, spiralEngine)
        const initCalldata = logic.interface.encodeFunctionData("initialize", [
            admin.address,
            await spiralEngine.getAddress()
        ]);

        // Деплой ActivityRegistryProxy
        const Proxy = await ethers.getContractFactory("ActivityRegistryProxy");
        proxy = await Proxy.deploy(await logic.getAddress(), initCalldata);
        await proxy.waitForDeployment();

        // Attach Logic ABI к адресу Proxy
        activityRegistry = Logic.attach(await proxy.getAddress());
    });

    // ========== P0: Deployment и инициализация ==========
    describe("Deployment and initialization", function () {
        it("должен задеплоить Proxy и привязать Logic к Proxy", async function () {
            const proxyAddr = await proxy.getAddress();
            expect(proxyAddr).to.match(/^0x[a-fA-F0-9]{40}$/);
            expect(await activityRegistry.getAddress()).to.equal(proxyAddr);
        });

        it("должен установить spiralEngine через initialize", async function () {
            expect(await activityRegistry.spiralEngine()).to.equal(await spiralEngine.getAddress());
        });

        it("admin имеет DEFAULT_ADMIN_ROLE, ADMIN_ROLE, UPGRADER_ROLE", async function () {
            const DEFAULT_ADMIN_ROLE = await activityRegistry.DEFAULT_ADMIN_ROLE();
            const ADMIN_ROLE = await activityRegistry.ADMIN_ROLE();
            const UPGRADER_ROLE = await activityRegistry.UPGRADER_ROLE();
            expect(await activityRegistry.hasRole(DEFAULT_ADMIN_ROLE, admin.address)).to.be.true;
            expect(await activityRegistry.hasRole(ADMIN_ROLE, admin.address)).to.be.true;
            expect(await activityRegistry.hasRole(UPGRADER_ROLE, admin.address)).to.be.true;
        });

        it("повторный initialize ревертит с InvalidInitialization", async function () {
            await expectRevertCustom(
                activityRegistry.connect(admin).initialize(admin.address, await spiralEngine.getAddress()),
                "InvalidInitialization",
                activityRegistry
            );
        });

        it("upgradeToAndCall от не-UPGRADER ревертит с AccessControlUnauthorizedAccount", async function () {
            const LogicV2 = await ethers.getContractFactory("ActivityRegistryLogic");
            const logicV2 = await LogicV2.deploy();
            await logicV2.waitForDeployment();
            await expectRevertCustom(
                activityRegistry.connect(creator).upgradeToAndCall(await logicV2.getAddress(), "0x"),
                "AccessControlUnauthorizedAccount",
                activityRegistry
            );
        });

        it("upgradeToAndCall(ZeroAddress) от admin ревертит с ZeroAddress", async function () {
            await expectRevertCustom(
                activityRegistry.connect(admin).upgradeToAndCall(ethers.ZeroAddress, "0x"),
                "ZeroAddress",
                activityRegistry
            );
        });
    });

    // ========== P0: Создание (createActivity Event/Service) ==========
    describe("Create activity", function () {
        it("должен создать активность типа Event и вернуть activityId 1", async function () {
            const id = await activityRegistry.connect(creator).createActivity.staticCall(0, "QmEvent1");
            expect(Number(id)).to.equal(1);
            await activityRegistry.connect(creator).createActivity(0, "QmEvent1");
            const ids = await activityRegistry.getActivitiesByCreator(creator.address);
            expect(Number(ids[0])).to.equal(1);
        });

        it("должен создать активность типа Service и вернуть activityId", async function () {
            await activityRegistry.connect(creator).createActivity(1, "QmService1"); // 1 = Service
            const ids = await activityRegistry.getActivitiesByCreator(creator.address);
            expect(ids.length).to.equal(1);
            expect(Number(ids[0])).to.equal(1);
        });

        it("createActivity(Event, cid): начальное active = false, событие ActivityCreated", async function () {
            await expectEvent(
                activityRegistry.connect(creator).createActivity(0, "QmEventCID"),
                activityRegistry,
                "ActivityCreated",
                args => {
                    expect(args.creator).to.equal(creator.address);
                    expect(Number(args.activityId)).to.equal(1);
                    expect(Number(args.activity_type)).to.equal(0);
                    expect(args.metadataCID).to.equal("QmEventCID");
                    expect(args.active).to.be.false;
                }
            );
        });
    });

    // ========== P0: Получение (getActivity) ==========
    describe("Get activity", function () {
        it("getActivity(activityId) возвращает корректную структуру", async function () {
            await activityRegistry.connect(creator).createActivity(0, "QmGetTest");
            const a = await activityRegistry.getActivity(1);
            expect(Number(a.id)).to.equal(1);
            expect(a.creator).to.equal(creator.address);
            expect(Number(a.activity_type)).to.equal(0);
            expect(a.metadataCID).to.equal("QmGetTest");
            expect(a.active).to.be.false;
        });

        it("getActivity(несуществующий id) ревертит с ActivityNotFound", async function () {
            await expectRevertCustom(activityRegistry.getActivity(0), "ActivityNotFound", activityRegistry);
            await expectRevertCustom(activityRegistry.getActivity(999), "ActivityNotFound", activityRegistry);
        });
    });

    // ========== P0: Публикация и снятие (activate/deactivate) ==========
    describe("Activate and deactivate", function () {
        it("activateActivity(activityId) только от creator; active = true; событие ActivityActivated", async function () {
            await activityRegistry.connect(creator).createActivity(0, "QmAct");
            await expectEvent(
                activityRegistry.connect(creator).activateActivity(1),
                activityRegistry,
                "ActivityActivated",
                args => {
                    expect(Number(args.activityId)).to.equal(1);
                    expect(args.initiator).to.equal(creator.address);
                }
            );
            const a = await activityRegistry.getActivity(1);
            expect(a.active).to.be.true;
        });

        it("deactivateActivity(activityId) только от creator; active = false; событие ActivityDeactivated", async function () {
            await activityRegistry.connect(creator).createActivity(0, "QmDeact");
            await activityRegistry.connect(creator).activateActivity(1);
            await expectEvent(
                activityRegistry.connect(creator).deactivateActivity(1),
                activityRegistry,
                "ActivityDeactivated",
                args => {
                    expect(Number(args.activityId)).to.equal(1);
                    expect(args.initiator).to.equal(creator.address);
                }
            );
            const a = await activityRegistry.getActivity(1);
            expect(a.active).to.be.false;
        });

        it("после deactivate getPublishedActivityIds не содержит id (swap-and-pop)", async function () {
            await activityRegistry.connect(creator).createActivity(0, "QmSwap");
            await activityRegistry.connect(creator).activateActivity(1);
            let published = await activityRegistry.getPublishedActivityIds();
            expect(published.map(n => Number(n))).to.deep.equal([1]);
            await activityRegistry.connect(creator).deactivateActivity(1);
            published = await activityRegistry.getPublishedActivityIds();
            expect(published.length).to.equal(0);
        });

        it("activateActivity повторно (уже active) ревертит с ActivityAlreadyActive", async function () {
            await activityRegistry.connect(creator).createActivity(0, "QmDup");
            await activityRegistry.connect(creator).activateActivity(1);
            await expectRevertCustom(
                activityRegistry.connect(creator).activateActivity(1),
                "ActivityAlreadyActive",
                activityRegistry
            );
        });

        it("deactivateActivity черновика (уже !active) ревертит с ActivityNotActive", async function () {
            await activityRegistry.connect(creator).createActivity(0, "QmDraft");
            await expectRevertCustom(
                activityRegistry.connect(creator).deactivateActivity(1),
                "ActivityNotActive",
                activityRegistry
            );
        });

        it("activateActivity от не-creator ревертит с NotActivityCreator", async function () {
            await activityRegistry.connect(creator).createActivity(0, "QmOwn");
            await expectRevertCustom(
                activityRegistry.connect(otherCreator).activateActivity(1),
                "NotActivityCreator",
                activityRegistry
            );
        });

        it("deactivateActivity от не-creator ревертит с NotActivityCreator", async function () {
            await activityRegistry.connect(creator).createActivity(0, "QmOwn2");
            await activityRegistry.connect(creator).activateActivity(1);
            await expectRevertCustom(
                activityRegistry.connect(otherCreator).deactivateActivity(1),
                "NotActivityCreator",
                activityRegistry
            );
        });

        it("admin может forceDeactivate чужую активность", async function () {
            await activityRegistry.connect(creator).createActivity(0, "QmForce");
            await activityRegistry.connect(creator).activateActivity(1);
            expect((await activityRegistry.getActivity(1)).active).to.be.true;
            expect((await activityRegistry.getPublishedActivityIds()).map(n => Number(n))).to.deep.equal([1]);
            await activityRegistry.connect(admin).forceDeactivate(1);
            expect((await activityRegistry.getActivity(1)).active).to.be.false;
            expect((await activityRegistry.getPublishedActivityIds()).length).to.equal(0);
        });
    });

    // ========== P0: Списки ==========
    describe("Lists", function () {
        it("getActivitiesByCreator(creator) возвращает список id", async function () {
            await activityRegistry.connect(creator).createActivity(0, "QmA");
            await activityRegistry.connect(creator).createActivity(1, "QmB");
            const ids = await activityRegistry.getActivitiesByCreator(creator.address);
            expect(ids.map(n => Number(n))).to.deep.equal([1, 2]);
        });

        it("getPublishedActivityIds() после активации содержит id", async function () {
            await activityRegistry.connect(creator).createActivity(0, "QmPub");
            expect((await activityRegistry.getPublishedActivityIds()).length).to.equal(0);
            await activityRegistry.connect(creator).activateActivity(1);
            const published = await activityRegistry.getPublishedActivityIds();
            expect(published.map(n => Number(n))).to.deep.equal([1]);
        });
    });

    // ========== P0: Access control ==========
    describe("Access control", function () {
        it("createActivity без роли ACTIVATOR_ROLE ревертит с NotActivatedActivityCreator", async function () {
            await expectRevertCustom(
                activityRegistry.connect(user1).createActivity(0, "QmNoRole"),
                "NotActivatedActivityCreator",
                activityRegistry
            );
        });

        it("createActivity при наличии роли но без активации (usedInviteByUser == 0) ревертит с NotActivatedActivityCreator", async function () {
            const ACTIVATOR_ROLE = await spiralEngine.ACTIVATOR_ROLE();
            await spiralEngine.grantRole(ACTIVATOR_ROLE, user1.address);
            expect(await spiralEngine.usedInviteByUser(user1.address)).to.equal(0n);
            await expectRevertCustom(
                activityRegistry.connect(user1).createActivity(0, "QmNoAct"),
                "NotActivatedActivityCreator",
                activityRegistry
            );
        });

        it("pause/unpause только ADMIN_ROLE", async function () {
            await expectRevertCustom(
                activityRegistry.connect(creator).pause(),
                "AccessControlUnauthorizedAccount",
                activityRegistry
            );
            await activityRegistry.connect(admin).pause();
            expect(await activityRegistry.paused()).to.be.true;
            await expectNotReverted(activityRegistry.connect(admin).unpause(), "unpause не должен ревертиться");
            expect(await activityRegistry.paused()).to.be.false;
        });
    });

    // ========== P0: Валидация ==========
    describe("Validation", function () {
        it("createActivity с пустым metadataCID ревертит с EmptyCID", async function () {
            await expectRevertCustom(
                activityRegistry.connect(creator).createActivity(0, ""),
                "EmptyCID",
                activityRegistry
            );
        });

        it("activate несуществующей активности ревертит с NotActivityCreator", async function () {
            // Модификатор onlyOwnActivity срабатывает первым: activities[999].creator == address(0) != msg.sender → NotActivityCreator
            await expectRevertCustom(
                activityRegistry.connect(creator).activateActivity(999),
                "NotActivityCreator",
                activityRegistry
            );
        });
    });

    // ========== P0: Pause ==========
    describe("Pause", function () {
        it("при pause() createActivity ревертит", async function () {
            await activityRegistry.connect(admin).pause();
            await expectRevertCustom(
                activityRegistry.connect(creator).createActivity(0, "QmPaused"),
                "EnforcedPause",
                activityRegistry
            );
        });

        it("при pause() activateActivity ревертит", async function () {
            await activityRegistry.connect(creator).createActivity(0, "QmP");
            await activityRegistry.connect(admin).pause();
            await expectRevertCustom(
                activityRegistry.connect(creator).activateActivity(1),
                "EnforcedPause",
                activityRegistry
            );
        });

        it("при pause() deactivateActivity ревертит", async function () {
            await activityRegistry.connect(creator).createActivity(0, "QmP2");
            await activityRegistry.connect(creator).activateActivity(1);
            await activityRegistry.connect(admin).pause();
            await expectRevertCustom(
                activityRegistry.connect(creator).deactivateActivity(1),
                "EnforcedPause",
                activityRegistry
            );
        });
    });

    // ========== P0: setSpiralEngine ==========
    describe("setSpiralEngine", function () {
        it("admin может вызвать setSpiralEngine; эмитится SpiralEngineUpdated", async function () {
            const MockSpiralEngine2 = await ethers.getContractFactory("contracts/mocks/MockSpiralEngine.sol:MockSpiralEngine");
            const spiral2 = await MockSpiralEngine2.deploy();
            await spiral2.waitForDeployment();
            const oldAddr = await activityRegistry.spiralEngine();
            const newAddr = await spiral2.getAddress();
            await expectEvent(
                activityRegistry.connect(admin).setSpiralEngine(newAddr),
                activityRegistry,
                "SpiralEngineUpdated",
                args => {
                    expect(args.oldSpiralEngine).to.equal(oldAddr);
                    expect(args.newSpiralEngine).to.equal(newAddr);
                }
            );
            expect(await activityRegistry.spiralEngine()).to.equal(newAddr);
        });

        it("setSpiralEngine от не-admin ревертит с AccessControlUnauthorizedAccount", async function () {
            const MockSpiralEngine2 = await ethers.getContractFactory("contracts/mocks/MockSpiralEngine.sol:MockSpiralEngine");
            const spiral2 = await MockSpiralEngine2.deploy();
            await spiral2.waitForDeployment();
            await expectRevertCustom(
                activityRegistry.connect(creator).setSpiralEngine(await spiral2.getAddress()),
                "AccessControlUnauthorizedAccount",
                activityRegistry
            );
        });

        it("setSpiralEngine(address(0)) ревертит с ZeroAddress", async function () {
            await expectRevertCustom(
                activityRegistry.connect(admin).setSpiralEngine(ethers.ZeroAddress),
                "ZeroAddress",
                activityRegistry
            );
        });

        it("setSpiralEngine при pause ревертит с EnforcedPause", async function () {
            await activityRegistry.connect(admin).pause();
            const MockSpiralEngine2 = await ethers.getContractFactory("contracts/mocks/MockSpiralEngine.sol:MockSpiralEngine");
            const spiral2 = await MockSpiralEngine2.deploy();
            await spiral2.waitForDeployment();
            await expectRevertCustom(
                activityRegistry.connect(admin).setSpiralEngine(await spiral2.getAddress()),
                "EnforcedPause",
                activityRegistry
            );
        });

        it("P1: после setSpiralEngine createActivity использует новый engine — creator не активирован на spiral2 → NotActivatedActivityCreator", async function () {
            const MockSpiralEngine2 = await ethers.getContractFactory("contracts/mocks/MockSpiralEngine.sol:MockSpiralEngine");
            const spiral2 = await MockSpiralEngine2.deploy();
            await spiral2.waitForDeployment();
            // На spiral2 для creator не выдаём ACTIVATOR_ROLE и не вызываем setUserActivated — контракт должен использовать новый engine
            await activityRegistry.connect(admin).setSpiralEngine(await spiral2.getAddress());
            await expectRevertCustom(
                activityRegistry.connect(creator).createActivity(0, "QmAfterSetSpiral"),
                "NotActivatedActivityCreator",
                activityRegistry
            );
        });
    });

    // ========== P1: Edge cases и доп. сценарии (unit-test-build) ==========
    describe("P1 — Edge cases и доп. сценарии", function () {
        it("несколько активностей у одного creator: список id и порядок", async function () {
            await activityRegistry.connect(creator).createActivity(0, "Qm1");
            await activityRegistry.connect(creator).createActivity(1, "Qm2");
            await activityRegistry.connect(creator).createActivity(0, "Qm3");
            await activityRegistry.connect(creator).createActivity(1, "Qm4");
            const ids = await activityRegistry.getActivitiesByCreator(creator.address);
            expect(ids.length).to.equal(4);
            expect(ids.map(n => Number(n))).to.deep.equal([1, 2, 3, 4]);
            const a2 = await activityRegistry.getActivity(2);
            expect(Number(a2.activity_type)).to.equal(1);
            expect(a2.metadataCID).to.equal("Qm2");
        });

        it("getPublishedActivityIds пустой до первой активации", async function () {
            const emptyBefore = await activityRegistry.getPublishedActivityIds();
            expect(emptyBefore.length).to.equal(0);
            await activityRegistry.connect(creator).createActivity(0, "QmDraft");
            const afterCreate = await activityRegistry.getPublishedActivityIds();
            expect(afterCreate.length).to.equal(0);
            await activityRegistry.connect(creator).activateActivity(1);
            const afterActivate = await activityRegistry.getPublishedActivityIds();
            expect(afterActivate.map(n => Number(n))).to.deep.equal([1]);
        });

        it("P1: при pause() createActivity ревертит (явная проверка Pausable)", async function () {
            await activityRegistry.connect(admin).pause();
            await expectRevertCustom(
                activityRegistry.connect(creator).createActivity(0, "QmP1"),
                "EnforcedPause",
                activityRegistry
            );
        });
    });

    // ========== P0: Full State Preservation после upgradeToAndCall ==========
    describe("Full State Preservation", function () {
        it("сохраняет состояние при upgradeToAndCall; новая активность после апгрейда", async function () {
            await activityRegistry.connect(creator).createActivity(0, "QmFsp1");
            await activityRegistry.connect(creator).createActivity(1, "QmFsp2");
            await activityRegistry.connect(creator).activateActivity(1);
            await activityRegistry.connect(otherCreator).createActivity(0, "QmFsp3");

            const activity1Before = await activityRegistry.getActivity(1);
            const activity2Before = await activityRegistry.getActivity(2);
            const activity3Before = await activityRegistry.getActivity(3);
            const byCreatorBefore = await activityRegistry.getActivitiesByCreator(creator.address);
            const byOtherBefore = await activityRegistry.getActivitiesByCreator(otherCreator.address);
            const publishedBefore = await activityRegistry.getPublishedActivityIds();

            const LogicV2 = await ethers.getContractFactory("ActivityRegistryLogic");
            const logicV2 = await LogicV2.deploy();
            await logicV2.waitForDeployment();
            await activityRegistry.connect(admin).upgradeToAndCall(await logicV2.getAddress(), "0x");

            expect((await activityRegistry.getActivity(1)).id).to.equal(activity1Before.id);
            expect((await activityRegistry.getActivity(1)).creator).to.equal(activity1Before.creator);
            expect((await activityRegistry.getActivity(1)).metadataCID).to.equal(activity1Before.metadataCID);
            expect((await activityRegistry.getActivity(1)).active).to.equal(activity1Before.active);

            expect((await activityRegistry.getActivity(2)).metadataCID).to.equal(activity2Before.metadataCID);
            expect((await activityRegistry.getActivity(2)).active).to.equal(activity2Before.active);

            expect((await activityRegistry.getActivity(3)).creator).to.equal(activity3Before.creator);

            const byCreatorAfter = await activityRegistry.getActivitiesByCreator(creator.address);
            const byOtherAfter = await activityRegistry.getActivitiesByCreator(otherCreator.address);
            const publishedAfter = await activityRegistry.getPublishedActivityIds();
            expect(byCreatorAfter.map(n => n.toString())).to.deep.equal(byCreatorBefore.map(n => n.toString()));
            expect(byOtherAfter.map(n => n.toString())).to.deep.equal(byOtherBefore.map(n => n.toString()));
            expect(publishedAfter.map(n => n.toString())).to.deep.equal(publishedBefore.map(n => n.toString()));

            await activityRegistry.connect(creator).createActivity(0, "QmAfterUpgrade");
            const idsAfter = await activityRegistry.getActivitiesByCreator(creator.address);
            expect(idsAfter.length).to.equal(3);
            expect(Number(idsAfter[2])).to.equal(4);
            await activityRegistry.connect(creator).activateActivity(4);
            expect((await activityRegistry.getActivity(4)).active).to.be.true;
            const publishedAfterNew = await activityRegistry.getPublishedActivityIds();
            expect(publishedAfterNew.map(n => Number(n))).to.include(4);
        });
    });
});
