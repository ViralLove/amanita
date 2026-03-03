/**
 * Валидация upload_token (JWT RS256).
 * Claims: upload_id, max_bytes, exp. Публичный ключ из env UPLOAD_TOKEN_JWT_PUBLIC_KEY (PEM или JWK).
 */

import crypto from "node:crypto";

function base64UrlDecode(str) {
  const base64 = str.replace(/-/g, "+").replace(/_/g, "/");
  const pad = base64.length % 4;
  if (pad) return Buffer.from(base64 + "===".slice(0, 4 - pad), "base64");
  return Buffer.from(base64, "base64");
}

function normalizePem(pem) {
  if (typeof pem !== "string") return pem;
  return pem.replace(/\\n/g, "\n").trim();
}

function getPublicKey(keyFromEnv) {
  if (!keyFromEnv || typeof keyFromEnv !== "string") return null;
  const trimmed = keyFromEnv.trim();
  if (trimmed.startsWith("-----BEGIN")) {
    const normalized = normalizePem(trimmed);
    try {
      return crypto.createPublicKey({ key: normalized, format: "pem" });
    } catch (err) {
      console.error("UPLOAD_TOKEN_JWT_PUBLIC_KEY PEM decode failed:", err?.message || err);
      return null;
    }
  }
  if (trimmed.startsWith("{")) {
    try {
      const jwk = JSON.parse(trimmed);
      return crypto.createPublicKey({ key: jwk, format: "jwk" });
    } catch (err) {
      console.error("UPLOAD_TOKEN_JWT_PUBLIC_KEY JWK decode failed:", err?.message || err);
      return null;
    }
  }
  return null;
}

/**
 * @param {string} token - JWT string
 * @param {string} uploadId - ожидаемый upload_id из тела запроса
 * @param {number} payloadSize - размер payload в байтах
 * @returns {Promise<{ ok: true } | { ok: false, code: 'token_invalid' }>}
 */
async function verifyUploadToken(token, uploadId, payloadSize) {
  const publicKeyPemOrJwk = process.env.UPLOAD_TOKEN_JWT_PUBLIC_KEY;
  const publicKey = getPublicKey(publicKeyPemOrJwk);
  if (!publicKey) {
    return { ok: false, code: "token_invalid" };
  }

  if (!token || typeof token !== "string") {
    return { ok: false, code: "token_invalid" };
  }

  const parts = token.split(".");
  if (parts.length !== 3) {
    return { ok: false, code: "token_invalid" };
  }

  let payload;
  try {
    const payloadBuf = base64UrlDecode(parts[1]);
    payload = JSON.parse(payloadBuf.toString("utf8"));
  } catch {
    return { ok: false, code: "token_invalid" };
  }

  if (payload.exp != null) {
    const expSec = typeof payload.exp === "number" ? payload.exp : parseInt(payload.exp, 10);
    if (Number.isNaN(expSec) || expSec * 1000 < Date.now()) {
      return { ok: false, code: "token_invalid" };
    }
  }

  if (payload.upload_id !== uploadId) {
    return { ok: false, code: "token_invalid" };
  }

  const maxBytes = payload.max_bytes;
  if (maxBytes != null) {
    const max = typeof maxBytes === "number" ? maxBytes : parseInt(maxBytes, 10);
    if (Number.isNaN(max) || payloadSize > max) {
      return { ok: false, code: "token_invalid" };
    }
  }

  const signature = base64UrlDecode(parts[2]);
  const signedData = `${parts[0]}.${parts[1]}`;

  const ok = crypto.verify(
    "RSA-SHA256",
    Buffer.from(signedData, "utf8"),
    { key: publicKey },
    signature
  );

  if (!ok) {
    return { ok: false, code: "token_invalid" };
  }

  return { ok: true };
}

export { verifyUploadToken };
