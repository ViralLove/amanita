/**
 * Фикстура для тестов verifyUploadToken: RSA-пара и генерация подписанного JWT (RS256).
 * Claims: upload_id, max_bytes, exp (опционально).
 */

import crypto from "node:crypto";

function base64UrlEncode(buf) {
  const b64 = Buffer.isBuffer(buf) ? buf.toString("base64") : Buffer.from(String(buf)).toString("base64");
  return b64.replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

let cachedKeyPair = null;

function getKeyPair() {
  if (!cachedKeyPair) {
    cachedKeyPair = crypto.generateKeyPairSync("rsa", { modulusLength: 2048 });
  }
  return cachedKeyPair;
}

/**
 * Публичный ключ в PEM для UPLOAD_TOKEN_JWT_PUBLIC_KEY.
 */
export function getPublicKeyPem() {
  const pair = getKeyPair();
  return pair.publicKey.export({ type: "spki", format: "pem" });
}

/**
 * Публичный ключ в JWK (объект) для UPLOAD_TOKEN_JWT_PUBLIC_KEY при передаче как JSON string.
 */
export function getPublicKeyJwk() {
  const pair = getKeyPair();
  const jwk = pair.publicKey.export({ format: "jwk" });
  return jwk;
}

/**
 * Создаёт подписанный JWT с claims upload_id, max_bytes, exp (опционально).
 * @param {object} opts
 * @param {string} opts.uploadId
 * @param {number} [opts.maxBytes=1024]
 * @param {number} [opts.exp] — Unix timestamp (секунды); если не задан, ставится далёкое будущее
 * @returns {string} JWT
 */
export function createSignedToken({ uploadId, maxBytes = 1024, exp }) {
  const pair = getKeyPair();
  const header = { alg: "RS256", typ: "JWT" };
  const expSec = exp ?? Math.floor(Date.now() / 1000) + 3600;
  const payload = { upload_id: uploadId, max_bytes: maxBytes, exp: expSec };
  const headerB64 = base64UrlEncode(Buffer.from(JSON.stringify(header)));
  const payloadB64 = base64UrlEncode(Buffer.from(JSON.stringify(payload)));
  const signedData = `${headerB64}.${payloadB64}`;
  const signature = crypto.createSign("RSA-SHA256").update(signedData).sign(pair.privateKey);
  return `${signedData}.${base64UrlEncode(signature)}`;
}
