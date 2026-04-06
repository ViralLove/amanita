#!/usr/bin/env node
/**
 * Wallet-mock runner (W6): опрос бота GET /v1/pending-sign-requests,
 * обработка sign_arweave (GET sign-payload → POST crystalize) и sign_contract (GET sign-request → POST submit).
 *
 * Конфиг: BOT_URL, USER_ID, POLL_INTERVAL_MS, ARWEAVE_SERVICE_URL (опционально).
 * По умолчанию: WALLET_MOCK_ARWEAVE_SIGN_MODE=local-valid (валидный ANS-104 Data Item через фикстуру arweave-uploader).
 * Режим poc-jwk: подпись тем же JWK, что в env (WALLET_MOCK_ARWEAVE_PRIVATE_KEY или WALLET_MOCK_ARWEAVE_PRIVATE_KEY_FILE);
 *   JWK — RSA (типично 2048 или 4096); validateDataItem на uploader принимает динамические длины SPKI/подписи. Альтернативное имя: env-jwk.
 *   Опечатка poc-jw в .env нормализуется в poc-jwk.
 * Явный режим dummy=заглушка (400 signature_invalid на прод-uploader) — только для отладки.
 * ARWEAVE_UPLOADER_PATH — путь к каталогу arweave-uploader (по умолчанию относительно mock-runner).
 *
 * sign_contract: по умолчанию собирается и подписывается tx createActivity(ActivityRegistry) из GET /sign-requests
 * (нужны WALLET_MOCK_PRIVATE_KEY + WALLET_MOCK_RPC_URL). Режим dummy — заглушка 0x00…64 (только отладка).
 *
 * Подгрузка .env: файл `wallet/mock-runner/.env` (рядом с index.js) через dotenv; переменные из окружения
 * процесса имеют приоритет над значениями из файла.
 */

import fs from "node:fs";
import path from "node:path";
import { pathToFileURL, fileURLToPath } from "node:url";
import dotenv from "dotenv";
import { ethers } from "ethers";
import { sanitizeForLog, sanitizeHttpErrorText } from "./log-sanitize.mjs";
import {
  loadWalletMockArweaveJwk,
  createSignedDataItemFromJwk,
  getRsaSpkiDerLengthFromJwk,
  UPLOADER_SUPPORTED_RSA_SPKI_DER_LENGTHS,
} from "./arweave-data-item-jwk.mjs";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
dotenv.config({ path: path.join(__dirname, ".env") });

const BOT_URL = (process.env.BOT_URL || "http://localhost:8000").replace(/\/$/, "");
const USER_ID = process.env.USER_ID || "";
const POLL_INTERVAL_MS = parseInt(process.env.POLL_INTERVAL_MS || "2000", 10);
const ARWEAVE_SERVICE_URL = process.env.ARWEAVE_SERVICE_URL || "";
/** Частая опечатка в .env: poc-jw → трактуем как poc-jwk (RSA JWK для ANS-104). */
const WALLET_MOCK_ARWEAVE_SIGN_MODE_RAW = (
  process.env.WALLET_MOCK_ARWEAVE_SIGN_MODE || "local-valid"
).toLowerCase();
const ARWEAVE_SIGN_MODE =
  WALLET_MOCK_ARWEAVE_SIGN_MODE_RAW === "poc-jw" ? "poc-jwk" : WALLET_MOCK_ARWEAVE_SIGN_MODE_RAW;
const ARWEAVE_UPLOADER_PATH = process.env.ARWEAVE_UPLOADER_PATH
  || path.resolve(__dirname, "../../arweave-uploader");
