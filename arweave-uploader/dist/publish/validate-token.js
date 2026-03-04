/**
 * Валидация upload_token (JWT RS256).
 * Claims: upload_id, max_bytes, exp. Публичный ключ из env UPLOAD_TOKEN_JWT_PUBLIC_KEY или UPLOAD_TOKEN_JWT_PUBLIC_KEY_FILE (PEM или JWK).
 */

import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";

function base64UrlDecode(str) {
  const base64 = str.replace(/-/g, "+").replace(/_/g, "/");
  const pad = base64.length % 4;
  if (pad) return Buffer.from(base64 + "===".slice(0, 4 - pad), "base64");
  return Buffer.from(base64, "base64");
}

function normalizePem(pem) {
  if (typeof pem !== "string") return pem;
  let out = pem
    .replace(/\\n/g, "\n")
    .replace(/\r\n/g, "\n")
    .replace(/\r/g, "\n")
    .trim();
  if (out.startsWith("-----BEGIN") && out.includes("-----END")) {
    out = out.replace(/\n\n+/g, "\n");
  }
  return out;
}

/**
 * Диагностика PEM: побайтово (коды символов), строки, тело между BEGIN/END.
 * 10=LF(\\n), 13=CR(\\r), 32=space, 92=backslash, 110='n' — для различения реальных \\n и буквальных \\n.
 */
function logPemDiagnostics(label, raw) {
  if (!raw || typeof raw !== "string") return;
  const len = raw.length;
  const lines = raw.split("\n");
  const hasCR = raw.includes("\r");
  const hasLiteralBackslashN =
    raw.includes("\\n") ||
    (raw.indexOf("\\") !== -1 && raw[raw.indexOf("\\") + 1] === "n");
  const first80Codes = Array.from(raw.slice(0, 80), (c) => c.charCodeAt(0));
  const last50Codes = len > 100 ? Array.from(raw.slice(-50), (c) => c.charCodeAt(0)) : [];

  console.error("[pem-diag] ---", label, "---");
  console.error("[pem-diag] length:", len);
  console.error("[pem-diag] hasCR:", hasCR, "| hasLiteralBackslashN (substring \\n):", raw.includes("\\n"));
  console.error("[pem-diag] first 80 char codes:", JSON.stringify(first80Codes));
  if (last50Codes.length) console.error("[pem-diag] last 50 char codes:", JSON.stringify(last50Codes));
  console.error("[pem-diag] line count:", lines.length, "| line lengths:", lines.map((l) => l.length));
  lines.forEach((l, i) => {
    if (l.length === 0) console.error("[pem-diag]   line[" + i + "] (empty)");
    else if (l.length <= 70) console.error("[pem-diag]   line[" + i + "] len=" + l.length + ":", l);
    else console.error("[pem-diag]   line[" + i + "] len=" + l.length + ":", l.slice(0, 50) + "...");
  });

  const beginIdx = raw.indexOf("-----BEGIN");
  const endIdx = raw.indexOf("-----END");
  if (beginIdx !== -1 && endIdx !== -1 && endIdx > beginIdx) {
    const body = raw.slice(beginIdx, endIdx + "-----END PUBLIC KEY-----".length);
    const inner = raw.slice(raw.indexOf("\n", beginIdx) + 1, endIdx);
    const innerTrimmed = inner.replace(/\n/g, "").trim();
    console.error("[pem-diag] body (BEGIN..END) length:", body.length);
    console.error("[pem-diag] inner (between header and END) length:", inner.length);
    console.error("[pem-diag] inner first 20 chars repr:", JSON.stringify(inner.slice(0, 20)));
    console.error("[pem-diag] inner last 20 chars repr:", JSON.stringify(inner.slice(-20)));
    console.error("[pem-diag] inner trimmed (base64 only) length:", innerTrimmed.length);
    console.error("[pem-diag] inner starts with newline:", inner.length > 0 && inner[0] === "\n");
    console.error("[pem-diag] inner has empty lines:", inner.split("\n").some((l) => l.length === 0));
  }
  console.error("[pem-diag] --- end", label, "---");
}

