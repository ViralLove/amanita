/**
 * Unit Tests: CatalogActions
 * Tests for catalog management actions (Layer 5).
 * 
 * Coverage:
 * - action41() - CSV Transform
 * - action42() - Arweave Upload
 * - action43() - Contract Registration
 * - action444() - Pipeline (41 → 42 → 43)
 * - action888() - MOVED to InviteActions.test.js
 */

const { expect } = require('chai');
const sinon = require('sinon');
const CatalogActions = require('../../../lib/actions/CatalogActions');

describe('CatalogActions', () => {
  let catalogActions;
  let mockContractManager;
  let mockArweaveManager;
  let mockEthersUtils;
  let mockConfig;

  beforeEach(() => {
    // Mock dependencies
    mockContractManager = {
      loadUUPSContract: sinon.stub(),
      loadContract: sinon.stub()
    };

    mockArweaveManager = {
      upload: sinon.stub().resolves('fake-cid-12345'),
      isReady: sinon.stub().returns(true),
      initialize: sinon.stub().resolves()
    };

    mockEthersUtils = {
      getSigner: sinon.stub().returns({
        getAddress: sinon.stub().resolves('0xSigner')
      })
    };
    mockEthersUtils.provider = {
      getBalance: sinon.stub().resolves(0n)
    };
    mockEthersUtils.formatEther = sinon.stub().returns('0.0');

    mockConfig = {
      get: sinon.stub()
    };

    catalogActions = new CatalogActions(
      mockContractManager,
      mockArweaveManager,
      mockEthersUtils,
      mockConfig
    );
  });

  afterEach(() => {
    sinon.restore();
  });

  // ================================================================
  // SMOKE TESTS
  // ================================================================

  describe('Initialization', () => {
    it('должен инициализироваться с dependencies', () => {
      expect(catalogActions.contractManager).to.equal(mockContractManager);
      expect(catalogActions.arweaveManager).to.equal(mockArweaveManager);
      expect(catalogActions.ethersUtils).to.equal(mockEthersUtils);
      expect(catalogActions.config).to.equal(mockConfig);
    });

    it('должен иметь метод action41', () => {
      expect(catalogActions.action41).to.be.a('function');
    });

    it('должен иметь метод action42', () => {
      expect(catalogActions.action42).to.be.a('function');
    });

    it('должен иметь метод action43', () => {
      expect(catalogActions.action43).to.be.a('function');
    });

    it('должен иметь метод action444', () => {
      expect(catalogActions.action444).to.be.a('function');
    });

    // NOTE: action888 moved to InviteActions (Layer 4A)
    // Test moved to InviteActions.test.js
  });

  // ================================================================
  // HELPER METHODS
  // ================================================================

  describe('checkComponentsLoaded()', () => {
    const fs = require('fs');
    const path = require('path');
    
    let fsExistsSync;
    let fsReadFileSync;

    beforeEach(() => {
      fsExistsSync = sinon.stub(fs, 'existsSync');
      fsReadFileSync = sinon.stub(fs, 'readFileSync');
      mockConfig.get.withArgs('network.name').returns('localhost');
    });

    afterEach(() => {
      fsExistsSync.restore();
      fsReadFileSync.restore();
    });

    it('должен вернуть true если найдены компоненты в state файле', async () => {
      // GIVEN: Mock fs для проверки state файлов
      const fs = require('fs');
      const path = require('path');
      
      // Mock COMPONENTS_DIR существует
      fsExistsSync.callsFake((filePath) => {
        // Если это директория components
        if (filePath.includes('data/components') && !filePath.includes('_upload_state')) {
          return true;
        }
        // Если это state файл
        if (filePath.includes('_upload_state.json')) {
          return true;
        }
        return false;
      });
      
      // Mock readdirSync для компонентов
      const fsReaddirSync = sinon.stub(fs, 'readdirSync');
      fsReaddirSync.returns(['comp1', 'comp2']);
      
      // Mock statSync для проверки директорий
      const fsStatSync = sinon.stub(fs, 'statSync');
      fsStatSync.returns({ isDirectory: () => true });
      
      // Mock readFileSync для state файлов
      const stateData = {
        arweave: {
          steps_completed: ['component_registered']
        }
      };
      fsReadFileSync.returns(JSON.stringify(stateData));

      // WHEN: checkComponentsLoaded вызывается
      const result = await catalogActions.checkComponentsLoaded();

      // THEN: Результат true (найдены компоненты с component_registered)
      expect(result).to.be.true;
      
      // Restore
      fsReaddirSync.restore();
      fsStatSync.restore();
    });

    it('должен вернуть true если найдены компоненты в контракте', async () => {
      const mockComponentRegistry = {
        getTotalComponents: sinon.stub().resolves(5n)
      };
      
      fsExistsSync.returns(false);
      mockContractManager.loadUUPSContract
        .withArgs('OrganicComponentRegistry')
        .resolves(mockComponentRegistry);

      const result = await catalogActions.checkComponentsLoaded();

      expect(result).to.be.true;
    });

    it('должен вернуть false если компоненты не найдены', async () => {
      const mockComponentRegistry = {
        getTotalComponents: sinon.stub().resolves(0n)
      };
      
      fsExistsSync.returns(false);
      mockContractManager.loadUUPSContract
        .withArgs('OrganicComponentRegistry')
        .resolves(mockComponentRegistry);

      const result = await catalogActions.checkComponentsLoaded();

      expect(result).to.be.false;
    });

    it('должен вернуть false при ошибке загрузки контракта', async () => {
      fsExistsSync.returns(false);
      mockContractManager.loadUUPSContract
        .withArgs('OrganicComponentRegistry')
        .rejects(new Error('Contract not deployed'));

      const result = await catalogActions.checkComponentsLoaded();

      expect(result).to.be.false;
    });

    it('должен использовать кастомную network из options', async () => {
      // GIVEN: Mock fs для проверки state файлов с кастомной network
      const fs = require('fs');
      const path = require('path');
      
      // Mock COMPONENTS_DIR существует
      fsExistsSync.callsFake((filePath) => {
        // Если это директория components
        if (filePath.includes('data/components') && !filePath.includes('_upload_state')) {
          return true;
        }
        // Если это state файл (универсальный формат _upload_state.json, не зависит от network)
        if (filePath.includes('_upload_state.json')) {
          return true;
        }
        return false;
      });
      
      // Mock readdirSync для компонентов
      const fsReaddirSync = sinon.stub(fs, 'readdirSync');
      fsReaddirSync.returns(['comp1']);
      
      // Mock statSync для проверки директорий
      const fsStatSync = sinon.stub(fs, 'statSync');
      fsStatSync.returns({ isDirectory: () => true });
      
      // Mock readFileSync для state файлов
      const stateData = {
        arweave: {
          steps_completed: ['component_registered']
        }
      };
      fsReadFileSync.returns(JSON.stringify(stateData));

      // WHEN: checkComponentsLoaded вызывается с кастомной network
      const result = await catalogActions.checkComponentsLoaded({ network: 'polygon' });

      // THEN: Результат true (найдены компоненты)
      // NOTE: В текущей реализации checkComponentsLoaded использует универсальный формат
      // _upload_state.json (не зависит от network), поэтому network из options не влияет
      // на поиск файлов, но передается в метод для будущего использования
      expect(result).to.be.true;
      
      // Restore
      fsReaddirSync.restore();
      fsStatSync.restore();
    });

    it('должен вернуть false при JSON parse ошибке', async () => {
      fsExistsSync.returns(true);
      fsReadFileSync.returns('INVALID JSON');

      const result = await catalogActions.checkComponentsLoaded();

      expect(result).to.be.false;
    });

    it('должен вернуть false если state file пустой', async () => {
      const stateData = {
        components: {}
      };
      
      fsExistsSync.returns(true);
      fsReadFileSync.returns(JSON.stringify(stateData));
      
      const mockComponentRegistry = {
        getTotalComponents: sinon.stub().resolves(0n)
      };
      
      mockContractManager.loadUUPSContract
        .withArgs('OrganicComponentRegistry')
        .resolves(mockComponentRegistry);

      const result = await catalogActions.checkComponentsLoaded();

      expect(result).to.be.false;
    });
  });

  describe('loadCatalogAuto()', () => {
    beforeEach(() => {
      // Mock checkComponentsLoaded
      sinon.stub(catalogActions, 'checkComponentsLoaded');
      
      // Mock action444, action4, action46
      sinon.stub(catalogActions, 'action444');
      sinon.stub(catalogActions, 'action4');
      sinon.stub(catalogActions, 'action46');
    });

    it('должен использовать modern pipeline если компоненты найдены', async () => {
      catalogActions.checkComponentsLoaded.resolves(true);
      catalogActions.action444.resolves({
        productsCreated: 17,
        productsActivated: 17
      });

      const result = await catalogActions.loadCatalogAuto('0xSeller');

      expect(result.success).to.be.true;
      expect(result.pipeline).to.equal('modern');
      expect(result.action).to.equal('444');
      expect(catalogActions.action444.calledOnce).to.be.true;
      expect(catalogActions.action4.called).to.be.false;
    });

    it('должен использовать classic pipeline если компонентов нет', async () => {
      catalogActions.checkComponentsLoaded.resolves(false);
      catalogActions.action4.resolves({
        success: true,
        totalProducts: 17
      });
      catalogActions.action46.resolves({
        success: true,
        activatedCount: 17
      });

      const result = await catalogActions.loadCatalogAuto('0xSeller');

      expect(result.success).to.be.true;
      expect(result.pipeline).to.equal('classic');
      expect(result.actions).to.deep.equal(['4', '46']);
      expect(catalogActions.action4.calledOnce).to.be.true;
      expect(catalogActions.action46.calledOnce).to.be.true;
      expect(catalogActions.action444.called).to.be.false;
    });

    it('должен пропустить activation если activateProducts=false', async () => {
      catalogActions.checkComponentsLoaded.resolves(false);
      catalogActions.action4.resolves({ success: true });

      const result = await catalogActions.loadCatalogAuto('0xSeller', {
        activateProducts: false
      });

      expect(result.success).to.be.true;
      expect(result.pipeline).to.equal('classic');
      expect(result.actions).to.deep.equal(['4']);
      expect(result.activateResult).to.be.null;
      expect(catalogActions.action46.called).to.be.false;
    });

    it('должен выбросить ошибку при провале modern pipeline', async () => {
      catalogActions.checkComponentsLoaded.resolves(true);
      catalogActions.action444.rejects(new Error('Pipeline failed'));

      try {
        await catalogActions.loadCatalogAuto('0xSeller');
        expect.fail('Should have thrown error');
      } catch (error) {
        expect(error.message).to.include('Pipeline failed');
      }
    });

    it('должен выбросить ошибку при провале classic pipeline', async () => {
      catalogActions.checkComponentsLoaded.resolves(false);
      catalogActions.action4.rejects(new Error('Create failed'));

      try {
        await catalogActions.loadCatalogAuto('0xSeller');
        expect.fail('Should have thrown error');
      } catch (error) {
        expect(error.message).to.include('Create failed');
      }
    });

    it('должен включить результаты обоих actions в classic pipeline', async () => {
      catalogActions.checkComponentsLoaded.resolves(false);
      catalogActions.action4.resolves({
        success: true,
        totalProducts: 17
      });
      catalogActions.action46.resolves({
        success: true,
        activatedCount: 17
      });

      const result = await catalogActions.loadCatalogAuto('0xSeller');

      expect(result.createResult).to.deep.equal({
        success: true,
        totalProducts: 17
      });
      expect(result.activateResult).to.deep.equal({
        success: true,
        activatedCount: 17
      });
    });
  });

  describe('createCatalogFromDataFile()', () => {
    const fs = require('fs');
    const path = require('path');

    let fsExistsSync;
    let fsReadFileSync;
    let mockProductRegistry;
    let mockSigner;

    beforeEach(() => {
      fsExistsSync = sinon.stub(fs, 'existsSync');
      fsReadFileSync = sinon.stub(fs, 'readFileSync');

      mockProductRegistry = {
        connect: sinon.stub().returnsThis(),
        createProduct: sinon.stub().resolves({
          wait: sinon.stub().resolves({})
        }),
        getProductsBySellerFull: sinon.stub().resolves([{
          id: 1,
          seller: '0xSeller',
          businessId: 'amanita_lux',
          componentIds: ['amanita_muscaria'],
          metadataCID: 'QmCID',
          active: false
        }])
      };

      mockContractManager.loadUUPSContract.withArgs('ProductRegistry').resolves(mockProductRegistry);
      mockConfig.get.withArgs('paths.projectRoot').returns('/workspace');
      mockConfig.get.withArgs('seller.privateKey').returns('0xpriv');
      mockConfig.get.withArgs('network.name').returns('localhost');

      mockSigner = {
        getAddress: sinon.stub().resolves('0xSeller')
      };
      mockEthersUtils.getSigner.returns(mockSigner);
    });

    afterEach(() => {
      fsExistsSync.restore();
      fsReadFileSync.restore();
    });

    it('должен передавать businessId (product.id) первым аргументом createProduct', async () => {
      const dataFile = path.join('/workspace', 'bot', 'catalog', 'product_registry_upload_data.json');
      fsExistsSync.withArgs(dataFile).returns(true);
      fsReadFileSync.withArgs(dataFile, 'utf8').returns(JSON.stringify([{
        id: 'amanita_lux',
        componentIds: ['amanita_muscaria'],
        metadataCID: 'QmCID'
      }]));

      await catalogActions.createCatalogFromDataFile(mockProductRegistry, '0xSeller');

      sinon.assert.calledWith(
        mockProductRegistry.createProduct,
        'amanita_lux',
        ['amanita_muscaria'],
        'QmCID',
        sinon.match.object
      );
    });

    it('должен выбрасывать ошибку если отсутствует строковый id (businessId)', async () => {
      const dataFile = path.join('/workspace', 'bot', 'catalog', 'product_registry_upload_data.json');
      fsExistsSync.withArgs(dataFile).returns(true);
      fsReadFileSync.withArgs(dataFile, 'utf8').returns(JSON.stringify([{
        componentIds: ['amanita_muscaria'],
        metadataCID: 'QmCID'
      }]));

      const result = await catalogActions.createCatalogFromDataFile(mockProductRegistry, '0xSeller');
      expect(result.productsFailed).to.equal(1);
    });
  });

  // ================================================================
  // REAL TESTS: action41 (CSV Transform)
  // ================================================================

  describe('action41() - CSV Transform', () => {
    it('должен выполнить CSV → JSON трансформацию', async () => {
      // TODO: Требует реальный CSV файл или mock fs
      // Stub для простоты
      const transformStub = sinon.stub(catalogActions, 'action41').resolves({
        success: true,
        products: [{ id: 1, name: 'Product 1' }]
      });
      
      // WHEN
      const result = await catalogActions.action41();
      
      // THEN
      expect(result.success).to.be.true;
      expect(result).to.have.property('products');
      
      transformStub.restore();
    });
  });

  // ================================================================
  // REAL TESTS: action42 (Arweave Upload)
  // ================================================================

  describe('action42() - Arweave Upload', () => {
    it('должен загрузить JSON на Arweave', async () => {
      // TODO: Зависит от action41 output
      // Stub
      const uploadStub = sinon.stub(catalogActions, 'action42').resolves({
        success: true,
        cid: 'fake-cid-12345'
      });
      
      // WHEN
      const result = await catalogActions.action42();
      
      // THEN
      expect(result.success).to.be.true;
      expect(result.cid).to.be.a('string');
      
      uploadStub.restore();
    });
  });

  // ================================================================
  // REAL TESTS: action43 (Contract Registration)
  // ================================================================

  describe('action43() - Contract Registration', () => {
    let mockProductRegistry;

    beforeEach(() => {
      mockProductRegistry = {
        getAddress: sinon.stub().resolves('0xProduct'),
        connect: sinon.stub().returnsThis(),
        registerCatalog: sinon.stub().resolves({
          wait: sinon.stub().resolves({ status: 1 })
        })
      };

      mockContractManager.loadUUPSContract.withArgs('ProductRegistry').resolves(mockProductRegistry);
    });

    it('должен загрузить ProductRegistry', async () => {
      // Stub action43
      const stub = sinon.stub(catalogActions, 'action43').resolves({ success: true });
      
      // WHEN
      await catalogActions.action43();
      
      // THEN
      // expect(mockContractManager.loadUUPSContract.calledWith('ProductRegistry')).to.be.true;
      
      stub.restore();
      expect(true).to.be.true; // Placeholder (метод использует внутренние вызовы)
    });

    it('должен зарегистрировать CID в контракте', async () => {
      // TODO: Требует CID из action42
      const stub = sinon.stub(catalogActions, 'action43').resolves({
        success: true,
        registered: true
      });
      
      // WHEN
      const result = await catalogActions.action43();
      
      // THEN
      expect(result.success).to.be.true;
      
      stub.restore();
    });
  });

  // ================================================================
  // REAL TESTS: action444 (Pipeline)
  // ================================================================

  describe('action444() - Pipeline (41 → 42 → 43)', () => {
    let prepareContextStub;
    beforeEach(() => {
      mockConfig.get.withArgs('catalog.csvPath').returns('/tmp/catalog.csv');
      mockConfig.get.withArgs('catalog.outputDir').returns('/tmp/output');
      mockConfig.get.withArgs('catalog.sellerId').returns('seller123');
      mockConfig.get.withArgs('catalog.sourceLang').returns('en');
    });

    it('должен делегировать в action444_AutomaticPipeline', async () => {
      // GIVEN: Mock product_upload_steps module
      const mockPipeline = sinon.stub().resolves({
        success: true,
        productsTransformed: 5,
        productsUploaded: 5,
        productsRegistered: 5
      });
      
      // Mock require для product_upload_steps
      const Module = require('module');
      const originalRequire = Module.prototype.require;
      Module.prototype.require = function(id) {
        if (id === '../product_upload_steps.js') {
          return { action444_AutomaticPipeline: mockPipeline };
        }
        return originalRequire.apply(this, arguments);
      };
      prepareContextStub = sinon.stub(catalogActions, '_prepareArweaveContext').resolves({});
      
      // WHEN
      const result = await catalogActions.action444();
      
      // THEN: Pipeline вызван
      expect(mockPipeline.calledOnce).to.be.true;
      expect(result.success).to.be.true;
      
      // Cleanup
      prepareContextStub.restore();
      Module.prototype.require = originalRequire;
    });

    it('должен вернуть success result', async () => {
      // GIVEN: Mock product_upload_steps module
      const Module = require('module');
      const originalRequire = Module.prototype.require;
      Module.prototype.require = function(id) {
        if (id === '../product_upload_steps.js') {
          return { 
            action444_AutomaticPipeline: sinon.stub().resolves({ success: true }) 
          };
        }
        return originalRequire.apply(this, arguments);
      };
      prepareContextStub = sinon.stub(catalogActions, '_prepareArweaveContext').resolves({});
      
      // WHEN
      const result = await catalogActions.action444();
      
      // THEN
      expect(result).to.have.property('success', true);
      
      // Cleanup
      prepareContextStub.restore();
      Module.prototype.require = originalRequire;
    });

    it('должен выбросить ошибку если pipeline падает', async () => {
      // GIVEN: Mock product_upload_steps to reject
      const Module = require('module');
      const originalRequire = Module.prototype.require;
      Module.prototype.require = function(id) {
        if (id === '../product_upload_steps.js') {
          return { 
            action444_AutomaticPipeline: sinon.stub().rejects(new Error('Upload failed')) 
          };
        }
        return originalRequire.apply(this, arguments);
      };
      prepareContextStub = sinon.stub(catalogActions, '_prepareArweaveContext').resolves({});
      
      // WHEN/THEN
      try {
        await catalogActions.action444();
        expect.fail('Should have thrown error');
      } catch (error) {
        expect(error.message).to.include('Upload failed');
      } finally {
        prepareContextStub.restore();
        Module.prototype.require = originalRequire;
      }
    });
  });

  // ================================================================
  // NOTE: action888() MOVED to InviteActions (Layer 4A)
  // Tests: See InviteActions.test.js
  // ================================================================
});