const WALLET_AUTH_MODE = (process.env.WALLET_AUTH_MODE || "challenge_signature").toLowerCase();
const WALLET_ALLOW_LEGACY_X_USER_ID = (process.env.WALLET_ALLOW_LEGACY_X_USER_ID || "true").toLowerCase() === "true";
const WALLET_MOCK_PRIVATE_KEY = process.env.WALLET_MOCK_PRIVATE_KEY || "";
const WALLET_MOCK_ADDRESS = (process.env.WALLET_MOCK_ADDRESS || "").toLowerCase();
const WALLET_AUTH_SCOPE = process.env.WALLET_AUTH_SCOPE || "signing_flow";
/** real — подписанная createActivity tx; dummy — заглушка как раньше (локальный stub broadcast в боте). */
const WALLET_MOCK_SIGN_CONTRACT_MODE = (process.env.WALLET_MOCK_SIGN_CONTRACT_MODE || "real").toLowerCase();
const WALLET_MOCK_RPC_URL = (process.env.WALLET_MOCK_RPC_URL || "").trim();
/** 0 = Event, 1 = Service (IActivityRegistry.ActivityType). */
const WALLET_MOCK_ACTIVITY_TYPE_RAW = parseInt(process.env.WALLET_MOCK_ACTIVITY_TYPE || "0", 10);
const WALLET_MOCK_ACTIVITY_TYPE =
  WALLET_MOCK_ACTIVITY_TYPE_RAW === 1 ? 1 : 0;

const CREATE_ACTIVITY_ABI = [
  "function createActivity(uint8 activity_type, string metadataCID) external returns (uint256 activityId)",
];
/** Если задан, после успешного POST submit пишется одна строка JSON (для orchestration, см. scripts/shell/run-bullrun-floou.sh). */
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
  if (data != null) {
    try {
      console.log(ts, msg, JSON.stringify(sanitizeForLog(data)));
    } catch {
      console.log(ts, msg, "[log data omitted]");
    }
  } else {
    console.log(ts, msg);
  }
}

