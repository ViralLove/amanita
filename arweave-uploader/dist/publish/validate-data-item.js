/**
 * Валидация Data Item (ANS-104): парсинг, проверка подписи RSA-PSS, тег Upload-Id.
 */

import crypto from "node:crypto";
import { deepHash } from "./deep-hash.js";

const SIGNATURE_TYPE_RSA = 1;
const RSA_SIGNATURE_LENGTH = 256;
const RSA_OWNER_LENGTH = 294;

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
  if (
    raw.length <
    2 + RSA_SIGNATURE_LENGTH + RSA_OWNER_LENGTH + 1 + 1 + 8 + 8
  ) {
    return { ok: false, code: "signature_invalid" };
  }
  let off = 0;
  const sigType = raw[0] | (raw[1] << 8);
  if (sigType !== SIGNATURE_TYPE_RSA)
    return { ok: false, code: "signature_invalid" };
  off += 2;
  const signature = raw.subarray(off, off + RSA_SIGNATURE_LENGTH);
  off += RSA_SIGNATURE_LENGTH;
  const owner = raw.subarray(off, off + RSA_OWNER_LENGTH);
  off += RSA_OWNER_LENGTH;
  const targetPresent = raw[off++];
  let target = Buffer.alloc(0);
  if (targetPresent === 1) {
    if (off + 32 > raw.length) return { ok: false, code: "signature_invalid" };
    target = raw.subarray(off, off + 32);
    off += 32;
  }
  const anchorPresent = raw[off++];
  let anchor = Buffer.alloc(0);
  if (anchorPresent === 1) {
    if (off + 32 > raw.length) return { ok: false, code: "signature_invalid" };
    anchor = raw.subarray(off, off + 32);
    off += 32;
  }
  const numTags = readUint64LE(raw, off);
  off += 8;
  const numTagBytes = readUint64LE(raw, off);
  off += 8;
  if (off + numTagBytes > raw.length)
    return { ok: false, code: "signature_invalid" };
  const tagBytes = raw.subarray(off, off + numTagBytes);
  off += numTagBytes;
  const data = raw.subarray(off);

  const tags = parseAvroTags(tagBytes, 0, numTagBytes);
  const uploadIdTag = getTagValue(tags, "Upload-Id");
  if (uploadIdTag !== uploadId) return { ok: false, code: "signature_invalid" };

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

  let publicKey;
  try {
    publicKey = crypto.createPublicKey({
      key: Buffer.from(owner),
      format: "der",
      type: "spki",
    });
  } catch {
    return { ok: false, code: "signature_invalid" };
  }

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
  if (!valid) return { ok: false, code: "signature_invalid" };

  const idHash = crypto.createHash("sha256").update(signature).digest();
  const itemId = base64UrlEncode(idHash);
  return { ok: true, itemId };
}
