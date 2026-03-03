/**
 * Unit: server.js — buildApp (существование и маршруты).
 */

import { describe, it, beforeEach, afterEach } from "node:test";
import assert from "node:assert";
import { buildApp, createMockPublish } from "../../dist/server.js";
import { setTestEnv, restoreEnv } from "../helpers/env.js";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { join, dirname } from "node:path";
import { getPublicKeyPem, createSignedToken } from "../fixtures/jwt-upload-token.js";
import { createValidDataItem } from "../fixtures/valid-data-item.js";

const __dirname = dirname(fileURLToPath(import.meta.url));
const fixtureJwk = JSON.parse(
  readFileSync(join(__dirname, "../fixtures/minimal-jwk.json"), "utf8")
);

describe("server", () => {
  let savedEnv;

  beforeEach(() => {
    savedEnv = setTestEnv({
      BACKEND_USE_MOCK: "true",
      PORT: "3000",
      ARWEAVE_PROTOCOL: "https",
      ARWEAVE_HOST: "arweave.net",
      ARWEAVE_PORT: "443",
      ARWEAVE_PRIVATE_KEY: JSON.stringify(fixtureJwk),
    });
  });
  afterEach(() => {
    restoreEnv(savedEnv);
  });

  describe("buildApp", () => {
    it("экспортируется и является функцией", () => {
      assert.strictEqual(typeof buildApp, "function");
    });
    it("возвращает приложение с GET /health", async () => {
      const { loadConfig } = await import("../../dist/config.js");
      const { ArweaveClient } = await import("../../dist/arweave-client.js");
      const config = loadConfig();
      const app = buildApp({ config, arweaveClient: new ArweaveClient(config) });
      const res = await app.inject({ method: "GET", url: "/health" });
      assert.strictEqual(res.statusCode, 200);
      const body = JSON.parse(res.body);
      assert.strictEqual(body.ok, true);
      assert.strictEqual(body.service, "arweave-uploader");
    });
    it("поддерживает POST /v1/crystalize", async () => {
      const { loadConfig } = await import("../../dist/config.js");
      const { ArweaveClient } = await import("../../dist/arweave-client.js");
      const config = loadConfig();
      const app = buildApp({ config, arweaveClient: new ArweaveClient(config) });
      const res = await app.inject({
        method: "POST",
        url: "/v1/crystalize",
        payload: {},
      });
      assert(res.statusCode === 400 || res.statusCode === 401);
    });

    it("POST /v1/crystalize без upload_id возвращает 400 и code missing_field", async () => {
      const { loadConfig } = await import("../../dist/config.js");
      const { ArweaveClient } = await import("../../dist/arweave-client.js");
      const config = loadConfig();
      const app = buildApp({ config, arweaveClient: new ArweaveClient(config) });
      const res = await app.inject({
        method: "POST",
        url: "/v1/crystalize",
        payload: { upload_token: "x", signed_data_item: "e30=", payload_size: 0 },
      });
      assert.strictEqual(res.statusCode, 400);
      const body = JSON.parse(res.body);
      assert.strictEqual(body.code, "missing_field");
    });

    it("POST /v1/crystalize без JWT public key возвращает 401 token_invalid", async () => {
      delete process.env.UPLOAD_TOKEN_JWT_PUBLIC_KEY;
      const { loadConfig } = await import("../../dist/config.js");
      const { ArweaveClient } = await import("../../dist/arweave-client.js");
      const config = loadConfig();
      const app = buildApp({ config, arweaveClient: new ArweaveClient(config) });
      const res = await app.inject({
        method: "POST",
        url: "/v1/crystalize",
        payload: {
          upload_id: "u1",
          upload_token: "a.b.c",
          signed_data_item: "e30=",
          payload_size: 0,
        },
      });
      assert.strictEqual(res.statusCode, 401);
      const body = JSON.parse(res.body);
      assert.strictEqual(body.code, "token_invalid");
    });

    it("P1: валидный JWT и невалидный/короткий signed_data_item → 400, code signature_invalid", async () => {
      process.env.UPLOAD_TOKEN_JWT_PUBLIC_KEY = getPublicKeyPem();
      const uploadId = "server-p1-upload";
      const token = createSignedToken({ uploadId, maxBytes: 1024 });
      const { loadConfig } = await import("../../dist/config.js");
      const { ArweaveClient } = await import("../../dist/arweave-client.js");
      const config = loadConfig();
      const app = buildApp({ config, arweaveClient: new ArweaveClient(config) });
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
      assert.strictEqual(res.statusCode, 400);
      const body = JSON.parse(res.body);
      assert.strictEqual(body.code, "signature_invalid");
    });

    it("POST /v1/crystalize success (mocked publish) returns 200 with bundle_tx_id and arweave_url", async () => {
      process.env.UPLOAD_TOKEN_JWT_PUBLIC_KEY = getPublicKeyPem();
      const uploadId = "server-200-upload";
      const token = createSignedToken({ uploadId, maxBytes: 1024 });
      const signedDataItem = await createValidDataItem(uploadId);
      const mockTxId = "test-tx-123";
      const mockPublish = () => Promise.resolve({ bundleTxId: mockTxId });
      const { loadConfig } = await import("../../dist/config.js");
      const { ArweaveClient } = await import("../../dist/arweave-client.js");
      const config = loadConfig();
      const app = buildApp({
        config,
        arweaveClient: new ArweaveClient(config),
        bundleAndPublish: mockPublish,
      });
      const res = await app.inject({
        method: "POST",
        url: "/v1/crystalize",
        payload: {
          upload_id: uploadId,
          upload_token: token,
          signed_data_item: signedDataItem,
          payload_size: 0,
        },
      });
      assert.strictEqual(res.statusCode, 200, res.body);
      const body = JSON.parse(res.body);
      assert.strictEqual(body.ack, true);
      assert.strictEqual(body.status, "queued_for_publish");
      assert.strictEqual(body.bundle_tx_id, mockTxId);
      assert.strictEqual(typeof body.arweave_url, "string");
      assert.ok(body.arweave_url.endsWith(mockTxId), "arweave_url must end with bundle_tx_id");
      assert.ok(
        body.arweave_url.startsWith(`${config.arweaveProtocol}://${config.arweaveHost}/`),
        "arweave_url must be built from config protocol and host"
      );
      console.log("  → arweave_url:", body.arweave_url);
    });

    it("POST /v1/crystalize with createMockPublish (USE_REAL_ARWEAVE=false style) returns 200, bundle_tx_id 43 chars base64url", async () => {
      process.env.UPLOAD_TOKEN_JWT_PUBLIC_KEY = getPublicKeyPem();
      const uploadId = "server-mock-format-upload";
      const token = createSignedToken({ uploadId, maxBytes: 1024 });
      const signedDataItem = await createValidDataItem(uploadId);
      const { loadConfig } = await import("../../dist/config.js");
      const { ArweaveClient } = await import("../../dist/arweave-client.js");
      const config = loadConfig();
      const app = buildApp({
        config,
        arweaveClient: new ArweaveClient(config),
        bundleAndPublish: createMockPublish(),
      });
      const res = await app.inject({
        method: "POST",
        url: "/v1/crystalize",
        payload: {
          upload_id: uploadId,
          upload_token: token,
          signed_data_item: signedDataItem,
          payload_size: 0,
        },
      });
      assert.strictEqual(res.statusCode, 200, res.body);
      const body = JSON.parse(res.body);
      assert.strictEqual(body.ack, true);
      assert.strictEqual(body.status, "queued_for_publish");
      assert.strictEqual(typeof body.bundle_tx_id, "string");
      assert.strictEqual(body.bundle_tx_id.length, 43, "bundle_tx_id must be 43 chars (Arweave tx id format)");
      assert.match(body.bundle_tx_id, /^[A-Za-z0-9_-]{43}$/, "bundle_tx_id must be base64url");
      assert.strictEqual(typeof body.arweave_url, "string");
      assert.ok(body.arweave_url.endsWith(body.bundle_tx_id), "arweave_url must end with bundle_tx_id");
      assert.ok(
        body.arweave_url.startsWith(`${config.arweaveProtocol}://${config.arweaveHost}/`),
        "arweave_url must be built from config"
      );
    });
  });
});
