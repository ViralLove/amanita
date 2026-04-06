/**
 * Фикстура: минимальный валидный Data Item (ANS-104) с одной меткой Upload-Id и подписью RSA-PSS.
 * Для P0/P1 тестов validateDataItem.
 *
 * Layout: signature type (2) + RSA signature (|n|/8) + owner SPKI DER (переменная длина) + target + anchor + tags + data.
 * Поддерживаются типичные RSA модули 2048 / 3072 / 4096 (и др., если Node генерирует пару).
 */

import crypto from "node:crypto";
import { deepHash } from "../../dist/publish/deep-hash.js";

const SIGNATURE_TYPE_RSA = 1;

function writeVInt(buf, offset, value) {
  let v = value;
  let pos = offset;
  while (v > 0x7f) {
    buf[pos++] = (v & 0x7f) | 0x80;
    v >>>= 7;
  }
  buf[pos++] = v & 0x7f;
  return pos - offset;
}

function writeUint64LE(buf, offset, value) {
  const lo = value >>> 0;
  const hi = (value / 0x100000000) >>> 0;
  buf[offset] = lo & 0xff;
  buf[offset + 1] = (lo >> 8) & 0xff;
  buf[offset + 2] = (lo >> 16) & 0xff;
  buf[offset + 3] = (lo >> 24) & 0xff;
  buf[offset + 4] = hi & 0xff;
  buf[offset + 5] = (hi >> 8) & 0xff;
  buf[offset + 6] = (hi >> 16) & 0xff;
  buf[offset + 7] = (hi >> 24) & 0xff;
  return 8;
}

function zigzagEncode(n) {
  return n >= 0 ? n * 2 : -n * 2 - 1;
}

const cachedKeyPairs = new Map();

function getKeyPair(modulusLength) {
  if (!cachedKeyPairs.has(modulusLength)) {
    cachedKeyPairs.set(
      modulusLength,
      crypto.generateKeyPairSync("rsa", { modulusLength })
    );
  }
  return cachedKeyPairs.get(modulusLength);
}

/**
 * Строит Avro-блок одного тега (name, value) и возвращает Buffer.
 */
function buildTagBlock(name, value) {
  const nameBuf = Buffer.from(name, "utf8");
  const valueBuf = Buffer.from(value, "utf8");
  const nameLenZ = zigzagEncode(nameBuf.length);
  const valueLenZ = zigzagEncode(valueBuf.length);
  const countZ = zigzagEncode(1);
  const size = 16 + nameBuf.length + valueBuf.length;
  const buf = Buffer.alloc(size);
  let off = 0;
  off += writeVInt(buf, off, countZ);
  off += writeVInt(buf, off, nameLenZ);
  buf.set(nameBuf, off);
  off += nameBuf.length;
  off += writeVInt(buf, off, valueLenZ);
  buf.set(valueBuf, off);
  off += valueBuf.length;
  return buf.subarray(0, off);
}

/**
 * Создаёт валидный подписанный Data Item с тегом Upload-Id = uploadIdValue.
 * @param {string} uploadIdValue — значение тега Upload-Id
 * @param {Buffer} [data] — тело data (по умолчанию пустой)
 * @param {{ modulusLength?: number }} [opts] — по умолчанию 2048; для тестов 4096: `{ modulusLength: 4096 }`
 * @returns {Promise<string>} base64 строки подписанного data item
 */
export async function createValidDataItem(uploadIdValue, data = Buffer.alloc(0), opts = {}) {
  const modulusLength = opts.modulusLength ?? 2048;
  const pair = getKeyPair(modulusLength);
  const owner = pair.publicKey.export({ type: "spki", format: "der" });
  const target = Buffer.alloc(0);
  const anchor = Buffer.alloc(0);
  const tagBlock = buildTagBlock("Upload-Id", uploadIdValue);
  const numTags = 1;
  const numTagBytes = tagBlock.length;

  const sigPlaceholderLen = modulusLength / 8;
  const raw = Buffer.alloc(
    2 + sigPlaceholderLen + owner.length + 1 + 1 + 8 + 8 + numTagBytes + data.length
  );
  let off = 0;
  raw[off++] = SIGNATURE_TYPE_RSA & 0xff;
  raw[off++] = (SIGNATURE_TYPE_RSA >> 8) & 0xff;
  off += sigPlaceholderLen;
  raw.set(owner, off);
  off += owner.length;
  raw[off++] = 0;
  raw[off++] = 0;
  off += writeUint64LE(raw, off, numTags);
  off += writeUint64LE(raw, off, numTagBytes);
  raw.set(tagBlock, off);
  off += numTagBytes;
  raw.set(data, off);

  const tagsForDeepHash = [["Upload-Id", uploadIdValue]].map(([n, v]) => [
    Buffer.from(n, "utf8"),
    Buffer.from(v, "utf8"),
  ]);
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
  const signature = crypto.sign("RSA-SHA256", message, {
    key: pair.privateKey,
    padding: crypto.constants.RSA_PKCS1_PSS_PADDING,
    saltLength: 32,
  });
  if (signature.length !== sigPlaceholderLen) {
    throw new Error(`Expected signature ${sigPlaceholderLen} bytes, got ${signature.length}`);
  }
  raw.set(signature, 2);
  return raw.toString("base64");
}
