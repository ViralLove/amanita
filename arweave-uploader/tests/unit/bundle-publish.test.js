/**
 * Unit: publish/bundle-publish.js — bundleAndPublish.
 */

import { describe, it } from "node:test";
import assert from "node:assert";
import { bundleAndPublish } from "../../dist/publish/bundle-publish.js";

describe("publish/bundle-publish", () => {
  describe("bundleAndPublish", () => {
    it("экспортируется и является функцией", () => {
      assert.strictEqual(typeof bundleAndPublish, "function");
    });
    it("при невалидном arweaveClient возвращает объект с error", async () => {
      const fakeClient = { arweave: null, jwk: null };
      const minimalItem = Buffer.alloc(2 + 256 + 294 + 1 + 1 + 8 + 8, 0);
      minimalItem[0] = 1;
      minimalItem[1] = 0;
      const result = await bundleAndPublish(minimalItem, fakeClient);
      assert("error" in result);
      assert.strictEqual(typeof result.error, "string");
    });
  });
});
