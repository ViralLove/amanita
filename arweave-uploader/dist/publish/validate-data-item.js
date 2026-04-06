/**
 * Валидация Data Item (ANS-104): парсинг, проверка подписи RSA-PSS, тег Upload-Id.
 * RSA: длина подписи = размер модуля в байтах; owner = DER SPKI переменной длины (2048→256/294, 4096→512/550, …).
 */

import crypto from "node:crypto";
import { deepHash } from "./deep-hash.js";

const SIGNATURE_TYPE_RSA = 1;

/** Кандидаты длины RSA-подписи (байт) = |n|/8 для типичных модулей. */
const RSA_SIGNATURE_LENGTH_CANDIDATES = [512, 384, 256];

function base64Decode(s) {
  const base64 = s.replace(/-/g, "+").replace(/_/g, "/");
  return Buffer.from(base64, "base64");
}

function base64UrlEncode(data) {
  return Buffer.from(data)
    .toString("base64")
    .replace(/\+/g, "-")
    .replace(/\//g, "_")
    .replace(/=+$/, "");
}

function readUint64LE(buf, off) {
  const lo =
    buf[off] | (buf[off + 1] << 8) | (buf[off + 2] << 16) | (buf[off + 3] << 24);
  const hi =
    buf[off + 4] |
    (buf[off + 5] << 8) |
    (buf[off + 6] << 16) |
    (buf[off + 7] << 24);
  return lo + hi * 0x100000000;
}

function readVInt(buf, off) {
  let value = 0;
  let shift = 0;
  let bytesRead = 0;
  let b;
  do {
    if (off + bytesRead >= buf.length) return { value: 0, bytesRead };
    b = buf[off + bytesRead];
    bytesRead++;
    value |= (b & 0x7f) << shift;
    shift += 7;
  } while (b & 0x80);
  return { value, bytesRead };
}

function zigzagDecode(n) {
  return (n >>> 1) ^ -(n & 1);
}

/**
 * Длина DER SEQUENCE начиная с offset (ожидается SPKI 0x30 …).
 * @returns {number|null}
 */
function derSequenceTotalLength(buf, offset) {
  if (offset >= buf.length || buf[offset] !== 0x30) return null;
  const lenByte = buf[offset + 1];
  if (lenByte === undefined) return null;
  let contentLen;
  let headerSize = 2;
  if (lenByte < 0x80) {
    contentLen = lenByte;
  } else {
    const n = lenByte & 0x7f;
    if (n === 0 || offset + 2 + n > buf.length) return null;
    contentLen = 0;
    for (let i = 0; i < n; i++) {
      contentLen = (contentLen << 8) | buf[offset + 2 + i];
    }
    headerSize = 2 + n;
  }
  const total = headerSize + contentLen;
  if (offset + total > buf.length) return null;
  return total;
}

function parseAvroTags(buf, offset, limit) {
  const tags = [];
  let pos = offset;
  const end = Math.min(offset + limit, buf.length);
  while (pos < end) {
    const { value: countZ, bytesRead: r1 } = readVInt(buf, pos);
    pos += r1;
    const count = zigzagDecode(countZ);
    if (count === 0) break;
    let blockBytesLeft = 0;
    if (count < 0) {
      const { value: sizeZ, bytesRead: r2 } = readVInt(buf, pos);
      pos += r2;
      blockBytesLeft = zigzagDecode(sizeZ);
    }
    const blockEnd = count < 0 ? pos + blockBytesLeft : end;
    const itemsInBlock = count < 0 ? 999 : count;
    for (let i = 0; i < itemsInBlock && pos < blockEnd; i++) {
      const { value: nameLenZ, bytesRead: rn } = readVInt(buf, pos);
      pos += rn;
      const nameLen = zigzagDecode(nameLenZ);
      if (pos + nameLen > blockEnd) break;
      const name = buf.subarray(pos, pos + nameLen);
      pos += nameLen;
      const { value: valueLenZ, bytesRead: rv } = readVInt(buf, pos);
      pos += rv;
      const valueLen = zigzagDecode(valueLenZ);
      if (pos + valueLen > blockEnd) break;
      const value = buf.subarray(pos, pos + valueLen);
      pos += valueLen;
      tags.push({ name, value });
    }
    if (count < 0) pos = blockEnd;
  }
  return tags;
}

function getTagValue(tags, tagName) {
  const want = Buffer.from(tagName, "utf8");
  for (const t of tags) {
    if (t.name.length !== want.length) continue;
    if (!t.name.equals(want)) continue;
    return t.value.toString("utf8");
  }
  return null;
}

/**
 * Парсинг тела Data Item после полей signature + owner.
 * @returns {{ target: Buffer, anchor: Buffer, numTags: number, numTagBytes: number, tagBytes: Buffer, data: Buffer, posAfter: number } | null}
 */
function parseAfterOwner(raw, pos) {
  if (pos + 1 + 1 + 8 + 8 > raw.length) return null;
  const targetPresent = raw[pos++];
  let target = Buffer.alloc(0);
  if (targetPresent === 1) {
    if (pos + 32 > raw.length) return null;
    target = raw.subarray(pos, pos + 32);
    pos += 32;
  } else if (targetPresent !== 0) return null;

  const anchorPresent = raw[pos++];
  let anchor = Buffer.alloc(0);
  if (anchorPresent === 1) {
    if (pos + 32 > raw.length) return null;
    anchor = raw.subarray(pos, pos + 32);
    pos += 32;
  } else if (anchorPresent !== 0) return null;

  const numTags = readUint64LE(raw, pos);
  pos += 8;
  const numTagBytes = readUint64LE(raw, pos);
  pos += 8;
  if (pos + numTagBytes > raw.length) return null;
  const tagBytes = raw.subarray(pos, pos + numTagBytes);
  pos += numTagBytes;
  const data = raw.subarray(pos);
  return { target, anchor, numTags, numTagBytes, tagBytes, data, posAfter: pos };
}

/**
 * @param {string} signedDataItemBase64
 * @param {string} uploadId
 * @returns {Promise<{ ok: true, itemId?: string } | { ok: false, code: 'signature_invalid' }>}
 */
export async function validateDataItem(signedDataItemBase64, uploadId) {
  let raw;
  try {
    raw = base64Decode(signedDataItemBase64);
  } catch {
    return { ok: false, code: "signature_invalid" };
  }
  if (raw.length < 2 + 1 + 1 + 8 + 8) {
    return { ok: false, code: "signature_invalid" };
  }

  const sigType = raw[0] | (raw[1] << 8);
  if (sigType !== SIGNATURE_TYPE_RSA) {
    return { ok: false, code: "signature_invalid" };
  }

  for (const sigLen of RSA_SIGNATURE_LENGTH_CANDIDATES) {
    const ostart = 2 + sigLen;
    if (ostart >= raw.length) continue;

    const spkiLen = derSequenceTotalLength(raw, ostart);
    if (spkiLen === null || spkiLen < 50) continue;

    const signature = raw.subarray(2, 2 + sigLen);
    const owner = raw.subarray(ostart, ostart + spkiLen);

    let publicKey;
    try {
      publicKey = crypto.createPublicKey({
        key: Buffer.from(owner),
        format: "der",
        type: "spki",
      });
    } catch {
      continue;
    }

    const details = publicKey.asymmetricKeyDetails;
    const modulusBits = details?.modulusLength;
    if (modulusBits == null) continue;
    const expectedSigBytes = modulusBits / 8;
    if (expectedSigBytes !== sigLen) continue;

    const rest = parseAfterOwner(raw, ostart + spkiLen);
    if (!rest) continue;

    const { target, anchor, numTagBytes, tagBytes, data } = rest;

    const tags = parseAvroTags(tagBytes, 0, numTagBytes);
    const uploadIdTag = getTagValue(tags, "Upload-Id");
    if (uploadIdTag !== uploadId) continue;

    const tagsForDeepHash = tags.map((t) => [t.name, t.value]);
    const deepHashInput = [
      Buffer.from("dataitem", "utf8"),
      Buffer.from("1", "utf8"),
      owner,
      target,
      anchor,
      tagsForDeepHash,
      data,
    ];
    const message = await deepHash(deepHashInput);

    const valid = crypto.verify(
      "RSA-SHA256",
      message,
      {
        key: publicKey,
        padding: crypto.constants.RSA_PKCS1_PSS_PADDING,
        saltLength: 32,
      },
      signature
    );
    if (!valid) continue;

    const idHash = crypto.createHash("sha256").update(signature).digest();
    const itemId = base64UrlEncode(idHash);
    return { ok: true, itemId, rsaSignatureBytes: sigLen };
  }

  return { ok: false, code: "signature_invalid" };
}

/**
 * Синхронно: длина RSA-подписи в байтах по структуре Data Item (без проверки подписи).
 * Нужна для сборки ANS-104 bundle с тем же смещением, что и при validateDataItem.
 * @param {Buffer | Uint8Array} raw
 * @returns {number | null}
 */
export function getRsaSignatureByteLength(raw) {
  const buf = Buffer.isBuffer(raw) ? raw : Buffer.from(raw);
  if (buf.length < 2 + 1 + 1 + 8 + 8) return null;
  const sigType = buf[0] | (buf[1] << 8);
  if (sigType !== SIGNATURE_TYPE_RSA) return null;
  for (const sigLen of RSA_SIGNATURE_LENGTH_CANDIDATES) {
    const ostart = 2 + sigLen;
    if (ostart >= buf.length) continue;
    const spkiLen = derSequenceTotalLength(buf, ostart);
    if (spkiLen === null || spkiLen < 50) continue;
    const owner = buf.subarray(ostart, ostart + spkiLen);
    let publicKey;
    try {
      publicKey = crypto.createPublicKey({
        key: Buffer.from(owner),
        format: "der",
        type: "spki",
      });
    } catch {
      continue;
    }
    const details = publicKey.asymmetricKeyDetails;
    const modulusBits = details?.modulusLength;
    if (modulusBits == null) continue;
    if (modulusBits / 8 !== sigLen) continue;
    const rest = parseAfterOwner(buf, ostart + spkiLen);
    if (!rest) continue;
    return sigLen;
  }
  return null;
}
