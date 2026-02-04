import { assertEquals } from "https://deno.land/std@0.168.0/testing/asserts.ts";
import { verifyUploadToken } from "../publish/validate-token.ts";

function base64UrlEncode(data: Uint8Array): string {
  let binary = "";
  for (let i = 0; i < data.length; i++) binary += String.fromCharCode(data[i]);
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

Deno.test("verifyUploadToken: valid token returns ok true", async () => {
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
  const publicJwk = JSON.stringify({
    kty: jwk.kty,
    n: jwk.n,
    e: jwk.e,
  });
  const prev = Deno.env.get("UPLOAD_TOKEN_JWT_PUBLIC_KEY");
  Deno.env.set("UPLOAD_TOKEN_JWT_PUBLIC_KEY", publicJwk);

  try {
    const exp = Math.floor(Date.now() / 1000) + 3600;
    const token = await createTestJWT(
      { exp, upload_id: "test-upload-123", max_bytes: 1024 },
      keyPair.privateKey
    );
    const result = await verifyUploadToken(token, "test-upload-123", 100);
    assertEquals(result, { ok: true });
  } finally {
    if (prev !== undefined) Deno.env.set("UPLOAD_TOKEN_JWT_PUBLIC_KEY", prev);
    else Deno.env.delete("UPLOAD_TOKEN_JWT_PUBLIC_KEY");
  }
});

Deno.test("verifyUploadToken: wrong upload_id returns token_invalid", async () => {
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
  Deno.env.set(
    "UPLOAD_TOKEN_JWT_PUBLIC_KEY",
    JSON.stringify({ kty: jwk.kty, n: jwk.n, e: jwk.e })
  );

  const exp = Math.floor(Date.now() / 1000) + 3600;
  const token = await createTestJWT(
    { exp, upload_id: "upload-a", max_bytes: 1024 },
    keyPair.privateKey
  );
  const result = await verifyUploadToken(token, "upload-b", 100);
  assertEquals(result, { ok: false, code: "token_invalid" });
});

Deno.test("verifyUploadToken: payload_size > max_bytes returns token_invalid", async () => {
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
  Deno.env.set(
    "UPLOAD_TOKEN_JWT_PUBLIC_KEY",
    JSON.stringify({ kty: jwk.kty, n: jwk.n, e: jwk.e })
  );

  const exp = Math.floor(Date.now() / 1000) + 3600;
  const token = await createTestJWT(
    { exp, upload_id: "upload-1", max_bytes: 100 },
    keyPair.privateKey
  );
  const result = await verifyUploadToken(token, "upload-1", 200);
  assertEquals(result, { ok: false, code: "token_invalid" });
});

Deno.test("verifyUploadToken: expired token returns token_invalid", async () => {
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
  Deno.env.set(
    "UPLOAD_TOKEN_JWT_PUBLIC_KEY",
    JSON.stringify({ kty: jwk.kty, n: jwk.n, e: jwk.e })
  );

  const exp = Math.floor(Date.now() / 1000) - 60;
  const token = await createTestJWT(
    { exp, upload_id: "upload-1", max_bytes: 1024 },
    keyPair.privateKey
  );
  const result = await verifyUploadToken(token, "upload-1", 100);
  assertEquals(result, { ok: false, code: "token_invalid" });
});
