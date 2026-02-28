/**
 * Unit: publish/validate-data-item.js — validateDataItem.
 */

import { describe, it } from "node:test";
import assert from "node:assert";
import { validateDataItem } from "../../dist/publish/validate-data-item.js";
import { createValidDataItem } from "../fixtures/valid-data-item.js";

describe("publish/validate-data-item", () => {
  describe("validateDataItem", () => {
    it("экспортируется и является функцией", () => {
      assert.strictEqual(typeof validateDataItem, "function");
    });
    it("при невалидном base64 возвращает ok: false, code signature_invalid", async () => {
      const result = await validateDataItem("not-valid-base64!!!", "upload-1");
      assert.strictEqual(result.ok, false);
      assert.strictEqual(result.code, "signature_invalid");
    });
    it("при слишком коротких данных возвращает ok: false", async () => {
      const short = Buffer.from("ab").toString("base64");
      const result = await validateDataItem(short, "upload-1");
      assert.strictEqual(result.ok, false);
    });
    it("P0: валидный Data Item (фикстура) и совпадающий uploadId → ok: true, itemId непустой", async () => {
      const uploadId = "p0-upload-id";
      const base64 = await createValidDataItem(uploadId);
      const result = await validateDataItem(base64, uploadId);
      assert.strictEqual(result.ok, true);
      assert.strictEqual(typeof result.itemId, "string");
      assert.ok(result.itemId.length > 0);
    });
    it("P0: валидный Data Item с тегом Upload-Id = A, вызов с uploadId B → ok: false, code signature_invalid", async () => {
      const base64 = await createValidDataItem("real-upload-id");
      const result = await validateDataItem(base64, "other-upload-id");
      assert.strictEqual(result.ok, false);
      assert.strictEqual(result.code, "signature_invalid");
    });
    it("P1: корректная структура и тег Upload-Id, неверная подпись → ok: false, code signature_invalid", async () => {
      const base64 = await createValidDataItem("p1-upload-id");
      const raw = Buffer.from(base64, "base64");
      raw[10] ^= 0xff;
      const badBase64 = raw.toString("base64");
      const result = await validateDataItem(badBase64, "p1-upload-id");
      assert.strictEqual(result.ok, false);
      assert.strictEqual(result.code, "signature_invalid");
    });
  });
});
