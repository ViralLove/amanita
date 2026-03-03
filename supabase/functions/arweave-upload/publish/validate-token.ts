/**
 * Верификация upload_token (JWT RS256): подпись, exp, upload_id, payload_size <= max_bytes.
 * Публичный ключ из UPLOAD_TOKEN_JWT_PUBLIC_KEY (PEM или JWK JSON).
 */

let cachedPublicKey: CryptoKey | null = null;

/** Сброс кэша публичного ключа (для тестов при смене UPLOAD_TOKEN_JWT_PUBLIC_KEY). */
export function clearPublicKeyCache(): void {
  cachedPublicKey = null;
}

async function getPublicKey(): Promise<CryptoKey | null> {
  if (cachedPublicKey) return cachedPublicKey;
  const raw = Deno.env.get("UPLOAD_TOKEN_JWT_PUBLIC_KEY");
  if (!raw || !raw.trim()) return null;
  const trimmed = raw.trim();
  // В .env/Secrets ключ часто вставляют одной строкой с литеральными \n — приводим к переносам
  const normalized = trimmed.startsWith("{") ? trimmed : trimmed.replace(/\\n/g, "\n");
  try {
    if (normalized.startsWith("{")) {
      const jwk = JSON.parse(normalized) as JsonWebKey;
      cachedPublicKey = await crypto.subtle.importKey(
        "jwk",
        jwk,
        { name: "RSASSA-PKCS1-v1_5", hash: "SHA-256" },
        false,
        ["verify"]
      );
    } else {
      const pem = normalized
        .replace(/-----BEGIN PUBLIC KEY-----/g, "")
        .replace(/-----END PUBLIC KEY-----/g, "")
        .replace(/\s/g, "");
      const binary = Uint8Array.from(atob(pem), (c) => c.charCodeAt(0));
      cachedPublicKey = await crypto.subtle.importKey(
        "spki",
        binary,
        { name: "RSASSA-PKCS1-v1_5", hash: "SHA-256" },
        false,
        ["verify"]
      );
    }
    return cachedPublicKey;
  } catch {
    return null;
  }
}

function base64UrlDecode(s: string): Uint8Array {
  const base64 = s.replace(/-/g, "+").replace(/_/g, "/");
  const pad = base64.length % 4;
  const padded = pad ? base64 + "=".repeat(4 - pad) : base64;
  const binary = atob(padded);
  return new Uint8Array(binary.length).map((_, i) => binary.charCodeAt(i));
}

export async function verifyUploadToken(
  token: string,
  uploadId: string,
  payloadSize: number
): Promise<{ ok: true } | { ok: false; code: "token_invalid" }> {
  const key = await getPublicKey();
  if (!key) return { ok: false, code: "token_invalid" };

  const parts = token.split(".");
  if (parts.length !== 3) return { ok: false, code: "token_invalid" };

  const [headerB64, payloadB64, sigB64] = parts;
  const dataToVerify = new TextEncoder().encode(`${headerB64}.${payloadB64}`);
  let payloadBytes: Uint8Array;
  try {
    payloadBytes = base64UrlDecode(payloadB64);
  } catch {
    return { ok: false, code: "token_invalid" };
  }
  const payloadJson = new TextDecoder().decode(payloadBytes);
  let payload: { exp?: number; upload_id?: string; max_bytes?: number };
  try {
    payload = JSON.parse(payloadJson);
  } catch {
    return { ok: false, code: "token_invalid" };
  }

  const now = Math.floor(Date.now() / 1000);
  if (typeof payload.exp !== "number" || payload.exp < now)
    return { ok: false, code: "token_invalid" };
  if (payload.upload_id !== uploadId) return { ok: false, code: "token_invalid" };
  if (typeof payload.max_bytes !== "number" || payloadSize > payload.max_bytes)
    return { ok: false, code: "token_invalid" };

  let signature: Uint8Array;
  try {
    signature = base64UrlDecode(sigB64);
  } catch {
    return { ok: false, code: "token_invalid" };
  }

  const valid = await crypto.subtle.verify(
    { name: "RSASSA-PKCS1-v1_5" },
    key,
    new Uint8Array(signature),
    new Uint8Array(dataToVerify)
  );
  if (!valid) return { ok: false, code: "token_invalid" };
  return { ok: true };
}
