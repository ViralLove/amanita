/**
 * Arweave deep-hash для верификации Data Item (ANS-104).
 * blob: sha256(sha256("blob" + len) + sha256(data))
 * list: sha256("list" + len), then acc = sha256(acc || deepHash(item)) for each item.
 */

import crypto from "node:crypto";

function sha256(data) {
  return crypto.createHash("sha256").update(data).digest();
}

function utf8Encode(s) {
  return Buffer.from(s, "utf8");
}

/**
 * @param {Uint8Array | (Uint8Array | any[])[]} chunk
 * @returns {Promise<Buffer>}
 */
async function deepHash(chunk) {
  if (
    (chunk instanceof Uint8Array || Buffer.isBuffer(chunk)) &&
    !Array.isArray(chunk)
  ) {
    const buf = Buffer.from(chunk);
    const tag = Buffer.concat([utf8Encode("blob"), utf8Encode(String(buf.length))]);
    const tagHash = sha256(tag);
    const dataHash = sha256(buf);
    return sha256(Buffer.concat([tagHash, dataHash]));
  }
  const list = chunk;
  const tag = Buffer.concat([utf8Encode("list"), utf8Encode(String(list.length))]);
  let acc = sha256(tag);
  for (const item of list) {
    const itemHash = await deepHash(item);
    acc = sha256(Buffer.concat([acc, itemHash]));
  }
  return acc;
}

export { deepHash };
