/**
 * Подпись Arweave-транзакции через RSASSA-PSS (Web Crypto API).
 * Arweave: RSA-PSS, SHA-256, saltLength 32.
 * Transaction ID = base64url(sha256(owner || signature)); префикс "ar" для совместимости с проверками.
 */

export async function signArweaveTransaction(
  privateKey: JsonWebKey,
  signatureData: Uint8Array
): Promise<{ signature: Uint8Array; transactionId: string }> {
  const privateCryptoKey = await crypto.subtle.importKey(
    "jwk",
    privateKey,
    { name: "RSA-PSS", hash: "SHA-256" },
    false,
    ["sign"]
  );

  const signature = await crypto.subtle.sign(
    { name: "RSA-PSS", saltLength: 32 },
    privateCryptoKey,
    signatureData
  );

  const signatureBytes = new Uint8Array(signature);
  const owner = await extractOwnerFromJwk(privateKey);
  const transactionId = await computeTransactionId(owner, signatureBytes);

  return { signature: signatureBytes, transactionId };
}

async function extractOwnerFromJwk(jwk: JsonWebKey): Promise<Uint8Array> {
  const publicKey = await crypto.subtle.importKey(
    "jwk",
    { kty: jwk.kty, n: jwk.n, e: jwk.e },
    { name: "RSA-PSS", hash: "SHA-256" },
    true,
    []
  );
  const exported = await crypto.subtle.exportKey("spki", publicKey);
  return new Uint8Array(exported);
}

async function computeTransactionId(
  owner: Uint8Array,
  signature: Uint8Array
): Promise<string> {
  const combined = new Uint8Array(owner.length + signature.length);
  combined.set(owner, 0);
  combined.set(signature, owner.length);
  const hash = await crypto.subtle.digest("SHA-256", combined);
  const hashBytes = new Uint8Array(hash);
  return "ar" + base64UrlEncode(hashBytes);
}

function base64UrlEncode(data: Uint8Array): string {
  let binary = "";
  for (let i = 0; i < data.length; i++) binary += String.fromCharCode(data[i]);
  const base64 = btoa(binary);
  return base64.replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}
