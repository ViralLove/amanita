/**
 * Unit: config.js — loadConfig (только при заданном ARWEAVE_PRIVATE_KEY).
 */

import { describe, it, beforeEach, afterEach } from "node:test";
import assert from "node:assert";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { join, dirname } from "node:path";
import { loadConfig } from "../../dist/config.js";
import { setTestEnv, restoreEnv } from "../helpers/env.js";

const __dirname = dirname(fileURLToPath(import.meta.url));
const fixtureJwk = JSON.parse(
  readFileSync(join(__dirname, "../fixtures/minimal-jwk.json"), "utf8")
);

describe("config", () => {
  let savedEnv;

  beforeEach(() => {
    savedEnv = setTestEnv({
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

  describe("loadConfig", () => {
    it("экспортируется и является функцией", () => {
      assert.strictEqual(typeof loadConfig, "function");
    });
    it("возвращает объект с port, arweaveProtocol, arweaveHost, arweavePort, jwk", () => {
      const c = loadConfig();
      assert.strictEqual(c.port, 3000);
      assert.strictEqual(c.arweaveProtocol, "https");
      assert.strictEqual(c.arweaveHost, "arweave.net");
      assert.strictEqual(c.arweavePort, 443);
      assert(c.jwk && typeof c.jwk === "object");
    });
    it("без ARWEAVE ключа бросает", () => {
      delete process.env.ARWEAVE_PRIVATE_KEY;
      delete process.env.ARWEAVE_PRIVATE_KEY_FILE;
      assert.throws(() => loadConfig(), /Missing Arweave key/);
    });
  });
});
