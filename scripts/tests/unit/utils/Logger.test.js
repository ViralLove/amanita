/**
 * Unit Tests: Logger
 * 
 * Tests for the centralized Logger utility.
 */

const { expect } = require('chai');
const sinon = require('sinon');

describe('Logger Module', () => {
  let Logger;
  let consoleLogStub;
  let consoleErrorStub;

  before(() => {
    // Load Logger module
    Logger = require('../../../lib/utils/Logger');
  });

  beforeEach(() => {
    // Stub console methods
    consoleLogStub = sinon.stub(console, 'log');
    consoleErrorStub = sinon.stub(console, 'error');
  });

  afterEach(() => {
    // Restore console methods
    consoleLogStub.restore();
    consoleErrorStub.restore();
  });

  describe('Log Levels', () => {
    it('должен логировать debug при level=debug', () => {
      // GIVEN: Logger с level='debug'
      Logger.setLevel('debug');
      
      // WHEN: logger.debug() вызывается
      Logger.debug('Test debug message');
      
      // THEN: Сообщение выводится
      expect(consoleLogStub.called).to.be.true;
      expect(consoleLogStub.firstCall.args[0]).to.include('Test debug message');
    });

    it('НЕ должен логировать debug при level=info', () => {
      // GIVEN: Logger с level='info'
      Logger.setLevel('info');
      
      // WHEN: logger.debug() вызывается
      Logger.debug('Test debug message');
      
      // THEN: Сообщение НЕ выводится
      expect(consoleLogStub.called).to.be.false;
    });

    it('должен логировать info при level=info', () => {
      // GIVEN: Logger с level='info'
      Logger.setLevel('info');
      
      // WHEN: logger.info() вызывается
      Logger.info('Test info message');
      
      // THEN: Сообщение выводится
      expect(consoleLogStub.called).to.be.true;
    });

    it('должен логировать warn при level=warn', () => {
      // GIVEN: Logger с level='warn'
      Logger.setLevel('warn');
      
      // WHEN: logger.warn() вызывается
      Logger.warn('Test warning message');
      
      // THEN: Сообщение выводится
      expect(consoleLogStub.called).to.be.true;
    });

    it('должен логировать error при любом level', () => {
      // GIVEN: Logger с level='error'
      Logger.setLevel('error');
      
      // WHEN: logger.error() вызывается
      Logger.error('Test error message');
      
      // THEN: Сообщение выводится
      expect(consoleErrorStub.called).to.be.true;
    });
  });

  describe('Special Formats', () => {
    it('должен форматировать action сообщения', () => {
      // GIVEN: Logger
      Logger.setLevel('info');
      
      // WHEN: logger.action(555, "Upload Components")
      Logger.action(555, 'Upload Components');
      
      // THEN: Форматированное сообщение выводится
      expect(consoleLogStub.called).to.be.true;
      const output = consoleLogStub.getCalls().map(call => call.args.join(' ')).join('\n');
      expect(output).to.include('Action 555');
      expect(output).to.include('Upload Components');
    });

    it('должен форматировать success сообщения', () => {
      // GIVEN: Logger
      Logger.setLevel('info');
      
      // WHEN: logger.success(555)
      Logger.success(555);
      
      // THEN: Success сообщение выводится
      expect(consoleLogStub.called).to.be.true;
      const output = consoleLogStub.getCalls().map(call => call.args.join(' ')).join('\n');
      expect(output).to.include('✅');
      expect(output).to.include('555');
    });

    it('должен форматировать section сообщения', () => {
      // GIVEN: Logger
      Logger.setLevel('info');
      
      // WHEN: logger.section('Test Section')
      Logger.section('Test Section');
      
      // THEN: Section сообщение выводится
      expect(consoleLogStub.called).to.be.true;
      const output = consoleLogStub.getCalls().map(call => call.args.join(' ')).join('\n');
      expect(output).to.include('Test Section');
    });
  });

  describe('Backward Compatibility', () => {
    it('должен поддерживать log() как алиас для info()', () => {
      // GIVEN: Logger с level='info'
      Logger.setLevel('info');
      
      // WHEN: logger.log() вызывается
      Logger.log('Test log message');
      
      // THEN: Сообщение выводится как info
      expect(consoleLogStub.called).to.be.true;
    });
  });
});

