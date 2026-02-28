/**
 * Unit: publish/deep-hash.js — deepHash.
 * Эталоны: sha256 — наша реализация (dist); referenceSha384 — референс arweave-js/Bundlr (проверка эталонов).
 */

import crypto from "node:crypto";
import { readFileSync } from "node:fs";
import { describe, it } from "node:test";
import assert from "node:assert";
import { deepHash } from "../../dist/publish/deep-hash.js";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const __dirname = dirname(fileURLToPath(import.meta.url));
const vectorsPath = join(__dirname, "../fixtures/deep-hash-vectors.json");
const vectors = JSON.parse(readFileSync(vectorsPath, "utf8"));

/** Deep-hash по структуре Arweave, с SHA-384 (референс arweave-js/Bundlr). Используется только для проверки эталонов. */
async function deepHashSha384(chunk) {
  const sha384 = (b) => crypto.createHash("sha384").update(b).digest();
  const utf8 = (s) => Buffer.from(s, "utf8");
  if (Buffer.isBuffer(chunk) && !Array.isArray(chunk)) {
    const tag = Buffer.concat([utf8("blob"), utf8(String(chunk.length))]);
    const tagHash = sha384(tag);
    const dataHash = sha384(chunk);
    return sha384(Buffer.concat([tagHash, dataHash]));
  }
  const list = chunk;
  const tag = Buffer.concat([utf8("list"), utf8(String(list.length))]);
  let acc = sha384(tag);
  for (const item of list) {
    const itemHash = await deepHashSha384(item);
    acc = sha384(Buffer.concat([acc, itemHash]));
  }
  return acc;
}

describe("publish/deep-hash", () => {
  describe("deepHash", () => {
    it("экспортируется и является функцией", () => {
      assert.strictEqual(typeof deepHash, "function");
    });
    it("для буфера возвращает Buffer длиной 32", async () => {
      const chunk = Buffer.from("hello");
      const out = await deepHash(chunk);
      assert(Buffer.isBuffer(out));
      assert.strictEqual(out.length, 32);
    });
    it("для массива возвращает Buffer длиной 32", async () => {
      const chunk = [Buffer.from("a"), Buffer.from("b")];
      const out = await deepHash(chunk);
      assert(Buffer.isBuffer(out));
      assert.strictEqual(out.length, 32);
    });
    it("детерминирован для одного и того же ввода", async () => {
      const chunk = Buffer.from("same");
      const a = await deepHash(chunk);
      const b = await deepHash(chunk);
      assert.deepStrictEqual(a, b);
    });
    it("P1: blob — эталонный хеш для 'hello' (SHA-256, наша реализация)", async () => {
      const blob = Buffer.from(vectors.sha256.blob.input, "base64");
      const out = await deepHash(blob);
      assert.strictEqual(out.toString("hex"), vectors.sha256.blob.expectedHex);
    });
    it("P1: list — эталонный хеш для ['a','b'] (SHA-256, наша реализация)", async () => {
      const list = vectors.sha256.list.input.map((b64) => Buffer.from(b64, "base64"));
      const out = await deepHash(list);
      assert.strictEqual(out.toString("hex"), vectors.sha256.list.expectedHex);
    });
    it("P1: referenceSha384 — эталоны совпадают с референсом (arweave-js/Bundlr)", async () => {
      const ref = vectors.referenceSha384;
      const blob = Buffer.from(ref.blob.input, "base64");
      const list = ref.list.input.map((b64) => Buffer.from(b64, "base64"));
      const blobHash = await deepHashSha384(blob);
      const listHash = await deepHashSha384(list);
      assert.strictEqual(blobHash.toString("hex"), ref.blob.expectedHex);
      assert.strictEqual(listHash.toString("hex"), ref.list.expectedHex);
    });
  });
});
