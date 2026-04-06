/**
 * Сводные тесты POST /v1/crystalize с моками (BACKEND_USE_MOCK=true).
 *
 * Как вызывать только этот floou (не unit):
 *   cd arweave-uploader
 *   npm run test:floou
 * или вручную:
 *   ARWEAVE_PRIVATE_KEY_FILE=tests/fixtures/minimal-jwk.json BACKEND_USE_MOCK=true node tests/publish-floou.test.js
 *
 * При успешном P0 выводится "  → arweave_url: <url>" и отдельной строкой "Arweave upload URL: <url>".
 *
 * Логирование со всех уровней: сервер пишет в stdout JSON-строки (logInfo/logWarn/logError).
 * Они выводятся автоматически при запуске скрипта. Чтобы удобнее читать:
 *   ... node tests/publish-floou.test.js 2>&1 | tee floou.log
 * или только логи сервера (каждая строка — JSON):
 *   ... node tests/publish-floou.test.js 2>&1 | grep '"level"'
 * Для красивого JSON по строкам (если есть jq): ... node tests/publish-floou.test.js 2>&1 | while IFS= read -r line; do echo "$line" | jq -c . 2>/dev/null || echo "$line"; done
 *
 * USE_REAL_ARWEAVE=true — реальная загрузка в Arweave (мок bundleAndPublish не подставляется, сервер реально шлёт в Arweave).
 * BACKEND_USE_MOCK — только для putStatus/postCallback к бекенду; на загрузку в Arweave не влияет.
 * USE_REAL_ACTIVITY=true — в Data Item кладётся реальный JSON из tests/fixtures/activity-example.json (полный цикл: JSON → байты → crystalize → Arweave).
 * .env подхватывается автоматически при запуске из cwd (loadEnvIfPresent). Если .env есть, его переменные переопределяют те, что заданы в npm-скрипте.
 * Реальные ключи JWT: UPLOAD_TOKEN_JWT_PRIVATE_KEY_FILE (приватный PEM), на uploader — UPLOAD_TOKEN_JWT_PUBLIC_KEY; для локального прогона — UPLOAD_TOKEN_JWT_PUBLIC_KEY_FILE.
 */

import { readFileSync, existsSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join, resolve } from "node:path";
import { loadConfig } from "../dist/config.js";

/**
 * Загружает .env из текущей рабочей директории (cwd) в process.env.
 * Формат: строки KEY=value; # — комментарий; пустые строки пропускаются.
 * Не перезаписывает переменные, уже заданные в окружении (npm-скрипт или shell),
 * чтобы при npm run test:floou сохранялся ARWEAVE_PRIVATE_KEY_FILE из скрипта, а из .env подтягивались USE_REAL_ARWEAVE и др.
 */
function loadEnvIfPresent() {
  const path = join(process.cwd(), ".env");
  if (!existsSync(path)) return;
  const raw = readFileSync(path, "utf8");
  for (const line of raw.split("\n")) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith("#")) continue;
    const eq = trimmed.indexOf("=");
    if (eq <= 0) continue;
    const key = trimmed.slice(0, eq).trim();
    if (!key || process.env[key] !== undefined) continue;
    let value = trimmed.slice(eq + 1).trim();
    if ((value.startsWith('"') && value.endsWith('"')) || (value.startsWith("'") && value.endsWith("'")))
      value = value.slice(1, -1).replace(/\\n/g, "\n");
    process.env[key] = value;
  }
}
loadEnvIfPresent();
if (!process.env.ARWEAVE_PRIVATE_KEY && !process.env.ARWEAVE_PRIVATE_KEY_FILE) {
  process.env.ARWEAVE_PRIVATE_KEY_FILE = "tests/fixtures/minimal-jwk.json";
}
import { ArweaveClient } from "../dist/arweave-client.js";
import { buildApp } from "../dist/server.js";
import { getPublicKeyPem, createSignedToken, createSignedTokenWithPrivateKey } from "./fixtures/jwt-upload-token.js";
import { createValidDataItem } from "./fixtures/valid-data-item.js";

const BACKEND_USE_MOCK = "true";

