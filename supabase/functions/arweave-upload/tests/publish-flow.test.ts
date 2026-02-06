/**
 * Сводные тесты потока POST /edge/v1/publish (Phase 4.1).
 * Запуск: SUPABASE_TEST=1 deno test tests/publish-flow.test.ts --allow-env
 * (SUPABASE_TEST=1 отключает serve() при загрузке index.)
 */

import { assertEquals } from "https://deno.land/std@0.168.0/testing/asserts.ts";
import { handler } from "../index.ts";
import { clearPublicKeyCache } from "../publish/validate-token.ts";
import { deepHash } from "../publish/deep-hash.ts";

function base64UrlEncode(data: Uint8Array): string {
  let binary = "";
  for (let i = 0; i < data.length; i++) binary += String.fromCharCode(data[i]!);
  return btoa(binary).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

async function createTestJWT(
  payload: { exp: number; upload_id: string; max_bytes: number },
  privateKey: CryptoKey
): Promise<string> {
  const header = { alg: "RS256", typ: "JWT" };
  const headerB64 = base64UrlEncode(new TextEncoder().encode(JSON.stringify(header)));
  const payloadB64 = base64UrlEncode(new TextEncoder().encode(JSON.stringify(payload)));
  const data = new TextEncoder().encode(`${headerB64}.${payloadB64}`);
  const sig = await crypto.subtle.sign(
    { name: "RSASSA-PKCS1-v1_5" },
    privateKey,
    data
  );
  const sigB64 = base64UrlEncode(new Uint8Array(sig));
  return `${headerB64}.${payloadB64}.${sigB64}`;
}

function zigzagEncode(n: number): number {
  return (n << 1) ^ (n >> 31);
}
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

async function buildValidDataItem(uploadId: string, keyPair: CryptoKeyPair): Promise<Uint8Array> {
  let owner = new Uint8Array(await crypto.subtle.exportKey("spki", keyPair.publicKey));
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
  const message = await deepHash([
    new TextEncoder().encode("dataitem"),
    new TextEncoder().encode("1"),
    owner,
    target,
    anchor,
    tagsForDeepHash,
    data,
  ]);
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

type FetchCall = { url: string; method: string; body: string };
let fetchCalls: FetchCall[] = [];
const originalFetch = globalThis.fetch;

function mockFetch() {
  fetchCalls = [];
  globalThis.fetch = (input: string | URL | Request, init?: RequestInit) => {
    const url = typeof input === "string" ? input : input instanceof Request ? input.url : input.href;
    const method = (init?.method ?? (input instanceof Request ? input.method : "GET")) as string;
    const body = (init?.body ?? (input instanceof Request ? input.body : undefined)) as string | undefined;
    fetchCalls.push({ url: String(url), method, body: body ?? "" });
    return Promise.resolve(new Response(null, { status: 204 }));
  };
}
function restoreFetch() {
  globalThis.fetch = originalFetch;
}

function createPublishRequest(body: Record<string, unknown>, path = "https://x/functions/v1/arweave-upload/edge/v1/publish") {
  return new Request(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

Deno.test("publish flow: missing required field -> 400, no putStatus", async () => {
  mockFetch();
  try {
    const req = createPublishRequest({});
    const res = await handler(req);
    assertEquals(res.status, 400);
    const json = await res.json();
    assertEquals(json.code, "bad_request");
    assertEquals(fetchCalls.length, 0);
  } finally {
    restoreFetch();
  }
});

Deno.test("publish flow: invalid token -> 401, putStatus failed token_invalid", async () => {
  Deno.env.set("BACKEND_URL", "https://backend.test");
  Deno.env.set("EDGE_TO_BACKEND_SECRET", "test-secret");
  mockFetch();
  try {
    const req = createPublishRequest({
      upload_token: "invalid.jwt.here",
      upload_id: "upload-123",
      signed_data_item: "YQ==",
      payload_size: 0,
    });
    const res = await handler(req);
    assertEquals(res.status, 401);
    const json = await res.json();
    assertEquals(json.code, "token_invalid");
    const putFailed = fetchCalls.find(
      (c) => c.method === "PUT" && c.body.includes("failed") && c.body.includes("token_invalid")
    );
    assertEquals(!!putFailed, true);
  } finally {
    restoreFetch();
  }
});

Deno.test("publish flow: valid token + invalid data item -> 400 signature_invalid, putStatus failed", async () => {
  Deno.env.set("BACKEND_URL", "https://backend.test");
  Deno.env.set("EDGE_TO_BACKEND_SECRET", "test-secret");
  clearPublicKeyCache();
  const keyPair = await crypto.subtle.generateKey(
    {
      name: "RSASSA-PKCS1-v1_5",
      modulusLength: 2048,
      publicExponent: new Uint8Array([1, 0, 1]),
      hash: "SHA-256",
    },
    true,
    ["sign", "verify"]
  );
  const jwk = await crypto.subtle.exportKey("jwk", keyPair.publicKey);
  const publicJwk = JSON.stringify({ kty: jwk.kty, n: jwk.n, e: jwk.e });
  const prev = Deno.env.get("UPLOAD_TOKEN_JWT_PUBLIC_KEY");
  Deno.env.set("UPLOAD_TOKEN_JWT_PUBLIC_KEY", publicJwk);
  mockFetch();
  try {
    const exp = Math.floor(Date.now() / 1000) + 3600;
    const token = await createTestJWT(
      { exp, upload_id: "upload-123", max_bytes: 1024 },
      keyPair.privateKey
    );
    const req = createPublishRequest({
      upload_token: token,
      upload_id: "upload-123",
      signed_data_item: "YQ==",
      payload_size: 0,
    });
    const res = await handler(req);
    assertEquals(res.status, 400);
    const json = await res.json();
    assertEquals(json.code, "signature_invalid");
    const putFailed = fetchCalls.find(
      (c) => c.method === "PUT" && c.body.includes("failed") && c.body.includes("signature_invalid")
    );
    assertEquals(!!putFailed, true);
  } finally {
    restoreFetch();
    if (prev !== undefined) Deno.env.set("UPLOAD_TOKEN_JWT_PUBLIC_KEY", prev);
    else Deno.env.delete("UPLOAD_TOKEN_JWT_PUBLIC_KEY");
  }
});

Deno.test("publish flow: valid token + valid data item -> 200, putStatus queued_for_publish", async () => {
  clearPublicKeyCache();
  const jwtKeyPair = await crypto.subtle.generateKey(
    {
      name: "RSASSA-PKCS1-v1_5",
      modulusLength: 2048,
      publicExponent: new Uint8Array([1, 0, 1]),
      hash: "SHA-256",
    },
    true,
    ["sign", "verify"]
  );
  const pssKeyPair = await crypto.subtle.generateKey(
    {
      name: "RSA-PSS",
      modulusLength: 2048,
      publicExponent: new Uint8Array([1, 0, 1]),
      hash: "SHA-256",
    },
    true,
    ["sign", "verify"]
  );
  const jwk = await crypto.subtle.exportKey("jwk", jwtKeyPair.publicKey);
  Deno.env.set("UPLOAD_TOKEN_JWT_PUBLIC_KEY", JSON.stringify({ kty: jwk.kty, n: jwk.n, e: jwk.e }));
  Deno.env.set("BACKEND_URL", "https://backend.test");
  Deno.env.set("EDGE_TO_BACKEND_SECRET", "test-secret");
  mockFetch();
  try {
    const uploadId = "flow-test-upload-1";
    const itemBytes = await buildValidDataItem(uploadId, pssKeyPair);
    const signedDataItem = base64Encode(itemBytes);
    const exp = Math.floor(Date.now() / 1000) + 3600;
    const token = await createTestJWT(
      { exp, upload_id: uploadId, max_bytes: 1024 },
      jwtKeyPair.privateKey
    );
    const req = createPublishRequest({
      upload_token: token,
      upload_id: uploadId,
      signed_data_item: signedDataItem,
      payload_size: itemBytes.length,
    });
    const res = await handler(req);
    assertEquals(res.status, 200);
    const json = await res.json();
    assertEquals(json.ack, true);
    assertEquals(json.status, "queued_for_publish");
    const putQueued = fetchCalls.find(
      (c) => c.method === "PUT" && c.body.includes("queued_for_publish")
    );
    assertEquals(!!putQueued, true);
  } finally {
    restoreFetch();
  }
});
