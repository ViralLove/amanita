/**
 * Diagnostic script: проверка появления receipt после отправки tx через alternate RPC
 * для идентификации гипотезы (A1/A2 vs B1 vs C1).
 *
 * Сценарий: отправить 1 tx на primary (polygon-rpc.com), дождаться receipt; переключить
 * provider на alternate (publicnode); отправить 2-ю tx на alternate; опрашивать
 * getTransactionReceipt(tx2Hash) на primary, alternate и третьем RPC с интервалами
 * (0s, 5s, 15s, 30s) и вывести, на каком RPC и когда receipt появился.
 *
 * Запуск (Polygon mainnet, нужен DEPLOYER_PRIVATE_KEY):
 *   npx hardhat run scripts/utility/diagnostic-rpc-receipt-after-switch.js --network polygon
 *
 * Если ключа нет — скрипт выводит инструкцию и завершается.
 *
 * Гипотезы:
 * - A1/A2: receipt на всех RPC остаётся null → alternate не разослал tx.
 * - B1: receipt сначала null, затем появляется на alternate (или на всех) с задержкой.
 * - C1: receipt не появляется или появляется только на части RPC (расхождение состояния).
 *
 * @see docs/methodology/hypothesis-driven-error-analysis.md
 * @see scripts/docs/analysis/rpc-retry-action777-tx3-not-in-chain-analysis-2026-01-30.md
 */

require('dotenv').config();
const { ethers } = require('hardhat');

const PRIMARY = 'https://polygon-rpc.com';
const ALTERNATE = 'https://polygon-bor-rpc.publicnode.com';
const THIRD = 'https://1rpc.io/matic';

const POLL_INTERVALS_MS = [0, 5000, 15000, 30000]; // 0s, 5s, 15s, 30s — итог ~50s

async function getReceipt(provider, txHash) {
  try {
    const r = await provider.send('eth_getTransactionReceipt', [txHash]);
    return r;
  } catch (e) {
    return { error: e.message };
  }
}

async function main() {
  const raw = process.env.DEPLOYER_PRIVATE_KEY;
  if (!raw || typeof raw !== 'string' || raw.trim().length < 32) {
    console.log('Diagnostic skipped: DEPLOYER_PRIVATE_KEY not set.');
    console.log('To run on Polygon: set DEPLOYER_PRIVATE_KEY and run with --network polygon');
    console.log('This script sends 2 real tx (tiny value to self) and polls for receipt of the 2nd.');
    return;
  }
  const pk = raw.startsWith('0x') ? raw : `0x${raw}`;

  const primaryProvider = new ethers.JsonRpcProvider(PRIMARY);
  const alternateProvider = new ethers.JsonRpcProvider(ALTERNATE);
  const thirdProvider = new ethers.JsonRpcProvider(THIRD);

  const walletPrimary = new ethers.Wallet(pk, primaryProvider);
  const walletAlternate = new ethers.Wallet(pk, alternateProvider);

  const addr = await walletPrimary.getAddress();
  console.log('Address:', addr);
  const nonce = await primaryProvider.getTransactionCount(addr, 'latest');
  console.log('Current nonce (from primary):', nonce);

  // Polygon: фиксированный gasPrice; отправка через eth_sendRawTransaction, чтобы не вызывать Polygon Gas Station
  const gasPricePolygon = ethers.parseUnits('700', 'gwei');
  const chainId = 137;

  async function sendRawTx(provider, wallet, to, value, nonce) {
    const tx = { to, value, gasLimit: 21000n, nonce, gasPrice: gasPricePolygon, chainId, type: 0 };
    const signed = await wallet.signTransaction(tx);
    let hash;
    try {
      hash = await provider.send('eth_sendRawTransaction', [signed]);
    } catch (e) {
      if (e.message && e.message.includes('already known')) {
        hash = ethers.keccak256(ethers.getBytes(signed));
      } else {
        throw e;
      }
    }
    return { hash: typeof hash === 'string' ? hash : hash.hash, provider };
  }

  // Tx1: на primary, 0 value к себе
  console.log('\n--- Tx1 on primary ---');
  const tx1Payload = await sendRawTx(primaryProvider, walletPrimary, addr, 0n, nonce);
  const tx1Hash = tx1Payload.hash;
  console.log('Tx1 hash:', tx1Hash);
  let receipt1 = null;
  for (let i = 0; i < 60; i++) {
    await new Promise(r => setTimeout(r, 2000));
    receipt1 = await primaryProvider.send('eth_getTransactionReceipt', [tx1Hash]);
    if (receipt1) break;
  }
  if (!receipt1) {
    console.log('Tx1 receipt not found on primary after 120s (primary RPC may be slow); proceeding to Tx2.');
  } else {
    console.log('Tx1 receipt: block', receipt1.blockNumber, 'status', receipt1.status);
  }

  // Tx2: на alternate, nonce+1
  console.log('\n--- Tx2 on alternate (after "switch") ---');
  const tx2Payload = await sendRawTx(alternateProvider, walletAlternate, addr, 0n, nonce + 1);
  const tx2Hash = tx2Payload.hash;
  console.log('Tx2 hash:', tx2Hash);

  // Poll receipt on primary, alternate, third at intervals
  console.log('\n--- Polling receipt on primary, alternate, third ---');
  const results = [];
  for (const delayMs of POLL_INTERVALS_MS) {
    if (delayMs > 0) {
      console.log(`Waiting ${delayMs / 1000}s...`);
      await new Promise(r => setTimeout(r, delayMs));
    }
    const t = Date.now();
    const [rPrimary, rAlternate, rThird] = await Promise.all([
      getReceipt(primaryProvider, tx2Hash),
      getReceipt(alternateProvider, tx2Hash),
      getReceipt(thirdProvider, tx2Hash)
    ]);
    const row = {
      delayMs,
      t,
      primary: rPrimary && !rPrimary.error ? (rPrimary.status === '0x1' ? 'Success' : 'Failed') : (rPrimary?.error || 'null'),
      alternate: rAlternate && !rAlternate.error ? (rAlternate.status === '0x1' ? 'Success' : 'Failed') : (rAlternate?.error || 'null'),
      third: rThird && !rThird.error ? (rThird.status === '0x1' ? 'Success' : 'Failed') : (rThird?.error || 'null')
    };
    results.push(row);
    console.log(`  ${delayMs}ms: primary=${row.primary} alternate=${row.alternate} third=${row.third}`);
  }

  console.log('\n--- Summary (hypothesis identification) ---');
  const last = results[results.length - 1];
  if (last.primary === 'null' && last.alternate === 'null' && last.third === 'null') {
    console.log('Receipt remained null on all RPCs → consistent with A1/A2 (alternate did not broadcast tx).');
  } else if (last.alternate !== 'null' && (last.primary === 'null' || last.third === 'null')) {
    console.log('Receipt appeared on alternate but not on all → possible propagation delay or C1 (state divergence).');
  } else if (last.primary !== 'null' || last.alternate !== 'null' || last.third !== 'null') {
    console.log('Receipt appeared on at least one RPC → tx reached chain; B1 (delay) or normal propagation.');
  }
}

main().catch(e => {
  console.error(e);
  process.exit(1);
});
