import { assertEquals } from "https://deno.land/std@0.168.0/testing/asserts.ts";
import { validateDataItem } from "../publish/validate-data-item.ts";
import { deepHash } from "../publish/deep-hash.ts";

/** Zigzag encode (n >= 0 -> n << 1). */
function zigzagEncode(n: number): number {
  return (n << 1) ^ (n >> 31);
}

/** Avro VInt: write zigzag-encoded int, return bytes. */
function writeVIntZigzag(n: number): number[] {
  const z = zigzagEncode(n);
  const bytes: number[] = [];
  let x = z;
  do {
    bytes.push(x & 0x7f);
    x >>>= 7;
  } while (x);
  for (let i = 0; i < bytes.length - 1; i++) bytes[i]! |= 0x80;
  return bytes;
}

function writeUint64LE(n: number): number[] {
  const arr: number[] = [];
  for (let i = 0; i < 8; i++) {
    arr.push(n & 0xff);
    n = Math.floor(n / 256);
  }
  return arr;
}

/** Собрать валидный Data Item (ANS-104) с одним тегом Upload-Id и подписью. */
async function buildValidDataItem(
  uploadId: string,
  keyPair: CryptoKeyPair
): Promise<Uint8Array> {
  let owner = new Uint8Array(
    await crypto.subtle.exportKey("spki", keyPair.publicKey)
  );
  if (owner.length < 294) {
    const padded = new Uint8Array(294);
    padded.set(owner);
    owner = padded;
  } else if (owner.length > 294) {
    owner = owner.subarray(0, 294);
  }
  const data = new Uint8Array(0);
  const target = new Uint8Array(0);
  const anchor = new Uint8Array(0);

  const tagName = new TextEncoder().encode("Upload-Id");
  const tagValue = new TextEncoder().encode(uploadId);
  const tagBytes: number[] = [];
  tagBytes.push(...writeVIntZigzag(1));
  tagBytes.push(...writeVIntZigzag(tagName.length), ...tagName);
  tagBytes.push(...writeVIntZigzag(tagValue.length), ...tagValue);
  tagBytes.push(...writeVIntZigzag(0));
  const tagBytesArr = new Uint8Array(tagBytes);

  const tagsForDeepHash: Uint8Array[][] = [[tagName, tagValue]];
  const deepHashInput = [
    new TextEncoder().encode("dataitem"),
    new TextEncoder().encode("1"),
    owner,
    target,
    anchor,
    tagsForDeepHash,
    data,
  ];
  const message = await deepHash(deepHashInput);

  const signature = new Uint8Array(
    await crypto.subtle.sign(
      { name: "RSA-PSS", saltLength: 32 },
      keyPair.privateKey,
      message
    )
  );

  const out: number[] = [];
  out.push(1, 0);
  for (let i = 0; i < signature.length; i++) out.push(signature[i]!);
  for (let i = 0; i < owner.length; i++) out.push(owner[i]!);
  out.push(0, 0);
  out.push(...writeUint64LE(1), ...writeUint64LE(tagBytesArr.length));
  for (let i = 0; i < tagBytesArr.length; i++) out.push(tagBytesArr[i]!);
  for (let i = 0; i < data.length; i++) out.push(data[i]!);
  return new Uint8Array(out);
}

function base64Encode(bytes: Uint8Array): string {
  let binary = "";
  for (let i = 0; i < bytes.length; i++) binary += String.fromCharCode(bytes[i]!);
  return btoa(binary);
}

Deno.test("validateDataItem: valid item with Upload-Id returns ok true and itemId", async () => {
  const keyPair = await crypto.subtle.generateKey(
    {
      name: "RSA-PSS",
      modulusLength: 2048,
      publicExponent: new Uint8Array([1, 0, 1]),
      hash: "SHA-256",
    },
    true,
    ["sign", "verify"]
  );

  const uploadId = "test-upload-123";
  const itemBytes = await buildValidDataItem(uploadId, keyPair);
  const b64 = base64Encode(itemBytes);
  const result = await validateDataItem(b64, uploadId);

  assertEquals(result.ok, true);
  if (result.ok) {
    assertEquals(typeof result.itemId, "string");
    assertEquals(result.itemId!.length > 0, true);
  }
});

Deno.test("validateDataItem: wrong Upload-Id returns signature_invalid", async () => {
  const keyPair = await crypto.subtle.generateKey(
    {
      name: "RSA-PSS",
      modulusLength: 2048,
      publicExponent: new Uint8Array([1, 0, 1]),
      hash: "SHA-256",
    },
    true,
    ["sign", "verify"]
  );

  const itemBytes = await buildValidDataItem("upload-a", keyPair);
  const b64 = base64Encode(itemBytes);
  const result = await validateDataItem(b64, "upload-b");

  assertEquals(result, { ok: false, code: "signature_invalid" });
});

Deno.test("validateDataItem: invalid base64 returns signature_invalid", async () => {
  const result = await validateDataItem("not-valid-base64!!!", "any");
  assertEquals(result, { ok: false, code: "signature_invalid" });
});
