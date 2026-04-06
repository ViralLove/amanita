/**
 * Без сети: длины SPKI для RSA 2048 / 4096 входят в поддерживаемый набор uploader.
 */
import crypto from "node:crypto";
import assert from "node:assert/strict";
import {
  getRsaSpkiDerLengthFromJwk,
  UPLOADER_SUPPORTED_RSA_SPKI_DER_LENGTHS,
} from "./arweave-data-item-jwk.mjs";

const jwk2048 = crypto.generateKeyPairSync("rsa", { modulusLength: 2048 }).privateKey.export({
  format: "jwk",
});
const len2048 = getRsaSpkiDerLengthFromJwk(jwk2048);
assert.ok(UPLOADER_SUPPORTED_RSA_SPKI_DER_LENGTHS.includes(len2048), `2048 SPKI ${len2048}`);

const jwk4096 = crypto.generateKeyPairSync("rsa", { modulusLength: 4096 }).privateKey.export({
  format: "jwk",
});
const len4096 = getRsaSpkiDerLengthFromJwk(jwk4096);
assert.ok(UPLOADER_SUPPORTED_RSA_SPKI_DER_LENGTHS.includes(len4096), `4096 SPKI ${len4096}`);

console.log("ok jwk-spki-preflight", { len2048, len4096, supported: UPLOADER_SUPPORTED_RSA_SPKI_DER_LENGTHS });
