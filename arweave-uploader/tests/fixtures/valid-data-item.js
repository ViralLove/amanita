/**
 * Фикстура: минимальный валидный Data Item (ANS-104) с одной меткой Upload-Id и подписью RSA-PSS.
 * Для P0/P1 тестов validateDataItem.
 *
 * Что за контент и почему в байтах:
 * - ANS-104 Data Item — это бинарный формат (спека Arweave/Bundlr): не JSON, а последовательность
 *   полей (signature type, signature 256b, owner 294b, target, anchor, num_tags, tag_bytes, tags, data).
 * - Поле "data" — произвольный payload в байтах. По умолчанию пустой Buffer; можно передать
 *   любой контент, например Buffer.from(JSON.stringify(activity), "utf8") для реального JSON Activity.
 * - Кристаллизатор не шифрует и не расшифровывает: он проверяет подпись Data Item и тег Upload-Id,
 *   затем упаковывает item в bundle и отправляет в Arweave. Кто подписывает — владелец ключа (в фикстуре
 *   своя RSA-пара); в проде — ключ кошелька пользователя.
 */

import crypto from "node:crypto";
import { deepHash } from "../../dist/publish/deep-hash.js";

const SIGNATURE_TYPE_RSA = 1;
const RSA_SIGNATURE_LENGTH = 256;
const RSA_OWNER_LENGTH = 294;

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

let cachedKeyPair = null;

function getKeyPair() {
  if (!cachedKeyPair) {
    cachedKeyPair = crypto.generateKeyPairSync("rsa", { modulusLength: 2048 });
  }
  return cachedKeyPair;
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
 * @returns {Promise<string>} base64 строки подписанного data item
 */
export async function createValidDataItem(uploadIdValue, data = Buffer.alloc(0)) {
  const pair = getKeyPair();
  const owner = pair.publicKey.export({ type: "spki", format: "der" });
  if (owner.length !== RSA_OWNER_LENGTH) {
    throw new Error(`Expected SPKI 294 bytes, got ${owner.length}`);
  }
  const target = Buffer.alloc(0);
  const anchor = Buffer.alloc(0);
  const tagBlock = buildTagBlock("Upload-Id", uploadIdValue);
  const numTags = 1;
  const numTagBytes = tagBlock.length;

  const signaturePlaceholder = Buffer.alloc(RSA_SIGNATURE_LENGTH);
  const raw = Buffer.alloc(
    2 + RSA_SIGNATURE_LENGTH + RSA_OWNER_LENGTH + 1 + 1 + 8 + 8 + numTagBytes + data.length
  );
  let off = 0;
  raw[off++] = SIGNATURE_TYPE_RSA & 0xff;
  raw[off++] = (SIGNATURE_TYPE_RSA >> 8) & 0xff;
  raw.set(signaturePlaceholder, off);
  off += RSA_SIGNATURE_LENGTH;
  raw.set(owner, off);
  off += RSA_OWNER_LENGTH;
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
  if (signature.length !== RSA_SIGNATURE_LENGTH) {
    throw new Error(`Expected signature 256 bytes, got ${signature.length}`);
  }
  raw.set(signature, 2);
  return raw.toString("base64");
}
