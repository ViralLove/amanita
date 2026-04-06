/**
 * Хелпер для изоляции process.env в тестах.
 * Сохраняет и восстанавливает env для параллельной безопасности.
 */

const keysToSave = [
  "PORT",
  "ARWEAVE_PROTOCOL",
  "ARWEAVE_HOST",
  "ARWEAVE_PORT",
  "ARWEAVE_PRIVATE_KEY",
  "ARWEAVE_PRIVATE_KEY_FILE",
  "RELAY_AUTH_TOKEN",
  "BACKEND_USE_MOCK",
  "BACKEND_URL",
  "NODE_AUTH_TOKEN",
  "UPLOAD_TOKEN_JWT_PUBLIC_KEY",
];

export function saveEnv() {
  const saved = {};
  for (const k of keysToSave) {
    if (process.env[k] !== undefined) saved[k] = process.env[k];
  }
  return saved;
}

export function restoreEnv(saved) {
  for (const k of keysToSave) {
    if (saved[k] !== undefined) process.env[k] = saved[k];
    else delete process.env[k];
  }
}

export function setTestEnv(overrides = {}) {
  const saved = saveEnv();
  for (const [k, v] of Object.entries(overrides)) {
    if (v === undefined) delete process.env[k];
    else process.env[k] = String(v);
  }
  return saved;
}
