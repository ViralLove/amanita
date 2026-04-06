/**
 * WAL-POC-5: не логировать секреты (JWT, upload_token, raw signed payloads, длинный base64).
 * Используется для второго аргумента log() в index.js.
 */

const SENSITIVE_KEY_SUBSTRINGS = ["token", "secret", "password", "authorization", "privatekey", "signed_data", "signedtransaction", "payload_base64", "bearer"];

function looksLikeJwt(s) {
  return typeof s === "string" && /^eyJ[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+/.test(s);
}

function looksLikeBase64Blob(s) {
  if (typeof s !== "string" || s.length < 80) return false;
  return /^[A-Za-z0-9+/=\s]+$/.test(s.slice(0, 64));
}

/** Редактирует произвольное тело ответа (JSON-строка или текст) для одной строки лога. */
export function sanitizeHttpErrorText(text, maxLen = 400) {
  if (text == null || text === "") return text;
  let s = String(text);
  s = s.replace(/eyJ[a-zA-Z0-9_-]+\.[a-zA-Z0-9_.-]+/g, "[jwt]");
  s = s.replace(/"upload_token"\s*:\s*"[^"]*"/gi, '"upload_token":"[redacted]"');
  s = s.replace(/"signed_data_item"\s*:\s*"[^"]*"/gi, '"signed_data_item":"[redacted]"');
  if (s.length > maxLen) s = `${s.slice(0, maxLen)}…[truncated ${s.length} chars]`;
  return s;
}

function keyLooksSensitive(key) {
  const k = String(key).toLowerCase();
  return SENSITIVE_KEY_SUBSTRINGS.some((sub) => k.includes(sub));
}

/**
 * Рекурсивно копирует значение для JSON.stringify в лог, вырезая секреты.
 */
export function sanitizeForLog(value, depth = 0) {
  if (depth > 8) return "[max depth]";
  if (value === null || value === undefined) return value;
  const t = typeof value;
  if (t === "string") {
    if (looksLikeJwt(value)) return "[jwt redacted]";
    if (looksLikeBase64Blob(value)) return `[base64 ${value.length} chars]`;
    if (value.length > 800) return `${value.slice(0, 300)}…[truncated ${value.length} chars]`;
    return value;
  }
  if (t === "number" || t === "boolean") return value;
  if (t === "bigint") return value.toString();
  if (Array.isArray(value)) return value.map((v) => sanitizeForLog(v, depth + 1));
  if (t === "object") {
    const out = {};
    for (const [k, v] of Object.entries(value)) {
      if (keyLooksSensitive(k)) {
        out[k] = v != null && v !== "" ? "[redacted]" : v;
      } else if (k === "body" && typeof v === "string") {
        out[k] = sanitizeHttpErrorText(v, 500);
      } else {
        out[k] = sanitizeForLog(v, depth + 1);
      }
    }
    return out;
  }
  return String(value);
}
