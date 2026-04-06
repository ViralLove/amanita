/**
 * Круговой тест: ephemeral RSA-2048 JWK → createSignedDataItemFromJwk → validateDataItem (uploader).
 * Не требует секретов; для CI / локальной проверки WAL-POC-7.
 */
import crypto from "node:crypto";
import { createSignedDataItemFromJwk } from "./arweave-data-item-jwk.mjs";
import { validateDataItem } from "../../arweave-uploader/dist/publish/validate-data-item.js";

const { privateKey } = crypto.generateKeyPairSync("rsa", {
  modulusLength: 2048,
  publicExponent: 0x10001,
});
const jwk = privateKey.export({ format: "jwk" });
const uploadId = "test-upload-roundtrip-001";
const payload = Buffer.from(JSON.stringify({ test: true }), "utf8");

const b64 = await createSignedDataItemFromJwk(jwk, uploadId, payload);
const v = await validateDataItem(b64, uploadId);
if (!v.ok) {
  console.error("validateDataItem failed", v);
  process.exit(1);
}
console.log("ok", { itemId: v.itemId });
