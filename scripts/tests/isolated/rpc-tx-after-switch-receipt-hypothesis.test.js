/**
 * Isolated test: воспроизведение ситуации "tx3 не в канонической цепи" после RPC switch
 * для идентификации правильной гипотезы (hypothesis-driven-error-analysis).
 *
 * Контекст: Action 777 — tx1,tx2 отправлены на primary RPC (в цепи), tx3 получил rate limit,
 * switch на alternate (publicnode), tx3 отправлена на alternate (hash возвращён), receipt на
 * обоих RPC = null. Гипотезы: A1/A2 (alternate не разослал), B1 (не дошла до валидаторов),
 * C1 (расхождение состояния ноды).
 *
 * Цель теста: изолированно воспроизвести сценарий (send на primary → rate limit → switch →
 * send на alternate → poll receipt на primary и alternate) и проверить ожидаемое поведение
 * при гипотезах A1/A2 vs B1.
 *
 * @see docs/methodology/hypothesis-driven-error-analysis.md
 * @see scripts/docs/analysis/rpc-retry-action777-tx3-not-in-chain-analysis-2026-01-30.md
 */

const { expect } = require('chai');
const sinon = require('sinon');

describe('Isolated: RPC tx-after-switch receipt hypothesis (Action 777 tx3)', () => {
  const TX1_HASH = '0x3e1ccce20a7a1c70cb100bd61540eacb96079966db2feae4b423d021428877ee';
  const TX2_HASH = '0x96efbb06d94528d2b4fd903934d2f17f93256b768bc966ebc4d3e4576421c491';
  const TX3_HASH = '0x9176d8942939352de5bbafd14fad5de69a7048db023240955030b326f8708072';

  let primaryProvider;
  let alternateProvider;
  let sendCallCountPrimary;
  let sendCallCountAlternate;

  beforeEach(() => {
    sendCallCountPrimary = 0;
    sendCallCountAlternate = 0;
    primaryProvider = createMockPrimaryProvider();
    alternateProvider = createMockAlternateProvider();
  });

  afterEach(() => {
    sinon.restore();
  });

  /**
   * Primary RPC: первые 2 send — success (возвращаем tx с hash), 3-й — rate limit.
   * getTransactionReceipt: для tx1,tx2 — receipt; для tx3 — null (tx ушла на alternate).
   */
  function createMockPrimaryProvider() {
    return {
      send: sinon.stub().callsFake((method, params) => {
        if (method === 'eth_sendRawTransaction') {
          sendCallCountPrimary++;
          if (sendCallCountPrimary <= 2) {
            return Promise.resolve(sendCallCountPrimary === 1 ? TX1_HASH : TX2_HASH);
          }
          return Promise.reject(Object.assign(new Error('Too many requests, reason: call rate limit exhausted'), { code: 'RATE_LIMIT' }));
        }
        if (method === 'eth_getTransactionReceipt') {
          const [txHash] = params || [];
          if (txHash === TX1_HASH || txHash === TX2_HASH) {
            return Promise.resolve({ status: '0x1', blockNumber: '0x4e82fe8', transactionHash: txHash });
          }
          return Promise.resolve(null);
        }
        if (method === 'eth_getTransactionCount') {
          return Promise.resolve('0x5a'); // 90
        }
        return Promise.resolve(null);
      })
    };
  }

  /**
   * Alternate RPC (publicnode): send всегда success (возвращаем tx3 hash).
   * getTransactionReceipt(tx3): по умолчанию null — воспроизводит гипотезу A1/A2 (не разослал).
   * Опция: вернуть receipt после "задержки" (второй вызов) — для сценария B1.
   */
  function createMockAlternateProvider(opts = {}) {
    const { receiptAfterDelay = false } = opts;
    let getReceiptCallCount = 0;
    return {
      send: sinon.stub().callsFake((method, params) => {
        if (method === 'eth_sendRawTransaction') {
          sendCallCountAlternate++;
          return Promise.resolve(TX3_HASH);
        }
        if (method === 'eth_getTransactionReceipt') {
          const [txHash] = params || [];
          if (txHash !== TX3_HASH) return Promise.resolve(null);
          getReceiptCallCount++;
          if (receiptAfterDelay && getReceiptCallCount >= 2) {
            return Promise.resolve({ status: '0x1', blockNumber: '0x4e82fea', transactionHash: TX3_HASH });
          }
          return Promise.resolve(null);
        }
        return Promise.resolve(null);
      })
    };
  }

  /**
   * Воспроизведение потока: 2 tx на primary, rate limit на 3-й, switch, 3-я tx на alternate,
   * затем опрос receipt для tx3 на primary и alternate.
   */
  async function reproduceFlow(primary, alternate) {
    const results = { tx1Hash: null, tx2Hash: null, tx3Hash: null, receiptOnPrimary: null, receiptOnAlternate: null };
    const getReceipt = (provider, hash) =>
      provider.send('eth_getTransactionReceipt', [hash]).then(r => r);

    // Tx1, Tx2 на primary
    results.tx1Hash = await primary.send('eth_sendRawTransaction', ['0x...1']);
    results.tx2Hash = await primary.send('eth_sendRawTransaction', ['0x...2']);
    expect(results.tx1Hash).to.equal(TX1_HASH);
    expect(results.tx2Hash).to.equal(TX2_HASH);

    // Tx3 на primary — rate limit
    try {
      await primary.send('eth_sendRawTransaction', ['0x...3']);
    } catch (e) {
      expect(e.message).to.include('rate limit');
    }

    // "Switch": используем alternate для tx3
    results.tx3Hash = await alternate.send('eth_sendRawTransaction', ['0x...3']);
    expect(results.tx3Hash).to.equal(TX3_HASH);

    // Poll receipt на primary и alternate (как в Phase 2)
    results.receiptOnPrimary = await getReceipt(primary, TX3_HASH);
    results.receiptOnAlternate = await getReceipt(alternate, TX3_HASH);

    return results;
  }

  describe('Reproduce problem situation', () => {
    it('воспроизводит ситуацию: tx3 отправлена на alternate, hash получен, receipt на обоих RPC = null (гипотеза A1/A2)', async () => {
      const primary = createMockPrimaryProvider();
      const alternate = createMockAlternateProvider({ receiptAfterDelay: false });

      const r = await reproduceFlow(primary, alternate);

      expect(r.tx3Hash).to.equal(TX3_HASH);
      expect(r.receiptOnPrimary).to.be.null;
      expect(r.receiptOnAlternate).to.be.null;

      // Диагностика: при A1/A2 alternate принял tx (вернул hash), но receipt у него же null
      expect(alternate.send.calledWith('eth_sendRawTransaction')).to.be.true;
      expect(alternate.send.calledWith('eth_getTransactionReceipt', [TX3_HASH])).to.be.true;
    });

    it('при сценарии "receipt после задержки" (B1): alternate возвращает receipt при повторном опросе', async () => {
      const primary = createMockPrimaryProvider();
      const alternate = createMockAlternateProvider({ receiptAfterDelay: true });

      const r = await reproduceFlow(primary, alternate);
      expect(r.receiptOnAlternate).to.be.null;

      const receiptSecondPoll = await alternate.send('eth_getTransactionReceipt', [TX3_HASH]);
      expect(receiptSecondPoll).to.not.be.null;
      expect(receiptSecondPoll.status).to.equal('0x1');
      expect(receiptSecondPoll.transactionHash).to.equal(TX3_HASH);
    });
  });

  describe('Hypothesis mapping', () => {
    it('A1/A2: alternate возвращает hash при send, но getTransactionReceipt(txHash) = null — согласуется с "RPC не разослал tx"', async () => {
      const alternate = createMockAlternateProvider({ receiptAfterDelay: false });
      const hash = await alternate.send('eth_sendRawTransaction', ['0xraw']);
      expect(hash).to.equal(TX3_HASH);
      const receipt = await alternate.send('eth_getTransactionReceipt', [hash]);
      expect(receipt).to.be.null;
    });

    it('B1: если бы alternate разослал tx, receipt мог бы появиться на нём при повторном опросе', async () => {
      const alternate = createMockAlternateProvider({ receiptAfterDelay: true });
      const hash = await alternate.send('eth_sendRawTransaction', ['0xraw']);
      const first = await alternate.send('eth_getTransactionReceipt', [hash]);
      const second = await alternate.send('eth_getTransactionReceipt', [hash]);
      expect(first).to.be.null;
      expect(second).to.not.be.null;
    });
  });
});
