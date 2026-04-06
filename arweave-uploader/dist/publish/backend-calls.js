/**
 * Вызовы микросервиса → Backend: PUT status, POST callback.
 * Authorization: Bearer NODE_AUTH_TOKEN (тот же секрет, что на bot для uploads status/callback).
 * При BACKEND_USE_MOCK=true реальный fetch не выполняется; код ответа задаётся env или per-request override.
 */

import { logInfo, logWarn } from "../logging.js";

let warnedBackendUrlAmbiguous = false;

/** 0.0.0.0 — адрес привязки, не надёжная цель для исходящего HTTP с uploader; лучше 127.0.0.1 / localhost. */
function warnIfBackendUrlAmbiguous(baseUrl) {
  if (warnedBackendUrlAmbiguous) return;
  if (typeof baseUrl !== "string" || !baseUrl.includes("0.0.0.0")) return;
  warnedBackendUrlAmbiguous = true;
  logWarn("publish.backend.url_ambiguous", {
    BACKEND_URL: baseUrl.replace(/\/$/, ""),
    hint: "Исходящие запросы с uploader должны идти на адрес, где слушает API (часто http://127.0.0.1:PORT или публичный host). 0.0.0.0 как URL назначения часто даёт сбой или не тот интерфейс.",
  });
}

function isBackendMockEnabled() {
  const v = process.env.BACKEND_USE_MOCK;
  return v === "true" || v === "1" || (typeof v === "string" && v.toLowerCase() === "true");
}

/** Допустимые коды для мока: 200, 404, 409; иное или пусто → 200. */
export function normalizeMockStatus(value) {
  if (value === 404 || value === 409) return value;
  if (value === 200) return 200;
  if (typeof value === "string") {
    const n = parseInt(value, 10);
    if (n === 404 || n === 409) return n;
  }
  return 200;
}

export async function putStatus(
  uploadId,
  status,
  failureCode,
  requestMockPutStatus
) {
  if (isBackendMockEnabled()) {
    const code =
      requestMockPutStatus !== undefined
        ? normalizeMockStatus(requestMockPutStatus)
        : normalizeMockStatus(process.env.BACKEND_MOCK_PUT_STATUS);
    logInfo("publish.mock.putStatus", {
      uploadId,
      status,
      failureCode,
      simulatedStatus: code,
    });
    if (code === 404 || code === 409) {
      logInfo("publish.mock.putStatus.simulated", { code });
    }
    return;
  }
  const baseUrl = process.env.BACKEND_URL;
  const secret = process.env.NODE_AUTH_TOKEN;
  if (!baseUrl || !secret) {
    logWarn("publish.backend.skip", {
      reason: "BACKEND_URL or NODE_AUTH_TOKEN not set; skipping putStatus",
    });
    return;
  }
  warnIfBackendUrlAmbiguous(baseUrl);
  const url = `${baseUrl.replace(/\/$/, "")}/v1/uploads/${uploadId}/status`;
  const body =
    status === "failed"
      ? JSON.stringify({ status, failure_code: failureCode })
      : JSON.stringify({ status });
  const t0 = Date.now();
  logInfo("publish.backend.request", {
    op: "putStatus",
    method: "PUT",
    url,
    uploadId,
    bodyStatus: status,
    failureCode: failureCode ?? null,
  });
  try {
    const res = await fetch(url, {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${secret}`,
      },
      body,
    });
    const durationMs = Date.now() - t0;
    const text = await res.text();
    if (!res.ok) {
      logWarn("publish.putStatus.failed", {
        uploadId,
        httpStatus: res.status,
        durationMs,
        url,
        body: text.slice(0, 2000),
      });
    } else {
      logInfo("publish.putStatus.ok", {
        uploadId,
        httpStatus: res.status,
        durationMs,
        responseBytes: text.length,
        responsePreview: text.length ? text.slice(0, 500) : "(empty)",
      });
    }
  } catch (e) {
    logWarn("publish.putStatus.networkError", {
      uploadId,
      url,
      durationMs: Date.now() - t0,
      error: e?.message ?? String(e),
    });
  }
}

export async function postCallback(
  uploadId,
  itemId,
  bundleTxId,
  publishedAt,
  requestMockCallback
) {
  if (isBackendMockEnabled()) {
    const code =
      requestMockCallback !== undefined
        ? normalizeMockStatus(requestMockCallback)
        : normalizeMockStatus(process.env.BACKEND_MOCK_CALLBACK);
    logInfo("publish.mock.postCallback", {
      uploadId,
      itemId,
      bundleTxId,
      publishedAt,
      simulatedStatus: code,
    });
    if (code === 404 || code === 409) {
      logInfo("publish.mock.postCallback.simulated", { code });
    }
    return;
  }
  const baseUrl = process.env.BACKEND_URL;
  const secret = process.env.NODE_AUTH_TOKEN;
  if (!baseUrl || !secret) {
    logWarn("publish.backend.skip", {
      reason: "BACKEND_URL or NODE_AUTH_TOKEN not set; skipping postCallback",
    });
    return;
  }
  warnIfBackendUrlAmbiguous(baseUrl);
  const url = `${baseUrl.replace(/\/$/, "")}/v1/uploads/callback`;
  const body = JSON.stringify({
    upload_id: uploadId,
    item_id: itemId,
    bundle_tx_id: bundleTxId,
    published_at: publishedAt,
  });
  const t0 = Date.now();
  logInfo("publish.backend.request", {
    op: "postCallback",
    method: "POST",
    url,
    uploadId,
    itemId,
    bundleTxId,
    publishedAt,
  });
  try {
    const res = await fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${secret}`,
      },
      body,
    });
    const durationMs = Date.now() - t0;
    const text = await res.text();
    if (!res.ok) {
      logWarn("publish.postCallback.failed", {
        uploadId,
        httpStatus: res.status,
        durationMs,
        url,
        body: text.slice(0, 2000),
      });
    } else {
      logInfo("publish.postCallback.ok", {
        uploadId,
        httpStatus: res.status,
        durationMs,
        responseBytes: text.length,
        responsePreview: text.length ? text.slice(0, 500) : "(empty)",
      });
    }
  } catch (e) {
    logWarn("publish.postCallback.networkError", {
      uploadId,
      url,
      durationMs: Date.now() - t0,
      error: e?.message ?? String(e),
    });
  }
}
