/**
 * E2E: Action 43 - Contract Registration
 * 
 * Tests product registration on ProductRegistry contract with on-chain validation
 */

const { expect } = require('chai');
const {
  E2EHarness,
  expectEvent,
  expectRevertCustom,
  assertBusinessIdMapping,
  assertBusinessIdCleared,
  assertRegisteredProxy,
  assertSellerState
} = require('../../../helpers');
const { ethers } = require('hardhat');

describe('E2E: Action 43 - Contract Registration', function() {
  this.timeout(120000);

  let harness;

  before(async function() {
    harness = new E2EHarness();
    await harness.startHardhatNode();
    harness.loadTestEnv();
    await harness.resetNetwork();
  });

  after(async () => {
    await harness.stopHardhatNode();
    harness.restoreEnv();
  });

  beforeEach(async () => {
    await harness.resetNetwork();
  });

  describe('Infrastructure', () => {
    it('should have ready infrastructure', async () => {
      const blockNumber = await ethers.provider.getBlockNumber();
      expect(blockNumber).to.be.a('number');
      console.log('✓ Infrastructure ready');
    });
  });

  describe('Seller Preparation via Harness Helper', () => {
    it('должен активировать seller и выдать роли через deployProductSuite()', async function() {
      this.timeout(60000);

      const suite = await harness.deployProductSuite({
        forceRedeploy: true,
        invitesPrefix: 'ACTION43'
      });

      const SpiralEngine = await ethers.getContractAt('SpiralEngineLogic', suite.spiralEngineAddress);
      const sellerAddress = await suite.seller.getAddress();
      const adminAddress = await suite.admin.getAddress();

      await assertSellerState(SpiralEngine, sellerAddress, {
        activated: true,
        sellerRole: true,
        activatorRole: true,
        activatorAddress: adminAddress
      });
    });
  });

  describe('ProductRegistry Deployment', () => {
    it('должен деплоить ProductRegistry и связать с OCR', async () => {
      console.log('Фаза 1: Понимание текущего состояния — готовим suite');
      const suite = await harness.deployProductSuite({ forceRedeploy: true });

      console.log('Фаза 2: Проверка infrastructure suite');
      expect(suite.productRegistry).to.exist;
      expect(suite.componentRegistry).to.exist;

      const registryAddress = suite.productRegistryAddress;
      const logicAddress = suite.productRegistryLogicAddress;

      console.log('Фаза 3: Проверяем связь ProductRegistry ↔ OCR');
      const onChainComponentRegistry = await suite.productRegistry.componentRegistry();
      expect(onChainComponentRegistry).to.equal(suite.componentRegistryAddress);

      console.log('Фаза 4: Валидация через MagicRegistryHelper');
      const entry = harness.loadContractFromSuite('ProductRegistry');
      assertRegisteredProxy({ ProductRegistry: entry }, 'ProductRegistry', registryAddress, logicAddress);

      console.log('Фаза 5: Проверка UUPS Deployment');
      const validation = await harness.validateUUPSDeployment(registryAddress, logicAddress);
      expect(validation.proxyDeployed).to.be.true;

      console.log('Фаза 6: Тест завершён — ProductRegistry связан с OCR');
    });
  });

  describe('Product Registration', () => {
    let suite;

    beforeEach(async () => {
      suite = await harness.deployProductSuite({ forceRedeploy: true });
    });

    it('должен регистрировать продукт с businessId и событием', async () => {
      console.log('Фаза 1: Готовим начальные данные');
      const { productRegistry, seller, sellerComponentIds } = suite;
      const businessId = 'e2e-prod-001';
      const metadataCID = 'QmE2EProductCID1';

      console.log('Фаза 2: Проверяем событие ProductCreated');
      await expectEvent(
        productRegistry
          .connect(seller)
          .createProduct(businessId, [sellerComponentIds[0]], metadataCID),
        productRegistry,
        'ProductCreated',
        async (args) => {
          expect(args.seller).to.equal(seller.address);
          expect(args.businessId).to.equal(businessId);
          expect(args.metadataCID).to.equal(metadataCID);
        }
      );

      console.log('Фаза 3: Проверяем mapping businessId → productId');
      await assertBusinessIdMapping(productRegistry, businessId, 1);

      console.log('Фаза 4: Сценарий завершён успешно');
    });

    it('должен сохранять состояние продукта', async () => {
      console.log('Фаза 1: Подготовка данных');
      const { productRegistry, seller, sellerComponentIds } = suite;
      const businessId = 'e2e-prod-state';
      const metadataCID = 'QmE2EProductCID2';

      console.log('Фаза 2: Создание продукта через suite');
      await productRegistry
        .connect(seller)
        .createProduct(businessId, [sellerComponentIds[1]], metadataCID);

      console.log('Фаза 3: Проверка mapping и состояния');
      const productId = await productRegistry.getProductIdByBusinessId(businessId);
      await assertBusinessIdMapping(productRegistry, businessId, Number(productId));
      const stored = await productRegistry.getProduct(Number(productId));
      expect(stored.businessId).to.equal(businessId);
      expect(stored.metadataCID).to.equal(metadataCID);
      expect(stored.componentIds[0]).to.equal(sellerComponentIds[1]);

      console.log('Фаза 4: Сценарий проверки state завершён');
    });

    it('должен обрабатывать bulk регистрацию 5 продуктов', async () => {
      console.log('Фаза 1: Подготовка bulk данных');
      const { productRegistry, seller, sellerComponentIds } = suite;
      const bulkBusinessIds = Array.from({ length: 5 }, (_, i) => `e2e-bulk-${i + 1}`);

      console.log('Фаза 2: Регистрация продуктов через suite');
      for (let i = 0; i < bulkBusinessIds.length; i++) {
        await productRegistry
          .connect(seller)
          .createProduct(bulkBusinessIds[i], [sellerComponentIds[i % sellerComponentIds.length]], `QmBulk${i}`);
      }

      console.log('Фаза 3: Проверка mapping каждого businessId');
      for (let i = 0; i < bulkBusinessIds.length; i++) {
        const productId = await productRegistry.getProductIdByBusinessId(bulkBusinessIds[i]);
        await assertBusinessIdMapping(productRegistry, bulkBusinessIds[i], i + 1);
      }

      console.log(`Фаза 4: Bulk регистрация завершена (${bulkBusinessIds.length} продуктов)`);
    });
  });

  describe('Error Scenarios', () => {
    let suite;

    beforeEach(async () => {
      suite = await harness.deployProductSuite({ forceRedeploy: true });
    });

    it('должен блокировать повторный businessId', async () => {
      console.log('Фаза 1: Подготовка исходного продукта');
      const { productRegistry, seller, sellerComponentIds } = suite;
      const businessId = 'e2e-duplicate';

      await productRegistry
        .connect(seller)
        .createProduct(businessId, [sellerComponentIds[0]], 'QmDupCID');

      console.log('Фаза 2: Проверка повторного использования businessId');
      await expectRevertCustom(
        productRegistry
          .connect(seller)
          .createProduct(businessId, [sellerComponentIds[1]], 'QmDupCID2'),
        'BusinessIdExists',
        productRegistry
      );

      console.log('Фаза 3: Ошибка BusinessIdExists подтверждена');
    });

    it('должен очищать businessId mapping после clearSellerCatalog', async () => {
      console.log('Фаза 1: Создаём продукт для проверки очистки');
      const { productRegistry, seller, sellerComponentIds } = suite;
      const businessId = 'e2e-clear';

      await productRegistry
        .connect(seller)
        .createProduct(businessId, [sellerComponentIds[0]], 'QmClearCID');

      console.log('Фаза 2: Проверяем наличие записи в mapping');
      await assertBusinessIdMapping(productRegistry, businessId, 1);

      console.log('Фаза 3: Очищаем каталог от имени продавца');
      const sellerAddress = await seller.getAddress();
      await productRegistry.connect(seller).clearSellerCatalog(sellerAddress);

      console.log('Фаза 4: Проверяем, что businessId очищен');
      await assertBusinessIdCleared(productRegistry, businessId);

      console.log('Фаза 5: Очистка каталога проверена');
    });
  });

  describe('Performance', () => {
    let suite;

    beforeEach(async () => {
      suite = await harness.deployProductSuite({ forceRedeploy: true });
    });

    it('должен регистрировать продукт < 1s', async () => {
      const { productRegistry, seller, sellerComponentIds } = suite;
      const timer = harness.measureExecutionTime('Action 43 product registration');

      await productRegistry
        .connect(seller)
        .createProduct('e2e-perf', [sellerComponentIds[0]], 'QmPerfCID');

      const duration = timer.end();
      expect(duration).to.be.lessThan(1000);
    });
  });
});