/** Эмодзи + короткий заголовок по-русски; data — машиночитаемый JSON как раньше. */
function logRu(emoji, titleRu, data = null) {
  log(`${emoji} ${titleRu}`, data);
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

function initSigner() {
  if (!WALLET_MOCK_PRIVATE_KEY) {
    logRu(
      "⚠️",
      "EVM: WALLET_MOCK_PRIVATE_KEY пуст — sign_contract в режиме real не сработает; остальное (poll, Arweave) по политике бота",
    );
    return;
  }
  try {
    signerWallet = new ethers.Wallet(WALLET_MOCK_PRIVATE_KEY);
    signerAddress = signerWallet.address.toLowerCase();
    logRu("🔑", "EVM-подписант готов (ethers.Wallet из приватного ключа)", { signerAddress });
  } catch (e) {
    logRu("❌", "EVM: не удалось создать Wallet из WALLET_MOCK_PRIVATE_KEY", { message: e.message });
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
    logRu("🔐", "Wallet-auth: challenge/verify прошли, Bearer для запросов к боту выдан", {
      signerAddress,
      authExpiresAt,
    });
    return true;
  } catch (e) {
    logRu("❌", "Wallet-auth: не удалось обновить сессию", {
      message: e.message,
      errorCode: e.errorCode || null,
    });
    return false;
  }
}

async function callBotJson(url, options = {}) {
  try {
    return await fetchJson(url, options);
  } catch (e) {
    if (!isAuthError(e)) throw e;
    logRu("🔄", "401/403 по auth — пробуем обновить Bearer и повторить запрос", {
      status: e.status,
      errorCode: e.errorCode || null,
    });
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
        logRu("🏥", "Бот отвечает /health — можно опрашивать pending-sign-requests", {
          attempt: i + 1,
          url: healthUrl,
        });
        return;
      }
    } catch {
      /* still starting */
    }
    await new Promise((r) => setTimeout(r, delayMs));
  }
  logRu("⏳", "Таймаут ожидания /health — всё равно начинаем опрос (проверь BOT_URL)", {
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
  logRu("🪙", "Шаг 1/2 Floou: sign_arweave — грузим sign-payload и шлём в uploader (crystalize)", {
    requestId,
  });
  floouCrystalizeOk = false;
  floouBundleTxId = null;
  const payloadRes = await callBotJson(
    `${BOT_URL}/v1/uploads/${encodeURIComponent(requestId)}/sign-payload`
  );
  const { upload_token, payload_base64, tags, arweave_uploader_url } = payloadRes;
  const uploaderUrl = (arweave_uploader_url || ARWEAVE_SERVICE_URL || "").replace(/\/$/, "");
  if (!uploaderUrl) {
    logRu("⛔", "Нет URL uploader (ни в ответе бота, ни ARWEAVE_SERVICE_URL) — crystalize пропущен");
    return;
  }
  const payloadBytes = Buffer.from(payload_base64 || "", "base64");
  const payloadSize = payloadBytes.length;
  let signedDataItemB64;
  if (ARWEAVE_SIGN_MODE === "dummy") {
    logRu(
      "🧪",
      "Режим dummy: подпись Data Item фиктивная — на реальном uploader будет signature_invalid",
    );
    signedDataItemB64 = Buffer.from(Array(512).fill(0)).toString("base64");
  } else if (ARWEAVE_SIGN_MODE === "local-valid") {
    try {
      const fixturePath = path.join(ARWEAVE_UPLOADER_PATH, "tests/fixtures/valid-data-item.js");
      const mod = await import(pathToFileURL(fixturePath).href);
      signedDataItemB64 = await mod.createValidDataItem(requestId, payloadBytes);
    } catch (e) {
      logRu("❌", "local-valid: не собрали Data Item из фикстуры", { message: e.message });
      return;
    }
  } else if (ARWEAVE_SIGN_MODE === "poc-jwk" || ARWEAVE_SIGN_MODE === "env-jwk") {
    let jwk;
    try {
      jwk = loadWalletMockArweaveJwk();
    } catch (e) {
      logRu("❌", "poc-jwk: не загрузили JWK", { message: e.message });
      return;
    }
    if (!jwk) {
      logRu("⛔", "poc-jwk: нет WALLET_MOCK_ARWEAVE_PRIVATE_KEY / _FILE — crystalize пропущен");
      return;
    }
    try {
      signedDataItemB64 = await createSignedDataItemFromJwk(jwk, requestId, payloadBytes);
    } catch (e) {
      logRu("❌", "poc-jwk: не собрали signed Data Item", { message: e.message });
      return;
    }
  } else {
    logRu("⛔", "Неизвестный WALLET_MOCK_ARWEAVE_SIGN_MODE — crystalize не вызываем", {
      mode: ARWEAVE_SIGN_MODE,
    });
    return;
  }
  try {
    logRu("🌐", "POST crystalize → uploader (очередь публикации bundle в Arweave)", {
      url: `${uploaderUrl}/v1/crystalize`,
      upload_id: requestId,
      payload_size: payloadSize,
      sign_mode: ARWEAVE_SIGN_MODE,
    });
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
      logRu("❌", "crystalize отклонён uploader’ом", {
        status: crystalizeRes.status,
        body: sanitizeHttpErrorText(text),
      });
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
    logRu("✅", "crystalize принят: bundle уходит в Arweave (см. bundle_tx_id / arweave_url)", {
      ...crystalizeJson,
      подсказка: "полный tx в Permaweb — по arweave_url или bundle_tx_id",
    });
  } catch (e) {
    logRu("❌", "crystalize: сетевая ошибка или не-JSON ответ", { message: e.message });
  }
}

async function handleSignContract(requestId) {
  logRu("📜", "Шаг 2/2 Floou: sign_contract — GET параметров и подпись createActivity на EVM", {
    requestId,
  });
  /** sign_contract появляется только после callback uploader → bot для этого upload. */
  const callbackOk = true;
  const sr = await callBotJson(`${BOT_URL}/v1/sign-requests/${encodeURIComponent(requestId)}`);
  const submitUrl = `${BOT_URL}/v1/sign-requests/${encodeURIComponent(requestId)}/submit`;

  let body;
  if (WALLET_MOCK_SIGN_CONTRACT_MODE === "dummy") {
    body = { signedTransaction: "0x" + "00".repeat(64) };
    logRu("🧪", "sign_contract: режим dummy — заглушка raw tx (только отладка broadcast на боте)");
  } else {
    if (!signerWallet) {
      logRu(
        "⏭️",
        "sign_contract пропущен: нет EVM-ключа — задай WALLET_MOCK_PRIVATE_KEY или WALLET_MOCK_SIGN_CONTRACT_MODE=dummy",
      );
      return;
    }
    if (!WALLET_MOCK_RPC_URL) {
      logRu("⏭️", "sign_contract пропущен: нужен WALLET_MOCK_RPC_URL (JsonRpcProvider для той же сети, что chain_id у бота)");
      return;
    }
    const contractAddress = (sr.contract_address || "").trim();
    const cid = sr.cid;
    const chainIdStr = String(sr.chain_id || "").trim();
    if (!contractAddress || cid == null || cid === "") {
      logRu("⛔", "В ответе GET /sign-requests не хватает contract_address или cid", {
        hasContract: !!contractAddress,
        hasCid: cid != null && cid !== "",
      });
      return;
    }
    const chainId = parseInt(chainIdStr, 10);
    if (!Number.isFinite(chainId) || chainId <= 0) {
      logRu("⛔", "Некорректный chain_id в sign-request", { chain_id: chainIdStr });
      return;
    }
    try {
      const provider = new ethers.JsonRpcProvider(WALLET_MOCK_RPC_URL);
      const wallet = signerWallet.connect(provider);
      /** До populateTransaction/signTransaction: в ethers v6 chainId mismatch может броситься уже на populate. */
      let rpcNetwork = null;
      let rpcEthChainId = null;
      try {
        rpcNetwork = await provider.getNetwork();
      } catch (eNet) {
        rpcNetwork = { error: eNet && eNet.message ? eNet.message : String(eNet) };
      }
      try {
        rpcEthChainId = await provider.send("eth_chainId", []);
      } catch (eCid) {
        rpcEthChainId = `error: ${eCid && eCid.message ? eCid.message : String(eCid)}`;
      }
      logRu("🔗", "Проверка сети: chain_id из API должен совпадать с eth_chainId у WALLET_MOCK_RPC_URL", {
        chain_id_from_get_sign_requests: sr.chain_id,
        tx_chainId_for_sign: chainId,
        rpc_getNetwork:
          rpcNetwork && typeof rpcNetwork.chainId !== "undefined"
            ? { chainId: rpcNetwork.chainId.toString(), name: rpcNetwork.name }
            : rpcNetwork,
        rpc_eth_chainId: rpcEthChainId,
        wallet_mock_rpc_url_set: !!WALLET_MOCK_RPC_URL,
      });
      const iface = new ethers.Interface(CREATE_ACTIVITY_ABI);
      const data = iface.encodeFunctionData("createActivity", [WALLET_MOCK_ACTIVITY_TYPE, String(cid)]);
      const txReq = await wallet.populateTransaction({
        to: contractAddress,
        data,
        chainId: BigInt(chainId),
        gasLimit: 800000n,
      });
      const signedTx = await wallet.signTransaction(txReq);
      body = { signedTransaction: signedTx };
      let signedTxHashLocal = null;
      try {
        signedTxHashLocal = ethers.Transaction.from(signedTx).hash;
      } catch {
        signedTxHashLocal = null;
      }
      logRu(
        "✍️",
        "Транзакция подписана локально (ещё не в блокчейне). Hash совпадёт с тем, что покажет нода после sendRawTransaction",
        {
          signed_tx_hash: signedTxHashLocal,
          from: wallet.address,
          to: contractAddress,
          chainId,
          activity_type: WALLET_MOCK_ACTIVITY_TYPE,
          metadata_cid: String(cid),
        },
      );
    } catch (e) {
      const msg = e && typeof e.message === "string" ? e.message : String(e);
      logRu("❌", "Сборка или signTransaction не удалась (часто chainId mismatch или RPC)", {
        message: msg,
        code: e && typeof e === "object" && e !== null && "code" in e ? e.code : undefined,
        shortMessage:
          e && typeof e === "object" && e !== null && "shortMessage" in e ? e.shortMessage : undefined,
      });
      return;
    }
  }

  try {
    const submitRes = await callBotJson(submitUrl, {
      method: "POST",
      body: JSON.stringify(body),
    });
    const txHash = submitRes && typeof submitRes.tx_hash === "string" ? submitRes.tx_hash : null;
    logRu(
      "📡",
      "POST /sign-requests/.../submit успешен: бот сделал eth_sendRawTransaction через свой WEB3_PROVIDER_URI",
      {
        sign_request_id: requestId,
        tx_hash: txHash,
        как_проверить:
          "тот же 0x… в логах anvil/hardhat в строке «Transaction:»; в эксплорере mainnet/testnet — по сети деплоя",
      },
    );
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
        logRu("⚠️", "Не удалось записать FLOOU_DONE_MARKER_FILE", { message: e.message });
      }
    }
  } catch (e) {
    logRu("❌", "POST submit на бот упал (broadcast / валидация raw tx)", { message: e.message });
  }
}

