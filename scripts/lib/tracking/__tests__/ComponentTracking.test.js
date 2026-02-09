/**
 * Unit Tests: ComponentTracking
 * 
 * Tests for component tracking module
 * 
 * Coverage:
 * - Constructor and helper methods
 * - Field update methods
 * - History management
 * - Source JSON cleaning
 * - High-level update methods
 * 
 * @version 1.0.0
 * @date 2025-01-XX
 */

const { expect } = require('chai');
const sinon = require('sinon');
const fs = require('fs');
const path = require('path');
const ComponentTracking = require('../ComponentTracking');

describe('ComponentTracking', () => {
  let tracking;
  const TEST_ADDRESS = '0x1234567890abcdef1234567890abcdef12345678';
  const ZERO_ADDRESS = '0x0000000000000000000000000000000000000000';
  const REAL_ADDRESS = '0x70997970C51812dc3A010C7d01b50e0d17dc79C8';

  beforeEach(() => {
    tracking = new ComponentTracking();
  });

  // ====================================================================
  // Тесты конструктора
  // ====================================================================

  describe('constructor()', () => {
    it('должен создать экземпляр с дефолтными значениями', () => {
      const instance = new ComponentTracking();
      expect(instance.testAddress).to.equal(TEST_ADDRESS);
      expect(instance.zeroAddress).to.equal(ZERO_ADDRESS);
    });

    it('должен создать экземпляр с кастомной конфигурацией', () => {
      const customTestAddress = '0xCustomTestAddress1234567890123456789012345678';
      const customZeroAddress = '0xCustomZeroAddress0000000000000000000000000000';
      
      const instance = new ComponentTracking({
        testAddress: customTestAddress,
        zeroAddress: customZeroAddress
      });
      
      expect(instance.testAddress).to.equal(customTestAddress);
      expect(instance.zeroAddress).to.equal(customZeroAddress);
    });
  });

  // ====================================================================
  // Тесты isTestAddress()
  // ====================================================================

  describe('isTestAddress()', () => {
    it('должен возвращать true для тестового адреса', () => {
      expect(tracking.isTestAddress(TEST_ADDRESS)).to.be.true;
    });

    it('должен возвращать true для нулевого адреса', () => {
      expect(tracking.isTestAddress(ZERO_ADDRESS)).to.be.true;
    });

    it('должен возвращать true для null', () => {
      expect(tracking.isTestAddress(null)).to.be.true;
    });

    it('должен возвращать true для undefined', () => {
      expect(tracking.isTestAddress(undefined)).to.be.true;
    });

    it('должен возвращать false для реального адреса', () => {
      expect(tracking.isTestAddress(REAL_ADDRESS)).to.be.false;
    });
  });

  // ====================================================================
  // Тесты hasContributor()
  // ====================================================================

  describe('hasContributor()', () => {
    it('должен возвращать false если contributors отсутствует', () => {
      const data = {};
      expect(tracking.hasContributor(data, REAL_ADDRESS)).to.be.false;
    });

    it('должен возвращать false если contributors пустой', () => {
      const data = { contributors: [] };
      expect(tracking.hasContributor(data, REAL_ADDRESS)).to.be.false;
    });

    it('должен возвращать true если адрес есть в contributors', () => {
      const data = {
        contributors: [
          { address: REAL_ADDRESS, role: 'creator' }
        ]
      };
      expect(tracking.hasContributor(data, REAL_ADDRESS)).to.be.true;
    });

    it('должен игнорировать регистр при сравнении адресов', () => {
      const data = {
        contributors: [
          { address: REAL_ADDRESS.toLowerCase(), role: 'creator' }
        ]
      };
      expect(tracking.hasContributor(data, REAL_ADDRESS.toUpperCase())).to.be.true;
    });
  });

  // ====================================================================
  // Тесты updateOwnership()
  // ====================================================================

  describe('updateOwnership()', () => {
    it('должен обновить created_by если тестовый', () => {
      const data = { created_by: TEST_ADDRESS };
      const result = tracking.updateOwnership(data, REAL_ADDRESS);
      expect(result.created_by).to.equal(REAL_ADDRESS);
    });

    it('должен обновить created_by если пустой', () => {
      const data = { created_by: null };
      const result = tracking.updateOwnership(data, REAL_ADDRESS);
      expect(result.created_by).to.equal(REAL_ADDRESS);
    });

    it('не должен обновлять created_by если реальный', () => {
      const data = { created_by: REAL_ADDRESS };
      const result = tracking.updateOwnership(data, '0xAnotherAddress');
      expect(result.created_by).to.equal(REAL_ADDRESS);
    });

    it('должен обновить contributors если только тестовые адреса', () => {
      const data = {
        contributors: [
          { address: TEST_ADDRESS, role: 'creator' }
        ]
      };
      const result = tracking.updateOwnership(data, REAL_ADDRESS);
      expect(result.contributors).to.have.length(1);
      expect(result.contributors[0].address).to.equal(REAL_ADDRESS);
      expect(result.contributors[0].role).to.equal('creator');
    });

    it('должен добавить контрибьютора если его нет', () => {
      const data = {
        contributors: [
          { address: '0xAnotherRealAddress', role: 'creator' }
        ]
      };
      const result = tracking.updateOwnership(data, REAL_ADDRESS);
      expect(result.contributors).to.have.length(2);
      expect(result.contributors.some(c => c.address === REAL_ADDRESS)).to.be.true;
    });

    it('не должен дублировать контрибьютора если он уже есть', () => {
      const data = {
        contributors: [
          { address: REAL_ADDRESS, role: 'creator' }
        ]
      };
      const result = tracking.updateOwnership(data, REAL_ADDRESS);
      expect(result.contributors).to.have.length(1);
    });
  });

  // ====================================================================
  // Тесты updateValidator()
  // ====================================================================

  describe('updateValidator()', () => {
    it('должен обновить validator в metadata.validation', () => {
      const data = {
        metadata: {
          validation: {
            validator: TEST_ADDRESS
          }
        }
      };
      const result = tracking.updateValidator(data, REAL_ADDRESS);
      expect(result.metadata.validation.validator).to.equal(REAL_ADDRESS);
      expect(result.metadata.validation.last_validated).to.be.a('string');
    });

    it('должен создать metadata.validation если отсутствует', () => {
      const data = { metadata: {} };
      const result = tracking.updateValidator(data, REAL_ADDRESS);
      expect(result.metadata.validation).to.exist;
      expect(result.metadata.validation.validator).to.equal(REAL_ADDRESS);
    });

    it('должен создать metadata если отсутствует', () => {
      const data = {};
      const result = tracking.updateValidator(data, REAL_ADDRESS);
      expect(result.metadata).to.exist;
      expect(result.metadata.validation.validator).to.equal(REAL_ADDRESS);
    });
  });

  // ====================================================================
  // Тесты updateModeration()
  // ====================================================================

  describe('updateModeration()', () => {
    it('должен обновить moderation.moderated_by', () => {
      const data = {
        moderation: {
          status: 'pending'
        }
      };
      const result = tracking.updateModeration(data, REAL_ADDRESS, 'approved');
      expect(result.moderation.moderated_by).to.equal(REAL_ADDRESS);
      expect(result.moderation.moderated_at).to.be.a('string');
      expect(result.moderation.status).to.equal('approved');
    });

    it('должен создать moderation если отсутствует', () => {
      const data = {};
      const result = tracking.updateModeration(data, REAL_ADDRESS, 'approved');
      expect(result.moderation).to.exist;
      expect(result.moderation.moderated_by).to.equal(REAL_ADDRESS);
    });
  });

  // ====================================================================
  // Тесты updateSharing()
  // ====================================================================

  describe('updateSharing()', () => {
    it('должен обновить sharing.shared_by', () => {
      const data = {
        sharing: {
          is_shared: true
        }
      };
      const result = tracking.updateSharing(data, REAL_ADDRESS);
      expect(result.sharing.shared_by).to.equal(REAL_ADDRESS);
      expect(result.sharing.shared_at).to.be.a('string');
    });

    it('должен создать sharing если отсутствует', () => {
      const data = {};
      const result = tracking.updateSharing(data, REAL_ADDRESS);
      expect(result.sharing).to.exist;
      expect(result.sharing.shared_by).to.equal(REAL_ADDRESS);
    });

    it('не должен перезаписывать shared_at если уже установлен', () => {
      const existingDate = '2025-01-01T00:00:00.000Z';
      const data = {
        sharing: {
          shared_at: existingDate
        }
      };
      const result = tracking.updateSharing(data, REAL_ADDRESS);
      expect(result.sharing.shared_at).to.equal(existingDate);
    });
  });

  // ====================================================================
  // Тесты addContributor()
  // ====================================================================

  describe('addContributor()', () => {
    it('должен добавить контрибьютора если contributors пустой', () => {
      const data = {};
      const result = tracking.addContributor(data, REAL_ADDRESS, 'editor');
      expect(result.contributors).to.have.length(1);
      expect(result.contributors[0].address).to.equal(REAL_ADDRESS);
      expect(result.contributors[0].role).to.equal('editor');
    });

    it('не должен дублировать контрибьютора если он уже есть', () => {
      const data = {
        contributors: [
          { address: REAL_ADDRESS, role: 'creator' }
        ]
      };
      const result = tracking.addContributor(data, REAL_ADDRESS, 'editor');
      expect(result.contributors).to.have.length(1);
    });

    it('должен использовать дефолтную роль если не указана', () => {
      const data = {};
      const result = tracking.addContributor(data, REAL_ADDRESS);
      expect(result.contributors[0].role).to.equal('contributor');
    });
  });

  // ====================================================================
  // Тесты addHistoryEntry()
  // ====================================================================

  describe('addHistoryEntry()', () => {
    it('должен добавить запись в пустой change_history', () => {
      const data = {};
      const entry = {
        timestamp: '2025-01-01T00:00:00.000Z',
        address: REAL_ADDRESS,
        action: 'create',
        changes: ['initial_creation'],
        transaction_hash: '0xHash123',
        block_number: 123
      };
      const result = tracking.addHistoryEntry(data, entry);
      expect(result.change_history).to.have.length(1);
      expect(result.change_history[0]).to.deep.include(entry);
    });

    it('должен добавить запись в существующий change_history', () => {
      const data = {
        change_history: [
          {
            timestamp: '2025-01-01T00:00:00.000Z',
            address: REAL_ADDRESS,
            action: 'create'
          }
        ]
      };
      const entry = {
        timestamp: '2025-01-02T00:00:00.000Z',
        address: REAL_ADDRESS,
        action: 'update'
      };
      const result = tracking.addHistoryEntry(data, entry);
      expect(result.change_history).to.have.length(2);
      expect(result.change_history[1]).to.deep.include(entry);
    });

    it('должен сохранять все поля записи', () => {
      const data = {};
      const entry = {
        timestamp: '2025-01-01T00:00:00.000Z',
        address: REAL_ADDRESS,
        action: 'register_in_contract',
        changes: ['contract_registration'],
        transaction_hash: '0xTransactionHash123',
        block_number: 456
      };
      const result = tracking.addHistoryEntry(data, entry);
      expect(result.change_history[0]).to.deep.equal(entry);
    });

    it('должен использовать дефолтные значения для отсутствующих полей', () => {
      const data = {};
      const entry = {
        address: REAL_ADDRESS,
        action: 'create'
      };
      const result = tracking.addHistoryEntry(data, entry);
      expect(result.change_history[0].timestamp).to.be.a('string');
      expect(result.change_history[0].changes).to.deep.equal([]);
      expect(result.change_history[0].transaction_hash).to.equal('0x0000000000000000000000000000000000000000000000000000000000000000');
      expect(result.change_history[0].block_number).to.equal(0);
    });
  });

  // ====================================================================
  // Тесты updateForCreation()
  // ====================================================================

  describe('updateForCreation()', () => {
    it('должен обновить все tracking-поля при создании', () => {
      const data = {
        created_by: TEST_ADDRESS,
        contributors: [{ address: TEST_ADDRESS, role: 'creator' }],
        metadata: {
          validation: {
            validator: TEST_ADDRESS
          }
        },
        sharing: {
          shared_by: TEST_ADDRESS
        }
      };
      const result = tracking.updateForCreation(data, {
        actorAddress: REAL_ADDRESS,
        action: 'upload_to_arweave',
        blockchain: null
      });
      
      expect(result.created_by).to.equal(REAL_ADDRESS);
      expect(result.contributors[0].address).to.equal(REAL_ADDRESS);
      expect(result.metadata.validation.validator).to.equal(REAL_ADDRESS);
      expect(result.sharing.shared_by).to.equal(REAL_ADDRESS);
    });

    it('должен добавить запись в change_history', () => {
      const data = {};
      const result = tracking.updateForCreation(data, {
        actorAddress: REAL_ADDRESS,
        action: 'create',
        blockchain: null
      });
      
      expect(result.change_history).to.have.length(1);
      expect(result.change_history[0].address).to.equal(REAL_ADDRESS);
      expect(result.change_history[0].action).to.equal('create');
    });

    it('должен обновить last_updated', () => {
      const data = {};
      const result = tracking.updateForCreation(data, {
        actorAddress: REAL_ADDRESS,
        action: 'create',
        blockchain: null
      });
      
      expect(result.last_updated).to.be.a('string');
      expect(new Date(result.last_updated).getTime()).to.be.closeTo(Date.now(), 1000);
    });

    it('должен использовать blockchain данные если предоставлены', () => {
      const data = {};
      const result = tracking.updateForCreation(data, {
        actorAddress: REAL_ADDRESS,
        action: 'register_in_contract',
        blockchain: {
          transactionHash: '0xTxHash123',
          blockNumber: 789
        }
      });
      
      expect(result.change_history[0].transaction_hash).to.equal('0xTxHash123');
      expect(result.change_history[0].block_number).to.equal(789);
    });
  });

  // ====================================================================
  // Тесты updateForModification()
  // ====================================================================

  describe('updateForModification()', () => {
    it('должен обновить validator при action=validate', () => {
      const data = {
        metadata: {
          validation: {
            validator: TEST_ADDRESS
          }
        }
      };
      const result = tracking.updateForModification(data, {
        actorAddress: REAL_ADDRESS,
        action: 'validate'
      });
      
      expect(result.metadata.validation.validator).to.equal(REAL_ADDRESS);
      expect(result.metadata.validation.last_validated).to.be.a('string');
      expect(result.change_history[0].action).to.equal('validate');
    });

    it('должен обновить moderation при action=moderate', () => {
      const data = {
        moderation: {
          status: 'pending'
        }
      };
      const result = tracking.updateForModification(data, {
        actorAddress: REAL_ADDRESS,
        action: 'moderate',
        status: 'approved'
      });
      
      expect(result.moderation.moderated_by).to.equal(REAL_ADDRESS);
      expect(result.moderation.status).to.equal('approved');
      expect(result.change_history[0].action).to.equal('moderate');
    });

    it('должен обновить sharing при action=share', () => {
      const data = {
        sharing: {
          is_shared: false
        }
      };
      const result = tracking.updateForModification(data, {
        actorAddress: REAL_ADDRESS,
        action: 'share'
      });
      
      expect(result.sharing.shared_by).to.equal(REAL_ADDRESS);
      expect(result.change_history[0].action).to.equal('share');
    });

    it('должен добавить контрибьютора при action=update', () => {
      const data = {
        contributors: []
      };
      const result = tracking.updateForModification(data, {
        actorAddress: REAL_ADDRESS,
        action: 'update'
      });
      
      expect(result.contributors).to.have.length(1);
      expect(result.contributors[0].address).to.equal(REAL_ADDRESS);
      expect(result.contributors[0].role).to.equal('editor');
    });
  });

  // ====================================================================
  // Тесты cleanSourceJson()
  // ====================================================================

  describe('cleanSourceJson()', () => {
    let tempJsonPath;
    let originalData;

    beforeEach(() => {
      // Создаем временный JSON файл для тестов
      tempJsonPath = path.join(__dirname, '../../../../data/components/test_component_tracking.json');
      originalData = {
        biounit_id: 'test_component',
        scientific_title: 'Test Component',
        created_by: TEST_ADDRESS,
        contributors: [
          { address: TEST_ADDRESS, role: 'creator' }
        ],
        metadata: {
          validation: {
            validator: TEST_ADDRESS
          }
        },
        sharing: {
          shared_by: TEST_ADDRESS
        },
        forms: ['dried'],
        features: { common: ['test'] }
      };
      
      // Создаем директорию если не существует
      const dir = path.dirname(tempJsonPath);
      if (!fs.existsSync(dir)) {
        fs.mkdirSync(dir, { recursive: true });
      }
      
      fs.writeFileSync(tempJsonPath, JSON.stringify(originalData, null, 2), 'utf8');
    });

    afterEach(() => {
      // Удаляем временный файл после теста
      if (fs.existsSync(tempJsonPath)) {
        fs.unlinkSync(tempJsonPath);
      }
    });

    it('должен читать исходный JSON файл', () => {
      const result = tracking.cleanSourceJson(tempJsonPath, REAL_ADDRESS);
      expect(result).to.exist;
      expect(result.biounit_id).to.equal('test_component');
    });

    it('должен заменять тестовые адреса на реальные', () => {
      const result = tracking.cleanSourceJson(tempJsonPath, REAL_ADDRESS);
      expect(result.created_by).to.equal(REAL_ADDRESS);
      expect(result.contributors[0].address).to.equal(REAL_ADDRESS);
      expect(result.metadata.validation.validator).to.equal(REAL_ADDRESS);
      expect(result.sharing.shared_by).to.equal(REAL_ADDRESS);
    });

    it('должен сохранять обновленный JSON обратно в файл', () => {
      tracking.cleanSourceJson(tempJsonPath, REAL_ADDRESS);
      
      // Читаем файл обратно и проверяем что он обновлен
      const savedData = JSON.parse(fs.readFileSync(tempJsonPath, 'utf8'));
      expect(savedData.created_by).to.equal(REAL_ADDRESS);
      expect(savedData.contributors[0].address).to.equal(REAL_ADDRESS);
    });

    it('должен сохранять остальной контент компонента', () => {
      const result = tracking.cleanSourceJson(tempJsonPath, REAL_ADDRESS);
      
      // Проверяем что остальные поля не изменились
      expect(result.biounit_id).to.equal(originalData.biounit_id);
      expect(result.scientific_title).to.equal(originalData.scientific_title);
      expect(result.forms).to.deep.equal(originalData.forms);
      expect(result.features).to.deep.equal(originalData.features);
    });

    it('должен возвращать обновленные данные', () => {
      const result = tracking.cleanSourceJson(tempJsonPath, REAL_ADDRESS);
      expect(result).to.be.an('object');
      expect(result.created_by).to.equal(REAL_ADDRESS);
    });

    it('должен выбрасывать ошибку если файл не найден', () => {
      const nonExistentPath = path.join(__dirname, '../../../../data/components/non_existent.json');
      expect(() => {
        tracking.cleanSourceJson(nonExistentPath, REAL_ADDRESS);
      }).to.throw('JSON файл не найден');
    });
  });
});
