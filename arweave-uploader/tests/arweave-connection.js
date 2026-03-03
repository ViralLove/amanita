/**
 * Минимальный интеграционный тест: загрузка в Arweave в нашей среде.
 * Контент — одна строка "111.444.555.888.555.444.111" (минимальный объём для экономии).
 * Запуск: npm run test:arweave-connection (отдельно от юнит-тестов).
 * Требует: ARWEAVE_PRIVATE_KEY или ARWEAVE_PRIVATE_KEY_FILE в .env или окружении.
 * При отсутствии ключа — выход 0 (skip). 502 от шлюза Arweave — временная недоступность, не баг теста.
 */

import { readFileSync, existsSync } from "node:fs";
import { join } from "node:path";
import { loadConfig } from "../dist/config.js";
import { ArweaveClient } from "../dist/arweave-client.js";
import { bundleAndPublish } from "../dist/publish/bundle-publish.js";
import { createValidDataItem } from "./fixtures/valid-data-item.js";

const MINIMAL_PAYLOAD = "111.444.555.888.555.444.111";
const VERIFY_DELAY_MS = 3000;

function loadEnvIfPresent() {
  const path = join(process.cwd(), ".env");
  if (!existsSync(path)) return;
  const raw = readFileSync(path, "utf8");
  for (const line of raw.split("\n")) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith("#")) continue;
    const eq = trimmed.indexOf("=");
    if (eq <= 0) continue;
    const key = trimmed.slice(0, eq).trim();
    if (!key || process.env[key] !== undefined) continue;
    let value = trimmed.slice(eq + 1).trim();
    if ((value.startsWith('"') && value.endsWith('"')) || (value.startsWith("'") && value.endsWith("'")))
      value = value.slice(1, -1).replace(/\\n/g, "\n");
    process.env[key] = value;
  }
}

async function main() {
  loadEnvIfPresent();

  if (!process.env.ARWEAVE_PRIVATE_KEY && !process.env.ARWEAVE_PRIVATE_KEY_FILE) {
    console.log("Skip arweave-connection: ARWEAVE_PRIVATE_KEY or ARWEAVE_PRIVATE_KEY_FILE not set");
    process.exit(0);
  }

  let config;
  try {
    config = loadConfig();
  } catch (e) {
    console.error("Config failed:", e.message);
    process.exit(1);
  }

  const uploadId = `arweave-connection-${Date.now()}`;
  const dataBytes = Buffer.from(MINIMAL_PAYLOAD, "utf8");
  const signedDataItemBase64 = await createValidDataItem(uploadId, dataBytes);
  const signedDataItemBytes = Buffer.from(
    signedDataItemBase64.replace(/-/g, "+").replace(/_/g, "/"),
    "base64"
  );

  // Размер bundle как в bundle-publish: 32 (count) + 64 (index entry) + data item
  const bundleByteLength = 32 + 64 + signedDataItemBytes.length;
  const port = config.arweavePort;
  const portSuffix = (config.arweaveProtocol === "https" && port === 443) || (config.arweaveProtocol === "http" && port === 80) ? "" : `:${port}`;
  const baseUrl = `${config.arweaveProtocol}://${config.arweaveHost}${portSuffix}`;
  const getPriceUrl = `${baseUrl}/price/${bundleByteLength}`;

  console.error("Arweave config: protocol=%s host=%s port=%s", config.arweaveProtocol, config.arweaveHost, port);
  console.error("Exact request that can return 502: GET %s", getPriceUrl);

  const arweaveClient = new ArweaveClient(config);
  const result = await bundleAndPublish(signedDataItemBytes, arweaveClient);

  if (result.error) {
    console.error("Arweave upload failed:", result.error);
    console.error("(Request was: GET %s)", getPriceUrl);
    process.exit(1);
  }

  const arweaveUrl = `${config.arweaveProtocol}://${config.arweaveHost}/${result.bundleTxId}`;
  console.log("Upload OK. bundle_tx_id:", result.bundleTxId);
  console.log("Arweave URL:", arweaveUrl);

  const delayMs = parseInt(process.env.ARWEAVE_VERIFY_DELAY_MS || String(VERIFY_DELAY_MS), 10);
  await new Promise((r) => setTimeout(r, delayMs));

  let verifyRes;
  try {
    verifyRes = await fetch(arweaveUrl, { method: "GET" });
  } catch (err) {
    console.error("Verify fetch failed:", err.message);
    process.exit(1);
  }
  if (!verifyRes.ok) {
    console.error("Tx not found on gateway (HTTP " + verifyRes.status + "). URL:", arweaveUrl);
    process.exit(1);
  }

  console.log("Arweave connection test passed.");
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
