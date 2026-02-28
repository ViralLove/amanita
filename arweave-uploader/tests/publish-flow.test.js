/**
 * Сводные тесты POST /v1/crystalize с моками (BACKEND_USE_MOCK=true).
 * Запуск: из корня arweave-uploader задать ARWEAVE_PRIVATE_KEY (или ARWEAVE_PRIVATE_KEY_FILE),
 * затем: node tests/publish-flow.test.js
 * Или: BACKEND_USE_MOCK=true node tests/publish-flow.test.js
 */

import { loadConfig } from "../dist/config.js";
import { ArweaveClient } from "../dist/arweave-client.js";
import { buildApp } from "../dist/server.js";
import { getPublicKeyPem, createSignedToken } from "./fixtures/jwt-upload-token.js";

const BACKEND_USE_MOCK = "true";

function run(name, fn) {
  return fn()
    .then(() => console.log(`  ok: ${name}`))
    .catch((err) => {
      console.error(`  fail: ${name}`, err.message);
      throw err;
    });
}

async function main() {
  process.env.BACKEND_USE_MOCK = BACKEND_USE_MOCK;

  let config;
  try {
    config = loadConfig();
  } catch (e) {
    console.log("Skip publish tests: ARWEAVE_PRIVATE_KEY or ARWEAVE_PRIVATE_KEY_FILE required:", e.message);
    process.exit(0);
  }

  const arweaveClient = new ArweaveClient(config);
  const app = buildApp({ config, arweaveClient });

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
    process.env.UPLOAD_TOKEN_JWT_PUBLIC_KEY = getPublicKeyPem();
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

  console.log("Publish flow tests passed.");
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
