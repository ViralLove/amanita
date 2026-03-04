#!/usr/bin/env node
/**
 * Real smoke: POST /v1/crystalize с валидным JWT и Data Item, проверка 200 и полей bundle_tx_id, arweave_url.
 *
 * Запуск: из корня arweave-uploader. Скрипт сам подхватывает .env из текущей директории.
 *   DEPLOYED_URL — URL задеплоенного uploader (по умолчанию Railway production).
 *   SMOKE_JWT_PRIVATE_KEY_FILE или SMOKE_JWT_PRIVATE_KEY_PEM — приватный ключ (RSA PEM) для подписи JWT.
 *     Должен быть из той же пары, что и UPLOAD_TOKEN_JWT_PUBLIC_KEY на деплое (иначе сервер вернёт 401).
 *     Пример: SMOKE_JWT_PRIVATE_KEY_FILE=../keys/amanita_111444555888555444111_private.pem (или ../bot/keys/...)
 */

import { readFileSync, existsSync } from "node:fs";
import { join, resolve } from "node:path";
import { createSignedTokenWithPrivateKey } from "../tests/fixtures/jwt-upload-token.js";
import { createValidDataItem } from "../tests/fixtures/valid-data-item.js";

function loadEnvIfPresent() {
  const path = join(process.cwd(), ".env");
  if (!existsSync(path)) return;
  let raw;
  try {
    raw = readFileSync(path, "utf8");
  } catch {
    return;
  }
  const lines = raw.split("\n");
  let i = 0;
  while (i < lines.length) {
    const trimmed = lines[i].trim();
    i += 1;
    if (!trimmed || trimmed.startsWith("#")) continue;
    const eq = trimmed.indexOf("=");
    if (eq <= 0) continue;
    const key = trimmed.slice(0, eq).trim();
    if (!key || process.env[key] !== undefined) continue;
    let value = trimmed.slice(eq + 1).trim();
    const quote = value.startsWith('"') ? '"' : value.startsWith("'") ? "'" : null;
    if (quote) {
      if (!value.endsWith(quote) || value.length === 1) {
        const acc = [value.slice(1)];
        while (i < lines.length) {
          const next = lines[i];
          i += 1;
          acc.push(next);
          if (next.endsWith(quote)) {
            acc[acc.length - 1] = next.slice(0, -1);
            break;
          }
        }
        value = acc.join("\n").replace(/\\n/g, "\n");
      } else {
        value = value.slice(1, -1).replace(/\\n/g, "\n");
      }
    }
    process.env[key] = value;
  }
}

function getBaseUrl() {
  const raw = process.env.DEPLOYED_URL;
  if (!raw) return "https://arweave-upload-production-888.up.railway.app";
  if (raw.startsWith("https://") || raw.startsWith("http://")) return raw.replace(/\/$/, "");
  return `https://${raw}`.replace(/\/$/, "");
}

function loadPrivateKey() {
  const pem = process.env.SMOKE_JWT_PRIVATE_KEY_PEM;
  if (pem) return pem;
  const pathRaw = process.env.SMOKE_JWT_PRIVATE_KEY_FILE;
  if (!pathRaw) {
    console.error("SMOKE_JWT_PRIVATE_KEY_PEM or SMOKE_JWT_PRIVATE_KEY_FILE required");
    process.exit(1);
  }
  const pathResolved = pathRaw.startsWith("/") ? pathRaw : resolve(process.cwd(), pathRaw);
  if (!existsSync(pathResolved)) {
    console.error("SMOKE_JWT_PRIVATE_KEY_FILE: file not found:", pathResolved);
    console.error("  (resolved from cwd:", process.cwd() + ", path from env:", pathRaw + ")");
    process.exit(1);
  }
  return readFileSync(pathResolved, "utf8");
}

function getKeySource() {
  if (process.env.SMOKE_JWT_PRIVATE_KEY_PEM) return "SMOKE_JWT_PRIVATE_KEY_PEM (inline)";
  const pathRaw = process.env.SMOKE_JWT_PRIVATE_KEY_FILE;
  if (pathRaw) {
    const resolved = pathRaw.startsWith("/") ? pathRaw : resolve(process.cwd(), pathRaw);
    return `SMOKE_JWT_PRIVATE_KEY_FILE=${resolved}`;
  }
  return "none";
}

async function main() {
  loadEnvIfPresent();
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

  console.log("smoke crystalize:", {
    url: `${baseUrl}/v1/crystalize`,
    uploadId,
    tokenLength: token?.length ?? 0,
    keySource: getKeySource(),
  });

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
    if (res.status === 401 && body.code === "token_invalid") {
      console.error(
        "Hint: 401 token_invalid — проверьте пару ключей: приватный (SMOKE_JWT_*) и публичный на сервере (UPLOAD_TOKEN_JWT_PUBLIC_KEY). Для локального теста задайте DEPLOYED_URL=http://localhost:3000 и запустите сервер с той же парой ключей (см. docs/local-run-and-smoke.md)."
      );
    }
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

  // Проверка, что tx реально появился в Arweave (нет фальшивого 200 при неудачной загрузке)
  const verifyUrl = process.env.SMOKE_VERIFY_ARWEAVE_URL || arweaveUrl;
  const verifyDelayMs = parseInt(process.env.SMOKE_VERIFY_DELAY_MS || "3000", 10);
  await new Promise((r) => setTimeout(r, verifyDelayMs));
  let verifyRes;
  try {
    verifyRes = await fetch(verifyUrl, { method: "GET" });
  } catch (err) {
    console.error("Verify tx on Arweave failed (fetch):", err.message);
    process.exit(1);
  }
  if (!verifyRes.ok) {
    console.error(
      "FAIL: tx not found on Arweave (HTTP " + verifyRes.status + "). URL: " + arweaveUrl
    );
    process.exit(1);
  }
  console.log("OK: tx verified on Arweave:", arweaveUrl);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
