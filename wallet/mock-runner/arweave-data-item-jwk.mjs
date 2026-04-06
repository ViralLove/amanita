/**
 * ANS-104 Data Item подпись RSA-PSS тем же JWK, что у Arweave-кошелька.
 * Логика совместима с arweave-uploader/tests/fixtures/valid-data-item.js,
 * но owner/signature строятся из импортированного JWK (не сгенерированная пара).
 */

import fs from "node:fs";
import crypto from "node:crypto";
import { deepHash } from "../../arweave-uploader/dist/publish/deep-hash.js";

const SIGNATURE_TYPE_RSA = 1;

/**
 * Максимальная длина DER SPKI для типичного RSA-4096 (диагностика JWK vs uploader).
 * Реальная длина берётся из `publicKey.export` — см. `getRsaSpkiDerLengthFromJwk`.
 */
export const UPLOADER_COMPATIBLE_SPKI_BYTES_MAX = 550;

/** Типичные длины DER SPKI (RSA 2048 / 3072 / 4096), которые принимает validate-data-item на uploader. */
export const UPLOADER_SUPPORTED_RSA_SPKI_DER_LENGTHS = [294, 422, 550];

/**
 * Длина DER SPKI публичного ключа из JWK (диагностика 2048 vs 4096 до crystalize).
 * @param {object} jwk
 * @returns {number}
 */
export function getRsaSpkiDerLengthFromJwk(jwk) {
  const privateKey = crypto.createPrivateKey({ key: jwk, format: "jwk" });
  const publicKey = crypto.createPublicKey(privateKey);
  return publicKey.export({ type: "spki", format: "der" }).length;
}

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
 * Загрузка JWK: приоритет как в arweave-uploader (env > file).
 * @returns {object|null} распарсенный JWK или null
 */
export function loadWalletMockArweaveJwk() {
  const keyJson = process.env.WALLET_MOCK_ARWEAVE_PRIVATE_KEY;
  if (keyJson && String(keyJson).trim()) {
    try {
      return JSON.parse(keyJson);
    } catch (e) {
      throw new Error(`Failed to parse WALLET_MOCK_ARWEAVE_PRIVATE_KEY: ${e.message}`);
    }
  }
  const filePath = process.env.WALLET_MOCK_ARWEAVE_PRIVATE_KEY_FILE;
  if (filePath && String(filePath).trim()) {
    try {
      const content = fs.readFileSync(filePath, "utf8");
      return JSON.parse(content);
    } catch (e) {
      throw new Error(`Failed to read WALLET_MOCK_ARWEAVE_PRIVATE_KEY_FILE: ${e.message}`);
    }
  }
  return null;
}

/**
 * Подписанный Data Item (base64) для POST /v1/crystalize.
 * @param {object} jwk — RSA private JWK (Arweave wallet)
 * @param {string} uploadIdValue — тег Upload-Id
 * @param {Buffer} [data] — поле data (payload из sign-payload)
 * @returns {Promise<string>}
 */
export async function createSignedDataItemFromJwk(jwk, uploadIdValue, data = Buffer.alloc(0)) {
  const privateKey = crypto.createPrivateKey({ key: jwk, format: "jwk" });
  const publicKey = crypto.createPublicKey(privateKey);
  const owner = publicKey.export({ type: "spki", format: "der" });
  const details = publicKey.asymmetricKeyDetails;
  const modulusBits = details?.modulusLength;
  const sigLen = modulusBits ? modulusBits / 8 : null;
  if (sigLen == null || !Number.isFinite(sigLen)) {
    throw new Error("Could not determine RSA modulus length from JWK public key");
  }

  const target = Buffer.alloc(0);
  const anchor = Buffer.alloc(0);
  const tagBlock = buildTagBlock("Upload-Id", uploadIdValue);
  const numTags = 1;
  const numTagBytes = tagBlock.length;

  const signaturePlaceholder = Buffer.alloc(sigLen);
  const raw = Buffer.alloc(
    2 + sigLen + owner.length + 1 + 1 + 8 + 8 + numTagBytes + data.length
  );
  let off = 0;
  raw[off++] = SIGNATURE_TYPE_RSA & 0xff;
  raw[off++] = (SIGNATURE_TYPE_RSA >> 8) & 0xff;
  raw.set(signaturePlaceholder, off);
  off += sigLen;
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
    key: privateKey,
    padding: crypto.constants.RSA_PKCS1_PSS_PADDING,
    saltLength: 32,
  });
  if (signature.length !== sigLen) {
    throw new Error(`Expected signature ${sigLen} bytes, got ${signature.length}`);
  }
  raw.set(signature, 2);
  return raw.toString("base64");
}
