/**
 * Unit: publish/validate-token.js — verifyUploadToken.
 */

import { describe, it, afterEach } from "node:test";
import assert from "node:assert";
import { verifyUploadToken } from "../../dist/publish/validate-token.js";
import { setTestEnv, restoreEnv } from "../helpers/env.js";
import { getPublicKeyPem, createSignedToken } from "../fixtures/jwt-upload-token.js";

describe("publish/validate-token", () => {
  let savedEnv;

  afterEach(() => {
    if (savedEnv) restoreEnv(savedEnv);
  });

  describe("verifyUploadToken", () => {
    it("экспортируется и является функцией", () => {
      assert.strictEqual(typeof verifyUploadToken, "function");
    });
    it("без UPLOAD_TOKEN_JWT_PUBLIC_KEY возвращает ok: false, code token_invalid", async () => {
      savedEnv = setTestEnv({});
      delete process.env.UPLOAD_TOKEN_JWT_PUBLIC_KEY;
      const result = await verifyUploadToken("any.token.here", "upload-1", 100);
      assert.strictEqual(result.ok, false);
      assert.strictEqual(result.code, "token_invalid");
    });
    it("при пустом токене возвращает ok: false", async () => {
      savedEnv = setTestEnv({ UPLOAD_TOKEN_JWT_PUBLIC_KEY: "dummy" });
      const result = await verifyUploadToken("", "u1", 0);
      assert.strictEqual(result.ok, false);
    });
    it("при не-JWT (меньше 3 частей) возвращает ok: false", async () => {
      savedEnv = setTestEnv({ UPLOAD_TOKEN_JWT_PUBLIC_KEY: "{}" });
      const result = await verifyUploadToken("a.b", "u1", 0);
      assert.strictEqual(result.ok, false);
    });
    it("P0: валидный JWT (фикстура) и публичный ключ → ok: true", async () => {
      const uploadId = "test-upload-p0";
      const token = createSignedToken({ uploadId, maxBytes: 1024 });
      savedEnv = setTestEnv({ UPLOAD_TOKEN_JWT_PUBLIC_KEY: getPublicKeyPem() });
      const result = await verifyUploadToken(token, uploadId, 100);
      assert.strictEqual(result.ok, true);
    });
    it("P1: истёкший exp → ok: false", async () => {
      const token = createSignedToken({ uploadId: "x", exp: 1 });
      savedEnv = setTestEnv({ UPLOAD_TOKEN_JWT_PUBLIC_KEY: getPublicKeyPem() });
      const result = await verifyUploadToken(token, "x", 0);
      assert.strictEqual(result.ok, false);
      assert.strictEqual(result.code, "token_invalid");
    });
    it("P1: несовпадающий upload_id → ok: false", async () => {
      const token = createSignedToken({ uploadId: "id-a" });
      savedEnv = setTestEnv({ UPLOAD_TOKEN_JWT_PUBLIC_KEY: getPublicKeyPem() });
      const result = await verifyUploadToken(token, "id-b", 0);
      assert.strictEqual(result.ok, false);
      assert.strictEqual(result.code, "token_invalid");
    });
    it("P1: payloadSize > max_bytes → ok: false", async () => {
      const token = createSignedToken({ uploadId: "x", maxBytes: 10 });
      savedEnv = setTestEnv({ UPLOAD_TOKEN_JWT_PUBLIC_KEY: getPublicKeyPem() });
      const result = await verifyUploadToken(token, "x", 100);
      assert.strictEqual(result.ok, false);
      assert.strictEqual(result.code, "token_invalid");
    });
    it("P1: поддельная подпись → ok: false", async () => {
      const token = createSignedToken({ uploadId: "x" });
      const parts = token.split(".");
      const crypto = await import("node:crypto");
      const fakeSig = crypto.default.randomBytes(256);
      const b64 = fakeSig.toString("base64").replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
      const badToken = `${parts[0]}.${parts[1]}.${b64}`;
      savedEnv = setTestEnv({ UPLOAD_TOKEN_JWT_PUBLIC_KEY: getPublicKeyPem() });
      const result = await verifyUploadToken(badToken, "x", 0);
      assert.strictEqual(result.ok, false);
      assert.strictEqual(result.code, "token_invalid");
    });
  });
});