function loadPublicKeyRaw() {
  let raw = process.env.UPLOAD_TOKEN_JWT_PUBLIC_KEY;
  if (raw && typeof raw === "string" && raw.trim()) {
    raw = raw.trim();
    logPemDiagnostics("UPLOAD_TOKEN_JWT_PUBLIC_KEY (raw)", raw);
    return raw;
  }
  const filePath = process.env.UPLOAD_TOKEN_JWT_PUBLIC_KEY_FILE;
  if (!filePath || typeof filePath !== "string") return null;
  const resolved = path.isAbsolute(filePath) ? filePath : path.resolve(process.cwd(), filePath);
  try {
    raw = fs.readFileSync(resolved, "utf8").trim();
    logPemDiagnostics("UPLOAD_TOKEN_JWT_PUBLIC_KEY_FILE (raw)", raw);
    return raw;
  } catch (err) {
    console.error("UPLOAD_TOKEN_JWT_PUBLIC_KEY_FILE read failed:", resolved, err?.message || err);
    return null;
  }
}

function getPublicKey(keyFromEnv) {
  if (!keyFromEnv || typeof keyFromEnv !== "string") return null;
  const trimmed = keyFromEnv.trim();
  if (trimmed.startsWith("-----BEGIN")) {
    const normalized = normalizePem(trimmed);
    logPemDiagnostics("PEM after normalizePem", normalized);
    try {
      return crypto.createPublicKey({ key: normalized, format: "pem" });
    } catch (err) {
      console.error("UPLOAD_TOKEN_JWT_PUBLIC_KEY PEM decode failed:", err?.message || err);
      console.error("[pem-diag] on decode failure: normalized length:", normalized.length);
      console.error("[pem-diag] on decode failure: endsWith END?:", normalized.trimEnd().endsWith("-----END PUBLIC KEY-----"));
      console.error("[pem-diag] on decode failure: first 30 char codes:", JSON.stringify(Array.from(normalized.slice(0, 30), (c) => c.charCodeAt(0))));
      console.error("[pem-diag] on decode failure: last 30 char codes:", JSON.stringify(Array.from(normalized.slice(-30), (c) => c.charCodeAt(0))));
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
 * @returns {Promise<{ ok: true } | { ok: false, code: 'token_invalid', reason?: string }>}
 */
async function verifyUploadToken(token, uploadId, payloadSize) {
  const publicKeyPemOrJwk = loadPublicKeyRaw();
  const publicKey = getPublicKey(publicKeyPemOrJwk);
  if (!publicKey) {
    return { ok: false, code: "token_invalid", reason: "no_public_key" };
  }

  if (!token || typeof token !== "string") {
    return { ok: false, code: "token_invalid", reason: "token_empty" };
  }

  const parts = token.split(".");
  if (parts.length !== 3) {
    return { ok: false, code: "token_invalid", reason: "token_not_three_parts" };
  }

  let payload;
  try {
    const payloadBuf = base64UrlDecode(parts[1]);
    payload = JSON.parse(payloadBuf.toString("utf8"));
  } catch {
    return { ok: false, code: "token_invalid", reason: "payload_decode_failed" };
  }

  if (payload.exp != null) {
    const expSec = typeof payload.exp === "number" ? payload.exp : parseInt(payload.exp, 10);
    if (Number.isNaN(expSec) || expSec * 1000 < Date.now()) {
      return { ok: false, code: "token_invalid", reason: "exp_expired" };
    }
  }

  if (payload.upload_id !== uploadId) {
    return { ok: false, code: "token_invalid", reason: "upload_id_mismatch" };
  }

  const maxBytes = payload.max_bytes;
  if (maxBytes != null) {
    const max = typeof maxBytes === "number" ? maxBytes : parseInt(maxBytes, 10);
    if (Number.isNaN(max) || payloadSize > max) {
      return { ok: false, code: "token_invalid", reason: "payload_size_exceeded" };
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
    return { ok: false, code: "token_invalid", reason: "signature_invalid" };
  }

  return { ok: true };
}

export { verifyUploadToken };
