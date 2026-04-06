/**
 * Сборка ANS-104 bundle из одного Data Item и публикация в Arweave.
 * Bundle: 32 bytes count, N×(32 bytes offset, 32 bytes id), затем сырые Data Items.
 * Длина RSA-подписи: 256 / 384 / 512 байт (2048 / 3072 / 4096 bit) — как в validateDataItem.
 */

import crypto from "node:crypto";
import { getRsaSignatureByteLength } from "./validate-data-item.js";

const BUNDLE_HEADER_ITEM_COUNT_SIZE = 32;
const BUNDLE_INDEX_ENTRY_SIZE = 64;

/**
 * @param {Buffer | Uint8Array} signedDataItemBytes
 * @param {number | undefined} rsaSignatureBytes — из успешного validateDataItem (rsaSignatureBytes); иначе detect по байтам
 */
function buildBundleBuffer(signedDataItemBytes, rsaSignatureBytes) {
  const dataItemBuf = Buffer.isBuffer(signedDataItemBytes)
    ? signedDataItemBytes
    : Buffer.from(signedDataItemBytes);
  const sigLen =
    rsaSignatureBytes ?? getRsaSignatureByteLength(dataItemBuf);
  if (sigLen == null) {
    throw new Error(
      "bundle: cannot determine RSA signature length (expected 2048/3072/4096-bit RSA Data Item)"
    );
  }
  const signature = dataItemBuf.subarray(2, 2 + sigLen);
  const itemId = crypto.createHash("sha256").update(signature).digest();

  const numItems = 1;
  const firstItemOffset = BUNDLE_HEADER_ITEM_COUNT_SIZE + BUNDLE_INDEX_ENTRY_SIZE;

  const header = Buffer.alloc(BUNDLE_HEADER_ITEM_COUNT_SIZE);
  header.writeBigUInt64LE(BigInt(numItems), 0);
  const offsetBuf = Buffer.alloc(32);
  offsetBuf.writeBigUInt64LE(BigInt(firstItemOffset), 0);
  const idBuf = Buffer.alloc(32);
  itemId.copy(idBuf, 0);

  return Buffer.concat([header, offsetBuf, idBuf, dataItemBuf]);
}

/**
 * @param {Buffer | Uint8Array} signedDataItemBytes — сырые байты подписанного Data Item (ANS-104).
 * @param {{ arweave: object, jwk: object }} arweaveClient — клиент с arweave и jwk.
 * @param {{ rsaSignatureBytes?: number }} [options] — rsaSignatureBytes из успешного validateDataItem (рекомендуется).
 * @returns {Promise<{ bundleTxId: string } | { error: string }>}
 */
export async function bundleAndPublish(signedDataItemBytes, arweaveClient, options = {}) {
  try {
    const bundleBytes = buildBundleBuffer(
      signedDataItemBytes,
      options.rsaSignatureBytes
    );
    const { arweave, jwk } = arweaveClient;
    const tx = await arweave.createTransaction(
      { data: bundleBytes },
      jwk
    );
    tx.addTag("Bundle-Format", "binary");
    tx.addTag("Bundle-Version", "2.0.0");
    await arweave.transactions.sign(tx, jwk);
    const response = await arweave.transactions.post(tx);
    if (response.status >= 400) {
      const bodySnippet =
        typeof response.data === "string"
          ? response.data.slice(0, 200)
          : JSON.stringify(response.data || {}).slice(0, 200);
      return {
        error: `Arweave rejected: ${response.status} ${response.statusText} ${bodySnippet}`,
      };
    }
    return { bundleTxId: tx.id };
  } catch (err) {
    const message = err?.message ?? String(err);
    return { error: message };
  }
}
