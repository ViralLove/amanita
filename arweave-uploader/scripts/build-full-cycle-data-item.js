#!/usr/bin/env node
/**
 * Строит подписанный ANS-104 Data Item с тегом Upload-Id для теста полного цикла (bot → crystalize).
 * Вывод: одна строка base64 в stdout (без переносов в середине).
 *
 * Использование (из корня arweave-uploader):
 *   node scripts/build-full-cycle-data-item.js <upload_id>
 *   node scripts/build-full-cycle-data-item.js <upload_id> <path-to-payload-file>
 *   node scripts/build-full-cycle-data-item.js <upload_id> -
 *     (payload из stdin)
 *
 * По умолчанию payload = {"title":"full-cycle-test"}.
 * Из bot-теста вызывается при заданном ARWEAVE_UPLOADER_DIR; см. bot/docs/tests/data-upload-integration-tests.md.
 */

import { readFileSync, existsSync } from "node:fs";
import { createValidDataItem } from "../tests/fixtures/valid-data-item.js";

const DEFAULT_PAYLOAD = Buffer.from('{"title":"full-cycle-test"}', "utf8");

async function main() {
  const uploadId = process.argv[2];
  if (!uploadId || !uploadId.trim()) {
    console.error("Usage: node scripts/build-full-cycle-data-item.js <upload_id> [payload-file|-]");
    process.exit(1);
  }

  let data = DEFAULT_PAYLOAD;
  const payloadArg = process.argv[3];
  if (payloadArg !== undefined) {
    if (payloadArg === "-") {
      const chunks = [];
      for await (const chunk of process.stdin) chunks.push(chunk);
      data = Buffer.concat(chunks);
    } else if (existsSync(payloadArg)) {
      data = readFileSync(payloadArg);
    } else {
      console.error(`Payload file not found: ${payloadArg}`);
      process.exit(1);
    }
  }

  try {
    const b64 = await createValidDataItem(uploadId.trim(), data);
    process.stdout.write(b64);
  } catch (err) {
    console.error(err.message || err);
    process.exit(1);
  }
}

main();
