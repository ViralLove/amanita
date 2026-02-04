/**
 * Сборка ANS-104 bundle из одного Data Item и публикация в Arweave.
 * Заголовок: 32 байта N=1, 32 байта size, 32 байта entry ID; затем сырой Data Item.
 */

import { signTransaction } from "../arweave/compatible.ts";

const RSA_SIGNATURE_LENGTH = 256;

/** Извлечь 32-байтный entry ID из подписанного Data Item (sha256(signature)). */
async function getDataItemId(signedItem: Uint8Array): Promise<Uint8Array> {
  if (signedItem.length < 2 + RSA_SIGNATURE_LENGTH) {
    throw new Error("Data item too short");
  }
  const signature = signedItem.slice(2, 2 + RSA_SIGNATURE_LENGTH);
  const hash = await crypto.subtle.digest("SHA-256", signature);
  return new Uint8Array(hash);
}

/** Записать 32-байтное число (little-endian). */
function writeU32LE(n: number): Uint8Array {
  const out = new Uint8Array(32);
  for (let i = 0; i < 32; i++) {
    out[i] = n & 0xff;
    n = Math.floor(n / 256);
  }
  return out;
}

/** Собрать тело bundle (ANS-104): N=1, size, entry_id, raw data item. */
async function buildBundleBody(signedDataItem: Uint8Array): Promise<Uint8Array> {
  const id = await getDataItemId(signedDataItem);
  const n = 1;
  const size = signedDataItem.length;
  const header = new Uint8Array(32 + 32 + 32);
  header.set(writeU32LE(n), 0);
  header.set(writeU32LE(size), 32);
  header.set(id, 64);
  const body = new Uint8Array(header.length + signedDataItem.length);
  body.set(header, 0);
  body.set(signedDataItem, header.length);
  return body;
}

export async function bundleAndPublish(
  signedDataItemBytes: Uint8Array,
  arweave: any,
  privateKey: JsonWebKey
): Promise<{ bundleTxId: string } | { error: string }> {
  try {
    const bundleBytes = await buildBundleBody(signedDataItemBytes);
    const transaction = await arweave.createTransaction(
      { data: bundleBytes },
      privateKey
    );
    transaction.addTag("Bundle-Format", "binary");
    transaction.addTag("Bundle-Version", "2.0.0");
    await signTransaction(arweave, transaction, privateKey);
    const response = await arweave.transactions.post(transaction);
    if (response.status === 200 || response.status === 202) {
      return { bundleTxId: transaction.id };
    }
    return { error: `Arweave post failed: ${response.status}` };
  } catch (e) {
    const msg = e instanceof Error ? e.message : String(e);
    return { error: msg };
  }
}
