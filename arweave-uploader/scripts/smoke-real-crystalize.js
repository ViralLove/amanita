#!/usr/bin/env node
/**
 * Real smoke: POST /v1/crystalize с валидным JWT и Data Item, проверка 200 и полей bundle_tx_id, arweave_url.
 * Запуск: из корня arweave-uploader, после загрузки .env с DEPLOYED_URL и SMOKE_JWT_PRIVATE_KEY_*.
 * На деплое должен быть UPLOAD_TOKEN_JWT_PUBLIC_KEY (публичный ключ от пары с этим приватным).
 */

import { readFileSync } from "node:fs";
import { createSignedTokenWithPrivateKey } from "../tests/fixtures/jwt-upload-token.js";
import { createValidDataItem } from "../tests/fixtures/valid-data-item.js";

function getBaseUrl() {
  const raw = process.env.DEPLOYED_URL;
  if (!raw) return "https://arweave-upload-production-888.up.railway.app";
  if (raw.startsWith("https://") || raw.startsWith("http://")) return raw.replace(/\/$/, "");
  return `https://${raw}`.replace(/\/$/, "");
}

function loadPrivateKey() {
  const pem = process.env.SMOKE_JWT_PRIVATE_KEY_PEM;
  if (pem) return pem;
  const path = process.env.SMOKE_JWT_PRIVATE_KEY_FILE;
  if (path) return readFileSync(path, "utf8");
  console.error("SMOKE_JWT_PRIVATE_KEY_PEM or SMOKE_JWT_PRIVATE_KEY_FILE required");
  process.exit(1);
}

async function main() {
  const baseUrl = getBaseUrl();
  const privateKeyPem = loadPrivateKey();
  const uploadId = `smoke-${Date.now()}`;
  const token = createSignedTokenWithPrivateKey(privateKeyPem, { uploadId, maxBytes: 1024 });
  const signedDataItem = await createValidDataItem(uploadId);
  const payload = {
    upload_id: uploadId,
    upload_token: token,
    signed_data_item: signedDataItem,
    payload_size: 0,
  };

  const url = `${baseUrl}/v1/crystalize`;
  let res;
  try {
    res = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
  } catch (err) {
    console.error("Request failed:", err.message);
    process.exit(1);
  }

  const body = await res.json().catch(() => ({}));
  if (res.status !== 200) {
    console.error("HTTP", res.status, body);
    process.exit(1);
  }

  const txId = body.bundle_tx_id;
  const arweaveUrl = body.arweave_url;
  if (typeof txId !== "string" || !txId) {
    console.error("Missing or invalid bundle_tx_id in response", body);
    process.exit(1);
  }
  if (typeof arweaveUrl !== "string" || !arweaveUrl.endsWith(txId)) {
    console.error("Missing or invalid arweave_url (must end with bundle_tx_id)", body);
    process.exit(1);
  }

  console.log("OK: 200, bundle_tx_id:", txId, "arweave_url:", arweaveUrl);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
