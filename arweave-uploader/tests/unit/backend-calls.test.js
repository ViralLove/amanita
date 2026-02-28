/**
 * Unit: publish/backend-calls.js — normalizeMockStatus, putStatus, postCallback.
 */

import { describe, it, beforeEach, afterEach } from "node:test";
import assert from "node:assert";
import { normalizeMockStatus, putStatus, postCallback } from "../../dist/publish/backend-calls.js";
import { setTestEnv, restoreEnv } from "../helpers/env.js";

describe("publish/backend-calls", () => {
  let savedEnv;

  beforeEach(() => {
    savedEnv = setTestEnv({ BACKEND_USE_MOCK: "true" });
  });
  afterEach(() => {
    restoreEnv(savedEnv);
  });

  describe("normalizeMockStatus", () => {
    it("экспортируется и является функцией", () => {
      assert.strictEqual(typeof normalizeMockStatus, "function");
    });
    it("200 → 200", () => assert.strictEqual(normalizeMockStatus(200), 200));
    it("404 → 404", () => assert.strictEqual(normalizeMockStatus(404), 404));
    it("409 → 409", () => assert.strictEqual(normalizeMockStatus(409), 409));
    it("строка '404' → 404", () => assert.strictEqual(normalizeMockStatus("404"), 404));
    it("любое другое значение → 200", () => assert.strictEqual(normalizeMockStatus(500), 200));
  });

  describe("putStatus", () => {
    it("экспортируется и является функцией", () => {
      assert.strictEqual(typeof putStatus, "function");
    });
    it("выполняется без исключения в mock-режиме", async () => {
      await assert.doesNotReject(() => putStatus("upload-1", "queued_for_publish"));
    });
  });

  describe("postCallback", () => {
    it("экспортируется и является функцией", () => {
      assert.strictEqual(typeof postCallback, "function");
    });
    it("выполняется без исключения в mock-режиме", async () => {
      await assert.doesNotReject(() =>
        postCallback("upload-1", "item-1", "tx-1", new Date().toISOString())
      );
    });
  });
});
