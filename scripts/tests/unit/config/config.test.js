/**
 * Unit Tests: Config Module
 * 
 * Tests for the centralized configuration module.
 */

const { expect } = require('chai');
const path = require('path');

describe('Config Module', () => {
  let config;

  before(() => {
    // Load test environment
    const testEnvPath = path.join(__dirname, '../../fixtures/env/test.env');
    require('dotenv').config({ path: testEnvPath });
    
    // Load config module
    config = require('../../../lib/config/index');
  });

  describe('Environment Validation', () => {
    it('должен загружать конфигурацию', () => {
      // THEN: Config загружен
      expect(config).to.be.an('object');
      expect(config.config).to.be.an('object');
    });

    it('должен иметь deployer конфигурацию', () => {
      // THEN: Deployer config существует
      expect(config.config.deployer).to.be.an('object');
      expect(config.config.deployer.privateKey).to.be.a('string');
    });

    it('должен иметь seller конфигурацию', () => {
      // THEN: Seller config существует
      expect(config.config.seller).to.be.an('object');
      expect(config.config.seller.address).to.be.a('string');
      expect(config.config.seller.businessId).to.be.a('string');
    });

    it('должен применять default значения', () => {
      // THEN: Default значения применены
      expect(['test_seller', 'iveta', 'Iveta']).to.include(config.config.seller.businessId);
      expect(['test_seller_001', 'iveta_zeya888', 'Iveta_zeya888']).to.include(config.config.seller.id);
    });

    it('должен нормализовать private keys (добавлять 0x)', () => {
      // THEN: Private keys начинаются с 0x
      expect(config.config.deployer.privateKey).to.match(/^0x[a-fA-F0-9]{64}$/);
    });
  });

  describe('Config Access Methods', () => {
    it('должен возвращать значения через get()', () => {
      // WHEN: get() вызывается с валидным путем
      const deployerKey = config.get('deployer.privateKey');
      
      // THEN: Корректное значение возвращается
      expect(deployerKey).to.be.a('string');
      expect(deployerKey).to.match(/^0x/);
    });

    it('должен возвращать undefined для несуществующего пути', () => {
      // WHEN: get() вызывается с несуществующим путем
      const result = config.get('nonexistent.path');
      
      // THEN: undefined возвращается
      expect(result).to.be.undefined;
    });

    it('должен возвращать default через getWithDefault()', () => {
      // WHEN: getWithDefault() вызывается для отсутствующего значения
      const result = config.getWithDefault('missing.value', 'default');
      
      // THEN: Default возвращается
      expect(result).to.equal('default');
    });

    it('должен проверять наличие значения через isSet()', () => {
      // WHEN: isSet() вызывается
      const isSet = config.isSet('deployer.privateKey');
      const notSet = config.isSet('nonexistent.value');
      
      // THEN: Корректные результаты
      expect(isSet).to.be.true;
      expect(notSet).to.be.false;
    });
  });

  describe('Backward Compatibility', () => {
    it('должен поддерживать getContractAddress()', () => {
      // WHEN: getContractAddress() вызывается
      const address = config.getContractAddress('MagicRegistry');
      
      // THEN: Значение возвращается или null/undefined
      const isValid = address === null || address === undefined || typeof address === 'string';
      expect(isValid).to.be.true;
    });

    it('должен поддерживать getSellerConfig()', () => {
      // WHEN: getSellerConfig() вызывается
      const sellerConfig = config.getSellerConfig();
      
      // THEN: Seller config возвращается
      expect(sellerConfig).to.be.an('object');
      expect(['test_seller', 'iveta', 'Iveta']).to.include(sellerConfig.businessId);
    });

    it('должен поддерживать getDeployerConfig()', () => {
      // WHEN: getDeployerConfig() вызывается
      const deployerConfig = config.getDeployerConfig();
      
      // THEN: Deployer config возвращается
      expect(deployerConfig).to.be.an('object');
      expect(deployerConfig.privateKey).to.be.a('string');
    });
  });
});

