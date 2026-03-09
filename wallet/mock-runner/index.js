#!/usr/bin/env node
/**
 * Wallet-mock runner (W6): опрос бота GET /v1/pending-sign-requests,
 * обработка sign_arweave (GET sign-payload → POST crystalize) и sign_contract (GET sign-request → POST submit).
 *
 * Конфиг: BOT_URL, USER_ID, POLL_INTERVAL_MS, ARWEAVE_SERVICE_URL (опционально).
 */

const BOT_URL = (process.env.BOT_URL || "http://localhost:8000").replace(/\/$/, "");
const USER_ID = process.env.USER_ID || "";
const POLL_INTERVAL_MS = parseInt(process.env.POLL_INTERVAL_MS || "2000", 10);
const ARWEAVE_SERVICE_URL = process.env.ARWEAVE_SERVICE_URL || "";

function log(msg, data = null) {
  const ts = new Date().toISOString();
  if (data != null) console.log(ts, msg, JSON.stringify(data));
  else console.log(ts, msg);
}

async function fetchJson(url, options = {}) {
  const res = await fetch(url, {
    ...options,
    headers: { "Content-Type": "application/json", "X-User-Id": USER_ID, ...options.headers },
  });
  const text = await res.text();
  let body;
  try {
    body = text ? JSON.parse(text) : {};
  } catch {
    body = {};
  }
  if (!res.ok) throw new Error(`HTTP ${res.status}: ${body.detail || body.message || text}`);
  return body;
}

async function getPendingEvents() {
  const url = `${BOT_URL}/v1/pending-sign-requests?user_id=${encodeURIComponent(USER_ID)}`;
  const res = await fetch(url, { headers: { "X-User-Id": USER_ID } });
  const text = await res.text();
  let body;
  try {
    body = text ? JSON.parse(text) : {};
  } catch {
    body = {};
  }
  if (!res.ok) throw new Error(`HTTP ${res.status}: ${body.detail || text}`);
  return body.events || [];
}

async function handleSignArweave(requestId) {
  log("handleSignArweave", { requestId });
  const payloadRes = await fetchJson(
    `${BOT_URL}/v1/uploads/${encodeURIComponent(requestId)}/sign-payload`
  );
  const { upload_token, payload_base64, tags, arweave_uploader_url } = payloadRes;
  const uploaderUrl = (arweave_uploader_url || ARWEAVE_SERVICE_URL || "").replace(/\/$/, "");
  if (!uploaderUrl) {
    log("ARWEAVE_SERVICE_URL / arweave_uploader_url missing, skip crystalize");
    return;
  }
  const payloadBytes = Buffer.from(payload_base64 || "", "base64");
  const payloadSize = payloadBytes.length;
  // Мок подписи: заглушка base64 (uploader вернёт 400 signature_invalid без реального ключа)
  const signedDataItemB64 = Buffer.from(Array(512).fill(0)).toString("base64");
  try {
    const crystalizeRes = await fetch(`${uploaderUrl}/v1/crystalize`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        upload_id: requestId,
        upload_token,
        signed_data_item: signedDataItemB64,
        payload_size: payloadSize,
      }),
    });
    const text = await crystalizeRes.text();
    if (!crystalizeRes.ok) {
      log("crystalize error", { status: crystalizeRes.status, body: text });
      return;
    }
    log("crystalize ok", text ? JSON.parse(text) : {});
  } catch (e) {
    log("crystalize exception", { message: e.message });
  }
}

async function handleSignContract(requestId) {
  log("handleSignContract", { requestId });
  const params = await fetchJson(`${BOT_URL}/v1/sign-requests/${encodeURIComponent(requestId)}`);
  const submitUrl = `${BOT_URL}/v1/sign-requests/${encodeURIComponent(requestId)}/submit`;
  const body = { signedTransaction: "0x" + "00".repeat(64) };
  try {
    await fetch(submitUrl, {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-User-Id": USER_ID },
      body: JSON.stringify(body),
    });
    log("submit ok", { requestId });
  } catch (e) {
    log("submit exception", { message: e.message });
  }
}

async function processEvents(events) {
  for (const ev of events) {
    const { request_type, request_id } = ev;
    try {
      if (request_type === "sign_arweave") await handleSignArweave(request_id);
      else if (request_type === "sign_contract") await handleSignContract(request_id);
      else log("unknown request_type", { request_type });
    } catch (e) {
      log("event handler error", { request_type, request_id, message: e.message });
    }
  }
}

async function pollOnce() {
  try {
    const events = await getPendingEvents();
    if (events.length) log("events received", { count: events.length });
    await processEvents(events);
  } catch (e) {
    log("poll error", { message: e.message });
  }
}

async function main() {
  if (!USER_ID) {
    console.error("USER_ID env required");
    process.exit(1);
  }
  log("wallet-mock-runner start", { BOT_URL, USER_ID, POLL_INTERVAL_MS });
  for (;;) {
    await pollOnce();
    await new Promise((r) => setTimeout(r, POLL_INTERVAL_MS));
  }
}

main();
