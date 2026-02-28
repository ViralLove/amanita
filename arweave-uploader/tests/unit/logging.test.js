/**
 * Unit: logging.js — существование и базовая работоспособность.
 */

import { describe, it } from "node:test";
import assert from "node:assert";
import { sha256Hex, logInfo, logWarn, logError, errorToMessage } from "../../dist/logging.js";

describe("logging", () => {
  describe("sha256Hex", () => {
    it("экспортируется и является функцией", () => {
      assert.strictEqual(typeof sha256Hex, "function");
    });
    it("возвращает строку из 64 hex-символов для непустого ввода", () => {
      const out = sha256Hex("hello");
      assert.strictEqual(typeof out, "string");
      assert.strictEqual(out.length, 64);
      assert.match(out, /^[a-f0-9]{64}$/);
    });
    it("детерминирован: один и тот же ввод даёт один и тот же хеш", () => {
      assert.strictEqual(sha256Hex("x"), sha256Hex("x"));
    });
  });

  describe("logInfo", () => {
    it("экспортируется и является функцией", () => {
      assert.strictEqual(typeof logInfo, "function");
    });
    it("вызывается без исключения", () => {
      assert.doesNotThrow(() => logInfo("test.event", { key: "value" }));
    });
    it("P2: выводит в stdout одну строку JSON с level info, event и details", () => {
      const orig = console.log;
      let captured = null;
      console.log = (...args) => {
        captured = args;
      };
      try {
        logInfo("p2.event", { detail: "ok" });
        assert.ok(captured !== null);
        assert.strictEqual(captured.length, 1);
        const obj = JSON.parse(captured[0]);
        assert.strictEqual(obj.level, "info");
        assert.strictEqual(obj.event, "p2.event");
        assert.strictEqual(obj.detail, "ok");
      } finally {
        console.log = orig;
      }
    });
  });

  describe("logWarn", () => {
    it("экспортируется и является функцией", () => {
      assert.strictEqual(typeof logWarn, "function");
    });
  });

  describe("logError", () => {
    it("экспортируется и является функцией", () => {
      assert.strictEqual(typeof logError, "function");
    });
  });

  describe("errorToMessage", () => {
    it("экспортируется и является функцией", () => {
      assert.strictEqual(typeof errorToMessage, "function");
    });
    it("для Error возвращает message", () => {
      assert.strictEqual(errorToMessage(new Error("err")), "err");
    });
    it("для не-Error возвращает String(value)", () => {
      assert.strictEqual(errorToMessage("str"), "str");
    });
  });
});