function run(name, fn) {
  return fn()
    .then(() => console.log(`  ok: ${name}`))
    .catch((err) => {
      console.error(`  fail: ${name}`, err.message);
      throw err;
    });
}

/** Модель тела POST /v1/crystalize по server.js: upload_id, upload_token, signed_data_item, payload_size */
function buildPositivePayload(uploadId, token, signedDataItem, payloadSize = 0) {
  return {
    upload_id: uploadId,
    upload_token: token,
    signed_data_item: signedDataItem,
    payload_size: payloadSize,
  };
}

async function main() {
  process.env.BACKEND_USE_MOCK = BACKEND_USE_MOCK;

  const useRealArweave = process.env.USE_REAL_ARWEAVE === "true" || process.env.USE_REAL_ARWEAVE === "1";

  const publicKeyPathRaw = process.env.UPLOAD_TOKEN_JWT_PUBLIC_KEY_FILE;
  const publicKeyPath = publicKeyPathRaw ? resolve(process.cwd(), publicKeyPathRaw) : null;
  if (publicKeyPath && existsSync(publicKeyPath)) {
    process.env.UPLOAD_TOKEN_JWT_PUBLIC_KEY = readFileSync(publicKeyPath, "utf8");
  }

  let config;
  try {
    config = loadConfig();
  } catch (e) {
    console.log("Skip publish tests: ARWEAVE_PRIVATE_KEY or ARWEAVE_PRIVATE_KEY_FILE required:", e.message);
    process.exit(0);
  }

  const arweaveClient = new ArweaveClient(config);
  const mockBundleAndPublish =
    !useRealArweave
      ? async (_signedDataItemBytes, _arweaveClient, _opts) => ({
          bundleTxId: "mock-bundle-tx-id-publish-flow",
        })
      : undefined;
  const app = buildApp({
    config,
    arweaveClient,
    bundleAndPublish: mockBundleAndPublish,
  });

  const uploadIdPositive = "flow-success-upload";
  let tokenPositive;
  const privateKeyPathRaw = process.env.UPLOAD_TOKEN_JWT_PRIVATE_KEY_FILE;
  const privateKeyPath = privateKeyPathRaw
    ? resolve(process.cwd(), privateKeyPathRaw)
    : null;
  const maxBytes = 64 * 1024;
  if (privateKeyPath && existsSync(privateKeyPath)) {
    try {
      const pem = readFileSync(privateKeyPath, "utf8");
      tokenPositive = createSignedTokenWithPrivateKey(pem, { uploadId: uploadIdPositive, maxBytes });
    } catch (e) {
      console.log("UPLOAD_TOKEN_JWT_PRIVATE_KEY_FILE read failed, using fixture JWT:", e.message);
      process.env.UPLOAD_TOKEN_JWT_PUBLIC_KEY = getPublicKeyPem();
      tokenPositive = createSignedToken({ uploadId: uploadIdPositive, maxBytes });
    }
  } else {
    if (privateKeyPathRaw)
      console.log("UPLOAD_TOKEN_JWT_PRIVATE_KEY_FILE not found, using fixture JWT:", privateKeyPath);
    process.env.UPLOAD_TOKEN_JWT_PUBLIC_KEY = getPublicKeyPem();
    tokenPositive = createSignedToken({ uploadId: uploadIdPositive, maxBytes });
  }

  const useRealActivity = process.env.USE_REAL_ACTIVITY === "true" || process.env.USE_REAL_ACTIVITY === "1";
  const __dirname = dirname(fileURLToPath(import.meta.url));
  const activityPath = join(__dirname, "fixtures", "activity-example.json");
  let dataBytes = Buffer.alloc(0);
  if (useRealActivity && existsSync(activityPath)) {
    const activity = JSON.parse(readFileSync(activityPath, "utf8"));
    dataBytes = Buffer.from(JSON.stringify(activity), "utf8");
    console.log("Using real Activity JSON in Data Item, size:", dataBytes.length);
  }
  const signedDataItemPositive = await createValidDataItem(uploadIdPositive, dataBytes);
  const positivePayload = buildPositivePayload(
    uploadIdPositive,
    tokenPositive,
    signedDataItemPositive,
    dataBytes.length
  );

  await run("400 on missing upload_id", async () => {
    const res = await app.inject({
      method: "POST",
      url: "/v1/crystalize",
      payload: { upload_token: "x", signed_data_item: "e30=", payload_size: 0 },
    });
    if (res.statusCode !== 400) throw new Error(`expected 400, got ${res.statusCode}`);
    const body = JSON.parse(res.body);
    if (body.code !== "missing_field") throw new Error(`expected code missing_field, got ${body.code}`);
  });

  await run("400 on missing upload_token", async () => {
    const res = await app.inject({
      method: "POST",
      url: "/v1/crystalize",
      payload: { upload_id: "u1", signed_data_item: "e30=", payload_size: 0 },
    });
    if (res.statusCode !== 400) throw new Error(`expected 400, got ${res.statusCode}`);
  });

  await run("400 on invalid payload_size (not number)", async () => {
    const res = await app.inject({
      method: "POST",
      url: "/v1/crystalize",
      payload: { upload_id: "u1", upload_token: "x", signed_data_item: "e30=", payload_size: "x" },
    });
    if (res.statusCode !== 400) throw new Error(`expected 400, got ${res.statusCode}`);
  });

  await run("401 on token_invalid (no UPLOAD_TOKEN_JWT_PUBLIC_KEY)", async () => {
    const prev = process.env.UPLOAD_TOKEN_JWT_PUBLIC_KEY;
    delete process.env.UPLOAD_TOKEN_JWT_PUBLIC_KEY;
    try {
      const res = await app.inject({
        method: "POST",
        url: "/v1/crystalize",
        payload: {
          upload_id: "u1",
          upload_token: "fake.jwt.token",
          signed_data_item: "e30=",
          payload_size: 0,
        },
      });
      if (res.statusCode !== 401) throw new Error(`expected 401, got ${res.statusCode}`);
      const body = JSON.parse(res.body);
      if (body.code !== "token_invalid") throw new Error(`expected code token_invalid, got ${body.code}`);
    } finally {
      if (prev !== undefined) process.env.UPLOAD_TOKEN_JWT_PUBLIC_KEY = prev;
    }
  });

  await run("P1: valid JWT + invalid signed_data_item → 400 signature_invalid", async () => {
    process.env.UPLOAD_TOKEN_JWT_PUBLIC_KEY = process.env.UPLOAD_TOKEN_JWT_PUBLIC_KEY || getPublicKeyPem();
    const uploadId = "flow-p1-upload";
    const token = createSignedToken({ uploadId, maxBytes: 1024 });
    const res = await app.inject({
      method: "POST",
      url: "/v1/crystalize",
      payload: {
        upload_id: uploadId,
        upload_token: token,
        signed_data_item: "e30=",
        payload_size: 0,
      },
    });
    if (res.statusCode !== 400) throw new Error(`expected 400, got ${res.statusCode}`);
    const body = JSON.parse(res.body);
    if (body.code !== "signature_invalid") throw new Error(`expected code signature_invalid, got ${body.code}`);
  });

  await run(
    useRealArweave
      ? "P0: positive crystalize (real Arweave) → 200"
      : "P0: positive crystalize (mocked publish) → 200",
    async () => {
      const res = await app.inject({
        method: "POST",
        url: "/v1/crystalize",
        payload: positivePayload,
      });
      if (res.statusCode !== 200) throw new Error(`expected 200, got ${res.statusCode}: ${res.body}`);
      const body = JSON.parse(res.body);
      if (body.ack !== true) throw new Error(`expected ack true, got ${body.ack}`);
      if (typeof body.status !== "string") throw new Error(`expected status string, got ${typeof body.status}`);
      if (body.bundle_tx_id == null) throw new Error(`expected bundle_tx_id, got ${body.bundle_tx_id}`);
      if (body.arweave_url == null) throw new Error(`expected arweave_url, got ${body.arweave_url}`);
      console.log("  → arweave_url:", body.arweave_url);
      console.log("");
      console.log("Arweave upload URL:", body.arweave_url);
      console.log("");
    }
  );

  console.log("Publish flow tests passed.");
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
