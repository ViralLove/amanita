/**
 * Вызовы микросервиса → Backend: PUT status, POST callback.
 * Authorization: Bearer UPLOADER_TO_BACKEND_SECRET (или EDGE_TO_BACKEND_SECRET).
 * При BACKEND_USE_MOCK=true реальный fetch не выполняется; код ответа задаётся env или per-request override.
 */

import { logInfo, logWarn } from "../logging.js";

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
  const secret =
    process.env.UPLOADER_TO_BACKEND_SECRET || process.env.EDGE_TO_BACKEND_SECRET;
  if (!baseUrl || !secret) {
    logWarn("publish.backend.skip", {
      reason: "BACKEND_URL or secret not set; skipping putStatus",
    });
    return;
  }
  const url = `${baseUrl.replace(/\/$/, "")}/v1/uploads/${uploadId}/status`;
  const body =
    status === "failed"
      ? JSON.stringify({ status, failure_code: failureCode })
      : JSON.stringify({ status });
  try {
    const res = await fetch(url, {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${secret}`,
      },
      body,
    });
    if (!res.ok) {
      logWarn("publish.putStatus.failed", {
        status: res.status,
        body: await res.text(),
      });
    }
  } catch (e) {
    logWarn("publish.putStatus.networkError", { error: e?.message ?? String(e) });
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
  const secret =
    process.env.UPLOADER_TO_BACKEND_SECRET || process.env.EDGE_TO_BACKEND_SECRET;
  if (!baseUrl || !secret) {
    logWarn("publish.backend.skip", {
      reason: "BACKEND_URL or secret not set; skipping postCallback",
    });
    return;
  }
  const url = `${baseUrl.replace(/\/$/, "")}/v1/uploads/callback`;
  const body = JSON.stringify({
    upload_id: uploadId,
    item_id: itemId,
    bundle_tx_id: bundleTxId,
    published_at: publishedAt,
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
    if (!res.ok) {
      logWarn("publish.postCallback.failed", {
        status: res.status,
        body: await res.text(),
      });
    }
  } catch (e) {
    logWarn("publish.postCallback.networkError", {
      error: e?.message ?? String(e),
    });
  }
}
