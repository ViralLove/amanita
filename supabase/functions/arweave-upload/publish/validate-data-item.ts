/**
 * Валидация Data Item (ANS-104): парсинг, проверка подписи RSA-PSS, тег Upload-Id.
 */

import { deepHash } from "./deep-hash.ts";

const SIGNATURE_TYPE_RSA = 1;
const RSA_SIGNATURE_LENGTH = 256;
/** Owner для RSA (type 1): SPKI RSA-2048 ~294 байт. */
const RSA_OWNER_LENGTH = 294;

function base64Decode(s: string): Uint8Array {
  const binary = atob(s.replace(/-/g, "+").replace(/_/g, "/"));
  const out = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) out[i] = binary.charCodeAt(i);
  return out;
}

function base64UrlEncode(data: Uint8Array): string {
  let binary = "";
  for (let i = 0; i < data.length; i++) binary += String.fromCharCode(data[i]);
  const base64 = btoa(binary);
  return base64.replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

function readUint64LE(buf: Uint8Array, off: number): number {
  const lo = buf[off]! | (buf[off + 1]! << 8) | (buf[off + 2]! << 16) | (buf[off + 3]! << 24);
  const hi = buf[off + 4]! | (buf[off + 5]! << 8) | (buf[off + 6]! << 16) | (buf[off + 7]! << 24);
  return lo + hi * 0x100000000;
}

/** Чтение Avro VInt (variable-length int) из buf начиная с off; возвращает { value, bytesRead }. */
function readVInt(buf: Uint8Array, off: number): { value: number; bytesRead: number } {
  let value = 0;
  let shift = 0;
  let bytesRead = 0;
  let b: number;
  do {
    if (off + bytesRead >= buf.length) return { value: 0, bytesRead };
    b = buf[off + bytesRead]!;
    bytesRead++;
    value |= (b & 0x7f) << shift;
    shift += 7;
  } while (b & 0x80);
  return { value, bytesRead };
}

/** ZigZag decode (VInt хранит zigzag). */
function zigzagDecode(n: number): number {
  return (n >>> 1) ^ -(n & 1);
}

/** Извлечь теги из Avro-массива тегов (блоки до count=0). */
function parseAvroTags(
  buf: Uint8Array,
  offset: number,
  limit: number
): { name: Uint8Array; value: Uint8Array }[] {
  const tags: { name: Uint8Array; value: Uint8Array }[] = [];
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
      const name = buf.slice(pos, pos + nameLen);
      pos += nameLen;
      const { value: valueLenZ, bytesRead: rv } = readVInt(buf, pos);
      pos += rv;
      const valueLen = zigzagDecode(valueLenZ);
      if (pos + valueLen > blockEnd) break;
      const value = buf.slice(pos, pos + valueLen);
      pos += valueLen;
      tags.push({ name, value });
    }
    if (count < 0) pos = blockEnd;
  }
  return tags;
}

/** Найти значение тега по имени (UTF-8). */
function getTagValue(
  tags: { name: Uint8Array; value: Uint8Array }[],
  tagName: string
): string | null {
  const want = new TextEncoder().encode(tagName);
  for (const t of tags) {
    if (t.name.length !== want.length) continue;
    let eq = true;
    for (let i = 0; i < want.length; i++) if (t.name[i] !== want[i]) { eq = false; break; }
    if (eq) return new TextDecoder().decode(t.value);
  }
  return null;
}

export async function validateDataItem(
  signedDataItemBase64: string,
  uploadId: string
): Promise<
  { ok: true; itemId?: string } | { ok: false; code: "signature_invalid" }
> {
  let raw: Uint8Array;
  try {
    raw = base64Decode(signedDataItemBase64);
  } catch {
    return { ok: false, code: "signature_invalid" };
  }
  if (raw.length < 2 + RSA_SIGNATURE_LENGTH + RSA_OWNER_LENGTH + 1 + 1 + 8 + 8) {
    return { ok: false, code: "signature_invalid" };
  }
  let off = 0;
  const sigType = raw[0]! | (raw[1]! << 8);
  if (sigType !== SIGNATURE_TYPE_RSA) return { ok: false, code: "signature_invalid" };
  off += 2;
  const signature = raw.slice(off, off + RSA_SIGNATURE_LENGTH);
  off += RSA_SIGNATURE_LENGTH;
  const owner = raw.slice(off, off + RSA_OWNER_LENGTH);
  off += RSA_OWNER_LENGTH;
  const targetPresent = raw[off++]!;
  let target: Uint8Array = new Uint8Array(0);
  if (targetPresent === 1) {
    if (off + 32 > raw.length) return { ok: false, code: "signature_invalid" };
    target = raw.slice(off, off + 32);
    off += 32;
  }
  const anchorPresent = raw[off++]!;
  let anchor: Uint8Array = new Uint8Array(0);
  if (anchorPresent === 1) {
    if (off + 32 > raw.length) return { ok: false, code: "signature_invalid" };
    anchor = raw.slice(off, off + 32);
    off += 32;
  }
  const numTags = readUint64LE(raw, off);
  off += 8;
  const numTagBytes = readUint64LE(raw, off);
  off += 8;
  if (off + numTagBytes > raw.length) return { ok: false, code: "signature_invalid" };
  const tagBytes = raw.slice(off, off + numTagBytes);
  off += numTagBytes;
  const data = raw.slice(off);

  const tags = parseAvroTags(tagBytes, 0, numTagBytes);
  const uploadIdTag = getTagValue(tags, "Upload-Id");
  if (uploadIdTag !== uploadId) return { ok: false, code: "signature_invalid" };

  const tagsForDeepHash: Uint8Array[][] = tags.map((t) => [t.name, t.value]);
  const deepHashInput: DeepHashChunk = [
    utf8("dataitem"),
    utf8("1"),
    owner,
    target,
    anchor,
    tagsForDeepHash,
    data,
  ];
  const message = await deepHash(deepHashInput);

  let publicKey: CryptoKey;
  try {
    publicKey = await crypto.subtle.importKey(
      "spki",
      owner,
      { name: "RSA-PSS", hash: "SHA-256" },
      false,
      ["verify"]
    );
  } catch {
    return { ok: false, code: "signature_invalid" };
  }

  const valid = await crypto.subtle.verify(
    { name: "RSA-PSS", saltLength: 32 },
    publicKey,
    signature,
    message
  );
  if (!valid) return { ok: false, code: "signature_invalid" };

  const idHash = await crypto.subtle.digest("SHA-256", signature);
  const itemId = base64UrlEncode(new Uint8Array(idHash));
  return { ok: true, itemId };
}

type DeepHashChunk = Uint8Array | DeepHashChunk[];
function utf8(s: string): Uint8Array {
  return new TextEncoder().encode(s);
}
