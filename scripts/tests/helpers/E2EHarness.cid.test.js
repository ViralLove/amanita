const { expect } = require('chai');

// Подавляем лишние логи от harness (использует console.log)
const originalConsoleLog = console.log;
const originalConsoleWarn = console.warn;
const originalConsoleError = console.error;

console.log = () => {};
console.warn = () => {};
console.error = () => {};

const E2EHarness = require('./E2EHarness');

describe('helpers/E2EHarness.generateValidCid', () => {
  let harness;

  before(() => {
    harness = new E2EHarness();
  });

  after(() => {
    console.log = originalConsoleLog;
    console.warn = originalConsoleWarn;
    console.error = originalConsoleError;
  });

  it('возвращает корректный CID формата base58 (Qm + 44 символа)', () => {
    const cid = harness.generateValidCid();

    expect(cid, 'CID должен начинаться с Qm').to.match(/^Qm/);
    expect(cid.length, 'CID должен содержать 46 символов').to.equal(46);
    harness.assertCidFormat(cid); // использует ту же регулярку, что и prod код
  });

  it('детерминирован при одинаковом seed', () => {
    const seed = 'seed-123';
    const cid1 = harness.generateValidCid(seed);
    const cid2 = harness.generateValidCid(seed);

    expect(cid1).to.equal(cid2);
  });

  it('генерирует разные CID для разных seed', () => {
    const cid1 = harness.generateValidCid('seed-1');
    const cid2 = harness.generateValidCid('seed-2');

    expect(cid1).to.not.equal(cid2);
  });
});
