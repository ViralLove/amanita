/**
 * Unit: auth.js — isAuthorized.
 */

import { describe, it } from "node:test";
import assert from "node:assert";
import { isAuthorized } from "../../dist/auth.js";

describe("auth", () => {
  describe("isAuthorized", () => {
    it("экспортируется и является функцией", () => {
      assert.strictEqual(typeof isAuthorized, "function");
    });
    it("без relayAuthToken возвращает true (не проверяет)", () => {
      const reply = { code: () => reply, send: () => {} };
      const result = isAuthorized({ headers: {} }, reply, null);
      assert.strictEqual(result, true);
    });
    it("при заданном токене и верном Bearer возвращает true", () => {
      const reply = { code: () => reply, send: () => {} };
      const request = { headers: { authorization: "Bearer secret123" } };
      const result = isAuthorized(request, reply, "secret123");
      assert.strictEqual(result, true);
    });
    it("при неверном Bearer возвращает false и отправляет 401", () => {
      let sent;
      const reply = {
        code: (c) => {
          reply._code = c;
          return reply;
        },
        send: (body) => { sent = body; },
      };
      const request = { headers: { authorization: "Bearer wrong" } };
      const result = isAuthorized(request, reply, "secret123");
      assert.strictEqual(result, false);
      assert.strictEqual(reply._code, 401);
      assert.strictEqual(sent?.code, "UNAUTHORIZED");
    });
    it("при отсутствии Authorization возвращает false", () => {
      const reply = { code: () => reply, send: (body) => { reply._body = body; } };
      const result = isAuthorized({ headers: {} }, reply, "secret");
      assert.strictEqual(result, false);
      assert.strictEqual(reply._body?.code, "UNAUTHORIZED");
    });
  });
});
