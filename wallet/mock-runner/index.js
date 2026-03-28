#!/usr/bin/env node
/**
 * Wallet-mock runner (W6): опрос бота GET /v1/pending-sign-requests,
 * обработка sign_arweave (GET sign-payload → POST crystalize) и sign_contract (GET sign-request → POST submit).
 *
 * Конфиг: BOT_URL, USER_ID, POLL_INTERVAL_MS, ARWEAVE_SERVICE_URL (опционально).
 * Вариант A (локальная валидная подпись): WALLET_MOCK_ARWEAVE_SIGN_MODE=local-valid,
 * опционально ARWEAVE_UPLOADER_PATH — путь к каталогу arweave-uploader (по умолчанию относительно mock-runner).
 */

import fs from "node:fs";
import path from "node:path";
import { pathToFileURL, fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

const BOT_URL = (process.env.BOT_URL || "http://localhost:8000").replace(/\/$/, "");
const USER_ID = process.env.USER_ID || "";
const POLL_INTERVAL_MS = parseInt(process.env.POLL_INTERVAL_MS || "2000", 10);
const ARWEAVE_SERVICE_URL = process.env.ARWEAVE_SERVICE_URL || "";
const ARWEAVE_SIGN_MODE = (process.env.WALLET_MOCK_ARWEAVE_SIGN_MODE || "dummy").toLowerCase();
const ARWEAVE_UPLOADER_PATH = process.env.ARWEAVE_UPLOADER_PATH
  || path.resolve(__dirname, "../../arweave-uploader");
const WALLET_AUTH_MODE = (process.env.WALLET_AUTH_MODE || "challenge_signature").toLowerCase();
const WALLET_ALLOW_LEGACY_X_USER_ID = (process.env.WALLET_ALLOW_LEGACY_X_USER_ID || "true").toLowerCase() === "true";
const WALLET_MOCK_PRIVATE_KEY = process.env.WALLET_MOCK_PRIVATE_KEY || "";
const WALLET_MOCK_ADDRESS = (process.env.WALLET_MOCK_ADDRESS || "").toLowerCase();
const WALLET_AUTH_SCOPE = process.env.WALLET_AUTH_SCOPE || "signing_flow";
/** Если задан, после успешного POST submit пишется одна строка JSON (для orchestration, см. scripts/run-bullrun-floou.sh). */
const FLOOU_DONE_MARKER_FILE = (process.env.FLOOU_DONE_MARKER_FILE || "").trim();

/** Состояние одного прогона floou (один upload_id): для structured summary и FLOOU_STRICT в оркестраторе. */
let floouCrystalizeOk = false;
let floouBundleTxId = null;

let signerWallet = null;
let signerAddress = WALLET_MOCK_ADDRESS || null;
let authToken = null;
let authExpiresAt = null;

function log(msg, data = null) {
  const ts = new Date().toISOString();
  if (data != null) console.log(ts, msg, JSON.stringify(data));
  else console.log(ts, msg);
}

async function fetchJson(url, options = {}) {
  const headers = { "Content-Type": "application/json", ...options.headers };
  if (WALLET_ALLOW_LEGACY_X_USER_ID || !authToken) headers["X-User-Id"] = USER_ID;
  if (authToken) {
    headers.Authorization = `Bearer ${authToken}`;
    if (signerAddress) headers["X-Wallet-Address"] = signerAddress;
  }
  const res = await fetch(url, {
    ...options,
    headers,
  });
  const text = await res.text();
  let body;
  try {
    body = text ? JSON.parse(text) : {};
  } catch {
    body = {};
  }
  if (!res.ok) {
    const detail = body?.detail;
    const errorCode = typeof detail === "object" && detail ? detail.error_code : null;
    const message = typeof detail === "string" ? detail : (body.message || text);
    const err = new Error(`HTTP ${res.status}: ${errorCode || message}`);
    err.status = res.status;
    err.errorCode = errorCode;
    err.payload = body;
    throw err;
  }
  return body;
}

function isAuthError(err) {
  if (!err) return false;
  if (![401, 403, 409].includes(err.status)) return false;
  if (typeof err.errorCode === "string" && err.errorCode.startsWith("auth_")) return true;
  return typeof err.message === "string" && err.message.includes("auth");
}

async function initSigner() {
  if (!WALLET_MOCK_PRIVATE_KEY) {
    log("wallet auth: private key missing, runner will use fallback mode if server allows");
    return;
  }
  try {
    const ethers = await import("ethers");
    signerWallet = new ethers.Wallet(WALLET_MOCK_PRIVATE_KEY);
    signerAddress = signerWallet.address.toLowerCase();
    log("wallet auth signer ready", { signerAddress });
  } catch (e) {
    log("wallet auth signer init failed, fallback mode only", { message: e.message });
  }
}

async function refreshWalletAuthSession() {
  if (WALLET_AUTH_MODE !== "challenge_signature") return false;
  if (!signerWallet || !signerAddress) return false;
  try {
    const challenge = await fetchJson(`${BOT_URL}/v1/wallet-auth/challenge`, {
      method: "POST",
      body: JSON.stringify({
        wallet_address: signerAddress,
        user_id: USER_ID,
        auth_scope: WALLET_AUTH_SCOPE,
      }),
    });
    const signature = await signerWallet.signMessage(challenge.canonical_message);
    const verify = await fetchJson(`${BOT_URL}/v1/wallet-auth/verify`, {
      method: "POST",
      body: JSON.stringify({
        challenge_id: challenge.challenge_id,
        wallet_address: signerAddress,
        user_id: USER_ID,
        signature,
      }),
    });
    authToken = verify.wallet_auth_token;
    authExpiresAt = verify.expires_at || null;
    log("wallet auth verified", { signerAddress, authExpiresAt });
    return true;
  } catch (e) {
    log("wallet auth refresh failed", { message: e.message, errorCode: e.errorCode || null });
    return false;
  }
}

async function callBotJson(url, options = {}) {
  try {
    return await fetchJson(url, options);
  } catch (e) {
    if (!isAuthError(e)) throw e;
    log("auth error detected, trying refresh/retry", { status: e.status, errorCode: e.errorCode || null });
    const refreshed = await refreshWalletAuthSession();
    if (!refreshed) throw e;
    return fetchJson(url, options);
  }
}

/** Ждём HTTP 200 на /health, чтобы не логировать ложные «ошибки» опроса до старта uvicorn. */
async function waitForBotHealth(maxAttempts = 60, delayMs = 500) {
  const healthUrl = `${BOT_URL}/health`;
  for (let i = 0; i < maxAttempts; i++) {
    try {
      const res = await fetch(healthUrl);
      if (res.ok) {
        log("bot health ok", { attempt: i + 1, url: healthUrl });
        return;
      }
    } catch {
      /* still starting */
    }
    await new Promise((r) => setTimeout(r, delayMs));
  }
  log("bot health wait timeout, continuing poll anyway", {
    attempts: maxAttempts,
    url: healthUrl,
  });
}

async function getPendingEvents() {
  const url = `${BOT_URL}/v1/pending-sign-requests?user_id=${encodeURIComponent(USER_ID)}`;
  const body = await callBotJson(url);
  return body.events || [];
}

async function handleSignArweave(requestId) {
  log("handleSignArweave", { requestId });
  floouCrystalizeOk = false;
  floouBundleTxId = null;
  const payloadRes = await callBotJson(
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
  let signedDataItemB64;
  if (ARWEAVE_SIGN_MODE === "local-valid") {
    try {
      const fixturePath = path.join(ARWEAVE_UPLOADER_PATH, "tests/fixtures/valid-data-item.js");
      const mod = await import(pathToFileURL(fixturePath).href);
      signedDataItemB64 = await mod.createValidDataItem(requestId, payloadBytes);
    } catch (e) {
      log("createValidDataItem failed, skip crystalize", { message: e.message });
      return;
    }
  } else {
    // Мок подписи: заглушка base64 (uploader вернёт 400 signature_invalid без реального ключа)
    signedDataItemB64 = Buffer.from(Array(512).fill(0)).toString("base64");
  }
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
    let crystalizeJson = {};
    try {
      crystalizeJson = text ? JSON.parse(text) : {};
    } catch {
      crystalizeJson = {};
    }
    floouCrystalizeOk = true;
    floouBundleTxId = crystalizeJson.bundle_tx_id || null;
    log("crystalize ok", crystalizeJson);
  } catch (e) {
    log("crystalize exception", { message: e.message });
  }
}

async function handleSignContract(requestId) {
  log("handleSignContract", { requestId });
  /** sign_contract появляется только после callback uploader → bot для этого upload. */
  const callbackOk = true;
  await callBotJson(`${BOT_URL}/v1/sign-requests/${encodeURIComponent(requestId)}`);
  const submitUrl = `${BOT_URL}/v1/sign-requests/${encodeURIComponent(requestId)}/submit`;
  const body = { signedTransaction: "0x" + "00".repeat(64) };
  try {
    const submitRes = await callBotJson(submitUrl, {
      method: "POST",
      body: JSON.stringify(body),
    });
    const txHash = submitRes && typeof submitRes.tx_hash === "string" ? submitRes.tx_hash : null;
    log("submit ok", { requestId, tx_hash: txHash });
    if (FLOOU_DONE_MARKER_FILE) {
      try {
        const payload = JSON.stringify({
          ok: true,
          crystalize_ok: floouCrystalizeOk,
          bundle_tx_id: floouBundleTxId,
          callback_ok: callbackOk,
          submit_ok: true,
          tx_hash: txHash,
          sign_request_id: requestId,
          at: new Date().toISOString(),
        });
        fs.writeFileSync(FLOOU_DONE_MARKER_FILE, `${payload}\n`, "utf8");
      } catch (e) {
        log("floou_done_marker write failed", { message: e.message });
      }
    }
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
  await initSigner();
  if (WALLET_AUTH_MODE === "challenge_signature") {
    await refreshWalletAuthSession();
  }
  await waitForBotHealth();
  log("wallet-mock-runner start", {
    BOT_URL,
    USER_ID,
    POLL_INTERVAL_MS,
    ARWEAVE_SIGN_MODE,
    WALLET_AUTH_MODE,
    WALLET_ALLOW_LEGACY_X_USER_ID,
    signerAddress,
  });
  for (;;) {
    await pollOnce();
    await new Promise((r) => setTimeout(r, POLL_INTERVAL_MS));
  }
}

main();
