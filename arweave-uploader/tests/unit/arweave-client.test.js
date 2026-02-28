/**
 * Unit: arweave-client.js — ArweaveClient (существование и инициализация).
 */

import { describe, it } from "node:test";
import assert from "node:assert";
import { ArweaveClient } from "../../dist/arweave-client.js";

describe("arweave-client", () => {
  describe("ArweaveClient", () => {
    it("экспортируется как класс", () => {
      assert.strictEqual(typeof ArweaveClient, "function");
    });
    it("создаёт экземпляр с config с arweave и jwk", () => {
      const config = {
        arweaveProtocol: "https",
        arweaveHost: "arweave.net",
        arweavePort: 443,
        jwk: { kty: "RSA", n: "x", e: "AQAB" },
      };
      const client = new ArweaveClient(config);
      assert(client.arweave);
      assert.strictEqual(client.jwk, config.jwk);
    });
  });
});