async function processEvents(events) {
  for (const ev of events) {
    const { request_type, request_id } = ev;
    try {
      if (request_type === "sign_arweave") await handleSignArweave(request_id);
      else if (request_type === "sign_contract") await handleSignContract(request_id);
      else logRu("❓", "Неизвестный request_type в очереди бота", { request_type });
    } catch (e) {
      logRu("❌", "Ошибка обработчика события", { request_type, request_id, message: e.message });
    }
  }
}

async function pollOnce() {
  try {
    const events = await getPendingEvents();
    if (events.length) {
      logRu("📬", "Бот вернул pending-события (sign_arweave / sign_contract)", { count: events.length });
    }
    await processEvents(events);
  } catch (e) {
    logRu("❌", "Ошибка опроса GET /pending-sign-requests", { message: e.message });
  }
}

async function main() {
  if (!USER_ID) {
    console.error("USER_ID env required");
    process.exit(1);
  }
  initSigner();
  if (WALLET_AUTH_MODE === "challenge_signature" && !signerWallet) {
    logRu(
      "🔓",
      "Wallet-auth (challenge): приватного ключа нет — сессия Bearer не поднимется; опрос с legacy X-User-Id если бот разрешает",
    );
  }
  if (WALLET_AUTH_MODE === "challenge_signature") {
    await refreshWalletAuthSession();
  }
  await waitForBotHealth();
  let pocJwkHint = null;
  if (ARWEAVE_SIGN_MODE === "poc-jwk" || ARWEAVE_SIGN_MODE === "env-jwk") {
    try {
      const j = loadWalletMockArweaveJwk();
      pocJwkHint = {
        poc_jwk_loaded: !!j,
        poc_jwk_source: process.env.WALLET_MOCK_ARWEAVE_PRIVATE_KEY
          ? "env"
          : (process.env.WALLET_MOCK_ARWEAVE_PRIVATE_KEY_FILE ? "file" : "none"),
      };
      if (j) {
        try {
          const spkiBytes = getRsaSpkiDerLengthFromJwk(j);
          pocJwkHint.poc_jwk_spki_bytes = spkiBytes;
          if (!UPLOADER_SUPPORTED_RSA_SPKI_DER_LENGTHS.includes(spkiBytes)) {
            logRu(
              "⚠️",
              "poc-jwk: нестандартная длина SPKI в JWK — uploader может отклонить, если не в whitelist",
              {
                spki_bytes: spkiBytes,
                known_lengths: UPLOADER_SUPPORTED_RSA_SPKI_DER_LENGTHS,
              },
            );
          }
        } catch (e) {
          pocJwkHint.poc_jwk_spki_error = e.message;
        }
      }
    } catch (e) {
      pocJwkHint = { poc_jwk_loaded: false, poc_jwk_error: e.message };
    }
  }
  logRu("🚀", "mock-runner запущен — круговой опрос бота и обработка очереди подписей", {
    BOT_URL,
    USER_ID,
    POLL_INTERVAL_MS,
    ARWEAVE_SIGN_MODE,
    ...(WALLET_MOCK_ARWEAVE_SIGN_MODE_RAW === "poc-jw"
      ? { подсказка: "в .env было poc-jw → нормализовано в poc-jwk" }
      : {}),
    WALLET_AUTH_MODE,
    WALLET_ALLOW_LEGACY_X_USER_ID,
    signerAddress,
    WALLET_MOCK_SIGN_CONTRACT_MODE,
    WALLET_MOCK_RPC_URL: WALLET_MOCK_RPC_URL ? "(set)" : "(missing)",
    ...pocJwkHint,
  });
  for (;;) {
    await pollOnce();
    await new Promise((r) => setTimeout(r, POLL_INTERVAL_MS));
  }
}

main();
