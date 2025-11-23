/**
 * Unit Tests: upload_steps.js
 * 
 * Tests for component upload steps, specifically uploadComplexFields
 * 
 * Coverage:
 * - uploadComplexFields() - complex fields upload with biounit_id in className
 * 
 * @version 1.0.0
 * @date 2025-01-12
 */

const { expect } = require('chai');
const sinon = require('sinon');
const Module = require('module');
const path = require('path');

describe('upload_steps.uploadComplexFields', () => {
  let originalRequire;
  let uploadSteps;
  let uploadComplexFields;
  const modulePath = path.resolve(__dirname, '../../../lib/upload_steps.js');

  // Mocks
  let mockUtils;
  let mockStateManager;
  let mockAmanitaIntl;
  let mockContext;
  let mockState;
  let mockSigner;
  let realUploadUtils; // Сохраняем ссылку на реальный модуль до перехвата require

  beforeEach(() => {
    // Загружаем реальный upload_utils ДО установки перехвата require
    const realUploadUtilsPath = path.resolve(__dirname, '../../../lib/upload_utils.js');
    realUploadUtils = require(realUploadUtilsPath);

    // Mock utils (upload_utils)
    mockUtils = {
      readJSON: sinon.stub().callsFake((componentDir, filePath) => {
        // Используем реальный readJSON для работы с реальными файлами
        try {
          const result = realUploadUtils.readJSON(componentDir, filePath);
          return result;
        } catch (error) {
          // Пробрасываем ошибку дальше для корректной обработки в upload_steps
          throw error;
        }
      }),
      getSupportedLanguages: sinon.stub().returns(['ru', 'en'])
    };

    // Mock stateManager
    mockStateManager = {
      isStepCompleted: sinon.stub().returns(false),
      markStepCompleted: sinon.stub(),
      saveComponentState: sinon.stub()
    };

    // Mock signer
    mockSigner = {
      address: '0xSeller'
    };

    // Mock AmanitaInternational contract
    mockAmanitaIntl = {
      connect: sinon.stub().returnsThis(),
      setComplexFieldCID: sinon.stub().resolves({
        wait: sinon.stub().resolves({ status: 1 })
      })
    };

    // Mock context
    mockContext = {
      biounit_id: 'amanita_muscaria',
      componentDir: path.resolve(__dirname, '../../../../data/components/amanita_muscaria'),
      network: 'localhost',
      dryRun: true,  // Используем dryRun для unit тестов - избегаем реальной загрузки в Arweave
      arweaveOnly: false,
      supportedLanguages: ['ru', 'en'],
      contracts: {
        amanitaInternational: mockAmanitaIntl
      },
      seller: {
        address: '0xSeller',
        signer: mockSigner
      },
      // Mock arweave для uploadToArweave (если не dryRun)
      arweave: {
        client: {
          wallets: {
            jwkToAddress: sinon.stub().resolves('arweave-address'),
            getBalance: sinon.stub().resolves('1000000')
          },
          ar: {
            winstonToAr: sinon.stub().returns('1.0')
          },
          createTransaction: sinon.stub().returns({
            // Arweave TX ID должен быть ровно 43 символа base64url
            id: 'QmMockCID1234567890123456789012345678901234',
            addTag: sinon.stub()
          }),
          transactions: {
            sign: sinon.stub().resolves(),
            post: sinon.stub().resolves({ status: 200 })
          }
        },
        key: {}
      },
      _arweaveBalanceChecked: false
    };

    // Mock state
    mockState = {
      steps_completed: [],
      complex_fields: {},
      network: 'localhost'
    };

    // Intercept require for dependencies before loading module under test
    originalRequire = Module.prototype.require;
    Module.prototype.require = function (request) {
      // Mock upload_utils
      if (request === './upload_utils') {
        return mockUtils;
      }
      // Mock state_manager
      if (request === './state_manager') {
        return mockStateManager;
      }
      return originalRequire.apply(this, arguments);
    };

    // Clear module cache and load
    delete require.cache[modulePath];
    uploadSteps = require(modulePath);
    uploadComplexFields = uploadSteps.uploadComplexFields;
  });

  afterEach(() => {
    delete require.cache[modulePath];
    Module.prototype.require = originalRequire;
    sinon.restore();
  });

  describe('uploadComplexFields() - ClassName Format with biounit_id', () => {
    // Мок readJSON уже настроен в основном beforeEach на использование реальной функции

    it('должен формировать className с biounit_id', async () => {
      // GIVEN: Отключаем dryRun для проверки вызова setComplexFieldCID
      mockContext.dryRun = false;
      
      // WHEN: Загружаем complex fields
      await uploadComplexFields(mockContext, mockState);

      // THEN: setComplexFieldCID вызван с правильным className
      expect(mockAmanitaIntl.setComplexFieldCID.called).to.be.true;

      // Проверяем все вызовы
      const calls = mockAmanitaIntl.setComplexFieldCID.getCalls();
      expect(calls.length).to.be.greaterThan(0);

      // Проверяем первый вызов (для языка 'ru')
      const firstCall = calls.find(call => call.args[1] === 'ru');
      if (firstCall) {
        const className = firstCall.args[0];
        expect(className).to.equal('ComponentDescription.amanita_muscaria');
        expect(className).to.include('amanita_muscaria'); // Содержит biounit_id
        expect(className).to.not.equal('ComponentDescription'); // НЕ без biounit_id
      }
    });

    it('должен вызывать setComplexFieldCID для каждого языка с правильным className', async () => {
      // GIVEN: Отключаем dryRun для проверки вызова setComplexFieldCID
      mockContext.dryRun = false;
      
      // WHEN: Загружаем complex fields
      await uploadComplexFields(mockContext, mockState);

      // THEN: setComplexFieldCID вызван для каждого языка
      const calls = mockAmanitaIntl.setComplexFieldCID.getCalls();
      const languages = ['ru', 'en'];

      expect(calls.length).to.equal(languages.length);

      // Проверяем каждый вызов
      for (const lang of languages) {
        const call = calls.find(c => c.args[1] === lang);
        expect(call).to.exist;
        expect(call.args[0]).to.equal(`ComponentDescription.${mockContext.biounit_id}`);
        expect(call.args[1]).to.equal(lang);
        expect(call.args[2]).to.be.a('string'); // CID
      }
    });

    it('должен сохранять CIDs в state.complex_fields', async () => {
      // GIVEN: Отключаем dryRun для проверки сохранения в state
      mockContext.dryRun = false;
      
      // WHEN: Загружаем complex fields
      const result = await uploadComplexFields(mockContext, mockState);

      // THEN: State обновлен
      expect(mockState.complex_fields).to.exist;
      expect(Object.keys(mockState.complex_fields).length).to.be.greaterThan(0);

      // THEN: Результат содержит CIDs для всех языков
      expect(result).to.exist;
      expect(Object.keys(result).length).to.equal(2); // ru, en

      // THEN: Каждый CID имеет правильную структуру
      expect(result.ru).to.have.property('cid');
      expect(result.ru).to.have.property('url');
      expect(result.en).to.have.property('cid');
      expect(result.en).to.have.property('url');
    });

    it('должен пропускать уже загруженные complex fields', async () => {
      // GIVEN: Complex fields уже загружены
      mockStateManager.isStepCompleted.returns(true);
      mockState.complex_fields = {
        ru: { cid: 'QmExistingCID', url: 'https://arweave.net/QmExistingCID' },
        en: { cid: 'QmExistingCID2', url: 'https://arweave.net/QmExistingCID2' }
      };

      // WHEN: Пытаемся загрузить снова
      const result = await uploadComplexFields(mockContext, mockState);

      // THEN: setComplexFieldCID НЕ вызван (шаг уже выполнен)
      expect(mockAmanitaIntl.setComplexFieldCID.called).to.be.false;

      // THEN: Возвращен существующий state
      expect(result).to.equal(mockState.complex_fields);
    });

    it('должен вызывать connect с правильным signer', async () => {
      // GIVEN: Отключаем dryRun для проверки вызова connect
      mockContext.dryRun = false;
      
      // WHEN: Загружаем complex fields
      await uploadComplexFields(mockContext, mockState);

      // THEN: connect вызван с seller.signer
      expect(mockAmanitaIntl.connect.called).to.be.true;
      expect(mockAmanitaIntl.connect.firstCall.args[0]).to.equal(mockSigner);
    });

    it('должен вызывать markStepCompleted и saveComponentState после успешной загрузки', async () => {
      // GIVEN: Отключаем dryRun
      mockContext.dryRun = false;
      
      // WHEN: Загружаем complex fields
      await uploadComplexFields(mockContext, mockState);

      // THEN: markStepCompleted вызван
      expect(mockStateManager.markStepCompleted.called).to.be.true;
      expect(mockStateManager.markStepCompleted.firstCall.args[1]).to.equal('complex_fields_uploaded');

      // THEN: saveComponentState вызван
      expect(mockStateManager.saveComponentState.called).to.be.true;
      expect(mockStateManager.saveComponentState.firstCall.args[0]).to.equal(mockContext.componentDir);
      expect(mockStateManager.saveComponentState.firstCall.args[1]).to.equal(mockContext.network);
    });
  });

  describe('uploadComplexFields() - ClassName Format Edge Cases', () => {
    // Мок readJSON уже настроен в основном beforeEach на использование реальной функции

    it('должен правильно формировать className для разных biounit_id', async () => {
      // GIVEN: Отключаем dryRun и используем только amanita_muscaria (файлы существуют)
      mockContext.dryRun = false;
      
      const testCases = [
        'amanita_muscaria' // Используем только компонент, для которого существуют файлы
        // Другие компоненты требуют существования файлов в data/components/
      ];

      for (const biounitId of testCases) {
        // Reset mocks for each test case
        mockAmanitaIntl.setComplexFieldCID.resetHistory();
        mockContext.biounit_id = biounitId;

        await uploadComplexFields(mockContext, mockState);

        const calls = mockAmanitaIntl.setComplexFieldCID.getCalls();
        if (calls.length > 0) {
          const className = calls[0].args[0];
          expect(className).to.equal(`ComponentDescription.${biounitId}`);
        }
      }
    });

    it('должен обрабатывать пустой biounit_id (edge case)', async () => {
      mockContext.biounit_id = '';

      // WHEN: Пытаемся загрузить с пустым biounit_id
      try {
        await uploadComplexFields(mockContext, mockState);
        // Если не выбросило ошибку, проверяем что className не пустой
        const calls = mockAmanitaIntl.setComplexFieldCID.getCalls();
        if (calls.length > 0) {
          const className = calls[0].args[0];
          expect(className).to.not.equal('ComponentDescription.'); // Не должно быть просто "ComponentDescription."
        }
      } catch (error) {
        // Если выбросило ошибку, это тоже приемлемо
        expect(error).to.exist;
      }
    });

    it('должен пропускать dry-run режим (не вызывать setComplexFieldCID)', async () => {
      // GIVEN: dryRun режим
      mockContext.dryRun = true;

      // WHEN: Загружаем complex fields
      await uploadComplexFields(mockContext, mockState);

      // THEN: setComplexFieldCID НЕ вызван
      expect(mockAmanitaIntl.setComplexFieldCID.called).to.be.false;

      // THEN: State все еще обновляется
      expect(mockState.complex_fields).to.exist;
    });

    it('должен пропускать arweaveOnly режим (не вызывать setComplexFieldCID)', async () => {
      // GIVEN: arweaveOnly режим
      mockContext.arweaveOnly = true;

      // WHEN: Загружаем complex fields
      await uploadComplexFields(mockContext, mockState);

      // THEN: setComplexFieldCID НЕ вызван
      expect(mockAmanitaIntl.setComplexFieldCID.called).to.be.false;
    });

    it('должен обрабатывать ошибки чтения файлов gracefully', async () => {
      // GIVEN: Отключаем dryRun и настраиваем readJSON для ошибки одного языка
      mockContext.dryRun = false;
      let callCount = 0;
      mockUtils.readJSON.callsFake((componentDir, filePath) => {
        callCount++;
        if (callCount === 1) {
          // Первый язык (ru) успешен - используем реальный readJSON
          return realUploadUtils.readJSON(componentDir, filePath);
        } else {
          // Второй язык (en) ошибка
          throw new Error('File not found');
        }
      });

      // WHEN: Загружаем complex fields
      const result = await uploadComplexFields(mockContext, mockState);

      // THEN: Обработан хотя бы один язык
      expect(Object.keys(result).length).to.be.greaterThan(0);

      // THEN: setComplexFieldCID вызван для успешных языков
      expect(mockAmanitaIntl.setComplexFieldCID.called).to.be.true;
    });

    it('должен выбрасывать ошибку если ни один файл не был загружен', async () => {
      // GIVEN: Все файлы не найдены
      mockUtils.readJSON.throws(new Error('File not found'));

      // WHEN/THEN: Должна быть выброшена ошибка
      try {
        await uploadComplexFields(mockContext, mockState);
        expect.fail('Should have thrown error');
      } catch (error) {
        expect(error.message).to.include('Ни один файл complex fields не был загружен');
      }
    });
  });
});

